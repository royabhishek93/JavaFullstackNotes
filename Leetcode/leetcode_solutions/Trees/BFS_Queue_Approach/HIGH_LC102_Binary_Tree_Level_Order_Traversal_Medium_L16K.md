# LC 102: Binary Tree Level Order Traversal

**Link**: [leetcode.com/problems/binary-tree-level-order-traversal](https://leetcode.com/problems/binary-tree-level-order-traversal/)

## Problem
Given the root of a binary tree, return the level order traversal of its nodes' values.

## Optimized Approach: BFS with Queue

```java
public List<List<Integer>> levelOrder(TreeNode root) {
    List<List<Integer>> result = new ArrayList<>();
    if (root == null) return result;

    Queue<TreeNode> queue = new LinkedList<>();
    queue.offer(root);

    while (!queue.isEmpty()) {
        int size = queue.size();
        List<Integer> level = new ArrayList<>();

        for (int i = 0; i < size; i++) {
            TreeNode node = queue.poll();
            level.add(node.val);

            if (node.left != null) queue.offer(node.left);
            if (node.right != null) queue.offer(node.right);
        }

        result.add(level);
    }

    return result;
}
```

**Time Complexity**: O(n)  
**Space Complexity**: O(n)

## Key Insights
- Queue naturally processes nodes in level order
- Use `size` snapshot per loop to isolate each level

## Tips and Tricks
- Mark visited when enqueuing, not when dequeuing, to avoid duplicates.
- Level-order problems usually need queue-size based iteration.
- If distance matters, increment the level only after processing one full layer.

## Related Problems
- LC 103 Binary Tree Zigzag Level Order Traversal
- LC 107 Binary Tree Level Order Traversal II
