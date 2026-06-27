# LC 283: Move Zeroes

**Link**: [leetcode.com/problems/move-zeroes](https://leetcode.com/problems/move-zeroes/)

## Problem
Given an integer array `nums`, move all `0`s to the end while maintaining the relative order of non-zero elements. Do it in-place.

## Optimized Approach: Two Pointers (Snowball)

```java
public void moveZeroes(int[] nums) {
    int write = 0;

    for (int read = 0; read < nums.length; read++) {
        if (nums[read] != 0) {
            nums[write++] = nums[read];
        }
    }

    while (write < nums.length) {
        nums[write++] = 0;
    }
}
```

**Time Complexity**: O(n)  
**Space Complexity**: O(1)

## Key Insights
- Compact all non-zeros to the front using write pointer
- Fill remaining positions with zeros

## Tips and Tricks
- State what each pointer represents and how movement changes the invariant.
- If the array is sorted, use pointer movement to eliminate search space instead of nested loops.
- Handle duplicates explicitly when the problem asks for unique answers.

## Related Problems
- LC 27 Remove Element
- LC 26 Remove Duplicates from Sorted Array
