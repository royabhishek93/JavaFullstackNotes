# Spring Scopes Senior Notes

## Scenario
- Controller calls a service method.
- Service is a `singleton` bean (default scope).
- Service uses a `prototype` bean.
- Interviewer asks: How many objects are created and when?

## Key Principle
- **Prototype scope creates a new instance only when Spring is asked for it.**
- **Singleton scope creates exactly one instance for the container.**

## Case A: Prototype Injected Directly Into Singleton
**Purpose (simple):** show what happens when a singleton gets a prototype only once at startup.

### What Happens
- Spring creates the singleton at startup (or first access if lazy).
- During singleton creation, Spring resolves its dependencies.
- The prototype bean is created once and injected into the singleton.

### Result
- Singleton instances: 1
- Prototype instances: 1 (created at singleton construction time)

### Important Consequence
- Every later method call on the singleton **reuses the same prototype instance**.
- This surprises many developers and can cause state leakage bugs.

### Example: 4 Calls, Same Prototype Instance
Assume `Task` is prototype-scoped and has an `id` set at construction.

```java
@Service
public class OrderService {
    private final Task task; // prototype injected once

    public OrderService(Task task) {
        this.task = task;
    }

    public void process() {
        System.out.println("Task id = " + task.getId());
    }
}
```

**Runtime (4 calls):**
```
service.process(); // Task id = 42
service.process(); // Task id = 42
service.process(); // Task id = 42
service.process(); // Task id = 42
```

Only one `Task` instance (id 42) was created when the singleton was built, so all 4 calls reuse it.

### Simple `Task` Class (for the examples)
```java
@Component
@Scope("prototype")
public class Task {
    private static int seq = 40;
    private final int id = ++seq;

    public int getId() {
        return id;
    }

    public void run() {
        System.out.println("Task running, id = " + id);
    }
}
```

Each new `Task` gets a new `id`, so repeated calls show whether a fresh instance was created.

## Case B: Prototype Looked Up on Demand
**Purpose (simple):** show how to get a fresh prototype every time the singleton needs it.

### What Happens
- Singleton is still created once.
- Each time the service requests the prototype bean, Spring creates a new instance.

### Example: 4 Calls, New Prototype Each Time
Assume `Task` is prototype-scoped and has an `id` set at construction. The service asks for a new `Task` on every call.

```java
@Service
public class OrderService {
    private final ObjectFactory<Task> taskFactory;

    public OrderService(ObjectFactory<Task> taskFactory) {
        this.taskFactory = taskFactory;
    }

    public void process() {
        Task task = taskFactory.getObject();
        System.out.println("Task id = " + task.getId());
    }
}
```

**Runtime (4 calls):**
```
service.process(); // Task id = 42
service.process(); // Task id = 43
service.process(); // Task id = 44
service.process(); // Task id = 45
```

Each call performs a fresh lookup, so Spring creates a new `Task` instance every time.

### Result
- Singleton instances: 1
- Prototype instances: 1 per lookup

## How to Fix the Prototype-in-Singleton Pitfall

### Option 1: `ObjectFactory<T>`
- Inject a factory and call `getObject()` when needed.
- **Purpose (simple):** lets the singleton ask Spring for a *new* prototype each time, instead of reusing one old instance.

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
- Similar pattern using `get()`.
- **Purpose (simple):** same idea as `ObjectFactory`, but from the standard Java/Jakarta spec, so it works across frameworks.

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
- Spring overrides the method to perform a dynamic lookup each call.
- **Purpose (simple):** you call a method like `createTask()` and Spring quietly creates a fresh prototype for you every time.

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

## Senior-Level Notes Interviewers Like
- Prototype scope affects **creation**, not **destruction**; the container does not manage full lifecycle cleanup for prototypes.
- If prototype beans own resources, the application must release them (e.g., `close()` or try-with-resources).
- A scoped proxy can also solve scope mismatch, but it adds proxy overhead and debugging complexity.
- `ObjectFactory` and `Provider` are explicit and easier to reason about in large codebases.

## Quick Interview Answer
"If a prototype is injected directly into a singleton, only one prototype instance is created at singleton construction and reused forever. To get a new prototype per call, you must request it on demand via `ObjectFactory`, `Provider`, or `@Lookup`."

## Interview Follow-Ups (With Short Answers)
**Q1: A singleton depends on a prototype. How many instances are created and when? How do you force a new one per call?**
A: One prototype is created when the singleton is built. Use `ObjectFactory`, `Provider`, or `@Lookup` to create a new prototype per call.

**Q2: You see state leakage in a service using a prototype. Where do you look and how do you fix it?**
A: Check if the prototype is injected directly into a singleton. Fix by looking it up on demand.

**Q3: When would you choose `ObjectFactory`, `Provider`, or `@Lookup`?**
A: `ObjectFactory` is Spring-specific and explicit, `Provider` is standard (JSR-330), `@Lookup` is convenient but less obvious in code.

**Q4: Prototype bean holds a DB connection. Who closes it and how?**
A: The app must close it. Spring does not manage destruction for prototypes.

**Q5: How do scoped proxies work, and when do they hurt?**
A: The proxy is injected and does lookup per call. It adds overhead and can make debugging harder.

**Q6: How does `@Lazy` affect singleton/prototype interactions?**
A: It delays bean creation, but does not change the fact that a directly injected prototype is still only created once.

**Q7: What happens if a prototype bean is injected into another prototype?**
A: Each time Spring creates the outer prototype, it creates a fresh inner prototype too.

**Q8: How would you write a test to prove new prototype instances are created?**
A: Fetch the bean multiple times and assert different instance references or ids.

**Q9: What changes when the scope is `request` or `session` instead of prototype?**
A: Instances are tied to HTTP request or session. You get one per request/session, not per lookup.

**Q10: How would you design a stateless service to avoid scope issues?**
A: Keep all state in method parameters or locals and avoid storing per-request data in fields.

