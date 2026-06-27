# LC 287: Find the Duplicate Number

**Link**: [leetcode.com/problems/find-the-duplicate-number](https://leetcode.com/problems/find-the-duplicate-number/)

## Problem
Given an array `nums` of `n + 1` integers where each value is in `[1, n]`, exactly one number is duplicated. Find it without modifying the array, using O(1) extra space.

## Optimized Approach: Floyd's Cycle Detection

```java
public int findDuplicate(int[] nums) {
    // Phase 1: find intersection point
    int slow = nums[0];
    int fast = nums[0];

    do {
        slow = nums[slow];
        fast = nums[nums[fast]];
    } while (slow != fast);

    // Phase 2: find cycle entry (duplicate)
    slow = nums[0];
    while (slow != fast) {
        slow = nums[slow];
        fast = nums[fast];
    }

    return slow;
}
```

**Time Complexity**: O(n)  
**Space Complexity**: O(1)

## Key Insights
- Treat `nums[i]` as a pointer: index → value link forms a cycle
- Duplicate value = cycle entry point (same as LC 142)

## Tips and Tricks
- State the core invariant before coding so the implementation follows the idea directly.
- Test the smallest edge cases first because they expose most off-by-one bugs.
- When explaining in interviews, lead with the optimized idea and then justify complexity clearly.

## Related Problems
- LC 141 Linked List Cycle
- LC 142 Linked List Cycle II
