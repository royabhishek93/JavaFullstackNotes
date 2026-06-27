# LC 5: Longest Palindromic Substring

**Link**: [leetcode.com/problems/longest-palindromic-substring](https://leetcode.com/problems/longest-palindromic-substring/)

## Problem
Given a string `s`, return the longest palindromic substring in `s`.

## Optimized Approach: Expand Around Center

```java
public String longestPalindrome(String s) {
    if (s == null || s.length() < 2) return s;

    int start = 0, end = 0;

    for (int i = 0; i < s.length(); i++) {
        int len1 = expand(s, i, i);       // odd length
        int len2 = expand(s, i, i + 1);   // even length
        int len = Math.max(len1, len2);

        if (len > end - start + 1) {
            start = i - (len - 1) / 2;
            end = i + len / 2;
        }
    }

    return s.substring(start, end + 1);
}

private int expand(String s, int left, int right) {
    while (left >= 0 && right < s.length() && s.charAt(left) == s.charAt(right)) {
        left--;
        right++;
    }
    return right - left - 1;
}
```

**Time Complexity**: O(n^2)  
**Space Complexity**: O(1)

## Key Insights
- Every palindrome has a center (char or gap)
- Expand from each center and keep best window

## Tips and Tricks
- Try both odd and even centers because palindromes have two shapes.
- Expansion logic is simple, but boundary checks must be exact.
- Center expansion is often easier to explain than DP for palindrome problems.

## Related Problems
- LC 647 Palindromic Substrings
- LC 125 Valid Palindrome
