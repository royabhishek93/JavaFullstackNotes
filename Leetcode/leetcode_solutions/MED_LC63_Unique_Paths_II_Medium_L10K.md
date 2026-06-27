# LC 63: Unique Paths II

**Link**: [leetcode.com/problems/unique-paths-ii](https://leetcode.com/problems/unique-paths-ii/)

## Problem
Like LC 62, but some cells are obstacles (`1`). Return number of unique paths.

## Optimized Approach: DP Grid

```java
public int uniquePathsWithObstacles(int[][] obstacleGrid) {
    int m = obstacleGrid.length, n = obstacleGrid[0].length;
    int[][] dp = new int[m][n];

    if (obstacleGrid[0][0] == 1) return 0;
    dp[0][0] = 1;

    for (int i = 0; i < m; i++) {
        for (int j = 0; j < n; j++) {
            if (obstacleGrid[i][j] == 1) {
                dp[i][j] = 0;
                continue;
            }
            if (i > 0) dp[i][j] += dp[i - 1][j];
            if (j > 0) dp[i][j] += dp[i][j - 1];
        }
    }

    return dp[m - 1][n - 1];
}
```

**Time Complexity**: O(m*n)  
**Space Complexity**: O(m*n)

## Tips and Tricks
- Write the recurrence from top and left dependencies before coding.
- Guard obstacle or blocked-cell logic before applying the normal transition.
- Use 1D DP only after the 2D state transition is fully clear.

## Related Problems
- LC 62 Unique Paths
- LC 64 Minimum Path Sum
