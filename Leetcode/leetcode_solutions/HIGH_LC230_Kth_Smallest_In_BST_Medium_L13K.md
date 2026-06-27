# LC 230: Kth Smallest Element in a BST

**Link**: [leetcode.com/problems/kth-smallest-element-in-a-bst](https://leetcode.com/problems/kth-smallest-element-in-a-bst/)

## Problem
Given the root of a Binary Search Tree (BST) and an integer `k`, return the `k`th smallest value among all nodes.

## Optimized Approach: Iterative Inorder (Stop Early)

```java
public int kthSmallest(TreeNode root, int k) {
    Deque<TreeNode> stack = new ArrayDeque<>();
    TreeNode cur = root;

    while (cur != null || !stack.isEmpty()) {
        while (cur != null) {
            stack.push(cur);
            cur = cur.left;
        }
        cur = stack.pop();
        k--;
        if (k == 0) return cur.val;
        cur = cur.right;
    }

    return -1; // never reached if k is valid
}
```

**Time Complexity**: O(H + k) where H is tree height  
**Space Complexity**: O(H)

## Key Insights
- Inorder traversal of BST yields sorted order
- Stop as soon as countdown reaches zero — no need to traverse full tree

## Tips and Tricks
- Define what the recursive call returns before coding the body.
- Write the null or leaf base case first to anchor the recursion.
- For tree problems, decide whether the answer is built top-down or bottom-up.

## Related Problems
- LC 94 Binary Tree Inorder Traversal
- LC 98 Validate Binary Search Tree
