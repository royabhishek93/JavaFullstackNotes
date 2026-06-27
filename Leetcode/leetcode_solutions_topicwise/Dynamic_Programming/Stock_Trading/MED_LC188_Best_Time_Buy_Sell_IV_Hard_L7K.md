# LC 188: Best Time to Buy and Sell Stock IV

**Link**: [leetcode.com/problems/best-time-to-buy-and-sell-stock-iv](https://leetcode.com/problems/best-time-to-buy-and-sell-stock-iv/)

## Problem
You are given an integer array prices where prices[i] is the price of a given stock on day i, and an integer k. Find the maximum profit you can achieve. You may complete at most k transactions (buy one and sell one share of the stock multiple times). Note: You cannot hold multiple shares at the same time.

### Examples
- Input: k = 2, prices = [3,2,6,5,0,3] → Output: 7 (buy 2, sell 6 → profit 4; buy 5, sell 0 is negative, buy 0, sell 3 → profit 3; total 7)
- Input: k = 2, prices = [1,2,4,2,5,7,2,4,9,0] → Output: 13 (buy 1, sell 4, buy 2, sell 9 = 3 + 7 = 10? or other combo = 13)

## Optimized Approach: State Machine (2k States) with Optimization

```java
public int maxProfit(int k, int[] prices) {
    if (prices.length < 2 || k == 0) return 0;

    // If k >= n/2, unlimited transactions (like LC 122)
    if (k >= prices.length / 2) {
        int profit = 0;
        for (int i = 1; i < prices.length; i++) {
            profit += Math.max(0, prices[i] - prices[i - 1]);
        }
        return profit;
    }

    // k transactions: 2k states (buy1, sell1, buy2, sell2, ...)
    int[] buy = new int[k + 1];
    int[] sell = new int[k + 1];

    for (int i = 0; i <= k; i++) {
        buy[i] = Integer.MIN_VALUE;  // Haven't done transaction yet
        sell[i] = 0;                 // No profit yet
    }

    for (int price : prices) {
        for (int j = k; j >= 1; j--) {
            sell[j] = Math.max(sell[j], buy[j] + price);
            buy[j] = Math.max(buy[j], sell[j - 1] - price);
        }
    }

    return sell[k];
}
```

**Time Complexity**: O(k·n) or O(n) if k ≥ n/2  
**Space Complexity**: O(k)

## Key Insights
- **2k states**: buy[j] and sell[j] for each transaction j
- **Optimize for large k**: If k ≥ n/2, use greedy (unlimited)
- **Update backward**: j from k down to 1 (avoid using updated values)
- **Dependencies**: First transaction must complete before second starts

## Interview Walkthrough
1. **Problem**: Generalize stock trading with transaction limit
2. **State definition**:
   - buy[j] = max profit after buying in j-th transaction
   - sell[j] = max profit after selling in j-th transaction
3. **Transitions**:
   - sell[j] = max(hold, buy[j] + price) (sell or hold)
   - buy[j] = max(hold, sell[j-1] - price) (buy or hold)
4. **Ordering**: Update j backward to avoid mixing old/new values
5. **Optimization**: If k ≥ n/2, treat as unlimited (LC 122)

## Why This Approach (Optimal)
- ✅ **O(k) space**: Not O(k·n) array
- ✅ **O(k·n) time**: Necessary for k bounded
- ✅ **Optimization for large k**: Falls back to O(n)
- ✅ **Generalizes**: Works for any k

## Backward Update Pattern (CRITICAL)
```java
// ✅ CORRECT: Update backward to avoid mixing states
for (int j = k; j >= 1; j--) {
    sell[j] = Math.max(sell[j], buy[j] + price);
    buy[j] = Math.max(buy[j], sell[j - 1] - price);
    // sell[j] is new, buy[j] is old, sell[j-1] is old
}

// ❌ WRONG: Update forward causes mixing
for (int j = 1; j <= k; j++) {
    buy[j] = Math.max(buy[j], sell[j - 1] - price);
    sell[j] = Math.max(sell[j], buy[j] + price);
    // buy[j] is new, but sell[j] uses new buy[j]!
}
```

## Common Mistakes
- Not checking if k ≥ n/2 (TLE on large k)
- Updating forward instead of backward
- Not initializing buy[i] = MIN_VALUE (first transaction doesn't use buy[-1])
- Complex 2D DP when 1D suffices

## Tips and Tricks
- "This is generalized stock problem with transaction limit"
- "Key optimization: if k too large, use unlimited greedy"
- "CRITICAL: Update j backward (k down to 1)"
- "State: buy[j] and sell[j] for each transaction j"
- "Backward ensures sell[j-1] is old value (previous transaction)"

## Progression: 1 → 2 → k Transactions
```
LC 121 (k=1):  2 states, simple O(1)
LC 123 (k=2):  4 states, explicit state machine
LC 188 (k):    2k states, array-based generalization
              + optimization for large k
```

## Related Problems
- **LC 121**: Best Time Buy/Sell I (k=1)
- **LC 122**: Best Time Buy/Sell II (unlimited)
- **LC 123**: Best Time Buy/Sell III (k=2, explicit)
- **LC 309**: Best Time Buy/Sell With Cooldown
- **LC 714**: Best Time Buy/Sell With Transaction Fee
