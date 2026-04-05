# Q11: Rearrange String So No Adjacent Same Characters

**Study Time:** 10-12 minutes | **Frequency:** 65% in interviews | **Difficulty:** ⭐⭐⭐⭐

---

## 🤔 Problem Statement

Given a string with repeated characters, **rearrange it** so that **no two adjacent characters are the same**. If multiple valid arrangements exist, return any one. If no valid arrangement exists, return empty string.

**Example:**
```
Input:  "aaabbc"
Output: "ababac" (or "abacab", "acabab", etc.)
Explanation: No two adjacent characters are the same

Input:  "aaaa"
Output: ""
Explanation: Impossible to arrange without adjacent duplicates

Input:  "aab"
Output: "aba" (or "baa" if we allow same at end)
Explanation: Multiple valid solutions exist
```

---

## 🧠 Key Principle: Greedy with Max Heap

**Core Insight:** Always place the **most frequent character** first (among valid choices).

**Why?** 
- If we place less frequent characters first, we might run out of "separator" characters
- Most frequent character is hardest to place → place it as soon as possible
- Use Max Heap to efficiently get most frequent character

**Algorithm:**
1. Count character frequencies
2. Build Max Heap based on frequency
3. Repeatedly:
   - Take top 2 characters from heap
   - Place them alternately
   - Decrement their counts
   - Put them back if count > 0
4. Handle last character separately (if odd total count)

---

## ✅ Correct Solution

```java
public static String rearrangeString(String s) {
    if (s == null || s.isEmpty()) {
        return s;
    }
    
    // Step 1: Count frequencies
    Map<Character, Integer> freqMap = new HashMap<>();
    for (char c : s.toCharArray()) {
        freqMap.put(c, freqMap.getOrDefault(c, 0) + 1);
    }
    
    // Step 2: Build max heap (by frequency)
    PriorityQueue<Map.Entry<Character, Integer>> maxHeap = new PriorityQueue<>(
        (a, b) -> b.getValue() - a.getValue()  // Max heap
    );
    maxHeap.addAll(freqMap.entrySet());
    
    // Step 3: Build result
    StringBuilder result = new StringBuilder();
    
    while (maxHeap.size() >= 2) {
        // Take two most frequent
        Map.Entry<Character, Integer> first = maxHeap.poll();
        Map.Entry<Character, Integer> second = maxHeap.poll();
        
        // Append both
        result.append(first.getKey());
        result.append(second.getKey());
        
        // Decrement and add back if count > 0
        if (first.getValue() > 1) {
            first.setValue(first.getValue() - 1);
            maxHeap.offer(first);
        }
        if (second.getValue() > 1) {
            second.setValue(second.getValue() - 1);
            maxHeap.offer(second);
        }
    }
    
    // Step 4: Handle remaining character (if any)
    if (!maxHeap.isEmpty()) {
        Map.Entry<Character, Integer> last = maxHeap.poll();
        if (last.getValue() > 1) {
            // More than 1 of the last character → impossible
            return "";
        }
        result.append(last.getKey());
    }
    
    return result.toString();
}
```

**Time Complexity:** O(n log k)
- n = string length
- k = number of unique characters
- Heap operations: O(log k) each
- Total heap operations: O(n)

**Space Complexity:** O(k) for frequency map and heap

---

## 📊 Step-by-Step Walkthrough

### Example: `"aaabbc"`

**Step 1: Count Frequencies**
```
freqMap = {a: 3, b: 2, c: 1}
```

**Step 2: Build Max Heap**
```
maxHeap = [(a,3), (b,2), (c,1)]  // Ordered by frequency
```

**Step 3: Process Pairs**

| Iteration | Top 2 | Result | Heap After |
|-----------|-------|--------|------------|
| 1 | (a,3), (b,2) | "ab" | [(a,2), (b,1), (c,1)] |
| 2 | (a,2), (b,1) | "abab" | [(a,1), (c,1)] |
| 3 | (a,1), (c,1) | "ababac" | [] |

**Final Result:** `"ababac"` ✓

---

## 🎯 Alternative Solution: Fill Even/Odd Positions

Simpler approach when you understand the pattern:

```java
public static String rearrangeStringAlternate(String s) {
    if (s == null || s.isEmpty()) {
        return s;
    }
    
    // Count frequencies
    Map<Character, Integer> freqMap = new HashMap<>();
    for (char c : s.toCharArray()) {
        freqMap.put(c, freqMap.getOrDefault(c, 0) + 1);
    }
    
    // Check if rearrangement is possible
    int maxFreq = Collections.max(freqMap.values());
    if (maxFreq > (s.length() + 1) / 2) {
        return "";  // Impossible
    }
    
    // Sort characters by frequency (descending)
    List<Map.Entry<Character, Integer>> sorted = new ArrayList<>(freqMap.entrySet());
    sorted.sort((a, b) -> b.getValue() - a.getValue());
    
    // Fill positions: even indices first (0, 2, 4, ...), then odd (1, 3, 5, ...)
    char[] result = new char[s.length()];
    int index = 0;
    
    for (Map.Entry<Character, Integer> entry : sorted) {
        char ch = entry.getKey();
        int count = entry.getValue();
        
        while (count > 0) {
            result[index] = ch;
            index += 2;  // Jump by 2 (even positions: 0, 2, 4, ...)
            
            if (index >= s.length()) {
                index = 1;  // Switch to odd positions: 1, 3, 5, ...
            }
            count--;
        }
    }
    
    return new String(result);
}
```

**Example:** `"aaabbc"`
```
Sorted by freq: [(a,3), (b,2), (c,1)]

Fill even positions (0, 2, 4):
- Place 3 a's: result = ['a', _, 'a', _, 'a', _]

Fill remaining even/odd:
- Place 2 b's at index 1, 3: result = ['a', 'b', 'a', 'b', 'a', _]
- Place 1 c at index 5: result = ['a', 'b', 'a', 'b', 'a', 'c']

Result: "ababac" ✓
```

---

## 📊 Test Cases

### Test Case 1: Basic Example
```java
String input = "aaabbc";
String result = rearrangeString(input);
System.out.println(result);
```
**Expected Output:** `"ababac"` (or any valid rearrangement)

### Test Case 2: Impossible Case
```java
String input = "aaaa";
String result = rearrangeString(input);
System.out.println(result);
```
**Expected Output:** `""` (empty string)

### Test Case 3: Simple Case
```java
String input = "aab";
String result = rearrangeString(input);
System.out.println(result);
```
**Expected Output:** `"aba"` (or "baa")

### Test Case 4: All Unique
```java
String input = "abc";
String result = rearrangeString(input);
System.out.println(result);
```
**Expected Output:** `"abc"` (or any permutation)

### Test Case 5: Two Characters
```java
String input = "aabb";
String result = rearrangeString(input);
System.out.println(result);
```
**Expected Output:** `"abab"` (or "baba")

### Test Case 6: Edge Case - Just Possible
```java
String input = "aaabc";
String result = rearrangeString(input);
System.out.println(result);
```
**Expected Output:** `"abaca"` (or similar)

---

## Interview Q&A

### Q1: "How do you know if rearrangement is impossible?"

**Answer:**
```
Mathematical Condition:
If any character appears MORE than ⌈n/2⌉ times, it's impossible.

Proof:
- String length: n
- If we place most frequent char at positions: 0, 2, 4, 6, ...
- Maximum positions available: ⌈n/2⌉

Examples:
String "aaaa" (length 4):
- Max positions: ⌈4/2⌉ = 2
- 'a' appears 4 times > 2 → IMPOSSIBLE ✗

String "aaabbc" (length 6):
- Max positions: ⌈6/2⌉ = 3
- 'a' appears 3 times = 3 → POSSIBLE ✓
- Result: a_a_a_ (fill blanks with b, b, c)

String "aaabc" (length 5):
- Max positions: ⌈5/2⌉ = 3
- 'a' appears 3 times = 3 → POSSIBLE ✓
- Result: a_a_a (fill blanks with b, c)

Implementation:
int maxFreq = Collections.max(freqMap.values());
if (maxFreq > (s.length() + 1) / 2) {
    return "";  // Impossible
}
```

### Q2: "Why use Max Heap instead of sorting once?"

**Answer:**
```
Approach 1: Max Heap (Dynamic)
- Pull top 2 characters
- Use them
- Decrease count and re-insert
- Heap automatically re-orders
- Time: O(n log k) for n heap operations

Approach 2: Sorting (Static)
- Sort all characters by frequency once
- Fill positions sequentially
- Time: O(k log k) for sorting + O(n) for filling
- Total: O(n + k log k)

Comparison:
For n = 1000, k = 26 (lowercase English):
- Heap: O(1000 × log 26) ≈ 4700 operations
- Sort: O(26 × log 26) + O(1000) ≈ 1120 operations

Sorting is FASTER for small k!

When to use each:
- Small character set (a-z): Sorting approach better
- Large character set (Unicode): Heap approach better
- Dynamic updates: Heap is more flexible

In interviews: Show both! Demonstrate understanding of tradeoffs.
```

### Q3: "What if we need exactly K different characters between same characters?"

**Answer:**
```java
// E.g., K=2 means: a__a__a (at least 2 chars between same)

public static String rearrangeStringWithGap(String s, int k) {
    if (k == 0) {
        return s;  // No restriction
    }
    
    Map<Character, Integer> freqMap = new HashMap<>();
    for (char c : s.toCharArray()) {
        freqMap.put(c, freqMap.getOrDefault(c, 0) + 1);
    }
    
    // Check if possible
    int maxFreq = Collections.max(freqMap.values());
    int uniqueChars = freqMap.size();
    
    // Need (maxFreq - 1) gaps, each gap needs k different chars
    // Total chars needed for gaps: (maxFreq - 1) × k
    // Remaining chars available: n - maxFreq
    if ((maxFreq - 1) * k > s.length() - maxFreq) {
        return "";  // Impossible
    }
    
    // Build result similar to before, but ensure gap of k
    PriorityQueue<Map.Entry<Character, Integer>> maxHeap = new PriorityQueue<>(
        (a, b) -> b.getValue() - a.getValue()
    );
    maxHeap.addAll(freqMap.entrySet());
    
    Queue<Map.Entry<Character, Integer>> cooldown = new LinkedList<>();
    StringBuilder result = new StringBuilder();
    
    while (!maxHeap.isEmpty()) {
        Map.Entry<Character, Integer> current = maxHeap.poll();
        result.append(current.getKey());
        current.setValue(current.getValue() - 1);
        
        cooldown.offer(current);
        
        // After k characters, we can use this character again
        if (cooldown.size() == k) {
            Map.Entry<Character, Integer> ready = cooldown.poll();
            if (ready.getValue() > 0) {
                maxHeap.offer(ready);
            }
        }
    }
    
    return result.length() == s.length() ? result.toString() : "";
}

// Example: s = "aaabbc", k = 2
// Result: "abacab" (a's are separated by at least 2 chars: b, a, c)
```

### Q4: "Can you solve this without a heap?"

**Answer:**
```java
// Yes! Greedy with frequency tracking

public static String rearrangeStringNoHeap(String s) {
    if (s == null || s.isEmpty()) {
        return s;
    }
    
    // Count frequencies
    int[] freq = new int[26];
    for (char c : s.toCharArray()) {
        freq[c - 'a']++;
    }
    
    StringBuilder result = new StringBuilder();
    char prevChar = '\0';  // Track previous character
    
    for (int i = 0; i < s.length(); i++) {
        // Find character with max frequency (excluding previous)
        int maxFreq = 0;
        int maxIdx = -1;
        
        for (int j = 0; j < 26; j++) {
            char candidate = (char)('a' + j);
            if (freq[j] > maxFreq && candidate != prevChar) {
                maxFreq = freq[j];
                maxIdx = j;
            }
        }
        
        if (maxIdx == -1) {
            return "";  // No valid character found
        }
        
        char chosen = (char)('a' + maxIdx);
        result.append(chosen);
        freq[maxIdx]--;
        prevChar = chosen;
    }
    
    return result.toString();
}

// Time Complexity: O(n × k) where k = 26 (constant)
// For each of n positions, scan 26 characters
// Slower than heap but simpler code
```

### Q5: "What if we want lexicographically smallest valid arrangement?"

**Answer:**
```java
// Modified heap: break ties by character order

public static String rearrangeStringLexicographic(String s) {
    Map<Character, Integer> freqMap = new HashMap<>();
    for (char c : s.toCharArray()) {
        freqMap.put(c, freqMap.getOrDefault(c, 0) + 1);
    }
    
    // Max heap: first by frequency (desc), then by character (asc)
    PriorityQueue<Map.Entry<Character, Integer>> maxHeap = new PriorityQueue<>(
        (a, b) -> {
            if (a.getValue() != b.getValue()) {
                return b.getValue() - a.getValue();  // Higher frequency first
            }
            return a.getKey() - b.getKey();  // Alphabetically first
        }
    );
    maxHeap.addAll(freqMap.entrySet());
    
    // Rest of algorithm stays the same...
    
    // Example: "aaabbc"
    // freqMap: {a:3, b:2, c:1}
    // Heap: [(a,3), (b,2), (c,1)]
    // Result: "ababac" (chose 'a' over others when freq is same)
}
```

---

## Common Mistakes

### ❌ Mistake 1: Not Checking if Rearrangement is Possible
```java
// WRONG - Doesn't validate first
public static String rearrange(String s) {
    // ... build heap and start placing characters
    // If impossible, result will have adjacent duplicates!
}

// CORRECT - Check first
int maxFreq = Collections.max(freqMap.values());
if (maxFreq > (s.length() + 1) / 2) {
    return "";
}
```

### ❌ Mistake 2: Only Taking One Character at a Time
```java
// WRONG - Can create adjacent duplicates
while (!maxHeap.isEmpty()) {
    Entry<Character, Integer> entry = maxHeap.poll();
    result.append(entry.getKey());
    // Decrement and re-add...
}

// If same character is still max, it gets placed twice!
// Example: "aaa" → Heap: [(a,3)] → append 'a' → Heap: [(a,2)] → append 'a' again!

// CORRECT - Take TWO at a time
while (maxHeap.size() >= 2) {
    Entry<Character, Integer> first = maxHeap.poll();
    Entry<Character, Integer> second = maxHeap.poll();
    result.append(first.getKey()).append(second.getKey());
    // ...
}
```

### ❌ Mistake 3: Not Handling Last Character
```java
// WRONG - Forgets last character when heap.size() == 1
while (maxHeap.size() >= 2) {
    // Process pairs...
}
// Missing: check if one character remains

// CORRECT
while (maxHeap.size() >= 2) {
    // Process pairs...
}
if (!maxHeap.isEmpty()) {
    Entry<Character, Integer> last = maxHeap.poll();
    if (last.getValue() > 1) {
        return "";  // More than 1 of last char → impossible
    }
    result.append(last.getKey());
}
```

### ❌ Mistake 4: Modifying Immutable Entry Objects
```java
// WRONG - Entry from HashMap is not always mutable
Entry<Character, Integer> entry = maxHeap.poll();
entry.setValue(entry.getValue() - 1);  // Might not work!

// SAFER - Create new entry
Entry<Character, Integer> entry = maxHeap.poll();
if (entry.getValue() > 1) {
    maxHeap.offer(new AbstractMap.SimpleEntry<>(
        entry.getKey(), 
        entry.getValue() - 1
    ));
}

// Or use custom class:
class CharFreq {
    char ch;
    int freq;
    CharFreq(char ch, int freq) {
        this.ch = ch;
        this.freq = freq;
    }
}
```

---

## Complete Working Code

```java
import java.util.*;

public class RearrangeString {
    
    // Solution 1: Max Heap Approach
    public static String rearrangeString(String s) {
        if (s == null || s.isEmpty()) {
            return s;
        }
        
        Map<Character, Integer> freqMap = new HashMap<>();
        for (char c : s.toCharArray()) {
            freqMap.put(c, freqMap.getOrDefault(c, 0) + 1);
        }
        
        PriorityQueue<Map.Entry<Character, Integer>> maxHeap = new PriorityQueue<>(
            (a, b) -> b.getValue() - a.getValue()
        );
        maxHeap.addAll(freqMap.entrySet());
        
        StringBuilder result = new StringBuilder();
        
        while (maxHeap.size() >= 2) {
            Map.Entry<Character, Integer> first = maxHeap.poll();
            Map.Entry<Character, Integer> second = maxHeap.poll();
            
            result.append(first.getKey());
            result.append(second.getKey());
            
            if (first.getValue() > 1) {
                first.setValue(first.getValue() - 1);
                maxHeap.offer(first);
            }
            if (second.getValue() > 1) {
                second.setValue(second.getValue() - 1);
                maxHeap.offer(second);
            }
        }
        
        if (!maxHeap.isEmpty()) {
            Map.Entry<Character, Integer> last = maxHeap.poll();
            if (last.getValue() > 1) {
                return "";
            }
            result.append(last.getKey());
        }
        
        return result.toString();
    }
    
    // Solution 2: Fill Even/Odd Positions
    public static String rearrangeStringAlternate(String s) {
        if (s == null || s.isEmpty()) {
            return s;
        }
        
        Map<Character, Integer> freqMap = new HashMap<>();
        for (char c : s.toCharArray()) {
            freqMap.put(c, freqMap.getOrDefault(c, 0) + 1);
        }
        
        int maxFreq = Collections.max(freqMap.values());
        if (maxFreq > (s.length() + 1) / 2) {
            return "";
        }
        
        List<Map.Entry<Character, Integer>> sorted = new ArrayList<>(freqMap.entrySet());
        sorted.sort((a, b) -> b.getValue() - a.getValue());
        
        char[] result = new char[s.length()];
        int index = 0;
        
        for (Map.Entry<Character, Integer> entry : sorted) {
            char ch = entry.getKey();
            int count = entry.getValue();
            
            while (count > 0) {
                result[index] = ch;
                index += 2;
                
                if (index >= s.length()) {
                    index = 1;
                }
                count--;
            }
        }
        
        return new String(result);
    }

    public static void main(String[] args) {
        // Test case 1
        System.out.println(rearrangeString("aaabbc"));  // "ababac" or similar
        
        // Test case 2
        System.out.println(rearrangeString("aaaa"));  // ""
        
        // Test case 3
        System.out.println(rearrangeString("aab"));  // "aba"
        
        // Test case 4
        System.out.println(rearrangeStringAlternate("aaabbc"));  // "ababac"
    }
}
```

---

## Key Takeaways

| Concept | Why Important | Interview Score |
|---------|---------------|-----------------|
| Greedy algorithm with heap | Advanced problem-solving | ⭐⭐⭐⭐⭐ |
| Impossibility detection | Edge case handling | ⭐⭐⭐⭐⭐ |
| Two-at-a-time pattern | Avoiding adjacent duplicates | ⭐⭐⭐⭐ |
| Even/odd position filling | Alternative elegant approach | ⭐⭐⭐⭐ |
| Frequency-based reasoning | Core algorithmic intuition | ⭐⭐⭐⭐ |

---

**Priority:** ✅ SHOULD KNOW (Tests greedy algorithms and heap usage)

**Related Problems:**
- Task Scheduler
- Reorganize String (same problem, different name)
- Distant Barcodes
- Rearrange String K Distance Apart

---

**Last Updated:** March 1, 2026
