# Q7: Minimum Window Substring

**Study Time:** 12-15 minutes | **Frequency:** 75% in interviews | **Difficulty:** ⭐⭐⭐⭐⭐

---

## 🤔 Problem Statement

Given two strings `s` and `t`, find the **minimum window substring** in `s` that contains **all characters** from `t` (including duplicates).

**Rules:**
- If no such window exists, return empty string ""
- If multiple windows of same minimum length exist, return any one
- Characters in `t` can appear in any order in the window
- Must handle duplicate characters correctly

**Example:**
```
Input:  s = "ADOBECODEBANC", t = "ABC"
Output: "BANC"
Explanation: "BANC" is the smallest window containing all chars of "ABC"

Input:  s = "a", t = "a"
Output: "a"

Input:  s = "a", t = "aa"
Output: ""
Explanation: t has two 'a's but s only has one
```

---

## 🧠 Key Principle: Sliding Window with Frequency Map

This is an **advanced sliding window problem**:
1. **Expand** window (right pointer) until all characters from `t` are included
2. **Contract** window (left pointer) while maintaining validity
3. Track the **minimum valid window** seen so far

**Data Structures:**
- `HashMap<Character, Integer>`: Frequency of characters needed from `t`
- `required`: Total unique characters needed
- `formed`: How many unique characters currently have required frequency

---

## ✅ Correct Solution

```java
public static String minWindow(String s, String t) {
    if (s == null || t == null || s.length() < t.length()) {
        return "";
    }
    
    // Frequency map for characters in t
    Map<Character, Integer> targetFreq = new HashMap<>();
    for (char c : t.toCharArray()) {
        targetFreq.put(c, targetFreq.getOrDefault(c, 0) + 1);
    }
    
    int required = targetFreq.size();  // Unique chars needed
    int formed = 0;  // Unique chars with desired frequency in current window
    
    // Frequency map for current window
    Map<Character, Integer> windowFreq = new HashMap<>();
    
    int left = 0;
    int minLen = Integer.MAX_VALUE;
    int minLeft = 0;  // Start of minimum window
    
    for (int right = 0; right < s.length(); right++) {
        // Expand window by adding character at right
        char c = s.charAt(right);
        windowFreq.put(c, windowFreq.getOrDefault(c, 0) + 1);
        
        // Check if frequency of current char matches target
        if (targetFreq.containsKey(c) && 
            windowFreq.get(c).intValue() == targetFreq.get(c).intValue()) {
            formed++;
        }
        
        // Contract window from left while it's still valid
        while (formed == required && left <= right) {
            // Update minimum window
            if (right - left + 1 < minLen) {
                minLen = right - left + 1;
                minLeft = left;
            }
            
            // Remove character at left
            char leftChar = s.charAt(left);
            windowFreq.put(leftChar, windowFreq.get(leftChar) - 1);
            
            // Check if removal breaks validity
            if (targetFreq.containsKey(leftChar) && 
                windowFreq.get(leftChar) < targetFreq.get(leftChar)) {
                formed--;
            }
            
            left++;
        }
    }
    
    return minLen == Integer.MAX_VALUE ? "" : s.substring(minLeft, minLeft + minLen);
}
```

---

## 📊 Step-by-Step Walkthrough

### Example: `s = "ADOBECODEBANC"`, `t = "ABC"`

**Target Frequency:** `{A:1, B:1, C:1}`, required = 3

| Step | right | left | char | windowFreq | formed | Action | minLen | Current Window |
|------|-------|------|------|------------|--------|--------|--------|----------------|
| 0 | 0 | 0 | A | {A:1} | 1 | Expand | ∞ | "A" |
| 1 | 1 | 0 | D | {A:1,D:1} | 1 | Expand | ∞ | "AD" |
| 2 | 2 | 0 | O | {A:1,D:1,O:1} | 1 | Expand | ∞ | "ADO" |
| 3 | 3 | 0 | B | {A:1,D:1,O:1,B:1} | 2 | Expand | ∞ | "ADOB" |
| 4 | 4 | 0 | E | {A:1,D:1,O:1,B:1,E:1} | 2 | Expand | ∞ | "ADOBE" |
| 5 | 5 | 0 | C | {A:1,D:1,O:1,B:1,E:1,C:1} | **3** | **Valid!** | 6 | "ADOBEC" |
| 6 | 5 | 1 | - | {D:1,O:1,B:1,E:1,C:1} | 2 | Contract (lost A) | 6 | "DOBEC" |
| 7 | 6 | 1 | O | {D:1,O:2,B:1,E:1,C:1} | 2 | Expand | 6 | "DOBECO" |
| 8 | 7 | 1 | D | {D:2,O:2,B:1,E:1,C:1} | 2 | Expand | 6 | "DOBECOD" |
| 9 | 8 | 1 | E | {D:2,O:2,B:1,E:2,C:1} | 2 | Expand | 6 | "DOBECODE" |
| 10 | 9 | 1 | B | {D:2,O:2,B:2,E:2,C:1} | 2 | Expand | 6 | "DOBECODEB" |
| 11 | 10 | 1 | A | {D:2,O:2,B:2,E:2,C:1,A:1} | **3** | **Valid!** | 6 | "DOBECODEBA" |
| 12 | 10 | 2 | - | {D:1,O:2,B:2,E:2,C:1,A:1} | 3 | Contract | 6 | "OBECODEBA" |
| ... | ... | ... | ... | ... | ... | ... | ... | ... |
| Final | 12 | 9 | - | {B:1,A:1,N:1,C:1} | 3 | **Contract** | **4** | **"BANC"** |

**Final Answer:** "BANC" (length 4)

---

## 📊 Test Cases

### Test Case 1: Basic Example
```java
String s = "ADOBECODEBANC";
String t = "ABC";
String result = minWindow(s, t);
System.out.println(result);
```
**Expected Output:** `"BANC"`

### Test Case 2: Single Character
```java
String s = "a";
String t = "a";
String result = minWindow(s, t);
System.out.println(result);
```
**Expected Output:** `"a"`

### Test Case 3: No Valid Window
```java
String s = "a";
String t = "aa";
String result = minWindow(s, t);
System.out.println(result);
```
**Expected Output:** `""` (empty string)

### Test Case 4: Entire String is Window
```java
String s = "abc";
String t = "abc";
String result = minWindow(s, t);
System.out.println(result);
```
**Expected Output:** `"abc"`

### Test Case 5: Duplicate Characters in Target
```java
String s = "aa";
String t = "aa";
String result = minWindow(s, t);
System.out.println(result);
```
**Expected Output:** `"aa"`

### Test Case 6: All Same Characters
```java
String s = "aaaaaaa";
String t = "aa";
String result = minWindow(s, t);
System.out.println(result);
```
**Expected Output:** `"aa"`

---

## Interview Q&A

### Q1: "What's the time and space complexity?"

**Answer:**
```
Time Complexity: O(|S| + |T|)
- Building targetFreq: O(|T|)
- Expanding window (right pointer): visits each character once → O(|S|)
- Contracting window (left pointer): visits each character at most once → O(|S|)
- Total: O(|S| + |T|)

Note: NOT O(|S| × |T|) because left pointer never moves backward

Space Complexity: O(|S| + |T|)
- targetFreq: O(|T|) for unique characters in t
- windowFreq: O(|S|) in worst case (all unique characters in s)
- For fixed character set (ASCII): O(1) space if using arrays
```

**Example proving O(|S|) for pointers:**
```
s = "ADOBECODEBANC" (length 13)
- right moves: 0 → 12 (13 operations)
- left moves: 0 → 9 (9 operations)
- Total: 13 + 9 = 22 operations = O(2|S|) = O(|S|)
```

### Q2: "Why track 'formed' instead of comparing entire frequency maps?"

**Answer:**
```
Without 'formed' (Naive Approach):
- After each character addition, compare ALL frequencies
- Comparison: O(unique chars in t) per iteration
- Total: O(|S| × |T|) → TOO SLOW for large inputs!

With 'formed' (Optimized):
- Track only when a character reaches required frequency
- Check: O(1) per iteration
- Total: O(|S|) → MUCH FASTER!

Example:
t = "ABC" (3 unique chars)
s = "ADOBECODEBANC" (13 chars)

Naive: 13 iterations × 3 comparisons = 39 operations
Optimized: 13 iterations × 1 check = 13 operations
```

**Code Comparison:**
```java
// SLOW - O(S × T)
while (true) {
    boolean valid = true;
    for (char c : targetFreq.keySet()) {
        if (windowFreq.getOrDefault(c, 0) < targetFreq.get(c)) {
            valid = false;
            break;
        }
    }
    if (!valid) break;
    // contract window...
}

// FAST - O(S)
if (targetFreq.containsKey(c) && 
    windowFreq.get(c).intValue() == targetFreq.get(c).intValue()) {
    formed++;  // Increment count
}
// Check formed == required (O(1))
```

### Q3: "What if we need to return the window as a substring vs just indices?"

**Answer:**
```java
// Current solution returns substring:
return s.substring(minLeft, minLeft + minLen);

// To return indices instead:
if (minLen == Integer.MAX_VALUE) {
    return new int[]{-1, -1};  // No valid window
}
return new int[]{minLeft, minLeft + minLen - 1};  // [start, end] inclusive

// To return all minimum windows (if multiple exist):
List<String> allMinWindows = new ArrayList<>();
while (/* sliding window logic */) {
    if (right - left + 1 == minLen) {
        allMinWindows.add(s.substring(left, right + 1));
    }
}
```

### Q4: "Can this be solved with array instead of HashMap for better performance?"

**Answer:**
```java
public static String minWindowArray(String s, String t) {
    if (s == null || t == null || s.length() < t.length()) {
        return "";
    }
    
    // Assuming extended ASCII (256 characters)
    int[] targetFreq = new int[256];
    int[] windowFreq = new int[256];
    
    int required = 0;
    for (char c : t.toCharArray()) {
        if (targetFreq[c] == 0) {
            required++;  // New unique character
        }
        targetFreq[c]++;
    }
    
    int formed = 0;
    int left = 0;
    int minLen = Integer.MAX_VALUE;
    int minLeft = 0;
    
    for (int right = 0; right < s.length(); right++) {
        char c = s.charAt(right);
        windowFreq[c]++;
        
        if (targetFreq[c] > 0 && windowFreq[c] == targetFreq[c]) {
            formed++;
        }
        
        while (formed == required && left <= right) {
            if (right - left + 1 < minLen) {
                minLen = right - left + 1;
                minLeft = left;
            }
            
            char leftChar = s.charAt(left);
            windowFreq[leftChar]--;
            
            if (targetFreq[leftChar] > 0 && windowFreq[leftChar] < targetFreq[leftChar]) {
                formed--;
            }
            
            left++;
        }
    }
    
    return minLen == Integer.MAX_VALUE ? "" : s.substring(minLeft, minLeft + minLen);
}
```

**Trade-offs:**
- ✅ Faster: O(1) array access vs O(1) amortized HashMap
- ✅ Better cache locality
- ❌ Fixed memory: 256 * 2 * 4 bytes = 2KB always allocated
- ❌ Wastes space if only ASCII lowercase (26 chars)

**When to use:**
- Known character set (ASCII) → array
- Unknown/Unicode characters → HashMap
```

### Q5: "What are the edge cases?"

**Answer:**
```
1. Empty strings:
   s = "", t = "a" → ""
   s = "a", t = "" → "" (or "a" depending on definition)

2. t longer than s:
   s = "ab", t = "abc" → "" (impossible)

3. No valid window:
   s = "a", t = "aa" → ""

4. Entire string is minimum:
   s = "abc", t = "abc" → "abc"

5. Multiple minimum windows:
   s = "abcabc", t = "abc" → "abc" (can return either occurrence)

6. Duplicate characters:
   s = "aa", t = "aa" → "aa" (must handle counts correctly)

7. Target has more frequency than source:
   s = "a", t = "aaa" → ""

Always validate: s != null, t != null, s.length() >= t.length()
```

---

## Common Mistakes

### ❌ Mistake 1: Not Handling Duplicate Characters
```java
// WRONG - Ignores frequency
Set<Character> needed = new HashSet<>();
for (char c : t.toCharArray()) {
    needed.add(c);  // Loses count!
}

// Example: t = "AA", needed = {A} (wrong! need 2 A's)

// CORRECT - Track frequency
Map<Character, Integer> needed = new HashMap<>();
for (char c : t.toCharArray()) {
    needed.put(c, needed.getOrDefault(c, 0) + 1);
}
```

### ❌ Mistake 2: Comparing Frequencies Incorrectly
```java
// WRONG - Can cause NullPointerException
if (windowFreq.get(c) == targetFreq.get(c)) {
    // Integer comparison by reference, not value!
}

// CORRECT
if (windowFreq.get(c).intValue() == targetFreq.get(c).intValue()) {
    formed++;
}

// Or even better:
if (windowFreq.get(c).equals(targetFreq.get(c))) {
    formed++;
}
```

### ❌ Mistake 3: Not Checking Window Validity Before Contracting
```java
// WRONG - Contracts without checking if window is valid
while (left <= right) {
    // Always contracts, even if window is invalid
}

// CORRECT - Only contract when window is valid
while (formed == required && left <= right) {
    // Contract only when all characters are present
}
```

### ❌ Mistake 4: Infinite Loop with Wrong Contraction Logic
```java
// WRONG - Infinite loop if logic is reversed
while (formed < required) {
    left++;  // Contracts when invalid, expands when valid!
}

// CORRECT
while (formed == required && left <= right) {
    // Contract when valid, expand (outer loop) when invalid
}
```

---

## Complete Working Code

```java
import java.util.*;

public class MinimumWindowSubstring {
    
    public static String minWindow(String s, String t) {
        if (s == null || t == null || s.length() < t.length()) {
            return "";
        }
        
        Map<Character, Integer> targetFreq = new HashMap<>();
        for (char c : t.toCharArray()) {
            targetFreq.put(c, targetFreq.getOrDefault(c, 0) + 1);
        }
        
        int required = targetFreq.size();
        int formed = 0;
        
        Map<Character, Integer> windowFreq = new HashMap<>();
        
        int left = 0;
        int minLen = Integer.MAX_VALUE;
        int minLeft = 0;
        
        for (int right = 0; right < s.length(); right++) {
            char c = s.charAt(right);
            windowFreq.put(c, windowFreq.getOrDefault(c, 0) + 1);
            
            if (targetFreq.containsKey(c) && 
                windowFreq.get(c).intValue() == targetFreq.get(c).intValue()) {
                formed++;
            }
            
            while (formed == required && left <= right) {
                if (right - left + 1 < minLen) {
                    minLen = right - left + 1;
                    minLeft = left;
                }
                
                char leftChar = s.charAt(left);
                windowFreq.put(leftChar, windowFreq.get(leftChar) - 1);
                
                if (targetFreq.containsKey(leftChar) && 
                    windowFreq.get(leftChar) < targetFreq.get(leftChar)) {
                    formed--;
                }
                
                left++;
            }
        }
        
        return minLen == Integer.MAX_VALUE ? "" : s.substring(minLeft, minLeft + minLen);
    }

    public static void main(String[] args) {
        // Test case 1
        System.out.println(minWindow("ADOBECODEBANC", "ABC"));  // "BANC"
        
        // Test case 2
        System.out.println(minWindow("a", "a"));  // "a"
        
        // Test case 3
        System.out.println(minWindow("a", "aa"));  // ""
        
        // Test case 4
        System.out.println(minWindow("abc", "abc"));  // "abc"
        
        // Test case 5
        System.out.println(minWindow("aa", "aa"));  // "aa"
    }
}
```

---

## Key Takeaways

| Concept | Why Important | Interview Score |
|---------|---------------|-----------------|
| Advanced sliding window | Complex algorithm pattern | ⭐⭐⭐⭐⭐ |
| Frequency map optimization | Avoid O(S×T) complexity | ⭐⭐⭐⭐⭐ |
| Two-pointer technique | Efficient window management | ⭐⭐⭐⭐⭐ |
| 'formed' counter trick | Key optimization insight | ⭐⭐⭐⭐ |
| Edge case handling | Avoiding bugs | ⭐⭐⭐⭐ |

---

**Priority:** 🔥 MUST KNOW (Hard problem, frequently asked at FAANG)

**Related Problems:**
- Longest Substring Without Repeating Characters
- Substring with Concatenation of All Words
- Find All Anagrams in a String

---

**Last Updated:** March 1, 2026
