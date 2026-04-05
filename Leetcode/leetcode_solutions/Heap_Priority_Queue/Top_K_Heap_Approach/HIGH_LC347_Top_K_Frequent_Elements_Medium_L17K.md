# LC 347: Top K Frequent Elements

**Link**: [leetcode.com/problems/top-k-frequent-elements](https://leetcode.com/problems/top-k-frequent-elements/)

## Problem
Given an integer array `nums` and an integer `k`, return the `k` most frequent elements.

## Optimized Approach: Frequency Map + Min Heap

```java
public int[] topKFrequent(int[] nums, int k) {
    Map<Integer, Integer> freq = new HashMap<>();
    for (int num : nums) {
        freq.put(num, freq.getOrDefault(num, 0) + 1);
    }

    PriorityQueue<int[]> minHeap = new PriorityQueue<>((a, b) -> a[1] - b[1]);

    for (Map.Entry<Integer, Integer> e : freq.entrySet()) {
        minHeap.offer(new int[]{e.getKey(), e.getValue()});
        if (minHeap.size() > k) minHeap.poll();
    }

    int[] result = new int[k];
    for (int i = k - 1; i >= 0; i--) {
        result[i] = minHeap.poll()[0];
    }

    return result;
}
```

**Time Complexity**: O(n log k)  
**Space Complexity**: O(n)

## Key Insights
- Keep heap size limited to `k`
- Heap root is smallest frequency among current top-k set

## Tips and Tricks
- Decide whether you need a min-heap or max-heap based on what should be removed first.
- For Top K problems, keep the heap at size K to control complexity.
- Store pairs when value alone is not enough to reconstruct the answer.

## Related Problems
- LC 215 Kth Largest Element in an Array
