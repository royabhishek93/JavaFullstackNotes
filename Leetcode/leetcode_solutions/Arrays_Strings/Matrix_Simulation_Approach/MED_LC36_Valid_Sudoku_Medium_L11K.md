# LC 36: Valid Sudoku

**Link**: [leetcode.com/problems/valid-sudoku](https://leetcode.com/problems/valid-sudoku/)

## Problem
Determine if a 9x9 Sudoku board is valid.

## Optimized Approach: Track Rows, Cols, Boxes

```java
public boolean isValidSudoku(char[][] board) {
    boolean[][] rows = new boolean[9][9];
    boolean[][] cols = new boolean[9][9];
    boolean[][] boxes = new boolean[9][9];

    for (int r = 0; r < 9; r++) {
        for (int c = 0; c < 9; c++) {
            if (board[r][c] == '.') continue;

            int num = board[r][c] - '1';
            int box = (r / 3) * 3 + (c / 3);

            if (rows[r][num] || cols[c][num] || boxes[box][num]) return false;

            rows[r][num] = true;
            cols[c][num] = true;
            boxes[box][num] = true;
        }
    }

    return true;
}
```

**Time Complexity**: O(1) (fixed 81 cells)  
**Space Complexity**: O(1)

## Key Insights
- Box index formula: `(r / 3) * 3 + (c / 3)`
- Check row, column, and sub-box uniqueness

## Tips and Tricks
- Write boundary variables clearly because simulation bugs are usually index mistakes.
- Update direction or boundary only after fully consuming the current row or column.
- Test tiny matrices like 1x1, 1xn, and nx1 before trusting the loop.

## Related Problems
- LC 37 Sudoku Solver
