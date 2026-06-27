# LC 240: Search a 2D Matrix II

**Link**: [leetcode.com/problems/search-a-2d-matrix-ii](https://leetcode.com/problems/search-a-2d-matrix-ii/)

## Problem
Write an efficient algorithm to search for a value in an `m x n` integer matrix where each row and column is sorted in ascending order.

## Optimized Approach: Start from Top-Right Corner

```java
public boolean searchMatrix(int[][] matrix, int target) {
    int row = 0, col = matrix[0].length - 1;

    while (row < matrix.length && col >= 0) {
        int val = matrix[row][col];

        if (val == target) return true;
        else if (val > target) col--;   // current too big, go left
        else row++;                      // current too small, go down
    }

    return false;
}
```

**Time Complexity**: O(m + n)  
**Space Complexity**: O(1)

## Key Insights
- Top-right is the unique pivot: larger than everything to its left, smaller than everything below
- Each comparison eliminates one full row or one full column

## Comparison with LC 74
- LC 74: rows are also globally ordered (use single binary search)
- LC 240: only row-sorted + col-sorted (use staircase search)

## Tips and Tricks
- Binary search the answer only when the search space is monotonic.
- Be explicit about whether the range is inclusive or half-open.
- When debugging, print low, mid, high and check which side is safely discarded.

## Related Problems
- LC 74 Search a 2D Matrix
