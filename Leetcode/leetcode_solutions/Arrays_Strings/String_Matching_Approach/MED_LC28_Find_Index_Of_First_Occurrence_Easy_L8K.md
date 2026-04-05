# LC 28: Find the Index of the First Occurrence in a String

**Link**: [leetcode.com/problems/find-the-index-of-the-first-occurrence-in-a-string](https://leetcode.com/problems/find-the-index-of-the-first-occurrence-in-a-string/)

## Problem
Given strings `haystack` and `needle`, return the index of the first occurrence of `needle` in `haystack`, or `-1` if not found.

## Optimized Approach: Sliding Window Match

```java
public int strStr(String haystack, String needle) {
    if (needle.length() == 0) return 0;
    if (needle.length() > haystack.length()) return -1;

    for (int i = 0; i <= haystack.length() - needle.length(); i++) {
        int j = 0;
        while (j < needle.length() && haystack.charAt(i + j) == needle.charAt(j)) {
            j++;
        }
        if (j == needle.length()) return i;
    }

    return -1;
}
```

**Time Complexity**: O((n-m+1)*m) worst case  
**Space Complexity**: O(1)

## Key Insights
- Try every valid start index in `haystack`
- Verify full `needle` match character by character

## Tips and Tricks
- Start with the direct scan and be explicit about substring boundaries.
- Watch off-by-one errors when comparing pattern length against remaining text.
- If repeated matching is heavy, then consider KMP or rolling hash; otherwise keep it simple.

## Related Problems
- LC 14 Longest Common Prefix
