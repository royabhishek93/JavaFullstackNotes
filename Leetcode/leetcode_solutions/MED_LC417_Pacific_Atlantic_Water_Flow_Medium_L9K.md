# LC 417: Pacific Atlantic Water Flow

**Link**: [leetcode.com/problems/pacific-atlantic-water-flow](https://leetcode.com/problems/pacific-atlantic-water-flow/)

## Problem
Return all coordinates where water can flow to both Pacific and Atlantic oceans.

## Optimized Approach: Reverse BFS from Ocean Borders

```java
public List<List<Integer>> pacificAtlantic(int[][] heights) {
    int rows = heights.length, cols = heights[0].length;
    boolean[][] pac = new boolean[rows][cols];
    boolean[][] atl = new boolean[rows][cols];

    Queue<int[]> pacQ = new LinkedList<>();
    Queue<int[]> atlQ = new LinkedList<>();

    for (int r = 0; r < rows; r++) {
        pacQ.offer(new int[]{r, 0});
        atlQ.offer(new int[]{r, cols - 1});
        pac[r][0] = true;
        atl[r][cols - 1] = true;
    }
    for (int c = 0; c < cols; c++) {
        pacQ.offer(new int[]{0, c});
        atlQ.offer(new int[]{rows - 1, c});
        pac[0][c] = true;
        atl[rows - 1][c] = true;
    }

    bfs(heights, pacQ, pac);
    bfs(heights, atlQ, atl);

    List<List<Integer>> ans = new ArrayList<>();
    for (int r = 0; r < rows; r++) {
        for (int c = 0; c < cols; c++) {
            if (pac[r][c] && atl[r][c]) {
                ans.add(Arrays.asList(r, c));
            }
        }
    }
    return ans;
}

private void bfs(int[][] h, Queue<int[]> q, boolean[][] seen) {
    int rows = h.length, cols = h[0].length;
    int[][] dirs = {{1,0},{-1,0},{0,1},{0,-1}};

    while (!q.isEmpty()) {
        int[] cur = q.poll();
        int r = cur[0], c = cur[1];

        for (int[] d : dirs) {
            int nr = r + d[0], nc = c + d[1];
            if (nr < 0 || nr >= rows || nc < 0 || nc >= cols || seen[nr][nc]) continue;
            if (h[nr][nc] < h[r][c]) continue;
            seen[nr][nc] = true;
            q.offer(new int[]{nr, nc});
        }
    }
}
```

**Time Complexity**: O(m*n)  
**Space Complexity**: O(m*n)

## Key Insights
- Reverse the flow direction: start from oceans and move inward
- A cell is valid if reachable from both ocean traversals
- Reverse traversal avoids repeated DFS from every cell

## Tips and Tricks
- Condition is `nextHeight >= currentHeight` in reverse traversal.
- Same pattern can be done with DFS as well.

## Related Problems
- LC 542 01 Matrix
- LC 200 Number of Islands
