# Where must authentication and authorization checks happen?

> **Interview priority:** SHOULD KNOW

## Question

Where must authentication and authorization checks happen in a React application?

## Beginner Lens

Watch the security boundary: hiding a route or button in React prevents the user from seeing it, but doesn't stop them from calling the API directly. Authentication (who are you?) and authorization (what can you do?) must ALWAYS be enforced on the server. Client-side checks are only for UX, not security.

## Detailed Explanation

**HOW TO SAY IT (spoken to interviewer):**

> "This is the most critical security mistake I see in React apps — treating client-side route guards as actual security. The reality is that React runs in the user's browser, so they can modify any code, bypass any check, and call any API directly. Real security MUST happen on the server. Client-side auth is purely for user experience — showing the right UI, hiding buttons, redirecting logged-out users. Let me show exactly what breaks when you rely on client-side checks..."

```
REAL APP: Admin Dashboard — THE CLASSIC SECURITY BUG
─────────────────────────────────────────────────────────────────

INSECURE CODE (client-side only):
────────────────────────────────────────────────────────────────

// Frontend route guard
function ProtectedRoute({ children, requiredRole }) {
  const { user } = useAuth();
  
  if (!user) {
    return <Navigate to="/login" />;
  }
  
  if (user.role !== requiredRole) {
    return <div>Access Denied</div>;  // ← NOT REAL SECURITY
  }
  
  return children;
}

// Admin page
function AdminDashboard() {
  const [users, setUsers] = useState([]);
  
  useEffect(() => {
    fetch('/api/admin/users')  // ← NO SERVER-SIDE CHECK
      .then(r => r.json())
      .then(setUsers);
  }, []);
  
  const deleteUser = (userId) => {
    fetch(`/api/admin/users/${userId}`, { method: 'DELETE' })  // ← EXPOSED
      .then(() => setUsers(prev => prev.filter(u => u.id !== userId)));
  };
  
  return (
    <div>
      <h1>Admin Panel</h1>
      {users.map(user => (
        <div key={user.id}>
          {user.email}
          <button onClick={() => deleteUser(user.id)}>Delete</button>
        </div>
      ))}
    </div>
  );
}

// App routing
function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/admin"
        element={
          <ProtectedRoute requiredRole="admin">
            <AdminDashboard />
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}

THE VULNERABILITY:
─────────────────────────────────────────────────────────────────

Attack scenario (any user can do this):

1. Regular user logs in (role: "user", not "admin")
2. Opens browser DevTools → Console
3. Types:
   fetch('/api/admin/users').then(r => r.json()).then(console.log)
   
   → API responds with ALL users ❌
   (because server doesn't check auth)

4. Types:
   fetch('/api/admin/users/123', { method: 'DELETE' })
   
   → User 123 DELETED ❌
   (regular user just deleted an account)

5. OR: Manually navigate to /admin by typing URL
   → ProtectedRoute blocks it (shows "Access Denied")
   → But attacker doesn't need the UI, they called the API directly ✅

WHAT WENT WRONG:
  - Frontend checks user.role === 'admin' ✅ (good UX)
  - Backend API has NO checks ❌ (critical vulnerability)
  - Anyone who knows the API endpoint can call it
  - Client-side code is PUBLIC (view-source://, React DevTools)
```

```
VISUAL DIAGRAM — CLIENT VS SERVER AUTH:
─────────────────────────────────────────────────────────────────

CLIENT-SIDE ONLY (INSECURE):
────────────────────────────────────────────────────────────────

Browser (user's device — attacker controls this)
  │
  ├─ React App
  │  ├─ ProtectedRoute checks user.role ← can be bypassed
  │  └─ if (user.role === 'admin') show button ← can be modified
  │
  ├─ DevTools Console
  │  └─ fetch('/api/admin/users') ← DIRECT API CALL
  │
  ▼
Server (NO checks)
  ├─ GET /api/admin/users
  │  └─ return all users ❌ NO AUTH CHECK
  ├─ DELETE /api/admin/users/:id
  │  └─ delete user ❌ NO AUTH CHECK

Result: Attacker bypasses React entirely, calls API directly ❌


CORRECT (DEFENSE IN DEPTH):
────────────────────────────────────────────────────────────────

Browser (user's device)
  │
  ├─ React App
  │  ├─ ProtectedRoute checks user.role ✅ (UX only)
  │  └─ Hides admin button for non-admins ✅ (UX only)
  │
  ├─ DevTools Console
  │  └─ fetch('/api/admin/users', { 
  │       headers: { Authorization: 'Bearer <token>' }
  │     })
  │
  ▼
Server (ENFORCES security)
  ├─ Middleware: Verify JWT token
  │  ├─ No token? → 401 Unauthorized ✅
  │  └─ Invalid token? → 401 Unauthorized ✅
  │
  ├─ Middleware: Check user role
  │  ├─ user.role !== 'admin'? → 403 Forbidden ✅
  │  └─ user.role === 'admin'? → Continue ✅
  │
  ├─ GET /api/admin/users
  │  └─ return all users ✅ (only if middleware passed)
  │
  └─ DELETE /api/admin/users/:id
     └─ delete user ✅ (only if admin)

Result: Attacker gets 401/403, cannot access data ✅
```

```
SOLUTION 1: SERVER-SIDE AUTH MIDDLEWARE
─────────────────────────────────────────────────────────────────

// Express.js example

// Authentication middleware (verify JWT)
const authenticate = async (req, res, next) => {
  const token = req.headers.authorization?.split(' ')[1];  // "Bearer <token>"
  
  if (!token) {
    return res.status(401).json({ error: 'Authentication required' });
  }
  
  try {
    const decoded = jwt.verify(token, process.env.JWT_SECRET);
    const user = await User.findById(decoded.userId);
    
    if (!user) {
      return res.status(401).json({ error: 'User not found' });
    }
    
    req.user = user;  // attach to request
    next();
  } catch (err) {
    return res.status(401).json({ error: 'Invalid token' });
  }
};

// Authorization middleware (check role)
const requireRole = (role) => {
  return (req, res, next) => {
    if (req.user.role !== role) {
      return res.status(403).json({ error: 'Insufficient permissions' });
    }
    next();
  };
};

// Protected routes
app.get('/api/admin/users', authenticate, requireRole('admin'), async (req, res) => {
  const users = await User.find();
  res.json(users);
});

app.delete('/api/admin/users/:id', authenticate, requireRole('admin'), async (req, res) => {
  await User.findByIdAndDelete(req.params.id);
  res.json({ success: true });
});

NOW:
  - Regular user calls /api/admin/users
  - authenticate passes ✅ (valid user)
  - requireRole('admin') fails ❌ (user.role = 'user')
  - Returns 403 Forbidden ✅
  - User NOT deleted, data NOT leaked ✅
```

```
SOLUTION 2: CLIENT-SIDE AUTH (FOR UX ONLY)
─────────────────────────────────────────────────────────────────

// React route guard (UX layer, NOT security)

function ProtectedRoute({ children, requiredRole }) {
  const { user, isLoading } = useAuth();
  
  if (isLoading) {
    return <Spinner />;
  }
  
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  
  if (requiredRole && user.role !== requiredRole) {
    return <Navigate to="/unauthorized" replace />;
  }
  
  return children;
}

// Conditional rendering based on permissions
function AdminDashboard() {
  const { user } = useAuth();
  const [users, setUsers] = useState([]);
  
  useEffect(() => {
    // API will enforce auth, but fetch anyway
    fetch('/api/admin/users', {
      headers: { Authorization: `Bearer ${user.token}` }
    })
      .then(r => {
        if (r.status === 403) {
          throw new Error('Unauthorized');
        }
        return r.json();
      })
      .then(setUsers)
      .catch(err => {
        console.error('Access denied:', err);
        // Redirect or show error
      });
  }, []);
  
  const deleteUser = async (userId) => {
    try {
      const res = await fetch(`/api/admin/users/${userId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${user.token}` }
      });
      
      if (res.status === 403) {
        alert('You do not have permission to delete users');
        return;
      }
      
      setUsers(prev => prev.filter(u => u.id !== userId));
    } catch (err) {
      console.error('Delete failed:', err);
    }
  };
  
  return (
    <div>
      <h1>Admin Panel</h1>
      {users.map(user => (
        <div key={user.id}>
          {user.email}
          <button onClick={() => deleteUser(user.id)}>Delete</button>
        </div>
      ))}
    </div>
  );
}

CLIENT-SIDE CHECKS ARE FOR:
  ✅ Showing/hiding UI elements
  ✅ Redirecting users before they waste time
  ✅ Improving user experience
  ✅ Reducing unnecessary API calls

CLIENT-SIDE CHECKS ARE NOT FOR:
  ❌ Security (easily bypassed)
  ❌ Preventing unauthorized actions (API must do this)
  ❌ Protecting sensitive data (data lives on server)
```

```
SOLUTION 3: ROLE-BASED UI RENDERING
─────────────────────────────────────────────────────────────────

// Show different UI based on user role (UX convenience)

function usePermissions() {
  const { user } = useAuth();
  
  return {
    canViewAdminPanel: user?.role === 'admin',
    canDeleteUsers: user?.role === 'admin',
    canEditPosts: ['admin', 'moderator'].includes(user?.role),
    canViewAnalytics: ['admin', 'analyst'].includes(user?.role)
  };
}

function Dashboard() {
  const permissions = usePermissions();
  
  return (
    <div>
      <h1>Dashboard</h1>
      
      {permissions.canViewAnalytics && (
        <AnalyticsPanel />  {/* shown to admin and analyst */}
      )}
      
      {permissions.canViewAdminPanel && (
        <Link to="/admin">Admin Panel</Link>  {/* shown to admin only */}
      )}
    </div>
  );
}

function PostCard({ post }) {
  const permissions = usePermissions();
  
  return (
    <div>
      <h2>{post.title}</h2>
      <p>{post.content}</p>
      
      {permissions.canEditPosts && (
        <button onClick={() => editPost(post.id)}>Edit</button>
      )}
      
      {/* Edit button hidden for regular users, shown for admin/moderator */}
      {/* BUT: Server still checks permission when API is called */}
    </div>
  );
}
```

```
REAL PRODUCTION BUG — RESOURCE-LEVEL AUTHORIZATION:
─────────────────────────────────────────────────────────────────

// User can edit THEIR OWN posts, but not others'

CLIENT (checks ownership):
────────────────────────────────────────────────────────────────

function EditPostButton({ post }) {
  const { user } = useAuth();
  
  // Only show edit button if user owns the post
  if (post.authorId !== user.id) {
    return null;  // ← UX check, NOT security
  }
  
  return <button onClick={() => editPost(post.id)}>Edit</button>;
}

SERVER (MUST also check ownership):
────────────────────────────────────────────────────────────────

app.put('/api/posts/:id', authenticate, async (req, res) => {
  const post = await Post.findById(req.params.id);
  
  if (!post) {
    return res.status(404).json({ error: 'Post not found' });
  }
  
  // CRITICAL: Check if user owns this post
  if (post.authorId.toString() !== req.user.id.toString()) {
    return res.status(403).json({ error: 'You can only edit your own posts' });
  }
  
  post.title = req.body.title;
  post.content = req.body.content;
  await post.save();
  
  res.json(post);
});

THE BUG (if server doesn't check):
  - User A sees post by User B
  - Edit button hidden (correct UX) ✅
  - User A opens DevTools:
    fetch('/api/posts/123', {
      method: 'PUT',
      body: JSON.stringify({ content: 'HACKED' })
    })
  - If server doesn't check authorId:
    → User A edits User B's post ❌

THE FIX:
  - Server checks post.authorId === req.user.id ✅
  - Returns 403 if mismatch ✅
  - User A cannot edit User B's post ✅
```

```
AUTHENTICATION vs AUTHORIZATION:
─────────────────────────────────────────────────────────────────

AUTHENTICATION (who are you?):
  - Login with username/password → JWT token
  - Token proves identity
  - Every API request includes token
  - Server verifies token signature
  - Example: "You are user ID 123"

AUTHORIZATION (what can you do?):
  - User has role: 'admin', 'moderator', 'user'
  - User has permissions: 'posts:edit', 'users:delete'
  - Server checks: does this user have permission for this action?
  - Example: "User 123 is NOT an admin, cannot delete users"

BOTH MUST BE ENFORCED ON SERVER:
  1. Authenticate: Is this token valid? (401 if not)
  2. Authorize: Does this user have permission? (403 if not)
```

```
COMMON PATTERNS:
─────────────────────────────────────────────────────────────────

1. JWT IN HTTP-ONLY COOKIE (more secure than localStorage)
────────────────────────────────────────────────────────────────

// Server sets cookie
res.cookie('token', jwt.sign({ userId }), {
  httpOnly: true,  // ← JavaScript cannot read it (XSS protection)
  secure: true,    // ← only sent over HTTPS
  sameSite: 'strict'  // ← CSRF protection
});

// Client makes request (cookie sent automatically)
fetch('/api/admin/users', {
  credentials: 'include'  // ← send cookies
});

// Server reads cookie
app.use(cookieParser());
const token = req.cookies.token;


2. REFRESH TOKEN PATTERN (long-lived sessions)
────────────────────────────────────────────────────────────────

// Short-lived access token (15 min) + long-lived refresh token (7 days)

Client:
  - Stores access token in memory (NOT localStorage)
  - Stores refresh token in HTTP-only cookie
  - When access token expires (401):
    → Call /api/refresh with refresh token
    → Get new access token
    → Retry original request

Server:
  - /api/refresh validates refresh token
  - Issues new access token
  - If refresh token expires: user must log in again


3. PERMISSION-BASED (fine-grained control)
────────────────────────────────────────────────────────────────

// Instead of roles, check specific permissions

const requirePermission = (permission) => {
  return (req, res, next) => {
    if (!req.user.permissions.includes(permission)) {
      return res.status(403).json({ error: 'Missing permission' });
    }
    next();
  };
};

app.delete('/api/users/:id', 
  authenticate, 
  requirePermission('users:delete'),  // ← specific permission
  async (req, res) => { /* ... */ }
);

User object:
{
  id: 123,
  role: 'moderator',
  permissions: ['posts:edit', 'posts:delete', 'comments:moderate']
}
```

```
DEBUGGING CHECKLIST — "Users accessing unauthorized data"
─────────────────────────────────────────────────────────────────

✅ Check if API has authentication middleware
   - Is Authorization header required?
   - What happens if you call API without token?
   → Should return 401 ✅

✅ Check if API has authorization middleware
   - Does it check user role/permissions?
   - What happens if regular user calls admin endpoint?
   → Should return 403 ✅

✅ Check resource-level authorization
   - Can user edit another user's post?
   - Does API check post.authorId === req.user.id?
   → Should return 403 if mismatch ✅

✅ Test in Postman/curl (bypass React)
   - Call API directly with manipulated token
   - Try accessing admin endpoints as regular user
   → Should fail ✅

✅ Check token storage
   - Stored in localStorage? → Vulnerable to XSS
   - Consider HTTP-only cookies instead

✅ Check for client-side only checks
   - If you remove ProtectedRoute, can you access data?
   → Server should still block it ✅
```

> "The mental model: React is a public park. Anyone can walk in, look around, read the code, modify it. You can put up signs saying 'Admins Only' (route guards), but that's just a polite suggestion. Real security is a locked vault on the server. The key (JWT token) proves who you are, and the vault checks if you're allowed in. Never trust the client, always verify on the server."

**INTERVIEW FOLLOW-UP QUESTIONS:**

**Q: "Is it okay to store roles/permissions in JWT token?"**

> "Yes for roles (low cardinality, rarely change). But verify them on the server too — don't trust the token blindly. For fine-grained permissions that change often, fetch from database. Tokens can become stale if permissions are revoked."

**Q: "How do you handle authorization in a microservices architecture?"**

> "Centralized auth service issues JWTs. Each microservice validates the JWT signature independently (no network call needed). Services can also call auth service to check permissions if not in token. Or use API gateway to enforce auth before routing to services."

**Q: "What about OAuth/social login?"**

> "OAuth handles authentication (Google proves user identity). Your server still handles authorization (what can this Google user do in your app?). Exchange OAuth token for your own JWT, store user ID and role in your database."
