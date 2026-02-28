# Q4: Max Vowels in Substring of Size K (Sliding Window)

**Study Time:** 4-5 minutes | **Frequency:** 65% in coding interviews | **Difficulty:** ⭐⭐⭐

---

## The Problem

**Given:**
- A string `s`
- An integer `k`

**Find:** The **maximum number of vowels** in ANY substring of exactly size `k`

### Example 1
```
Input: s = "abciiidef", k = 3
Output: 3

Explanation:
Substrings of size 3:
- "abc" → 1 vowel (a)
- "bci" → 1 vowel (i)
- "cii" → 2 vowels (i, i)
- "iii" → 3 vowels (i, i, i)  ← Maximum = 3
- "iid" → 2 vowels (i, i)
- "ide" → 2 vowels (i, e)
- "def" → 1 vowel (e)

Answer: 3
```

### Example 2
```
Input: s = "rhythms", k = 4
Output: 0

Explanation:
"rhythms" has NO vowels (a, e, i, o, u)
Answer: 0
```

---

## 🔥 Core Approach: Sliding Window

**Why Sliding Window?**
- Brute force: Generate all substrings → O(n * k)
- Sliding window: Maintain a fixed-size window → O(n)

**Idea:**
1. Count vowels in first window (indices 0 to k-1)
2. Slide window right: Add new element, remove leftmost element
3. Update max vowel count at each step

---

## Step-by-Step Solution

### Code

```java
public static int maxVowels(String s, int k) {
    int maxCount = 0;
    int count = 0;
    
    // Step 1: Count vowels in first window [0, k-1]
    for (int i = 0; i < k; i++) {
        if (isVowel(s.charAt(i))) {
            count++;
        }
    }
    maxCount = count;
    
    // Step 2: Slide window from k to end
    for (int i = k; i < s.length(); i++) {
        // Add new element (right side)
        if (isVowel(s.charAt(i))) {
            count++;
        }
        
        // Remove leftmost element (left side shifts right)
        if (isVowel(s.charAt(i - k))) {
            count--;
        }
        
        // Update max
        maxCount = Math.max(maxCount, count);
    }
    
    return maxCount;
}

// Helper: Check if character is vowel
public static boolean isVowel(char c) {
    c = Character.toLowerCase(c);
    return c == 'a' || c == 'e' || c == 'i' || c == 'o' || c == 'u';
}
```

---

## Walkthrough: `s = "abciiidef"`, `k = 3`

### Step 1: First Window [0, 2] = "abc"

```
Window: "abc"
Vowels: a (1), b (0), c (0)
count = 1
maxCount = 1
```

### Step 2: Slide to [1, 3] = "bci"

```
i = 3:
  Add s[3]='i' → isVowel('i')? YES → count++ (now 2)
  Remove s[0]='a' → isVowel('a')? YES → count-- (now 1)
  maxCount = max(1, 1) = 1
```

### Step 3: Slide to [2, 4] = "cii"

```
i = 4:
  Add s[4]='i' → isVowel('i')? YES → count++ (now 2)
  Remove s[1]='b' → isVowel('b')? NO → count stays 2
  maxCount = max(1, 2) = 2
```

### Step 4: Slide to [3, 5] = "iii"

```
i = 5:
  Add s[5]='i' → isVowel('i')? YES → count++ (now 3)
  Remove s[2]='c' → isVowel('c')? NO → count stays 3
  maxCount = max(2, 3) = 3
```

### Continue...

```
i = 6: Window "iid" → count = 2, maxCount = 3
i = 7: Window "ide" → count = 2, maxCount = 3
i = 8: Window "def" → count = 1, maxCount = 3
```

**Answer: 3** ✅

---

## Complexity Analysis

| Aspect | Value |
|--------|-------|
| **Time Complexity** | O(n) - single pass through string |
| **Space Complexity** | O(1) - only using count and maxCount |
| **Optimal?** | Yes, can't do better than O(n) |

---

## Real Interview Answer (2-3 minutes)

"This is a sliding window problem. I maintain a fixed-size window of k characters and track vowel count. I count vowels in the first window, then slide the window right by removing the leftmost character and adding the new rightmost character. This way, I only update the vowel count incrementally instead of recounting from scratch. Time complexity is O(n) with O(1) space."

---

## ⚠️ Common Pitfalls

**Pitfall 1: Recounting vowels for each window (brute force)**

❌ **Wrong approach:**
```java
public static int maxVowels(String s, int k) {
    int maxCount = 0;
    
    // ❌ Recounting from scratch each time
    for (int i = 0; i <= s.length() - k; i++) {
        int count = 0;
        for (int j = i; j < i + k; j++) {
            if (isVowel(s.charAt(j))) {
                count++;
            }
        }
        maxCount = Math.max(maxCount, count);
    }
    
    return maxCount;
}
```
**Why it fails:** Time complexity O(n * k) instead of O(n). With k=1000 and n=100,000, this times out.

✅ **Right approach:**
```java
// Sliding window - increment/decrement, don't recount
// Time complexity O(n)
```

---

**Pitfall 2: Off-by-one error in window indices**

❌ **Wrong approach:**
```java
// Wrong: First loop counts [0, k-1], but second loop misses k
for (int i = 0; i < k; i++) {
    if (isVowel(s.charAt(i))) count++;
}

// This loop misses index k!
for (int i = k + 1; i < s.length(); i++) {  // ❌ Starts at k+1
    ...
}
```
**Why it fails:** Skips substring [k-1, k+1], giving wrong answer.

✅ **Right approach:**
```java
// First window: [0, k-1]
for (int i = 0; i < k; i++) {
    if (isVowel(s.charAt(i))) count++;
}

// Slide: start at k, remove i-k
for (int i = k; i < s.length(); i++) {  // ✅ Starts at k
    if (isVowel(s.charAt(i))) count++;
    if (isVowel(s.charAt(i - k))) count--;
    maxCount = Math.max(maxCount, count);
}
```

---

**Pitfall 3: Wrong vowel detection (case sensitivity)**

❌ **Wrong approach:**
```java
public static boolean isVowel(char c) {
    return c == 'a' || c == 'e' || c == 'i' || c == 'o' || c == 'u';
    // Missing uppercase: A, E, I, O, U
}
```
**Why it fails:** If input has uppercase (e.g., "AbCdEf"), misses them.

✅ **Right approach:**
```java
public static boolean isVowel(char c) {
    c = Character.toLowerCase(c);  // Normalize
    return c == 'a' || c == 'e' || c == 'i' || c == 'o' || c == 'u';
}
```

---

## 🛑 When NOT to Use Sliding Window

1. **When you need multiple different window sizes** → Solve each separately
2. **When order matters differently** → Use different approach
3. **On unsorted arrays** → Sliding window assumes contiguity
4. **For non-continuous subarrays** → Sliding window finds continuous only

---

## Quick Checklist

- ✅ **Problem type:** Fixed-size sliding window
- ✅ **Window size:** k (given)
- ✅ **What to track:** Vowel count in current window
- ✅ **Slide operation:** Remove left (i-k), add right (i)
- ✅ **Time:** O(n) - single pass
- ✅ **Space:** O(1) - no extra data structure
- ✅ **Answer:** Maximum count seen

---

## Variations

### Variation 1: Max K-Length Substring with Most Vowels (where k is variable)

Use dynamic sliding window that adjusts size.

### Variation 2: Count of All K-Length Substrings with Exactly 3 Vowels

Maintain count instead of max.

### Variation 3: Max Consonants Instead of Vowels

Flip the isVowel check → !isVowel(c)

---

**Last Updated:** February 28, 2026
