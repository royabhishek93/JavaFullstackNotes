# LC 113: Path Sum II

**Link**: [leetcode.com/problems/path-sum-ii](https://leetcode.com/problems/path-sum-ii/)

## Problem
Given the root of a binary tree and an integer targetSum, return all root-to-leaf paths where each path's sum equals targetSum. You may return the result in any order. A leaf is a node with no children.

### Examples
- Input: root = [5,4,8,11,null,13,4,7,2,null,1], targetSum = 22 → Output: [[5,4,11,2],[5,8,4,5]]
- Input: root = [1,2,3], targetSum = 5 → Output: []
- Input: root = [1,2], targetSum = 0 → Output: []

## Optimized Approach: DFS with Backtracking

```java
public List<List<Integer>> pathSum(TreeNode root, int targetSum) {
    List<List<Integer>> result = new ArrayList<>();
    List<Integer> path = new ArrayList<>();
    dfs(root, targetSum, path, result);
    return result;
}

private void dfs(TreeNode root, int remaining, List<Integer> path, 
                 List<List<Integer>> result) {
    if (root == null) {
        return;
    }

    // Add current node to path
    path.add(root.val);

    // Check if leaf node and sum matches
    if (root.left == null && root.right == null && remaining == root.val) {
        // IMPORTANT: Add new list copy, not reference
        result.add(new ArrayList<>(path));
    }

    // Recurse on children with updated remaining
    dfs(root.left, remaining - root.val, path, result);
    dfs(root.right, remaining - root.val, path, result);

    // IMPORTANT: Backtrack - remove current node after recursion
    path.remove(path.size() - 1);
}
```

**Time Complexity**: O(n·h) where n = nodes, h = path length (copying paths)  
**Space Complexity**: O(h) - recursion stack, not counting output

## Key Insights
- **Maintain path list**: Add before recursing, remove after (backtracking)
- **Copy when adding**: new ArrayList<>(path) not just path reference
- **Leaf check**: Both children null AND sum matches
- **Backtracking pattern**: Add → Recurse → Remove

## Interview Walkthrough
1. **Problem**: Find ALL root-to-leaf paths with target sum
2. **Difference from LC 112**: Collect all paths, not just check existence
3. **Pattern - Backtracking**:
   - Add current node to path
   - Recurse on children
   - Remove current node (undo change)
   - This allows reusing path list across branches
4. **Algorithm**:
   - Base: if null, return
   - Add node value to path
   - Check if leaf with matching sum
   - Recurse left and right
   - Remove from path (backtrack)
5. **Why backtracking**:
   - [1,2] and [1,3] share path prefix [1]
   - Can't create separate lists for each branch
   - Must remove after exploring to "undo" the choice

## Why This Approach (Optimal)
- ✅ **O(n·h) time**: Single pass, copying found paths
- ✅ **Backtracking**: Reuses single path list
- ✅ **Space efficient**: O(h) temp space, not O(n) per path

## Critical Details
- **MUST create new ArrayList**: new ArrayList<>(path)
- **MUST remove after recursion**: path.remove(path.size()-1)
- **Leaf definition**: Both left and right null
- **Recurse first, then backtrack**: Order matters!

## Common Mistakes
- Forgetting to copy: result.add(path) → all entries become same list
- Forgetting to backtrack: path.remove() → wrong paths in result
- Checking internal nodes instead of leaf
- Modifying path during iteration
- Not handling null or both children null cases

## Tips and Tricks
- "This is backtracking - need to undo changes after recursion"
- "CRITICAL: new ArrayList<>(path) to copy, not reference"
- "CRITICAL: path.remove() after recurse to backtrack"
- "Leaf = both children null, not just value match"
- "Walk through [5,4,8,11,...] tracing path and backtracking"

## Backtracking Pattern
```
✅ CORRECT Pattern:
path.add(val)          // 1. Add
dfs(left, ...)         // 2. Recurse
dfs(right, ...)        // 3. Recurse
path.remove()          // 4. Backtrack (undo)

❌ WRONG: If you forget backtrack:
- path becomes garbage after recursion
- All results modify same list
```

## Related Problems
- **LC 112**: Path Sum (just check existence, no backtracking needed)
- **LC 129**: Sum Root to Leaf Numbers (different calculation, still backtracking)
- **LC 437**: Path Sum III (any node as start)
- **LC 257**: Binary Tree Paths (collect all paths as strings)
