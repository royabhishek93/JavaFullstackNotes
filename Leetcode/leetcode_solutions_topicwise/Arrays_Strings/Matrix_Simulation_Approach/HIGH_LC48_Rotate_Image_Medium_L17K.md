# LC 48: Rotate Image

**Link**: [leetcode.com/problems/rotate-image](https://leetcode.com/problems/rotate-image/)

## Problem
Rotate an `n x n` matrix by 90 degrees clockwise in-place.

## Optimized Approach: Transpose + Reverse Rows

```java
public void rotate(int[][] matrix) {
    int n = matrix.length;

    // Transpose
    for (int i = 0; i < n; i++) {
        for (int j = i + 1; j < n; j++) {
            int t = matrix[i][j];
            matrix[i][j] = matrix[j][i];
            matrix[j][i] = t;
        }
    }

    // Reverse each row
    for (int i = 0; i < n; i++) {
        int l = 0, r = n - 1;
        while (l < r) {
            int t = matrix[i][l];
            matrix[i][l] = matrix[i][r];
            matrix[i][r] = t;
            l++;
            r--;
        }
    }
}
```

**Time Complexity**: O(n^2)  
**Space Complexity**: O(1)

## Key Insights
- Rotation decomposition: transpose then horizontal mirror
- Works in-place without extra matrix

## Tips and Tricks
- Write boundary variables clearly because simulation bugs are usually index mistakes.
- Update direction or boundary only after fully consuming the current row or column.
- Test tiny matrices like 1x1, 1xn, and nx1 before trusting the loop.

## Related Problems
- LC 54 Spiral Matrix
