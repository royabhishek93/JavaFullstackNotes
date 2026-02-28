# Q8: What happens with `String car, bus = "petrol";`?

**Study Time:** 2-3 minutes | **Frequency:** Common in coding interviews 🔥

---

## The Problem (Classic Interview Gotcha)

You see this code and think both variables are initialized:

```java
String car, bus = "petrol";
System.out.println(car);  // null or compile error?
System.out.println(bus);  // petrol?
```

Which line will fail and why?

---

## What Actually Happens

### Declaration vs Initialization

When you write:
```java
String car, bus = "petrol";
```

It means:
```java
String car;              // ← declared, NOT initialized
String bus = "petrol";   // ← declared AND initialized
```

**Key Point:** Only the **last variable** in the declaration receives the value.

---

## The Execution

```java
String car, bus = "petrol";

System.out.println(bus);   // ✅ petrol (initialized)
System.out.println(car);   // ❌ compile-time error: variable car might not have been initialized
```

### Error Message You'll See
```
error: variable car might not have been initialized
System.out.println(car);
                   ^
```

---

## Why Does This Happen?

The JVM reads the declaration left-to-right:

1. **`String car`** → Variables space allocated, no value assigned
2. **`, bus = "petrol"`** → Only `bus` gets the assignment

The declaration-initialization operator `=` **only applies to the variable immediately before it**.

---

## Visual Memory State

```
Memory After: String car, bus = "petrol";

Stack:
┌──────────────┬─────────────────────┐
│ car: null⚠️  │ bus: ──→ "petrol"   │
└──────────────┴─────────────────────┘
                        ↓
                   String Pool/Heap
                   ┌─────────┐
                   │ "petrol"│
                   └─────────┘
```

---

## If You Want Both Variables Initialized

### ❌ Wrong Approach (Still Confusing)
```java
String car, bus = "petrol";  // Only bus gets value
```

### ✅ Right Approaches

**Option 1: Explicit initialization**
```java
String car = "petrol", bus = "petrol";
System.out.println(car);   // petrol ✅
System.out.println(bus);   // petrol ✅
```

**Option 2: Separate declarations (Most readable)**
```java
String car = "petrol";
String bus = "petrol";
System.out.println(car);   // petrol ✅
System.out.println(bus);   // petrol ✅
```

---

## Interview Q&A

### Q: Why would someone write this confusing syntax?
**A:** They mistakenly think the initialization applies to all variables in the declaration. In reality, Java allows multiple declarations in one statement, but the `=` operator only initializes the **last** variable before the comma or semicolon.

### Q: Is this a Java bug?
**A:** No, it's by design. The syntax mirrors other languages, but it's definitely a source of bugs. Most linters warn against this pattern.

### Q: What's the proper term for this?
**A:** **Multiple variable declaration** or **combined declaration with partial initialization**.

---

## 🔥 Production Interview Tip

**Interview Question You Might Get:**

> "What's the output and explain why?"
> ```java
> String x, y = "Java", z;
> System.out.println(y);
> ```

**Your Answer:**
- `x` → declared but not initialized
- `y` → declared and initialized with "Java"
- `z` → declared but not initialized
- Printing `y` outputs: **Java** ✅
- Printing `x` or `z` would give: **compile-time error**

---

## Pitfall Summary

| Code | Result |
|------|--------|
| `String a, b = "test";` | `a` is null (uninitialized), compile error if used |
| `String a = "test", b = "test";` | Both initialized ✅ |
| `String a = "test"; String b = "test";` | Both initialized, most readable ✅ |

