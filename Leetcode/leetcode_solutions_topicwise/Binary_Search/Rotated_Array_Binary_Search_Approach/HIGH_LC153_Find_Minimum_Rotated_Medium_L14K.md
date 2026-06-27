# LC 153: Find Minimum in Rotated Sorted Array

**Link**: [leetcode.com/problems/find-minimum-in-rotated-sorted-array](https://leetcode.com/problems/find-minimum-in-rotated-sorted-array/)

## Problem
Suppose an array of length n sorted in ascending order is rotated between 1 and n times. For example, the array [0,1,2,4,5,6,7] might become [4,5,6,7,0,1,2]. Find the minimum element. You must write an algorithm that runs in O(log n) time.

### Examples
- Input: nums = [3,4,5,1,2] → Output: 1
- Input: nums = [2,1] → Output: 1
- Input: nums = [1] → Output: 1
- Input: nums = [1,3] → Output: 1

## Optimized Approach: Binary Search with Rotation Detection

```java
public int findMin(int[] nums) {
    int left = 0, right = nums.length - 1;

    // Early exit if not rotated (or single element)
    if (nums[left] <= nums[right]) {
        return nums[left];
    }

    while (left < right) {
        int mid = left + (right - left) / 2;

        // Check if mid is in rotated section
        if (nums[mid] > nums[right]) {
            // Min is in right half (rotation point passed mid)
            left = mid + 1;
        } else {
            // Min is in left half (including mid)
            right = mid;
        }
    }

    return nums[left];
}
```

**Time Complexity**: O(log n) - binary search  
**Space Complexity**: O(1)

## Key Insights
- **Compare mid with right**: Determines which half has minimum
- **nums[mid] > nums[right]**: Min is definitely right of mid
- **nums[mid] <= nums[right]**: Min is mid or left (could be mid)
- **Use right = mid (not mid-1)**: mid might be minimum

## Interview Walkthrough
1. **Problem**: Find minimum in rotated array, O(log n)
2. **Key insight**: Rotation point (minimum) somewhere in array
3. **Strategy**: Compare mid with right boundary
   - If mid > right: rotation is to the right
   - If mid <= right: rotation is to the left (or none)
4. **Example**: [4,5,6,7,0,1,2]
   ```
   left=0, right=6, mid=3
   nums[3]=7 > nums[6]=2
   Min is right: left=4
   
   left=4, right=6, mid=5
   nums[5]=1 <= nums[6]=2
   Min is left or mid: right=5
   
   left=4, right=5, mid=4
   nums[4]=0 <= nums[5]=1
   Min is left or mid: right=4
   
   left=4, right=4
   Return nums[4]=0
   ```

## Why This Approach (Optimal)
- ✅ **O(log n) time**: Binary search guarantee
- ✅ **O(1) space**: Only pointers
- ✅ **Handles all cases**: Single element, no rotation, rotated

## Common Mistakes
- Using mid instead of right for comparison
- Using mid - 1 when should use mid
- Not handling non-rotated case
- Wrong boundary adjustment

## Tips and Tricks
- "Compare nums[mid] with nums[right], NOT nums[left]"
- "If mid > right: min definitely right of mid"
- "If mid <= right: min is mid or left (use right=mid)"
- "Why nums[right]? It's outside the rotation point"

## Edge Cases
- Single element
- Two elements
- Not rotated (already sorted)
- Fully rotated (almost back to original)

## Related Problems
- **LC 33**: Search in Rotated Sorted Array (harder)
- **LC 704**: Binary Search (basic)
