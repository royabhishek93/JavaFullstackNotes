# Q65: Find First Non-Repeated Character Using Java 8 (Interview Code)

**Study Time:** 5-7 minutes | **Frequency:** 60% in coding interviews 🔥 | **Difficulty:** ⭐⭐⭐

---

## The Problem

Find the **first character that appears only once** in a string.

```
Input: "abracadabra"
Output: 'c'  (appears only once)

Input: "programming"
Output: 'p'  (first non-repeated)

Input: "aabbcc"
Output: null or empty (all repeated)
```

---

## Wrong Approaches (Common Mistakes)

### ❌ WRONG Approach 1: Nested Loop (O(n²) complexity)

```java
public char findNonRepeatedChar(String str) {
    for (int i = 0; i < str.length(); i++) {
        char c = str.charAt(i);
        boolean isRepeated = false;
        
        for (int j = 0; j < str.length(); j++) {
            if (i != j && str.charAt(j) == c) {
                isRepeated = true;
                break;
            }
        }
        
        if (!isRepeated) {
            return c;
        }
    }
    return '\0';  // Not found
}

// Problems:
// 1. O(n²) time complexity - slow for large strings
// 2. Not using Java 8 features
// 3. Inefficient iteration
```

---

### ❌ WRONG Approach 2: Using HashMap manually (Verbose)

```java
public char findNonRepeatedChar(String str) {
    Map<Character, Integer> charCount = new HashMap<>();
    
    // Count occurrences
    for (char c : str.toCharArray()) {
        charCount.put(c, charCount.getOrDefault(c, 0) + 1);
    }
    
    // Find first non-repeated
    for (char c : str.toCharArray()) {
        if (charCount.get(c) == 1) {
            return c;
        }
    }
    
    return '\0';
}

// Problems:
// 1. Verbose and not idiomatic Java 8
// 2. Two passes through the string
// 3. Manual loop instead of functional approach
```

---

## ✅ RIGHT Approach: Using Java 8 Streams

### Solution 1: Using Stream + LinkedHashMap (Best for Interviews)

```java
public Optional<Character> findNonRepeatedCharacter(String str) {
    return str.chars()
        .boxed()
        .collect(Collectors.groupingBy(
            c -> (char) c.intValue(),
            LinkedHashMap::new,
            Collectors.counting()
        ))
        .entrySet()
        .stream()
        .filter(entry -> entry.getValue() == 1)
        .map(Map.Entry::getKey)
        .findFirst();
}

// Usage:
String input = "abracadabra";
char result = findNonRepeatedCharacter(input).orElse('\0');
System.out.println(result);  // Output: c
```

**Why LinkedHashMap?**
- Maintains insertion order
- `.findFirst()` returns first non-repeated in original string order
- Without it, order would be lost

---

### Solution 2: More Readable Version (Recommended)

```java
public Optional<Character> findNonRepeatedChar(String str) {
    Map<Character, Long> charCounts = str.chars()
        .boxed()
        .collect(Collectors.groupingBy(
            c -> (char) c.intValue(),
            LinkedHashMap::new,
            Collectors.counting()
        ));
    
    return str.chars()
        .boxed()
        .map(c -> (char) c.intValue())
        .filter(c -> charCounts.get(c) == 1)
        .findFirst();
}

// Usage:
String input = "programming";
Optional<Character> result = findNonRepeatedChar(input);
result.ifPresent(c -> System.out.println("First non-repeated: " + c));
// Output: First non-repeated: p
```

---

### Solution 3: Using Collectors.toMap (Alternative)

```java
public Optional<Character> findNonRepeatedCharacter(String str) {
    return str.chars()
        .boxed()
        .collect(Collectors.toMap(
            c -> (char) c.intValue(),
            c -> 1L,
            Long::sum,
            LinkedHashMap::new
        ))
        .entrySet()
        .stream()
        .filter(e -> e.getValue() == 1)
        .map(Map.Entry::getKey)
        .findFirst();
}
```

---

## Step-by-Step Breakdown

### Stream 1: `.chars()` - Convert String to IntStream
```java
"abc".chars()
// Output: [97, 98, 99]  (ASCII values)
```

### Stream 2: `.boxed()` - Convert to Stream<Integer>
```java
.boxed()
// Output: Integer[97], Integer[98], Integer[99]
```

### Stream 3: `.collect(Collectors.groupingBy())` - Count Occurrences
```java
.collect(Collectors.groupingBy(
    c -> (char) c.intValue(),      // Map to character
    LinkedHashMap::new,             // Preserve insertion order
    Collectors.counting()           // Count occurrences
))
// Output: Map: {'a': 1, 'b': 1, 'c': 1}
//         (for "abc" where each appears once)
```

### Stream 4: `.stream()` - Stream the map entries
```java
.entrySet()
.stream()
// Output: Map.Entry(a=1), Map.Entry(b=1), Map.Entry(c=1)
```

### Stream 5: `.filter()` - Keep only count == 1
```java
.filter(entry -> entry.getValue() == 1)
// Output: All entries with value == 1
```

### Stream 6: `.map()` - Extract character
```java
.map(Map.Entry::getKey)
// Output: 'a', 'b', 'c'
```

### Stream 7: `.findFirst()` - Get first match
```java
.findFirst()
// Output: Optional.of('a')
```

---

## Complete Working Code

```java
import java.util.*;
import java.util.stream.Collectors;

public class NonRepeatedCharacter {
    
    // Solution 1: One-liner (Not readable for interview)
    public Optional<Character> findNonRepeated(String str) {
        return str.chars()
            .boxed()
            .collect(Collectors.groupingBy(c -> (char) c.intValue(), 
                LinkedHashMap::new, Collectors.counting()))
            .entrySet().stream()
            .filter(e -> e.getValue() == 1)
            .map(Map.Entry::getKey)
            .findFirst();
    }
    
    // Solution 2: Better readability for interview
    public Optional<Character> findFirstNonRepeatedChar(String str) {
        if (str == null || str.isEmpty()) {
            return Optional.empty();
        }
        
        // Step 1: Count character frequencies
        Map<Character, Long> charFrequency = str.chars()
            .boxed()
            .collect(Collectors.groupingBy(
                c -> (char) c.intValue(),
                LinkedHashMap::new,
                Collectors.counting()
            ));
        
        // Step 2: Find first character with count == 1
        return str.chars()
            .boxed()
            .map(c -> (char) c.intValue())
            .filter(c -> charFrequency.get(c) == 1)
            .findFirst();
    }
    
    // Main
    public static void main(String[] args) {
        NonRepeatedCharacter finder = new NonRepeatedCharacter();
        
        // Test case 1
        String test1 = "abracadabra";
        System.out.println(finder.findFirstNonRepeatedChar(test1));
        // Output: Optional[c]
        
        // Test case 2
        String test2 = "programming";
        System.out.println(finder.findFirstNonRepeatedChar(test2));
        // Output: Optional[p]
        
        // Test case 3
        String test3 = "aabbcc";
        System.out.println(finder.findFirstNonRepeatedChar(test3));
        // Output: Optional.empty
        
        // Test case 4
        String test4 = "abcdefg";
        System.out.println(finder.findFirstNonRepeatedChar(test4));
        // Output: Optional[a]
    }
}
```

---

## Interview Q&A

### Q1: "Why use LinkedHashMap instead of HashMap?"

**Wrong Answer:** "No difference, both are maps"

**Right Answer:**
```
HashMap: No order guarantee
LinkedHashMap: Maintains insertion order

When you call filter() → findFirst(),
you want the FIRST non-repeated in original string order.

Example:
String: "abracadabra"
HashMap might give: {a: 5, b: 2, r: 2, c: 1, d: 1}
            → findFirst() might return 'c' or 'd' (unordered)

LinkedHashMap gives: {a: 5, b: 2, r: 2, a: ..., c: 1, a: ..., d: 1}
            → findFirst() returns 'c' (first non-repeated in original order)
```

---

### Q2: "Why use Optional instead of returning Character?"

**Wrong Answer:** "Same thing, Optional is just a wrapper"

**Right Answer:**
```
Character:
- Returns null when not found
- Caller might forget null check
- NullPointerException risk

Optional:
- Explicit: "This value might not exist"
- Caller forced to handle: ifPresent(), orElse(), etc.
- Safer and more idiomatic Java 8
- Shows functional programming knowledge

Example:
Optional<Character> result = find(...);
result.ifPresent(c -> System.out.println("Found: " + c));
// Safe, no NPE
```

---

### Q3: "What's the time complexity?"

**Answer:**
```
Time Complexity: O(n) where n = string length

Why?
1. .chars() → O(n) to convert string to stream
2. .boxed() → O(n) to box integers
3. .collect(groupingBy) → O(n) to count frequencies
4. .stream().filter().map() → O(n) to find first

Total: O(n) + O(n) + O(n) + O(n) = O(n)

Space Complexity: O(k) where k = unique characters (max 26 for English)
- LinkedHashMap stores at most 26 entries for English letters
```

---

### Q4: "How would you optimize for memory?"

**Answer:**
```
Current approach: Stores entire character frequency map in memory

Optimized for memory: Single-pass solution (no extra map)

// This won't work because we need counts first
// The two-pass approach is actually the optimal one

Alternative: Use int[26] for only English lowercase letters
int[] charCount = new int[26];
for (char c : str.toCharArray()) {
    charCount[c - 'a']++;
}

Similar O(n) complexity, but constant O(26) space instead of O(k)
But less flexible (only for English lowercase)
```

---

### Q5: "Can you do this without Java 8 streams?"

**Answer:**
```
Yes, but streams are preferred in interviews:

// Traditional way
public Character findNonRepeated(String str) {
    Map<Character, Integer> map = new LinkedHashMap<>();
    
    for (char c : str.toCharArray()) {
        map.put(c, map.getOrDefault(c, 0) + 1);
    }
    
    for (char c : str.toCharArray()) {
        if (map.get(c) == 1) {
            return c;
        }
    }
    return null;
}

// Java 8 streams are cleaner and show modern Java knowledge
```

---

## Real Interview Scenario

**Interviewer:** "Write a function to find the first non-repeated character in a string using Java 8."

**Your Answer (Step-by-step):**

> "I'll solve this in two steps:
> 
> **Step 1: Count character frequencies**
> Using `Collectors.groupingBy()` with counting, I'll create a frequency map.
> I'll use LinkedHashMap to preserve insertion order, which is important
> because I want the first non-repeated character in the original string order.
> 
> **Step 2: Find the first character with count == 1**
> I'll stream through the original string again, filter characters where 
> frequency == 1, and use findFirst() to get the first one.
> 
> **Code:**
> ```java
> public Optional<Character> findFirstNonRepeatedChar(String str) {
>     Map<Character, Long> freqMap = str.chars()
>         .boxed()
>         .collect(Collectors.groupingBy(
>             c -> (char) c.intValue(),
>             LinkedHashMap::new,
>             Collectors.counting()
>         ));
>     
>     return str.chars()
>         .boxed()
>         .map(c -> (char) c.intValue())
>         .filter(c -> freqMap.get(c) == 1)
>         .findFirst();
> }
> ```
> 
> **Complexity:**
> - Time: O(n) - two passes through the string
> - Space: O(k) where k is the number of unique characters
> 
> **Why Optional?** It's safer than returning null and shows I understand
> functional programming idioms in Java 8."

---

## Bonus: Finding All Non-Repeated Characters

```java
public List<Character> findAllNonRepeatedChars(String str) {
    Map<Character, Long> freqMap = str.chars()
        .boxed()
        .collect(Collectors.groupingBy(
            c -> (char) c.intValue(),
            LinkedHashMap::new,
            Collectors.counting()
        ));
    
    return str.chars()
        .boxed()
        .map(c -> (char) c.intValue())
        .distinct()
        .filter(c -> freqMap.get(c) == 1)
        .collect(Collectors.toList());
}

// Example:
String input = "abracadabra";
List<Character> result = findAllNonRepeatedChars(input);
System.out.println(result);  // [c, d]
```

---

## Wrong vs Right Comparison

| Approach | ❌ Wrong | ✅ Right |
|----------|---------|----------|
| **Complexity** | O(n²) nested loops | O(n) single stream |
| **Return type** | null for not found | Optional for safety |
| **Order preservation** | HashMap loses order | LinkedHashMap preserves order |
| **Java 8 idioms** | Manual loops, imperative | Streams, functional |
| **Readability** | Two separate loops | Declarative pipeline |
| **Code length** | 10+ lines | 4-6 lines |

---

## Key Takeaways for Interview

| Concept | Why It Matters | Interview Score |
|---------|----------------|-----------------|
| **Stream pipeline** | Shows Java 8 mastery | ⭐⭐⭐⭐⭐ |
| **Collectors.groupingBy** | Common collector usage | ⭐⭐⭐⭐ |
| **LinkedHashMap** | Order preservation | ⭐⭐⭐⭐ |
| **Optional usage** | Null safety | ⭐⭐⭐⭐ |
| **Time complexity** | Algorithm thinking | ⭐⭐⭐⭐⭐ |

