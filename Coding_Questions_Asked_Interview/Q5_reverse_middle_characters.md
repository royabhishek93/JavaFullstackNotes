# Q5: Reverse Middle Characters in Each Word

**Study Time:** 5-7 minutes | **Frequency:** 45% in interviews | **Difficulty:** ⭐⭐⭐

---

## 🤔 Problem Statement

Given a string with multiple words, **reverse the middle characters of each word while keeping the first and last characters intact**.

**Rules:**
- Words with length ≤ 2: Keep as-is (nothing to reverse)
- Words with length > 2: Reverse only the middle characters
- Preserve word boundaries and spacing

**Example:**
```
Input:  "hello world"
Output: "hlleo wlrod"

Explanation:
- "hello" → h + reverse("ell") + o → h + "lle" + o → "hlleo"
- "world" → w + reverse("orl") + d → w + "lro" + d → "wlrod"
```

---

## ✅ Correct Solution

```java
public static String reverseMiddle(String str) {
    String[] words = str.split(" ");
    StringBuilder result = new StringBuilder();

    for (String word : words) {
        // Words with 2 or fewer characters: keep as-is
        if (word.length() <= 2) {
            result.append(word).append(" ");
            continue;
        }

        // Extract middle characters (all except first and last)
        String middle = word.substring(1, word.length() - 1);
        
        // Reverse the middle
        String reversedMiddle = new StringBuilder(middle).reverse().toString();

        // Reconstruct: first char + reversed middle + last char
        result.append(word.charAt(0))
              .append(reversedMiddle)
              .append(word.charAt(word.length() - 1))
              .append(" ");
    }

    return result.toString().trim();
}
```

---

## 📊 Test Cases & Expected Output

### Test Case 1: Basic Example
```java
String input = "hello world";
String output = reverseMiddle(input);
System.out.println(output);
```

**Expected Output:**
```
hlleo wlrod
```
---

### Test Case 2: Words with Short Length
```java
String input = "a is good";
String output = reverseMiddle(input);
System.out.println(output);
```

**Expected Output:**
```
a is good
```

### Test Case 3: Longer Words
```java
String input = "programming java";
String output = reverseMiddle(input);
System.out.println(output);
```

**Expected Output:**
```
pnimmargorg jvaa
```

---

## Interview Q&A

### Q1: "Why use StringBuilder instead of string concatenation?"

**Wrong Answer:**
"They're basically the same thing."

**Right Answer:**
```
String concatenation (+=) creates a new String object each time:
- Time Complexity: O(n²) for building n-character result
- Memory: Creates intermediate strings

StringBuilder approach:
- Time Complexity: O(n) - single allocation and append
- Memory: Single result buffer

For large inputs, StringBuilder is much faster.

Example:
// BAD - O(n²)
result += word.charAt(0);
result += reversedMiddle;
result += word.charAt(word.length()-1);

// GOOD - O(n)
result.append(word.charAt(0))
      .append(reversedMiddle)
      .append(word.charAt(word.length()-1));
```

---

### Q2: "What if the word has exactly 3 characters?"

**Answer:**
```
Word: "cat" (length 3)
- First char: 'c' (index 0)
- Middle: substring(1, 2) = "a" (only 1 character)
- Last char: 't' (index 2)
- Reverse "a": "a" (single char, no change)
- Result: "c" + "a" + "t" = "cat"

So 3-char words return the same (middle has only 1 char, can't reverse).
This is correct behavior.
```

---

### Q3: "What if input has multiple spaces between words?"

**Current Behavior:**
```java
String input = "hello  world";  // Two spaces
String[] words = str.split(" ");
// Result: ["hello", "", "world"]
// Empty string causes issues!
```

**Fixed Solution:**
```java
public static String reverseMiddle(String str) {
    String[] words = str.split(" ");  // or use str.split("\\s+") for all whitespace
    StringBuilder result = new StringBuilder();

    for (String word : words) {
        // Skip empty words
        if (word.isEmpty()) {
            result.append(" ");
            continue;
        }
        
        if (word.length() <= 2) {
            result.append(word).append(" ");
            continue;
        }

        String middle = word.substring(1, word.length() - 1);
        String reversedMiddle = new StringBuilder(middle).reverse().toString();

        result.append(word.charAt(0))
              .append(reversedMiddle)
              .append(word.charAt(word.length() - 1))
              .append(" ");
    }

    return result.toString().trim();
}
```

---

### Q4: "Can you optimize this with Java 8 Streams?"

**Answer:**
```java
public static String reverseMiddleWithStreams(String str) {
    return Arrays.stream(str.split(" "))
        .map(word -> {
            if (word.length() <= 2) {
                return word;
            }
            String middle = word.substring(1, word.length() - 1);
            String reversed = new StringBuilder(middle).reverse().toString();
            return word.charAt(0) + reversed + word.charAt(word.length() - 1);
        })
        .collect(Collectors.joining(" "));
}
```

**Trade-offs:**
- ✅ More functional/modern
- ❌ Potential overhead for small inputs
- ❌ Less readable (lambda is complex)

**Interview Tip:** Mention this but stick with the loop-based solution unless specifically asked for streams.

---

### Q4.5: "Can you solve this without using the `reverse()` method?"

**Answer:**
```java
import java.util.*;

public static String reverseMiddleManual(String str) {
    String[] words = str.split(" ");
    StringBuilder result = new StringBuilder();

    for (String word : words) {
        if (word.length() <= 2) {
            result.append(word).append(" ");
            continue;
        }

        // Extract middle characters
        String middle = word.substring(1, word.length() - 1);
        
        // Manually reverse without using reverse() method
        StringBuilder reversedMiddle = new StringBuilder();
        for (int i = middle.length() - 1; i >= 0; i--) {
            reversedMiddle.append(middle.charAt(i));
        }

        // Reconstruct the word
        result.append(word.charAt(0))
              .append(reversedMiddle)
              .append(word.charAt(word.length() - 1))
              .append(" ");
    }

    return result.toString().trim();
}
```

**How the manual reversal works:**
```
String middle = "ell"
Loop backwards through indices:
  i = 2: append middle.charAt(2) = 'l'
  i = 1: append middle.charAt(1) = 'l'
  i = 0: append middle.charAt(0) = 'e'
Result: "lle"
```

**Comparison:**

| Method | How It Works | Pros | Cons |
|--------|-------------|------|------|
| `StringBuilder.reverse()` | Built-in method | Simple, readable, efficient | Requires additional StringBuilder object |
| Loop backwards | Loop from end to start | No extra objects | Slightly more verbose |
| Char array swap | Two pointers meet in middle | In-place reversal, efficient | More complex logic |

---

### Q5: "What's the time and space complexity?"

**Answer:**
```
Time Complexity: O(n) where n = total characters in input
- Split: O(n)
- Loop through words: O(w) where w = number of words
- For each word: substring, reverse, append = O(c) where c = chars in word
- Total: O(n) across all words

Space Complexity: O(n)
- StringBuilder result: O(n) for the output
- String array from split: O(n)
- Middle substring: O(c) for each word
- Reversed string: O(c) for each word
- Total: O(n) dominated by the output

Can we do better? NO - we must at least create the output (O(n)).
```

---

## Common Mistakes

### ❌ Mistake 1: Forgetting to Handle Short Words
```java
// WRONG - Crashes on words with 2 chars
for (String word : words) {
    String middle = word.substring(1, word.length() - 1);
    // For "is": word.substring(1, 2) = "s"
    // For "a": word.substring(1, 1) = "" (empty, but process continues)
    // These edge cases should skip!
}

// CORRECT
if (word.length() <= 2) {
    result.append(word).append(" ");
    continue;
}
```

---

### ❌ Mistake 2: Forgetting to Trim Final Output
```java
// WRONG - Output has trailing space
return result.toString();  // "hlleo wlrod "

// CORRECT
return result.toString().trim();  // "hlleo wlrod"
```

---

### ❌ Mistake 3: Off-by-One Errors in substring()
```java
// WRONG - Includes last character in middle
String middle = word.substring(1, word.length());

// CORRECT - Excludes last character
String middle = word.substring(1, word.length() - 1);
```

---

## Complete Working Code

```java
public class ReverseMiddle {
    
    public static String reverseMiddle(String str) {
        if (str == null || str.isEmpty()) {
            return "";
        }
        
        String[] words = str.split(" ");
        StringBuilder result = new StringBuilder();

        for (String word : words) {
            if (word.length() <= 2) {
                result.append(word).append(" ");
                continue;
            }

            String middle = word.substring(1, word.length() - 1);
            String reversedMiddle = new StringBuilder(middle).reverse().toString();

            result.append(word.charAt(0))
                  .append(reversedMiddle)
                  .append(word.charAt(word.length() - 1))
                  .append(" ");
        }

        return result.toString().trim();
    }

    public static void main(String[] args) {
        // Test case 1
        System.out.println(reverseMiddle("hello world"));
        // Output: hlleo wlrod

        // Test case 2
        System.out.println(reverseMiddle("a is good"));
        // Output: a is good

        // Test case 3
        System.out.println(reverseMiddle("programming java"));
        // Output: pnimmargorg jvaa

        // Test case 4
        System.out.println(reverseMiddle("testing"));
        // Output: tnitseg

        // Test case 5
        System.out.println(reverseMiddle(""));
        // Output: (empty)
    }
}
```

---

## Key Takeaways

| Concept | Why Important | Interview Score |
|---------|---------------|-----------------|
| String manipulation | Core skill | ⭐⭐⭐⭐⭐ |
| StringBuilder efficiency | Performance awareness | ⭐⭐⭐⭐ |
| Edge case handling | Code quality | ⭐⭐⭐⭐ |
| substring() indexing | Accuracy | ⭐⭐⭐⭐ |
| Complexity analysis | Big picture thinking | ⭐⭐⭐⭐ |

---

**Last Updated:** March 1, 2026
