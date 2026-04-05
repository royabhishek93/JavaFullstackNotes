# LC 209: Minimum Size Subarray Sum

**Link**: [leetcode.com/problems/minimum-size-subarray-sum](https://leetcode.com/problems/minimum-size-subarray-sum/)

## Problem
Given an array of positive integers nums and a positive integer target, return the minimal length of a contiguous subarray whose sum is greater than or equal to target. If there is no such subarray, return 0.

### Examples
- Input: target = 7, nums = [2,3,1,2,4,3] → Output: 2 (subarray [4,3])
- Input: target = 4, nums = [1,4,1,1,1,1,1,1,1,1] → Output: 1 (subarray [4])
- Input: target = 11, nums = [1,1,1,1,1,1,1,1] → Output: 0

## Optimized Approach: Sliding Window with Sum

```java
public int minSubArrayLen(int target, int[] nums) {
    int left = 0;
    int sum = 0;
    int minLen = Integer.MAX_VALUE;

    for (int right = 0; right < nums.length; right++) {
        // Expand window: add right element
        sum += nums[right];

        // Shrink window while sum >= target
        // Try to minimize window length
        while (sum >= target) {
            // Update result with current window length
            minLen = Math.min(minLen, right - left + 1);

            // Remove left element and move left pointer
            sum -= nums[left];
            left++;
        }
    }

    // Return 0 if no valid subarray found
    return minLen == Integer.MAX_VALUE ? 0 : minLen;
}
```

**Time Complexity**: O(n) - each element visited at most twice  
**Space Complexity**: O(1) - only tracking sum and pointers

## Key Insights
- **No HashMap needed**: Only track running sum (simpler than LC 76)
- **Expand then shrink**: Add right, then shrink left when sum >= target
- **Minimize length**: Update minLen inside shrink loop
- **Positive integers**: Allows shrinking logic (sum never uncontrollable)

## Interview Walkthrough
1. **Problem**: Find shortest contiguous subarray with sum >= target
2. **Sliding Window Strategy**: 
   - Expand right to accumulate sum
   - When sum sufficient, shrink left to minimize length
3. **Algorithm**:
   - Add element at right pointer
   - While sum >= target:
     - Update min length
     - Remove element from left pointer
   - Continue expanding right
4. **Why different from LC 76?**: 
   - No complex frequency matching needed
   - Just numeric comparison (sum >= target)
   - Shrinking always makes sum smaller

## Why This Approach (Optimal)
- ✅ **O(n) time**: Two pointers each visit array once
- ✅ **O(1) space**: No extra data structures
- ✅ **Simple logic**: Just track sum, no HashMap needed

## Common Mistakes
- Shrinking before checking condition → miss some subarrays
- Not resetting minLen → returns wrong value
- Using <= instead of >= for target comparison
- Off-by-one in length calculation (should be right - left + 1)
- Forgetting to return 0 when no valid subarray

## Tips and Tricks
- "Expand right to increase sum, shrink left to minimize length"
- "While sum is sufficient, keep shrinking to find minimum"
- "Each element processed at most twice (right, then left)"
- "This is simpler than minimum window substring (no HashMap needed)"
- "Key insight: we WANT to shrink (minimize), not avoid shrinking"

## Comparison with Similar Problems
| Problem | Type | Data Structure | Condition |
|---------|------|-----------------|-----------|
| LC 3 | Maximum length | HashMap | No duplicates |
| LC 209 | Minimum length | Just sum | Sum >= target |
| LC 76 | Minimum length | 2 HashMaps | Contains all chars |

## Related Problems
- **LC 76**: Minimum Window Substring (similar but with characters)
- **LC 3**: Longest Substring Without Repeating (maximize, use HashMap)
- **LC 438**: Find All Anagrams (fixed window)
- **LC 325**: Maximum Size Subarray Sum Equals K (exact sum)
