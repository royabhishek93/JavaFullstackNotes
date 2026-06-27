# LC 59: Spiral Matrix II

**Link**: [leetcode.com/problems/spiral-matrix-ii](https://leetcode.com/problems/spiral-matrix-ii/)

## Problem
Given a positive integer `n`, generate an `n x n` matrix filled with elements from 1 to n² in spiral order.

## Optimized Approach: Boundary Simulation (Fill)

```java
public int[][] generateMatrix(int n) {
    int[][] matrix = new int[n][n];
    int top = 0, bottom = n - 1, left = 0, right = n - 1;
    int num = 1;

    while (top <= bottom && left <= right) {
        for (int c = left; c <= right; c++) matrix[top][c] = num++;
        top++;

        for (int r = top; r <= bottom; r++) matrix[r][right] = num++;
        right--;

        if (top <= bottom) {
            for (int c = right; c >= left; c--) matrix[bottom][c] = num++;
            bottom--;
        }

        if (left <= right) {
            for (int r = bottom; r >= top; r--) matrix[r][left] = num++;
            left++;
        }
    }

    return matrix;
}
```

**Time Complexity**: O(n²)  
**Space Complexity**: O(1) extra

## Key Insights
- Exact same boundary pattern as LC 54 (Spiral Matrix) — just writing instead of reading
- Same guard conditions for inner partial rows/cols

## Tips and Tricks
- Write boundary variables clearly because simulation bugs are usually index mistakes.
- Update direction or boundary only after fully consuming the current row or column.
- Test tiny matrices like 1x1, 1xn, and nx1 before trusting the loop.

## Related Problems
- LC 54 Spiral Matrix
