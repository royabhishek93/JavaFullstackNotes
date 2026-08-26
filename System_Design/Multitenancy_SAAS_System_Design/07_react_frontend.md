# React.js Frontend — Multitenant Architecture

## The Multitenant Frontend Challenge

In SAP BTP, the App Router serves per-tenant URLs. In our architecture:
- **Single React build** is deployed to S3
- **CloudFront** serves it to all tenant subdomains
- React detects the subdomain at **runtime** to know which tenant it is
- Per-tenant theming, branding, and feature flags are loaded dynamically

---

## Project Structure

```
frontend/
├── src/
│   ├── tenant/
│   │   ├── TenantContext.tsx        ← tenant detection + context provider
│   │   ├── useTenant.ts             ← hook for consuming tenant info
│   │   ├── TenantThemeProvider.tsx  ← dynamic theme loading
│   │   └── tenantConfig.ts          ← per-tenant config type
│   ├── auth/
│   │   ├── AuthProvider.tsx         ← Cognito auth flow
│   │   ├── useAuth.ts
│   │   ├── PrivateRoute.tsx
│   │   └── callback/CallbackPage.tsx
│   ├── api/
│   │   ├── apiClient.ts             ← Axios with tenant + auth headers
│   │   └── hooks/                   ← React Query hooks per domain
│   ├── pages/
│   │   ├── admin/                   ← Admin portal (provider)
│   │   └── app/                     ← Tenant app pages
│   └── App.tsx
```

---

## 1. Tenant Detection from Subdomain

```typescript
// src/tenant/TenantContext.tsx

interface TenantInfo {
  tenantId: string;
  displayName: string;
  logoUrl: string;
  primaryColor: string;
  features: string[];
  plan: 'FREE' | 'PRO' | 'ENTERPRISE';
}

interface TenantContextValue {
  tenant: TenantInfo | null;
  isLoading: boolean;
  error: string | null;
}

const TenantContext = createContext<TenantContextValue>({
  tenant: null, isLoading: true, error: null
});

export function TenantProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<TenantContextValue>({
    tenant: null, isLoading: true, error: null
  });

  useEffect(() => {
    const tenantId = extractTenantFromSubdomain();

    if (!tenantId) {
      setState({ tenant: null, isLoading: false, error: 'Invalid tenant URL' });
      return;
    }

    // Fetch tenant config from public endpoint (no auth required)
    fetch(`/api/public/tenants/${tenantId}/config`)
      .then(res => {
        if (!res.ok) throw new Error('Tenant not found');
        return res.json() as Promise<TenantInfo>;
      })
      .then(tenant => setState({ tenant, isLoading: false, error: null }))
      .catch(err => setState({ tenant: null, isLoading: false, error: err.message }));
  }, []);

  return (
    <TenantContext.Provider value={state}>
      {children}
    </TenantContext.Provider>
  );
}

function extractTenantFromSubdomain(): string | null {
  const hostname = window.location.hostname;
  // acmecorp.app.yourdomain.com → "acmecorp"
  const match = hostname.match(/^([a-z0-9-]+)\.app\.yourdomain\.com$/);
  return match ? match[1] : null;
}

export function useTenant(): TenantInfo {
  const { tenant, isLoading, error } = useContext(TenantContext);
  if (isLoading) throw new Promise(resolve => setTimeout(resolve, 100)); // Suspense
  if (error || !tenant) throw new Error(error ?? 'Tenant unavailable');
  return tenant;
}
```

---

## 2. Dynamic Tenant Theming (MUI / Tailwind)

```typescript
// src/tenant/TenantThemeProvider.tsx

import { createTheme, ThemeProvider } from '@mui/material/styles';

export function TenantThemeProvider({ children }: { children: ReactNode }) {
  const { tenant } = useContext(TenantContext);

  const theme = useMemo(() => {
    if (!tenant) return defaultTheme;

    return createTheme({
      palette: {
        primary: { main: tenant.primaryColor },
        // secondary, background derived from primary
      },
      typography: {
        fontFamily: tenant.fontFamily ?? 'Inter, sans-serif',
      },
      components: {
        MuiButton: {
          styleOverrides: {
            root: {
              borderRadius: tenant.borderRadius ?? 8,
            }
          }
        }
      }
    });
  }, [tenant?.primaryColor, tenant?.fontFamily]);

  return (
    <ThemeProvider theme={theme}>
      {/* Inject tenant logo as CSS variable */}
      <style>{`
        :root {
          --tenant-logo: url('${tenant?.logoUrl}');
          --tenant-color: ${tenant?.primaryColor ?? '#1976d2'};
        }
      `}</style>
      {children}
    </ThemeProvider>
  );
}
```

---

## 3. Cognito Auth Flow

```typescript
// src/auth/AuthProvider.tsx

const COGNITO_DOMAIN = 'https://auth.app.yourdomain.com';
const CLIENT_ID = import.meta.env.VITE_COGNITO_CLIENT_ID;

interface AuthContextValue {
  user: CognitoUser | null;
  isAuthenticated: boolean;
  login: () => void;
  logout: () => void;
  getAccessToken: () => Promise<string>;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [tokens, setTokens] = useTokenStorage(); // httpOnly cookie for refresh

  const login = useCallback(() => {
    const redirectUri = encodeURIComponent(window.location.origin + '/callback');
    const loginUrl = `${COGNITO_DOMAIN}/login`
      + `?client_id=${CLIENT_ID}`
      + `&response_type=code`
      + `&scope=email+openid+profile`
      + `&redirect_uri=${redirectUri}`;
    window.location.href = loginUrl;
  }, []);

  const logout = useCallback(() => {
    setTokens(null);
    const redirectUri = encodeURIComponent(window.location.origin);
    window.location.href =
      `${COGNITO_DOMAIN}/logout?client_id=${CLIENT_ID}&logout_uri=${redirectUri}`;
  }, []);

  const getAccessToken = useCallback(async (): Promise<string> => {
    if (!tokens) throw new Error('Not authenticated');

    // Check if access token expired (check exp claim)
    if (isExpired(tokens.accessToken)) {
      const refreshed = await refreshTokens(tokens.refreshToken);
      setTokens(refreshed);
      return refreshed.accessToken;
    }

    return tokens.accessToken;
  }, [tokens]);

  return (
    <AuthContext.Provider value={{
      user: tokens ? parseJwt(tokens.idToken) : null,
      isAuthenticated: !!tokens,
      login, logout, getAccessToken
    }}>
      {children}
    </AuthContext.Provider>
  );
}
```

---

## 4. API Client — Tenant + Auth Headers

```typescript
// src/api/apiClient.ts

import axios, { AxiosInstance } from 'axios';

let authContext: { getAccessToken: () => Promise<string> } | null = null;
let tenantId: string | null = null;

export function initApiClient(auth: typeof authContext, tid: string) {
  authContext = auth;
  tenantId = tid;
}

const apiClient: AxiosInstance = axios.create({
  baseURL: '/api',
  timeout: 30_000,
});

// Request interceptor: attach auth token
// Note: X-Tenant-ID is derived server-side from the Host header (subdomain)
// We don't send it manually — the gateway already knows from the subdomain.
apiClient.interceptors.request.use(async config => {
  if (authContext) {
    const token = await authContext.getAccessToken();
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor: handle 401 → redirect to login
apiClient.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      window.location.href = '/login';
    }
    if (error.response?.status === 403
        && error.response.data?.error === 'Tenant subscription inactive') {
      window.location.href = '/subscription-expired';
    }
    return Promise.reject(error);
  }
);

export default apiClient;
```

---

## 5. Feature Flags — Tenant Plan Gating

```typescript
// src/tenant/useFeature.ts

const PLAN_FEATURES: Record<string, string[]> = {
  FREE:       ['basic_reports', 'up_to_5_users'],
  PRO:        ['basic_reports', 'advanced_reports', 'up_to_50_users', 'api_access'],
  ENTERPRISE: ['basic_reports', 'advanced_reports', 'unlimited_users',
               'api_access', 'custom_branding', 'sso', 'audit_logs'],
};

export function useFeature(featureKey: string): boolean {
  const tenant = useTenant();
  return tenant.features.includes(featureKey);
}

// Usage in components:
function ReportsPage() {
  const hasAdvancedReports = useFeature('advanced_reports');

  return (
    <div>
      <BasicReports />
      {hasAdvancedReports ? (
        <AdvancedReports />
      ) : (
        <UpgradeBanner feature="Advanced Reports" requiredPlan="PRO" />
      )}
    </div>
  );
}
```

---

## 6. App Entry Point — Provider Composition

```typescript
// src/App.tsx

export default function App() {
  return (
    <Suspense fallback={<FullPageLoader />}>
      <TenantProvider>
        <TenantThemeProvider>
          <AuthProvider>
            <QueryClientProvider client={queryClient}>
              <Router>
                <Routes>
                  <Route path="/callback" element={<CallbackPage />} />
                  <Route path="/login"    element={<LoginPage />} />
                  <Route path="/subscription-expired"
                         element={<SubscriptionExpiredPage />} />
                  <Route element={<PrivateRoute />}>
                    <Route path="/"         element={<DashboardPage />} />
                    <Route path="/orders/*" element={<OrdersRoutes />} />
                    <Route path="/settings" element={<SettingsPage />} />
                    {/* Feature-gated route */}
                    <Route path="/reports"
                           element={<FeatureRoute feature="basic_reports">
                                      <ReportsPage />
                                    </FeatureRoute>} />
                  </Route>
                </Routes>
              </Router>
            </QueryClientProvider>
          </AuthProvider>
        </TenantThemeProvider>
      </TenantProvider>
    </Suspense>
  );
}
```

---

## 7. Provider Admin Dashboard

The provider's admin portal runs on `admin.yourdomain.com` — separate from tenant apps.

```typescript
// src/pages/admin/TenantManagementPage.tsx
// Provider staff manages all tenants from here

function TenantManagementPage() {
  const { data: tenants } = useQuery({
    queryKey: ['admin', 'tenants'],
    queryFn: () => adminApiClient.get('/internal/tenants').then(r => r.data),
  });

  return (
    <AdminLayout>
      <Stack direction="row" justifyContent="space-between">
        <Typography variant="h4">Tenant Management</Typography>
        <Button onClick={() => setOnboardDialogOpen(true)}>
          + Onboard Tenant
        </Button>
      </Stack>

      <TenantTable
        tenants={tenants}
        onSuspend={id => suspendMutation.mutate(id)}
        onActivate={id => activateMutation.mutate(id)}
        onDelete={id => setDeleteConfirm(id)}
      />

      <TenantOnboardingDialog
        open={onboardDialogOpen}
        onSubmit={handleOnboard}
        onClose={() => setOnboardDialogOpen(false)}
      />
    </AdminLayout>
  );
}
```

---

## 8. Tenant Branding — Logo & Colors in Header

```typescript
function AppHeader() {
  const tenant = useTenant();

  return (
    <AppBar sx={{ backgroundColor: tenant.primaryColor }}>
      <Toolbar>
        <Box
          component="img"
          src={tenant.logoUrl}
          alt={tenant.displayName}
          sx={{ height: 40, mr: 2 }}
        />
        <Typography variant="h6" sx={{ flexGrow: 1 }}>
          {tenant.displayName}
        </Typography>
        <UserMenu />
      </Toolbar>
    </AppBar>
  );
}
```

---

## Build & Deployment

```bash
# Single build — works for ALL tenants
npm run build

# Deploy to S3 (same files for all subdomains)
aws s3 sync dist/ s3://saas-frontend-bucket/ --delete

# CloudFront invalidation
aws cloudfront create-invalidation \
  --distribution-id EDFDVBD6EXAMPLE \
  --paths "/*"
```

CloudFront serves the same `index.html` to `acmecorp.app.yourdomain.com` and `globex.app.yourdomain.com`. React's `TenantProvider` reads the subdomain at runtime and loads the right config.
