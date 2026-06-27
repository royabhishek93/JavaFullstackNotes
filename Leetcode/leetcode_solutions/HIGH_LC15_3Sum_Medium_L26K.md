# LC 15: 3Sum

**Link**: [leetcode.com/problems/3sum](https://leetcode.com/problems/3sum/)

## Problem
Given an integer array nums, return all triplets [nums[i], nums[j], nums[k]] such that i != j, i != k, and j != k, and nums[i] + nums[j] + nums[k] == 0. Notice that the solution set must not contain duplicate triplets.

### Examples
- Input: nums = [-1,0,1,2,-1,-4] → Output: [[-1,-1,2],[-1,0,1]]
- Input: nums = [0,1,1] → Output: []
- Input: nums = [0,0,0] → Output: [[0,0,0]]

## Optimized Approach: Two Pointers After Sorting

```java
public List<List<Integer>> threeSum(int[] nums) {
    List<List<Integer>> result = new ArrayList<>();
    
    if (nums == null || nums.length < 3) {
        return result;
    }

    Arrays.sort(nums);

    for (int i = 0; i < nums.length - 2; i++) {
        if (nums[i] > 0) break;  // Optimization: no positive triplets sum to 0
        
        if (i > 0 && nums[i] == nums[i - 1]) continue;  // Skip duplicate fixed element

        int left = i + 1, right = nums.length - 1;
        int target = -nums[i];

        while (left < right) {
            int sum = nums[left] + nums[right];

            if (sum == target) {
                result.add(Arrays.asList(nums[i], nums[left], nums[right]));

                // Skip duplicates on left
                while (left < right && nums[left] == nums[left + 1]) left++;
                // Skip duplicates on right
                while (left < right && nums[right] == nums[right - 1]) right--;

                left++;
                right--;
            } else if (sum < target) {
                left++;
            } else {
                right--;
            }
        }
    }

    return result;
}
```

**Time Complexity**: O(n²) - sorting O(n log n), then two nested loops O(n²)  
**Space Complexity**: O(1) - excluding output array

## Key Insights
- **Reduce to 2Sum**: Fix one element, find two-sum on rest
- **Sort for De-duplication**: Enables easy duplicate skipping
- **Early Break**: If nums[i] > 0, no solution possible
- **Skip Duplicates**: At all three positions (fixed, left, right)
- **Two Pointers**: Move apart based on sum comparison

## Interview Walkthrough
1. **Problem**: Find ALL triplets summing to zero (no duplicates in result)
2. **Key Insight**: If we sort, we can use two pointers for remaining elements
3. **Reduce Dimension**: 3Sum = 1 fixed element + 2Sum on rest
4. **Duplicate Handling**: Sort enables checking i == i-1, left == left+1, right == right-1
5. **Algorithm Flow**:
   - Sort array
   - For each element as fixed value
   - Use two pointers to find pairs summing to -fixed value
   - Skip duplicates to avoid duplicate triplets
6. **Example**: [-1, 0, 1, 2, -1, -4]
   - After sort: [-4, -1, -1, 0, 1, 2]
   - Fix -1: find pairs summing to 1 → [-1, 0, 1]
   - Fix 0: find pairs summing to 0 → [0] (no valid pairs left)

## Common Mistakes
- Forgetting to skip duplicates → duplicate triplets in result
- Wrong target calculation (should be -nums[i] not target-nums[i])
- Moving pointers wrong direction when sum < target (should move left, not right)
- Starting from i=0 without optimization (missing early break when nums[i] > 0)

## Tips and Tricks
- State what each pointer represents and how movement changes the invariant.
- If the array is sorted, use pointer movement to eliminate search space instead of nested loops.
- Handle duplicates explicitly when the problem asks for unique answers.
