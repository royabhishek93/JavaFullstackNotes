# LC 3: Longest Substring Without Repeating Characters

**Link**: [leetcode.com/problems/longest-substring-without-repeating-characters](https://leetcode.com/problems/longest-substring-without-repeating-characters/)

## Problem
Given a string s, find the length of the longest substring without repeating characters.

### Examples
- Input: s = "abcabcbb" → Output: 3 (substring "abc")
- Input: s = "bbbbb" → Output: 1 (substring "b")
- Input: s = "pwwkew" → Output: 3 (substring "wke")

## Optimized Approach: Sliding Window with HashMap

```java
public int lengthOfLongestSubstring(String s) {
    if (s == null || s.length() == 0) {
        return 0;
    }

    Map<Character, Integer> charIndexMap = new HashMap<>();
    int left = 0, maxLength = 0;

    for (int right = 0; right < s.length(); right++) {
        char currentChar = s.charAt(right);

        if (charIndexMap.containsKey(currentChar)) {
            left = Math.max(left, charIndexMap.get(currentChar) + 1);
        }

        charIndexMap.put(currentChar, right);
        maxLength = Math.max(maxLength, right - left + 1);
    }

    return maxLength;
}
```

**Time Complexity**: O(n)  
**Space Complexity**: O(min(n, m)) where m is charset size  

## Key Insights
- **HashMap Role**: Store character → most recent index mapping
- **Window Validity**: All characters in [left, right] are unique
- **Move Left Pointer**: When duplicate found, move LEFT to position after the previous occurrence
- **Max(left, ...)**: Prevent left pointer from moving backward
- **Window Size**: right - left + 1 at each step

## Interview Walkthrough
1. **Problem**: Find longest substring WITHOUT repeating characters
2. **Brute Force**: Check all substrings O(n³), validate each O(n)
3. **Optimization**: "We can track seen characters and move left pointer when we find duplicates"
4. **Two Pointer Pattern**: left and right pointers with HashMap for O(1) lookups
5. **Key Decision**: When duplicate found, update left but don't shrink unnecessarily (use Math.max)
6. **Trace Example**: "s = 'abcabcbb'" → window grows: "a", "ab", "abc", then "bca", "cab", "abc", "bc", "c"

## Common Mistakes
- Not using Math.max when updating left → pointer goes backward
- Forgetting to store character → can't detect duplicates
- Updating maxLength before moving left → incorrect counts
- Using charIndex[char] without checking if exists → need HashMap
                maxLen = Math.max(maxLen, j - i + 1);
            }
        }
    }
    return maxLen;
}

private boolean allUnique(String s, int start, int end) {
    Set<Character> set = new HashSet<>();
    for (int i = start; i <= end; i++) {
        if (set.contains(s.charAt(i))) {
            return false;
        }
        set.add(s.charAt(i));
    }
    return true;
}
```
**Complexity**: O(n³) time, O(m) space

## Key Insights
- **Sliding Window**: Expand with right pointer, shrink with left pointer
- **HashMap Optimization**: Jump left pointer directly to position after duplicate
- **HashSet Alternative**: Move left pointer one step at a time
- **Valid Window**: All characters in [left, right] are unique

## Tips and Tricks
1. "Use sliding window pattern..."
2. "Expand window with right pointer..."
3. "Shrink window when duplicate found..."
4. "Track maximum window size..."
5. "Optimization: HashMap lets us jump left pointer directly..."
