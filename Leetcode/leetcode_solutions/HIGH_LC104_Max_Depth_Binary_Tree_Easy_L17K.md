# LC 104: Maximum Depth of Binary Tree

**Link**: [leetcode.com/problems/maximum-depth-of-binary-tree](https://leetcode.com/problems/maximum-depth-of-binary-tree/)

## Problem
Given the root of a binary tree, return its maximum depth. A binary tree's maximum depth is the number of nodes along the longest path from the root node down to the farthest leaf node.

### Examples
- Input: root = [3,9,20,null,null,15,7] → Output: 3 (path: 3→9, or 3→20→15/7)
- Input: root = [1,null,2] → Output: 2 (path: 1→2)

## Optimized Approach: Recursive DFS

```java
public int maxDepth(TreeNode root) {
    // Base case: null tree has depth 0
    if (root == null) {
        return 0;
    }

    // Recursively find depth of left and right subtrees
    int leftDepth = maxDepth(root.left);
    int rightDepth = maxDepth(root.right);

    // Return 1 (current node) + maximum depth of subtrees
    return 1 + Math.max(leftDepth, rightDepth);
}
```

**Time Complexity**: O(n) - visit each node once  
**Space Complexity**: O(h) - recursion stack where h = tree height

## Key Insights
- **Definition**: Depth = 1 + max(left_depth, right_depth)
- **Base Case**: Null tree has depth 0
- **Recursive Pattern**: Solve subproblems (left and right subtrees) then combine
- **Space Trade-off**: Recursive uses O(h) stack space (h is height, not n for balanced trees)
- **Implicit Traversal**: Every node visited exactly once through recursion

## Interview Walkthrough
1. **Problem**: Find maximum depth (number of nodes from root to farthest leaf)
2. **Key Insight**: Depth of tree = 1 + max(depth of left subtree, depth of right subtree)
3. **Recursive Logic**:
   - Base case: empty tree has depth 0
   - Recursive case: 1 + max depths of children
4. **Example with [3, 9, 20, null, null, 15, 7]**:
   ```
       3
      / \
     9   20
        /  \
       15   7
   
   maxDepth(3):
   - maxDepth(9) = 1 (leaf node: 1 + max(0, 0))
   - maxDepth(20) = 2 (1 + max(maxDepth(15), maxDepth(7)))
     - maxDepth(15) = 1 (leaf)
     - maxDepth(7) = 1 (leaf)
   - Return 1 + max(1, 2) = 3
   ```
5. **Path Trace**: Root 3 → Node 20 → Node 15/7 = 3 nodes = depth 3

## Why This Approach (Optimal for Interviews)
- ✅ **Elegant**: Natural recursive structure mirrors tree structure
- ✅ **O(n) time**: Must visit each node anyway
- ✅ **Easy to understand**: Direct implementation of definition
- ✅ **Easy to remember**: "1 + max of subtrees"

## Common Mistakes
- **Boundary**: Returning 0 for root instead of 1
- **Wrong comparison**: Using min instead of max
- **Off-by-one**: Returning maxDepth(left) instead of 1 + maxDepth(left)
- **Comparing with wrong node**: Comparing root == null (correct) vs root.left == null || root.right == null (wrong)

## Alternative Approach Mention
- **Iterative BFS**: Can use Queue to traverse level-by-level, count levels (good if recursion depth concerns interviewer)
- **Iterative DFS**: Stack-based, same complexity but more verbose

## Tips and Tricks
- "Depth is 1 plus the maximum depth of subtrees"
- "Base case: empty tree has depth 0"
- "This is a classic FP tree problem - recursion directly maps to tree structure"
- "Why O(h) space not O(n)? On balanced tree, height is O(log n), but on skewed tree height = n"
- "If interviewer concerned about recursion depth, offer iterative BFS alternative"
