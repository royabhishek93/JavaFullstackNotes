# LC 33: Search in Rotated Sorted Array

**Link**: [leetcode.com/problems/search-in-rotated-sorted-array](https://leetcode.com/problems/search-in-rotated-sorted-array/)

## Problem
There is an integer array nums sorted in ascending order (with distinct values). Prior to being passed to your function, nums is possibly rotated at an unknown pivot index k. For example, [0,1,2,4,5,6,7] might be rotated at pivot index 3 and become [4,5,6,7,0,1,2]. Given the rotated array nums and an integer target, return the index of target if it is in nums, or -1 if it is not in nums. You must write an algorithm with O(log n) runtime complexity.

### Examples
- Input: nums = [4,5,6,7,0,1,2], target = 0 → Output: 4
- Input: nums = [4,5,6,7,0,1,2], target = 3 → Output: -1
- Input: nums = [1], target = 1 → Output: 0

## Optimized Approach: Binary Search with Rotation Check

```java
public int search(int[] nums, int target) {
    int left = 0, right = nums.length - 1;

    while (left <= right) {
        int mid = left + (right - left) / 2;

        if (nums[mid] == target) {
            return mid;
        }

        // Determine which half is sorted
        if (nums[left] <= nums[mid]) {  // Left half is sorted
            // Check if target is in sorted left half
            if (nums[left] <= target && target < nums[mid]) {
                right = mid - 1;  // Search left
            } else {
                left = mid + 1;   // Search right
            }
        } else {  // Right half is sorted
            // Check if target is in sorted right half
            if (nums[mid] < target && target <= nums[right]) {
                left = mid + 1;   // Search right
            } else {
                right = mid - 1;  // Search left
            }
        }
    }

    return -1;
}
```

**Time Complexity**: O(log n) - binary search  
**Space Complexity**: O(1) - only pointers

## Key Insights
- **One half is always sorted**: After rotation split
- **Determine sorted half**: Compare nums[left] with nums[mid]
- **Check if target in sorted half**: Only then search that half
- **Otherwise search other half**: Might contain target

## Interview Walkthrough
1. **Problem**: Array is rotated, still binary search
2. **Key challenge**: Array not globally sorted anymore
3. **Insight**: One half is always sorted (the unrotated part)
4. **Algorithm**:
   - Find which half is sorted
   - Check if target is in that sorted half
   - Search accordingly
5. **Example**: [4,5,6,7,0,1,2], target = 0
   ```
   left=0, right=6, mid=3
   nums[mid]=7, not target
   nums[left]=4 <= nums[mid]=7 (left half sorted)
   Is 0 between 4 and 7? No.
   Search right: left=4
   
   left=4, right=6, mid=5
   nums[mid]=1, not target
   nums[left]=0 <= nums[mid]=1 (left half sorted)
   Is 0 between 0 and 1? Yes!
   Search left: right=4
   
   left=4, right=4, mid=4
   nums[mid]=0 == target
   return 4
   ```

## Why This Approach (Optimal)
- ✅ **O(log n) time**: Binary search despite rotation
- ✅ **O(1) space**: Only pointers
- ✅ **Handles rotation**: Always one sorted half

## Common Mistakes
- Comparing with wrong element for mid
- Wrong range checks for target
- Not handling duplicate/edge cases
- Using <= vs < inconsistently

## Tips and Tricks
- "One half is always sorted after rotation"
- "Identify which half is sorted"
- "Check if target in that half, search accordingly"
- "Handle boundary checks carefully"

## Related Problems
- **LC 153**: Find Minimum in Rotated Sorted Array (similar)
- **LC 704**: Binary Search (basic)
- **LC 34**: Find First and Last Position
