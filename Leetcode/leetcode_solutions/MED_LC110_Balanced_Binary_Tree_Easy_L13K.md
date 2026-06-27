# LC 110: Balanced Binary Tree

**Link**: [leetcode.com/problems/balanced-binary-tree](https://leetcode.com/problems/balanced-binary-tree/)

## Problem
Given a binary tree, determine if it is height-balanced. A binary tree is height-balanced if the absolute difference between the left and right subtrees of every node is no more than 1.

### Examples
- Input: root = [3,9,20,null,null,15,7] → Output: true
- Input: root = [1,2,2,3,3,null,null,4,4] → Output: false (has subtree with height diff = 2)

## Optimized Approach: Bottom-Up DFS with Sentinel Value

```java
public boolean isBalanced(TreeNode root) {
    return getHeight(root) != -1;
}

private int getHeight(TreeNode root) {
    // Base case: null tree is balanced with height 0
    if (root == null) {
        return 0;
    }

    // Check left subtree
    int leftHeight = getHeight(root.left);
    if (leftHeight == -1) {
        return -1;  // Left subtree is unbalanced
    }

    // Check right subtree
    int rightHeight = getHeight(root.right);
    if (rightHeight == -1) {
        return -1;  // Right subtree is unbalanced
    }

    // Check if current node is balanced
    if (Math.abs(leftHeight - rightHeight) > 1) {
        return -1;  // Current node unbalanced
    }

    // Current node is balanced, return height
    return 1 + Math.max(leftHeight, rightHeight);
}
```

**Time Complexity**: O(n) - visit each node once  
**Space Complexity**: O(h) - recursion stack height

## Key Insights
- **Sentinel value -1**: Represents "unbalanced" subtree
- **Early termination**: Return -1 immediately, no need to check further
- **Bottom-up check**: Verify balance from leaves upward
- **Single pass**: Check height and balance simultaneously

## Interview Walkthrough
1. **Problem**: Is every node's left and right subtrees height-balanced?
2. **Brute Force**: Calculate height of each subtree separately O(n²)
3. **Optimization**: Use -1 as "unbalanced" marker
4. **Algorithm**:
   - Get left height: if -1, return -1 (left unbalanced)
   - Get right height: if -1, return -1 (right unbalanced)
   - Check |left - right| <= 1: if false, return -1
   - Otherwise return 1 + max(left, right)
5. **Why it works**:
   - -1 propagates up immediately
   - No unnecessary traversals after finding imbalance
   - O(n) instead of O(n²)

## Why This Approach (Optimal)
- ✅ **O(n) time**: One pass, early termination
- ✅ **O(h) space**: Recursion stack only
- ✅ **Elegant**: Combines height calculation with balance checking

## Common Mistakes
- Using boolean return → forces full tree traversal O(n²)
- Not checking each subtree's balance before current node
- Using -1 for height instead of error indicator
- Returning wrong values (should be -1 for unbalanced)
- Not handling the "check height difference" step properly

## Tips and Tricks
- "Brute force: calculate height of every subtree separately O(n²)"
- "Optimize: use -1 as sentinel for 'unbalanced' and return immediately"
- "Height definition: for balanced node, return 1 + max(left, right)"
- "Why -1? It allows both checking balance AND height in one pass"
- "Early return on first unbalanced subtree saves time"

## Brute Force vs Optimized
```java
// Brute Force O(n²)
public boolean isBalanced(TreeNode root) {
    if (root == null) return true;
    
    int leftHeight = getHeight(root.left);      // O(n)
    int rightHeight = getHeight(root.right);    // O(n)
    
    if (Math.abs(leftHeight - rightHeight) > 1) return false;
    
    return isBalanced(root.left) && isBalanced(root.right);  // Recalculates!
}

// Optimized O(n) - no recalculation
private int getHeight(TreeNode root) {  // Returns height or -1 if unbalanced
    // Single pass: checks balance while computing height
}
```

## Related Problems
- **LC 104**: Maximum Depth (simpler, no balance check)
- **LC 111**: Minimum Depth (reach leaf with different logic)
- **LC 543**: Diameter Binary Tree (track global max)
- **LC 98**: Validate BST (pass constraints down)
