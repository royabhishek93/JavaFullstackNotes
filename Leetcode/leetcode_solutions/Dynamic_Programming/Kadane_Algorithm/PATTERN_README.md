# Kadane's Algorithm / Greedy One-Pass Pattern

## 🎯 When to Use
- "Maximum/minimum subarray/subsequence"
- Single pass optimization
- Previous state affects current decision
- Track current best and global best

## 📝 Master Template (Kadane's Algorithm)

```java
public int kadane(int[] nums) {
    // STEP 1: Initialize tracking variables
    int currentMax = nums[0];  // Best ending at current position
    int globalMax = nums[0];   // Best seen so far
    
    // STEP 2: Iterate from second element
    for (int i = 1; i < nums.length; i++) {
        // STEP 3: Decide: extend current or start fresh
        currentMax = Math.max(nums[i], currentMax + nums[i]);
        
        // STEP 4: Update global maximum
        globalMax = Math.max(globalMax, currentMax);
    }
    
    return globalMax;
}
```

## 🔄 Problem Variations & Modifications

### ✅ LC 53: Maximum Subarray (IMPLEMENTED)
**What changes**: Nothing - this IS the template
**Difficulty**: Medium
```java
public int maxSubArray(int[] nums) {
    int currentMax = nums[0];
    int globalMax = nums[0];
    
    for (int i = 1; i < nums.length; i++) {
        currentMax = Math.max(nums[i], currentMax + nums[i]);
        globalMax = Math.max(globalMax, currentMax);
    }
    
    return globalMax;
}
```
**DP Interpretation**: `dp[i] = max(nums[i], dp[i-1] + nums[i])`

---

### LC 152: Maximum Product Subarray
**What changes**: Track both max and min (for negative numbers)
**Difficulty**: Medium
```java
public int maxProduct(int[] nums) {
    int currentMax = nums[0];
    int currentMin = nums[0];  // Need min because negatives can flip
    int globalMax = nums[0];
    
    for (int i = 1; i < nums.length; i++) {
        int num = nums[i];
        
        // If current number is negative, max and min swap
        if (num < 0) {
            int temp = currentMax;
            currentMax = currentMin;
            currentMin = temp;
        }
        
        // Same logic as LC 53 but for product
        currentMax = Math.max(num, currentMax * num);
        currentMin = Math.min(num, currentMin * num);
        
        globalMax = Math.max(globalMax, currentMax);
    }
    
    return globalMax;
}
```
**Key Changes**:
- Track currentMin (two negatives make positive)
- Swap max/min when encountering negative
- Use multiplication instead of addition

---

## 📊 Pattern Recognition

| Problem | Track | Operation | Special Handling |
|---------|-------|-----------|------------------|
| LC 53 | max | addition | none |
| LC 152 | max + min | multiplication | swap on negative |
| LC 918 | total + max + min | Kadane + circular | return max(normal, total-min) |

## 💡 Key Insights

### Kadane's Logic:
- **At each position**: "Should I extend from previous or start fresh?"
- `current[i] = max(arr[i], current[i-1] + arr[i])`
- If previous sum is negative, start fresh

### For Products:
- Negative number can turn max into min
- Need to swap and recalculate
- Always compare with new num (don't include previous)

## Tips and Tricks

1. **Start with brute force**: "Check all subarrays would be O(n²)..."
2. **Optimize with DP**: "At each position, I only need the best ending here..."
3. **Explain the recurrence**: "dp[i] depends only on dp[i-1]..."
4. **Space optimization**: "Since I only need previous value, I can use O(1) space..."
5. **Edge cases**: All negative, all positive, single element
