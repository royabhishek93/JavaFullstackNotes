# LC 11: Container With Most Water

**Link**: [leetcode.com/problems/container-with-most-water](https://leetcode.com/problems/container-with-most-water/)

## Problem
Given an integer array `height`, return the maximum area of water a container can store.

## Optimized Approach: Two Pointers

```java
public int maxArea(int[] height) {
    int left = 0, right = height.length - 1;
    int max = 0;

    while (left < right) {
        int h = Math.min(height[left], height[right]);
        int width = right - left;
        max = Math.max(max, h * width);

        // Move the smaller wall; only that can potentially improve area
        if (height[left] < height[right]) {
            left++;
        } else {
            right--;
        }
    }

    return max;
}
```

**Time Complexity**: O(n)  
**Space Complexity**: O(1)

## Key Insights
- Area = `min(leftHeight, rightHeight) * width`
- Width shrinks each step, so we must try to increase limiting height
- Moving taller pointer cannot improve current limiting height

## Common Mistakes
- Using brute force O(n^2)
- Moving both pointers every iteration

## Tips and Tricks
- State what each pointer represents and how movement changes the invariant.
- If the array is sorted, use pointer movement to eliminate search space instead of nested loops.
- Handle duplicates explicitly when the problem asks for unique answers.

## Related Problems
- LC 42 Trapping Rain Water
- LC 167 Two Sum II
