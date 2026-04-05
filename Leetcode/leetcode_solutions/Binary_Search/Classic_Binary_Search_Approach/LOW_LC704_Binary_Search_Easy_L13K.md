# LC 704: Binary Search

**Link**: [leetcode.com/problems/binary-search](https://leetcode.com/problems/binary-search/)

## Problem
Given an array of integers nums which is sorted in ascending order, and an integer target, write a function to search target in nums. If target exists, return its index. Otherwise, return -1. You must write an algorithm with O(log n) runtime complexity.

### Examples
- Input: nums = [-1,0,3,1,4,1,5], target = 0 → Output: 4
- Input: nums = [-1,0,3,1,4,1,5], target = 5 → Output: -1

## Optimized Approach: Standard Binary Search

```java
public int search(int[] nums, int target) {
    int left = 0;
    int right = nums.length - 1;

    while (left <= right) {
        int mid = left + (right - left) / 2;  // Avoid overflow
        
        if (nums[mid] == target) {
            return mid;
        } else if (nums[mid] < target) {
            left = mid + 1;  // Search right half
        } else {
            right = mid - 1; // Search left half
        }
    }

    return -1;  // Not found
}
```

**Time Complexity**: O(log n) - halves search space each iteration  
**Space Complexity**: O(1) - only pointers

## Key Insights
- **Overflow prevention**: mid = left + (right - left) / 2 not (left + right) / 2
- **Search halving**: Each iteration eliminates half of remaining elements
- **Boundary**: left <= right includes both ends
- **Not found**: If loop ends without finding, element doesn't exist

## Interview Walkthrough
1. **Problem**: Find target in sorted array O(log n)
2. **Approach**: Eliminate half of search space each step
3. **Algorithm**:
   - Mid divides array into two halves
   - Compare mid with target
   - Adjust boundaries based on comparison
4. **Example**: [-1, 0, 3, 1, 4, 1, 5], target = 0
   ```
   left=0, right=6, mid=3 → nums[3]=1, 1>0, right=2
   left=0, right=2, mid=1 → nums[1]=0, found!
   return 1
   ```

## Why This Approach (Optimal)
- ✅ **O(log n) time**: Required by problem
- ✅ **O(1) space**: Only two pointers
- ✅ **Guarantee**: Works on sorted arrays

## Common Mistakes
- Integer overflow in mid calculation
- Wrong boundary conditions
- Off-by-one errors
- Not handling empty array

## Tips and Tricks
- "Use mid = left + (right - left) / 2 to avoid overflow"
- "Three cases: found, too small, too large"
- "Adjust boundaries, don't jump"

## Related Problems
- **LC 33**: Search in Rotated Sorted Array
- **LC 34**: Find First and Last Position
- **LC 35**: Search Insert Position
