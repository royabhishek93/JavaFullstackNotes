# LC 105: Construct Binary Tree from Preorder and Inorder Traversal

**Link**: [leetcode.com/problems/construct-binary-tree-from-preorder-and-inorder-traversal](https://leetcode.com/problems/construct-binary-tree-from-preorder-and-inorder-traversal/)

## Problem
Given `preorder` and `inorder` traversal arrays of a binary tree, reconstruct and return the tree.

## Optimized Approach: Recursive with HashMap Index

```java
private int preIdx = 0;

public TreeNode buildTree(int[] preorder, int[] inorder) {
    Map<Integer, Integer> inMap = new HashMap<>();
    for (int i = 0; i < inorder.length; i++) {
        inMap.put(inorder[i], i);
    }
    return build(preorder, inMap, 0, inorder.length - 1);
}

private TreeNode build(int[] preorder, Map<Integer, Integer> inMap, int left, int right) {
    if (left > right) return null;

    int rootVal = preorder[preIdx++];
    TreeNode root = new TreeNode(rootVal);
    int mid = inMap.get(rootVal);

    root.left = build(preorder, inMap, left, mid - 1);
    root.right = build(preorder, inMap, mid + 1, right);
    return root;
}
```

**Time Complexity**: O(n)  
**Space Complexity**: O(n)

## Key Insights
- Preorder gives root first; inorder splits left/right subtrees
- HashMap gives O(1) root-index lookup in inorder array

## Tips and Tricks
- Define what the recursive call returns before coding the body.
- Write the null or leaf base case first to anchor the recursion.
- For tree problems, decide whether the answer is built top-down or bottom-up.

## Related Problems
- LC 106 Construct Binary Tree from Inorder and Postorder Traversal
