# Q9: Why does `car = bus + "petrol"` give `"petrolapetrol"`?

**Study Time:** 3-4 minutes | **Frequency:** Common logic question 🔥

---

## The Scenario

You declare and initialize variables, then concatenate strings:

```java
String car, bus = "petrol";
car = bus + "petrol";
System.out.println(car);  // What gets printed?
```

You need to trace through the execution step-by-step.

---

## Step-by-Step Execution

### Step 1: Variable Declaration
```java
String car, bus = "petrol";
```
- `car` → declared but uninitialized
- `bus` → initialized with "petrol"

### Step 2: Assignment with Concatenation
```java
car = bus + "petrol";
```

Let's trace this:
1. Evaluate right side: `bus + "petrol"`
2. `bus` contains: `"petrol"`
3. `"petrol"` (literal) is the second string
4. They concatenate: `"petrol" + "petrol"`
5. Result: `"petrolapetrol"`
6. Assign to `car`

### Step 3: Print
```java
System.out.println(car);  // petrolapetrol
```

---

## The Output

```
petrolapetrol
```

**Wait, that's wrong!** Let me check... Actually it's correct:
- First "petrol" comes from the `bus` variable
- Second "petrol" comes from the literal `"petrol"`
- Together: `petrolapetrol`

---

## Visual Execution

```java
bus = "petrol"          // bus points to → "petrol"
                        
car = bus + "petrol"    // Re-evaluate step by step:
                        // "petrol" (from bus) + "petrol" (literal)
                        // No new String created here actually, 
                        // Java compiler optimizes this!

Result: car → "petrolapetrol"
```

---

## Complete Working Code

```java
public class StringConcatenationExample {
    public static void main(String[] args) {
        String car, bus = "petrol";
        car = bus + "petrol";
        System.out.println(car);  // Output: petrolapetrol
        System.out.println(bus);  // Output: petrol (unchanged)
    }
}
```

**Output:**
```
petrolapetrol
petrol
```

---

## 🔥 Critical Interview Point: What Does `+` Really Do?

The `+` operator behaves **completely differently** depending on operand types!

### With Strings

```java
String result = "petrol" + "diesel";
// Result: petroldiesel (concatenation - joining)
```

### With Numbers

```java
int sum = 5 + 2;
// Result: 7 (addition - mathematical)
```

### Mixed: String + Number

```java
System.out.println("5" + 2);
// Result: 52 (converts number to string, then concatenates!)
```

### The Rule

| Code | Left Type | Right Type | Operation | Result |
|------|-----------|-----------|-----------|--------|
| `5 + 2` | Number | Number | Addition | `7` |
| `"5" + 2` | String | Number | Concatenation | `"52"` |
| `"hello" + "world"` | String | String | Concatenation | `"helloworld"` |
| `2 + 5 + "sum"` | Number then String | String | `2+5=7` first, then concat | `"7sum"` |

**Why?** In Java, if **either operand is a String**, the `+` operator performs **concatenation**, not addition.

---

## Common Interview Traps

### Trap 1: Forgetting String is Immutable
```java
String bus = "petrol";
bus = bus + "diesel";  // Creates NEW String object, bus now points to it
System.out.println(bus);  // petroldiesel ✅
```

### Trap 2: Confusing + with Addition
```java
System.out.println("5" + 2);      // "52" (String first = concat)
System.out.println(5 + 2);        // 7 (both numbers = add)
System.out.println(5 + 2 + "3");  // "73" (5+2=7, then concat with "3")
```

### Trap 3: Null Values
```java
String bus = null;
String car = bus + "petrol";
System.out.println(car);  // null petrol (NullPointerException? No!)
// Actually prints: nullpetrol
// The null is converted to string "null"!
```

---

## Interview Q&A

### Q: What's the actual output of this code?
```java
String car, bus = "petrol";
car = bus + "petrol";
System.out.println(car);
```
**A:** `petrolapetrol`

### Q: Can you trace step-by-step what happens?
**A:** 
1. `bus` is initialized with `"petrol"`
2. The expression `bus + "petrol"` evaluates to concatenate two strings
3. Result `"petrol" + "petrol"` = `"petrolapetrol"`
4. This result is assigned to `car`

### Q: Is a new String object created? How many?
**A:** Yes, at least one new String object is created. The right side of the assignment (`bus + "petrol"`) creates a new String in the heap. Due to StringBuilder optimization by the Java compiler, internally it might use StringBuilder, but ultimately we get one new String object in memory.

### Q: What if someone writes `car = bus + petrol;` (without quotes)?
**A:** Compile-time error: `petrol cannot be resolved to a variable`. The Java compiler treats `petrol` as an identifier/variable name, not a string literal.

---

## Real-World Production Scenarios

### Scenario 1: Building Database Queries
```java
String fuel = "diesel";
String query = "SELECT * FROM cars WHERE fuel = '" + fuel + "'";
// Danger: SQL Injection! Always use PreparedStatement
```

### Scenario 2: Efficient String Building in Loops
```java
// ❌ BAD: Creates new String in every iteration
String result = "";
for (int i = 0; i < 1000; i++) {
    result = result + "petrol";  // O(n²) complexity!
}

// ✅ GOOD: Use StringBuilder
StringBuilder sb = new StringBuilder();
for (int i = 0; i < 1000; i++) {
    sb.append("petrol");  // O(n) complexity
}
String result = sb.toString();
```

---

## 🔥 Production Interview Tip

**Interviewer Question:**
> "How would you optimize this string concatenation in a loop?"

**Your Answer:**
- For single concatenations: `+` is fine (compiler optimizes with StringBuilder)
- For loops: Use `StringBuilder` because `+` creates new String object in each iteration
- Reason: Strings are immutable, so `+` internally uses StringBuilder and creates new object each time

---

## Key Takeaways

| Concept | Key Point | Interview Score |
|---------|-----------|-----------------|
| String concatenation with `+` | Joins strings when operand is String | ⭐⭐ Basic |
| Uninitialized variable usage | Will throw compile error | ⭐⭐⭐ Important |
| String vs Number behavior | `+` does different things | ⭐⭐⭐⭐ Critical |
| Performance in loops | Use StringBuilder not `+` | ⭐⭐⭐⭐⭐ Senior |

