# LC 300: Longest Increasing Subsequence

**Link**: [leetcode.com/problems/longest-increasing-subsequence](https://leetcode.com/problems/longest-increasing-subsequence/)

## Problem
Return length of the longest strictly increasing subsequence.

## Optimized Approach: Patience Sorting + Binary Search

```java
public int lengthOfLIS(int[] nums) {
    int[] tails = new int[nums.length];
    int size = 0;

    for (int num : nums) {
        int l = 0, r = size;
        while (l < r) {
            int m = l + (r - l) / 2;
            if (tails[m] < num) l = m + 1;
            else r = m;
        }

        tails[l] = num;
        if (l == size) size++;
    }

    return size;
}
```

**Time Complexity**: O(n log n)  
**Space Complexity**: O(n)

## Key Insights
- `tails[i]` = minimum possible tail of increasing subsequence of length `i+1`
- Replace using binary search to keep tails minimal

## Tips and Tricks
- Define the DP state in one sentence before writing transitions.
- Initialize base cases carefully because most DP bugs come from wrong starting values.
- Check whether the transition depends on previous row, previous column, or previous index only.

## Related Problems
- LC 354 Russian Doll Envelopes
