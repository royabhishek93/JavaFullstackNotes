# LC 122: Best Time to Buy and Sell Stock II

**Link**: [leetcode.com/problems/best-time-to-buy-and-sell-stock-ii](https://leetcode.com/problems/best-time-to-buy-and-sell-stock-ii/)

## Problem
You are given an array prices where prices[i] is the price of a given stock on day i. Find the maximum profit you can achieve. You may complete as many transactions as you want (buy one and sell one share of the stock multiple times). Note: You cannot hold multiple shares of the same stock at the same time. This means you must sell the stock before you buy again.

### Examples
- Input: prices = [7,1,5,3,6,4] → Output: 7 (buy 1 at 1, sell at 5 → profit 4; buy at 3, sell at 6 → profit 3; total 7)
- Input: prices = [1,2,3,4,5] → Output: 4 (buy at 1, sell at 5)
- Input: prices = [7,6,4,3,1] → Output: 0 (no profit possible)

## Optimized Approach: Sum Every Profitable Jump

```java
public int maxProfit(int[] prices) {
    int profit = 0;
    for (int i = 1; i < prices.length; i++) {
        // If tomorrow is higher, lock in the gain
        if (prices[i] > prices[i - 1]) {
            profit += prices[i] - prices[i - 1];
        }
    }
    return profit;
}
```

**Time Complexity**: O(n)  
**Space Complexity**: O(1)

## Key Insights
- **Unlimited transactions**: Model as capturing every up-movement
- **Sum jumps, not find valley-peak**: prices[i] - prices[i-1] for each increase
- **No holding stock**: Simplifies to greedy approach
- **Intuition**: [1,2,3,4,5] = (2-1) + (3-2) + (4-3) + (5-4) = 4

## Interview Walkthrough
1. **Problem**: Multiple buy-sell transactions allowed
2. **Key Insight**: Unlimited transactions = sum of all profitable single-day jumps
3. **Why this works**:
   - Buy at 1, sell at 5 = (2-1) + (3-2) + (4-3) + (5-4)
   - Can't do better by splitting into two transactions
4. **Algorithm**: For each day, if tomorrow > today, add the difference
5. **Example**: [7,1,5,3,6,4]
   ```
   (5-1) + (6-3) = 4 + 3 = 7
   (prices[2]-prices[1]) + (prices[4]-prices[3])
   ```

## Why This Approach (Optimal)
- ✅ **O(1) space**: No state machine needed
- ✅ **O(n) time**: Single pass
- ✅ **Greedy works**: Unlimited transactions remove constraints
- ✅ **Elegant**: One line logic

## Common Mistakes
- Complex state machine (unnecessary for unlimited transactions)
- Trying to find valley-peak pairs (overthinking)
- Negative profit handling (just skip if tomorrow ≤ today)
- Integer overflow (unlikely with prices ≤ 10^5)

## Tips and Tricks
- "Unlimited transactions = sum of every profitable jump"
- "Don't think 'when to buy/sell', think 'capture every gain'"
- "If tomorrow > today, we profit, so add difference"

## Comparison with LC 121 (One Transaction)
```
LC 121: [7,1,5,3,6,4] → 5 (buy 1, sell 6)
LC 122: [7,1,5,3,6,4] → 7 (buy 1 sell 5, then buy 3 sell 6)

LC 122 approach: (5-1) + (6-3) = 7
```

## Related Problems
- **LC 121**: Best Time Buy/Sell Stock I (one transaction only)
- **LC 123**: Best Time Buy/Sell III (two transactions)
- **LC 188**: Best Time Buy/Sell IV (k transactions)
- **LC 309**: Best Time Buy/Sell With Cooldown
- **LC 714**: Best Time Buy/Sell With Transaction Fee
