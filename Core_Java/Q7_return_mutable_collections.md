# Q7: How do you return mutable collections safely?

**Study Time:** 3 minutes

---

## Problem

Exposing collections without allowing external modification.

## ❌ Wrong (Unsafe)

```java
public class Database {
    private List<User> users = new ArrayList<>();
    
    // Direct return - DANGEROUS!
    public List<User> getUsers() {
        return users;  // Caller can modify!
    }
}

// Usage - breaks data integrity!
List<User> users = db.getUsers();
users.clear();  // Clears the database! ❌
```

## ✅ Right Option 1: Return Copy

```java
public List<User> getUsers() {
    return new ArrayList<>(users);  // Client gets copy
}

// Usage - safe!
List<User> users = db.getUsers();
users.clear();  // Only clears the copy, not database ✅
```

## ✅ Right Option 2: Return Unmodifiable View

```java
public List<User> getUsers() {
    return Collections.unmodifiableList(users);  // View, not copy
}

// Usage - throws exception on modification attempt
List<User> users = db.getUsers();
users.add(new User());  // Throws UnsupportedOperationException ✅
```

## ✅ Right Option 3: Return Stream (Java 8+)

```java
public Stream<User> getUsers() {
    return users.stream();  // Can't modify stream
}

// Usage - expressive and safe
db.getUsers()
  .filter(u -> u.isActive())
  .forEach(System.out::println);
```

## ✅ Right Option 4: Return Immutable (Java 9+)

```java
public List<User> getUsers() {
    return List.copyOf(users);  // Immutable copy
}

// Usage - most restrictive
List<User> users = db.getUsers();
users.add(new User());  // Throws UnsupportedOperationException
```

## Comparison

| Method | Copy? | Type-Safe? | Performance | Use When |
|--------|-------|-----------|-----------|----------|
| Return copy | ✅ Yes | ✅ High | Slower | Want modifiable copy |
| Unmodifiable | ⚠️ No | ✅ High | Fast | Prevent modifications |
| Stream | ❌ No | ✅ High | Fast | Processing only |
| List.copyOf | ✅ Yes | ✅ High | Medium | Java 9+ immutable |

## Interview Tip

"Return `Collections.unmodifiableList()` if you want to prevent modifications without copying. Use `new ArrayList<>(list)` if client needs a modifiable copy. Both prevent external modification of your internal state."

## Quick Checklist

- ✅ Never return internal collection directly
- ✅ Use `Collections.unmodifiable*()` to prevent modifications
- ✅ Use `new ArrayList<>(list)` for modifiable copies
- ✅ Use `Stream` for processing pipelines
- ✅ Use `List.copyOf()` for true immutability (Java 9+)
- ✅ Consider memory cost of copying large lists

---

**Next:** Study Q8 on race conditions
