# LC 4: Median of Two Sorted Arrays

**Link**: [leetcode.com/problems/median-of-two-sorted-arrays](https://leetcode.com/problems/median-of-two-sorted-arrays/)

## Problem
Given two sorted arrays `nums1` and `nums2` of sizes `m` and `n`, return the median of the two sorted arrays. Must run in O(log(m+n)).

## Optimized Approach: Binary Search on Smaller Array

```java
public double findMedianSortedArrays(int[] nums1, int[] nums2) {
    // Always binary search on smaller array
    if (nums1.length > nums2.length) return findMedianSortedArrays(nums2, nums1);

    int m = nums1.length, n = nums2.length;
    int lo = 0, hi = m;
    int half = (m + n + 1) / 2;

    while (lo <= hi) {
        int i = lo + (hi - lo) / 2; // partition in nums1
        int j = half - i;           // partition in nums2

        int maxLeft1  = (i == 0) ? Integer.MIN_VALUE : nums1[i - 1];
        int minRight1 = (i == m) ? Integer.MAX_VALUE : nums1[i];
        int maxLeft2  = (j == 0) ? Integer.MIN_VALUE : nums2[j - 1];
        int minRight2 = (j == n) ? Integer.MAX_VALUE : nums2[j];

        if (maxLeft1 <= minRight2 && maxLeft2 <= minRight1) {
            // Correct partition found
            if ((m + n) % 2 == 1) return Math.max(maxLeft1, maxLeft2);
            return (Math.max(maxLeft1, maxLeft2) + Math.min(minRight1, minRight2)) / 2.0;
        } else if (maxLeft1 > minRight2) {
            hi = i - 1; // move partition left in nums1
        } else {
            lo = i + 1; // move partition right in nums1
        }
    }

    return 0.0;
}
```

**Time Complexity**: O(log(min(m, n)))  
**Space Complexity**: O(1)

## Key Insights
- We partition both arrays so that left half has `(m+n+1)/2` elements total
- Binary search on smaller array's partition index
- Valid partition: `maxLeft1 <= minRight2` AND `maxLeft2 <= minRight1`

## Step-by-Step
```
nums1 = [1, 3]      nums2 = [2]
half = 2

i=1, j=1
maxLeft1=1, minRight1=3
maxLeft2=2, minRight2=MAX

1<=MAX ✓ and 2<=3 ✓ → valid
(1+2+3 total=3, odd) → max(1,2) = 2.0
```

## Common Mistakes
- Not handling empty partitions with MIN/MAX_VALUE
- Binary search on wrong (larger) array
- Off-by-one in half calculation

## Tips and Tricks
- Binary search the answer only when the search space is monotonic.
- Be explicit about whether the range is inclusive or half-open.
- When debugging, print low, mid, high and check which side is safely discarded.

## Related Problems
- LC 33 Search in Rotated Sorted Array
- LC 153 Find Minimum in Rotated Sorted Array
