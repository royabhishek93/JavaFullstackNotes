# LC 80: Remove Duplicates from Sorted Array II

**Link**: [leetcode.com/problems/remove-duplicates-from-sorted-array-ii](https://leetcode.com/problems/remove-duplicates-from-sorted-array-ii/)

## Problem
Given a sorted array, remove duplicates in-place such that each unique element appears at most twice.

## Optimized Approach: Two Pointers (Allow 2 Copies)

```java
public int removeDuplicates(int[] nums) {
    if (nums.length <= 2) return nums.length;

    int write = 2;
    for (int read = 2; read < nums.length; read++) {
        // Keep nums[read] only if it differs from value 2 places behind write
        if (nums[read] != nums[write - 2]) {
            nums[write++] = nums[read];
        }
    }

    return write;
}
```

**Time Complexity**: O(n)  
**Space Complexity**: O(1)

## Key Insights
- Keep first 2 elements always
- For next elements, compare with `write-2` position

## Tips and Tricks
- State what each pointer represents and how movement changes the invariant.
- If the array is sorted, use pointer movement to eliminate search space instead of nested loops.
- Handle duplicates explicitly when the problem asks for unique answers.

## Related Problems
- LC 26 Remove Duplicates from Sorted Array
