# String Pool vs Heap: Where Do Strings Live?

**Study Time:** 10-12 minutes | **Frequency:** 75% in interviews | **Difficulty:** ⭐⭐⭐⭐⭐

---

## 🤔 Problem Scenario

Where do these strings actually live in memory?

```java
String s1 = "Hello";           // Where?
String s2 = new String("Hello"); // Where?
String s3 = "Hello";           // Same as s1?
String s4 = new String("Hello"); // Same as s2?

System.out.println(s1 == s2);  // ???
System.out.println(s1 == s3);  // ???
System.out.println(s2 == s4);  // ???
System.out.println(s1.equals(s2)); // ???
```

**Output:**
```
s1 == s2: false
s1 == s3: true
s2 == s4: false
s1.equals(s2): true
```

**Question:** Why? What's the difference between `s1`, `s2`, and `s3`?

---

## 🧠 Key Principle: String Literal vs String Object

### String Literal (s1 = "Hello")

```
Stored in: STRING POOL (part of Heap)
Created: At compile time
Reused: Yes, if same literal exists
Example: String s1 = "Hello";
```

### String Object (s2 = new String(...))

```
Stored in: HEAP (not pool)
Created: At runtime
Reused: No, new object each time
Example: String s2 = new String("Hello");
```

---

## 📊 Memory Visualization

```
JVM Memory Structure:

┌─────────────────────────────────────┐
│         HEAP MEMORY                 │
├─────────────────────────────────────┤
│                                     │
│  ┌──────────────────────────────┐   │
│  │    STRING POOL               │   │
│  │ (built-in space for literals)│   │
│  │  s1─→["Hello"]               │   │
│  │  s3─→(same "Hello")          │   │
│  └──────────────────────────────┘   │
│                                     │
│  ┌──────────────────────────────┐   │
│  │    REGULAR HEAP OBJECTS      │   │
│  │  s2─→[new String("Hello")]   │   │
│  │  s4─→[new String("Hello")]   │   │
│  └──────────────────────────────┘   │
│                                     │
└─────────────────────────────────────┘
```

---

## ✅ Scenario 1: String Literals

```java
String s1 = "Hello";
String s2 = "Hello";
String s3 = "Hello";

System.out.println(s1 == s2);  // true
System.out.println(s2 == s3);  // true
System.out.println(s1 == s3);  // true
```

**Execution:**
```
Step 1: String s1 = "Hello";
  - Compiler checks if "Hello" in String Pool
  - Not found, create and add to pool
  - s1 points to pool location

Step 2: String s2 = "Hello";
  - Compiler checks if "Hello" in String Pool
  - FOUND! Reuse same location
  - s2 points to SAME pool location as s1

Step 3: String s3 = "Hello";
  - FOUND in pool! Reuse
  - s3 points to SAME pool location

Result: s1 == s2 == s3 (all same object)
```

**Memory:**
```
Pool: 0x100 ["Hello"]
s1 → 0x100
s2 → 0x100
s3 → 0x100
```

---

## ✅ Scenario 2: String Objects (new)

```java
String s1 = new String("Hello");
String s2 = new String("Hello");

System.out.println(s1 == s2);     // false
System.out.println(s1.equals(s2)); // true
```

**Execution:**
```
Step 1: String s1 = new String("Hello");
  - 'new' forces creation on heap (NOT pool)
  - Creates OBJECT on heap at location 0x200
  - s1 points to 0x200

Step 2: String s2 = new String("Hello");
  - 'new' forces creation on heap AGAIN
  - Creates NEW OBJECT on heap at location 0x300
  - s2 points to 0x300

Result: s1 == s2 is false (different objects)
        s1.equals(s2) is true (same content)
```

**Memory:**
```
Heap:
0x200: ["Hello"] ← s1
0x300: ["Hello"] ← s2

s1 == s2? false (different addresses)
s1.equals(s2)? true (same content)
```

---

## ✅ Scenario 3: Mixed - Literal vs New

```java
String s1 = "Hello";              // Pool
String s2 = new String("Hello"); // Heap

System.out.println(s1 == s2);     // false (different locations)
System.out.println(s1.equals(s2)); // true (same content)
```

**Memory:**
```
Pool: 0x100 ["Hello"] ← s1
Heap: 0x200 ["Hello"] ← s2

s1 == s2? false (different locations)
s1.equals(s2)? true (same content)
```

---

## ✅ Scenario 4: String Concatenation

```java
String s1 = "Hello";
String s2 = "World";
String s3 = s1 + s2;           // Runtime concatenation
String s4 = "Hello" + "World"; // Compile-time concatenation

System.out.println(s3 == s4);  // false (different objects)
```

**Execution:**
```
Step 1: s3 = s1 + s2;
  - Runtime operation: uses StringBuilder internally
  - Result created on HEAP (not pool)
  - s3 → 0x300 ["HelloWorld"]

Step 2: s4 = "Hello" + "World";
  - Compile-time constant folding
  - Compiler optimizes to "HelloWorld"
  - String literal goes to POOL
  - s4 → 0x100 ["HelloWorld"]

Result: s3 == s4 is false (different locations)
```

---

## ✅ Scenario 5: String.intern()

Force a string to go to the pool:

```java
String s1 = "Hello";            // Pool
String s2 = new String("Hello"); // Heap

System.out.println(s1 == s2);           // false

String s3 = s2.intern();        // Force to pool
System.out.println(s1 == s3);           // true (both in pool)
```

**Execution:**
```
s2.intern() does:
  - Check if "Hello" in pool
  - YES, found (s1 is there)
  - Return reference to pool location
  - s3 now points to pool (same as s1)

Result: s1 == s3 is true
```

**Memory:**
```
Before intern():
Pool: 0x100 ["Hello"] ← s1
Heap: 0x200 ["Hello"] ← s2

After intern():
Pool: 0x100 ["Hello"] ← s1, s3
Heap: 0x200 ["Hello"] ← s2 (garbage if no other refs)
```

---

## ❌ Common Mistakes

### ❌ Mistake 1: Assuming == Checks Content

```java
String s1 = "Hello";
String s2 = new String("Hello");

if (s1 == s2) {  // WRONG
    System.out.println("Same");
} else {
    System.out.println("Different");  // This prints
}

// CORRECT
if (s1.equals(s2)) {
    System.out.println("Same content");  // This prints
}

// == checks reference/identity
// .equals() checks content
```

---

### ❌ Mistake 2: Not Understanding String Immutability

```java
String s = "Hello";
s.concat(" World");  // Creates new string, doesn't modify s

System.out.println(s);  // Still "Hello"

// CORRECT
s = s.concat(" World");

System.out.println(s);  // "Hello World"

// String operations return new strings, don't modify original
```

---

### ❌ Mistake 3: Performance - Concatenation in Loop

```java
// WRONG - Creates new string each iteration
String result = "";
for (int i = 0; i < 1000; i++) {
    result += "a";  // Creates new string, old garbage collected
}

// CORRECT - Use StringBuilder
StringBuilder sb = new StringBuilder();
for (int i = 0; i < 1000; i++) {
    sb.append("a");  // Modifies same object
}
String result = sb.toString();

// Wrong version: O(n²) time
// Correct version: O(n) time
```

---

### ❌ Mistake 4: Comparing StringBuilders with ==

```java
StringBuilder sb1 = new StringBuilder("Hello");
StringBuilder sb2 = new StringBuilder("Hello");

System.out.println(sb1 == sb2);  // false (always false)
System.out.println(sb1.equals(sb2)); // true (different equals impl)

// StringBuilder.equals() returns true if same object
// (doesn't compare content like String.equals())

// Convert to String first if comparing content
System.out.println(sb1.toString().equals(sb2.toString())); // true
```

---

## 🎯 Interview Q&A

### Q1: "Explain == vs equals for strings"

**Answer (30 seconds):**
```
== checks if two references point to the SAME object in memory.
equals() checks if the content/value is the SAME.

String s1 = "Hello";              // Pool
String s2 = new String("Hello");  // Heap

s1 == s2?        false (different locations)
s1.equals(s2)?   true (same content)

ALWAYS use .equals() for String comparison!
```

---

### Q2: "Will this print 'true' or 'false'?"

```java
String s1 = "test";
String s2 = "te" + "st";
System.out.println(s1 == s2);
```

**Answer:**
```
true

Explanation:
"te" + "st" is a compile-time constant folding.
Compiler optimizes it to "test" at compile time.
Both s1 and s2 reference the SAME pool location.

But if it was:
String s1 = "test";
String s2 = "te";
String s3 = s2 + "st";
System.out.println(s1 == s3); // false (runtime concatenation)
```

---

### Q3: "When should you use intern()?"

**Answer:**
```
Rarely - usually for:

1. Comparing strings for equality (performance):
   if (s1.intern() == s2.intern()) { }
   But better: just use .equals()

2. Memory optimization when:
   - Comparing many strings
   - Storing duplicate strings
   - But this is premature optimization

3. Special cases:
   - Legacy code compatibility
   - Working with external data with duplicates

In modern Java:
- intern() is rarely needed
- Use .equals() or .intern() on specific cases
- Let GC handle string management

WARNING: intern() manual management can cause memory leaks (strings won't be GC'd)
```

---

### Q4: "String vs StringBuilder - when to use each?"

**Answer:**
```
STRING - When:
- Content never changes
- Not concatenating in loops
- Used as HashMap key (immutability guarantees)

StringBuilder - When:
- Building strings in loops
- Frequent concatenations
- Performance critical

Example - WRONG (String):
String s = "";
for (int i = 0; i < 10000; i++) {
    s += data[i];  // Creates 10000 strings!
}

Example - CORRECT (StringBuilder):
StringBuilder sb = new StringBuilder();
for (int i = 0; i < 10000; i++) {
    sb.append(data[i]);  // Same object, appended to
}
String s = sb.toString();
```

---

### Q5: "Where are String objects stored in memory?"

**Answer:**
```
Both STRING POOL and HEAP are part of the HEAP memory:

Heap Memory:
├── String Pool (fixed size)
│   └── String literals ("Hello", "World", etc.)
│       └── Compact, interned, reused
└── Regular Heap
    └── Objects created with 'new'
        └── Always new objects

Stack Memory:
└── Variables (references to heap objects)
    └── s1, s2, s3 (just references pointing to heap)

Example:
String s1 = "Hello";           // 'Hello' in pool, s1 on stack
String s2 = new String("Hello"); // new object on heap, s2 on stack

NOTHING is stored on the stack - only REFERENCES (addresses).
```

---

## 📚 String Memory Timeline

```java
// String s1 = "Hello";
// Timeline:
// Compile time: See literal "Hello", add to pool
// Runtime: s1 references pool location

// String s2 = new String("Hello");
// Timeline:
// Compile time: See new keyword, will allocate at runtime
// Runtime: Create new object on heap, 
//          may also add "Hello" to pool (for future literals)

// String s3 = "Hello";
// Timeline:
// Compile time: See literal "Hello", already in pool (from s1)
// Runtime: s3 references existing pool location (same as s1)

Result:
s1 == s3 (both reference pool)
s2 != s1 (heap object vs pool)
```

---

## 💬 Interview Tip (Exact Answer)

"String literals go to the String Pool, so identical literals reuse the same object. `new String()` always creates a new heap object, so `==` differs while `.equals()` matches content. The pool is part of the heap." 

---

## ☑️ Quick Checklist

- Literals reuse the String Pool.
- `new String()` creates a new heap object.
- Use `.equals()` for content, not `==`.
- `intern()` can move or return a pooled reference.
- Prefer `StringBuilder` for loops.

---

## ⚠️ Common Pitfalls

**Pitfall 1: Using `new String()` unnecessarily**
```java
String s = new String("hello"); // Creates pool + heap
```

**Pitfall 2: Comparing strings with `==`**
```java
String a = "hi";
String b = new String("hi");
// a == b is false, use a.equals(b)
```

**Pitfall 3: Overusing `intern()`**
```java
for (String s : bigList) {
  s.intern(); // Adds lookup cost and pressure
}
```

---

## 🛑 When NOT to Worry About the String Pool

- Short-lived local strings
- One-off dynamic strings (API responses, user input)
- Non-repeated values where pooling does not help

## 🔑 Key Takeaways

| Concept | Why Important | Interview Score |
|---------|---------------|-----------------|
| String Pool existence | Fundamental memory knowledge | ⭐⭐⭐⭐⭐ |
| Literal vs new behavior | Critical for == vs equals | ⭐⭐⭐⭐⭐ |
| Reference vs content | Debugging string issues | ⭐⭐⭐⭐⭐ |
| StringBuilder performance | Real-world coding | ⭐⭐⭐⭐ |
| intern() use cases | Edge case knowledge | ⭐⭐⭐ |

---

## ✅ Best Practices

```java
// 1. Use .equals() for content comparison
if (s1.equals(s2)) { }  // ✅
if (s1 == s2) { }       // ❌

// 2. Use StringBuilder for concatenation in loops
StringBuilder sb = new StringBuilder();
for (item : list) {
    sb.append(item);  // ✅
}

// 3. Use String literals for known constants
String status = "ACTIVE";  // ✅ (goes to pool)

// 4. Use String.intern() sparingly (if at all)
// Usually not needed in modern Java

// 5. Remember: Strings are immutable
String s = "Hello";
s + " World";  // Creates new string, doesn't modify s
s = s + " World";  // This reassigns s
```

---

**Priority:** 🔥 MUST KNOW (75% interview frequency)

**Related Topics:**
- [String Immutability in Depth](#)
- [StringBuilder vs StringBuffer](#)
- [Garbage Collection and String Pool](#)

---

**Last Updated:** March 5, 2026
