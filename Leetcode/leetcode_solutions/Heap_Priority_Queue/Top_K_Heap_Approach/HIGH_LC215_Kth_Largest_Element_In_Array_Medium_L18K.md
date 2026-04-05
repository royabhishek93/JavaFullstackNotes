# LC 215: Kth Largest Element in an Array

**Link**: [leetcode.com/problems/kth-largest-element-in-an-array](https://leetcode.com/problems/kth-largest-element-in-an-array/)

## Problem
Given an integer array `nums` and an integer `k`, return the `k`th largest element in the array.

## Optimized Approach: Min Heap of Size k

```java
public int findKthLargest(int[] nums, int k) {
    PriorityQueue<Integer> minHeap = new PriorityQueue<>();

    for (int num : nums) {
        minHeap.offer(num);
        if (minHeap.size() > k) {
            minHeap.poll();
        }
    }

    return minHeap.peek();
}
```

**Time Complexity**: O(n log k)  
**Space Complexity**: O(k)

## Key Insights
- Keep top k largest seen so far
- Heap root is smallest among top k, i.e., kth largest overall

## Tips and Tricks
- Decide whether you need a min-heap or max-heap based on what should be removed first.
- For Top K problems, keep the heap at size K to control complexity.
- Store pairs when value alone is not enough to reconstruct the answer.

## Related Problems
- LC 347 Top K Frequent Elements
- LC 23 Merge k Sorted Lists
