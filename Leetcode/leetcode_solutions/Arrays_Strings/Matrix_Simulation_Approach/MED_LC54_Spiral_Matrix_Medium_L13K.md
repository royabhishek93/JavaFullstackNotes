# LC 54: Spiral Matrix

**Link**: [leetcode.com/problems/spiral-matrix](https://leetcode.com/problems/spiral-matrix/)

## Problem
Given an `m x n` matrix, return all elements in spiral order.

## Optimized Approach: Boundary Simulation

```java
public List<Integer> spiralOrder(int[][] matrix) {
    List<Integer> result = new ArrayList<>();
    int top = 0, bottom = matrix.length - 1;
    int left = 0, right = matrix[0].length - 1;

    while (top <= bottom && left <= right) {
        for (int c = left; c <= right; c++) result.add(matrix[top][c]);
        top++;

        for (int r = top; r <= bottom; r++) result.add(matrix[r][right]);
        right--;

        if (top <= bottom) {
            for (int c = right; c >= left; c--) result.add(matrix[bottom][c]);
            bottom--;
        }

        if (left <= right) {
            for (int r = bottom; r >= top; r--) result.add(matrix[r][left]);
            left++;
        }
    }

    return result;
}
```

**Time Complexity**: O(m*n)  
**Space Complexity**: O(1) extra (excluding output)

## Key Insights
- Maintain four shrinking boundaries: top, bottom, left, right
- Guard reverse traversals with boundary checks

## Tips and Tricks
- Write boundary variables clearly because simulation bugs are usually index mistakes.
- Update direction or boundary only after fully consuming the current row or column.
- Test tiny matrices like 1x1, 1xn, and nx1 before trusting the loop.

## Related Problems
- LC 59 Spiral Matrix II
- LC 73 Set Matrix Zeroes
