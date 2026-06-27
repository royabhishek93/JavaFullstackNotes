# LC 55: Jump Game

**Link**: [leetcode.com/problems/jump-game](https://leetcode.com/problems/jump-game/)

## Problem
You are given an integer array nums. You are initially positioned at the array's first index, and each element in the array represents your maximum jump length from that position. Determine if you can reach the last index.

### Examples
- Input: nums = [2,3,1,1,4] → Output: true (jump 1 step from index 0 to 1, then 3 steps to last)
- Input: nums = [3,2,1,0,4] → Output: false (always arrive at index 3, max jump is 0)

## Optimized Approach: Greedy (Track Max Reachable)

```java
public boolean canJump(int[] nums) {
    int maxReach = 0;

    for (int i = 0; i < nums.length; i++) {
        // If current index is unreachable, return false
        if (i > maxReach) {
            return false;
        }

        // Update max reachable
        maxReach = Math.max(maxReach, i + nums[i]);

        // If can reach last index, return true
        if (maxReach >= nums.length - 1) {
            return true;
        }
    }

    return false;
}
```

**Time Complexity**: O(n) - single pass  
**Space Complexity**: O(1) - only one variable

## Key Insights
- **Greedy approach**: Track maximum index reachable
- **Early exit**: If reach end, can stop early
- **Unreachable**: If current index > maxReach, can't proceed
- **Intuition**: Can only reach index if it's <= maxReach

## Interview Walkthrough
1. **Problem**: Can we reach the last index?
2. **Brute force**: Try all combinations (exponential)
3. **Better intuition**: What's the farthest we can go?
4. **Greedy insight**: At each index, update farthest reachable
5. **Example**: [2,3,1,1,4]
   ```
   i=0: nums[0]=2, max_reach=0+2=2
   i=1: i<=2 ✓, nums[1]=3, max_reach=max(2,1+3)=4
   i=2: i<=4 ✓, max_reach>=4 (last index), return true
   ```
6. **Counter-example**: [3,2,1,0,4]
   ```
   i=0: max_reach=0+3=3
   i=1: max_reach=max(3,1+2)=3
   i=2: max_reach=max(3,2+1)=3
   i=3: max_reach=max(3,3+0)=3
   i=4: i=4 > max_reach=3, return false
   ```

## Why This Approach (Optimal)
- ✅ **O(n) time**: Single pass
- ✅ **O(1) space**: Only one variable
- ✅ **Greedy works**: Always optimal to jump furthest
- ✅ **Simple**: Clear logic

## Common Mistakes
- Using complex DP when greedy works
- Wrong condition for unreachable
- Not updating maxReach correctly
- Off-by-one in last index

## Tips and Tricks
- "Track the farthest point we can reach"
- "If current position > farthest, we're stuck"
- "Greedy: always jump farthest (updates maxReach)"
- "Early exit: if reach end, done!"

## Why Greedy Works
```
At each position, jumping furthest is always optimal
because it maximizes our range for future jumps
No need to explore all combinations
```

## Related Problems
- **LC 45**: Jump Game II (minimum jumps, different problem)
- **LC 1306**: Jump Game III (different rules)
- **LC 1871**: Jump Game VII (different rules)
