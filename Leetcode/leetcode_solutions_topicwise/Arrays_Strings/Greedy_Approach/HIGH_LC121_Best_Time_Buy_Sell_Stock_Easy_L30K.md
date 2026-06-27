# LC 121: Best Time to Buy and Sell Stock

**Link**: [leetcode.com/problems/best-time-to-buy-and-sell-stock](https://leetcode.com/problems/best-time-to-buy-and-sell-stock/)

## Problem
You are given an array prices where prices[i] is the price of a given stock on the ith day. You want to maximize your profit by choosing a single day to buy one stock and choosing a different day in the future to sell that stock. Return the maximum profit you can achieve. If you cannot achieve any profit, return 0.

### Examples
- Input: prices = [7,1,5,3,6,4] → Output: 5 (buy at 1, sell at 6)
- Input: prices = [7,6,4,3,1] → Output: 0 (no profit possible)

## Optimized Approach: Greedy One-Pass

```java
public int maxProfit(int[] prices) {
    if (prices == null || prices.length < 2) {
        return 0;
    }

    int minPrice = prices[0];
    int maxProfit = 0;

    for (int i = 1; i < prices.length; i++) {
        int profit = prices[i] - minPrice;
        maxProfit = Math.max(maxProfit, profit);
        minPrice = Math.min(minPrice, prices[i]);
    }

    return maxProfit;
}
```

**Time Complexity**: O(n)  
**Space Complexity**: O(1)

## Key Insights
- **Greedy Choice**: Track minimum price seen so far
- **Profit Calculation**: profit = current price - minimum price seen before today
- **Local Optimal = Global Optimal**: Greedy works because we always want lowest buy price for any sell price
- **Prevent Negative Profit**: Start with 0, never go below 0

## Interview Walkthrough
1. **Problem**: Maximize profit by buying once and selling once (sell after buy)
2. **Brute Force**: "Check all pairs O(n²)..."
3. **Optimization**: "For each day as sell day, what's the best buy price? The minimum before it!"
4. **Algorithm**: 
   - Track minimum price as we iterate
   - For each price, calculate profit if we sold at this price
   - Track maximum profit seen
5. **Why Greedy Works**: 
   - For any sell day, the best buy is the minimum price before it
   - We only need one pass to find both min and max profit
6. **Example**: [7, 1, 5, 3, 6, 4]
   - i=1: min=1, profit=0
   - i=2: min=1, profit=4
   - i=3: min=1, profit=2
   - i=4: min=1, profit=5 ← max
   - i=5: min=1, profit=3

## Common Mistakes
- Using two loops (naive two-pointer approach) → O(n²)
- Updating maxProfit before updating minPrice → incorrect calculations
- Not handling negative profit by starting with 0
- Using simple variable assignments instead of Math.min/max

## Tips and Tricks
- State the core invariant before coding so the implementation follows the idea directly.
- Test the smallest edge cases first because they expose most off-by-one bugs.
- When explaining in interviews, lead with the optimized idea and then justify complexity clearly.
