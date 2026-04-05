# LC 26: Remove Duplicates from Sorted Array

**Link**: [leetcode.com/problems/remove-duplicates-from-sorted-array](https://leetcode.com/problems/remove-duplicates-from-sorted-array/)

## Problem
Given an integer array `nums` sorted in non-decreasing order, remove duplicates in-place and return the number of unique elements.

## Optimized Approach: Two Pointers (Read/Write)

```java
public int removeDuplicates(int[] nums) {
    if (nums.length == 0) return 0;

    int write = 1;
    for (int read = 1; read < nums.length; read++) {
        if (nums[read] != nums[read - 1]) {
            nums[write] = nums[read];
            write++;
        }
    }

    return write;
}
```

**Time Complexity**: O(n)  
**Space Complexity**: O(1)

## Key Insights
- Sorted property makes duplicate detection local
- `write` keeps compact unique prefix

## Tips and Tricks
- State what each pointer represents and how movement changes the invariant.
- If the array is sorted, use pointer movement to eliminate search space instead of nested loops.
- Handle duplicates explicitly when the problem asks for unique answers.

## Related Problems
- LC 80 Remove Duplicates from Sorted Array II
- LC 27 Remove Element
