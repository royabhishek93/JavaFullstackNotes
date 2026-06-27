# LC 45: Jump Game II

**Link**: [leetcode.com/problems/jump-game-ii](https://leetcode.com/problems/jump-game-ii/)

## Problem
Given `nums`, return minimum number of jumps to reach last index.

## Optimized Approach: Greedy BFS-Layer View

```java
public int jump(int[] nums) {
    int jumps = 0;
    int currentEnd = 0;
    int farthest = 0;

    for (int i = 0; i < nums.length - 1; i++) {
        farthest = Math.max(farthest, i + nums[i]);

        if (i == currentEnd) {
            jumps++;
            currentEnd = farthest;
        }
    }

    return jumps;
}
```

**Time Complexity**: O(n)  
**Space Complexity**: O(1)

## Key Insights
- Current jump covers range `[0..currentEnd]`
- When range ends, take one jump and extend to `farthest`

## Tips and Tricks
- A greedy choice is valid only if you can justify why local optimality leads to global optimality.
- When unsure, compare the greedy idea with a DP formulation to validate it.
- Track the exact invariant that each greedy update preserves.

## Related Problems
- LC 55 Jump Game
