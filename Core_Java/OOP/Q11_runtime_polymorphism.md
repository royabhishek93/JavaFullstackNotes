# Q11: Runtime Polymorphism - Reference Type vs Object Type

**Study Time:** 4-5 minutes | **Frequency:** 78% in senior interviews 🔥 | **Difficulty:** ⭐⭐⭐⭐

---

## The Scenario

```java
class A {
    public void m1() { System.out.println("A.m1()"); }
    public void m2() { System.out.println("A.m2()"); }
}

class B extends A {
    @Override
    public void m2() { System.out.println("B.m2()"); }
    
    public void m3() { System.out.println("B.m3()"); }
}

A a0 = new B();

a0.m1();  // ? Which method executes?
a0.m2();  // ? Which method executes?
a0.m3();  // ? Compile-time error or runtime error?
```

**What happens?**

---

## 🔥 The Core Principle

```
👉 Object type decides EXECUTION
👉 Reference type decides VISIBILITY (compile-time)
```

This is **Runtime Polymorphism** - the method executed is determined at **runtime** by the actual object, not the reference type.

---

## Step-by-Step Analysis

### Call 1: `a0.m1()`

```java
A a0 = new B();
a0.m1();  // ✅ Prints: A.m1()
```

**What happens:**
- Reference type is `A` - has method `m1()`? ✅ Yes
- Object type is `B` - overrides `m1()`? ❌ No
- So calls `A.m1()`

**Rule:** Method NOT overridden in B → Uses A's implementation

---

### Call 2: `a0.m2()`

```java
a0.m2();  // ✅ Prints: B.m2()
```

**What happens:**
- Reference type is `A` - has method `m2()`? ✅ Yes
- Object type is `B` - overrides `m2()`? ✅ Yes → **Calls B's version**
- Runtime binding: actual object type determines execution

**Rule:** Method overridden in B → Uses B's implementation (Runtime binding)

---

### Call 3: `a0.m3()`

```java
a0.m3();  // ❌ COMPILE-TIME ERROR
```

**What happens:**
- Reference type is `A` - has method `m3()`? ❌ No
- Compiler error: "The method m3() is undefined for the type A"

**Rule:** Reference type doesn't have method → Compile-time error, never reaches runtime

```java
// To fix: Cast to B first
if (a0 instanceof B) {
    B b = (B) a0;
    b.m3();  // ✅ Works at runtime
}
```

---

## Complete Execution Table

| Method | In A? | Overridden in B? | Called? | Why? |
|--------|-------|------------------|---------|------|
| **m1()** | ✅ | ❌ | A.m1() | Not overridden, use parent |
| **m2()** | ✅ | ✅ | B.m2() | Overridden, use child (Runtime binding) |
| **m3()** | ❌ | ✅ | ❌ ERROR | Reference type (A) doesn't have m3() |

---

## Real Example: Collections

```java
List<String> list = new ArrayList<>();  // Reference: List, Object: ArrayList
list.add("hello");                       // ✅ List has add()
list.forEach(System.out::println);       // ✅ Calls ArrayList's forEach()
list.stream();                           // ✅ List has stream()
```

All methods are resolved at runtime to the actual object (ArrayList).

---

## Important Concepts

### 1) Method Overloading vs Overriding

```java
class A {
    public void show(int x) { System.out.println("int: " + x); }
    public void show(String s) { System.out.println("String: " + s); }
}

class B extends A {
    @Override
    public void show(int x) { System.out.println("B int: " + x); }
    // Overriding, not overloading
}

A a = new B();
a.show(5);       // ✅ B's show(int)
a.show("hello"); // ✅ A's show(String)
```

---

### 2) Virtual Method Invocation

Java uses **Virtual Method Tables** at runtime:

```
Reference type A → points to B's actual object
At runtime → JVM looks up method in B first
If not found → looks up in A (parent)
```

This is called **Late Binding** or **Dynamic Dispatch**.

---

## Interview Tip

"Runtime polymorphism allows parent references to point to child objects. The **compile-time visibility** is determined by the reference type, but the **actual method executed** is determined by the object type at runtime. This is why `a0.m3()` won't compile even though the actual object (B) has m3() - the reference type (A) doesn't see it."

---

## ⚠️ Common Pitfalls

**Pitfall 1: Assuming reference type determines method execution**

❌ **Wrong approach:**
```java
A a0 = new B();
a0.m2();  // Thinking: "Reference is A, so calls A.m2()"
```
**Why it fails:** Executes B.m2() at runtime, not A.m2(). The object type matters, not the reference type.

✅ **Right approach:**
```java
// Remember: Object type (B) determines execution
A a0 = new B();
a0.m2();  // Calls B.m2() ✅ Runtime binding
```

---

**Pitfall 2: Trying to access child-only methods through parent reference**

❌ **Wrong approach:**
```java
A a0 = new B();
a0.m3();  // ❌ Compile error - A doesn't have m3()

// Then trying to force it:
Object result = a0;
// This doesn't help - still can't call m3()
```
**Why it fails:** Compiler checks reference type, not object type. Even though object IS a B, reference type is A.

✅ **Right approach:**
```java
A a0 = new B();
if (a0 instanceof B) {
    B b = (B) a0;  // Cast to actual type
    b.m3();        // ✅ Now accessible
}

// Or use polymorphism instead:
public interface Runnable {
    void run();    // Both A and B implement
}
```

---

**Pitfall 3: Forgetting that field access is NOT polymorphic**

❌ **Wrong approach:**
```java
class A {
    public String name = "A";
}

class B extends A {
    public String name = "B";  // Shadows parent field
}

A a0 = new B();
System.out.println(a0.name);  // Prints: "A" ❌ NOT "B"!
```
**Why it fails:** Fields are accessed based on reference type, NOT object type. Only methods are polymorphic.

✅ **Right approach:**
```java
class A {
    public String getName() { return "A"; }
}

class B extends A {
    @Override
    public String getName() { return "B"; }
}

A a0 = new B();
System.out.println(a0.getName());  // ✅ Prints: "B" (method is polymorphic)
```

---

## 🛑 When NOT to Rely on Runtime Polymorphism

1. **When you need compile-time type safety** → Use generics, not casts
2. **For field access** → Fields aren't polymorphic, use getters
3. **When you need guaranteed parent behavior** → Call `super.method()` explicitly
4. **In critical performance paths** → Polymorphism has JIT overhead (usually minimal)

---

## Quick Checklist

- ✅ Reference type = Type of variable (controls what's visible at compile-time)
- ✅ Object type = Actual class instance created with `new`
- ✅ **Methods execute based on OBJECT type (Runtime Binding)**
- ✅ **Compile errors based on REFERENCE type**
- ✅ Methods must exist in parent to use through parent reference
- ✅ Only methods are polymorphic, NOT fields
- ✅ This is the foundation of OOP design
- ✅ Enables writing flexible, maintainable code

---

**Last Updated:** February 28, 2026
