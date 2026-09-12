# Java Reflection — Inspecting and Modifying Classes at Runtime

## What is this? (Plain English)

Reflection lets your running Java program look inside any class — its fields, methods, and constructors — and even change or invoke them, all *while the program is executing*, without you having written that code at compile time.

**Real-world analogy:** think of a sealed box (an object) with a label on the outside (its public API). Normally you can only use what's printed on the label — the public methods and fields. Reflection is like having an X-ray machine: you can point it at the box and see everything inside — including the parts that were never meant to be visible from outside (private fields, private methods, even a private constructor) — and you can reach in and rearrange those internal parts directly, bypassing the label entirely.

## The Problem It Solves

Reflection answers two needs:
1. **Examine a class at runtime** — find out what methods, fields, constructors, modifiers, return types, and parameters a class has, without knowing any of that in advance at compile time.
2. **Change the behavior of a class at runtime** — read or overwrite the values of its fields (its "behavior" depends on its field values), and invoke its methods or constructors dynamically, based on information (like a class name or method name) obtained only while the program is running.

This is why frameworks and tools that need to work generically with classes they've never seen before (e.g. reading annotations, wiring objects, serializing fields) rely on reflection — but it comes at the cost of speed and encapsulation, discussed below.

## How Reflection Works

Every class loaded by the JVM gets exactly one associated `Class` object, created automatically by the JVM the moment the class is loaded. This `Class` object holds all the metadata about that class — its fields, methods, constructors, modifiers, etc. — and exposes "get" methods to query that metadata. Reflection always starts by obtaining this `Class` object, then drilling down into fields, methods, or constructors from there.

```
Class Bird (source code) --> JVM loads the class --> JVM creates ONE Class object
                                                       (holds metadata: fields, methods,
                                                        constructors, modifiers)
                                                              ^
        Three ways to obtain it:                              │
        Class.forName("Bird")  ─────────────────────────────────────────────────┤
        Bird.class              ─────────────────────────────────────────────────┤
        birdObj.getClass()      ───────────────────────────────────────────────┘
                                                              │
              ┌────────────────────────┬───────────────────────────────────────┐
              v                           v                                    v
   getFields()/getDeclaredFields()  getMethods()/getDeclaredMethods()  getDeclaredConstructors()
              │                           │                                    │
              v                           v                                    v
       Field public? ──Yes──> field.get(obj)/set(obj,value)    Method public? ──Yes──> method.invoke(obj,args...)
              │No, private                        ^                    │No, private              ^
              v                                    │                    v                          │
   field.setAccessible(true) ───────────────┘         method.setAccessible(true) ───────┘

                                                        Constructor public? ──Yes──> constructor.newInstance(args...)
                                                              │No, private                    │
                                                              v                                v
                                              constructor.setAccessible(true) ─────────────────┘
                                                                                                 │
                                                                                                 v
                                                            New object instance created
                                                       (even from a private constructor
                                                            -> breaks Singleton)
```
*(Full Mermaid source: see [mermaid-diagrams.md](mermaid-diagrams.md))*

All the reflection types used here (`Class`, `Field`, `Method`, `Constructor`) live in the `java.lang.reflect` package.

### Three ways to get a `Class` object

| Approach | Example | When you'd use it |
|---|---|---|
| `Class.forName(String)` | `Class.forName("Eagle")` | You only have the class name as a `String` (e.g. read from config) |
| `.class` literal | `Eagle.class` | You already have the class type available in code |
| `.getClass()` on an instance | `eagleObj.getClass()` | You already have an object and want its runtime class |

### `getX()` vs `getDeclaredX()`

- `getFields()` / `getMethods()` — return only **public** members, including ones **inherited from superclasses** (e.g. `Object`'s `wait()`, `notify()`, etc. show up when reflecting methods).
- `getDeclaredFields()` / `getDeclaredMethods()` / `getDeclaredConstructors()` — return **all members declared directly in that class** (public *and* private), but **not** inherited ones from the superclass.

## Key Code / Config

```java
import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.lang.reflect.Method;

public class Eagle {
    public String breed;
    private boolean canSwim;

    private Eagle() {
        // private constructor
    }

    public void fly(int count, boolean fast, String note) {
        System.out.println("Flying " + count + " times, fast=" + fast + ", note=" + note);
    }

    private void eat() {
        System.out.println("Eating");
    }
}
```

```java
public class ReflectionDemo {

    public static void main(String[] args) throws Exception {

        // ---- 1. Get the Class object (three equivalent ways) ----
        Class<?> eagleClass = Class.forName("Eagle");   // by name
        // Class<?> eagleClass = Eagle.class;            // by literal
        // Class<?> eagleClass = someEagleObj.getClass(); // from an instance

        System.out.println("Name: " + eagleClass.getName());
        System.out.println("Modifiers: " + eagleClass.getModifiers());

        // ---- 2. Reflect methods ----
        // getMethods() -> only public methods, including inherited ones (e.g. from Object)
        for (Method m : eagleClass.getMethods()) {
            System.out.println("Public method: " + m.getName()
                    + ", returnType=" + m.getReturnType()
                    + ", declaringClass=" + m.getDeclaringClass());
        }

        // getDeclaredMethods() -> all methods (public + private) declared in Eagle only
        for (Method m : eagleClass.getDeclaredMethods()) {
            System.out.println("Declared method: " + m.getName());
        }

        // ---- 3. Invoke a method via reflection ----
        Object eagleInstance = eagleClass.getDeclaredConstructor().newInstance();
        Method flyMethod = eagleClass.getMethod("fly", int.class, boolean.class, String.class);
        flyMethod.invoke(eagleInstance, 1, true, "hello");

        // ---- 4. Reflect fields ----
        // getFields() -> only public fields
        for (Field f : eagleClass.getFields()) {
            System.out.println("Public field: " + f.getName() + ", type=" + f.getType());
        }

        // getDeclaredFields() -> all fields (public + private) declared in Eagle
        for (Field f : eagleClass.getDeclaredFields()) {
            System.out.println("Declared field: " + f.getName() + ", type=" + f.getType()
                    + ", modifiers=" + f.getModifiers());
        }

        // ---- 5. Set a public field's value ----
        Field breedField = eagleClass.getDeclaredField("breed");
        breedField.set(eagleInstance, "Eagle Brown");
        System.out.println("breed = " + breedField.get(eagleInstance));

        // ---- 6. Set a private field's value (bypasses encapsulation) ----
        Field canSwimField = eagleClass.getDeclaredField("canSwim");
        canSwimField.setAccessible(true);   // required to touch a private member
        canSwimField.set(eagleInstance, true);
        System.out.println("canSwim = " + canSwimField.get(eagleInstance));

        // ---- 7. Reflect constructors, including a private one ----
        for (Constructor<?> c : eagleClass.getDeclaredConstructors()) {
            System.out.println("Constructor modifiers: " + c.getModifiers());
        }

        // ---- 8. Invoke a private constructor (this is how reflection breaks Singleton) ----
        Constructor<?> privateCtor = eagleClass.getDeclaredConstructor();
        privateCtor.setAccessible(true);          // bypass "private" access check
        Object anotherEagle = privateCtor.newInstance(); // creates a NEW instance despite private ctor
        System.out.println("Created another instance via reflection: " + anotherEagle);
    }
}
```

## Interview Q&A

**Q1: What's the difference between `getFields()`/`getMethods()` and `getDeclaredFields()`/`getDeclaredMethods()`?**
A: `getFields()`/`getMethods()` return only **public** members, and they include members **inherited from superclasses** (e.g. calling `getMethods()` on any class also returns `Object`'s `wait()`, `notify()`, etc.). `getDeclaredX()` returns **all members declared directly in that class** — public and private — but excludes anything inherited from a superclass.

**Q2: How do you read or modify a private field using reflection?**
A: Get the field with `getDeclaredField(name)` (not `getField`, since that only returns public fields), then call `field.setAccessible(true)` to bypass the private-access check, and finally use `field.get(obj)` / `field.set(obj, value)`. Without `setAccessible(true)`, accessing a private member from outside its class throws an `IllegalAccessException`.

**Q3: How does reflection break the Singleton pattern?**
A: A Singleton relies on a **private constructor** so that no other class can call `new` on it directly. But reflection can fetch that constructor via `getDeclaredConstructor()`, call `setAccessible(true)` on it, and then call `newInstance()` — which invokes the private constructor anyway and produces a brand-new object, defeating the "only one instance" guarantee.

**Q4: What are the three ways to get a `Class` object for a given class?**
A: `Class.forName("fully.qualified.ClassName")` (when you only have the name as a string), `ClassName.class` (the class literal, when the type is known at compile time), and `someObject.getClass()` (when you already hold an instance and want its runtime class).

**Q5: Why is reflection generally discouraged / used rarely?**
A: Two main reasons: (1) it **breaks encapsulation** — private fields, private methods, and even private constructors can be accessed or modified from completely unrelated classes, defeating the whole purpose of declaring something private; (2) it's **slower than direct access** — because member resolution (finding the right field/method/constructor by name and matching parameter types) happens at runtime instead of compile time, adding overhead compared to calling something directly.

**Q6: How do you invoke a method with parameters using reflection?**
A: Get the `Method` object with `getMethod(name, paramType1.class, paramType2.class, ...)` (matching by name and parameter types), then call `method.invoke(targetObjectInstance, arg1, arg2, ...)` — passing the object to invoke it on, followed by the actual argument values.
