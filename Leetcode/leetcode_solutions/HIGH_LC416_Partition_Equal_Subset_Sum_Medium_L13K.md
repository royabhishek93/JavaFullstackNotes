# LC 416: Partition Equal Subset Sum

**Link**: [leetcode.com/problems/partition-equal-subset-sum](https://leetcode.com/problems/partition-equal-subset-sum/)

## Problem
Given an integer array `nums`, return `true` if you can partition it into two subsets with equal sum.

## Optimized Approach: 0/1 Knapsack DP (1D)

```java
public boolean canPartition(int[] nums) {
    int total = 0;
    for (int n : nums) total += n;

    if (total % 2 != 0) return false;

    int target = total / 2;
    boolean[] dp = new boolean[target + 1];
    dp[0] = true;

    for (int num : nums) {
        // Iterate right-to-left to avoid reusing same element
        for (int j = target; j >= num; j--) {
            dp[j] |= dp[j - num];
        }
    }

    return dp[target];
}
```

**Time Complexity**: O(n × target)  
**Space Complexity**: O(target)

## Key Insights
- Equivalent to: can a subset sum to `total / 2`?
- 0/1 knapsack: iterate `j` right-to-left prevents double-counting element

## Tips and Tricks
- Define the DP state in one sentence before writing transitions.
- Initialize base cases carefully because most DP bugs come from wrong starting values.
- Check whether the transition depends on previous row, previous column, or previous index only.

## Related Problems
- LC 322 Coin Change (unbounded knapsack)
- LC 39 Combination Sum
