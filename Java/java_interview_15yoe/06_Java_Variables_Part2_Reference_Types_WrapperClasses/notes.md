# Java Reference Types vs Primitives — Wrapper Classes, Autoboxing/Unboxing, and the String Constant Pool

## What is this? (Plain English)

A primitive variable (`int`, `boolean`, etc.) is like writing a number directly on a sticky note you carry with you — the value itself lives in your hand (the stack). A reference variable (an object, a `String`, an array, an interface-typed variable) is instead like a claim ticket for a locker — the ticket lives in your hand, but the actual contents live in a separate storage room (the heap). Handing someone a copy of your claim ticket doesn't give them a new locker — it points to the *same* locker, so if they put something new inside, you'll see it too when you open your own copy of the ticket.

This is exactly how Java implements "pass by value" while still giving you pointer-like behavior: Java always copies the *value* you pass into a method — but when that value is a reference (a claim ticket), copying the ticket still lets both copies point at the same heap object.

## The Problem It Solves

Java has no pointers and no "pass by reference" — every argument passed to a method is passed by value, full stop. So how can a method still modify an object such that the caller sees the change after the method returns (the kind of thing you'd normally need pointers for in C/C++)?

Reference data types solve this: `class`, `String`, `interface`, and `array` variables don't hold the actual data — they hold a reference (an address) to where the data actually lives in heap memory. When you pass such a variable into a method, Java copies the reference by value, but both the original and the copy still point to the same object in the heap. Changing a field through either reference changes the one shared object.

This also explains why wrapper classes (`Integer`, `Character`, `Short`, `Byte`, `Long`, `Float`, `Double`, `Boolean`) exist for the eight primitive types:
1. **Reference capability for primitives** — wrapping a primitive in its wrapper class gives it the same "modify it in one place, see it everywhere" behavior that plain primitives don't have (primitives are copied by value and live on the stack).
2. **Java Collections only work with objects** — `ArrayList`, `HashMap`, and the rest of the Collections framework operate on reference types only. To store an `int` in a collection, you need its wrapper, `Integer`.

## Reference Types and Where They Live: Stack vs Heap

```
STACK (method call frame)                            HEAP
───────────────────────────                            ────

int a = 10 (value stored directly)                   (no reference — value lives directly on stack)

Employee empObject (reference variable)   ──────>   Employee object: employeeId = 10

String s1 (reference variable)            ──────>   [String Constant Pool] 'hello' literal

String s3 (reference variable)            ──────>   new String('hello') object  (separate copy, NOT pool)

Person personRef (interface-typed ref)    ──────>   Engineer object (implements Person) [child impl]

int array arr (reference variable)        ──────>   int array object, size 5

Integer wrapperX (reference variable)     ──────>   Integer object, value 20
         ^                                                        |
         |<── unboxing: Integer to int ─────────────────────────────────────|
         ── autoboxing: int to Integer ────────────────────────────────────>|
```
*(Full Mermaid source: see [mermaid-diagrams.md](mermaid-diagrams.md))*

Key facts from this model:
- **Primitives** (`int`, `boolean`, `float`, ...) store their value directly on the **stack**. When passed to a method, the value is copied; changes inside the method are not visible to the caller once the method returns.
- **Reference types** (`class` objects, `String`, `interface`-typed variables, arrays) store the variable itself on the stack, but that variable only holds a reference (address) to the real object sitting on the **heap**. Copying the reference (e.g. passing it to a method, or assigning it to a second variable) still points at the same heap object — so changes made through any copy of the reference are visible everywhere.
- **String literals** are special: they are stored in a dedicated **String Constant Pool** inside the heap, not as regular heap objects.

## Key Code / Config

### 1. Why reference types behave like "pass by reference" even though Java is pass-by-value

```java
class Employee {
    private int employeeId;

    public int getEmployeeId() { return employeeId; }
    public void setEmployeeId(int employeeId) { this.employeeId = employeeId; }
}

public class ReferenceDemo {

    static void modify(Employee employee) {
        employee.setEmployeeId(20); // changes the shared heap object
    }

    public static void main(String[] args) {
        Employee empObject = new Employee(); // object created in heap; empObject holds a reference to it
        empObject.setEmployeeId(10);

        modify(empObject); // the reference (not the object) is copied into the method

        System.out.println(empObject.getEmployeeId()); // prints 20 - both references point to the same heap object

        // Two references can point to the exact same object:
        Employee obj2 = empObject;
        obj2.setEmployeeId(30);
        System.out.println(empObject.getEmployeeId()); // prints 30 - empObject and obj2 share one object
    }
}
```

### 2. Contrast: primitives are copied by value, changes are NOT visible to the caller

```java
public class PrimitivePassByValueDemo {

    static void modify(int x) {
        x = 20; // only changes the local copy on this method's stack frame
    }

    public static void main(String[] args) {
        int a = 10;
        modify(a);
        System.out.println(a); // still prints 10 - primitives live on the stack and are copied by value
    }
}
```

### 3. Interfaces are reference types too — you can't instantiate one directly

```java
interface Person {
    String profession();
}

class Teacher implements Person {
    public String profession() { return "Teaching"; }
}

class Engineer implements Person {
    public String profession() { return "Software Engineer"; }
}

public class InterfaceReferenceDemo {
    public static void main(String[] args) {
        Person personAsEngineer = new Engineer(); // parent-type reference pointing to a child object - valid
        Person personAsTeacher = new Teacher();   // also valid

        System.out.println(personAsEngineer.profession()); // Software Engineer
        System.out.println(personAsTeacher.profession());  // Teaching

        // Person invalid = new Person(); // COMPILE ERROR - cannot instantiate an interface directly
    }
}
```

### 4. String literals, the String Constant Pool, immutability, and `==` vs `.equals()`

```java
public class StringPoolDemo {
    public static void main(String[] args) {
        String s1 = "hello";        // literal goes into the String Constant Pool
        String s2 = "hello";        // pool already has "hello" - s2 points to the SAME literal as s1
        String s3 = new String("hello"); // new keyword forces creation of a separate object on the heap

        System.out.println(s1 == s2);      // true  - both reference the same pooled literal
        System.out.println(s1.equals(s2)); // true  - same content too

        System.out.println(s1 == s3);      // false - s3 is a distinct heap object, not the pooled literal
        System.out.println(s1.equals(s3)); // true  - content is still equal

        // Strings are immutable: "changing" a string never mutates the pooled literal,
        // it only makes the variable point to a different (possibly new) literal.
        s1 = "world";
        System.out.println(s2); // still prints "hello" - the original literal was never modified
    }
}
```

### 5. Arrays are reference types (1D and 2D)

```java
public class ArrayReferenceDemo {
    public static void main(String[] args) {
        // 1D array - fixed capacity, then fill by index
        int[] arr = new int[5];
        arr[0] = 10;
        arr[3] = 40;

        // 1D array - capacity inferred directly from the provided values
        int[] arr2 = {30, 20, 10, 40, 50};

        // 2D array - 5 rows, 4 columns, default value 0
        int[][] grid = new int[5][4];
        grid[2][2] = 20;
        grid[1][3] = 30;

        // 2D array - inferred from literal values (2 rows, 3 columns)
        int[][] grid2 = {
            {1, 5, 7},
            {4, 2, 3}
        };

        System.out.println(grid2[0][1]); // 5
    }
}
```

### 6. Wrapper classes: autoboxing and unboxing

```java
public class WrapperAutoboxingDemo {
    public static void main(String[] args) {
        int a = 10;
        Integer wrapped = a; // autoboxing: primitive -> wrapper (reference type)

        Integer x = 20;
        int unwrapped = x;   // unboxing: wrapper -> primitive

        System.out.println(wrapped + " " + unwrapped);
    }
}
```

### 7. Constant variables: `static` alone is not enough — you need `static final`

```java
class Config {
    static int employeeId = 10;        // static: shared by all instances, but still mutable

    static final int EMPLOYEE_ID = 10; // static + final: one shared copy, and it can never be reassigned
}

public class ConstantDemo {
    public static void main(String[] args) {
        Config.employeeId = 20; // allowed - static alone does not prevent modification

        // Config.EMPLOYEE_ID = 30; // COMPILE ERROR - final fields cannot be reassigned
    }
}
```

## Interview Q&A

**Q1: Java is strictly pass-by-value. So how can a method modify an object's field and have the caller see the change after the method returns?**
A: The *value* being passed is a reference (an address to a heap object), not the object itself. Java copies that reference by value into the method's parameter, but the copy still points to the same heap object as the original. Modifying a field through either the original or the copied reference changes the one shared object, so both see the update. Primitives don't have this behavior because their actual value (not a reference to it) is what gets copied.

**Q2: Why is `String` classified as a reference type in Java, even though it's built into the language like a primitive?**
A: A `String` variable never holds the text itself — it holds a reference either to a literal sitting in the String Constant Pool or to an object created on the heap via `new String(...)`. Since the variable is only a reference to memory elsewhere, `String` qualifies as a reference (non-primitive) type, just like `class`, `interface`, and array types.

**Q3: What's the difference between `s1 == s2` and `s1.equals(s2)` for strings, and why does `s1 == s3` return false when `s3 = new String("hello")` even though `s1 = "hello"`?**
A: `==` compares whether two references point to the exact same memory location. `.equals()` compares the actual content stored at those locations. `s1` and `s2` (both plain literals `"hello"`) are pooled, so they point to the identical String Constant Pool entry — `==` is true. `s3` was created with `new String("hello")`, which forces a brand-new object on the heap outside the pool, so `s1 == s3` is false even though the content ("hello") is identical and `.equals()` returns true.

**Q4: Why can't you write `new Person()` for an interface, but you can write `Person personRef = new Engineer();`?**
A: An interface only declares a method's signature/blueprint — it has no implementation, so instantiating it directly makes no sense and the compiler rejects it. However, a variable typed as the interface is still just a reference, and a reference of a parent (interface) type is allowed to point to any object of a class that implements it (e.g. `Engineer`, `Teacher`). The reference just needs to be a valid pointer to a fully-implemented child object.

**Q5: Why does Java provide a wrapper class (`Integer`, `Character`, `Short`, `Byte`, `Long`, `Float`, `Double`, `Boolean`) for every one of the eight primitive types?**
A: Two reasons. First, wrapping a primitive gives it reference-type behavior — passed around as a reference, changes are visible across methods, the same benefit primitives lack because they're copied by value on the stack. Second, the entire Java Collections framework (`ArrayList`, `HashMap`, etc.) only works with objects/reference types, never with raw primitives — so to store an `int` in a collection you must use its wrapper, `Integer`.

**Q6: What's the actual difference between autoboxing and unboxing?**
A: Autoboxing is converting a primitive value into its corresponding wrapper object (e.g. `int` → `Integer`). Unboxing is the reverse — converting a wrapper object back into its primitive value (e.g. `Integer` → `int`).

**Q7: If you declare `static int employeeId = 10;` in a class, is that a constant?**
A: No. `static` only means there is a single shared copy across all instances of the class — any instance can still reassign it, changing the value for everyone. To make it a true constant, you must add `final` as well (`static final int EMPLOYEE_ID = 10;`), which makes the single shared copy read-only after initialization — any attempt to reassign it is a compile-time error.
