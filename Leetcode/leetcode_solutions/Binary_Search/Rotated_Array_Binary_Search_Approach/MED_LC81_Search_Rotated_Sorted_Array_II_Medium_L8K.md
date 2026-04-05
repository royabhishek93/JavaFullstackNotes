# LC 81: Search in Rotated Sorted Array II

**Link**: [leetcode.com/problems/search-in-rotated-sorted-array-ii](https://leetcode.com/problems/search-in-rotated-sorted-array-ii/)

## Problem
Like LC 33 but array may contain duplicates. Return `true` if `target` exists.

## Optimized Approach: Binary Search with Duplicate Skip

```java
public boolean search(int[] nums, int target) {
    int left = 0, right = nums.length - 1;

    while (left <= right) {
        int mid = left + (right - left) / 2;

        if (nums[mid] == target) return true;

        // Can't determine sorted half — skip duplicates
        if (nums[left] == nums[mid] && nums[mid] == nums[right]) {
            left++;
            right--;
        } else if (nums[left] <= nums[mid]) {
            // Left half is sorted
            if (nums[left] <= target && target < nums[mid]) right = mid - 1;
            else left = mid + 1;
        } else {
            // Right half is sorted
            if (nums[mid] < target && target <= nums[right]) left = mid + 1;
            else right = mid - 1;
        }
    }

    return false;
}
```

**Time Complexity**: O(n) worst case (all duplicates), O(log n) average  
**Space Complexity**: O(1)

## Key Insights
- Same logic as LC 33 plus the edge case where `nums[left] == nums[mid] == nums[right]`
- In that case, can't identify sorted half — shrink both ends by 1

## Tips and Tricks
- Binary search the answer only when the search space is monotonic.
- Be explicit about whether the range is inclusive or half-open.
- When debugging, print low, mid, high and check which side is safely discarded.

## Related Problems
- LC 33 Search in Rotated Sorted Array
