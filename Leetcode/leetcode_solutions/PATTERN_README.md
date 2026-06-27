# DFS Recursive Tree Traversal Pattern

## 🎯 When to Use
- Any tree problem
- Need to process all nodes
- "Depth", "height", "path", "sum" keywords
- Bottom-up or top-down traversal

## 📝 Master Template

```java
public ReturnType dfs(TreeNode root) {
    // STEP 1: Base case - handle null/leaf
    if (root == null) {
        return baseValue;  // 0 for counts, null for nodes, etc.
    }
    
    // STEP 2: Recursive calls on subtrees
    ReturnType leftResult = dfs(root.left);
    ReturnType rightResult = dfs(root.right);
    
    // STEP 3: Combine results with current node
    ReturnType currentResult = combine(root.val, leftResult, rightResult);
    
    // STEP 4: (Optional) Update global variable if needed
    globalMax = Math.max(globalMax, someValue);
    
    return currentResult;
}
```

## 🔄 Problem Variations & Modifications

### ✅ LC 104: Maximum Depth (IMPLEMENTED)
**What changes**: Nothing - this IS the template
**Difficulty**: Easy
```java
public int maxDepth(TreeNode root) {
    if (root == null) return 0;
    
    int leftDepth = maxDepth(root.left);
    int rightDepth = maxDepth(root.right);
    
    return 1 + Math.max(leftDepth, rightDepth);
}
```
**Key**: Return 1 + max of subtrees

---

### LC 111: Minimum Depth
**What changes**: Use min instead of max, handle single-child case
**Difficulty**: Easy
```java
public int minDepth(TreeNode root) {
    if (root == null) return 0;
    
    // Special case: only one child exists
    if (root.left == null) return 1 + minDepth(root.right);
    if (root.right == null) return 1 + minDepth(root.left);
    
    // Both children exist
    int leftDepth = minDepth(root.left);
    int rightDepth = minDepth(root.right);
    
    return 1 + Math.min(leftDepth, rightDepth);
}
```
**Key Change**: Must reach a LEAF node (both children null)

---

### LC 110: Balanced Binary Tree
**What changes**: Return -1 if unbalanced, height if balanced
**Difficulty**: Easy
```java
public boolean isBalanced(TreeNode root) {
    return getHeight(root) != -1;
}

private int getHeight(TreeNode root) {
    if (root == null) return 0;
    
    int leftHeight = getHeight(root.left);
    if (leftHeight == -1) return -1;  // Left subtree unbalanced
    
    int rightHeight = getHeight(root.right);
    if (rightHeight == -1) return -1;  // Right subtree unbalanced
    
    // Check if current node is balanced
    if (Math.abs(leftHeight - rightHeight) > 1) {
        return -1;  // Current node unbalanced
    }
    
    return 1 + Math.max(leftHeight, rightHeight);
}
```
**Key Addition**: Use -1 as sentinel value for "unbalanced"

---

### LC 543: Diameter of Binary Tree
**What changes**: Track global max of left + right, return height
**Difficulty**: Easy
```java
private int diameter = 0;  // Global variable

public int diameterOfBinaryTree(TreeNode root) {
    getHeight(root);
    return diameter;
}

private int getHeight(TreeNode root) {
    if (root == null) return 0;
    
    int leftHeight = getHeight(root.left);
    int rightHeight = getHeight(root.right);
    
    // Update diameter (path through this node)
    diameter = Math.max(diameter, leftHeight + rightHeight);
    
    // Return height for parent
    return 1 + Math.max(leftHeight, rightHeight);
}
```
**Key Changes**:
- Global variable for diameter
- Update diameter with `left + right` (path through node)
- Return height (not diameter) for recursion

---

### LC 124: Binary Tree Maximum Path Sum ⭐ HARD
**What changes**: Track global max, handle negative paths
**Difficulty**: Hard
```java
private int maxSum = Integer.MIN_VALUE;

public int maxPathSum(TreeNode root) {
    maxGain(root);
    return maxSum;
}

private int maxGain(TreeNode root) {
    if (root == null) return 0;
    
    // Only take positive gains
    int leftGain = Math.max(maxGain(root.left), 0);
    int rightGain = Math.max(maxGain(root.right), 0);
    
    // Update global max (path through this node)
    int pathThroughNode = root.val + leftGain + rightGain;
    maxSum = Math.max(maxSum, pathThroughNode);
    
    // Return max path including this node (can only go one direction)
    return root.val + Math.max(leftGain, rightGain);
}
```
**Key Changes**:
- Use `Math.max(..., 0)` to ignore negative paths
- Consider path through node vs path including node
- Return single direction path for parent

---

## 💡 Key Insights

### Return Type Matters:
- **Int**: Return depth, height, count
- **Boolean**: Return true/false
- **TreeNode**: Return modified node (mutations)
- **List**: Return all values/paths

### Global Variable Pattern:
```java
private int maxValue = Integer.MIN_VALUE;  // Need global track

public Type dfs(TreeNode root) {
    // ... update globalMax here ...
    globalMax = Math.max(globalMax, someValue);
    // ...
}
```

### Backtracking Pattern (for paths):
```java
path.add(root.val);
dfs(root.left, path, result);
dfs(root.right, path, result);
path.remove(path.size() - 1);  // Backtrack!
```

## Tips and Tricks

1. **Always define base case first**: What should null return?
2. **Understand return value**: What info do I need from subtrees?
3. **Use global variable only when necessary**: Can you return instead?
4. **Test with asymmetric trees**: Single child cases
5. **Test with edge cases**: Empty tree, single node
