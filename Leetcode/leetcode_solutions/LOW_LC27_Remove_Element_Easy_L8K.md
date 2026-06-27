# LC 27: Remove Element

**Link**: [leetcode.com/problems/remove-element](https://leetcode.com/problems/remove-element/)

## Problem
Remove all occurrences of `val` in-place and return the new length.

## Optimized Approach: Two Pointers

```java
public int removeElement(int[] nums, int val) {
    int write = 0;

    for (int read = 0; read < nums.length; read++) {
        if (nums[read] != val) {
            nums[write++] = nums[read];
        }
    }

    return write;
}
```

**Time Complexity**: O(n)  
**Space Complexity**: O(1)

## Key Insights
- Keep non-target values at front
- Order can be preserved with read/write pointers

## Tips and Tricks
- State what each pointer represents and how movement changes the invariant.
- If the array is sorted, use pointer movement to eliminate search space instead of nested loops.
- Handle duplicates explicitly when the problem asks for unique answers.

## Related Problems
- LC 26 Remove Duplicates from Sorted Array
