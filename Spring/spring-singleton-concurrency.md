# Spring Singleton Concurrency (Beginner-Friendly)

## Scenario
- A singleton service is shared by all users.
- 100 users call the same service at the same time.
- The service has an instance variable.

## Question: Is It Thread Safe?
- **Usually no.** A singleton is one object shared by many threads.
- If the service has a **mutable instance variable**, different users can overwrite each other.
- This causes **wrong results** or **data leakage** between users.

## Small Example (Not Thread Safe)
```java
@Service
public class OrderService {
    private String currentUser; // shared by all threads

    public String placeOrder(String user) {
        currentUser = user;
        return "Order placed by " + currentUser;
    }
}
```
**Problem:** If 2 users call at the same time, `currentUser` can change in the middle.

## How to Fix (Easy Options)
- **Make the service stateless:** move per-request data into method parameters or local variables.
- **Use request scope:** create a new service instance per HTTP request if you must keep state.
- **Use thread-safe structures:** only if shared state is truly needed (e.g., `ConcurrentHashMap`).

## Solution Example (Request Scope)
```java
@Service
@Scope("request")
public class OrderService {
    private String currentUser; // safe because each request gets a new instance

    public String placeOrder(String user) {
        currentUser = user;
        return "Order placed by " + currentUser;
    }
}
```

## Safe Version (Stateless)
```java
@Service
public class OrderService {
    public String placeOrder(String user) {
        return "Order placed by " + user;
    }
}
```

## Quick Interview Answer
"A singleton bean is shared by all threads, so instance variables are not thread safe. The safest fix is to make the service stateless or move state to method locals. If state is required, use request scope or thread-safe structures."
