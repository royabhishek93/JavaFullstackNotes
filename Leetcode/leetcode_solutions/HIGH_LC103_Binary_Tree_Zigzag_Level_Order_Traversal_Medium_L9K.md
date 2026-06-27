# LC 103: Binary Tree Zigzag Level Order Traversal

**Link**: [leetcode.com/problems/binary-tree-zigzag-level-order-traversal](https://leetcode.com/problems/binary-tree-zigzag-level-order-traversal/)

## Problem
Given the root of a binary tree, return the zigzag level order traversal of its nodes' values.

## Optimized Approach: BFS + Direction Flag

```java
public List<List<Integer>> zigzagLevelOrder(TreeNode root) {
    List<List<Integer>> result = new ArrayList<>();
    if (root == null) return result;

    Queue<TreeNode> queue = new LinkedList<>();
    queue.offer(root);
    boolean leftToRight = true;

    while (!queue.isEmpty()) {
        int size = queue.size();
        LinkedList<Integer> level = new LinkedList<>();

        for (int i = 0; i < size; i++) {
            TreeNode node = queue.poll();
            if (leftToRight) {
                level.addLast(node.val);
            } else {
                level.addFirst(node.val);
            }

            if (node.left != null) queue.offer(node.left);
            if (node.right != null) queue.offer(node.right);
        }

        result.add(level);
        leftToRight = !leftToRight;
    }

    return result;
}
```

**Time Complexity**: O(n)  
**Space Complexity**: O(n)

## Key Insights
- Level order BFS stays same
- Only insertion direction changes per level
- `LinkedList` gives O(1) front/back inserts

## Tips and Tricks
- This is a classic follow-up on LC 102.
- Keep traversal order of children normal; only output order flips.

## Related Problems
- LC 102 Binary Tree Level Order Traversal
- LC 107 Binary Tree Level Order Traversal II
