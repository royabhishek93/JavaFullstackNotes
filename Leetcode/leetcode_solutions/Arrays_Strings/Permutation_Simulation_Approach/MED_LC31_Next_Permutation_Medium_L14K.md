# LC 31: Next Permutation

**Link**: [leetcode.com/problems/next-permutation](https://leetcode.com/problems/next-permutation/)

## Problem
Rearrange numbers into the lexicographically next greater permutation. If not possible, rearrange to lowest order.

## Optimized Approach: Pivot + Swap + Reverse

```java
public void nextPermutation(int[] nums) {
    int i = nums.length - 2;

    // 1) Find first decreasing element from right
    while (i >= 0 && nums[i] >= nums[i + 1]) i--;

    // 2) If exists, swap with next greater from right
    if (i >= 0) {
        int j = nums.length - 1;
        while (nums[j] <= nums[i]) j--;
        swap(nums, i, j);
    }

    // 3) Reverse suffix to get smallest order
    reverse(nums, i + 1, nums.length - 1);
}

private void swap(int[] nums, int i, int j) {
    int t = nums[i]; nums[i] = nums[j]; nums[j] = t;
}

private void reverse(int[] nums, int l, int r) {
    while (l < r) swap(nums, l++, r--);
}
```

**Time Complexity**: O(n)  
**Space Complexity**: O(1)

## Key Insights
- Suffix after pivot is non-increasing
- Swap pivot with just-larger element, then reverse suffix

## Tips and Tricks
- Find the pivot where the order stops increasing from the right.
- After the swap, restore the smallest lexicographic suffix by reversing or sorting it.
- A one-line mistake in pivot detection usually breaks the entire permutation logic.

## Related Problems
- LC 46 Permutations
