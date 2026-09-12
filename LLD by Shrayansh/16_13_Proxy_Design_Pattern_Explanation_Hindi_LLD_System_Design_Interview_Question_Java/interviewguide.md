# Interview Guide: Proxy Design Pattern

## 🗣️ The Interview Scenario

> "You have an `EmployeeDAO` interface with `create`, `delete`, and `get` operations backed by a real database implementation. Now, the business wants only ADMIN users to be able to create or delete employee records — regular users should only be able to read. You cannot modify the existing `EmployeeDAO` implementation class (it's used elsewhere and is considered stable/frozen). How do you add this access-control rule without touching the existing implementation or the callers that already depend on the `EmployeeDAO` interface?"

This is the single most common way Proxy gets tested: framed as an "add a cross-cutting concern (access control, caching, logging) without modifying existing, working code" problem. The trap is that many candidates instinctively reach for inheritance ("I'll subclass `EmployeeDAOImpl` and override the methods") — which is fragile and often impossible if the class is final or if you need composition-based flexibility. The Proxy pattern is the composition-based answer the interviewer is fishing for.

## 🏗️ Architect's Explanation (For a New Developer)

You've already used the Proxy pattern today, even if you've never written one yourself. When your office laptop tries to reach a blocked website, your request doesn't go straight to the internet — it first passes through a **proxy server**, which checks "is this destination on the blocklist?" *before* deciding whether to actually forward your request to the real destination. If it's blocked, the proxy server itself responds with "access denied," and your request never touches the real server at all. If it's allowed, the proxy quietly forwards your request through and relays the real server's response back to you, and you never even notice the proxy was involved.

That's the whole idea: **a Proxy is a stand-in object that sits between a client and the real object, implementing the exact same interface as the real object, so the client can't tell the difference — but the proxy gets a chance to intercept every call, either blocking it, modifying it, or doing extra work before and/or after forwarding it to the real object.** The client only ever holds a reference typed to the shared interface; whether that reference happens to be pointing at the real implementation or a proxy wrapping the real implementation is invisible to the client's code.

The three most common *reasons* to insert a proxy — call these out explicitly in an interview because they're literally the pattern's use-case checklist:
1. **Access control / restriction** — the proxy checks permissions before allowing a call through (our `EmployeeDAO` example).
2. **Caching** — the proxy checks "do I already have this answer cached?" before bothering the real (expensive) object at all — e.g., a proxy server that returns a cached page instead of hitting the real internet server again.
3. **Pre-processing / post-processing** — the proxy does something before the real call (e.g., logging, request enrichment) and/or something after the real call returns (e.g., emitting an event so other systems get notified that "something changed").

## 📊 Visualize It

Class structure:

```
                     +------------------------+
                     |     EmployeeDAO          |   <<interface>>
                     +------------------------+
                     | +create(...)             |
                     | +delete(...)              |
                     | +get(id)                  |
                     +------------------------+
                            ▲            ▲
                  implements|            |implements
                            |            |
              +----------------------+  +--------------------------+
              |  EmployeeDAOImpl      |  |   EmployeeDAOProxy         |
              +----------------------+  +--------------------------+
              | +create(...) { ...DB...} | - EmployeeDAOImpl realDao  |  <-- HAS-A the real object
              | +delete(...) { ...DB...} | +create(...) { checkAdmin(); realDao.create(...); } |
              | +get(id) { ...DB...}      | +delete(...) { checkAdmin(); realDao.delete(...); } |
              +----------------------+  | +get(id) { realDao.get(id); }  (no restriction) |
                            ▲             +--------------------------+
                            |  wraps/delegates to
                            +---------------------------------------------+
                                                                            |
                     +------------------------+                            |
                     |        Client            |----------(only ever talks to `EmployeeDAO` interface)---+
                     +------------------------+
```

Runtime call flow — request interception:

```
 Client holds:  EmployeeDAO dao = new EmployeeDAOProxy(currentUser);
 Client calls:  dao.delete(employeeId)
        |
        v
 EmployeeDAOProxy.delete(employeeId)
        |
        v
 if (currentUser.role != ADMIN)  ---->  throw AccessDeniedException   (real object NEVER touched)
        |  (else, role == ADMIN)
        v
 realDao.delete(employeeId)   <-- only now does the REAL implementation get called
        |
        v
 (delete actually happens in the DB)
```

## 🔧 Deep Dive: How It Actually Works

### The interface and the real implementation (unchanged, frozen code)

```java
interface EmployeeDAO {
    void create(Employee e);
    void delete(String employeeId);
    Employee get(String employeeId);
}

class EmployeeDAOImpl implements EmployeeDAO {
    public void create(Employee e) {
        // reads employee object, creates a new row in the DB
    }
    public void delete(String employeeId) {
        // reads the id, deletes the corresponding row
    }
    public Employee get(String employeeId) {
        // fetches from DB using id, returns the Employee
    }
}
```

This class is explicitly treated as untouchable — the transcript's whole premise is "I want to add a rule without editing this."

### The proxy — same interface, extra logic wrapped around delegation

```java
class EmployeeDAOProxy implements EmployeeDAO {
    private EmployeeDAOImpl realDao;   // composition: proxy HOLDS a reference to the real object
    private String clientRole;          // e.g., "ADMIN" or "USER"

    EmployeeDAOProxy(String clientRole) {
        this.realDao = new EmployeeDAOImpl();
        this.clientRole = clientRole;
    }

    @Override
    public void create(Employee e) {
        if (!clientRole.equals("ADMIN")) {
            throw new AccessDeniedException("Only ADMIN can create employees");
        }
        realDao.create(e);   // access check passed -- now forward to the real object
    }

    @Override
    public void delete(String employeeId) {
        if (!clientRole.equals("ADMIN")) {
            throw new AccessDeniedException("Only ADMIN can delete employees");
        }
        realDao.delete(employeeId);
    }

    @Override
    public Employee get(String employeeId) {
        // No restriction here — both ADMIN and regular USER are allowed to read.
        return realDao.get(employeeId);
    }
}
```

### The client — completely unaware a proxy is involved

```java
EmployeeDAO dao = new EmployeeDAOProxy(currentUserRole);
dao.create(newEmployee);   // if currentUserRole != "ADMIN", this throws before ever reaching the DB
dao.get(employeeId);        // works regardless of role
```

The client's code is written entirely against the `EmployeeDAO` interface. Whether `dao` happens to be an `EmployeeDAOImpl` or an `EmployeeDAOProxy` is an implementation detail decided wherever the object is constructed (often in a factory or a dependency-injection configuration) — the calling code never branches on it.

### Why this is composition, not inheritance

The proxy does **not** extend `EmployeeDAOImpl` — it implements the same `EmployeeDAO` interface and **holds a reference** to a real `EmployeeDAOImpl` instance internally. This is a deliberate structural choice: composition means the proxy fully controls whether, when, and how the real object's method actually gets invoked (it can skip calling it entirely, as in the access-denied case), whereas inheriting and overriding would still expose the base class's other behaviors and would tie the proxy's lifecycle to the real class's constructor semantics.

### The three motivating use cases, elaborated

1. **Access restriction** (built above) — the proxy is the single centralized place where "who can do what" is decided. If tomorrow the business adds a third role ("MANAGER can create but not delete"), you change exactly one class (`EmployeeDAOProxy`) — `EmployeeDAOImpl` and every existing caller remain untouched.

2. **Caching** — a `CachingProxy` implementing the same interface would check an internal cache before delegating:
   ```java
   public Employee get(String employeeId) {
       if (cache.containsKey(employeeId)) return cache.get(employeeId);   // never touches realDao
       Employee e = realDao.get(employeeId);
       cache.put(employeeId, e);
       return e;
   }
   ```
   This mirrors the internet-proxy-server analogy exactly: "does the proxy already have this data cached? If yes, don't even bother the real server."

3. **Pre-processing / post-processing** — e.g., logging before a call, or firing a "something changed" notification/event after a call completes, so that other interested systems can react (a classic use case the transcript ties directly to the Observer-style "notify all listeners that something changed" need). The proxy is the natural, centralized place to hook this in without scattering logging/eventing calls across every caller.

### Real-world instances of this exact pattern

- **Browser/network proxy servers** — exactly the access-control and caching motivating example: your request is intercepted, checked against a blocklist, potentially served from cache, and only forwarded to the real destination if none of that short-circuits it.
- **Spring Framework beans** — the transcript explicitly calls this out: whenever you use Spring's `@Transactional`, `@Cacheable`, or AOP-based annotations, Spring internally wraps your bean in a dynamically generated **proxy** object. Your code calls a method on what looks like your own bean, but it's actually going through a proxy first, which handles the transaction boundary or caching logic before delegating to your actual bean instance. This is precisely why proxy-based Spring features sometimes surprise developers (e.g., "why didn't my `@Transactional` method work when called from within the same class?") — self-invocation bypasses the proxy entirely, since the call never goes through the proxy object when it's an internal `this.method()` call.

### Chaining proxies (an advanced but important nuance)

The transcript raises a subtle but important point: a proxy can itself be *unaware* that the object it's delegating to is yet another proxy, rather than the real object. As long as every layer honors the same interface, you can chain: Client → Proxy A → Proxy B → RealObject, and each layer only needs to know about the layer directly beneath it, not the whole chain. Each layer can add its own concern (one does access-control, another does caching, another does logging), and none of them need to coordinate with each other directly — the interface is the only contract that matters.

## 🔥 Real Production Incident & Fix

**What broke**: A team building an internal admin tool exposed an `InventoryService` interface with a `deleteProduct(id)` method backed by a single `InventoryServiceImpl`. Early on, someone needed to add "only users with the `INVENTORY_ADMIN` role can delete products," and instead of introducing a proxy, they added the role check as an `if` statement **directly inside** `InventoryServiceImpl.deleteProduct()`, reading the current user's role from a thread-local security context.

**How the team noticed**: Months later, the team needed to reuse `InventoryServiceImpl` inside a **batch/background job** that ran as a system process with no logged-in user and no security context at all — the job's job was to auto-archive discontinued products nightly. The batch job started throwing `NullPointerException`s reading the thread-local role, because there was no interactive user session in that execution context — the access-control logic had been baked directly into the business-logic implementation, so it was now impossible to invoke the "real" delete logic in any context that didn't also carry an HTTP-request-scoped security principal. This was first noticed as repeated job-failure alerts in the nightly batch monitoring dashboard, followed by an on-call engineer tracing the stack trace back to the access-control `if` block that had no business being inside the core DAO/service implementation at all.

**Root cause**: Access control was mixed directly into the real implementation instead of being layered on top of it via a proxy. This conflated two genuinely separate concerns — "how do I delete a product from the database" and "who is allowed to trigger a delete" — into one class, making the core deletion logic impossible to reuse in any context (like a trusted background job) that legitimately shouldn't be subject to the same interactive-user access rule.

**The fix**: The team extracted the role-check into a dedicated `InventoryServiceProxy implements InventoryService`, restored `InventoryServiceImpl` to pure business logic with no security-context dependency at all, and had the HTTP-request-handling layer construct callers against the proxy (`new InventoryServiceProxy(realImpl, securityContext)`) while the batch job constructed callers directly against the real `InventoryServiceImpl` (bypassing the proxy entirely, since it doesn't need — and structurally can't satisfy — the interactive access-control rule). This mirrors exactly the guidance in this transcript: keep access-control logic in the proxy layer so the real implementation stays reusable in *any* calling context.

```
BEFORE: access-control baked into the real service           AFTER: access-control lives only in the proxy

 InventoryServiceImpl.deleteProduct(id) {                      InventoryServiceImpl.deleteProduct(id) {
   if (currentUser.role != ADMIN) throw ...;  <-- breaks         // pure business logic, no security dependency
       batch jobs with no currentUser                          }
   ...actual delete logic...                                   InventoryServiceProxy.deleteProduct(id) {
 }                                                                if (securityContext.role != ADMIN) throw ...;
                                                                   realImpl.deleteProduct(id);
   (batch job: NO valid path to call this safely)              }
                                                                 (batch job calls InventoryServiceImpl directly;
                                                                  HTTP layer calls through the proxy)
```

## ❓ Likely Interview Follow-Up Questions & Answers

1. **"Why not just add the access-control check directly inside `EmployeeDAOImpl` instead of creating a whole new Proxy class?"**
   Because that couples a cross-cutting concern (who's allowed to call this) with the core responsibility of the class (talking to the database), violating Single Responsibility — and, as the production incident shows, it makes the real implementation impossible to reuse in any context (like a trusted internal job) that shouldn't be subject to that same rule. A proxy keeps the two concerns separately swappable and testable.

2. **"How is Proxy different from the Decorator pattern — both wrap an object implementing the same interface?"**
   They share the same mechanical shape (composition + same interface + delegation), but their *intent* differs: Decorator's purpose is to **add or stack behavior/responsibilities** onto an object, typically composably with multiple decorators layered arbitrarily, while Proxy's purpose is to **control access to** an object — deciding whether, when, and how the real call happens at all (including potentially never forwarding the call, as in the access-denied case). In practice, some Proxy variants (like a logging proxy) look almost identical to a Decorator; the naming distinction is about the primary intent, not a hard structural difference.

3. **"How would you implement a caching proxy for `get(employeeId)`, and what's a risk you'd need to handle?"**
   Check an internal cache/map first; if present, return the cached value without touching `realDao`; if absent, call `realDao.get()`, store the result in the cache, then return it. The risk to call out explicitly: **cache invalidation** — if `create`/`delete`/an update happens (possibly through a *different* proxy instance, or directly against the real DAO), the cache can go stale, so you need a clear invalidation strategy (TTL, explicit eviction on writes, or routing all writes through the same proxy instance that owns the cache).

4. **"You mentioned Spring uses proxies for `@Transactional`. Why does calling an `@Transactional` method from another method in the *same* class sometimes silently not start a transaction?"**
   Because Spring's proxy sits *outside* your actual bean instance — external callers go through the proxy (which starts the transaction, then delegates), but a call from `this.someOtherMethod()` inside the same class bypasses the proxy entirely and calls the real object's method directly, so the transaction-starting logic (which lives in the proxy, not the real bean) never runs. This is a very concrete, very common real-world gotcha directly caused by the Proxy pattern's mechanics.

5. **"Can proxies be chained — e.g., an access-control proxy wrapping a caching proxy wrapping the real object? Walk through why that works."**
   Yes — as long as every layer implements the same interface, each layer only needs a reference typed to that interface, and it doesn't matter (or need to know) whether what it's holding is the real object or yet another proxy. So `AccessControlProxy` holds an `EmployeeDAO` reference that happens to be a `CachingProxy`, which itself holds an `EmployeeDAO` reference that happens to be the real `EmployeeDAOImpl` — each layer adds its own concern independently, and none of them are aware of how many layers exist beneath them.

6. **"What's the downside/cost of introducing a Proxy layer?"**
   Extra indirection: every call now passes through at least one additional method-dispatch hop, which is usually negligible in cost but can complicate debugging (stack traces get longer, and it's less immediately obvious which concrete class is actually handling a call) and can introduce subtle bugs like the Spring self-invocation issue above if developers aren't aware a proxy is involved at all.

## 🔑 Key Takeaway

A Proxy implements the exact same interface as the real object, holds a reference to it via composition (not inheritance), and sits transparently between client and real object to intercept every call for access control, caching, or pre/post-processing — the client never needs to know, or care, whether it's talking to the real thing or a proxy standing in for it.
