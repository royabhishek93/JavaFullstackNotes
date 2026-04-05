# LC 123: Best Time to Buy and Sell Stock III

**Link**: [leetcode.com/problems/best-time-to-buy-and-sell-stock-iii](https://leetcode.com/problems/best-time-to-buy-and-sell-stock-iii/)

## Problem
You are given an array prices where prices[i] is the price of a given stock on day i. Find the maximum profit you can achieve. You may complete at most two transactions (buy one and sell one share of the stock, then buy one and sell one share again). Note: You cannot hold multiple shares at the same time. This means you must sell before buying again.

### Examples
- Input: prices = [3,3,5,0,0,3,1,4] → Output: 6 (buy 3 at index 2, sell 5 at index 4 → profit 2; buy 0, sell 4 → profit 4; total 6)
- Input: prices = [1,2,3,4,5] → Output: 4 (one transaction: buy 1, sell 5)
- Input: prices = [7,6,4,3,1] → Output: 0

## Optimized Approach: State Machine (4 States)

```java
public int maxProfit(int[] prices) {
    // State machine with 4 states:
    // buy1: after first buy
    // sell1: after first sell
    // buy2: after second buy
    // sell2: after second sell
    
    int buy1 = Integer.MIN_VALUE;
    int sell1 = 0;
    int buy2 = Integer.MIN_VALUE;
    int sell2 = 0;

    for (int price : prices) {
        buy1 = Math.max(buy1, -price);                    // Buy or hold
        sell1 = Math.max(sell1, buy1 + price);            // Sell or hold
        buy2 = Math.max(buy2, sell1 - price);             // Buy again or hold
        sell2 = Math.max(sell2, buy2 + price);            // Sell again or hold
    }

    return sell2;
}
```

**Time Complexity**: O(n)  
**Space Complexity**: O(1)

## Key Insights
- **State machine**: Track 4 states (buy1, sell1, buy2, sell2)
- **Sequential constraint**: Must sell1 before buy2
- **hold is option**: Each transition can choose to hold instead
- **Update order matters**: Use previous states before updating

## Interview Walkthrough
1. **Problem**: Exactly 2 transactions (0, 1, or 2)
2. **State transitions**:
   - After buy1: have spent money, profit = -price
   - After sell1: add profit, profit = buy1 + price
   - After buy2: spend using sell1 profit, profit = sell1 - price
   - After sell2: final profit = buy2 + price

3. **Example**: [3,3,5,0,0,3,1,4]
   ```
   day 0 (price=3): buy1=-3, sell1=0, buy2=-3, sell2=0
   day 1 (price=3): buy1=-3, sell1=0, buy2=-3, sell2=0
   day 2 (price=5): 
     buy1=max(-3, -5)=-3
     sell1=max(0, -3+5)=2
     buy2=max(-3, 2-5)=-3
     sell2=max(0, -3+5)=2
   day 3 (price=0):
     buy1=max(-3, -0)=-0
     sell1=max(2, -0+0)=2
     buy2=max(-3, 2-0)=2
     sell2=max(2, 2+0)=2
   day 7 (price=4):
     buy2=max(..., 2-4)=-2
     sell2=max(2, -2+4)=2+(4-0)=6
   ```

## Why This Approach (Optimal)
- ✅ **O(1) space**: Only 4 variables
- ✅ **O(n) time**: Single pass
- ✅ **Elegant**: State transitions clear
- ✅ **Generalizable**: Works for 1, 2, or k transactions

## Critical Order
```java
// ✅ CORRECT: Update in sequence
buy1 = Math.max(buy1, -price);
sell1 = Math.max(sell1, buy1 + price);       // Uses new buy1
buy2 = Math.max(buy2, sell1 - price);        // Uses new sell1
sell2 = Math.max(sell2, buy2 + price);       // Uses new buy2

// ❌ WRONG: Saving old values breaks state
int oldBuy1 = buy1;
buy1 = Math.max(buy1, -price);
sell1 = Math.max(sell1, oldBuy1 + price);    // Misses optimization
```

## Common Mistakes
- Wrong update order (not sequential)
- Using Integer.MIN_VALUE instead of negative price for buy1
- Not initializing sell states to 0
- Complex DP array approach (not needed)

## Tips and Tricks
- "State machine with 4 states: buy1, sell1, buy2, sell2"
- "Each state transitions: hold or take action"
- "Must update in sequence: buy1→sell1→buy2→sell2"
- "Answer is sell2 (final state)"

## Comparison: 1, 2, k Transactions
```
LC 121 (1 tx):  O(n) space, 2 states, simpler
LC 123 (2 tx):  O(1) space, 4 states, state machine
LC 188 (k tx):  O(k·n) space, 2k states, generalized
```

## Related Problems
- **LC 121**: Best Time Buy/Sell Stock I (one transaction)
- **LC 122**: Best Time Buy/Sell II (unlimited transactions)
- **LC 188**: Best Time Buy/Sell IV (k transactions)
- **LC 309**: Best Time Buy/Sell With Cooldown
- **LC 714**: Best Time Buy/Sell With Transaction Fee
