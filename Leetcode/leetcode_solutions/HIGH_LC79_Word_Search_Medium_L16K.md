# LC 79: Word Search

**Link**: [leetcode.com/problems/word-search](https://leetcode.com/problems/word-search/)

## Problem
Given a board and a word, return true if word exists in grid by sequentially adjacent cells. A cell cannot be reused.

## Optimized Approach: DFS Backtracking

```java
public boolean exist(char[][] board, String word) {
    int rows = board.length, cols = board[0].length;

    for (int r = 0; r < rows; r++) {
        for (int c = 0; c < cols; c++) {
            if (dfs(board, word, r, c, 0)) return true;
        }
    }
    return false;
}

private boolean dfs(char[][] board, String word, int r, int c, int idx) {
    if (idx == word.length()) return true;

    if (r < 0 || r >= board.length || c < 0 || c >= board[0].length || board[r][c] != word.charAt(idx)) {
        return false;
    }

    char temp = board[r][c];
    board[r][c] = '#';

    boolean found = dfs(board, word, r + 1, c, idx + 1)
            || dfs(board, word, r - 1, c, idx + 1)
            || dfs(board, word, r, c + 1, idx + 1)
            || dfs(board, word, r, c - 1, idx + 1);

    board[r][c] = temp;
    return found;
}
```

**Time Complexity**: O(m*n*4^L)  
**Space Complexity**: O(L)

## Tips and Tricks
- Use the pattern: choose, recurse, undo.
- Prune branches as early as possible to avoid combinatorial explosion.
- Copy the current path only at a valid terminal state, not on every recursive call.

## Related Problems
- LC 212 Word Search II
