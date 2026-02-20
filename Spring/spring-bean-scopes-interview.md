# Spring Bean Scopes Interview Notes

## Scenario
- A controller calls a service method.
- The service uses two beans:
  - `prototype` scope
  - `request` scope
- The service method accesses beans in this order:
  1. Prototype
  2. Request
  3. Prototype (again)
- Two HTTP requests hit the application, and the same service method runs for each request.

## Core Concepts the Interviewer Is Checking

### Prototype Scope
- **Rule:** Every time Spring is asked for the bean, it creates a **new instance**.
- **Implication:** Even within the **same HTTP request**, repeated access creates multiple instances.
- **No reuse** by Spring.

### Request Scope
- **Rule:** One instance **per HTTP request**.
- **Implication:** Within a single request, the same instance is reused.
- **New request = new instance**.

## Step-by-Step Execution

### For One HTTP Request
Execution order in the service method:

1) **Prototype bean access**
- Spring creates a new prototype instance.
- Prototype count = 1

2) **Request bean access**
- First access in this request, so Spring creates a new request-scoped instance.
- Request count = 1

3) **Prototype bean access again**
- Spring is asked again for a prototype bean, so it creates a new instance.
- Prototype count = 2

**Total for ONE request:**
- Prototype instances = 2
- Request instances = 1

### For TWO HTTP Requests
Spring repeats the same behavior for each request.

- Prototype instances: 2 per request x 2 requests = **4**
- Request instances: 1 per request x 2 requests = **2**

## Final Answer
- **Prototype scope bean instances created:** 4
- **Request scope bean instances created:** 2

## Interview-Ready Explanation
"Prototype scope creates a new instance every time it is requested, so calling it twice per request creates two objects. Request scope creates one instance per HTTP request and reuses it within that request. With two requests, that results in four prototype beans and two request beans."

## Why the Prototype Bean Is Created Again
- The service method explicitly accesses the prototype bean **twice**.
- **Prototype rule:** every lookup creates a new instance.
- So Step 3 triggers a second new instance, even inside the same request.

## Memory Aid / Analogy
- **Prototype = disposable cup** (new cup every time you ask)
- **Request = water bottle per person** (same bottle within the same request)

## Common Follow-Up Questions (Practice)
- What happens if a prototype bean is injected into a singleton?
- Compare `singleton` vs `prototype` vs `request` scope behaviors.
- How bean lifecycle management differs across scopes.
- Real production use cases for each scope.

## Senior-Level Deep Dive: Singleton + Prototype Scenario

### Scenario
- A controller calls a service.
- The service is a `singleton` bean (default scope).
- The service uses a `prototype` bean.

### How Many Objects Are Created? When?

**Case A: Prototype is injected directly into the singleton**

- The singleton is created **once** at container startup (or first access if lazy).
- During singleton creation, Spring **resolves and injects** its dependencies.
- If the prototype bean is injected directly, **one prototype instance** is created at that time.
- That prototype instance is **cached inside the singleton** for the lifetime of the singleton.

**Result:**
- Singleton instances: 1
- Prototype instances: 1 (created at singleton construction time)
- Later calls to the service **reuse the same prototype instance**, which is often a bug.

**Case B: Prototype is looked up on demand**

- The singleton still has **one instance**.
- Each time the service method requests a prototype, Spring **creates a new instance**.

**Result:**
- Singleton instances: 1
- Prototype instances: 1 per lookup (can be many over time)

### Follow-Up: Why Is Prototype-in-Singleton a Common Pitfall?
- Developers expect a new prototype instance for each service method call.
- Direct field/constructor injection **locks** a single prototype instance inside the singleton.
- The prototype scope only affects **lookup time**, not the lifecycle of the singleton that holds it.

## Fixes: Getting a Fresh Prototype Each Time

### Option 1: `ObjectFactory<T>`
- Inject a factory and call `getObject()` when you need a new instance.

```java
@Service
public class OrderService {
  private final ObjectFactory<Task> taskFactory;

  public OrderService(ObjectFactory<Task> taskFactory) {
    this.taskFactory = taskFactory;
  }

  public void process() {
    Task task = taskFactory.getObject();
    task.run();
  }
}
```

### Option 2: `Provider<T>` (JSR-330)
- Similar to `ObjectFactory`, with `get()` for lookup.

```java
@Service
public class OrderService {
  private final Provider<Task> taskProvider;

  public OrderService(Provider<Task> taskProvider) {
    this.taskProvider = taskProvider;
  }

  public void process() {
    Task task = taskProvider.get();
    task.run();
  }
}
```

### Option 3: `@Lookup`
- Spring overrides a method to do dynamic lookup at runtime.
- Good when you want a clean API without factories.

```java
@Service
public abstract class OrderService {
  public void process() {
    Task task = createTask();
    task.run();
  }

  @Lookup
  protected abstract Task createTask();
}
```

## Senior-Level Notes Interviewers Like to Hear
- Prototype scope governs **creation**, not **destruction**; the container does not manage full lifecycle cleanup.
- If a prototype holds resources, **you** must release them (e.g., `close()` or try-with-resources).
- Use `@Scope(proxyMode = ScopedProxyMode.TARGET_CLASS)` only when you need to inject a scoped bean into another scope and accept proxying costs.
- Prefer `Provider` or `ObjectFactory` for clarity in codebases that avoid proxies.
