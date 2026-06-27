# LC 286: Walls and Gates

**Link**: [leetcode.com/problems/walls-and-gates](https://leetcode.com/problems/walls-and-gates/)

## Problem
Fill each empty room with distance to nearest gate. Walls are `-1`, gates are `0`, and empty rooms are `INF`.

## Optimized Approach: Multi-Source BFS from Gates

```java
public void wallsAndGates(int[][] rooms) {
    if (rooms == null || rooms.length == 0) return;

    int rows = rooms.length, cols = rooms[0].length;
    Queue<int[]> queue = new LinkedList<>();
    int INF = 2147483647;

    for (int r = 0; r < rows; r++) {
        for (int c = 0; c < cols; c++) {
            if (rooms[r][c] == 0) queue.offer(new int[]{r, c});
        }
    }

    int[][] dirs = {{1,0},{-1,0},{0,1},{0,-1}};
    while (!queue.isEmpty()) {
        int[] cur = queue.poll();
        int r = cur[0], c = cur[1];

        for (int[] d : dirs) {
            int nr = r + d[0], nc = c + d[1];
            if (nr >= 0 && nr < rows && nc >= 0 && nc < cols && rooms[nr][nc] == INF) {
                rooms[nr][nc] = rooms[r][c] + 1;
                queue.offer(new int[]{nr, nc});
            }
        }
    }
}
```

**Time Complexity**: O(m*n)  
**Space Complexity**: O(m*n)

## Key Insights
- Distances grow layer by layer from all gates
- First assignment to a room is the shortest distance
- Same pattern as LC 542 and LC 994

## Tips and Tricks
- Never BFS from each room individually.
- In-place updates avoid extra distance matrix.

## Related Problems
- LC 542 01 Matrix
- LC 994 Rotting Oranges
