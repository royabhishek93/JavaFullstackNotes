# LC 994: Rotting Oranges

**Link**: [leetcode.com/problems/rotting-oranges](https://leetcode.com/problems/rotting-oranges/)

## Problem
In a grid, each cell is 0 (empty), 1 (fresh orange), or 2 (rotten orange). Every minute, any fresh orange adjacent (4-directionally) to a rotten orange becomes rotten. Return minimum minutes to rot all oranges, or -1 if impossible.

## Optimized Approach: Multi-Source BFS

```java
public int orangesRotting(int[][] grid) {
    int rows = grid.length, cols = grid[0].length;
    Queue<int[]> queue = new LinkedList<>();
    int fresh = 0;

    for (int r = 0; r < rows; r++) {
        for (int c = 0; c < cols; c++) {
            if (grid[r][c] == 2) queue.offer(new int[]{r, c});
            if (grid[r][c] == 1) fresh++;
        }
    }

    if (fresh == 0) return 0;

    int minutes = 0;
    int[][] dirs = {{1,0},{-1,0},{0,1},{0,-1}};

    while (!queue.isEmpty()) {
        int size = queue.size();
        boolean rottedThisMinute = false;

        for (int i = 0; i < size; i++) {
            int[] cell = queue.poll();
            int r = cell[0], c = cell[1];

            for (int[] d : dirs) {
                int nr = r + d[0], nc = c + d[1];
                if (nr >= 0 && nr < rows && nc >= 0 && nc < cols && grid[nr][nc] == 1) {
                    grid[nr][nc] = 2;
                    fresh--;
                    rottedThisMinute = true;
                    queue.offer(new int[]{nr, nc});
                }
            }
        }

        if (rottedThisMinute) minutes++;
    }

    return fresh == 0 ? minutes : -1;
}
```

**Time Complexity**: O(m*n)  
**Space Complexity**: O(m*n)

## Key Insights
- Start BFS from all rotten oranges at once (multi-source)
- Each BFS layer equals one minute
- If fresh remain after BFS, answer is -1

## Tips and Tricks
- Use a direction array to keep neighbor logic compact and consistent.
- Mark a cell visited as soon as it is queued.
- For shortest path on unweighted grids, BFS is the default choice.

## Related Problems
- LC 200 Number of Islands
- LC 1091 Shortest Path in Binary Matrix
