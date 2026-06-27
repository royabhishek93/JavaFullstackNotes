# LC 542: 01 Matrix

**Link**: [leetcode.com/problems/01-matrix](https://leetcode.com/problems/01-matrix/)

## Problem
For each cell containing `1`, return distance to nearest `0`.

## Optimized Approach: Multi-Source BFS

```java
public int[][] updateMatrix(int[][] mat) {
    int rows = mat.length, cols = mat[0].length;
    int[][] dist = new int[rows][cols];
    Queue<int[]> queue = new LinkedList<>();

    for (int r = 0; r < rows; r++) {
        for (int c = 0; c < cols; c++) {
            if (mat[r][c] == 0) {
                queue.offer(new int[]{r, c});
            } else {
                dist[r][c] = -1;
            }
        }
    }

    int[][] dirs = {{1,0},{-1,0},{0,1},{0,-1}};
    while (!queue.isEmpty()) {
        int[] cur = queue.poll();
        int r = cur[0], c = cur[1];

        for (int[] d : dirs) {
            int nr = r + d[0], nc = c + d[1];
            if (nr >= 0 && nr < rows && nc >= 0 && nc < cols && dist[nr][nc] == -1) {
                dist[nr][nc] = dist[r][c] + 1;
                queue.offer(new int[]{nr, nc});
            }
        }
    }

    return dist;
}
```

**Time Complexity**: O(m*n)  
**Space Complexity**: O(m*n)

## Key Insights
- All zero cells are starting points simultaneously
- First time a cell is reached gives shortest distance
- This is shortest path in unweighted grid

## Tips and Tricks
- Initialize non-zero cells as unvisited with `-1`.
- Single-source BFS from each `1` is too slow.

## Related Problems
- LC 994 Rotting Oranges
- LC 286 Walls and Gates
