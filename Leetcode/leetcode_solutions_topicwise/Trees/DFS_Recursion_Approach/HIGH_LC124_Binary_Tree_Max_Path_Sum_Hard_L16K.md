# LC 124: Binary Tree Maximum Path Sum

**Link**: [leetcode.com/problems/binary-tree-maximum-path-sum](https://leetcode.com/problems/binary-tree-maximum-path-sum/)

## Problem
A path in a binary tree is a sequence of nodes where each pair of adjacent nodes in the sequence has an edge connecting them. A node can only appear in the sequence at most once. Note that the path does not need to pass through the root. The path sum of a path is the sum of the node's values in the path. Given the root of a binary tree, return the maximum path sum of any non-empty path.

### Examples
- Input: root = [1,2,3] → Output: 6 (path: 2→1→3)
- Input: root = [-10,9,20,null,null,15,7] → Output: 42 (path: 15→20→7)

## Optimized Approach: DFS with Global Maximum

```java
private int maxSum = Integer.MIN_VALUE;  // Global variable for answer

public int maxPathSum(TreeNode root) {
    maxGain(root);
    return maxSum;
}

private int maxGain(TreeNode root) {
    if (root == null) {
        return 0;
    }

    // Recursively get max gains from subtrees
    // Use Math.max(..., 0) to ignore negative paths
    int leftGain = Math.max(maxGain(root.left), 0);
    int rightGain = Math.max(maxGain(root.right), 0);

    // Calculate path sum through this node (can go both directions)
    int pathThroughNode = root.val + leftGain + rightGain;

    // Update global maximum with path through this node
    maxSum = Math.max(maxSum, pathThroughNode);

    // Return best path including this node (can only go one direction to parent)
    return root.val + Math.max(leftGain, rightGain);
}
```

**Time Complexity**: O(n) - visit each node once  
**Space Complexity**: O(h) - recursion stack

## Key Insights
- **Two different returns**:
  - pathThroughNode: 360° path (both left & right), used to update maxSum
  - return value: 180° path (one direction), returned to parent
- **Math.max(..., 0)**: Ignore negative branches
- **Global maximum**: Update for every node
- **Negative path rejection**: Paths that decrease total are ignored

## Interview Walkthrough
1. **Problem**: Find maximum sum path in tree (not necessarily through root)
2. **Challenge**: Path might bend at a node (go through both children)
3. **Key Insight**:
   - At each node, two considerations:
     - Best path THROUGH this node (for answer)
     - Best path INCLUDING this node to parent (for recursion)
4. **Algorithm**:
   - Calculate left and right gains (ignoring negative)
   - maxSum = node + left_gain + right_gain (best path through here)
   - Return = node + max(left_gain, right_gain) (best path for parent)
5. **Example**: root = [1, 2, 3]
   ```
       1
      / \
     2   3
   
   maxGain(2) = 2 (leaf), returns 2
   maxGain(3) = 3 (leaf), returns 3
   At node 1:
   - pathThroughNode = 1 + 2 + 3 = 6, maxSum = 6
   - return 1 + max(2, 3) = 4 (to grandparent if exists)
   ```

## Why This Approach (Optimal)
- ✅ **O(n) time**: Single traversal
- ✅ **O(h) space**: Recursion only
- ✅ **Handles negatives**: Reject negative paths gracefully
- ✅ **Correct logic**: Separates "path through" from "path including"

## Common Mistakes
- Returning maxSum instead of maxGain (breaks parent recursion)
- Not using Math.max(..., 0) to handle negatives
- Confusing pathThroughNode with return value
- Not considering paths through every node
- Not updating maxSum inside every recursive call

## Tips and Tricks
- "Key challenge: path can bend at any node, going through both children"
- "At each node: calculate path through it (for answer) vs path to parent (for recursion)"
- "Use Math.max(..., 0) to ignore negative subtrees"
- "Global variable tracks best answer seen so far"
- "Return value goes to parent, not what we're looking for"

## Critical Detail: Two Different Purposes
```java
// What we calculate
pathThroughNode = root.val + leftGain + rightGain  // Full path (both directions)

// What we return
return root.val + Math.max(leftGain, rightGain)    // Limited path (parent's viewpoint)

// Why different?
// - Parent can only add us if we go in ONE direction
// - But we need to check via BOTH directions for our answer
```

## Example Walkthrough
```
Tree: [-10, 9, 20, null, null, 15, 7]
     -10
     /  \
    9   20
       /  \
      15   7
      
At node 15: maxGain=15, return 15
At node 7:  maxGain=7,  return 7
At node 20: 
  leftGain=15, rightGain=7
  pathThroughNode = 20+15+7 = 42 ← ANSWER!
  return 20+max(15,7) = 35 (to parent)
  
At node 9:  return 9
At node -10:
  leftGain=9, rightGain=35
  pathThroughNode = -10+9+35 = 34 (less than 42)
  return -10+35 = 25
```

## Related Problems
- **LC 543**: Diameter Binary Tree (similar structure, simpler)
- **LC 112**: Path Sum (reach leaf with target)
- **LC 113**: Path Sum II (collect all paths)
- **LC 129**: Sum Root to Leaf Numbers
