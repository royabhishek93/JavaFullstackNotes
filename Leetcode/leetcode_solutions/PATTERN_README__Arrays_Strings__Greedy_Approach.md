# Greedy Approach: Single-Pass Optimization Pattern

## 🎯 When to Use
- "Maximum/minimum" problems (single transaction)
- Single pass solution possible
- Previous state affects current decision
- Track one or two key variables

## 📝 Master Template

```java
public int greedyOnePass(int[] nums) {
    // STEP 1: Initialize tracking variables
    int minValue = nums[0];  // Key state to track
    int result = 0;          // Result to optimize
    
    // STEP 2: Iterate through array
    for (int i = 1; i < nums.length; i++) {
        // STEP 3: Calculate result based on current value
        result = Math.max(result, nums[i] - minValue);
        
        // STEP 4: Update tracked state
        minValue = Math.min(minValue, nums[i]);
    }
    
    return result;
}
```

## 🔄 Problem Variations & Modifications

### ✅ LC 121: Best Time to Buy and Sell Stock (IMPLEMENTED)
**What changes**: Track minimum price, calculate profit
**Difficulty**: Easy
```java
public int maxProfit(int[] prices) {
    int minPrice = prices[0];
    int maxProfit = 0;
    
    for (int i = 1; i < prices.length; i++) {
        // Update profit if selling today
        maxProfit = Math.max(maxProfit, prices[i] - minPrice);
        
        // Update minimum price seen so far
        minPrice = Math.min(minPrice, prices[i]);
    }
    
    return maxProfit;
}
```
**Key Changes**:
- Track min instead of sum
- Calculate profit as difference
- Can't have negative profit (start with 0)

---

### LC 122: Best Time to Buy and Sell Stock II (Multiple Transactions)
**What changes**: Sum all positive differences
**Difficulty**: Medium
```java
public int maxProfit(int[] prices) {
    int totalProfit = 0;
    
    for (int i = 1; i < prices.length; i++) {
        // Add profit whenever price increases
        if (prices[i] > prices[i-1]) {
            totalProfit += prices[i] - prices[i-1];
        }
    }
    
    return totalProfit;
}
```
**Key Change**: Sum all increases (unlimited transactions)

---

## 💡 Key Insights

### Greedy vs Dynamic Programming:
- **Greedy**: Local optimum at each step = global optimum
- **DP**: Need to track multiple states
- Stock problems can use both approaches

### Common Pitfalls:
1. ❌ Not initializing with first element
2. ❌ Allowing negative profits
3. ❌ Updating state before using it

## Tips and Tricks

1. **Greedy is faster**: O(1) space, single pass
2. **Always verify correctness**: Is local optimum global?
3. **Discuss with interviewer**: "Can I use a greedy approach here?"
4. **Compare with DP**: "DP would be more flexible if constraints change..."
