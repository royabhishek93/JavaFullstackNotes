# LC 322: Coin Change

**Link**: [leetcode.com/problems/coin-change](https://leetcode.com/problems/coin-change/)

## Problem
You are given an integer array coins representing coins of different denominations and an integer amount representing a total amount of money. Return the fewest number of coins that you need to make up that amount. If that amount of money cannot be made up by any combination of the coins, return -1. You may assume that you have an infinite number of each kind of coin.

### Examples
- Input: coins = [1,2,5], amount = 11 → Output: 3 (11 = 5 + 5 + 1)
- Input: coins = [2], amount = 3 → Output: -1
- Input: coins = [1], amount = 0 → Output: 0

## Optimized Approach: Bottom-Up DP

```java
public int coinChange(int[] coins, int amount) {
    int[] dp = new int[amount + 1];

    // Initialize all amounts as impossible (use amount + 1)
    Arrays.fill(dp, amount + 1);
    dp[0] = 0;  // Base case: 0 coins needed for amount 0

    // For each amount from 1 to target
    for (int i = 1; i <= amount; i++) {
        // Try each coin
        for (int coin : coins) {
            if (i >= coin) {
                // Take minimum: current dp[i] or (1 + coins needed for remaining amount)
                dp[i] = Math.min(dp[i], dp[i - coin] + 1);
            }
        }
    }

    // If dp[amount] is still impossible value, return -1
    return dp[amount] > amount ? -1 : dp[amount];
}
```

**Time Complexity**: O(amount × coins.length)  
**Space Complexity**: O(amount)

## Key Insights
- **DP Definition**: dp[i] = minimum coins needed to make exactly amount i
- **Base Case**: dp[0] = 0 (no coins needed for amount 0)
- **Impossible Marker**: Use (amount + 1) → always greater than any possible answer
- **Recurrence**: For amount i, try each coin c:
  - dp[i] = min(dp[i], dp[i - c] + 1)
  - If we use coin c, we need 1 + minimum coins for (i - c)
- **Unbounded**: Each coin can be used unlimited times

## Interview Walkthrough
1. **Problem**: Find MINIMUM coins to make exact amount (unlimited coins)
2. **Brute Force**: "Try all combinations recursively - exponential"
3. **Observation**: "Subproblem: what if I use coin X? Then I need coins for (amount - X) + 1"
4. **DP State**: dp[i] = min coins for amount i
5. **Recurrence Relation**: 
   ```
   dp[i] = min over all coins c (dp[i - c] + 1)
   ```
6. **Build Bottom-Up**:
   - Start from amount=0 (base case)
   - Build up to target amount
   - Each amount uses previously computed smaller amounts
7. **Example**: coins=[1,2,5], amount=11
   ```
   dp[0]=0
   dp[1]=1 (use coin 1)
   dp[2]=1 (use coin 2)
   dp[3]=2 (use coins 1+2 or 1+1+1)
   dp[4]=2 (use coins 2+2)
   dp[5]=1 (use coin 5)
   dp[6]=2 (use coins 5+1)
   ...
   dp[11]=3 (use coins 5+5+1)
   ```

## Common Mistakes
- Using 0 as impossible marker instead of (amount+1) → Wrong answer when coin makes 0
- Not checking `if (i >= coin)` → Array index out of bounds
- Forgetting `dp[0] = 0` base case → Everything becomes impossible
- Using memoization without proper check → TLE or stack overflow
- Checking `dp[amount] == amount+1` instead of `> amount` → Wrong logic

## Tips and Tricks
- "This is unbounded knapsack variant - each coin can be used unlimited times"
- "DP builds on previously solved subproblems"
- "Key: for each amount, try using each coin type and take minimum"
- "The impossible marker technique prevents false -1 answers"
- "Walk trace for coins=[1,2,5], amount=5 step-by-step"
