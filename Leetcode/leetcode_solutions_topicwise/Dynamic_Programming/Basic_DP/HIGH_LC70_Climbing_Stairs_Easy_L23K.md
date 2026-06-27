# LC 70: Climbing Stairs

**Link**: [leetcode.com/problems/climbing-stairs](https://leetcode.com/problems/climbing-stairs/)

## Problem
You are climbing a staircase. It takes n steps to reach the top. Each time you can climb 1 or 2 steps. In how many distinct ways can you climb to the top?

### Examples
- Input: n = 2 → Output: 2 (1 step + 1 step, or 2 steps)
- Input: n = 3 → Output: 3 (1+1+1, 1+2, 2+1)
- Input: n = 4 → Output: 5
- Input: n = 5 → Output: 8

## Optimized Approach: Dynamic Programming (Bottom-Up)

```java
public int climbStairs(int n) {
    if (n == 1) return 1;
    if (n == 2) return 2;

    int[] dp = new int[n + 1];
    dp[1] = 1;  // 1 way to reach step 1
    dp[2] = 2;  // 2 ways to reach step 2

    // For each step, can come from (i-1) or (i-2)
    for (int i = 3; i <= n; i++) {
        dp[i] = dp[i - 1] + dp[i - 2];
    }

    return dp[n];
}
```

**Space-Optimized (Fibonacci):**
```java
public int climbStairs(int n) {
    if (n == 1) return 1;
    if (n == 2) return 2;

    int prev1 = 2;  // dp[i-1]
    int prev2 = 1;  // dp[i-2]

    for (int i = 3; i <= n; i++) {
        int current = prev1 + prev2;
        prev2 = prev1;
        prev1 = current;
    }

    return prev1;
}
```

**Time Complexity**: O(n)  
**Space Complexity**: O(1) or O(n) depending on version

## Key Insights
- **State**: dp[i] = ways to reach step i
- **Transition**: dp[i] = dp[i-1] + dp[i-2] (can come from 1 or 2 steps back)
- **Base cases**: dp[1] = 1, dp[2] = 2
- **Fibonacci pattern**: Actually Fibonacci sequence!

## Interview Walkthrough
1. **Problem**: Count distinct ways to reach top
2. **Key insight**: To reach step i, must come from i-1 or i-2
3. **DP definition**: dp[i] = number of ways to reach step i
4. **Recurrence**: dp[i] = dp[i-1] + dp[i-2]
5. **Example**: n = 4
   ```
   dp[1] = 1 (just step 1)
   dp[2] = 2 (1+1 or 2)
   dp[3] = dp[2] + dp[1] = 2 + 1 = 3
   dp[4] = dp[3] + dp[2] = 3 + 2 = 5
   
   Ways: (1+1+1+1), (1+1+2), (1+2+1), (2+1+1), (2+2)
   ```

## Why This Approach (Optimal)
- ✅ **O(n) time**: Linear pass
- ✅ **O(1) space**: Only two variables
- ✅ **Simple**: Clear DP transition
- ✅ **Optimal**: Can't do better than reading n

## Common Mistakes
- Wrong base cases
- Forgetting recurrence relation
- Off-by-one errors in loop
- Not initializing correctly

## Tips and Tricks
- "To reach step i, must come from i-1 or i-2"
- "dp[i] = dp[i-1] + dp[i-2] (Fibonacci!)"
- "Space optimization: only track last two values"
- "This is literally Fibonacci sequence"

## Pattern Recognition
```
This is THE classic DP introduction problem
Shows:
1. State definition (what does dp[i] mean?)
2. Base cases (small problem solutions)
3. Recurrence (how to extend from smaller solutions)
4. Implementation (bottom-up iteration)
```

## Related Problems
- **LC 198**: House Robber (similar DP)
- **LC 55**: Jump Game (different DP)
- **LC 213**: House Robber II (circular)
