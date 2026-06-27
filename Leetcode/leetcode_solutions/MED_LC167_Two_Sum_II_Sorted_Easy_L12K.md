# LC 167: Two Sum II - Input Array Is Sorted

**Link**: [leetcode.com/problems/two-sum-ii-input-array-is-sorted](https://leetcode.com/problems/two-sum-ii-input-array-is-sorted/)

## Problem
Given a 1-indexed array of integers numbers that is already sorted in non-decreasing order, find two numbers such that they add up to a specific target number. Return the indices of the two numbers as an integer array [index1, index2] where 1 <= index1 < index2 <= numbers.length.

### Examples
- Input: numbers = [2,7,11,15], target = 9 → Output: [1,2]
- Input: numbers = [2,3,4], target = 6 → Output: [1,3]
- Input: numbers = [-1,0], target = -1 → Output: [1,2]

## Optimized Approach: Two Pointers (Sorted Array)

```java
public int[] twoSum(int[] numbers, int target) {
    int left = 0;
    int right = numbers.length - 1;

    while (left < right) {
        int sum = numbers[left] + numbers[right];

        if (sum == target) {
            return new int[]{left + 1, right + 1};  // Convert to 1-indexed
        } else if (sum < target) {
            left++;  // Need larger sum
        } else {
            right--;  // Need smaller sum
        }
    }

    return new int[]{};  // No solution found
}
```

**Time Complexity**: O(n)  
**Space Complexity**: O(1)

## Key Insights
- **Two Pointers Pattern**: Left starts at beginning, right at end
- **Sorted Advantage**: Can make intelligent pointer movements
- **Sum < target**: Move left pointer right (increase sum)
- **Sum > target**: Move right pointer left (decrease sum)
- **1-Indexed Output**: Convert 0-indexed positions to 1-indexed (add 1)

## Interview Walkthrough
1. **Problem**: Find two indices with sum = target (input is SORTED)
2. **Key Advantage**: Because sorted, left pointer < right pointer always
3. **Algorithm**:
   - Start: left at 0, right at end
   - Calculate sum = numbers[left] + numbers[right]
   - If sum == target: return indices (convert to 1-indexed)
   - If sum < target: left++ (need bigger sum, move left pointer right)
   - If sum > target: right-- (need smaller sum, move right pointer left)
4. **Why it works**: 
   - If sum too small, moving left right gives us a larger number
   - If sum too large, moving right left gives us a smaller number
5. **Example**: numbers=[2,7,11,15], target=9
   - left=0 (nums[0]=2), right=3 (nums[3]=15)
   - sum=17 > 9 → right--
   - left=0, right=2: sum=13 > 9 → right--
   - left=0, right=1: sum=9 == 9 → return [1, 2]

## Why Two Pointers (Better than HashMap)
- ✅ **O(1) space**: No HashMap needed
- ✅ **O(n) time**: Single pass needed
- ✅ **Sorted input advantage**: Natural for two-pointer approach
- ⚠️ **Requires sorted input**: Cannot be used on unsorted array

## Comparison with LC 1 (Two Sum)
| Aspect | LC 1 (Unsorted) | LC 167 (Sorted) |
|--------|-----------------|-----------------|
| Input | Unsorted | Sorted |
| Approach | HashMap | Two Pointers |
| Time | O(n) | O(n) |
| Space | O(n) | O(1) |
| Preserves Index | ✅ | ❌ |
| Elegant | Medium | Better |

## Common Mistakes
- Forgetting to convert to 1-indexed output (add 1 to indices)
- Using wrong pointer movement (left++ when should be right--)
- Not handling the case where no solution exists
- Comparing indices incorrectly (should be left < right, not <=)

## Tips and Tricks
- "Since input is sorted, I can use two pointers instead of HashMap"
- "Move left pointer right when sum is too small"
- "Move right pointer left when sum is too large"
- "This uses O(1) space and O(n) time"
- "Output must be 1-indexed per the problem statement"

## Related Problems
- **LC 1**: Two Sum (unsorted, HashMap approach)
- **LC 15**: 3Sum (extend two pointers with outer loop)
- **LC 18**: 4Sum (similar to 3Sum with another outer loop)
- **LC 16**: 3Sum Closest (track closest instead of exact match)
