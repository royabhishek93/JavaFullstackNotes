# LC 200: Number of Islands

**Link**: [leetcode.com/problems/number-of-islands](https://leetcode.com/problems/number-of-islands/)

## Problem
Given an m x n 2D binary grid grid where '1' represents land and '0' represents water, return the number of islands. An island is surrounded by water and is formed by connecting adjacent lands horizontally or vertically. You may assume all four edges of the grid are surrounded by water.

### Examples
- Input: grid = [["1","1","1","1","0"],["1","1","0","1","0"],["1","1","0","0","0"],["0","0","0","0","0"]] → Output: 1
- Input: grid = [["1","1","0","0","0"],["1","1","0","0","0"],["0","0","1","0","0"],["0","0","0","1","1"]] → Output: 3

## Optimized Approach: DFS with Grid Marking

```java
public int numIslands(char[][] grid) {
    if (grid == null || grid.length == 0) {
        return 0;
    }

    int islandCount = 0;
    int rows = grid.length;
    int cols = grid[0].length;

    for (int i = 0; i < rows; i++) {
        for (int j = 0; j < cols; j++) {
            if (grid[i][j] == '1') {
                islandCount++;
                dfs(grid, i, j);
            }
        }
    }

    return islandCount;
}

private void dfs(char[][] grid, int i, int j) {
    int rows = grid.length;
    int cols = grid[0].length;

    // Boundary and water check
    if (i < 0 || i >= rows || j < 0 || j >= cols || grid[i][j] == '0') {
        return;
    }

    // Mark as visited
    grid[i][j] = '0';

    // Explore 4 directions
    dfs(grid, i + 1, j);
    dfs(grid, i - 1, j);
    dfs(grid, i, j + 1);
    dfs(grid, i, j - 1);
}
```

**Time Complexity**: O(m*n) - visit each cell once  
**Space Complexity**: O(m*n) - recursion stack worst case

## Key Insights
- **Island definition**: Connected '1's (4-directional)
- **DFS approach**: Mark visited by setting to '0'
- **Count islands**: Increment counter when finding new unvisited '1'
- **In-place modification**: No extra visited array needed

## Interview Walkthrough
1. **Problem**: Count separate islands
2. **Key insight**: Each island is a connected component of '1's
3. **Algorithm**:
   - Scan grid for unvisited '1'
   - When found, DFS to mark entire island
   - Increment island counter
4. **Example**: 3x5 grid with 1 island
   ```
   Grid:
   1 1 1 1 0
   1 1 0 1 0
   1 1 0 0 0
   0 0 0 0 0
   
   i=0,j=0: Found '1', dfs to mark all connected
   Island 1 marked completely
   Rest is water
   Return 1
   ```

## Why This Approach (Optimal)
- ✅ **O(m*n) time**: Visit each cell once
- ✅ **O(1) space**: Modify grid in-place
- ✅ **Simple**: Clear DFS logic
- ✅ **Efficient**: No extra structures

## Common Mistakes
- Forgetting to mark as visited
- Only checking 2 directions (need 4)
- Wrong boundary conditions
- Not returning from base case

## Tips and Tricks
- "Count connected components of '1's"
- "DFS to mark entire island as visited"
- "Increment counter when finding NEW island"
- "Mark as '0' to prevent revisit"

## Alternative: BFS
```java
// Use queue instead of recursion stack
// Same O(m*n) complexity
```

## Related Problems
- **LC 695**: Max Area of Island (find largest)
- **LC 733**: Flood Fill (similar approach)
- **LC 547**: Number of Provinces (similar concept)
