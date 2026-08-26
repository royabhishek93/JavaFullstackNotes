# 🎯 Method Overloading in Java - Senior Interview Guide (2026)

**Ranked by Interview Importance**

> **Master ambiguous method overloading scenarios** that trip up most developers
> 
> **Study time:** 20-30 minutes | **Interview frequency:** 60% of senior Java interviews

---

## Interview Importance Ranking

| Rank | Topic | Importance | Why |
|------|-------|-----------|-----|
| 1 | Q1: Basics | 95% 🔥 | Foundation everyone asks |
| 2 | Q5: Widening vs Boxing | 90% 🔥 | Most tested in real interviews |
| 3 | Q9: Resolution Process | 85% 🔥 | Shows deep understanding |
| 4 | Q10: Priority Rules | 85% 🔥 | Practical knowledge needed |
| 5 | Q2: Null Parameters | 75% ✅ | Common interview scenario |
| 6 | Q6: Widen+Box Conflict | 70% ✅ | Testing edge case knowledge |
| 7 | Q3: Competing Null | 65% ✅ | Tests compilation understanding |
| 8 | Q7: Varargs Priority | 60% ✅ | Real-world gotcha |
| 9 | Q8: Ambiguous Varargs | 50% 👍 | Less common edge case |
| 10 | Q4: Deep Inheritance | 45% 👍 | Rare scenario |

---

## 🎯 How to Use for Your Interview

1. **Master Q1-Q4** (top priorities) - Study these thoroughly
2. **Know Q5-Q8** - Review these situations
3. **Reference Q9-Q10** - Edge cases (nice to know)
4. **Practice explaining** out loud (interviews are spoken!)

---

---

## Q1: What is Method Overloading? (95% - MUST KNOW)

### Problem
Understanding the basics - what exactly counts as method overloading vs. just naming methods differently.

### Why It Happens
Java allows **multiple methods with the same name in one class** if they have different parameter lists. This lets you write cleaner code with fewer method names.

### ❌ Wrong Understanding
```java
class Bank {
    public double getBalance() { 
        return 1000; 
    }
    
    // Not overloading - different method name!
    public double getBalance2() { 
        return 2000; 
    }
}
```

### ✅ Correct Understanding
```java
class Bank {
    // Same name, different parameters = OVERLOADING
    public double getBalance(int accountId) {
        return 1000;
    }
    
    public double getBalance(int accountId, String currency) {
        return 1000 * getExchangeRate(currency);
    }
    
    public List<Double> getBalance(String customerName) {
        return fetchAllAccountsForCustomer(customerName);
    }
}
```

### Methods Differ By:
1. **Number of parameters** - `add(int, int)` vs `add(int, int, int)`
2. **Type of parameters** - `add(int, int)` vs `add(double, double)`
3. **Sequence of types** - `test(String, Object)` vs `test(Object, String)`

### Interview Tip (Say This in Interview)
"Method overloading allows multiple methods with the same name if they have different parameter lists. The difference can be in number, type, or sequence of parameters. This is compile-time polymorphism - the compiler decides which method to use based on the arguments you pass."

### Quick Checklist
- ✅ Same method name required
- ✅ Different parameter list (number, type, or sequence)
- ✅ Return type does NOT matter for overloading
- ✅ Exception types do NOT matter for overloading
- ✅ Can exist in same class or inherited class

---

## Q5: Widening vs Boxing - Widening Always Wins (90% - MOST TESTED)

### Problem
When you pass a primitive number, does Java widen the type or box it?

### Code Scenario
```java
class Demo {
    public void test(long lng) {
        System.out.println("Long (widened)");
    }
    
    public void test(Integer integer) {
        System.out.println("Integer (boxed)");
    }
    
    public static void main(String[] args) {
        Demo d = new Demo();
        d.test(1);  // Which gets called?
    }
}
```

### Why It Happens
**Java's Priority: Exact → Widening → Boxing → Varargs**

- Argument `1` is type `int`
- `test(long)` requires widening: int→long (PRIORITY 2)
- `test(Integer)` requires boxing: int→Integer (PRIORITY 3)
- **Widening has HIGHER priority**
- Winner: `test(long)`

```
Priority (from highest to lowest):
1. Exact match (no conversion)
2. Widening (int→long, char→int)
3. Boxing (int→Integer, char→Character)
4. Varargs (lowest priority)
     ↓
  Widening beats Boxing!
```

### ❌ Wrong Thinking
```java
// "Integer wrapper is more specific than long"
// WRONG! Widening has higher priority!

d.test(1);
// Actual output: Long (widened)
```

### ✅ Correct Output
```
Long (widened)
```

### Interview Tip (Say This)
"Java prioritizes method resolution by: exact match, then widening, then boxing, then varargs. Widening ALWAYS beats boxing. So when you pass `1`, it will widen to `long` rather than box to `Integer`, even if boxing seems more 'natural'."

### Quick Checklist
- ✅ Widening: int→long, char→int, byte→int (primitive type hierarchy)
- ✅ Boxing: int→Integer, char→Character (primitive→wrapper)
- ✅ **Widening has higher priority than boxing**
- ✅ Exact match beats both
- ✅ Varargs is lowest priority

**Widening conversions allowed:**
```
byte→short→int→long→float→double
```

---

## Q9: Three-Step Method Resolution Process (85% - DEEP UNDERSTANDING)

### Problem
Understanding the three phases Java uses to resolve method calls.

### Why It Happens
Java's method resolution is strict and happens in three phases (from Java Language Specification):

**PHASE 1:** Without any conversion (widening, boxing, varargs)
- Looks for exact matches only
- If method found → use it
- If NOT found → go to PHASE 2

**PHASE 2:** With boxing and unboxing (but NOT varargs)
- Allows int→Integer, char→Character etc
- Allows unboxing Integer→int
- If method found → use it
- If NOT found → go to PHASE 3

**PHASE 3:** With boxing/unboxing AND varargs
- Allows all of PHASE 2 plus varargs
- If method found → use it
- If NOT found → COMPILE ERROR

### Code Scenario
```java
class Demo {
    public void test(char i, Character j) {
        System.out.println("method 1");
    }
    
    public void test(Character i, Character j) {
        System.out.println("method 2");
    }
    
    public static void main(String[] args) {
        Demo d = new Demo();
        d.test('a', 'a');  // ERROR! Why?
    }
}
```

### Why It's Ambiguous
```
PHASE 1: test('a', 'a')
  - First arg: char matches 'a' in method 1 ✓
  - Second arg: 'a' is char, needs Character... ✗
  - No PHASE 1 match → PHASE 2

PHASE 2: test('a', 'a') with boxing
  - Method 1: char and Character ✓ MATCH!
  - Method 2: Character and Character ✓ MATCH!
  - Both match! AMBIGUOUS! → ERROR
```

### Interview Tip (Say This)
"Java resolves method calls in three strict phases: 1) No conversion, 2) Boxing/unboxing only, 3) Plus varargs. If a method matches in an earlier phase, later phases aren't checked. If multiple methods match in the same phase, it's an ambiguous call error."

### Quick Checklist
- ✅ Phase 1: Exact match only
- ✅ Phase 2: Add boxing/unboxing
- ✅ Phase 3: Add varargs
- ✅ Earlier phase blocks later phases
- ✅ Multiple matches in same phase = ERROR

---

## Q10: Priority Rules - Complete Ranking (85% - PRACTICAL KNOWLEDGE)

### Problem
Remembering the complete priority order for method resolution.

### The Complete Priority Ranking

```
PRIORITY 1: Exact Match
     - int to test(int) ✓

PRIORITY 2: Widening
     - int to test(long) ✓
     - char to test(int) ✓
     - byte to test(short) ✓

PRIORITY 3: Boxing
     - int to test(Integer) ✓
     - char to test(Character) ✓

PRIORITY 4: Widening + Boxing
     - int to test(Number) via Integer ✓
     - byte to test(Object) via Byte ✓

PRIORITY 5: Varargs
     - int to test(int...) ✓
     - Last resort!
```

### Code Example - Showing Priority
```java
class Demo {
    public void test(int exact) {
        System.out.println("1. Exact");
    }
    
    public void test(long widening) {
        System.out.println("2. Widening");
    }
    
    public void test(Integer boxing) {
        System.out.println("3. Boxing");
    }
    
    public void test(int... varargs) {
        System.out.println("5. Varargs");
    }
    
    public static void main(String[] args) {
        Demo d = new Demo();
        d.test(5);  // Which gets called?
    }
}

// Output: 1. Exact
// Because exact match is highest priority
```

### Interview Tip (Say This)
"Method resolution priority is: Exact Match (highest) > Widening > Boxing > Varargs (lowest). Java always tries exact match first. Only if no exact match exists does it consider wider conversions. This priority system ensures backward compatibility while supporting newer features."

### Quick Checklist
- ✅ High priority methods chosen first
- ✅ Exact match always beats everything
- ✅ Widening beats boxing
- ✅ Boxing beats varargs
- ✅ Varargs is absolute last resort

---

## Q2: Null Parameter - Which Method Wins? (75% - COMMON SCENARIO)

### Problem
When you pass `null` to an overloaded method, how does Java know which method you want to call?

### Code Scenario
```java
class Demo {
    public void test(String str) {
        System.out.println("String");
    }
    
    public void test(Object obj) {
        System.out.println("Object");
    }
    
    public static void main(String[] args) {
        Demo d = new Demo();
        d.test(null);  // Which prints? String or Object?
    }
}
```

### Why It Happens
**Java's rule: Pick the MOST SPECIFIC class in inheritance chain**

- `null` can be assigned to ANY reference type
- Both `test(String)` and `test(Object)` are valid
- But `String` extends `Object` → `String` is more specific
- `null` is closest match for `String` than for `Object`

```
Inheritance hierarchy:
    Object (generic)
      ↑
    String (more specific) ← null matches this better
```

### ❌ Wrong Thinking
```java
// "Object is the superclass, so it must be Object version"
// WRONG! Compiler picks MORE specific class!
d.test(null);  
// Actual output: String
```

### ✅ What Actually Happens
```java
d.test(null);  
// Output: String
// Because String is more specific than Object
```

### Interview Tip (Say This)
"When `null` is passed to overloaded methods, the compiler chooses the MOST SPECIFIC method based on inheritance hierarchy. If `String` and `Object` both can accept null, `String` wins because it's more specific - it extends Object."

### Quick Checklist
- ✅ `null` is assignable to any reference type
- ✅ Compiler always picks **most specific** type
- ✅ Specificity = lower in inheritance tree
- ✅ String is more specific than Object
- ✅ If no clear winner → compile error

---

## Q6: Cannot Widen AND Box - Compiler Error (70% - EDGE CASE)

### Problem
When the only way to match requires BOTH widening AND boxing, Java doesn't allow it.

### Code Scenario
```java
class Demo {
    public void test(Character c) {
        System.out.println("Character");
    }
    
    public void test(Integer i) {
        System.out.println("Integer");
    }
    
    public void test(Object o) {
        System.out.println("Object");
    }
    
    public static void main(String[] args) {
        Demo d = new Demo();
        byte b = 10;
        d.test(b);  // Which gets called?
    }
}
```

### Why It Happens
**Java's rule: Cannot widen THEN box (but CAN box THEN widen)**

- Argument `b` is type `byte`
- To call `test(Integer)`: need byte→int→Integer (widen THEN box) ✗ NOT ALLOWED
- To call `test(Character)`: need byte→char→Character (widen THEN box) ✗ NOT ALLOWED
- To call `test(Object)`: need byte→int→Integer→Object (box THEN widen) ✓ ALLOWED
- Winner: `test(Object)`

```
Timeline of conversions:
byte→int (widen) then Integer (box) ✗ NOT ALLOWED
     ↓
byte→int→Integer (box) then Object (widen) ✓ ALLOWED
     ↓ (Java picks this!)
```

### ❌ Wrong Thinking
```java
// "Integer is the most specific wrapper"
// WRONG! Can't widen then box!

d.test(b);
// Actual output: Object
// Because Object follows the 'box then widen' rule
```

### ✅ What Actually Happens
```
Object
```

### Interview Tip (Say This)
"Java has a strict rule: you CANNOT widen and then box. So `byte` to `Integer` is not allowed (would be widen→box). But Java CAN box first then widen, so `byte` to `Object` works (box→widen). In ambiguous cases, Java follows this strict rule."

### Quick Checklist
- ✅ Cannot do: Widen THEN Box
- ✅ CAN do: Box THEN Widen
- ✅ Example not allowed: byte→int→Integer
- ✅ Example allowed: byte→Byte→Object
- ✅ Restrictions help maintain compatibility

---

## Q3: Competing Null at Same Hierarchy Level (65% - COMPILATION RULE)

### Problem
When two classes are NOT related (same level), passing null becomes ambiguous.

### Code Scenario
```java
class Demo {
    public void test(String str) {
        System.out.println("String");
    }
    
    public void test(StringBuffer sb) {
        System.out.println("StringBuffer");
    }
    
    public static void main(String[] args) {
        Demo d = new Demo();
        d.test(null);  // ERROR! Ambiguous!
    }
}
```

### Why It Happens
**String and StringBuffer are NOT related:**

- Both are independent classes
- Both extend `Object` at same level
- Neither is more specific than the other
- `null` could match either one equally
- Compiler cannot decide!

```
Hierarchy (no clear winner):
      Object
       / \
    String  StringBuffer ← Both equally valid!
      ↑    ↑
    null could go either way!
```

### ❌ Wrong Thinking
```java
// "String was declared first, so it will be chosen"
// WRONG! Declaration order doesn't matter!

d.test(null);
// COMPILE ERROR - not runtime choice!
```

### ✅ What Actually Happens
```
Compile Error: 
  The method test(String) is ambiguous for type Demo
```

### Interview Tip (Say This)
"When two methods' parameter types are at the SAME level in inheritance hierarchy, passing `null` creates an ambiguous call. The compiler cannot determine which is more specific, so it throws a compile-time error immediately. You must fix this with explicit type casting."

### Quick Checklist
- ✅ Same hierarchy level = ambiguous with null
- ✅ Different inheritance branches = ambiguous
- ✅ Error happens at COMPILE time (not runtime!)
- ✅ Use explicit casting to fix: `d.test((String) null);`
- ✅ Not a runtime decision

---

## Q7: Varargs - Lowest Priority (60% - REAL-WORLD GOTCHA)

### Problem
When varargs methods are overloaded, they have the LOWEST priority.

### Code Scenario
```java
class Demo {
    public void test(char c) {
        System.out.println("char");
    }
    
    public void test(char... chars) {
        System.out.println("varargs");
    }
    
    public static void main(String[] args) {
        Demo d = new Demo();
        d.test('a');  // Which gets called?
    }
}
```

### Why It Happens
**Varargs were added in Java 5. Low priority for backward compatibility.**

- Priority: Exact → Widening → Boxing → **Varargs (lowest)**
- Argument `'a'` is type `char`
- `test(char)` is an exact match (PRIORITY 1)
- `test(char...)` is varargs (PRIORITY 4)
- Exact match beats varargs
- Winner: `test(char)`

```
Priority order:
1. Exact match ← 'a' matches char exactly!
2. Widening
3. Boxing
4. Varargs ← this is lowest
```

### ❌ Wrong Thinking
```java
// "Varargs is more flexible, so it might be chosen"
// WRONG! Varargs is LOWEST priority!

d.test('a');
// Actual output: char (exact match)
```

### ✅ Correct Output
```
char
```

### Real Example - Varargs Gets Called
```java
class Demo {
    public void test(char... chars) {
        System.out.println("varargs");
    }
    
    public static void main(String[] args) {
        Demo d = new Demo();
        d.test('a', 'b');  // No single-char match!
    }
}

// Output: varargs
// Because no exact match for two arguments
```

### Interview Tip (Say This)
"Varargs has the absolute lowest priority for method resolution. Varargs were added late in Java 5, so they were given lowest priority for backward compatibility. If any other method matches (exact, widening, or boxing), that method will be chosen instead of varargs."

### Quick Checklist
- ✅ Varargs = lowest priority always
- ✅ Exact match beats varargs
- ✅ Widening beats varargs
- ✅ Boxing beats varargs
- ✅ Varargs only chosen as last resort

---

## Q8: Ambiguous Varargs - Compile Error (50% - LESS COMMON EDGE CASE)

### Problem
When varargs methods compete at same priority, you get ambiguous call.

### Code Scenario
```java
class Demo {
    public void test(int... args) {
        System.out.println("int varargs");
    }
    
    public void test(Integer... args) {
        System.out.println("Integer varargs");
    }
    
    public static void main(String[] args) {
        Demo d = new Demo();
        d.test(1);  // ERROR! Ambiguous!
    }
}
```

### Why It Happens
**Both varargs methods are equally valid:**

- Argument `1` is type `int`
- `test(int...)` requires no conversion (exact for primitives)
- `test(Integer...)` requires boxing: int→Integer
- Both could work!
- Java cannot decide
- ERROR!

### ❌ Wrong Thinking
```java
// "int... is more direct than Integer..."
// WRONG! Both are equally valid!

d.test(1);
// COMPILE ERROR - both work equally!
```

### ✅ What Actually Happens
```
Compile Error:
  The method test(int[]) is ambiguous for type Demo
```

### Interview Tip (Say This)
"When you have competing varargs methods like `test(int...)` and `test(Integer...)`, passing a single argument creates ambiguity. Both methods are equally valid - one requires no conversion, the other requires boxing. Since neither is clearly better, the compiler throws an ambiguous method call error."

### Quick Checklist
- ✅ Multiple varargs methods can be ambiguous
- ✅ int[] vs Integer[] at same level = ambiguous
- ✅ Compiler cannot decide between them
- ✅ Use explicit casting to Fix: `d.test((int[]) new int[]{1});`
- ✅ Or pass multiple args: `d.test(1, 2, 3);`

---

## Q4: Deep Inheritance Chain - Null Method Resolution (45% - RARE SCENARIO)

### Problem
With a 3-level inheritance hierarchy (A extends B extends C), which method gets called with null?

### Code Scenario
```java
class A {}
class B extends A {}
class C extends B {}

class Demo {
    public void test(B obj) {
        System.out.println("B");
    }
    
    public void test(C obj) {
        System.out.println("C");
    }
    
    public static void main(String[] args) {
        Demo d = new Demo();
        d.test(null);  // B or C?
    }
}
```

### Why It Happens
**Rule: Pick the LOWEST (deepest) class in hierarchy**

- Both methods can accept `null`
- `C` is LOWER/DEEPER than `B`
- Lower = more specific
- `C` wins!

```
Hierarchy (bottom = most specific):
    A (root)
    ↑
    B  ← test(B)
    ↑
    C  ← test(C) WINS! (lowest/deepest)
    ↑
   null
```

### ❌ Wrong Thinking
```java
// "B is declared first, so test(B) is called"
// WRONG! Hierarchy determines specificity!

d.test(null);
// Actual output: C (it's deepest)
```

### ✅ Correct Output
```
C
```

### Interview Tip (Say This)
"When resolving null in a deep inheritance chain, the compiler picks the LOWEST class in the hierarchy. 'Lowest' means deepest - so if you have A→B→C, then 'C' is lowest and most specific. Declaration order doesn't matter."

### Quick Checklist
- ✅ `null` matches all types in hierarchy
- ✅ Compiler picks the LOWEST/DEEPEST level
- ✅ Lower = extends more classes
- ✅ Not based on declaration order
- ✅ Clear hierarchy = no ambiguity

---

## Interview Tips Summary

### When Interviewer Asks "Explain Method Overloading"
✅ "Same method name, different parameters - number, type, or sequence"  
✅ "Compiler decides which to call based on argument types"  
✅ "This is compile-time polymorphism"  
✅ "Return type doesn't matter"

### When They Ask "What About Null?"
✅ "Compiler picks the MOST SPECIFIC type"  
✅ "If no clear hierarchy - compile error"  
✅ "String more specific than Object"

### When They Ask "Which Has Priority?"
✅ "Exact > Widening > Boxing > Varargs"  
✅ "Widening beats boxing"  
✅ "Cannot widen then box"  
✅ "Can box then widen"

### When They Ask "What About Ambiguity?"
✅ "Same hierarchy level + null = ambiguous"  
✅ "Different branches at same level = ambiguous"  
✅ "Compile error, not runtime"  
✅ "Use explicit casting to fix"

---

## Quick Reference - Common Patterns

| Pattern | Output | Why |
|---------|--------|-----|
| `test(null)` when `test(String)` and `test(Object)` | String | More specific |
| `test(1)` when `test(long)` and `test(Integer)` | long | Widening > Boxing |
| `test(1)` when `test(int)` and `test(int...)` | int | Exact > Varargs |
| `test(null)` when `test(String)` and `test(StringBuffer)` | ERROR | Same level |
| `test(b)` where b=byte, `test(Integer)` available | Object | Can box+widen, not widen+box |

---

**Last Updated:** February 22, 2026  
**Difficulty Level:** Senior/Staff Engineer  
**Interview Frequency:** 60%+ of Java interviews  
**Study Time:** 20-30 minutes  
**Ordered By:** Interview importance (95% → 45%)
