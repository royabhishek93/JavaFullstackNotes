# LC 64: Minimum Path Sum

**Link**: [leetcode.com/problems/minimum-path-sum](https://leetcode.com/problems/minimum-path-sum/)

## Problem
Given a non-negative grid, find a path from top-left to bottom-right with minimum sum. You can move only right or down.

## Optimized Approach: In-Place DP

```java
public int minPathSum(int[][] grid) {
    int m = grid.length, n = grid[0].length;

    for (int i = 0; i < m; i++) {
        for (int j = 0; j < n; j++) {
            if (i == 0 && j == 0) continue;
            int up = i > 0 ? grid[i - 1][j] : Integer.MAX_VALUE;
            int left = j > 0 ? grid[i][j - 1] : Integer.MAX_VALUE;
            grid[i][j] += Math.min(up, left);
        }
    }

    return grid[m - 1][n - 1];
}
```

**Time Complexity**: O(m*n)  
**Space Complexity**: O(1) extra

## Tips and Tricks
- Write the recurrence from top and left dependencies before coding.
- Guard obstacle or blocked-cell logic before applying the normal transition.
- Use 1D DP only after the 2D state transition is fully clear.

## Related Problems
- LC 62 Unique Paths
- LC 63 Unique Paths II
