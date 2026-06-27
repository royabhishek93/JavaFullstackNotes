# LC 101: Symmetric Tree

**Link**: [leetcode.com/problems/symmetric-tree](https://leetcode.com/problems/symmetric-tree/)

## Problem
Given the root of a binary tree, check whether it is a mirror of itself around its center.

## Optimized Approach: Mirror DFS

```java
public boolean isSymmetric(TreeNode root) {
    if (root == null) return true;
    return isMirror(root.left, root.right);
}

private boolean isMirror(TreeNode a, TreeNode b) {
    if (a == null && b == null) return true;
    if (a == null || b == null) return false;
    if (a.val != b.val) return false;

    return isMirror(a.left, b.right) && isMirror(a.right, b.left);
}
```

**Time Complexity**: O(n)  
**Space Complexity**: O(h)

## Key Insights
- Mirror condition compares cross children
- Left subtree of one side must match right subtree of other

## Tips and Tricks
- Define what the recursive call returns before coding the body.
- Write the null or leaf base case first to anchor the recursion.
- For tree problems, decide whether the answer is built top-down or bottom-up.

## Related Problems
- LC 100 Same Tree
