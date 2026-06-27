# LC 88: Merge Sorted Array

**Link**: [leetcode.com/problems/merge-sorted-array](https://leetcode.com/problems/merge-sorted-array/)

## Problem
You are given two integer arrays `nums1` and `nums2`, sorted in non-decreasing order. Merge `nums2` into `nums1` as one sorted array in-place.

## Optimized Approach: Fill from End

```java
public void merge(int[] nums1, int m, int[] nums2, int n) {
    int i = m - 1, j = n - 1, k = m + n - 1;

    while (j >= 0) {
        if (i >= 0 && nums1[i] > nums2[j]) {
            nums1[k--] = nums1[i--];
        } else {
            nums1[k--] = nums2[j--];
        }
    }
}
```

**Time Complexity**: O(m+n)  
**Space Complexity**: O(1)

## Key Insights
- Merge backwards to avoid overwriting unprocessed values in `nums1`
- Only need loop while `j >= 0` because leftover `nums1` already in place

## Tips and Tricks
- State what each pointer represents and how movement changes the invariant.
- If the array is sorted, use pointer movement to eliminate search space instead of nested loops.
- Handle duplicates explicitly when the problem asks for unique answers.

## Related Problems
- LC 26 Remove Duplicates from Sorted Array
- LC 21 Merge Two Sorted Lists
