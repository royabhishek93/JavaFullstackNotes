# LC 226: Invert Binary Tree

**Link**: [leetcode.com/problems/invert-binary-tree](https://leetcode.com/problems/invert-binary-tree/)

## Problem
Given the root of a binary tree, invert the tree, and return its root. Inverting means swapping the left and right children of every node.

### Examples
- Input: root = [4,2,7,1,3,6,9] → Output: [4,7,2,9,6,3,1]
- Input: root = [2,1,3] → Output: [2,3,1]
- Input: root = [] → Output: []

## Optimized Approach: Recursive DFS

```java
public TreeNode invertTree(TreeNode root) {
    if (root == null) {
        return null;
    }

    // Recursively invert subtrees
    TreeNode leftInverted = invertTree(root.left);
    TreeNode rightInverted = invertTree(root.right);

    // Swap children
    root.left = rightInverted;
    root.right = leftInverted;

    return root;
}
```

**Time Complexity**: O(n) - visit each node once  
**Space Complexity**: O(h) - recursion stack

## Key Insights
- **Modify in-place**: Swap children directly
- **Recurse first**: Invert subtrees before swapping
- **Return root**: Chain operations for parent swaps
- **Simple pattern**: Just swap and recurse

## Interview Walkthrough
1. **Problem**: Swap all left↔right children in tree
2. **Algorithm**:
   - Base: null returns null
   - Recursively invert left subtree
   - Recursively invert right subtree
   - Swap left ↔ right at current node
   - Return root
3. **Example**: [4, 2, 7]
   ```
   Original:    4
               / \
              2   7
              
   After:       4
               / \
              7   2
   ```

## Why This Approach (Optimal)
- ✅ **O(n) time**: Must visit every node
- ✅ **O(h) space**: Only recursion stack
- ✅ **Simple**: Minimal code
- ✅ **In-place**: No extra data structures

## Common Mistakes
- Not recursing before swapping
- Breaking reference chain (not returning modified root)
- Creating new nodes instead of reusing
- Not handling null properly

## Tips and Tricks
- "Recursively invert both subtrees THEN swap"
- "This is in-place modification, no extra data structures"
- "Every node gets its children swapped"

## Related Problems
- **LC 104**: Maximum Depth (read-only traversal)
- **LC 226**: Invert Tree (modify structure)
- **LC 617**: Merge Two Binary Trees (similar recursive pattern)
