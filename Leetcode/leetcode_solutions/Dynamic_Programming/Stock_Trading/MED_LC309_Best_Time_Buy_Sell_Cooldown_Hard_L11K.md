# LC 309: Best Time to Buy and Sell Stock with Cooldown

**Link**: [leetcode.com/problems/best-time-to-buy-and-sell-stock-with-cooldown](https://leetcode.com/problems/best-time-to-buy-and-sell-stock-with-cooldown/)

## Problem
You are given an array prices where prices[i] is the price of a given stock on day i. Find the maximum profit you can achieve. You may complete as many transactions as you want, but you are not allowed to engage in multiple transactions simultaneously (you must sell the stock before buying again). After you sell your stock, you cannot buy stock on the next day (the cooldown rule).

### Examples
- Input: prices = [3,1,4] → Output: 0 (no profit with cooldown)
- Input: prices = [1,2,4] → Output: 3 (buy 1, sell 4)
- Input: prices = [1,2,3,0,2] → Output: 3 (buy 1, sell 3; day 3 is cooldown; buy 0, sell 2)

## Optimized Approach: State Machine with Cooldown

```java
public int maxProfit(int[] prices) {
    // Three states:
    // buy: holding stock
    // sell: just sold (cooldown today)
    // cooldown: after cooldown, ready to buy again
    
    int buy = Integer.MIN_VALUE;
    int sell = 0;
    int cooldown = 0;

    for (int price : prices) {
        int prevBuy = buy;
        int prevSell = sell;
        int prevCooldown = cooldown;

        // Buy: come from cooldown state
        buy = Math.max(prevBuy, prevCooldown - price);

        // Sell: come from buy state
        sell = prevBuy + price;

        // Cooldown: come from sell state
        cooldown = Math.max(prevCooldown, prevSell);

        // Update for next iteration
        buy = prevBuy;
        sell = Math.max(sell, prevSell);
        cooldown = Math.max(prevCooldown, prevSell);
    }

    // Can't hold stock at end, answer is max of sell/cooldown
    return Math.max(sell, cooldown);
}
```

**Time Complexity**: O(n)  
**Space Complexity**: O(1)

## Key Insights
- **3 states**: Buy (holding), Sell (just sold), Cooldown (resting)
- **Cooldown transition**: After sell, must cooldown before next buy
- **Can only buy from cooldown**: Not from sell state
- **Save previous states**: To avoid mix of new and old values

## Interview Walkthrough
1. **Problem**: Unlimited transactions but must cooldown after selling
2. **State machine**:
   - HOLD/BUY: Currently holding stock
   - SELL: Just sold today (in profit calculation)
   - COOLDOWN: After selling, must wait today
3. **Transitions**:
   - Buy → transition from COOLDOWN (spend money)
   - Sell → transition from BUY (gain from sale)
   - Cooldown → transition from SELL (forced wait)
4. **Example**: [1,2,3,0,2]
   ```
   Day 0: buy=-1
   Day 1: sell=2-1=1, cooldown=0
   Day 2: next cooldown must wait, but can ignore sell from day 1
   Day 3: buy from cooldown state: 0-0=0
   Day 4: sell from buy state: 0-2=2
   ```

## Why This Approach (Optimal)
- ✅ **O(1) space**: Only 3 states
- ✅ **O(n) time**: Single pass
- ✅ **Elegant**: States reflect cooldown constraint
- ✅ **Profitable**: Skips transactions that lose money

## Save Previous State Pattern
```java
// ✅ CORRECT: Save old values before updating
int prevBuy = buy;
int prevSell = sell;  
int prevCooldown = cooldown;

buy = Math.max(prevBuy, prevCooldown - price);
sell = prevBuy + price;
cooldown = Math.max(prevCooldown, prevSell);

// ❌ WRONG: Updates mix old and new values
buy = Math.max(buy, cooldown - price);       // Uses new cooldown
sell = buy + price;                          // Uses new buy!
cooldown = Math.max(cooldown, sell);         // Uses new sell!
```

## Common Mistakes
- Not saving previous states before updating
- Can buy from SELL state (should only come from COOLDOWN)
- Wrong state transitions
- Not returning max(sell, cooldown) at end

## Tips and Tricks
- "This is state machine WITH THREE STATES (not two)"
- "After selling, MUST cooldown before buying again"
- "CRITICAL: Save all previous states before updating"
- "Can skip transactions: if profit negative, stay in cooldown"

## Comparison: Stock Problems Progression
```
LC 121 (1 tx):    2 states, simple
LC 122 (unlimited): Greedy, no states needed
LC 123 (2 tx):    4 states, complex
LC 309 (cooldown): 3 states, temporal constraint
LC 714 (fee):     2 states, cost constraint
LC 188 (k tx):    2k states, generalized
```

## Related Problems
- **LC 121**: Best Time Buy/Sell I (one transaction)
- **LC 122**: Best Time Buy/Sell II (unlimited, no cooldown)
- **LC 123**: Best Time Buy/Sell III (two transactions)
- **LC 188**: Best Time Buy/Sell IV (k transactions)
- **LC 714**: Best Time Buy/Sell With Transaction Fee
