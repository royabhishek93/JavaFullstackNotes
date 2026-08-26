# Method Overriding and Method Hiding - Complete Interview Guide

**Ranked by Interview Importance for 2026**

**Interview Frequency:** 65% of senior Java interviews  
**Difficulty Level:** Medium-High  
**Study Time:** 25-35 minutes  
**Priority:** 🔥 MUST KNOW (polymorphism foundation)

---

## Interview Importance Ranking

| Rank | Topic | Importance | Why |
|------|-------|-----------|-----|
| 1 | Q1: Static Override | 95% 🔥 | Foundation + trick question |
| 2 | Q5: Variable Polymorphism | 90% 🔥 | Critical concept |
| 3 | Q8: Method Hiding | 85% 🔥 | Separates Junior from Senior |
| 4 | Q2: Null Reference | 80% 🔥 | Common confusion point |
| 5 | Q3: Instance vs Static | 75% ✅ | Compilation rules |
| 6 | Q4: Static vs Instance | 70% ✅ | Compilation rules |
| 7 | Q6: Chained Calls | 70% ✅ | Type resolution |
| 8 | Q7: Static Variables | 65% ✅ | Understanding static |
| 9 | Q9: Serialization | 60% 👍 | Advanced concept |
| 10 | Q10: Missing Constructor | 55% 👍 | Edge case |

---

## Quick Overview

Method Overriding and Method Hiding are critical concepts that separate Junior from Senior Java developers. While they sound similar, they have fundamentally different behaviors:

- **Method Overriding** (instance methods) → Polymorphic behavior, decided at **runtime**
- **Method Hiding** (static methods) → NO polymorphic behavior, decided at **compile time**

This distinction is **interview gold** because it reveals understanding of Java's type system and compilation process.

---

## Q1: Can Static Methods Be Overridden? (95% - MUST KNOW)

### Problem
You see two classes with identical static methods. Are they overriding each other or something else?

```java
class Parent {
    public static void print() {
        System.out.println("Parent");
    }
}

class Child extends Parent {
    public static void print() {
        System.out.println("Child");
    }
}
```

### Why It Happens
Static methods are **not polymorphic** by design. They belong to the class, not instances. Method resolution happens at compile time based on the reference type, not the object type.

### ❌ Wrong Code (Thinking It's Overriding)
```java
Parent parent = new Child();
parent.print();  // Prints "Parent" - NOT "Child"!
// Many developers expect "Child" here (polymorphism)
```

### ✅ Right Code (Understanding Method Hiding)
```java
// Method 1: Direct call (clear what happens)
Parent.print();   // Prints "Parent"
Child.print();    // Prints "Child"

// Method 2: Understand compile-time resolution
Parent parent = new Child();
parent.print();   // Compiler resolves to Parent.print()
                 // At compile time: Parent parent → Parent.print()
                 // NOT Child.print(), even though object is Child

// Method 3: This is method hiding, not overriding
Child child = new Child();
child.print();    // Prints "Child" (because reference type is Child)
```

### Interview Tip
**"Static methods are hidden, not overridden. The compiler replaces the instance reference with the class name for static method calls. This happens at compile time, not runtime, so there's no polymorphic behavior."**

### Quick Checklist
- ✅ Static methods are inherited but NOT overridden
- ✅ Called methods resolve based on **reference type**, not object type
- ✅ Compiler replaces `parent.print()` → `Parent.print()` at compile time
- ✅ This is **method hiding**, not overriding
- ✅ No NullPointerException even if reference is null (compile-time resolution)

---

## Q5: Are Variables Polymorphic? Variable Hiding vs Method Overriding (90% - CRITICAL CONCEPT)

### Problem
Do variables exhibit polymorphic behavior like methods?

```java
class Parent {
    public int var = 10;
    
    public void print() {
        System.out.println("var = " + var);
    }
}

class Child extends Parent {
    public int var = 30;  // Hiding parent's var
    
    public void print() {
        System.out.println("var = " + var);
        System.out.println("super.var = " + super.var);
    }
}

Parent p = new Child();
System.out.println(p.var);  // 10 or 30?
p.print();  // Which var is used?
```

### Why It Happens
Variables are **resolved at compile time** based on the reference type, NOT the object type. Unlike methods (which can be overridden), variables don't participate in polymorphism. This is a design decision to keep field access deterministic and predictable.

### ❌ Wrong Code (Assuming Polymorphism)
```java
Parent p = new Child();
System.out.println(p.var);  // Wrong: expecting 30
// Actual output: 10 (compile-time bound to Parent.var)

Child c = new Child();
c.print();  // Assuming this prints var=30 both times
// Actual: var=40 (if local), var=30 (this.var), var=10 (super.var)
```

### ✅ Right Code (Understanding Compile-Time Binding)
```java
Parent p = new Child();
System.out.println(p.var);  // 10 (reference type is Parent)
// Compiler binds to Parent.var at compile time

Child c = new Child();
System.out.println(c.var);  // 30 (reference type is Child)

// Variables are resolved at COMPILE TIME
// NOT at runtime like methods
```

**Full Example with Scoping:**
```java
class Child extends Parent {
    public int var = 30;  // Hiding
    
    public void print() {
        int var = 40;  // Local variable (highest priority)
        
        System.out.println(var);        // 40 (local)
        System.out.println(this.var);   // 30 (Child's var)
        System.out.println(super.var);  // 10 (Parent's var)
    }
}

Child c = new Child();
c.print();
// Output:
// 40
// 30
// 10
```

### Interview Tip
**"Variables are NOT polymorphic. They're resolved at compile time based on reference type. If `Parent p = new Child()`, then `p.var` accesses Parent's var, not Child's var—even though the object is a Child. This is different from method overriding, which IS polymorphic and resolved at runtime."**

### Quick Checklist
- ✅ Variables don't exhibit polymorphic behavior
- ✅ Variables resolved at COMPILE TIME (reference type)
- ✅ Methods resolved at RUNTIME (object type)
- ✅ Shadowing (variable hiding) is different from overriding
- ✅ Access both using `this.var` and `super.var` when needed
- ✅ Local variables > instance variables > parent variables (scope priority)

---

## Q8: Method Hiding - Static Methods are Inherited (85% - SEPARATES JUNIOR FROM SENIOR)

### Problem
Are static methods inherited by subclasses?

```java
class Parent {
    public static void print() {
        System.out.println("I am Parent");
    }
}

class Child extends Parent {
    // No print() method defined
}

Child.print();  // Works or error?
```

### Why It Happens
Static methods ARE inherited (like instance methods). However, if the subclass defines a method with the same signature, it's **method hiding** (not overriding) because static methods don't participate in polymorphism.

### ❌ Wrong Code (Assuming No Inheritance)
```java
class Child extends Parent {
    // Assuming: Child doesn't have access to print()
}

Child.print();  // Wrong thinking: This should fail
// Actual: Works fine! Inherited static methods are accessible
```

### ✅ Right Code (Understanding Inheritance and Hiding)
```java
// Case 1: Simple inheritance (no hiding)
class Child extends Parent {
    // No print() defined
}
Child.print();  // Works - inherited from Parent
Parent.print();  // "I am Parent"

// Case 2: Method hiding (redefining in subclass)
class Child extends Parent {
    public static void print() {
        System.out.println("I am Child");
    }
}

Parent p = new Parent();
p.print();  // OUTPUT: "I am Parent"

Child c = new Child();
c.print();  // OUTPUT: "I am Child"

Parent pc = new Child();
pc.print();  // OUTPUT: "I am Parent" (NOT "I am Child"!)
// Because static method resolution is based on reference type, not object type

// Direct calls make it clear:
Parent.print();  // "I am Parent"
Child.print();   // "I am Child"
```

**Key Difference: Overriding vs Hiding**
```java
// METHOD OVERRIDING (Instance Methods - Polymorphic):
class Parent {
    public void print() { System.out.println("Parent"); }
}
class Child extends Parent {
    public void print() { System.out.println("Child"); }  // Overrides
}
Parent p = new Child();
p.print();  // OUTPUT: "Child" (polymorphism - runtime resolution)

// METHOD HIDING (Static Methods - Non-polymorphic):
class Parent {
    public static void print() { System.out.println("Parent"); }
}
class Child extends Parent {
    public static void print() { System.out.println("Child"); }  // Hides
}
Parent p = new Child();
p.print();  // OUTPUT: "Parent" (NO polymorphism - compile-time resolution)
```

### Interview Tip
**"Static methods are inherited but can be 'hidden' (not overridden) by subclasses. When a child class provides a static method with the same signature, it hides the parent's method. The key difference from overriding: hidden methods don't participate in polymorphism—the method called is determined by reference type at compile time, not object type at runtime."**

### Quick Checklist
- ✅ Static methods are inherited to subclasses
- ✅ Redefining static method in subclass = method hiding
- ✅ Method hiding is NOT method overriding
- ✅ No polymorphism for static methods
- ✅ Reference type determines which static method is called
- ✅ Direct class calls make behavior clearer: `Parent.print()` vs `Child.print()`

---

## Q2: Static Method Called on Null Reference - Does It Throw NPE? (80% - COMMON CONFUSION)

### Problem
Can I call a static method on a null reference, or does it throw NullPointerException?

```java
Parent parent = null;
parent.print();  // Will this throw NPE?
```

### Why It Happens
Since static methods are resolved at compile time based on reference type, the actual object (null or not) is irrelevant. The compiler transforms the call before runtime even begins.

### ❌ Wrong Code (Assuming Runtime Check)
```java
Parent parent = null;
try {
    parent.print();  // Expected to throw NPE
} catch (NullPointerException e) {
    System.out.println("Caught NPE");  // This won't execute
}
```

### ✅ Right Code (Compile-Time Resolution)
```java
Parent parent = null;
parent.print();  // Prints "Parent" - NO NPE!

// Compiler converts this to:
// Parent.print();  (at compile time)

// At runtime: the null reference is never actually used
System.out.println("No exception thrown");  // Always executes
```

### Interview Tip
**"Static methods bypass the instance completely. The compiler converts instance-based calls to class-based calls at compile time. The reference can be null, dead, or invalid—it doesn't matter because it's never used."**

### Quick Checklist
- ✅ Static method calls on null references do NOT throw NPE
- ✅ Compiler resolves based on reference type, not object
- ✅ Reference value (null or object) is ignored for static methods
- ✅ This is a quirk that confuses many developers
- ✅ Always use `ClassName.staticMethod()` for clarity

---

## Q3: Instance Method in Subclass vs Static in Parent (75% - COMPILATION RULES)

### Problem
What happens when a subclass provides an instance method while the parent has a static method with the same signature?

```java
class Parent {
    public static void print() {
        System.out.println("Parent");
    }
}

class Child extends Parent {
    public void print() {  // Instance method in subclass
        System.out.println("Child");
    }
}
```

### Why It Happens
There's an **ambiguity conflict**:
- Parent has static `print()` (compile-time resolution)
- Child has instance `print()` (runtime resolution/polymorphic)

If this were allowed, `parent.print()` would create confusion:
- Is it resolved at compile time (static behavior)?
- Or at runtime (instance behavior)?

Java **forbids this ambiguity** at compile time.

### ❌ Wrong Code (Causes Compilation Error)
```java
class Child extends Parent {
    public void print() {  // COMPILE ERROR HERE
        // "This instance method cannot override the static method from Parent"
        System.out.println("Child");
    }
}
```

### ✅ Right Code (Make Both Static or Both Instance)
```java
// Option 1: Both static (method hiding)
class Parent {
    public static void print() {
        System.out.println("Parent");
    }
}

class Child extends Parent {
    public static void print() {  // OK - both static
        System.out.println("Child");
    }
}

// Option 2: Both instance methods (method overriding)
class Parent {
    public void print() {  // Changed to instance
        System.out.println("Parent");
    }
}

class Child extends Parent {
    public void print() {  // OK - both instance
        System.out.println("Child");
    }
}
```

### Interview Tip
**"Java prevents mixing static and instance methods with the same signature because the resolution strategies conflict. Static methods use compile-time resolution while instance methods use runtime resolution. Mixing them creates ambiguity that Java won't allow."**

### Quick Checklist
- ✅ Instance method cannot hide/override static method (compile error)
- ✅ The conflict is about mixed resolution strategies
- ✅ Both must be static (hiding) OR both must be instance (overriding)
- ✅ Compiler catches this at compile time (safety feature)
- ✅ Common mistake: forget static keyword in subclass

---

## Q4: Static Method in Subclass vs Instance in Parent (70% - COMPILATION RULES)

### Problem
What happens when a subclass provides a static method while the parent has an instance method with the same signature?

```java
class Parent {
    public void print() {
        System.out.println("Parent");
    }
}

class Child extends Parent {
    public static void print() {  // Static in subclass
        System.out.println("Child");
    }
}
```

### Why It Happens
Again, **ambiguity conflict** (the reverse of Q3):
- Parent has instance `print()` (polymorphic, runtime resolution)
- Child has static `print()` (non-polymorphic, compile-time resolution)

If `parent.print()` could be satisfied by two different resolution strategies, it creates an unsolvable ambiguity.

### ❌ Wrong Code (Causes Compilation Error)
```java
class Child extends Parent {
    public static void print() {  // COMPILE ERROR
        // "This static method cannot hide the instance method from Parent"
        System.out.println("Child");
    }
}
```

### ✅ Right Code (Consistent Resolution Strategy)
```java
// Option 1: Both instance methods (method overriding)
class Parent {
    public void print() {
        System.out.println("Parent");
    }
}

class Child extends Parent {
    public void print() {  // OK - both instance
        System.out.println("Child");
    }
}

// Option 2: Both static methods (method hiding)
class Parent {
    public static void print() {  // Changed to static
        System.out.println("Parent");
    }
}

class Child extends Parent {
    public static void print() {  // OK - both static
        System.out.println("Child");
    }
}
```

### Interview Tip
**"Static methods cannot hide instance methods. The parent's polymorphic behavior (compile-time unresolved) conflicts with the child's static behavior (compile-time resolved). Java requires consistency: either both resolve at compile time (both static) or at runtime (both instance)."**

### Quick Checklist
- ✅ Static method cannot override/hide instance method (compile error)
- ✅ This is the reverse ambiguity of Q3
- ✅ Java enforces resolution strategy consistency
- ✅ Both must use the same strategy
- ✅ This prevents confusing situations at runtime

---

## Q6: Chained Method Calls with Different Return Types (70% - TYPE RESOLUTION)

### Problem
When chaining method calls, what type is used for variable resolution?

```java
class Parent {
    int x = 10;
    
    public Parent getObject() {
        return new Parent();
    }
}

class Child extends Parent {
    int x = 20;
    
    public Child getObject() {
        return new Child();
    }
}

Parent p = new Child();
System.out.println(p.getObject().x);  // 10 or 20?
```

### Why It Happens
The compiler follows this logic:
1. `p` is type `Parent` → Check if `Parent` has `getObject()` ✓
2. Return type of `getObject()` is `Parent`
3. Access `x` on the `Parent` return type → Uses `Parent.x`
4. Result: 10 (compile-time bound to Parent.x)

Even though the actual returned object is a Child, variables are resolved by return type at compile time.

### ❌ Wrong Code (Expecting Polymorphic Binding)
```java
Parent p = new Child();
System.out.println(p.getObject().x);  // Expecting 20
// Actual output: 10 (Parent.x)
// Because return type of getObject() in Parent is Parent
```

### ✅ Right Code (Understanding Return Type Matters)
```java
// Case 1: If you don't override return type
class Parent {
    int x = 10;
    public Parent getObject() { return new Parent(); }
}
class Child extends Parent {
    int x = 20;
    public Parent getObject() { return new Child(); }  // Same return type
}
Parent p = new Child();
System.out.println(p.getObject().x);  // 10 (Parent.x)

// Case 2: If you use covariant return type (Java 5+)
class Parent {
    int x = 10;
    public Parent getObject() { return new Parent(); }
}
class Child extends Parent {
    int x = 20;
    public Child getObject() { return new Child(); }  // Covariant return
}
Parent p = new Child();
System.out.println(p.getObject().x);  // Still 10! (Parent.x)
// Because p is type Parent, so getObject() return type is Parent
// Child's return type only matters if reference is actually Child

Child c = new Child();
System.out.println(c.getObject().x);  // 20 (now references Child.x)
```

### Interview Tip
**"The method can be overridden with covariant return types, but variable access is still bound to the compile-time type. When `Parent p = new Child()` and you call `p.getObject()`, the return type is determined by Parent's signature, so accessing `x` uses Parent's variable, not Child's."**

### Quick Checklist
- ✅ Return type is determined by reference type (compile time)
- ✅ Methods are polymorphic (overridden at runtime)
- ✅ Variables are NOT polymorphic (bound at compile time)
- ✅ Covariant return types are allowed (Java 5+)
- ✅ Chain operations → always use reference type for next step

---

## Q7: Static Variables and Hidden Values (65% - UNDERSTANDING STATIC)

### Problem
When a subclass modifies a static variable inherited from parent, what happens?

```java
class Parent {
    public static int x = 10;
    
    public void print() {
        System.out.println(x);
    }
}

class Child extends Parent {
    public Child() {
        x = 30;  // Modifying static x
    }
}

Parent p = new Child();
System.out.println(p.x);  // What's the value?
p.print();  // Same value?
```

### Why It Happens
Static fields are **shared across the entire inheritance hierarchy**. When Child modifies `x`, it's modifying the **same static variable** that Parent has—not creating a new hidden variable. (Unlike instance variables where Child can shadow Parent's variable.)

### ❌ Wrong Code (Thinking There Are Separate Variables)
```java
class Child extends Parent {
    public Child() {
        x = 30;  // Thinking: creating Child's own x
    }
}

// Mistaken assumption: Parent.x = 10, Child.x = 30
// Reality: There's only ONE x = 30 (shared)
```

### ✅ Right Code (Sharing Static Variables)
```java
class Parent {
    public static int x = 10;
    public void print() {
        System.out.println("x = " + x);
    }
}

class Child extends Parent {
    public Child() {
        x = 30;  // Modifies THE SAME x, not creating new one
    }
}

Parent p = new Child();
System.out.println(p.x);  // 30 (the shared x is modified)
p.print();  // Prints "x = 30" (same x)

// Verification: all references see the same value
Parent parent = new Parent();
System.out.println(parent.x);  // 30 (affected by Child's modification)
```

**Contrast with Instance Variables (True Hiding):**
```java
class Parent {
    public int instanceVar = 10;  // Instance variable
    public static int staticVar = 10;  // Static variable
}

class Child extends Parent {
    public int instanceVar = 30;  // HIDES Parent's instanceVar
    public static int staticVar = 30;  // SHARES Parent's staticVar? NO!
}

// If Child declares static variable with same name:
// It HIDES the Parent's static variable (creates new one)
// But if Child only modifies (no declaration), it modifies parent's
```

### Interview Tip
**"Static variables are not overridden or hidden unless explicitly redeclared. When a child class modifies a static variable inherited from the parent, it modifies the ONE shared variable across the entire hierarchy. This is different from instance variables, where child can create a completely separate variable by hiding parent's."**

### Quick Checklist
- ✅ Static variables are shared, not shadowed (unless redeclared)
- ✅ Modifications in child affect parent's view of the variable
- ✅ This is different from instance variables (which CAN be shadowed)
- ✅ If Child declares static var with same name → creates separate var
- ✅ Multiple references see the same modified value

---

## Q9: Serialization - No Constructor Called During Deserialization (60% - ADVANCED CONCEPT)

### Problem
When deserializing an object, are the constructors called?

```java
class Parent implements Serializable {
    public Parent() {
        System.out.println("Parent Constructor");
    }
}

class Child extends Parent {
    public Child() {
        System.out.println("Child Constructor");
    }
}

// Serialization
Child c = new Child();
// ... serialize c ...

// Deserialization
Child deserializedChild = (Child) ois.readObject();
// Are constructors called?
```

### Why It Happens
Serialization captures the complete object state. During deserialization, the JVM needs to:
1. Restore object structure (class hierarchy)
2. Restore object data (field values)

It does **NOT** call constructors because constructors might throw exceptions or have side effects. Instead, it uses reflection to create objects bypassing constructors.

### ❌ Wrong Code (Expecting Constructor Calls)
```java
Child c = new Child();  // Output: "Parent Constructor" "Child Constructor"
ByteArrayOutputStream baos = new ByteArrayOutputStream();
ObjectOutputStream oos = new ObjectOutputStream(baos);
oos.writeObject(c);

ByteArrayInputStream bais = new ByteArrayInputStream(baos.toByteArray());
ObjectInputStream ois = new ObjectInputStream(bais);
Child deserialized = (Child) ois.readObject();
// Wrong: expecting "Parent Constructor" "Child Constructor" again
// Actual: nothing printed (no constructors called)
```

### ✅ Right Code (Understanding Serialization Mechanism)
```java
// Serialization (constructors called)
Child c = new Child();
// Output: "Parent Constructor" "Child Constructor"

byte[] data = serializeObject(c);  // Captures state

// Deserialization (NO constructors called)
Child deserialized = deserializeObject(data);
// Output: (nothing - no constructors called)

// But object is valid with preserved state
System.out.println(deserialized.getName());  // Fields are restored
```

**More Complex Example: Mixed Serializable/Non-Serializable**
```java
class A {  // Non-serializable (not implementing Serializable)
    protected int a = 10;
    public A() { System.out.println("A Constructor"); }
}

class B extends A {  // Non-serializable
    protected int b = 15;
    public B() { System.out.println("B Constructor"); }
}

class C extends B implements Serializable {  // Serializable!
    protected int c = 25;
    public C() { System.out.println("C Constructor"); }
}

class D extends C {  // Serializable (through C)
    protected int d = 30;
    public D() { System.out.println("D Constructor"); }
}

// Serialization
D d = new D();
// Output: A -> B -> C -> D constructors called
// Fields: a=10, b=15, c=25, d=30

// Deserialization
D deserialized = (D) ois.readObject();
// Output: A -> B constructors called (first non-serializable class)
// But C and D constructors NOT called
// Fields: a=10, b=15, c=25, d=30 (preserved from serialization)

assertTrue(deserialized.getA() == 10);  // ✓
assertTrue(deserialized.getB() == 15);  // ✓
assertTrue(deserialized.getC() == 25);  // ✓ (preserved)
assertTrue(deserialized.getD() == 30);  // ✓ (preserved)
```

### Interview Tip
**"During deserialization, the first non-serializable supertype's no-arg constructor is called (to initialize its fields), but serializable classes' constructors are bypassed. The JVM uses reflection to reconstruct the object without invoking constructors. This is why field initializers in serializable classes are ignored during deserialization."**

### Quick Checklist
- ✅ Serialization calls all constructors (creates object normally)
- ✅ Deserialization calls only first non-serializable class's constructor
- ✅ Serializable classes' constructors are NOT called on deserialization
- ✅ Field values from serialization stream override default initializers
- ✅ This is done via reflection (ReflectionFactory.newConstructorForSerialization)
- ✅ If first non-serializable class lacks no-arg constructor → runtime exception

---

## Q10: Deserialization - Missing No-Arg Constructor in Non-Serializable Parent (55% - EDGE CASE)

### Problem
What happens if the first non-serializable parent class doesn't have a no-arg constructor?

```java
class A {  // Non-serializable (first in hierarchy)
    private int a = 10;
    
    public A(int a) {  // No no-arg constructor!
        System.out.println("A Constructor");
        this.a = a;
    }
}

class B extends A {  // Non-serializable
    private int b = 15;
    public B() {
        super(100);  // Calls A(int)
        System.out.println("B Constructor");
    }
}

class C extends B implements Serializable {
    private int c = 25;
    public C() {
        System.out.println("C Constructor");
    }
}

// Deserialization: Will it work?
```

### Why It Happens
During deserialization, the JVM tries to instantiate the first non-serializable class (A in this case) using its no-arg constructor. If no-arg constructor doesn't exist:
- **Compile time:** No error (the code compiles fine)
- **Runtime:** InvalidClassException when deserializing

This is a runtime check because the discovery happens only during deserialization.

### ❌ Wrong Code (Assuming Compile-Time Error)
```java
// This code compiles fine!
class A {
    public A(int a) { }  // No no-arg constructor
}

class C extends ... implements Serializable { }

// But deserialization fails:
try {
    C c = (C) ois.readObject();
} catch (InvalidClassException e) {
    // Runtime error: "no valid constructor"
}
```

### ✅ Right Code (Providing No-Arg Constructor in First Non-Serializable Class)
```java
// FIX: Add no-arg constructor to first non-serializable class
class A {
    private int a = 10;
    
    public A() {  // No-arg constructor added
        System.out.println("A Constructor");
    }
    
    public A(int a) {
        System.out.println("A Constructor with param");
        this.a = a;
    }
}

class B extends A {
    private int b = 15;
    public B() {
        super();  // Now calls A() no-arg constructor
        System.out.println("B Constructor");
    }
}

class C extends B implements Serializable {
    private int c = 25;
    public C() {
        System.out.println("C Constructor");
    }
}

// Deserialization now works
C deserialized = (C) ois.readObject();  // ✓ No exception
```

**Case: First Non-Serializable Class Has No-Arg, But Parent Does Not**
```java
class A {
    private int a = 10;
    public A(int a) { this.a = a; }  // No no-arg
}

class B extends A {
    private int b = 15;
    public B() {  // No-arg constructor exists
        super(100);
        System.out.println("B Constructor");
    }
}

class C extends B implements Serializable {
    private int c = 25;
}

// Deserialization: Works fine!
// Reason: B is first non-serializable, and B has no-arg constructor
// A's missing no-arg constructor doesn't matter
// (A is not first non-serializable, so its constructor isn't called)
```

### Interview Tip
**"The rule is: the FIRST non-serializable class in the inheritance hierarchy must have a no-arg constructor. This is checked only at runtime during deserialization, so you won't know about the problem until you actually deserialize. If missing, you get InvalidClassException."**

### Quick Checklist
- ✅ First non-serializable class MUST have no-arg constructor
- ✅ This is a **runtime check**, not compile-time
- ✅ Missing no-arg → InvalidClassException during deserialization
- ✅ "First non-serializable" means first class that doesn't implement Serializable
- ✅ Parents of non-serializable classes can have any constructors
- ✅ All serializable classes don't need no-arg constructors

---

## Quick Reference: Key Distinctions

| Aspect | Method Overriding | Method Hiding |
|--------|-------------------|---------------|
| **Type** | Instance methods | Static methods |
| **Resolution** | Runtime (object type) | Compile time (reference type) |
| **Polymorphic** | Yes | No |
| **Example** | `child.print()` → calls Child's method | `parent.print()` → calls Parent's method |
| **Access** | Through inheritance | Through inheritance |
| **Syntax Rule** | Can't mix with static | Can't mix with instance |

---

## Variable Resolution Priority (Local → This → Super)

```java
class Parent {
    int x = 10;
}

class Child extends Parent {
    int x = 20;
    
    void method() {
        int x = 30;  // Local variable
        
        System.out.println(x);        // 30 (local has highest priority)
        System.out.println(this.x);   // 20 (this.x = Child's var)
        System.out.println(super.x);  // 10 (super.x = Parent's var)
    }
}
```

---

## Common Interview Traps

### Trap 1: Expecting Polymorphism with Static Methods
```java
Parent p = new Child();
p.staticMethod();  // Calls Parent's, not Child's!
```

### Trap 2: Visibility of Variables
```java
Parent p = new Child();
p.instanceVar;  // Accesses Parent's var, not Child's!
```

### Trap 3: Null Reference with Static Methods
```java
Parent p = null;
p.staticMethod();  // No NPE! Resolved at compile time
```

### Trap 4: Constructor Inheritance in Serialization
```java
// Serializable subclass - constructors NOT called on deserialization
C c = ois.readObject();  // No constructor calls!
```

### Trap 5: Mixing Static and Instance Methods
```java
class Parent { public static void m() {} }
class Child extends Parent {
    public void m() {}  // COMPILE ERROR!
}
```

---

## Study Checklist

- [ ] Understand method overriding (instance methods, runtime resolution, polymorphic)
- [ ] Understand method hiding (static methods, compile-time resolution, non-polymorphic)
- [ ] Know compile-time errors (mixing static/instance with same signature)
- [ ] Understand variable resolution (compile-time, based on reference type)
- [ ] Variables can be hidden (different from overriding)
- [ ] Static methods are inherited but hide parent's (not override)
- [ ] Static method calls on null references don't throw NPE
- [ ] Serialization calls all constructors; deserialization may not
- [ ] First non-serializable class in hierarchy must have no-arg constructor
- [ ] Priority chain: local variable > `this` > `super`

---

## Related Interview Topics

- **Method Overloading** - Different from overriding (compile-time vs runtime)
- **Polymorphism** - Instance methods achieve it; static methods don't
- **Access Modifiers** - Overridden methods can't reduce visibility
- **Covariant Return Types** - Allowed in method overriding (Java 5+)
- **Serialization Process** - Deep understanding of object reconstruction
- **Inheritance Hierarchy** - How Java walks up the chain
- **Compile-Time vs Runtime** - Core to understanding Java's type system

---

**Last Updated:** February 22, 2026  
**Interview Readiness:** Expert level (staff engineer+)  
**Ordered By:** Interview importance (95% → 55%)  
**Revision Notes:** Comprehensive guide covering all aspects of overriding and hiding with detailed examples and common traps.
