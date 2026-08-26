# Authentication & Authorization — AWS Cognito + Spring Security

## Concept: SAP XSUAA → AWS Cognito

SAP BTP uses XSUAA (Extended Services for User Account and Authentication) for multitenant auth.

**AWS equivalent:** AWS Cognito with tenant-aware User Pools + Spring Security OAuth2 Resource Server.

---

## Two Strategies for Multitenant Cognito

### Strategy A: Shared User Pool (Recommended for < 10,000 tenants)

```
Single Cognito User Pool
   ├── User: alice@acmecorp.com  { custom:tenantId: "acmecorp",  custom:role: "ADMIN" }
   ├── User: bob@acmecorp.com    { custom:tenantId: "acmecorp",  custom:role: "USER"  }
   ├── User: charlie@globex.com  { custom:tenantId: "globex",    custom:role: "ADMIN" }
   └── User: diana@globex.com    { custom:tenantId: "globex",    custom:role: "USER"  }
```

- All tenants share one User Pool.
- `custom:tenantId` attribute is set on each user during registration.
- JWT contains `custom:tenantId` — used for tenant routing and data isolation.
- **Cheaper** (one pool) and **simpler** operations.

### Strategy B: Pool per Tenant (For high-isolation requirements)

```
User Pool: acmecorp-pool  → App Client: acmecorp-web
User Pool: globex-pool    → App Client: globex-web
User Pool: initech-pool   → App Client: initech-web
```

- Created programmatically during tenant onboarding.
- Higher cost but complete auth isolation.
- Required when tenants have custom IdP (SAML/OIDC federation requirements).

**Default recommendation: Strategy A** — Strategy B only if tenant contracts demand auth isolation.

---

## JWT Token Structure (Strategy A)

```json
{
  "sub": "user-uuid-123",
  "email": "alice@acmecorp.com",
  "cognito:username": "alice@acmecorp.com",
  "custom:tenantId": "acmecorp",
  "custom:role": "ADMIN",
  "cognito:groups": ["acmecorp-admins"],
  "iss": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_POOLID",
  "aud": "CLIENT_ID",
  "exp": 1700000000,
  "iat": 1699996400
}
```

---

## Cognito Setup (Terraform/CDK outline)

```typescript
// AWS CDK — shared user pool with tenant attributes
const userPool = new cognito.UserPool(this, 'SaasUserPool', {
  userPoolName: 'saas-platform-pool',
  selfSignUpEnabled: false,  // invitation-only (provider controls onboarding)
  signInAliases: { email: true },
  customAttributes: {
    'tenantId': new cognito.StringAttribute({ mutable: false }),
    'role':     new cognito.StringAttribute({ mutable: true }),
  },
  passwordPolicy: {
    minLength: 12,
    requireUppercase: true,
    requireDigits: true,
    requireSymbols: true,
  },
  accountRecovery: cognito.AccountRecovery.EMAIL_ONLY,
});

const userPoolClient = userPool.addClient('WebClient', {
  authFlows: {
    userPassword: false,       // no legacy auth
    userSrp: true,             // SRP (secure)
    custom: false,
  },
  oAuth: {
    flows: { authorizationCodeGrant: true },
    scopes: [cognito.OAuthScope.EMAIL, cognito.OAuthScope.OPENID,
             cognito.OAuthScope.PROFILE],
    callbackUrls: ['https://*.app.yourdomain.com/callback'],
  },
  accessTokenValidity: Duration.minutes(60),
  refreshTokenValidity: Duration.days(30),
  preventUserExistenceErrors: true,
});
```

---

## Spring Boot — OAuth2 Resource Server Configuration

```java
@Configuration
@EnableWebSecurity
@EnableMethodSecurity
public class SecurityConfig {

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        http
            .sessionManagement(s -> s.sessionCreationPolicy(STATELESS))
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/actuator/health").permitAll()
                .requestMatchers("/api/admin/**").hasRole("ADMIN")
                .anyRequest().authenticated()
            )
            .oauth2ResourceServer(oauth2 -> oauth2
                .jwt(jwt -> jwt
                    .jwtAuthenticationConverter(tenantAwareJwtConverter())
                )
            );
        return http.build();
    }

    @Bean
    public JwtDecoder jwtDecoder() {
        // Cognito JWKS endpoint for token verification
        String jwksUri = "https://cognito-idp.us-east-1.amazonaws.com/"
                       + "${cognito.user-pool-id}/.well-known/jwks.json";
        return NimbusJwtDecoder.withJwkSetUri(jwksUri).build();
    }

    @Bean
    public JwtAuthenticationConverter tenantAwareJwtConverter() {
        JwtAuthenticationConverter converter = new JwtAuthenticationConverter();
        converter.setJwtGrantedAuthoritiesConverter(jwt -> {
            // Extract roles from Cognito groups claim
            List<String> groups = jwt.getClaimAsStringList("cognito:groups");
            if (groups == null) groups = List.of();
            return groups.stream()
                .map(g -> new SimpleGrantedAuthority("ROLE_" + g.toUpperCase()))
                .collect(Collectors.toList());
        });
        return converter;
    }
}
```

---

## Tenant-Aware Authentication — Custom JWT Filter

After Spring Security validates the JWT, extract tenant context:

```java
@Component
@Order(2)  // runs after TenantContextFilter
public class JwtTenantValidationFilter extends OncePerRequestFilter {

    @Override
    protected void doFilterInternal(HttpServletRequest request,
                                    HttpServletResponse response,
                                    FilterChain chain) throws ServletException, IOException {

        Authentication auth = SecurityContextHolder.getContext().getAuthentication();

        if (auth instanceof JwtAuthenticationToken jwtAuth) {
            Jwt jwt = jwtAuth.getToken();
            String jwtTenantId = jwt.getClaimAsString("custom:tenantId");
            String headerTenantId = TenantContextHolder.getTenantId();

            // Cross-tenant access check: JWT tenant must match request tenant
            if (!headerTenantId.equals(jwtTenantId)) {
                response.sendError(HttpServletResponse.SC_FORBIDDEN,
                    "Cross-tenant access denied");
                return;
            }
        }
        chain.doFilter(request, response);
    }
}
```

---

## Authorization — Method-Level Security

```java
@Service
public class OrderService {

    // ROLE_ADMIN from Cognito group
    @PreAuthorize("hasRole('ADMIN')")
    public void deleteOrder(Long orderId) { ... }

    // Any authenticated user
    @PreAuthorize("isAuthenticated()")
    public List<Order> getMyOrders() {
        // tenantId comes from TenantContextHolder — already verified
        return orderRepository.findAll();
    }
}
```

---

## Tenant User Management (via Admin API)

When a tenant admin invites a new user:

```java
@Service
public class TenantUserService {

    private final CognitoIdentityProviderClient cognitoClient;

    public void inviteUser(String email, String tenantId, String role) {
        // Create user in Cognito
        cognitoClient.adminCreateUser(AdminCreateUserRequest.builder()
            .userPoolId(userPoolId)
            .username(email)
            .temporaryPassword(generateTempPassword())
            .userAttributes(
                AttributeType.builder().name("email").value(email).build(),
                AttributeType.builder().name("custom:tenantId").value(tenantId).build(),
                AttributeType.builder().name("custom:role").value(role).build(),
                AttributeType.builder().name("email_verified").value("true").build()
            )
            .messageAction(MessageActionType.SUPPRESS)  // send custom email via SES
            .build());

        // Add to tenant-specific Cognito group
        cognitoClient.adminAddUserToGroup(AdminAddUserToGroupRequest.builder()
            .userPoolId(userPoolId)
            .username(email)
            .groupName(tenantId + "-" + role.toLowerCase())
            .build());

        // Send branded invitation email via SES
        emailService.sendInvitation(email, tenantId);
    }
}
```

---

## Login Flow (React → Cognito → API)

```
1. User visits https://acmecorp.app.yourdomain.com
2. React detects unauthenticated → redirect to Cognito Hosted UI
   URL: https://auth.app.yourdomain.com/login
        ?client_id=CLIENT_ID
        &response_type=code
        &redirect_uri=https://acmecorp.app.yourdomain.com/callback
        &scope=email+openid+profile

3. User authenticates in Cognito Hosted UI

4. Cognito redirects to /callback?code=AUTH_CODE

5. React exchanges code for tokens:
   POST https://auth.app.yourdomain.com/oauth2/token
   → { access_token, id_token, refresh_token }

6. React stores tokens (memory + httpOnly cookie for refresh token)

7. API calls include:
   Authorization: Bearer <access_token>
   Host: acmecorp.app.yourdomain.com  ← tenant derived from this

8. API Gateway Lambda Authorizer:
   - Validates JWT signature (Cognito JWKS)
   - Validates exp, iss, aud
   - Cross-checks JWT tenantId vs subdomain
   - Returns IAM allow policy + custom context { tenantId: "acmecorp" }
```

---

## Role Hierarchy Per Tenant

```
PLATFORM_ADMIN     → Provider staff, full system access
TENANT_ADMIN       → Tenant's admin, manages their org
TENANT_MANAGER     → Manager-level within tenant
TENANT_USER        → Regular end user within tenant
```

Cognito groups per tenant:
```
acmecorp-admin
acmecorp-manager
acmecorp-user
```
