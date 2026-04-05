# LC 1: Two Sum

**Link**: [leetcode.com/problems/two-sum](https://leetcode.com/problems/two-sum/)

## Problem
Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target. You may assume that each input would have exactly one solution, and you may not use the same element twice.

### Examples
- Input: nums = [2,7,11,15], target = 9 → Output: [0,1]
- Input: nums = [3,2,4], target = 6 → Output: [1,2]
- Input: nums = [3,3], target = 6 → Output: [0,1]

## Optimized Approach: HashMap - One Pass

```java
public int[] twoSum(int[] nums, int target) {
    Map<Integer, Integer> numToIndex = new HashMap<>();

    for (int i = 0; i < nums.length; i++) {
        int complement = target - nums[i];

        if (numToIndex.containsKey(complement)) {
            return new int[]{numToIndex.get(complement), i};
        }

        numToIndex.put(nums[i], i);
    }

    return new int[]{};
}
```

**Time Complexity**: O(n)  
**Space Complexity**: O(n)

## Key Insights
- **One Pass HashMap**: Check for complement while building map
- **Add After Checking**: Prevent using same element twice
- **Preserve Indices**: HashMap preserves original indices (crucial for solution)
- **Key Logic**: For each num, check if (target - num) exists in map

## Interview Walkthrough
1. **Clarify Problem**: Find TWO indices where nums[i] + nums[j] == target
2. **Brute Force First**: "We could check all pairs O(n²), but let's optimize..."
3. **Optimization Insight**: "Instead of finding num2, we SEARCH for it in constant time"
4. **Algorithm**: For each element, check if its complement exists in previously seen numbers
5. **Why it works**: HashMap lookup is O(1), so one pass is sufficient
6. **Edge Cases**: Duplicates (different indices), negative numbers, single pair guarantee

## Common Mistakes
- Adding element to map BEFORE checking complement → duplicates
- Using `nums[j]` instead of `complement` in containsKey
- Forgetting that indices must be different (handled by one-pass)

## Tips and Tricks
- Use hashing when constant-time membership or frequency lookup matters more than order.
- Be explicit about what the key represents: value, index relation, or prefix state.
- Frequency maps and prefix maps solve many array problems that look quadratic at first.
