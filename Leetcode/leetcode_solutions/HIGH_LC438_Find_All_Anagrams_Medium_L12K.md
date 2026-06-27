# LC 438: Find All Anagrams in a String

**Link**: [leetcode.com/problems/find-all-anagrams-in-a-string](https://leetcode.com/problems/find-all-anagrams-in-a-string/)

## Problem
Given two strings s and p, return an array of all start indices of p's anagrams in s. You may return the answer in any order.

### Examples
- Input: s = "cbaebabacd", p = "abc" → Output: [0,6]
- Input: s = "abab", p = "ab" → Output: [0,1,2]

## Optimized Approach: Fixed-Size Sliding Window

```java
public List<Integer> findAnagrams(String s, String p) {
    List<Integer> result = new ArrayList<>();
    
    if (s.length() < p.length()) {
        return result;
    }

    // Map target: character counts in p
    Map<Character, Integer> target = new HashMap<>();
    for (char c : p.toCharArray()) {
        target.put(c, target.getOrDefault(c, 0) + 1);
    }

    // Map window: character counts in current window
    Map<Character, Integer> window = new HashMap<>();
    int windowSize = p.length();

    // Initialize first window
    for (int i = 0; i < windowSize; i++) {
        char c = s.charAt(i);
        window.put(c, window.getOrDefault(c, 0) + 1);
    }

    // Check if initial window matches
    if (window.equals(target)) {
        result.add(0);
    }

    // Slide the window
    for (int right = windowSize; right < s.length(); right++) {
        // Add new character to right side
        char rightChar = s.charAt(right);
        window.put(rightChar, window.getOrDefault(rightChar, 0) + 1);

        // Remove leftmost character
        char leftChar = s.charAt(right - windowSize);
        window.put(leftChar, window.get(leftChar) - 1);
        if (window.get(leftChar) == 0) {
            window.remove(leftChar);
        }

        // Check if current window matches target
        if (window.equals(target)) {
            result.add(right - windowSize + 1);
        }
    }

    return result;
}
```

**Time Complexity**: O(n) where n = s.length  
**Space Complexity**: O(1) - max 26 unique characters

## Key Insights
- **Fixed Window Size**: Window always = p.length()
- **Slide, not expand/shrink**: Remove left, add right each iteration
- **Map comparison**: Use equals() to check if window matches target
- **All anagrams**: Check every possible window position

## Interview Walkthrough
1. **Problem**: Find ALL starting positions where p's anagram appears in s
2. **Key Insight**: Anagrams have same character frequencies
3. **Algorithm**:
   - Build frequency map for p (target)
   - Create sliding window of size p.length()
   - For each position, slide window by: remove left, add right
   - When window frequencies match target, add starting index
4. **Why Fixed Size**: Anagram must match p's length exactly

## Why This Approach (Optimal)
- ✅ **O(n) time**: Single pass with window sliding
- ✅ **Simple logic**: Fixed window easier than variable
- ✅ **Direct comparison**: Maps can be directly compared with equals()

## Common Mistakes
- Not initializing first window → miss first anagram
- Incorrect window size calculation (right - windowSize + 1)
- Removing character without checking if count becomes 0
- Using == instead of equals() for map comparison
- Off-by-one errors in loop bounds

## Tips and Tricks
- "Anagrams have identical character frequencies"
- "Fixed-size window at size = pattern length"
- "Slide by removing left and adding right each step"
- "Use HashMap equals() to compare frequency maps"
- "Check every position where window could start"

## Related Problems
- **LC 76**: Minimum Window Substring (variable window, harder)
- **LC 567**: Permutation in String (same logic, returns boolean)
- **LC 242**: Valid Anagram (simpler, just check two strings)
- **LC 3**: Longest Substring Without Repeating (sliding window variant)
