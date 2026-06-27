# LC 52: N-Queens II

**Link**: [leetcode.com/problems/n-queens-ii](https://leetcode.com/problems/n-queens-ii/)

## Problem
Given an integer `n`, return the number of distinct solutions to the n-queens puzzle.

## Optimized Approach: Backtracking (Count Only)

```java
public int totalNQueens(int n) {
    Set<Integer> cols = new HashSet<>();
    Set<Integer> diag1 = new HashSet<>();
    Set<Integer> diag2 = new HashSet<>();
    return backtrack(0, n, cols, diag1, diag2);
}

private int backtrack(int row, int n, Set<Integer> cols,
                      Set<Integer> diag1, Set<Integer> diag2) {
    if (row == n) return 1;

    int count = 0;
    for (int col = 0; col < n; col++) {
        if (cols.contains(col) || diag1.contains(row - col) || diag2.contains(row + col)) {
            continue;
        }

        cols.add(col); diag1.add(row - col); diag2.add(row + col);
        count += backtrack(row + 1, n, cols, diag1, diag2);
        cols.remove(col); diag1.remove(row - col); diag2.remove(row + col);
    }

    return count;
}
```

**Time Complexity**: O(n!)  
**Space Complexity**: O(n)

## Key Insights
- Same algorithm as LC 51 but accumulates count instead of board strings
- No board construction needed — saves overhead

## Tips and Tricks
- Use the pattern: choose, recurse, undo.
- Prune branches as early as possible to avoid combinatorial explosion.
- Copy the current path only at a valid terminal state, not on every recursive call.

## Related Problems
- LC 51 N-Queens
