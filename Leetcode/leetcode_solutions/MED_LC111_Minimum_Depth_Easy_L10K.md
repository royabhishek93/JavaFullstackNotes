# LC 111: Minimum Depth of Binary Tree

**Link**: [leetcode.com/problems/minimum-depth-of-binary-tree](https://leetcode.com/problems/minimum-depth-of-binary-tree/)

## Problem
Given a binary tree, find its minimum depth. The minimum depth is the number of nodes along the shortest path from the root node down to the nearest leaf node. A leaf node is a node with no children.

### Examples
- Input: root = [3,9,20,null,null,15,7] → Output: 2 (path: 3→9)
- Input: root = [2,null,3,null,4,null,5,null,6] → Output: 5 (path: 2→3→4→5→6)

## Optimized Approach: Recursive DFS

```java
public int minDepth(TreeNode root) {
    if (root == null) {
        return 0;
    }

    // Special case: only one child exists
    // We must reach a leaf node (both children null), not stop at single child
    if (root.left == null) {
        return 1 + minDepth(root.right);
    }
    if (root.right == null) {
        return 1 + minDepth(root.left);
    }

    // Both children exist - take minimum
    int leftDepth = minDepth(root.left);
    int rightDepth = minDepth(root.right);

    return 1 + Math.min(leftDepth, rightDepth);
}
```

**Time Complexity**: O(n) worst case, O(log n) best case (balanced)  
**Space Complexity**: O(h) where h = height (recursion stack)

## Key Insights
- **Special handling for single child**: Must reach actual LEAF (both null)
- **Don't stop at first null**: LC 111 differs from symmetric maximum depth
- **Definition matters**: Leaf = both left AND right are null
- **Early termination**: Returns faster than max depth on skewed trees

## Interview Walkthrough
1. **Problem**: Find shortest path from root to LEAF
2. **Key Difference from LC 104**:
   - Max depth: return 0 for null (can stop anywhere)
   - Min depth: must reach leaf (node with no children)
3. **Algorithm**:
   - Base case: null returns 0
   - If only one child: continue to that child (1 + minDepth(child))
   - If both children: 1 + min(left, right)
4. **Why special case needed**:
   - [2, null, 3, null, 4, null, 5, null, 6]
   - Without special case: minDepth(2) = 1 + minDepth(null) = 1 (WRONG!)
   - With special case: follows right child to actual leaf = 5 (CORRECT!)

## Common Mistakes
- Returning 1 when root.left == null (but root.right exists) → incorrect
- Using simple min without checking for single-child case
- Confusing "depth at null" with "depth at leaf"
- Not returning early for single-child nodes

## Tips and Tricks
- "Minimum depth means MINIMUM PATH TO A LEAF"
- "A leaf must have both children as null"
- "If node has only one child, we MUST continue down that path"
- "This is different from max depth where we can reach null"
- "Compare to LC 104 to understand the distinction"

## Comparison with LC 104 (Maximum Depth)
```java
// LC 104 - Max Depth
public int maxDepth(TreeNode root) {
    if (root == null) return 0;
    return 1 + Math.max(maxDepth(root.left), maxDepth(root.right));
}

// LC 111 - Min Depth (DIFFERENT)
public int minDepth(TreeNode root) {
    if (root == null) return 0;
    if (root.left == null) return 1 + minDepth(root.right);  // Continue right!
    if (root.right == null) return 1 + minDepth(root.left);  // Continue left!
    return 1 + Math.min(minDepth(root.left), minDepth(root.right));
}
```

## Related Problems
- **LC 104**: Maximum Depth Binary Tree (simpler, no special case)
- **LC 110**: Balanced Binary Tree (check balance property)
- **LC 112**: Path Sum (reach leaf with target sum)
- **LC 543**: Diameter Binary Tree (longest path through node)
