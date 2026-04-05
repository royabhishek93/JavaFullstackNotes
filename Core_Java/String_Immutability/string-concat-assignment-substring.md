# Q10: String Immutability + Concatenation + Substring (Output Prediction)

**Study Time:** 8-10 minutes | **Frequency:** 70% in interviews 🔥 | **Difficulty:** ⭐⭐⭐

---

## Scenario

**Given this code, what is the output and why?**

```java
public class StringFlowDemo {
    public static void main(String[] args) {
        String str1 = "Hey";
        String str2 = new String("Java");
        String str3 = new String(str2.concat("Job"));

        str1.concat(str3);
        str2 = str3;

        System.out.println(str1);
        System.out.println(str2);
        System.out.println(str3);

        String s3 = "JournalDev";
        System.out.println(s3.substring(1, 5));
    }
}
```

---

## Expected Output

```
Hey
JavaJob
JavaJob
ourn
```

---

## Key Principle

- Strings are **immutable**.
- `concat()` returns a **new** String but does **not** modify the original.
- `substring(begin, end)` is **begin inclusive**, **end exclusive**.

---

## Step-by-Step Analysis

### 1) `String str1 = "Hey";`

- Stored in **String pool**
- `str1` → "Hey"

### 2) `String str2 = new String("Java");`

- Creates a **new heap object**
- `str2` → heap("Java")

### 3) `String str3 = new String(str2.concat("Job"));`

- `str2.concat("Job")` → "JavaJob"
- New heap String created
- `str3` → heap("JavaJob")

### 4) `str1.concat(str3);`

- Creates "HeyJavaJob"
- **Not assigned**, so result is discarded
- `str1` still → "Hey"

### 5) `str2 = str3;`

- Both `str2` and `str3` now reference "JavaJob"

---

## Substring Breakdown

```java
String s3 = "JournalDev";
System.out.println(s3.substring(1, 5));
```

Index map:

```
J  o  u  r  n  a  l  D  e  v
0  1  2  3  4  5  6  7  8  9
```

- `substring(1, 5)` → indices **1,2,3,4**
- Output: `ourn`

---

## Variant: "July" Instead of "Job"

```java
String str3 = new String(str2.concat("July"));
str1.concat(str3);
str2 = str3;

System.out.println(str1); // Hey
System.out.println(str2); // JavaJuly
System.out.println(str3); // JavaJuly
```

**Why:** Same immutability rules apply.

---

## Interview Q&A

### Q1: Why doesn't `str1` change after `concat()`?

**Answer:**
```
String is immutable. concat() returns a new String.
If you don't assign it, the original remains unchanged.
```

---

### Q2: Where are these objects stored?

**Answer:**
```
"Hey" is in the String pool.
new String("Java") creates a heap object.
"JavaJob" is a new heap object.
```

---

### Q3: Why does substring use end-exclusive?

**Answer:**
```
To make length calculation easier:
substring(a, b) length = b - a
```

---

## Common Pitfalls

```java
❌ Pitfall 1: Assuming concat mutates the original
str1.concat("X"); // str1 unchanged

❌ Pitfall 2: Off-by-one in substring
substring(1, 5) returns 4 chars, not 5
```

---

## Interview Answer (Concise)

**Q: "What is the output and why?"**

**Answer:**

> "`str1` stays `Hey` because `concat()` creates a new String and the result isn’t assigned. `str3` is `JavaJob` from `str2.concat("Job")`, and after `str2 = str3`, both point to `JavaJob`. `substring(1,5)` on `JournalDev` returns `ourn` because index 1 is inclusive and 5 is exclusive."

---

## Key Takeaways

| Concept | Why It Matters | Interview Score |
|---------|----------------|-----------------|
| String immutability | Explains output | ⭐⭐⭐⭐⭐ |
| Pool vs heap | Memory behavior | ⭐⭐⭐⭐ |
| concat() behavior | Common trick | ⭐⭐⭐⭐⭐ |
| substring indexing | Off-by-one risk | ⭐⭐⭐⭐ |
