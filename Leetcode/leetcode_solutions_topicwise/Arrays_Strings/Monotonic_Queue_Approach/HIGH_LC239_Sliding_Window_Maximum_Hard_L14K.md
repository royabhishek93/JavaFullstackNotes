# LC 239: Sliding Window Maximum

**Link**: [leetcode.com/problems/sliding-window-maximum](https://leetcode.com/problems/sliding-window-maximum/)

## Problem
Given an integer array `nums` and a sliding window of size `k`, return the maximum value in each window position.

## Optimized Approach: Monotonic Deque

```java
public int[] maxSlidingWindow(int[] nums, int k) {
    int n = nums.length;
    int[] result = new int[n - k + 1];
    Deque<Integer> deque = new ArrayDeque<>(); // stores indices

    for (int i = 0; i < n; i++) {
        // Remove indices outside window
        while (!deque.isEmpty() && deque.peekFirst() < i - k + 1) {
            deque.pollFirst();
        }

        // Maintain decreasing order: remove smaller elements
        while (!deque.isEmpty() && nums[deque.peekLast()] < nums[i]) {
            deque.pollLast();
        }

        deque.offerLast(i);

        if (i >= k - 1) {
            result[i - k + 1] = nums[deque.peekFirst()];
        }
    }

    return result;
}
```

**Time Complexity**: O(n)  
**Space Complexity**: O(k)

## Key Insights
- Deque front is always the index of current window maximum
- Expire front when out of window; evict back when smaller than incoming

## Tips and Tricks
- Keep the deque monotonic by removing weaker candidates from the back.
- Drop indices from the front when they fall out of the current window.
- Store indices, not values, so you can handle expiry correctly.

## Related Problems
- LC 84 Largest Rectangle in Histogram
