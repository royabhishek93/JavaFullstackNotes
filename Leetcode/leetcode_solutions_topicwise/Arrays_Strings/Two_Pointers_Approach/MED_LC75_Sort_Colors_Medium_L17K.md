# LC 75: Sort Colors

**Link**: [leetcode.com/problems/sort-colors](https://leetcode.com/problems/sort-colors/)

## Problem
Given an array with values `0`, `1`, and `2`, sort it in-place without built-in sort.

## Optimized Approach: Dutch National Flag

```java
public void sortColors(int[] nums) {
    int low = 0, mid = 0, high = nums.length - 1;

    while (mid <= high) {
        if (nums[mid] == 0) {
            swap(nums, low++, mid++);
        } else if (nums[mid] == 1) {
            mid++;
        } else {
            swap(nums, mid, high--);
        }
    }
}

private void swap(int[] nums, int i, int j) {
    int t = nums[i];
    nums[i] = nums[j];
    nums[j] = t;
}
```

**Time Complexity**: O(n)  
**Space Complexity**: O(1)

## Key Insights
- Maintain partitions: `[0..low-1]=0`, `[low..mid-1]=1`, `[high+1..end]=2`
- When swapping with `high`, do not advance `mid` immediately

## Tips and Tricks
- State what each pointer represents and how movement changes the invariant.
- If the array is sorted, use pointer movement to eliminate search space instead of nested loops.
- Handle duplicates explicitly when the problem asks for unique answers.

## Related Problems
- LC 26 Remove Duplicates from Sorted Array
