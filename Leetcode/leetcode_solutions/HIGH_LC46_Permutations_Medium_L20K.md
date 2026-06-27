# LC 46: Permutations

**Link**: [leetcode.com/problems/permutations](https://leetcode.com/problems/permutations/)

## Problem
Given an array nums of distinct integers, return all the possible permutations. You can return the answer in any order.

### Examples
- Input: nums = [1,2,3] → Output: [[1,2,3],[1,3,2],[2,1,3],[2,3,1],[3,1,2],[3,2,1]]
- Input: nums = [0,1] → Output: [[0,1],[1,0]]
- Input: nums = [1] → Output: [[1]]

## Optimized Approach: Backtracking with Swap

```java
public List<List<Integer>> permute(int[] nums) {
    List<List<Integer>> result = new ArrayList<>();
    backtrack(result, nums, 0);
    return result;
}

private void backtrack(List<List<Integer>> result, int[] nums, int start) {
    // Base case: reached end, add permutation
    if (start == nums.length) {
        List<Integer> perm = new ArrayList<>();
        for (int num : nums) {
            perm.add(num);
        }
        result.add(perm);
        return;
    }

    // Try swapping each element with start position
    for (int i = start; i < nums.length; i++) {
        // Swap
        swap(nums, start, i);
        
        // Recurse
        backtrack(result, nums, start + 1);
        
        // Backtrack (undo swap)
        swap(nums, start, i);
    }
}

private void swap(int[] nums, int i, int j) {
    int temp = nums[i];
    nums[i] = nums[j];
    nums[j] = temp;
}
```

**Time Complexity**: O(n! * n) - n! permutations, O(n) to copy  
**Space Complexity**: O(n) - recursion depth

## Key Insights
- **In-place swapping**: Build permutations by swapping
- **Partition concept**: Elements [0, start-1] fixed, explore [start, n)
- **Undo swap**: Backtrack by reversing the swap
- **No HashSet needed**: Swapping naturally avoids duplicates

## Interview Walkthrough
1. **Problem**: Generate all permutations of distinct elements
2. **Approach**: Fix position, try all elements in it
3. **Algorithm**:
   - For each position, try swapping with all remaining elements
   - Recurse on next position
   - Undo swap (backtrack)
4. **Example**: [1,2,3]
   ```
   Position 0: Try 1 (swap with 0)
     [1,2,3] Position 1: Try 2
       [1,2,3] Position 2: base case → add [1,2,3]
     [1,2,3] Position 1: Try 3
       [1,3,2] swap back
   Position 0: Try 2 (swap with 1)
     [2,1,3] Position 1: similar...
   ...
   ```

## Why This Approach (Optimal)
- ✅ **O(n) space**: Only recursion depth
- ✅ **In-place**: Modify array, restore with backtrack
- ✅ **Elegant**: Clear swap-recurse-unswap pattern
- ✅ **No duplicates**: Swapping ensures uniqueness

## Common Mistakes
- Forgetting to backtrack (undo swap)
- Creating new list for each recursion level (wastes space)
- Not handling the swap correctly
- Off-by-one in base case

## Tips and Tricks
- "Think of it as: fix position, permute rest"
- "Swap to place each element at current position"
- "CRITICAL: Undo swap after recursing (backtrack)"
- "In-place prevents O(n) space per recursion"

## Alternative: Using unused set
```java
// Track used elements with HashSet (uses O(n) space)
// Less efficient than swap approach
```

## Related Problems
- **LC 47**: Permutations II (with duplicates)
- **LC 78**: Subsets (similar backtracking)
- **LC 39**: Combination Sum (backtracking)
