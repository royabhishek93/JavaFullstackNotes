# LC 51: N-Queens

**Link**: [leetcode.com/problems/n-queens](https://leetcode.com/problems/n-queens/)

## Problem
Place `n` queens on an `n x n` chessboard so that no two queens attack each other. Return all distinct solutions.

## Optimized Approach: Backtracking with Sets

```java
public List<List<String>> solveNQueens(int n) {
    List<List<String>> result = new ArrayList<>();
    char[][] board = new char[n][n];
    for (char[] row : board) Arrays.fill(row, '.');

    Set<Integer> cols = new HashSet<>();
    Set<Integer> diag1 = new HashSet<>(); // row - col
    Set<Integer> diag2 = new HashSet<>(); // row + col

    backtrack(0, n, board, cols, diag1, diag2, result);
    return result;
}

private void backtrack(int row, int n, char[][] board, Set<Integer> cols,
                       Set<Integer> diag1, Set<Integer> diag2, List<List<String>> result) {
    if (row == n) {
        List<String> config = new ArrayList<>();
        for (char[] r : board) config.add(new String(r));
        result.add(config);
        return;
    }

    for (int col = 0; col < n; col++) {
        int d1 = row - col, d2 = row + col;
        if (cols.contains(col) || diag1.contains(d1) || diag2.contains(d2)) continue;

        board[row][col] = 'Q';
        cols.add(col); diag1.add(d1); diag2.add(d2);

        backtrack(row + 1, n, board, cols, diag1, diag2, result);

        board[row][col] = '.';
        cols.remove(col); diag1.remove(d1); diag2.remove(d2);
    }
}
```

**Time Complexity**: O(n!) (worst-case search)  
**Space Complexity**: O(n)

## Key Insights
- One queen per row
- Track used columns and diagonals for O(1) validity checks

## Tips and Tricks
- Use the pattern: choose, recurse, undo.
- Prune branches as early as possible to avoid combinatorial explosion.
- Copy the current path only at a valid terminal state, not on every recursive call.

## Related Problems
- LC 52 N-Queens II
- LC 79 Word Search
