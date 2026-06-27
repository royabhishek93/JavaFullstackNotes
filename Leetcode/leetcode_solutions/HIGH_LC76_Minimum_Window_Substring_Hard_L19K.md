# LC 76: Minimum Window Substring

**Link**: [leetcode.com/problems/minimum-window-substring](https://leetcode.com/problems/minimum-window-substring/)

## Problem
Given two strings s and t, return the minimum window substring of s that contains all the characters in t. If there is no such window, return empty string "".

### Examples
- Input: s = "ADOBECODEBANC", t = "ABC" → Output: "BANC"
- Input: s = "a", t = "aa" → Output: ""
- Input: s = "ab", t = "b" → Output: "b"

## Optimized Approach: Sliding Window with Two HashMaps

```java
public String minWindow(String s, String t) {
    if (s == null || s.length() == 0 || t == null || t.length() == 0) {
        return "";
    }

    // Map 1: Target characters and their required counts
    Map<Character, Integer> target = new HashMap<>();
    for (char c : t.toCharArray()) {
        target.put(c, target.getOrDefault(c, 0) + 1);
    }

    // Map 2: Characters in current window and their counts
    Map<Character, Integer> window = new HashMap<>();

    int left = 0;
    int minLen = Integer.MAX_VALUE;
    int minStart = 0;
    int matched = 0;  // How many unique target chars have met their count requirement

    for (int right = 0; right < s.length(); right++) {
        char rightChar = s.charAt(right);
        
        // Add character to window
        window.put(rightChar, window.getOrDefault(rightChar, 0) + 1);

        // If this character's count now matches target requirement
        if (target.containsKey(rightChar) && 
            window.get(rightChar).equals(target.get(rightChar))) {
            matched++;
        }

        // Shrink window from left while all target chars are satisfied
        while (matched == target.size()) {
            // Update result with current valid window
            if (right - left + 1 < minLen) {
                minLen = right - left + 1;
                minStart = left;
            }

            // Try to shrink from left
            char leftChar = s.charAt(left);
            window.put(leftChar, window.get(leftChar) - 1);

            // If this removal breaks a requirement, stop shrinking
            if (target.containsKey(leftChar) && 
                window.get(leftChar) < target.get(leftChar)) {
                matched--;
            }

            left++;
        }
    }

    return minLen == Integer.MAX_VALUE ? "" : s.substring(minStart, minStart + minLen);
}
```

**Time Complexity**: O(n + m) where n = s.length, m = t.length  
**Space Complexity**: O(1) - max 26 unique characters

## Key Insights
- **Two HashMaps**: target (required) and window (current)
- **Matched Counter**: Track how many target chars have sufficient count
- **Expand Right**: Always move right pointer to populate window  
- **Shrink Left**: When valid, try to minimize window while maintaining validity
- **Update Result**: Record minimum window found

## Interview Walkthrough
1. **Problem**: Find shortest substring containing ALL characters from t
2. **Insight**: Use sliding window to avoid checking all O(n²) substrings
3. **Algorithm**:
   - Build target map with required character counts
   - Use two pointers (left, right) for window
   - Expand right to include more characters
   - When all target chars satisfied, shrink left to minimize
   - Track the smallest valid window
4. **Key Decision**: When do we consider window "valid"?
   - Every required character from t appears with required frequency
   - Use matched counter to track this efficiently

## Why This Approach (Optimal)
- ✅ **O(n) time**: Each character visited twice at most (once by right, once by left)
- ✅ **Early termination**: Shrink when valid, not scanning all substrings
- ✅ **Space efficient**: Only store unique characters (max 26)

## Critical Details
- **Matched logic**: Increment when reaching requirement, decrement when falling below
- **Use equals()**: For Integer comparison (not ==)
- **Window bounds**: right - left + 1 for size
- **Special cases**: Empty t, no valid window, t longer than s

## Common Mistakes
- Not using `matched` counter → O(n²) checking each character
- Confusing expand/shrink conditions
- Not copying matched count before shrinking
- Returning wrong indices or substring bounds

## Tips and Tricks
- "This is like two pointer with HashMaps for O(1) validation"
- "Matched counter tracks how many unique chars have correct frequency"
- "Shrink only when valid, to minimize window size"
- "Why O(n)? Each char processed at most twice (once by right, once by left)"
- "Walk through 'ADOBECODEBANC' and t='ABC' step by step"

## Related Problems
- **LC 438**: Find All Anagrams (fixed window size)
- **LC 567**: Permutation in String (similar logic)
- **LC 209**: Minimum Size Subarray Sum (numeric version)
- **LC 3**: Longest Substring Without Repeating (simpler sliding window)
