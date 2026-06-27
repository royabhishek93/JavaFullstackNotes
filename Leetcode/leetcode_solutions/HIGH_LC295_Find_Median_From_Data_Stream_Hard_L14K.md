# LC 295: Find Median from Data Stream

**Link**: [leetcode.com/problems/find-median-from-data-stream](https://leetcode.com/problems/find-median-from-data-stream/)

## Problem
Design a data structure that supports:
- `addNum(int num)`
- `findMedian()`

## Optimized Approach: Two Heaps

```java
class MedianFinder {
    // Max-heap for lower half
    private PriorityQueue<Integer> low;
    // Min-heap for upper half
    private PriorityQueue<Integer> high;

    public MedianFinder() {
        low = new PriorityQueue<>((a, b) -> b - a);
        high = new PriorityQueue<>();
    }

    public void addNum(int num) {
        low.offer(num);
        high.offer(low.poll());

        if (high.size() > low.size()) {
            low.offer(high.poll());
        }
    }

    public double findMedian() {
        if (low.size() > high.size()) {
            return low.peek();
        }
        return (low.peek() + high.peek()) / 2.0;
    }
}
```

**Time Complexity**: O(log n) for `addNum`, O(1) for `findMedian`  
**Space Complexity**: O(n)

## Key Insights
- Keep sizes balanced (`low` has equal or one extra)
- All values in `low` <= all values in `high`

## Tips and Tricks
- Decide whether you need a min-heap or max-heap based on what should be removed first.
- For Top K problems, keep the heap at size K to control complexity.
- Store pairs when value alone is not enough to reconstruct the answer.

## Related Problems
- LC 215 Kth Largest Element in an Array
- LC 347 Top K Frequent Elements
