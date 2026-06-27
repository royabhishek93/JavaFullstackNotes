# LC 41: First Missing Positive

**Link**: [leetcode.com/problems/first-missing-positive](https://leetcode.com/problems/first-missing-positive/)

## Problem
Given an unsorted integer array `nums`, return the smallest missing positive integer. Must run in O(n) time and O(1) space.

## Optimized Approach: Cyclic Sort (Index as Hash)

```java
public int firstMissingPositive(int[] nums) {
    int n = nums.length;

    // Place each positive number i at index i-1
    for (int i = 0; i < n; i++) {
        while (nums[i] > 0 && nums[i] <= n && nums[nums[i] - 1] != nums[i]) {
            int dest = nums[i] - 1;
            int tmp = nums[dest];
            nums[dest] = nums[i];
            nums[i] = tmp;
        }
    }

    // Find first position where nums[i] != i+1
    for (int i = 0; i < n; i++) {
        if (nums[i] != i + 1) return i + 1;
    }

    return n + 1;
}
```

**Time Complexity**: O(n)  
**Space Complexity**: O(1)

## Key Insights
- Key insight: answer must be in range `[1, n+1]`
- Use array as in-place hash map: place value `v` at index `v-1`
- After rearranging, first `i` where `nums[i] != i+1` gives the answer

## Trace Example
```
nums = [3, 4, -1, 1]

After cyclic sort: [1, -1, 3, 4]
Scan: nums[0]=1 ✓, nums[1]=-1 ≠ 2 → return 2
```

## Common Mistakes
- Trying O(n) sort first (misses O(1) space requirement)
- Forgetting to handle duplicates in while condition

## Tips and Tricks
- This pattern works when values naturally belong to indices in a fixed range.
- Only swap when the destination index is valid and does not already hold the same value.
- Duplicates are where most infinite loops happen, so guard that condition explicitly.

## Related Problems
- LC 268 Missing Number
- LC 287 Find the Duplicate Number
