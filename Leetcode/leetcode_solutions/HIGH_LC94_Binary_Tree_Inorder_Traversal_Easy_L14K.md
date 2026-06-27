# LC 94: Binary Tree Inorder Traversal

**Link**: [leetcode.com/problems/binary-tree-inorder-traversal](https://leetcode.com/problems/binary-tree-inorder-traversal/)

## Problem
Given the root of a binary tree, return the inorder traversal (left → root → right) of its nodes' values.

## Optimized Approach: Iterative with Stack

```java
public List<Integer> inorderTraversal(TreeNode root) {
    List<Integer> result = new ArrayList<>();
    Deque<TreeNode> stack = new ArrayDeque<>();
    TreeNode cur = root;

    while (cur != null || !stack.isEmpty()) {
        while (cur != null) {
            stack.push(cur);
            cur = cur.left;
        }
        cur = stack.pop();
        result.add(cur.val);
        cur = cur.right;
    }

    return result;
}
```

**Time Complexity**: O(n)  
**Space Complexity**: O(h)

## Key Insights
- Push left chain, then process node, then go right
- Iterative avoids system recursion stack

## Tips and Tricks
- Define what the recursive call returns before coding the body.
- Write the null or leaf base case first to anchor the recursion.
- For tree problems, decide whether the answer is built top-down or bottom-up.

## Related Problems
- LC 144 Binary Tree Preorder Traversal
- LC 145 Binary Tree Postorder Traversal
