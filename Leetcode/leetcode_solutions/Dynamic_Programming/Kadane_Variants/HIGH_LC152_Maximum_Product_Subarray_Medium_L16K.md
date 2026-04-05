# LC 152: Maximum Product Subarray

**Link**: [leetcode.com/problems/maximum-product-subarray](https://leetcode.com/problems/maximum-product-subarray/)

## Problem
Given an integer array nums, find a contiguous subarray which has the largest product. Return the maximum product.

### Examples
- Input: nums = [2,3,-2,4] → Output: 6 (subarray [2,3])
- Input: nums = [-2] → Output: -2
- Input: nums = [0,2] → Output: 2
- Input: nums = [-2, 3, -4] → Output: 24 (entire array)

## Optimized Approach: Track Both Max and Min DP

```java
public int maxProduct(int[] nums) {
    int n = nums.length;
    int maxSoFar = nums[0];
    int maxEndingHere = nums[0];
    int minEndingHere = nums[0];

    for (int i = 1; i < n; i++) {
        // When we multiply by negative, min might become max
        int tempMax = maxEndingHere;
        
        // Current can be: start fresh, extend max, or extend min
        maxEndingHere = Math.max(nums[i], 
                        Math.max(tempMax * nums[i], minEndingHere * nums[i]));
        
        minEndingHere = Math.min(nums[i], 
                        Math.min(tempMax * nums[i], minEndingHere * nums[i]));

        maxSoFar = Math.max(maxSoFar, maxEndingHere);
    }

    return maxSoFar;
}
```

**Time Complexity**: O(n)  
**Space Complexity**: O(1)

## Key Insights
- **Track both max and min**: Negative number flips them
- **Three choices**: Start fresh, extend max, or extend min (↔ becomes max)
- **Negative nums dangerous**: -2 × (-4) = 8 > any positive product
- **Restart anytime**: Don't force accumulation

## Interview Walkthrough
1. **Problem**: Find subarray with maximum product (not sum!)
2. **Difference from LC 53**:
   - Negatives can become positives if multiplied together
   - Must track minEndingHere because it might become max
3. **Algorithm**:
   - At each position: can start fresh OR extend previous
   - When extending: might use maxEndingHere × nums[i] OR minEndingHere × nums[i]
   - Track global max throughout

4. **Example**: [-2, 3, -4]
   ```
   i=0: max=-2, min=-2
   i=1: 
     - 3*1=3, max(-2)=3, (-2*3)=-6, min=-6
     - max=3, min=-6
   i=2:
     - (-6 * -4)=24 ← min becomes max!
     - max=Math.max(3, 24)=24
   ```

## Why This Approach (Optimal)
- ✅ **O(n) time**: Single pass
- ✅ **O(1) space**: Only three variables
- ✅ **Handles negatives**: Tracks both min and max
- ✅ **Works with zeros**: Reset both to current

## Common Mistakes
- Only tracking max, not min
- Not handling negative number multiplication flips
- Comparing values instead of Math.max/Math.min
- Starting loop at 0 instead of 1
- Not saving tempMax before updating

## Tips and Tricks
- "This is like LC 53 Maximum Subarray but multiplication, not sum"
- "CRITICAL: Track minEndingHere because negative × negative = positive"
- "At each step: start fresh, extend max, or extend min"
- "Walk through [-2, 3, -4] showing min becomes max at -4"

## Related Problems
- **LC 53**: Maximum Subarray (sum version, don't need min)
- **LC 189**: Maximum Product Subarray with k changes
- **LC 918**: Maximum Sum Circular Subarray (circular max sum)
