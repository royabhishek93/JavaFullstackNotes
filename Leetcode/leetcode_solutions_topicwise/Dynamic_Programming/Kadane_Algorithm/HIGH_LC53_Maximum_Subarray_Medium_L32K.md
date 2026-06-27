# LC 53: Maximum Subarray (Kadane's Algorithm)

**Link**: [leetcode.com/problems/maximum-subarray](https://leetcode.com/problems/maximum-subarray/)

## Problem
Given an integer array nums, find the subarray with the largest sum, and return its sum.

### Examples
- Input: nums = [-2,1,-3,4,-1,2,1,-5,4] → Output: 6 (subarray [4,-1,2,1])
- Input: nums = [1] → Output: 1
- Input: nums = [5,4,-1,7,8] → Output: 23

## Optimized Approach: Kadane's Algorithm

```java
public int maxSubArray(int[] nums) {
    if (nums == null || nums.length == 0) {
        return 0;
    }

    int maxSum = nums[0];        // Global maximum subarray sum
    int currentSum = nums[0];    // Maximum subarray sum ending at current position

    for (int i = 1; i < nums.length; i++) {
        // Decide: extend previous subarray or start fresh from current element
        currentSum = Math.max(nums[i], currentSum + nums[i]);
        // Update global maximum
        maxSum = Math.max(maxSum, currentSum);
    }

    return maxSum;
}
```

**Time Complexity**: O(n)  
**Space Complexity**: O(1)

## Key Insights
- **DP Definition**: currentSum = max subarray sum ENDING at current position
- **Recurrence**: currentSum = max(nums[i], currentSum + nums[i])
  - Start fresh if current element alone is better
  - Extend previous if including previous yields better result
- **Track Global Max**: Update maxSum at each step
- **No Extra Space**: Only track two variables (currentSum, maxSum)

## Interview Walkthrough
1. **Problem**: Find contiguous subarray with largest sum
2. **Brute Force**: "All subarrays → O(n²) or O(n³)..."
3. **Key Insight**: "At each position, we ONLY need to know: what's the best sum ending at previous position?"
4. **DP State**: 
   - currentSum = best subarray sum ending at index i
   - maxSum = best sum seen so far globally
5. **Decision Logic**:
   - If nums[i] > currentSum + nums[i]: start fresh from nums[i]
   - Otherwise: extend by adding nums[i] to previous sum
6. **Example**: [-2, 1, -3, 4, -1, 2, 1, -5, 4]
   - i=0: currentSum=-2, maxSum=-2
   - i=1: currentSum=max(1, -2+1)=1, maxSum=1
   - i=2: currentSum=max(-3, 1-3)=-2, maxSum=1
   - i=3: currentSum=max(4, -2+4)=4, maxSum=4
   - i=4: currentSum=max(-1, 4-1)=3, maxSum=4
   - i=5: currentSum=max(2, 3+2)=5, maxSum=5
   - i=6: currentSum=max(1, 5+1)=6, maxSum=6 ← answer

## Common Mistakes
- Comparing currentSum with nums[i] incorrectly
- Forgetting to update maxSum at each iteration
- Not using Math.max (manual if-else) → harder to debug
- Initializing currentSum or maxSum incorrectly (should both start at nums[0])

## Tips and Tricks
- "This is classic dynamic programming with space optimization"
- "We track 'best sum ending at current position' and update global max"
- "The beauty is we only need O(1) space instead of O(n) DP array"
- "Walk through with [-2, 1, -3, 4, -1, 2, 1, -5, 4] step by step"
