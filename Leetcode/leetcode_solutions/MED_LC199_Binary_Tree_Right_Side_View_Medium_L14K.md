# LC 199: Binary Tree Right Side View

**Link**: [leetcode.com/problems/binary-tree-right-side-view](https://leetcode.com/problems/binary-tree-right-side-view/)

## Problem
Given the root of a binary tree, return the values of nodes you can see when looking from the right side.

## Optimized Approach: BFS, Last Node Per Level

```java
public List<Integer> rightSideView(TreeNode root) {
    List<Integer> result = new ArrayList<>();
    if (root == null) return result;

    Queue<TreeNode> queue = new LinkedList<>();
    queue.offer(root);

    while (!queue.isEmpty()) {
        int size = queue.size();

        for (int i = 0; i < size; i++) {
            TreeNode node = queue.poll();

            if (i == size - 1) result.add(node.val); // rightmost

            if (node.left != null) queue.offer(node.left);
            if (node.right != null) queue.offer(node.right);
        }
    }

    return result;
}
```

**Time Complexity**: O(n)  
**Space Complexity**: O(n)

## Key Insights
- BFS level-order traversal; capture the last node value at each level
- Right child is added after left, so last polled in each level is rightmost visible

## Tips and Tricks
- Mark visited when enqueuing, not when dequeuing, to avoid duplicates.
- Level-order problems usually need queue-size based iteration.
- If distance matters, increment the level only after processing one full layer.

## Related Problems
- LC 102 Binary Tree Level Order Traversal
