# LC 98: Validate Binary Search Tree

**Link**: [leetcode.com/problems/validate-binary-search-tree/](https://leetcode.com/problems/validate-binary-search-tree/)

## Problem
Given the root of a binary tree, determine if it is a valid binary search tree (BST). A valid BST is defined as follows:
- The left subtree of a node contains only nodes with keys less than the node's key
- The right subtree of a node contains only nodes with keys greater than the node's key
- Both the left and right subtrees must also be binary search trees

### Examples
- Input: root = [2,1,3] → Output: true
- Input: root = [5,1,4,null,null,3,6] → Output: false (4 in right subtree of 5, but 4 < 5)

## Optimized Approach: DFS with Range Constraints

```java
public boolean isValidBST(TreeNode root) {
    return validate(root, null, null);
}

private boolean validate(TreeNode root, Integer min, Integer max) {
    if (root == null) {
        return true;
    }

    // Check current node value against allowed range
    if ((min != null && root.val <= min) || 
        (max != null && root.val >= max)) {
        return false;
    }

    // Left subtree: values must be < root.val
    // So upper bound becomes root.val
    boolean leftValid = validate(root.left, min, root.val);

    // Right subtree: values must be > root.val
    // So lower bound becomes root.val
    boolean rightValid = validate(root.right, root.val, max);

    return leftValid && rightValid;
}
```

**Time Complexity**: O(n) - visit each node once  
**Space Complexity**: O(h) - recursion stack

## Key Insights
- **Range constraints**: Pass min/max bounds down
- **Use Integer for null**: Allows distinguishing "no constraint" from 0
- **Update bounds**: Left uses root as max, right uses root as min
- **Validate all constraints**: Must satisfy ALL inherited constraints

## Interview Walkthrough
1. **Problem**: Verify if tree satisfies BST property
2. **Key Challenge**: 
   - Node 5 has left child 1 (valid: 1<5)
   - Node 5 has right child 4 (invalid: 4<5, violates BST)
   - Node 4 is in right subtree of 5 but 4 is too small!
3. **Solution**: Pass constraint ranges
   - Left subtree of node: all values < node
   - Right subtree of node: all values > node
4. **Algorithm**:
   - For each node, check: min < value < max
   - Recurse left with max=node.val
   - Recurse right with min=node.val
   - Both must be valid

## Why This Approach (Optimal)
- ✅ **O(n) time**: Single pass
- ✅ **Correct**: Catches invalid BSTs like [5,1,4,null,null,3,6]
- ✅ **Clean**: Constraints propagate naturally

## Common Mistakes
- Only checking immediate children (missing deep violations)
- Using Integer (not Integer) for bounds (can't handle null)
- Comparing with wrong bounds
- Using < instead of <= (or > instead of >=)
- Not propagating constraints to children

## Tips and Tricks
- "A node's value must satisfy ALL inherited constraints"
- "Left subtree: all values < node, right subtree: all values > node"
- "Use Integer (nullable) to distinguish 'no bound' from value 0"
- "Walk through [5,1,4,null,null,3,6] showing invalid node 4"

## Comparison: Wrong Approaches
```java
// ❌ WRONG: Only checks immediate children
public boolean isValidBST(TreeNode root) {
    if (root == null) return true;
    if (root.left != null && root.left.val >= root.val) return false;
    if (root.right != null && root.right.val <= root.val) return false;
    return isValidBST(root.left) && isValidBST(root.right);
}
// This fails on [5,1,4,null,null,3,6] because 3 is deep

// ✅ CORRECT: Propagates constraints
private boolean validate(TreeNode root, Integer min, Integer max) {
    if (root == null) return true;
    if ((min != null && root.val <= min) || 
        (max != null && root.val >= max)) return false;
    return validate(root.left, min, root.val) && 
           validate(root.right, root.val, max);
}
```

## Related Problems
- **LC 235**: Lowest Common Ancestor in BST (use BST property)
- **LC 230**: Kth Smallest in BST (in-order traversal)
- **LC 99**: Recover BST (find and fix violations)
- **LC 108**: Convert Sorted Array to BST
