# LC 42: Trapping Rain Water

**Link**: [leetcode.com/problems/trapping-rain-water](https://leetcode.com/problems/trapping-rain-water/)

## Problem
Given `n` non-negative integers representing elevation map, compute how much water it can trap after raining.

## Optimized Approach: Two Pointers with Running Max

```java
public int trap(int[] height) {
    int left = 0, right = height.length - 1;
    int leftMax = 0, rightMax = 0;
    int water = 0;

    while (left < right) {
        if (height[left] < height[right]) {
            if (height[left] >= leftMax) leftMax = height[left];
            else water += leftMax - height[left];
            left++;
        } else {
            if (height[right] >= rightMax) rightMax = height[right];
            else water += rightMax - height[right];
            right--;
        }
    }

    return water;
}
```

**Time Complexity**: O(n)  
**Space Complexity**: O(1)

## Key Insights
- Water at index depends on min(maxLeft, maxRight)
- Move smaller side pointer and resolve deterministically

## Tips and Tricks
- State what each pointer represents and how movement changes the invariant.
- If the array is sorted, use pointer movement to eliminate search space instead of nested loops.
- Handle duplicates explicitly when the problem asks for unique answers.

## Related Problems
- LC 11 Container With Most Water
