# Try-Catch-Finally Execution Order

**Study Time:** 8-10 minutes | **Frequency:** 85% in interviews | **Difficulty:** ⭐⭐⭐⭐⭐

---

## 🤔 Problem Scenario

What gets printed when exception is thrown in try block?

```java
public class TryCatchFinallyExample {

    public static void main(String[] args) {
        System.out.println(testMethod());
    }

    public static String testMethod() {
        try {
            System.out.println("In try block");
            throw new Exception("Exception in try");
            // return "from try";  // Never reached
        } catch (Exception e) {
            System.out.println("In catch block");
            return "from catch";
        } finally {
            System.out.println("In finally block");
        }
    }
}
```

**Output:**
```
In try block
In catch block
In finally block
from catch
```

**Question:** Why does finally execute AFTER catch returns?

---

## 🧠 Key Principle: Finally Always Executes

**Rule #1:** `finally` block ALWAYS executes, regardless of:
- Exception thrown
- Return statement in try/catch
- Break/continue in loop
- System.exit() ... well, almost (see exceptions below)

**Execution Order:**
```
1. try block executes
   ↓
2. If exception → catch block executes
   OR skip to finally (if no catch matches)
   ↓
3. If return/break/continue → held temporarily
   ↓
4. finally block ALWAYS executes
   ↓
5. Then return/break/continue executes
```

---

## ✅ Scenario 1: Exception Thrown, Caught

```java
public static String scenario1() {
    try {
        System.out.println("1. try");
        throw new RuntimeException("error");
    } catch (RuntimeException e) {
        System.out.println("2. catch");
        return "from catch";
    } finally {
        System.out.println("3. finally");
    }
}

// Output:
// 1. try
// 2. catch
// 3. finally
// Result: "from catch"
```

**Execution flow:**
```
try (executes, throws exception)
  ↓ (exception caught)
catch (executes, prepares return "from catch")
  ↓ (finally always runs, even with pending return)
finally (executes)
  ↓ (now actually return)
return "from catch"
```

---

## ✅ Scenario 2: No Exception, Normal Return

```java
public static String scenario2() {
    try {
        System.out.println("1. try");
        return "from try";  // Pending return
    } catch (RuntimeException e) {
        System.out.println("2. catch");
        return "from catch";
    } finally {
        System.out.println("3. finally");
    }
}

// Output:
// 1. try
// 3. finally
// Result: "from try"
```

**Execution flow:**
```
try (executes, encounters return)
  ↓ (return value held, finally must execute)
finally (executes)
  ↓ (finally done, now execute return)
return "from try"
```

---

## ✅ Scenario 3: Finally Modifies Return Value

```java
public static String scenario3() {
    String result = "initial";
    try {
        System.out.println("1. try: " + result);
        result = "from try";
        return result;
    } finally {
        System.out.println("2. finally");
        result = "from finally";
        // This modification does NOT affect the return!
    }
}

// Output:
// 1. try: initial
// 2. finally
// Result: "from try" (NOT "from finally")
```

**Why?**
- Primitive types and Strings are immutable/passed by value
- The return value is already determined before finally executes
- Finally's modification happens too late

---

## ✅ Scenario 4: Finally Modifies Object (Reference Type)

```java
public static StringBuilder scenario4() {
    StringBuilder sb = new StringBuilder("initial");
    try {
        System.out.println("1. try: " + sb);
        sb.append(" from try");
        return sb;
    } finally {
        System.out.println("2. finally");
        sb.append(" from finally");
        // Object is modified before return!
    }
}

// Output:
// 1. try: initial
// 2. finally
// Result: "initial from try from finally"
```

**Why?**
- Objects (references) are passed by reference
- Both try and finally can modify the same object
- Return gets the modified object

---

## ✅ Scenario 5: Finally Throws Exception

```java
public static String scenario5() {
    try {
        System.out.println("1. try");
        throw new IOException("IOException in try");
    } catch (IOException e) {
        System.out.println("2. catch");
        return "from catch";
    } finally {
        System.out.println("3. finally");
        throw new RuntimeException("RuntimeException in finally");
    }
}

// Output:
// 1. try
// 2. catch
// 3. finally
// Exception thrown: RuntimeException (original IOException lost!)
```

**Execution flow:**
```
try (throws IOException)
  ↓
catch (prepares return, but...)
  ↓
finally (throws RuntimeException!)
  ↓
RuntimeException propagates (IOException suppressed)
```

**Key point:** Exception from finally OVERRIDES exception from try/catch.

---

## ✅ Scenario 6: Finally with Break in Loop

```java
public static void scenario6() {
    for (int i = 0; i < 3; i++) {
        try {
            System.out.println("1. try: " + i);
            if (i == 1) {
                break;  // Pending break
            }
        } finally {
            System.out.println("2. finally: " + i);
            // Finally executes even with break!
        }
    }
    System.out.println("3. after loop");
}

// Output:
// 1. try: 0
// 2. finally: 0
// 1. try: 1
// 2. finally: 1
// 3. after loop
```

---

## ✅ Scenario 7: Nested Try-Catch-Finally

```java
public static String scenario7() {
    try {
        System.out.println("1. outer try");
        try {
            System.out.println("2. inner try");
            throw new RuntimeException("inner exception");
        } catch (RuntimeException e) {
            System.out.println("3. inner catch");
            throw new Exception("outer exception");
        } finally {
            System.out.println("4. inner finally");
        }
    } catch (Exception e) {
        System.out.println("5. outer catch");
        return "caught outer";
    } finally {
        System.out.println("6. outer finally");
    }
}

// Output:
// 1. outer try
// 2. inner try
// 3. inner catch
// 4. inner finally
// 5. outer catch
// 6. outer finally
// Result: "caught outer"
```

---

## ❌ Errors and Edge Cases

### ❌ Exception in Finally Suppresses Original Exception

```java
try {
    throw new Exception("Original");
} catch (Exception e) {
    return "catch";
} finally {
    throw new RuntimeException("Final");
    // RuntimeException overrides Exception from catch!
}

// Result: RuntimeException thrown (Exception lost)
```

**Fix (Java 7+):**
```java
try {
    throw new Exception("Original");
} catch (Exception e) {
    try {
        return "catch";
    } catch (Exception innerE) {
        e.addSuppressed(innerE);
        throw e;
    }
} finally {
    // ...
}

// Or use try-with-resources (auto-closes resources)
try (Resource r = new Resource()) {
    // work
} finally {
    // cleanup
}
```

---

### ❌ Finally with System.exit()

```java
try {
    System.out.println("Try");
    System.exit(0);  // Terminates JVM
} finally {
    System.out.println("Finally");  // NEVER executes
}

// Output:
// Try
// (JVM exits, finally not called)
```

**Exception:** System.exit() prevents finally from executing.

---

### ❌ Finally with Return on Collection

```java
public static List<String> scenario() {
    List<String> list = new ArrayList<>(List.of("a", "b"));
    try {
        System.out.println("1. try");
        return list;
    } finally {
        System.out.println("2. finally");
        list.clear();  // Modifies the returned list!
    }
}

// Output:
// 1. try
// 2. finally
// Result: [] (empty list - modified in finally)
```

---

## 🎯 Interview Q&A

### Q1: "Will finally always execute?"

**Answer:**
```
Yes, almost always. Exception: System.exit()

try {
    return "try";
} finally {
    System.out.println("Finally");  // WILL execute
}

But:
try {
    System.exit(0);
} finally {
    System.out.println("Finally");  // WON'T execute (JVM exits)
}
```

---

### Q2: "Code - what prints?"

```java
public static void test() {
    try {
        System.out.println("A");
        return;
    } finally {
        System.out.println("B");
    }
}
```

**Answer:**
```
Output:
A
B

Explanation:
- try executes (prints A), prepares return
- finally executes (prints B), even though return is pending
- Then return executes
```

---

### Q3: "Will catch execute if exception not thrown?"

```java
try {
    System.out.println("Try");
} catch (IOException e) {
    System.out.println("Catch");
} finally {
    System.out.println("Finally");
}
```

**Answer:**
```
Output:
Try
Finally

Explanation:
- try executes (no exception)
- catch skipped (no exception to catch)
- finally always executes
```

---

### Q4: "Can finally return override try return?"

```java
public static String test() {
    try {
        return "from try";
    } finally {
        return "from finally";  // Overrides try return
    }
}
```

**Answer:**
```
YES - finally return overrides try/catch return.

Output: "from finally"

But this is BAD PRACTICE:
- Confusing
- Suppresses exceptions
- Hard to debug

Avoid finally blocks with explicit returns!
```

---

### Q5: "What if finally throws exception?"

```java
try {
    throw new IOException("IO");
} catch (IOException e) {
    return "catch";
} finally {
    throw new RuntimeException("Runtime");
}
```

**Answer:**
```
RuntimeException is thrown (IOException lost).

The original IOException is SUPPRESSED.

Output: RuntimeException

Fix: 
- Don't throw exceptions in finally
- Or use try-with-resources
- Or properly chain/suppress exceptions
```

---

## 📚 Best Practices

### ✅ DO

```java
// Use finally for cleanup
try {
    // work
} finally {
    resource.close();  // Cleanup always happens
}

// Prefer try-with-resources (Java 7+)
try (Resource r = new Resource()) {
    // work with r
}
// Auto-closes r in finally

// Use different catch blocks
try {
    // work
} catch (IOException e) {
    // handle IO
} catch (SQLException e) {
    // handle SQL
} finally {
    // cleanup both
}
```

### ❌ DON'T

```java
// Don't return from finally
try {
    return "try";
} finally {
    return "finally";  // Bad! Suppresses exceptions
}

// Don't throw in finally (without care)
try {
    // work
} finally {
    throw new Exception();  // May suppress original exception
}

// Don't use finally for business logic
try {
    // work
} finally {
    result.append("extra");  // No! Use finally only for cleanup
}
```

---

## 🔑 Key Takeaways

| Concept | Why Important | Interview Score |
|---------|---------------|-----------------|
| Finally always executes | Fundamental rule | ⭐⭐⭐⭐⭐ |
| Execution order | Logic understanding | ⭐⭐⭐⭐⭐ |
| Return suppression | Edge case awareness | ⭐⭐⭐⭐ |
| Try-with-resources | Modern Java practice | ⭐⭐⭐⭐ |
| Exception overriding | Debugging skills | ⭐⭐⭐⭐ |

---

**Priority:** 🔥 MUST KNOW (85% interview frequency)

**Related Topics:**
- [Exception Handling Best Practices](#)
- [Try-With-Resources](#)
- [Custom Exceptions](#)

---

**Last Updated:** March 5, 2026
