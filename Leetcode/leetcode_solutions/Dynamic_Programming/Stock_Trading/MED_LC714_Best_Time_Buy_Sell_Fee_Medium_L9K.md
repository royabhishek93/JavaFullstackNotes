# LC 714: Best Time to Buy and Sell Stock with Transaction Fee

**Link**: [leetcode.com/problems/best-time-to-buy-and-sell-stock-with-transaction-fee](https://leetcode.com/problems/best-time-to-buy-and-sell-stock-with-transaction-fee/)

## Problem
You are given an array prices where prices[i] is the price of a given stock on day i, and an integer fee representing a transaction fee. Find the maximum profit you can achieve. You may complete as many transactions as you want, but you need to pay the transaction fee on each sell. Note: You cannot hold multiple shares at the same time.

### Examples
- Input: prices = [1,3,2,8,4,9], fee = 2 → Output: 8 (buy 1, sell 8 → fee 2 → profit 8-1-2=5; buy 4, sell 9 → fee 2 → profit 9-4-2=3; total 8)
- Input: prices = [1,3,7,5,10,3], fee = 3 → Output: 6

## Optimized Approach: State Machine with Fee

```java
public int maxProfit(int[] prices, int fee) {
    // Two states:
    // hold: currently holding stock
    // sold: currently not holding stock
    
    int hold = -prices[0];      // Buy first stock
    int sold = 0;               // No stock held initially

    for (int i = 1; i < prices.length; i++) {
        // Sell today or continue holding
        int newSold = Math.max(sold, hold + prices[i] - fee);
        
        // Buy today or continue not holding
        int newHold = Math.max(hold, sold - prices[i]);

        hold = newHold;
        sold = newSold;
    }

    return sold;    // Must end without holding stock
}
```

**Time Complexity**: O(n)  
**Space Complexity**: O(1)

## Key Insights
- **2 states**: Hold stock or don't hold stock
- **Fee on sell**: Subtract fee when selling (hold + price - fee)
- **Simple transitions**: Just buy/sell/hold decisions
- **End in sold**: Can't hold stock at finish

## Interview Walkthrough
1. **Problem**: Unlimited transactions with fee per sell
2. **Difference from LC 122**:
   - LC 122: Greedy, sum all positive jumps
   - LC 714: State machine, account for fee
3. **State transitions**:
   - HOLD: Stay holding or buy from SOLD
   - SOLD: Stay sold or sell from HOLD (minus fee)
4. **Example**: [1,3,2,8,4,9], fee=2
   ```
   Day 0: hold=-1, sold=0
   Day 1 (price=3):
     newSold = max(0, -1+3-2) = max(0, 0) = 0
     newHold = max(-1, 0-3) = max(-1, -3) = -1
   Day 2 (price=2):
     newSold = max(0, -1+2-2) = 0
     newHold = max(-1, 0-2) = -1
   Day 3 (price=8):
     newSold = max(0, -1+8-2) = 5
     newHold = max(-1, 5-8) = -1
   Day 5 (price=9):
     newSold = max(5, -1+9-2) = max(5, 6) = 6
     newHold = max(-1, 6-9) = -1
   But can we do better? Let me retrace...
   Actually: buy at 1, hold, sell at 8 (profit 7-2=5)
            buy at 4, hold, sell at 9 (profit 5-2=3)
            total = 8
   ```

## Why This Approach (Optimal)
- ✅ **O(1) space**: Only 2 variables
- ✅ **O(n) time**: Single pass
- ✅ **Simple logic**: Pure state transitions
- ✅ **Fee handled elegantly**: Subtracted at sell

## Common Mistakes
- Subtracting fee from buy (should be from sell)
- Forgetting to return sold (not hold)
- Not updating both states before using in next iteration
- Comparing greedy vs state machine approaches

## Tips and Tricks
- "Similar to LC 122 but state machine because of fee"
- "Fee changes economics: might skip some transactions"
- "HOLD state: -prices[0] initially, later max(hold, sold - price)"
- "SOLD state: max(sold, hold + price - fee)"
- "End: return sold (can't hold at finish)"

## Fee Intuition
```
Without fee: Sum of positive jumps (greedy works)
[1,3,2,8,4,9] → (3-1) + (8-2) + (9-4) = 2+6+5 = 13

With fee=2: State machine necessary
Each sell costs 2, so some transactions not profitable
Example: buy-sell in 2 days = 1-day jump, if profit < fee, skip
```

## Related Problems
- **LC 121**: Best Time Buy/Sell I (one transaction)
- **LC 122**: Best Time Buy/Sell II (unlimited, no fee)
- **LC 123**: Best Time Buy/Sell III (two transactions)
- **LC 188**: Best Time Buy/Sell IV (k transactions)
- **LC 309**: Best Time Buy/Sell With Cooldown
