# BFS - Grid Traversal Pattern

## 🎯 When to Use
- Graph/grid connectivity problems
- Find all connected components
- Shortest path in unweighted graphs
- "Number of islands", "surrounded regions" keywords

## 📝 Master Template - BFS (Queue-Based)

```java
public void bfs(char[][] grid, int i, int j) {
    Queue<int[]> queue = new LinkedList<>();
    queue.add(new int[]{i, j});
    grid[i][j] = 0;  // Mark as visited
    
    int[][] directions = {{0,1}, {0,-1}, {1,0}, {-1,0}};
    
    while (!queue.isEmpty()) {
        int[] cell = queue.poll();
        int row = cell[0], col = cell[1];
        
        for (int[] dir : directions) {
            int newRow = row + dir[0];
            int newCol = col + dir[1];
            
            if (isValid(grid, newRow, newCol)) {
                queue.add(new int[]{newRow, newCol});
                grid[newRow][newCol] = 0;  // Mark visited
            }
        }
    }
}

private boolean isValid(char[][] grid, int i, int j) {
    return i >= 0 && i < grid.length && 
           j >= 0 && j < grid[0].length && 
           grid[i][j] == '1';
}
```

## 📝 Master Template - DFS (Stack-Based)

```java
public void dfs(char[][] grid, int i, int j) {
    // Base case
    if (i < 0 || i >= grid.length || j < 0 || j >= grid[0].length || 
        grid[i][j] == '0') {
        return;
    }
    
    // Mark as visited
    grid[i][j] = '0';
    
    // Explore all 4 directions
    dfs(grid, i + 1, j);
    dfs(grid, i - 1, j);
    dfs(grid, i, j + 1);
    dfs(grid, i, j - 1);
}
```

## 🔄 Problem Variations & Modifications

### ✅ LC 200: Number of Islands (IMPLEMENTED - DFS)
**What changes**: Count islands (connected component count)
**Difficulty**: Medium
```java
public int numIslands(char[][] grid) {
    if (grid == null || grid.length == 0) return 0;
    
    int count = 0;
    
    for (int i = 0; i < grid.length; i++) {
        for (int j = 0; j < grid[0].length; j++) {
            if (grid[i][j] == '1') {
                dfs(grid, i, j);
                count++;
            }
        }
    }
    
    return count;
}

private void dfs(char[][] grid, int i, int j) {
    if (i < 0 || i >= grid.length || j < 0 || j >= grid[0].length || 
        grid[i][j] == '0') {
        return;
    }
    
    grid[i][j] = '0';  // Mark visited
    
    dfs(grid, i + 1, j);
    dfs(grid, i - 1, j);
    dfs(grid, i, j + 1);
    dfs(grid, i, j - 1);
}
```
**Key**: Each unvisited '1' is a new island

---

### LC 130: Surrounded Regions
**What changes**: BFS from '0's touching borders to mark safe regions
**Difficulty**: Medium
```java
public void solve(char[][] board) {
    // First: DFS/BFS from borders to mark safe regions
    int rows = board.length, cols = board[0].length;
    
    for (int i = 0; i < rows; i++) {
        if (board[i][0] == 'O') dfs(board, i, 0);
        if (board[i][cols-1] == 'O') dfs(board, i, cols-1);
    }
    for (int j = 0; j < cols; j++) {
        if (board[0][j] == 'O') dfs(board, 0, j);
        if (board[rows-1][j] == 'O') dfs(board, rows-1, j);
    }
    
    // Second: Change unmarked 'O' to 'X', restore marked to 'O'
    for (int i = 0; i < rows; i++) {
        for (int j = 0; j < cols; j++) {
            if (board[i][j] == 'O') board[i][j] = 'X';
            else if (board[i][j] == '*') board[i][j] = 'O';
        }
    }
}

private void dfs(char[][] board, int i, int j) {
    if (i < 0 || i >= board.length || j < 0 || j >= board[0].length || 
        board[i][j] != 'O') {
        return;
    }
    
    board[i][j] = '*';  // Mark safe
    dfs(board, i+1, j);
    dfs(board, i-1, j);
    dfs(board, i, j+1);
    dfs(board, i, j-1);
}
```
**Key Insight**: Inverse problem - mark safe regions from borders

---

### LC 695: Max Area of Island
**What changes**: Track size of each island
**Difficulty**: Medium
```java
public int maxAreaOfIsland(int[][] grid) {
    if (grid == null || grid.length == 0) return 0;
    
    int maxArea = 0;
    
    for (int i = 0; i < grid.length; i++) {
        for (int j = 0; j < grid[0].length; j++) {
            if (grid[i][j] == 1) {
                int area = dfs(grid, i, j);
                maxArea = Math.max(maxArea, area);
            }
        }
    }
    
    return maxArea;
}

private int dfs(int[][] grid, int i, int j) {
    if (i < 0 || i >= grid.length || j < 0 || j >= grid[0].length || 
        grid[i][j] == 0) {
        return 0;
    }
    
    grid[i][j] = 0;  // Mark visited
    
    int area = 1;
    area += dfs(grid, i+1, j);
    area += dfs(grid, i-1, j);
    area += dfs(grid, i, j+1);
    area += dfs(grid, i, j-1);
    
    return area;
}
```
**Key Change**: Return and accumulate area

---

## 📊 BFS vs DFS Comparison

| Aspect | BFS | DFS |
|--------|-----|-----|
| Space | O(width) queue | O(height) stack |
| Traversal | Level by level | Deep then back |
| Shortest path | ✅ Guaranteed | ✗ Not guaranteed |
| Implementation | Queue | Recursion/Explicit stack |
| Grid problems | Both work | Both work |

## 💡 Key Insights

### Direction Arrays:
```java
int[][] directions = {{0,1}, {0,-1}, {1,0}, {-1,0}};  // 4-directional
int[][] directions = {{0,1}, {0,-1}, {1,0}, {-1,0}, {1,1}, {1,-1}, {-1,1}, {-1,-1}};  // 8-directional
```

### Visited Marking:
- **Option 1**: Modify grid in-place (if allowed)
- **Option 2**: Use separate visited array
- **Option 3**: Use Set to track visited coordinates

### Connected Components:
```
Count = number of times you start new DFS/BFS
Each component discovered exactly once
```

## Tips and Tricks

1. **Choose DFS for recursion**: "I'll do DFS since grid is small..."
2. **Choose BFS for shortest path**: "Need shortest path, so BFS..."
3. **Always check bounds**: Common off-by-one errors
4. **Mark visited immediately**: Before adding to queue/stack
5. **Handle edge cases**: Empty grid, all water, all land
