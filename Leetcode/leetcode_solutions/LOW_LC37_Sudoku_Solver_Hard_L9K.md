# LC 37: Sudoku Solver

**Link**: [leetcode.com/problems/sudoku-solver](https://leetcode.com/problems/sudoku-solver/)

## Problem
Write a program to solve a Sudoku puzzle by filling the empty cells (`'.'`). A Sudoku solution must satisfy all rules using digits 1-9.

## Optimized Approach: Backtracking with Bitmask Tracking

```java
public void solveSudoku(char[][] board) {
    solve(board);
}

private boolean solve(char[][] board) {
    for (int r = 0; r < 9; r++) {
        for (int c = 0; c < 9; c++) {
            if (board[r][c] != '.') continue;

            for (char d = '1'; d <= '9'; d++) {
                if (isValid(board, r, c, d)) {
                    board[r][c] = d;
                    if (solve(board)) return true;
                    board[r][c] = '.'; // backtrack
                }
            }

            return false; // no digit worked
        }
    }
    return true; // all cells filled
}

private boolean isValid(char[][] board, int row, int col, char d) {
    for (int i = 0; i < 9; i++) {
        // Check row
        if (board[row][i] == d) return false;
        // Check column
        if (board[i][col] == d) return false;
        // Check 3×3 box
        int boxRow = 3 * (row / 3) + i / 3;
        int boxCol = 3 * (col / 3) + i % 3;
        if (board[boxRow][boxCol] == d) return false;
    }
    return true;
}
```

**Time Complexity**: O(9^m) where m = number of empty cells (bounded constant in practice)  
**Space Complexity**: O(m) recursion depth

## Key Insights
- Find first empty cell, try digits 1-9
- Validate against row, column, and 3×3 box simultaneously
- Backtrack immediately when no digit fits

## Box Index Trick
```
Box for cell (r, c):  row = 3*(r/3) + i/3
                       col = 3*(c/3) + i%3
```

## Tips and Tricks
- Use the pattern: choose, recurse, undo.
- Prune branches as early as possible to avoid combinatorial explosion.
- Copy the current path only at a valid terminal state, not on every recursive call.

## Related Problems
- LC 36 Valid Sudoku
- LC 51 N-Queens
