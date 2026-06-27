# LC 100: Same Tree

**Link**: [leetcode.com/problems/same-tree](https://leetcode.com/problems/same-tree/)

## Problem
Given roots of two binary trees `p` and `q`, return `true` if they are structurally identical with equal node values.

## Optimized Approach: DFS Recursion

```java
public boolean isSameTree(TreeNode p, TreeNode q) {
    if (p == null && q == null) return true;
    if (p == null || q == null) return false;
    if (p.val != q.val) return false;

    return isSameTree(p.left, q.left) && isSameTree(p.right, q.right);
}
```

**Time Complexity**: O(n)  
**Space Complexity**: O(h)

## Key Insights
- Compare value and both subtrees recursively
- Null cases are base conditions

## Tips and Tricks
- Define what the recursive call returns before coding the body.
- Write the null or leaf base case first to anchor the recursion.
- For tree problems, decide whether the answer is built top-down or bottom-up.

## Related Problems
- LC 101 Symmetric Tree
- LC 104 Maximum Depth of Binary Tree
