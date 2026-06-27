# LC 909: Snakes and Ladders

**Link**: [leetcode.com/problems/snakes-and-ladders](https://leetcode.com/problems/snakes-and-ladders/)

## Problem
Given an `n x n` board with snakes/ladders, return the minimum number of moves to reach square `n*n`.

## Optimized Approach: BFS on Board Positions

```java
public int snakesAndLadders(int[][] board) {
    int n = board.length;
    Queue<Integer> queue = new LinkedList<>();
    boolean[] visited = new boolean[n * n + 1];

    queue.offer(1);
    visited[1] = true;
    int moves = 0;

    while (!queue.isEmpty()) {
        int size = queue.size();

        for (int i = 0; i < size; i++) {
            int cur = queue.poll();
            if (cur == n * n) return moves;

            for (int next = cur + 1; next <= Math.min(cur + 6, n * n); next++) {
                int[] rc = toRowCol(next, n);
                int dest = board[rc[0]][rc[1]] == -1 ? next : board[rc[0]][rc[1]];
                if (!visited[dest]) {
                    visited[dest] = true;
                    queue.offer(dest);
                }
            }
        }

        moves++;
    }

    return -1;
}

private int[] toRowCol(int num, int n) {
    int r = (num - 1) / n;
    int c = (num - 1) % n;
    int row = n - 1 - r;
    int col = (r % 2 == 0) ? c : (n - 1 - c);
    return new int[]{row, col};
}
```

**Time Complexity**: O(n^2)  
**Space Complexity**: O(n^2)

## Key Insights
- Treat board as unweighted graph of squares
- From each square, edges to next 1..6 squares
- Apply snake/ladder jump immediately on landing square

## Tips and Tricks
- Most bugs come from index conversion.
- Visit destination square after snake/ladder jump.

## Related Problems
- LC 752 Open the Lock
- LC 127 Word Ladder
