# LC 73: Set Matrix Zeroes

**Link**: [leetcode.com/problems/set-matrix-zeroes](https://leetcode.com/problems/set-matrix-zeroes/)

## Problem
Given an `m x n` matrix, if an element is 0, set its entire row and column to 0 in-place.

## Optimized Approach: First Row/Column as Markers

```java
public void setZeroes(int[][] matrix) {
    int rows = matrix.length, cols = matrix[0].length;
    boolean firstColZero = false;

    for (int r = 0; r < rows; r++) {
        if (matrix[r][0] == 0) firstColZero = true;
        for (int c = 1; c < cols; c++) {
            if (matrix[r][c] == 0) {
                matrix[r][0] = 0;
                matrix[0][c] = 0;
            }
        }
    }

    for (int r = 1; r < rows; r++) {
        for (int c = 1; c < cols; c++) {
            if (matrix[r][0] == 0 || matrix[0][c] == 0) {
                matrix[r][c] = 0;
            }
        }
    }

    if (matrix[0][0] == 0) {
        for (int c = 0; c < cols; c++) matrix[0][c] = 0;
    }

    if (firstColZero) {
        for (int r = 0; r < rows; r++) matrix[r][0] = 0;
    }
}
```

**Time Complexity**: O(m*n)  
**Space Complexity**: O(1)

## Key Insights
- Use first row/column as marker arrays
- Track first column separately to avoid collision with `matrix[0][0]`

## Tips and Tricks
- Write boundary variables clearly because simulation bugs are usually index mistakes.
- Update direction or boundary only after fully consuming the current row or column.
- Test tiny matrices like 1x1, 1xn, and nx1 before trusting the loop.

## Related Problems
- LC 54 Spiral Matrix
