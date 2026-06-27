# LC 189: Rotate Array

**Link**: [leetcode.com/problems/rotate-array](https://leetcode.com/problems/rotate-array/)

## Problem
Given an integer array `nums`, rotate the array to the right by `k` steps in-place.

## Optimized Approach: Three Reverses

```java
public void rotate(int[] nums, int k) {
    int n = nums.length;
    k %= n;

    reverse(nums, 0, n - 1);
    reverse(nums, 0, k - 1);
    reverse(nums, k, n - 1);
}

private void reverse(int[] nums, int l, int r) {
    while (l < r) {
        int t = nums[l];
        nums[l++] = nums[r];
        nums[r--] = t;
    }
}
```

**Time Complexity**: O(n)  
**Space Complexity**: O(1)

## Key Insights
- Rotating right by k = reverse all → reverse first k → reverse rest
- Always `k %= n` to handle `k > n`

## Tips and Tricks
- Reverse-based solutions often work when rotation can be decomposed into segments.
- Write down the three reversal steps before coding.
- Normalize k with modulo first to avoid unnecessary work.

## Related Problems
- LC 48 Rotate Image
