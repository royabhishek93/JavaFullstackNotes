# LC 139: Word Break

**Link**: [leetcode.com/problems/word-break](https://leetcode.com/problems/word-break/)

## Problem
Given a string `s` and a dictionary of strings `wordDict`, return `true` if `s` can be segmented into a space-separated sequence of one or more dictionary words.

## Optimized Approach: DP on Prefixes

```java
public boolean wordBreak(String s, List<String> wordDict) {
    Set<String> dict = new HashSet<>(wordDict);
    boolean[] dp = new boolean[s.length() + 1];
    dp[0] = true;

    for (int i = 1; i <= s.length(); i++) {
        for (int j = 0; j < i; j++) {
            if (dp[j] && dict.contains(s.substring(j, i))) {
                dp[i] = true;
                break;
            }
        }
    }

    return dp[s.length()];
}
```

**Time Complexity**: O(n^3) worst-case with substring checks  
**Space Complexity**: O(n)

## Key Insights
- `dp[i]` means prefix `s[0..i)` can be segmented
- Transition: if `dp[j]` and `s[j..i)` in dictionary, then `dp[i] = true`

## Tips and Tricks
- Define the DP state in one sentence before writing transitions.
- Initialize base cases carefully because most DP bugs come from wrong starting values.
- Check whether the transition depends on previous row, previous column, or previous index only.

## Related Problems
- LC 140 Word Break II
- LC 472 Concatenated Words
