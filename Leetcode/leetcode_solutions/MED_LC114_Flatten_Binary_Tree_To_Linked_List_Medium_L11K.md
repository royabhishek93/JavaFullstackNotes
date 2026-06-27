# LC 114: Flatten Binary Tree to Linked List

**Link**: [leetcode.com/problems/flatten-binary-tree-to-linked-list](https://leetcode.com/problems/flatten-binary-tree-to-linked-list/)

## Problem
Flatten binary tree to a linked list in-place following preorder traversal.

## Optimized Approach: Reverse Preorder DFS

```java
private TreeNode prev = null;

public void flatten(TreeNode root) {
    if (root == null) return;

    flatten(root.right);
    flatten(root.left);

    root.right = prev;
    root.left = null;
    prev = root;
}
```

**Time Complexity**: O(n)  
**Space Complexity**: O(h)

## Key Insights
- Process in reverse preorder: right -> left -> root
- `prev` holds next node in final flattened list

## Tips and Tricks
- Define what the recursive call returns before coding the body.
- Write the null or leaf base case first to anchor the recursion.
- For tree problems, decide whether the answer is built top-down or bottom-up.

## Related Problems
- LC 144 Binary Tree Preorder Traversal
