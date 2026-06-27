# LC 34: Find First and Last Position of Element in Sorted Array

**Link**: [leetcode.com/problems/find-first-and-last-position-of-element-in-sorted-array](https://leetcode.com/problems/find-first-and-last-position-of-element-in-sorted-array/)

## Problem
Given an array of integers nums sorted in non-decreasing order, find the starting and ending position of a given target value. If target is not found in the array, return [-1, -1]. You must write an algorithm with O(log n) runtime complexity.

### Examples
- Input: nums = [5,7,7,8,8,10], target = 8 → Output: [3,4]
- Input: nums = [5,7,7,8,8,10], target = 6 → Output: [-1,-1]
- Input: nums = [], target = 0 → Output: [-1,-1]

## Optimized Approach: Two Binary Searches

```java
public int[] searchRange(int[] nums, int target) {
    if (nums == null || nums.length == 0) {
        return new int[]{-1, -1};
    }

    int first = findFirst(nums, target);
    if (first == -1) {
        return new int[]{-1, -1};
    }

    int last = findLast(nums, target);
    return new int[]{first, last};
}

private int findFirst(int[] nums, int target) {
    int left = 0, right = nums.length - 1;
    int result = -1;

    while (left <= right) {
        int mid = left + (right - left) / 2;
        if (nums[mid] == target) {
            result = mid;
            right = mid - 1;  // Keep searching left for earlier occurrence
        } else if (nums[mid] < target) {
            left = mid + 1;
        } else {
            right = mid - 1;
        }
    }

    return result;
}

private int findLast(int[] nums, int target) {
    int left = 0, right = nums.length - 1;
    int result = -1;

    while (left <= right) {
        int mid = left + (right - left) / 2;
        if (nums[mid] == target) {
            result = mid;
            left = mid + 1;   // Keep searching right for later occurrence
        } else if (nums[mid] < target) {
            left = mid + 1;
        } else {
            right = mid - 1;
        }
    }

    return result;
}
```

**Time Complexity**: O(log n) - two binary searches  
**Space Complexity**: O(1) - only pointers

## Key Insights
- **Two binary searches**: One for first, one for last position
- **Don't stop at first finding**: Continue searching in appropriate direction
- **Early exit**: If first not found, no need to search for last
- **Predefined result**: Track best result seen so far

## Interview Walkthrough
1. **Problem**: Find range [first, last] of target value
2. **Naive approach**: One binary search, then expand left/right (could be O(n))
3. **Better approach**: Two separate binary searches
4. **findFirst**: When found, search LEFT (right = mid - 1)
5. **findLast**: When found, search RIGHT (left = mid + 1)
6. **Example**: [5,7,7,8,8,10], target = 8
   ```
   findFirst:
   left=0, right=5, mid=2
   nums[2]=7 < 8, left=3
   left=3, right=5, mid=4
   nums[4]=8, result=4, right=3
   left=3, right=3, mid=3
   nums[3]=8, result=3, right=2
   Return 3
   
   findLast:
   Similar process but searching right when found
   Return 4
   ```

## Why This Approach (Optimal)
- ✅ **O(log n) time**: Two binary searches
- ✅ **O(1) space**: Only pointers
- ✅ **Correct**: Finds exact boundaries
- ✅ **All cases handled**: No element, one occurrence, many

## Common Mistakes
- Stopping after first occurrence (not finding boundaries)
- Wrong direction after finding (should continue searching)
- Not checking if first = -1 before searching last
- Off-by-one in boundary adjustments

## Tips and Tricks
- "Need two binary searches: one for first, one for last"
- "When found, DON'T stop: search further in that direction"
- "Early exit if target not found (first = -1)"
- "Track result as you search, moving boundary"

## Related Problems
- **LC 704**: Binary Search (basic template)
- **LC 33**: Search in Rotated Sorted Array
- **LC 35**: Search Insert Position
