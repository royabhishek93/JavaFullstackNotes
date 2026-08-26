# Q15: Generate Hashtags from Sentence (Java 8 Streams)

**Study Time:** 6-8 minutes | **Frequency:** 55% in interviews 🔥 | **Difficulty:** ⭐⭐⭐

## Problem Statement

Given a string `sentence`, convert it to a **hashtag format** where:
1. Each word is capitalized (first letter uppercase, rest lowercase)
2. Words are concatenated together (no spaces)
3. Prefix with `#`
4. If input is empty/null, return just `#`
5. If result exceeds 140 characters, return `#` (optional constraint)

### Examples

```
Example 1:
Input: "hello world java"
Output: "#HelloWorldJava"

Example 2:
Input: "never stop coding"
Output: "#NeverStopCoding"

Example 3:
Input: "java"
Output: "#Java"

Example 4:
Input: "   " (spaces only)
Output: "#"

Example 5:
Input: "" (empty)
Output: "#"

Example 6:
Input: "hello world" (11 chars)
Output: "#HelloWorld"
```

---

## Wrong Approaches

### ❌ WRONG Approach 1: Manual Loop

```java
public String toHashtag(String sentence) {
    if (sentence == null || sentence.isEmpty()) {
        return "#";
    }
    
    String result = "#";
    String[] words = sentence.split(" ");
    
    for (String word : words) {
        if (!word.isEmpty()) {
            // Capitalize first letter, lowercase rest
            String capitalized = word.substring(0, 1).toUpperCase() + 
                                word.substring(1).toLowerCase();
            result += capitalized;  // ❌ String concatenation in loop!
        }
    }
    
    return result;
}

// Problems:
// - Creates new String object in each iteration (O(n²) memory)
// - NOT using Java 8 streams (interview expects modern approach)
// - Hard to read
// - Inefficient for large inputs
```

---

### ❌ WRONG Approach 2: StringBuilder Without Stream Features

```java
public String toHashtag(String sentence) {
    if (sentence == null || sentence.trim().isEmpty()) {
        return "#";
    }
    
    StringBuilder result = new StringBuilder("#");
    String[] words = sentence.trim().split("\\s+");
    
    for (String word : words) {
        if (!word.isEmpty()) {
            result.append(word.substring(0, 1).toUpperCase())
                  .append(word.substring(1).toLowerCase());
        }
    }
    
    return result.toString();
}

// While efficient, doesn't demonstrate Java 8 streams
// Interview likely expects stream-based solution
```

---

## ✅ RIGHT Approach: Java 8 Streams

### Solution 1: Complete Stream Pipeline

```java
public String toHashtag(String sentence) {
    // Null/empty check
    if (sentence == null || sentence.trim().isEmpty()) {
        return "#";
    }
    
    // Stream pipeline:
    // 1. Split by whitespace and create stream
    // 2. Filter out empty strings
    // 3. Capitalize each word
    // 4. Join without separator
    // 5. Prefix with #
    return "#" + Arrays.stream(sentence.trim().split("\\s+"))
            .filter(word -> !word.isEmpty())
            .map(word -> word.substring(0, 1).toUpperCase() +
                        word.substring(1).toLowerCase())
            .collect(Collectors.joining());
}

// Complexity:
// Time: O(n) - scan sentence once, process each char
// Space: O(n) - result string
```

---

### Solution 2: More Readable with Helper Method

```java
public String toHashtag(String sentence) {
    if (sentence == null || sentence.trim().isEmpty()) {
        return "#";
    }
    
    String result = "#" + Arrays.stream(sentence.trim().split("\\s+"))
            .filter(word -> !word.isEmpty())
            .map(this::capitalize)
            .collect(Collectors.joining());
    
    // Optional: enforce max length
    return result.length() > 140 ? "#" : result;
}

private String capitalize(String word) {
    return word.substring(0, 1).toUpperCase() + 
           word.substring(1).toLowerCase();
}

// Benefits:
// - Cleaner, more testable
// - Reusable capitalize method
// - Easier to understand
```

---

## Step-by-Step Breakdown

### Input Processing

```
Input: "  hello world  java  "

Step 1: .trim()
        "hello world  java"

Step 2: .split("\\s+")  (split by 1+ whitespace)
        ["hello", "world", "java"]

Step 3: Arrays.stream(...)
        Stream of: "hello", "world", "java"
```

### Stream Operations

```
Step 4: .filter(word -> !word.isEmpty())
        (Already no empty strings from regex split, but defensive)
        Stream of: "hello", "world", "java"

Step 5: .map(word -> capitalize(word))
        "hello" → "Hello"
        "world" → "World"
        "java" → "Java"
        Stream of: "Hello", "World", "Java"

Step 6: .collect(Collectors.joining())
        Concatenate without separator
        "HelloWorldJava"

Step 7: Prefix with "#"
        "#HelloWorldJava"
```

---

## Complete Working Code

```java
import java.util.Arrays;
import java.util.stream.Collectors;

public class GenerateHashtag {
    
    // Solution 1: Inline version
    public String toHashtag(String sentence) {
        if (sentence == null || sentence.trim().isEmpty()) {
            return "#";
        }
        
        return "#" + Arrays.stream(sentence.trim().split("\\s+"))
                .filter(word -> !word.isEmpty())
                .map(word -> word.substring(0, 1).toUpperCase() +
                            word.substring(1).toLowerCase())
                .collect(Collectors.joining());
    }
    
    // Solution 2: With helper method and length check
    public String toHashtagWithLimit(String sentence) {
        if (sentence == null || sentence.trim().isEmpty()) {
            return "#";
        }
        
        String result = "#" + Arrays.stream(sentence.trim().split("\\s+"))
                .filter(word -> !word.isEmpty())
                .map(this::capitalize)
                .collect(Collectors.joining());
        
        return result.length() > 140 ? "#" : result;
    }
    
    private String capitalize(String word) {
        if (word.isEmpty()) return word;
        return word.substring(0, 1).toUpperCase() + 
               word.substring(1).toLowerCase();
    }
    
    public static void main(String[] args) {
        GenerateHashtag generator = new GenerateHashtag();
        
        // Test case 1: Normal input
        System.out.println(generator.toHashtag("hello world java"));
        // Output: #HelloWorldJava
        
        // Test case 2: Multiple spaces
        System.out.println(generator.toHashtag("never stop  coding"));
        // Output: #NeverStopCoding
        
        // Test case 3: Single word
        System.out.println(generator.toHashtag("java"));
        // Output: #Java
        
        // Test case 4: Spaces only
        System.out.println(generator.toHashtag("   "));
        // Output: #
        
        // Test case 5: Empty string
        System.out.println(generator.toHashtag(""));
        // Output: #
        
        // Test case 6: Null
        System.out.println(generator.toHashtag(null));
        // Output: #
        
        // Test case 7: Mixed case
        System.out.println(generator.toHashtag("HeLLo WoRLd"));
        // Output: #HelloWorld
        
        // Test case 8: With length check
        String longInput = "a ".repeat(50); // 100 chars
        System.out.println(generator.toHashtagWithLimit(longInput));
        // Output: depends on length
    }
}
```

---

## Stream Operations Explained

### `Arrays.stream(array)`
Converts array to Stream
```java
String[] words = {"hello", "world"};
Arrays.stream(words)  // Stream<String>
```

### `.filter(predicate)`
Keep only matching elements
```java
.filter(word -> !word.isEmpty())  // Skip empty words
```

### `.map(function)`
Transform each element
```java
.map(word -> word.toUpperCase())  // Transform to uppercase
```

### `.collect(Collectors.joining())`
Join strings without separator
```java
.collect(Collectors.joining())     // "helloworld"
.collect(Collectors.joining("-"))  // "hello-world"
```

---

## Interview Q&A

### Q1: "Why use `split("\\s+")` instead of `split(" ")`?"

**Answer:**
```
split(" "):
  "hello  world".split(" ")
  → ["hello", "", "world"]  ← Empty string for double space!
  
split("\\s+"):  (1 or more whitespace)
  "hello  world".split("\\s+")
  → ["hello", "world"]  ← Cleaner, no empties
  
\s+ handles:
  - Multiple spaces
  - Tabs (\t)
  - Newlines (\n)
  - All whitespace characters
  
Filter is still needed? Not strictly (regex handles it already)
But kept for defensive programming.
```

---

### Q2: "Why check `trim()` before split?"

**Answer:**
```
Without trim():
  "  hello world  ".split("\\s+")
  → ["", "hello", "world", ""]  ← Leading/trailing empties
  
With trim():
  "  hello world  ".trim() → "hello world"
  .split("\\s+")
  → ["hello", "world"]  ← Clean
  
trim() removes leading and trailing whitespace first,
making split cleaner.
```

---

### Q3: "What if we want a length limit (e.g., Twitter 140 chars)?"

**Answer:**
```java
public String toHashtag(String sentence) {
    if (sentence == null || sentence.trim().isEmpty()) {
        return "#";
    }
    
    String result = "#" + Arrays.stream(sentence.trim().split("\\s+"))
            .filter(word -> !word.isEmpty())
            .map(word -> word.substring(0, 1).toUpperCase() +
                        word.substring(1).toLowerCase())
            .collect(Collectors.joining());
    
    // Return # if exceeds limit
    return result.length() > 140 ? "#" : result;
}

Why not in stream?
  Can't efficiently break stream early for length check
  Better to compute, then check length
```

---

### Q4: "How would you get the longest word?"

**Answer:**
```java
String longestWord = Arrays.stream(sentence.trim().split("\\s+"))
    .filter(word -> !word.isEmpty())
    .max(Comparator.comparingInt(String::length))
    .orElse("");

// Returns the word with maximum length
```

---

### Q5: "What if input has numbers/special chars?"

**Answer:**
```
Current solution: Keeps as-is
  "hello123 world!" → "#Hello123World!"
  
If want to remove special chars:

public String toHashtag(String sentence) {
    if (sentence == null || sentence.trim().isEmpty()) {
        return "#";
    }
    
    return "#" + Arrays.stream(sentence.trim().split("\\s+"))
            .filter(word -> !word.isEmpty())
            .filter(word -> word.matches("[a-zA-Z0-9]+"))  // ← Add filter
            .map(word -> word.substring(0, 1).toUpperCase() +
                        word.substring(1).toLowerCase())
            .collect(Collectors.joining());
}

Or remove special chars from words:
.map(word -> word.replaceAll("[^a-zA-Z0-9]", ""))
.filter(word -> !word.isEmpty())
```

---

## Common Mistakes

```java
❌ MISTAKE 1: String concatenation in loop
String result = "#";
for (String word : words) {
    result += capitalize(word);  // O(n²) complexity!
}

✅ CORRECT: Use StringBuilder or Collectors.joining()

❌ MISTAKE 2: Not handling null/empty
return "#" + ...
// If sentence is null, throws NullPointerException

✅ CORRECT: Check first
if (sentence == null || sentence.trim().isEmpty()) {
    return "#";
}

❌ MISTAKE 3: Forgetting filter after split
.split("\\s+")
// If leading/trailing spaces, empties created

✅ CORRECT: Filter or trim first

❌ MISTAKE 4: Using map for side effects
.map(System.out::println)  // ❌ Wrong!

✅ CORRECT: Use forEach for side effects
.forEach(System.out::println)
```

---

## Complexity Analysis

| Operation | Complexity | Notes |
|-----------|-----------|-------|
| `trim()` | O(n) | Linear scan |
| `split()` | O(n) | Scan full string |
| `stream()` | O(1) | Just wrapping |
| `filter()` | O(m) | m = words count |
| `map()` | O(m) | Transform each word |
| `joining()` | O(n) | Build result string |
| **Total** | **O(n)** | Each character processed once |

---

## Stream Best Practices

```java
// ✅ DO: Use streams for transformations
employees.stream()
    .filter(...)
    .map(...)
    .collect(...)

// ✅ DO: One operation per line for readability
return "#" + Arrays.stream(sentence.trim().split("\\s+"))
        .filter(word -> !word.isEmpty())
        .map(this::capitalize)
        .collect(Collectors.joining());

// ✅ DO: Extract complex logic to methods
.map(this::capitalize)

// ❌ DON'T: Stream for single operations
List<String> list = Arrays.stream(arr).collect(toList());
// Just use: Arrays.asList(arr);

// ❌ DON'T: Multiple streams when one suffices
words.stream().filter(...).collect(toList());
words.stream().map(...).collect(toList());
// Combine into single pipeline
```

---

## Interview Answer

**Q: "Convert sentence to hashtag format using streams."**

**Answer:**

> "I'll break this into two parts: **validation** and **stream pipeline**.
> 
> **Validation:**
> - Check if input is null or empty after trimming
> - Return just `#` if invalid
> 
> **Stream Pipeline:**
> 1. **Split** sentence by whitespace (using `\\s+` regex)
> 2. **Filter** out empty strings (defensive, regex already clean)
> 3. **Map** each word to capitalize (first upper, rest lower)
> 4. **Collect** with `joining()` to concatenate without separator
> 5. **Prefix** with `#`
> 
> **Why this approach?**
> - Java 8 streams are idiomatic for transformations
> - One-liner pipeline is declarative and readable
> - No string concatenation in loops (avoids O(n²))
>
> **Code:**
> ```java
> public String toHashtag(String sentence) {
>     if (sentence == null || sentence.trim().isEmpty()) {
>         return \"#\";
>     }
>     
>     return \"#\" + Arrays.stream(sentence.trim().split(\"\\\\s+\"))
>             .filter(word -> !word.isEmpty())
>             .map(word -> word.substring(0, 1).toUpperCase() +
>                         word.substring(1).toLowerCase())
>             .collect(Collectors.joining());
> }
> ```
> 
> **Complexity:**
> - Time: O(n) - each character processed once
> - Space: O(n) - result string
> 
> **Optional enhancement:** Check length limit (Twitter: 140 chars)"

---

## Key Takeaways

| Concept | Why It Matters | Interview Score |
|---------|----------------|-----------------|
| **Stream pipeline** | Demonstrates Java 8 mastery | ⭐⭐⭐⭐⭐ |
| **split("\\s+")** | Regex pattern knowledge | ⭐⭐⭐⭐ |
| **Collectors.joining()** | Common collector usage | ⭐⭐⭐⭐ |
| **Filter vs validation** | Understanding stream logic | ⭐⭐⭐⭐ |
| **O(n) vs O(n²)** | Performance awareness | ⭐⭐⭐⭐⭐ |

