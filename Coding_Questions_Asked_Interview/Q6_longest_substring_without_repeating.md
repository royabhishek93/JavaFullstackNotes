# Q6: Longest Substring Without Repeating Characters

**Study Time:** 8-10 minutes | **Frequency:** 85% in interviews | **Difficulty:** ⭐⭐⭐⭐

---

## 🤔 Problem Statement

Given a string, find the **length of the longest substring without repeating characters**.

**Example:**
```
Input:  "abcabcbb"
Output: 3
Explanation: "abc" is the longest substring without repeating characters (length 3)

Input:  "bbbbb"
Output: 1
Explanation: "b" is the longest (all characters repeat)

Input:  "pwwkew"
Output: 3
Explanation: "wke" is the longest (not "pwke" because 'w' repeats)
```

---

## 🧠 Key Principle: Sliding Window

This is a **classic sliding window problem** using two pointers:
- **Left pointer**: Start of the current window
- **Right pointer**: End of the current window (expanding)
- **HashSet/HashMap**: Track characters in current window

**Algorithm:**
1. Expand window by moving right pointer
2. If character is already in window → shrink from left until duplicate is removed
3. Track maximum window size seen so far

---

## ✅ Correct Solution (HashSet Approach)

```java
public static int lengthOfLongestSubstring(String s) {
    if (s == null || s.isEmpty()) {
        return 0;
    }
    
    Set<Character> seen = new HashSet<>();
    int left = 0;
    int maxLength = 0;
    
    for (int right = 0; right < s.length(); right++) {
        char currentChar = s.charAt(right);
        
        // If character already exists, shrink window from left
        while (seen.contains(currentChar)) {
            seen.remove(s.charAt(left));
            left++;
        }
        
        // Add current character to window
        seen.add(currentChar);
        
        // Update max length
        maxLength = Math.max(maxLength, right - left + 1);
    }
    
    return maxLength;
}
```

---

## 📊 Step-by-Step Walkthrough

### Example: `"abcabcbb"`

| Step | right | left | currentChar | seen | Action | maxLength |
|------|-------|------|-------------|------|--------|-----------|
| 0 | 0 | 0 | 'a' | {} | Add 'a' | 1 |
| 1 | 1 | 0 | 'b' | {a} | Add 'b' | 2 |
| 2 | 2 | 0 | 'c' | {a,b} | Add 'c' | 3 |
| 3 | 3 | 0 | 'a' | {a,b,c} | **Conflict!** Remove 'a' (left=1) | 3 |
| 4 | 4 | 1 | 'b' | {b,c,a} | **Conflict!** Remove 'b' (left=2) | 3 |
| 5 | 5 | 2 | 'c' | {c,a,b} | **Conflict!** Remove 'c' (left=3) | 3 |
| 6 | 6 | 3 | 'b' | {a,b,c} | Add 'b' | 3 |
| 7 | 7 | 3 | 'b' | {a,b,c,b} | **Conflict!** Remove 'a','b' (left=5) | 3 |

**Final Answer:** 3 (substring "abc")

---

## 🚀 Optimized Solution (HashMap with Index)

Instead of shrinking the window one character at a time, **jump directly** to the position after the duplicate:

```java
public static int lengthOfLongestSubstringOptimized(String s) {
    if (s == null || s.isEmpty()) {
        return 0;
    }
    
    // Map: character → last seen index
    Map<Character, Integer> lastSeen = new HashMap<>();
    int left = 0;
    int maxLength = 0;
    
    for (int right = 0; right < s.length(); right++) {
        char currentChar = s.charAt(right);
        
        // If character was seen and is within current window
        if (lastSeen.containsKey(currentChar)) {
            // Jump left pointer to position after last occurrence
            left = Math.max(left, lastSeen.get(currentChar) + 1);
        }
        
        // Update last seen position
        lastSeen.put(currentChar, right);
        
        // Update max length
        maxLength = Math.max(maxLength, right - left + 1);
    }
    
    return maxLength;
}
```

**Why `Math.max(left, lastSeen.get(currentChar) + 1)`?**
```
Example: "abba"
- At index 3, we see 'a' again (last seen at index 0)
- But left is already at 2 (moved forward from first 'b' duplicate)
- We should NOT move left backward to 1
- So: left = Math.max(2, 0+1) = 2 (stays at 2)
```

---

## 📊 Test Cases

### Test Case 1: Basic Example
```java
String input = "abcabcbb";
int result = lengthOfLongestSubstring(input);
System.out.println(result);
```
**Expected Output:** `3` (substring "abc")

### Test Case 2: All Same Characters
```java
String input = "bbbbb";
int result = lengthOfLongestSubstring(input);
System.out.println(result);
```
**Expected Output:** `1` (substring "b")

### Test Case 3: Hidden Trap
```java
String input = "pwwkew";
int result = lengthOfLongestSubstring(input);
System.out.println(result);
```
**Expected Output:** `3` (substring "wke", not "pwke")

### Test Case 4: All Unique
```java
String input = "abcdef";
int result = lengthOfLongestSubstring(input);
System.out.println(result);
```
**Expected Output:** `6` (entire string)

### Test Case 5: Empty String
```java
String input = "";
int result = lengthOfLongestSubstring(input);
System.out.println(result);
```
**Expected Output:** `0`

### Test Case 6: Single Character
```java
String input = "a";
int result = lengthOfLongestSubstring(input);
System.out.println(result);
```
**Expected Output:** `1`

---

## Interview Q&A

### Q1: "What's the time and space complexity?"

**Answer:**
```
HashSet Approach:
- Time: O(n) where n = string length
  - Each character is visited at most twice (once by right, once by left)
  - In worst case: O(2n) = O(n)
- Space: O(min(n, m)) where m = character set size
  - At most n unique characters in the set
  - For ASCII: O(128), for Unicode: O(n)

HashMap Approach:
- Time: O(n) - single pass through string
- Space: O(min(n, m)) - same as above

Both are O(n) time, but HashMap is faster in practice (single pass).
```

### Q2: "Why use `while` loop in HashSet approach but not in HashMap?"

**Answer:**
```
HashSet Approach:
while (seen.contains(currentChar)) {
    seen.remove(s.charAt(left));
    left++;
}
// Shrinks window one character at a time until duplicate is removed

HashMap Approach:
left = Math.max(left, lastSeen.get(currentChar) + 1);
// Jumps directly to position after duplicate

Example: "abcda"
- At 'a' (index 4), HashSet removes 'a','b','c' one by one (3 operations)
- HashMap jumps left from 0 to 1 directly (1 operation)

HashMap is more efficient!
```

### Q3: "Can you solve this with a fixed-size array instead of HashMap?"

**Answer:**
```java
public static int lengthOfLongestSubstringArray(String s) {
    if (s == null || s.isEmpty()) {
        return 0;
    }
    
    // Assuming ASCII characters (0-127)
    int[] lastIndex = new int[128];
    Arrays.fill(lastIndex, -1);  // -1 means not seen
    
    int left = 0;
    int maxLength = 0;
    
    for (int right = 0; right < s.length(); right++) {
        char currentChar = s.charAt(right);
        
        // If character was seen within current window
        if (lastIndex[currentChar] >= left) {
            left = lastIndex[currentChar] + 1;
        }
        
        // Update last seen index
        lastIndex[currentChar] = right;
        
        // Update max length
        maxLength = Math.max(maxLength, right - left + 1);
    }
    
    return maxLength;
}
```

**Trade-offs:**
- ✅ Faster: O(1) array access vs O(1) amortized HashMap
- ✅ No hashing overhead
- ❌ Fixed memory: Always uses 128 bytes (ASCII) or 65536 bytes (Unicode)
- ❌ Only works for known character sets

**When to use:**
- Interviewer specifies ASCII input → use array
- Unicode or unknown charset → use HashMap
```

### Q4: "What if we need to return the actual substring, not just the length?"

**Answer:**
```java
public static String longestSubstringWithoutRepeating(String s) {
    if (s == null || s.isEmpty()) {
        return "";
    }
    
    Map<Character, Integer> lastSeen = new HashMap<>();
    int left = 0;
    int maxLength = 0;
    int maxStart = 0;  // Track where the longest substring starts
    
    for (int right = 0; right < s.length(); right++) {
        char currentChar = s.charAt(right);
        
        if (lastSeen.containsKey(currentChar)) {
            left = Math.max(left, lastSeen.get(currentChar) + 1);
        }
        
        lastSeen.put(currentChar, right);
        
        // Update max and track starting position
        if (right - left + 1 > maxLength) {
            maxLength = right - left + 1;
            maxStart = left;
        }
    }
    
    return s.substring(maxStart, maxStart + maxLength);
}
```

**Example:**
```
Input: "pwwkew"
Output: "wke" (not just 3)
```

### Q5: "What are the edge cases?"

**Answer:**
```
1. Empty string: "" → return 0
2. Single character: "a" → return 1
3. All unique: "abcdef" → return 6 (entire string)
4. All same: "aaaa" → return 1
5. Duplicate at start: "aabcd" → return 4 ("abcd")
6. Duplicate at end: "abcda" → return 4 ("abcd" or "bcda")
7. Null input: null → return 0 (handle gracefully)

Always test these during interviews!
```

---

## Common Mistakes

### ❌ Mistake 1: Forgetting to Remove Characters from Set
```java
// WRONG - Set keeps growing, never shrinks
while (seen.contains(currentChar)) {
    left++;  // Move pointer but don't remove from set!
}

// CORRECT
while (seen.contains(currentChar)) {
    seen.remove(s.charAt(left));
    left++;
}
```

### ❌ Mistake 2: Not Using `Math.max()` in HashMap Approach
```java
// WRONG - Left pointer can move backward!
left = lastSeen.get(currentChar) + 1;

// CORRECT - Never move left backward
left = Math.max(left, lastSeen.get(currentChar) + 1);

// Why? Example: "abba"
// At index 3 ('a'), left is at 2 (from 'b' duplicate)
// lastSeen.get('a') = 0, so 0+1=1
// We should NOT move left from 2 to 1 (backward)
```

### ❌ Mistake 3: Off-by-One in Window Size
```java
// WRONG - Missing +1
maxLength = Math.max(maxLength, right - left);

// CORRECT - Indices are 0-based
maxLength = Math.max(maxLength, right - left + 1);

// Example: left=0, right=2 → window has 3 characters (indices 0,1,2)
```

---

## Complete Working Code

```java
import java.util.*;

public class LongestSubstringWithoutRepeat {
    
    // Approach 1: HashSet with Sliding Window
    public static int lengthOfLongestSubstring(String s) {
        if (s == null || s.isEmpty()) {
            return 0;
        }
        
        Set<Character> seen = new HashSet<>();
        int left = 0;
        int maxLength = 0;
        
        for (int right = 0; right < s.length(); right++) {
            char currentChar = s.charAt(right);
            
            while (seen.contains(currentChar)) {
                seen.remove(s.charAt(left));
                left++;
            }
            
            seen.add(currentChar);
            maxLength = Math.max(maxLength, right - left + 1);
        }
        
        return maxLength;
    }
    
    // Approach 2: HashMap (Optimized)
    public static int lengthOfLongestSubstringOptimized(String s) {
        if (s == null || s.isEmpty()) {
            return 0;
        }
        
        Map<Character, Integer> lastSeen = new HashMap<>();
        int left = 0;
        int maxLength = 0;
        
        for (int right = 0; right < s.length(); right++) {
            char currentChar = s.charAt(right);
            
            if (lastSeen.containsKey(currentChar)) {
                left = Math.max(left, lastSeen.get(currentChar) + 1);
            }
            
            lastSeen.put(currentChar, right);
            maxLength = Math.max(maxLength, right - left + 1);
        }
        
        return maxLength;
    }

    public static void main(String[] args) {
        // Test case 1
        System.out.println(lengthOfLongestSubstring("abcabcbb"));  // 3
        
        // Test case 2
        System.out.println(lengthOfLongestSubstring("bbbbb"));  // 1
        
        // Test case 3
        System.out.println(lengthOfLongestSubstring("pwwkew"));  // 3
        
        // Test case 4
        System.out.println(lengthOfLongestSubstring(""));  // 0
        
        // Test case 5
        System.out.println(lengthOfLongestSubstring("abcdef"));  // 6
    }
}
```

---

## Key Takeaways

| Concept | Why Important | Interview Score |
|---------|---------------|-----------------|
| Sliding window pattern | Fundamental algorithm technique | ⭐⭐⭐⭐⭐ |
| Two-pointer technique | Optimization skill | ⭐⭐⭐⭐⭐ |
| HashSet for duplicates | Data structure choice | ⭐⭐⭐⭐ |
| HashMap optimization | Jump vs shrink | ⭐⭐⭐⭐ |
| Edge case handling | Code quality | ⭐⭐⭐⭐ |

---

**Priority:** 🔥 MUST KNOW (Asked in 85% of coding interviews at FAANG)

**Related Problems:**
- Longest Repeating Character Replacement
- Minimum Window Substring
- Substring with Concatenation of All Words

---

**Last Updated:** March 1, 2026
