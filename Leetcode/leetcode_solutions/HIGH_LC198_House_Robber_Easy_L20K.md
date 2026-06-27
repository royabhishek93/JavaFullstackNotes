# LC 198: House Robber

**Link**: [leetcode.com/problems/house-robber](https://leetcode.com/problems/house-robber/)

## Problem
You are a robber, and adjacent houses cannot both be robbed. Given `nums[i]` representing the amount in house `i`, return the maximum amount you can rob.

## Optimized Approach: DP with O(1) Space

```java
public int rob(int[] nums) {
    if (nums.length == 1) return nums[0];

    int prev2 = 0, prev1 = 0;

    for (int num : nums) {
        int cur = Math.max(prev1, prev2 + num);
        prev2 = prev1;
        prev1 = cur;
    }

    return prev1;
}
```

**Time Complexity**: O(n)  
**Space Complexity**: O(1)

## Key Insights
- At each house: either skip (take prev1) or rob (take prev2 + current)
- Only need 2 previous values; no full DP array needed

## Tips and Tricks
- Define the DP state in one sentence before writing transitions.
- Initialize base cases carefully because most DP bugs come from wrong starting values.
- Check whether the transition depends on previous row, previous column, or previous index only.

## Related Problems
- LC 213 House Robber II (circular)
- LC 337 House Robber III (tree)
