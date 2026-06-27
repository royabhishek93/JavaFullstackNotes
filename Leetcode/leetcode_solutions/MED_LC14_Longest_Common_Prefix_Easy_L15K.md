# LC 14: Longest Common Prefix

**Link**: [leetcode.com/problems/longest-common-prefix](https://leetcode.com/problems/longest-common-prefix/)

## Problem
Write a function to find the longest common prefix string amongst an array of strings.

## Optimized Approach: Vertical Scanning

```java
public String longestCommonPrefix(String[] strs) {
    if (strs == null || strs.length == 0) return "";

    for (int i = 0; i < strs[0].length(); i++) {
        char c = strs[0].charAt(i);
        for (int j = 1; j < strs.length; j++) {
            if (i >= strs[j].length() || strs[j].charAt(i) != c) {
                return strs[0].substring(0, i);
            }
        }
    }

    return strs[0];
}
```

**Time Complexity**: O(S) where S is total compared characters  
**Space Complexity**: O(1)

## Key Insights
- Compare characters column by column
- Stop at first mismatch
- Handles different length strings naturally

## Tips and Tricks
- Single-pass scanning problems usually become easy once you define the stopping condition.
- Trim or skip irrelevant characters early to keep the core logic linear.
- Think carefully about what should happen at the end of the scan, not just during it.

## Related Problems
- LC 28 Find the Index of the First Occurrence in a String
