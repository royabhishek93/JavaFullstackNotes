# Exception Propagation in Method Overriding

**Study Time:** 8-10 minutes | **Frequency:** 70% in interviews | **Difficulty:** ⭐⭐⭐⭐

---

## 🤔 Problem Scenario

Can a subclass throw ANY exception when overriding a method?

```java
class Parent {
    public void process() throws IOException {
        throw new IOException("IO error");
    }
}

class Child extends Parent {
    @Override
    public void process() throws Exception {  // ❌ Is this allowed?
        throw new Exception("General error");
    }
}
```

**Question:** Can overriding method declare a BROADER exception?

---

## 🧠 Key Principle: Exception Compatibility Rule

**Rule:** Overriding method can throw **fewer or same** exceptions, NOT more.

```
Parent declares: throws IOException
Child can declare:
  ✅ throws IOException (same)
  ✅ throws FileNotFoundException (subclass - narrower)
  ✅ throws nothing (no exception)
  ❌ throws Exception (broader - ERROR)
  ❌ throws Throwable (broader - ERROR)
```

**Why?** Liskov Substitution Principle: Subclass must be usable wherever parent is used.

```java
Parent p = new Child();  // Child is-a Parent
p.process();  // Caller expects IOException only
              // If Child throws Exception, caller not prepared!
```

---

## ✅ Scenario 1: Same Exception

```java
class Parent {
    public void method() throws IOException { }
}

class Child extends Parent {
    @Override
    public void method() throws IOException { }  // ✅ OK - same
}
```

---

## ✅ Scenario 2: Narrower Exception (Subclass)

```java
class Parent {
    public void method() throws IOException { }
}

class Child extends Parent {
    @Override
    public void method() throws FileNotFoundException { }  // ✅ OK - narrower
    // FileNotFoundException extends IOException
}

// Usage:
public static void main(String[] args) throws IOException {
    Parent p = new Child();
    p.method();  // Caller catches IOException, works fine
    // FileNotFoundException IS-A IOException
}
```

---

## ✅ Scenario 3: No Exception

```java
class Parent {
    public void method() throws IOException { }
}

class Child extends Parent {
    @Override
    public void method() { }  // ✅ OK - throws nothing
}

// Usage:
public static void main(String[] args) throws IOException {
    Parent p = new Child();
    p.method();  // No exception thrown, safe
}
```

---

## ❌ Scenario 4: Broader Exception (ERROR)

```java
class Parent {
    public void method() throws IOException { }
}

class Child extends Parent {
    @Override
    public void method() throws Exception { }  // ❌ COMPILE ERROR
    // Exception is broader than IOException
}

// Compiler Error:
// "Exception IOException is not compatible with throws clause in Parent"
```

**Why this fails:**

```
public static void main(String[] args) throws IOException {
    Parent p = new Child();
    try {
        p.method();  // Caller only expects IOException
    } catch (IOException e) { }
    // But Child throws Exception (RuntimeException, etc.)
    // Caller not prepared!
}
```

---

## ✅ Scenario 5: Multiple Exceptions

```java
class Parent {
    public void process() throws IOException, SQLException { }
}

class Child extends Parent {
    @Override
    public void process() throws IOException { }  // ✅ OK - fewer exceptions
}
```

**Valid combinations:**
- Same two: throws IOException, SQLException ✅
- Subset: throws IOException ✅
- Subset: throws SQLException ✅
- Empty: throws nothing ✅
- Different set: throws IOException, RuntimeException ❌
- Superset: throws IOException, SQLException, Exception ❌

---

## ✅ Scenario 6: Checked vs Unchecked Exceptions

```java
class Parent {
    public void method() throws IOException { }
}

class Child extends Parent {
    @Override
    public void method() throws RuntimeException { }  // ✅ OK!
    // RuntimeException (unchecked) doesn't need declaration
}

// Why? RuntimeExceptions don't have to be caught
// They represent programming errors, not resource issues
```

**Important:**
```
Unchecked exceptions (RuntimeException) are always allowed:

class Parent {
    public void method() throws IOException { }
}

class Child extends Parent {
    @Override
    public void method() throws NullPointerException { }  // ✅ OK
    public void other() throws ArithmeticException { }    // ✅ OK
}

// Unchecked exceptions aren't part of the contract
```

---

## 🎯 Interview Q&A

### Q1: "Can overriding method throw broader exception?"

**Answer (20 seconds):**
```
No. Overriding method must throw same or NARROWER exceptions.

Parent: throws IOException
Child: can throw:
  ✅ IOException (same)
  ✅ FileNotFoundException (narrower subclass)
  ✅ Nothing

Child: CANNOT throw:
  ❌ Exception (broader)
  ❌ Throwable (broader)

Reason: Liskov Substitution Principle
When using Parent reference pointing to Child,
caller expects only Parent's exceptions.
```

---

### Q2: "What if parent throws nothing?"

**Answer:**
```
class Parent {
    public void method() { }  // No exception
}

class Child extends Parent {
    @Override
    public void method() throws Exception { }  // ❌ ERROR!
}

If parent throws nothing, child CANNOT throw checked exceptions.

But unchecked is OK:
class Child extends Parent {
    @Override
    public void method() throws RuntimeException { }  // ✅ OK
}
```

---

### Q3: "What about unchecked exceptions?"

**Answer:**
```
Unchecked exceptions (RuntimeException) are ALWAYS allowed:

class Parent {
    public void method() throws IOException { }
}

class Child extends Parent {
    @Override
    public void method() throws IOException, NullPointerException { }
    // ✅ OK - runtime exceptions don't count
}

Why?
- Unchecked exceptions represent programming errors
- They can happen anywhere (division by 0, null access, etc.)
- Not part of method contract
- Caller doesn't need to catch them

But adding CHECKED exceptions is not allowed.
```

---

### Q4: "Code - will this compile?"

```java
class Parent {
    public void test() throws IOException { }
}

class Child extends Parent {
    @Override
    public void test() throws FileNotFoundException { }
}
```

**Answer:**
```
YES - Compiles successfully.

FileNotFoundException extends IOException,
so it's a narrower (more specific) exception.

Caller expecting IOException can handle it:
try {
    parent.test();  // Actually Child.test()
} catch (IOException e) { }  // Catches FileNotFoundException too
```

---

### Q5: "Real-world example?"

**Answer:**
```
Data Access Layer:

class BaseRepository {
    public User findById(int id) throws SQLException { }
}

class UserRepository extends BaseRepository {
    @Override
    public User findById(int id) throws SQLException { }
    // ✅ Same exception - fine
}

Better design:
class UserRepository extends BaseRepository {
    @Override
    public User findById(int id) throws DataAccessException { }
    // ✅ More specific (subclass) - better
}

Wrong:
class UserRepository extends BaseRepository {
    @Override
    public User findById(int id) throws Exception { }
    // ❌ Too broad - compile error
}
```

---

## ❌ Common Mistakes

### ❌ Mistake 1: Thinking Subclass Can Add Checked Exceptions

```java
// WRONG
class Parent {
    public void method() throws IOException { }
}

class Child extends Parent {
    @Override
    public void method() throws IOException, SQLException { }
    // ❌ COMPILE ERROR: Cannot add SQLException
}

// CORRECT
class Child extends Parent {
    @Override
    public void method() throws IOException { }
}
```

---

### ❌ Mistake 2: Forgetting Liskov Substitution

```java
// WRONG THINKING
Parent p = new Child();
p.method();  // Throws IOException? Or Exception?
             // Caller confused - undefined behavior

// If Child throws broader exception, caller's IOException handler
// doesn't catch it → Runtime error or unhandled exception

// CORRECT THINKING
// Child must throw same or narrower exceptions
// So caller's IOException handler catches it
```

---

### ❌ Mistake 3: Confusing Unchecked Exceptions

```java
// CORRECT - Unchecked allowed
class Parent {
    public void method() throws IOException { }
}

class Child extends Parent {
    @Override
    public void method() throws NullPointerException { }
    // ✅ OK - RuntimeException (unchecked)
}

// WRONG - Adding checked exceptions not allowed
class Child2 extends Parent {
    @Override
    public void method() throws SQLException { }
    // ❌ ERROR - SQLException is checked, not in parent's contract
}
```

---

## 📊 Exception Hierarchy Reference

```
Throwable
├── Error (system errors, not caught usually)
├── Exception
│   ├── IOException (checked)
│   │   └── FileNotFoundException (checked)
│   ├── SQLException (checked)
│   └── RuntimeException (unchecked)
│       ├── NullPointerException
│       ├── ArithmeticException
│       └── ArrayIndexOutOfBoundsException
```

---

## 🔑 Key Takeaways

| Concept | Why Important | Interview Score |
|---------|---------------|-----------------|
| Exception propagation rules | Core OOP principle (Liskov) | ⭐⭐⭐⭐⭐ |
| Narrower exceptions allowed | Design pattern knowledge | ⭐⭐⭐⭐ |
| Broad exceptions forbidden | Contract enforcement | ⭐⭐⭐⭐ |
| Unchecked exceptions always OK | Exception type distinction | ⭐⭐⭐ |

---

**Priority:** ✅ SHOULD KNOW (70% interview frequency, tests OOP understanding)

**Related Topics:**
- [Checked vs Unchecked Exceptions](#)
- [Liskov Substitution Principle](#)
- [Exception Handling Best Practices](#)

---

**Last Updated:** March 5, 2026
