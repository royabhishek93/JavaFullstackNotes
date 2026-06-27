# LC 62: Unique Paths

**Link**: [leetcode.com/problems/unique-paths](https://leetcode.com/problems/unique-paths/)

## Problem
There is a robot on an m x n grid. The robot is initially at the top-left corner (0, 0) and tries to move to the bottom-right corner (m - 1, n - 1). The robot can only move right or down. How many unique paths exist?

### Examples
- Input: m = 3, n = 7 → Output: 28
- Input: m = 3, n = 2 → Output: 3 (right-right-down, right-down-right, down-right-right)
- Input: m = 1, n = 1 → Output: 1

## Optimized Approach: Dynamic Programming (Bottom-Up)

```java
public int uniquePaths(int m, int n) {
    // dp[i][j] = unique paths to reach (i, j)
    int[][] dp = new int[m][n];

    // Initialize: first row and column
    for (int i = 0; i < m; i++) {
        dp[i][0] = 1;  // Only one way down first column
    }
    for (int j = 0; j < n; j++) {
        dp[0][j] = 1;  // Only one way right first row
    }

    // Fill entire table
    for (int i = 1; i < m; i++) {
        for (int j = 1; j < n; j++) {
            // Can come from above or left
            dp[i][j] = dp[i - 1][j] + dp[i][j - 1];
        }
    }

    return dp[m - 1][n - 1];
}
```

**Space-Optimized (O(n)):**
```java
public int uniquePaths(int m, int n) {
    int[] dp = new int[n];
    for (int j = 0; j < n; j++) {
        dp[j] = 1;  // First row
    }

    for (int i = 1; i < m; i++) {
        for (int j = 1; j < n; j++) {
            dp[j] += dp[j - 1];  // Add path from left
        }
    }

    return dp[n - 1];
}
```

**Time Complexity**: O(m*n)  
**Space Complexity**: O(m*n) or O(n) optimized

## Key Insights
- **Movement constraints**: Only right or down
- **DP state**: dp[i][j] = ways to reach cell (i,j)
- **Recurrence**: dp[i][j] = dp[i-1][j] + dp[i][j-1]
- **Base case**: First row and column all 1

## Interview Walkthrough
1. **Problem**: Count paths from top-left to bottom-right
2. **Constraints**: Only right (R) or down (D) moves
3. **DP insight**: Paths = paths from above + paths from left
4. **Example**: 3x2 grid
   ```
   dp[0][0]=1, dp[0][1]=1
   dp[1][0]=1, dp[2][0]=1
   
   dp[1][1] = dp[0][1] + dp[1][0] = 1 + 1 = 2
   dp[2][1] = dp[1][1] + dp[2][0] = 2 + 1 = 3
   
   Paths: RDD, DRD, DDR
   ```

## Why This Approach (Optimal)
- ✅ **O(m*n) time**: Fill grid once
- ✅ **O(n) space**: Space-optimized with single row
- ✅ **Simple**: Clear DP transition
- ✅ **Correct**: Covers all possibilities

## Combinatorial Insight
```
Total moves = m-1 down + n-1 right = m+n-2
Choose which m-1 are down (rest are right)
Answer = C(m+n-2, m-1) = (m+n-2)! / ((m-1)!(n-1)!)
```

## Common Mistakes
- Wrong DP transition
- Not initializing first row/column
- Off-by-one in array indexing
- Forgetting to add both sources

## Tips and Tricks
- "DP[i][j] = ways to reach cell i,j"
- "Can only come from above or left"
- "First row and column are base cases (all 1)"
- "Space optimization: only need previous row"

## Related Problems
- **LC 63**: Unique Paths II (with obstacles)
- **LC 64**: Minimum Path Sum (different goal)
- **LC 174**: Dungeon Game (harder variant)
