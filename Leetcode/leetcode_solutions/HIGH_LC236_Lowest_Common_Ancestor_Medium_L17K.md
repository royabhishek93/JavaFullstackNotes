# LC 236: Lowest Common Ancestor of a Binary Tree

**Link**: [leetcode.com/problems/lowest-common-ancestor-of-a-binary-tree/](https://leetcode.com/problems/lowest-common-ancestor-of-a-binary-tree/)

## Problem
Given a binary tree, find the lowest common ancestor (LCA) of two given nodes p and q in the tree. The lowest common ancestor is defined between two nodes p and q as the lowest node in the tree that has both p and q as descendants (where a node can be a descendant of itself).

### Examples
- Input: root = [3,5,1,6,2,0,8,null,null,7,4], p = 5, q = 1 → Output: 3
- Input: root = [3,5,1,6,2,0,8,null,null,7,4], p = 5, q = 4 → Output: 5 (5 is ancestor of 4)

## Optimized Approach: Bottom-Up DFS

```java
public TreeNode lowestCommonAncestor(TreeNode root, TreeNode p, TreeNode q) {
    // Base cases
    if (root == null || root == p || root == q) {
        return root;
    }

    // Search in left and right subtrees
    TreeNode left = lowestCommonAncestor(root.left, p, q);
    TreeNode right = lowestCommonAncestor(root.right, p, q);

    // If both sides found something, current node is LCA
    if (left != null && right != null) {
        return root;
    }

    // If only one side found something, return it
    // (might be p, q, or LCA from deeper down)
    return left != null ? left : right;
}
```

**Time Complexity**: O(n) - worst case visit all nodes  
**Space Complexity**: O(h) - recursion stack

## Key Insights
- **Base case includes target**: root == p or root == q
- **Both sides found**: current node is LCA
- **One side found**: LCA is deeper in that subtree
- **Bottom-up**: Build answer from leaves upward

## Interview Walkthrough
1. **Problem**: Find lowest (deepest) node that is ancestor of both p and q
2. **Cases**:
   - Found one target: return it (might be ancestor of other)
   - Found target in both subtrees: current node is LCA
   - Found target in one subtree: LCA is in that subtree
3. **Algorithm**:
   - Base: null or found target
   - Recurse left and right
   - If both non-null: return root (LCA found!)
   - Else return whichever is non-null

## Why This Approach (Optimal)
- ✅ **O(n) time**: Single pass
- ✅ **O(h) space**: Recursion only
- ✅ **Elegant**: No need to store paths
- ✅ **Correct**: Works for all cases

## Common Mistakes
- Not including "root == p or root == q" in base case
- Comparing values instead of node references (root.val == p.val)
- Complex path-finding approach (unnecessary O(n) space)
- Wrong logic when both sides return non-null

## Tips and Tricks
- "If current node IS one of the targets, it might be the LCA"
- "If both subtrees find something, current is LCA"
- "If only one subtree finds something, recurse down"
- "Walk through example showing how both sides work"

## Example Walkthrough
```
Tree:       3
           / \
          5   1
         / \  / \
        6  2 0   8
          / \
         7   4

LCA(5, 4):
- At 3: left subtree has 5, right subtree doesn't have 4 → left=3, right=null
- At 5: left doesn't have 4, right subtree has 4 → left=null, right=4
  
Wait, let me trace correctly:
- Search for p=5 and q=4
- At 3: left finds 5, right doesn't find 4 → return left (5)
- But we need to check: does 5 contain 4? 
- At 5: left doesn't have 4, right subtree (2 has 4) → return right subtree...

Actually LCA(5,4)=5 because 5 is ancestor of 4.
```

## Related Problems
- **LC 235**: Lowest Common Ancestor in BST (use BST property for O(log n))
- **LC 1257**: Smallest Common Region (graph version)
- **LC 1644**: Lowest Common Ancestor with Parent Pointers
- **LC 1676**: Lowest Common Ancestor of a Binary Tree IV (multiple nodes)
