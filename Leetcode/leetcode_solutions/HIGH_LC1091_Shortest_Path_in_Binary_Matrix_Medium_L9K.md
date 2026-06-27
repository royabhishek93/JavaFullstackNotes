# LC 1091: Shortest Path in Binary Matrix

**Link**: [leetcode.com/problems/shortest-path-in-binary-matrix](https://leetcode.com/problems/shortest-path-in-binary-matrix/)

## Problem
Find shortest clear path from top-left to bottom-right in a binary matrix. You can move in 8 directions through cells with value `0`.

## Optimized Approach: BFS (8 Directions)

```java
public int shortestPathBinaryMatrix(int[][] grid) {
    int n = grid.length;
    if (grid[0][0] == 1 || grid[n - 1][n - 1] == 1) return -1;
    if (n == 1) return 1;

    Queue<int[]> queue = new LinkedList<>();
    queue.offer(new int[]{0, 0, 1});
    grid[0][0] = 1; // mark visited

    int[][] dirs = {
        {1,0},{-1,0},{0,1},{0,-1},
        {1,1},{1,-1},{-1,1},{-1,-1}
    };

    while (!queue.isEmpty()) {
        int[] cur = queue.poll();
        int r = cur[0], c = cur[1], dist = cur[2];

        for (int[] d : dirs) {
            int nr = r + d[0], nc = c + d[1];
            if (nr < 0 || nr >= n || nc < 0 || nc >= n || grid[nr][nc] != 0) continue;
            if (nr == n - 1 && nc == n - 1) return dist + 1;

            grid[nr][nc] = 1;
            queue.offer(new int[]{nr, nc, dist + 1});
        }
    }

    return -1;
}
```

**Time Complexity**: O(n^2)  
**Space Complexity**: O(n^2)

## Key Insights
- BFS is shortest path for unweighted graph
- This problem uses 8-direction movement, not 4
- Mark visited when enqueuing to avoid duplicates

## Tips and Tricks
- Handle blocked start/end first.
- If interviewer asks weighted version, switch to Dijkstra.

## Related Problems
- LC 542 01 Matrix
- LC 994 Rotting Oranges
