# LC 567: Permutation in String

**Link**: [leetcode.com/problems/permutation-in-string](https://leetcode.com/problems/permutation-in-string/)

## Problem
Given two strings s1 and s2, return true if s2 contains a permutation of s1, or false otherwise. You may assume the input strings only contain lowercase English letters.

### Examples
- Input: s1 = "ab", s2 = "eidbaooo" → Output: true (s2 contains "ba")
- Input: s1 = "ab", s2 = "eidboaoo" → Output: false
- Input: s1 = "a", s2 = "a" → Output: true

## Optimized Approach: Fixed-Size Sliding Window

```java
public boolean checkInclusion(String s1, String s2) {
    if (s1.length() > s2.length()) {
        return false;
    }

    // Map target: character counts in s1
    Map<Character, Integer> target = new HashMap<>();
    for (char c : s1.toCharArray()) {
        target.put(c, target.getOrDefault(c, 0) + 1);
    }

    // Map window: character counts in current window
    Map<Character, Integer> window = new HashMap<>();
    int windowSize = s1.length();

    // Initialize first window
    for (int i = 0; i < windowSize; i++) {
        char c = s2.charAt(i);
        window.put(c, window.getOrDefault(c, 0) + 1);
    }

    // Check initial window
    if (window.equals(target)) {
        return true;
    }

    // Slide the window
    for (int right = windowSize; right < s2.length(); right++) {
        // Add new character to right
        char rightChar = s2.charAt(right);
        window.put(rightChar, window.getOrDefault(rightChar, 0) + 1);

        // Remove leftmost character
        char leftChar = s2.charAt(right - windowSize);
        window.put(leftChar, window.get(leftChar) - 1);
        if (window.get(leftChar) == 0) {
            window.remove(leftChar);
        }

        // Check if current window matches target
        if (window.equals(target)) {
            return true;  // Early return on first match
        }
    }

    return false;
}
```

**Time Complexity**: O(n) where n = s2.length  
**Space Complexity**: O(1) - max 26 unique characters

## Key Insights
- **Same as LC 438**: Logic is identical, only difference is return type
- **Early termination**: Return true immediately on first match
- **Permutation = Anagram**: Same frequencies, different order
- **Fixed window size**: Window size = s1.length()

## Interview Walkthrough
1. **Problem**: Check if s2 contains any permutation/anagram of s1
2. **Key Insight**: Permutation has same character frequencies in same quantity
3. **Algorithm**:
   - Build frequency map for s1
   - Slide fixed-size window through s2
   - When any window matches frequencies exactly, return true
   - If complete scan with no match, return false
4. **Difference from LC 438**: Need only ONE match (return early)

## Why This Approach (Optimal)
- ✅ **O(n) time**: Single pass through s2
- ✅ **Early exit**: Return true on first match
- ✅ **Clean logic**: Fixed window simplifies sliding

## Common Mistakes
- Not handling early termination (should return true immediately)
- Checking s1.length > s2.length upfront (avoids index errors)
- Map comparison with == instead of equals()
- Off-by-one in window calculation

## Tips and Tricks
- "A permutation has the same character frequencies as the original"
- "This is essentially 'anagram' detection in a string"
- "Fixed-size sliding window helps avoid complex shrinking logic"
- "Return early on first match - don't collect all like LC 438"
- "Compare: LC 438 finds all positions, LC 567 finds if any exists"

## Comparison with LC 438
| Aspect | LC 438 | LC 567 |
|--------|--------|--------|
| Return type | List of indices | Boolean |
| Stops early? | No, finds all | Yes, first match |
| Use case | Find all occurrences | Check existence |
| Time | O(n) | O(n) but faster in practice |

## Related Problems
- **LC 438**: Find All Anagrams (returns all starting indices)
- **LC 76**: Minimum Window Substring (variable window, harder)
- **LC 242**: Valid Anagram (simpler, just two strings)
- **LC 383**: Ransom Note (character frequency check)
