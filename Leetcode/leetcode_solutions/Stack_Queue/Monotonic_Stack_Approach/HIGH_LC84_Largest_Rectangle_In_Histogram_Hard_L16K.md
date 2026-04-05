# LC 84: Largest Rectangle in Histogram

**Link**: [leetcode.com/problems/largest-rectangle-in-histogram](https://leetcode.com/problems/largest-rectangle-in-histogram/)

## Problem
Given heights of bars in histogram, return area of largest rectangle.

## Optimized Approach: Monotonic Increasing Stack

```java
public int largestRectangleArea(int[] heights) {
    Deque<Integer> stack = new ArrayDeque<>();
    int maxArea = 0;

    for (int i = 0; i <= heights.length; i++) {
        int h = (i == heights.length) ? 0 : heights[i];

        while (!stack.isEmpty() && heights[stack.peek()] > h) {
            int height = heights[stack.pop()];
            int right = i;
            int left = stack.isEmpty() ? -1 : stack.peek();
            int width = right - left - 1;
            maxArea = Math.max(maxArea, height * width);
        }

        stack.push(i);
    }

    return maxArea;
}
```

**Time Complexity**: O(n)  
**Space Complexity**: O(n)

## Tips and Tricks
- Ask what the stack or queue is storing: values, indices, or states.
- Monotonic structures are about preserving an ordering invariant after every push.
- If boundaries matter, storing indices is usually safer than storing raw values.

## Related Problems
- LC 85 Maximal Rectangle
