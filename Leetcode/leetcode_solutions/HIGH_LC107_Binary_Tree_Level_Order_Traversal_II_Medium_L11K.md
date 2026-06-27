# LC 107: Binary Tree Level Order Traversal II

**Link**: [leetcode.com/problems/binary-tree-level-order-traversal-ii](https://leetcode.com/problems/binary-tree-level-order-traversal-ii/)

## Problem
Given the root of a binary tree, return the bottom-up level order traversal of its nodes' values.

## Optimized Approach: BFS + Front Insert

```java
public List<List<Integer>> levelOrderBottom(TreeNode root) {
    LinkedList<List<Integer>> result = new LinkedList<>();
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

        result.addFirst(level);
    }

    return result;
}
```

**Time Complexity**: O(n)  
**Space Complexity**: O(n)

## Key Insights
- Same BFS template as LC 102
- Only difference: place each level at the front
- Avoid extra reverse pass by using `LinkedList.addFirst`

## Tips and Tricks
- If interviewer asks for top-down then reverse, mention both approaches.
- `addFirst` is cleaner than `Collections.reverse(result)` at the end.

## Related Problems
- LC 102 Binary Tree Level Order Traversal
- LC 103 Binary Tree Zigzag Level Order Traversal
