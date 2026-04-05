# LC 543: Diameter of Binary Tree

**Link**: [leetcode.com/problems/diameter-of-binary-tree](https://leetcode.com/problems/diameter-of-binary-tree/)

## Problem
Given the root of a binary tree, return the length of the diameter of the tree. The diameter of a binary tree is the length of the longest path between any two nodes in a tree. This path may or may not pass through the root.

### Examples
- Input: root = [1,2,3,4,5] → Output: 3 (path: 4→2→1→3)
- Input: root = [1,2] → Output: 1

## Optimized Approach: DFS with Global Maximum

```java
private int diameter = 0;  // Global variable tracking max diameter

public int diameterOfBinaryTree(TreeNode root) {
    getHeight(root);
    return diameter;
}

private int getHeight(TreeNode root) {
    if (root == null) {
        return 0;
    }

    // Recursively get height of left and right subtrees
    int leftHeight = getHeight(root.left);
    int rightHeight = getHeight(root.right);

    // Update global diameter
    // Diameter through this node = left_height + right_height
    diameter = Math.max(diameter, leftHeight + rightHeight);

    // Return height of tree rooted at this node
    return 1 + Math.max(leftHeight, rightHeight);
}
```

**Time Complexity**: O(n) - visit each node once  
**Space Complexity**: O(h) - recursion stack

## Key Insights
- **Two separate values**: diameter (path through node) vs height (used by parent)
- **Diameter = left_height + right_height**: Longest path through current node
- **Height = 1 + max(left, right)**: What we return to parent
- **Global tracking**: Update diameter as we explore all nodes

## Interview Walkthrough
1. **Problem**: Find longest path between ANY two nodes (not necessarily root)
2. **Key Insight**: 
   - For each node, longest path through it = left_height + right_height
   - Must check all nodes to find global maximum
3. **Algorithm**:
   - For each node, calculate: left height, right height
   - Update diameter with left + right
   - Return height to parent (1 + max of children)
4. **Example**: root = [1,2,3,4,5]
   ```
       1
      / \
     2   3
    / \
   4   5
   
   At node 2: left_height=1 (node4), right_height=1 (node5)
   diameter = 1 + 1 = 2
   
   At node 1: left_height=2 (path through 2), right_height=1 (node3)
   diameter = 2 + 1 = 3  ← answer!
   ```

## Why This Approach (Optimal)
- ✅ **O(n) time**: Single traversal
- ✅ **Clean logic**: Separate concerns (height vs diameter)
- ✅ **Correct answer**: Checks all possible paths

## Common Mistakes
- Confusing diameter with height
- Not updating diameter for every node
- Returning diameter instead of height (breaks recursion for parent)
- Using local variables instead of global
- Not considering paths that don't go through root

## Tips and Tricks
- "Diameter might not pass through root - need to check all nodes"
- "For each node, longest path through it = left_height + right_height"
- "Use global variable to track maximum diameter seen"
- "Return height to parent, update diameter at each node"
- "Two different calculations: diameter (for global) vs height (for parent)"

## Key Difference: Diameter vs Height
```
At each node:
- Height = 1 + max(left_height, right_height)      // return to parent
- Diameter = left_height + right_height              // update global max

They're different!
- Height is how deep the subtree is
- Diameter is the longest path through this node
```

## Related Problems
- **LC 104**: Maximum Depth (simpler, returns single value)
- **LC 110**: Balanced Binary Tree (check balance property)
- **LC 124**: Binary Tree Maximum Path Sum (similar structure, with values)
- **LC 111**: Minimum Depth (reach leaf with min distance)
