# LC 424: Longest Repeating Character Replacement

**Link**: [leetcode.com/problems/longest-repeating-character-replacement](https://leetcode.com/problems/longest-repeating-character-replacement/)

## Problem
You are given a string s and an integer k. You can choose any character of the string and change it to any other uppercase English character. You can perform this operation at most k times. Return the length of the longest substring containing the same letter you can get after performing the above operations.

### Examples
- Input: s = "ABAB", k = 2 → Output: 4 (replace both 'B' with 'A')
- Input: s = "AABABBA", k = 1 → Output: 4 (substring "AAAA" by replacing one 'B')

## Optimized Approach: Sliding Window with Maximum Frequency

```java
public int characterReplacement(String s, int k) {
    // Map to count frequency of each character in window
    Map<Character, Integer> count = new HashMap<>();
    
    int left = 0;
    int maxCount = 0;  // Most frequent character in current window
    int result = 0;    // Max length found

    for (int right = 0; right < s.length(); right++) {
        char rightChar = s.charAt(right);
        
        // Add right character to window
        count.put(rightChar, count.getOrDefault(rightChar, 0) + 1);
        
        // Update maxCount (most frequent char in window)
        maxCount = Math.max(maxCount, count.get(rightChar));

        // Window is invalid if: num_replacements_needed > k
        // num_replacements_needed = window_size - max_freq_char
        while (right - left + 1 - maxCount > k) {
            // Shrink window from left
            char leftChar = s.charAt(left);
            count.put(leftChar, count.get(leftChar) - 1);
            left++;
        }

        // Update result with current valid window length
        result = Math.max(result, right - left + 1);
    }

    return result;
}
```

**Time Complexity**: O(n) - each element processed at most twice  
**Space Complexity**: O(1) - at most 26 uppercase letters

## Key Insights
- **maxCount tracking**: Most frequent character in current window
- **Replacements needed**: window_size - max_freq_char
- **Keep shrinking**: Only when replacements_needed > k
- **Update result**: After ensuring window validity

## Interview Walkthrough
1. **Problem**: Maximize substring where we can make all chars same with <= k replacements
2. **Key Insight**: For a window to be valid:
   - Choose most frequent character
   - Replace all others (at most k replacements)
   - Valid if: window_size - max_freq_char <= k
3. **Algorithm**:
   - Expand right: add character, update max frequency
   - Track most frequent character in current window
   - Shrink left: when too many replacements needed
   - Keep window as large as possible
4. **Why maxCount matters**: 
   - Don't need to count all chars
   - Only the most frequent one matters
   - All others get replaced

## Why This Approach (Optimal)
- ✅ **O(n) time**: Two pointers each pass once
- ✅ **O(1) space**: At most 26 letters
- ✅ **Greedy**: Always choose most frequent to maximize window

## Critical Details
- **maxCount never decreases**: Only increases or stays same (important!)
- **Validity check**: window_size - maxCount <= k
- **Window size**: right - left + 1
- **Update maxCount after adding**: Before checking validity

## Common Mistakes
- Not tracking maxCount → need to recalculate every iteration O(n²)
- Using maxCount from entire string instead of window only
- Off-by-one in validity check
- Not updating result inside while loop
- Forgetting to shrink when invalid

## Tips and Tricks
- "We want to keep same character and replace others"
- "maxCount is the most frequent char in CURRENT window"
- "Valid window means: (window_size - most_freq) <= k"
- "Why not recalculate maxCount after shrinking? We can ignore decreases!"
- "The key optimization: maxCount is monotonic (never decreases)"

## Key Optimization Explained
```
Why maxCount never moves backward:
- It represents the best frequency we've achieved
- Even if we shrink window, maxCount stays same
- We only update when we find better frequency
- This is what makes O(n) possible instead of O(n²)
```

## Related Problems
- **LC 3**: Longest Substring Without Repeating (no replacements)
- **LC 209**: Minimum Size Subarray Sum (numeric instead of chars)
- **LC 76**: Minimum Window Substring (different condition)
- **LC 438**: Find All Anagrams (different approach)
