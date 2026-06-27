# LC 112: Path Sum

**Link**: [leetcode.com/problems/path-sum](https://leetcode.com/problems/path-sum/)

## Problem
Given the root of a binary tree and an integer targetSum, return true if the tree has a root-to-leaf path such that adding up all the values along the path equals targetSum. A leaf is a node with no children.

### Examples
- Input: root = [5,4,8,11,null,13,4,7,2,null,1], targetSum = 22 → Output: true (path: 5→4→11→2)
- Input: root = [1,2,3], targetSum = 5 → Output: false  
- Input: root = [1,2], targetSum = 0 → Output: false

## Optimized Approach: DFS with Remaining Sum

```java
public boolean hasPathSum(TreeNode root, int targetSum) {
    if (root == null) {
        return false;
    }

    // Leaf node: check if remaining sum equals node value
    if (root.left == null && root.right == null) {
        return root.val == targetSum;
    }

    // Recursive case: search in either subtree with updated sum
    int remaining = targetSum - root.val;
    return hasPathSum(root.left, remaining) || 
           hasPathSum(root.right, remaining);
}
```

**Time Complexity**: O(n) worst case, O(log n) best case  
**Space Complexity**: O(h) - recursion stack

## Key Insights
- **Pass remaining**: Subtract current node from target going down
- **Check at leaf**: Only valid if we reach leaf with remaining = 0
- **Early termination**: Return false on first non-matching path
- **OR logic**: Either left or right path works

## Interview Walkthrough
1. **Problem**: Find if any root-to-leaf path sums to target
2. **Approach**:
   - At each node, calculate what sum we still need
   - Recurse with remaining = targetSum - currentNode
   - At leaf, check if remaining == leaf value
3. **Algorithm**:
   - Base: null → false
   - Leaf: return (value == targetSum)
   - Internal: return searchLeft(remaining) OR searchRight(remaining)
4. **Example**: root = [5,4,8,11,null,13,4,7,2,null,1], target=22
   ```
   At 5: remaining = 22-5 = 17
   At 4: remaining = 17-4 = 13
   At 11: remaining = 13-11 = 2
   At 2 (leaf): 2 == 2? YES!
   ```

## Why This Approach (Optimal)
- ✅ **O(n) time**: Single traversal
- ✅ **O(h) space**: Only recursion stack
- ✅ **Clean logic**: Passing remaining is elegant
- ✅ **Early exit**: Stop on first match

## Common Mistakes
- Checking at internal nodes instead of leaf
- Using sum accumulation instead of remaining subtraction
- Not handling null correctly (root.left/right null checks)
- Not verifying both children are null (leaf definition)
- Forgetting OR logic (should be || not &&)

## Tips and Tricks
- "We need to reach a LEAF with exact sum match"
- "Pass remaining down: target - currentNode"
- "Check balancing only when both children null"
- "Use OR because ANY path working is enough"

## Related Problems
- **LC 113**: Path Sum II (collect all paths, not just exists)
- **LC 129**: Sum Root to Leaf Numbers (different calculation)
- **LC 437**: Path Sum III (any node as start, not just root)
- **LC 124**: Binary Tree Maximum Path Sum (find max, not check target)
