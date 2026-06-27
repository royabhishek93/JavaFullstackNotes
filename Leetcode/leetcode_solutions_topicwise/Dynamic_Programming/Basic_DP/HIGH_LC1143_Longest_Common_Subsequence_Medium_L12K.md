# LC 1143: Longest Common Subsequence

**Link**: [leetcode.com/problems/longest-common-subsequence](https://leetcode.com/problems/longest-common-subsequence/)

## Problem
Given two strings `text1` and `text2`, return the length of their longest common subsequence.

## Optimized Approach: 2D DP

```java
public int longestCommonSubsequence(String text1, String text2) {
    int m = text1.length(), n = text2.length();
    int[][] dp = new int[m + 1][n + 1];

    for (int i = 1; i <= m; i++) {
        for (int j = 1; j <= n; j++) {
            if (text1.charAt(i - 1) == text2.charAt(j - 1)) {
                dp[i][j] = dp[i - 1][j - 1] + 1;
            } else {
                dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1]);
            }
        }
    }

    return dp[m][n];
}
```

**Time Complexity**: O(m × n)  
**Space Complexity**: O(m × n)

## Key Insights
- If chars match, extend diagonal: `dp[i-1][j-1] + 1`
- If not, carry forward best of skipping either character

## Tips and Tricks
- Define the DP state in one sentence before writing transitions.
- Initialize base cases carefully because most DP bugs come from wrong starting values.
- Check whether the transition depends on previous row, previous column, or previous index only.

## Related Problems
- LC 72 Edit Distance
- LC 300 Longest Increasing Subsequence
