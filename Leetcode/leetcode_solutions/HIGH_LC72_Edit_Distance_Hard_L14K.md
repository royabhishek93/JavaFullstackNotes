# LC 72: Edit Distance

**Link**: [leetcode.com/problems/edit-distance](https://leetcode.com/problems/edit-distance/)

## Problem
Given two words, return the minimum number of operations (insert, delete, replace) required to convert one word to the other.

## Optimized Approach: 2D DP

```java
public int minDistance(String word1, String word2) {
    int m = word1.length(), n = word2.length();
    int[][] dp = new int[m + 1][n + 1];

    for (int i = 0; i <= m; i++) dp[i][0] = i;
    for (int j = 0; j <= n; j++) dp[0][j] = j;

    for (int i = 1; i <= m; i++) {
        for (int j = 1; j <= n; j++) {
            if (word1.charAt(i - 1) == word2.charAt(j - 1)) {
                dp[i][j] = dp[i - 1][j - 1];
            } else {
                dp[i][j] = 1 + Math.min(dp[i - 1][j - 1], Math.min(dp[i - 1][j], dp[i][j - 1]));
            }
        }
    }

    return dp[m][n];
}
```

**Time Complexity**: O(m*n)  
**Space Complexity**: O(m*n)

## Tips and Tricks
- Define the DP state in one sentence before writing transitions.
- Initialize base cases carefully because most DP bugs come from wrong starting values.
- Check whether the transition depends on previous row, previous column, or previous index only.

## Related Problems
- LC 1143 Longest Common Subsequence
