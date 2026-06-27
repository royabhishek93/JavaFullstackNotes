# LC 918: Maximum Sum Circular Subarray

**Link**: [leetcode.com/problems/maximum-sum-circular-subarray](https://leetcode.com/problems/maximum-sum-circular-subarray/)

## Problem
Given a circular integer array nums of length n, return the maximum sum of a subarray in this array. A circular subarray may start and end at any index in the array and the subarray may wrap around the end of the array. An empty subarray is not valid, so you need at least one number from the array.

### Examples
- Input: nums = [1,-2,3,-2] → Output: 3 (subarray [3])
- Input: nums = [5,-3,5] → Output: 10 (subarray [5,5] wrapping around)
- Input: nums = [-2,-1,-3] → Output: -1 (subarray [-1])

## Optimized Approach: Kadane + Circular Logic

```java
public int maxSubarraySumCircular(int[] nums) {
    // Case 1: Max subarray does NOT wrap (use Kadane's)
    int kadaneMax = kadaneMax(nums);

    // Case 2: Max subarray DOES wrap
    // = total - minSubarray
    int total = 0;
    for (int num : nums) {
        total += num;
    }
    
    // Invert signs to find minimum subarray
    for (int i = 0; i < nums.length; i++) {
        nums[i] = -nums[i];
    }
    int minSubarray = -kadaneMax(nums);  // Negate back
    
    // Revert for safety
    for (int i = 0; i < nums.length; i++) {
        nums[i] = -nums[i];
    }

    // If minSubarray == total, entire array is min, return kadaneMax
    if (minSubarray == total) {
        return kadaneMax;
    }

    // Answer is max of non-wrapped and wrapped cases
    return Math.max(kadaneMax, total - minSubarray);
}

private int kadaneMax(int[] nums) {
    int maxSoFar = nums[0];
    int maxEndingHere = nums[0];

    for (int i = 1; i < nums.length; i++) {
        maxEndingHere = Math.max(nums[i], maxEndingHere + nums[i]);
        maxSoFar = Math.max(maxSoFar, maxEndingHere);
    }

    return maxSoFar;
}
```

**Time Complexity**: O(n) - 3 passes through array  
**Space Complexity**: O(1) - modify array in-place or use separate logic

## Key Insights
- **Two cases**: Max wraps around OR doesn't wrap
- **Non-wrapped**: Standard Kadane's algorithm
- **Wrapped case**: total - (minimum subarray)
- **Edge case**: If min subarray == total, all elements are min, return kadane

## Interview Walkthrough
1. **Problem**: Circular array means you can wrap around [... end | start ...]
2. **Two possibilities**:
   - Maximum doesn't wrap: Use Kadane's (LC 53)
   - Maximum wraps: middle section is minimum
3. **If max wraps**:
   - Max_circular = Total - Min_subarray
   - So find minimum subarray (negative Kadane)
4. **Example**: [5, -3, 5]
   ```
   Case 1 (no wrap): max([5], [-3], [5]) = 5
   Case 2 (wrap): [5,5] = total_10 - min_[-3] = 10
   Answer: max(5, 10) = 10
   ```

## Why This Approach (Optimal)
- ✅ **O(n) time**: 3 linear passes
- ✅ **O(1) space**: Apart from modifying array (reversible)
- ✅ **Insight-based**: Circular = total - minimum subarray
- ✅ **Generalizes Kadane**: Uses standard algorithm

## Critical Edge Case
```java
// ❌ TRAP: If minSubarray == total, entire array is minimum
if (minSubarray == total) {
    return kadaneMax;
}
// Why? Because circular case would be:
// total - total = 0, but we need at least one element
// So return the regular Kadane (at least one element guaranteed)
```

## Common Mistakes
- Forgetting circular case (just using Kadane)
- Not handling edge case where all elements are minimum
- Wrong formula: max_wrap should be total - min_wrap, not total - max_wrap
- Modifying array without reverting (though not critical)

## Tips and Tricks
- "Circular array = two cases: wrap or non-wrap"
- "Non-wrap is standard Kadane (LC 53)"
- "Wrap = total - minimum subarray (use negative Kadane)"
- "Critical: If min_subarray == total, use non-wrap result"
- "Walk through [5,-3,5] showing wrap case = 10"

## Comparison: Kadane Variants
```
LC 53:   Maximum Subarray (non-circular)
LC 152:  Maximum Product Subarray (track max/min)
LC 918:  Maximum Sum Circular (two cases)
```

## Related Problems
- **LC 53**: Maximum Subarray (non-circular foundation)
- **LC 152**: Maximum Product Subarray (track two values)
- **LC 560**: Subarray Sum Equals K (different goal)
- **LC 209**: Minimum Size Subarray Sum (sliding window)
