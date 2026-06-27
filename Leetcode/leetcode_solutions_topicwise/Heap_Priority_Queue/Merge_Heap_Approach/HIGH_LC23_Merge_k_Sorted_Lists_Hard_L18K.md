# LC 23: Merge k Sorted Lists

**Link**: [leetcode.com/problems/merge-k-sorted-lists](https://leetcode.com/problems/merge-k-sorted-lists/)

## Problem
You are given an array of `k` linked lists, each sorted in ascending order. Merge all linked lists into one sorted linked list.

## Optimized Approach: Min Heap

```java
public ListNode mergeKLists(ListNode[] lists) {
    PriorityQueue<ListNode> minHeap = new PriorityQueue<>((a, b) -> a.val - b.val);

    for (ListNode node : lists) {
        if (node != null) minHeap.offer(node);
    }

    ListNode dummy = new ListNode(-1);
    ListNode tail = dummy;

    while (!minHeap.isEmpty()) {
        ListNode node = minHeap.poll();
        tail.next = node;
        tail = tail.next;

        if (node.next != null) {
            minHeap.offer(node.next);
        }
    }

    return dummy.next;
}
```

**Time Complexity**: O(N log k) where N is total nodes  
**Space Complexity**: O(k)

## Key Insights
- Heap always exposes smallest current head
- After picking node, push its next node into heap

## Tips and Tricks
- Decide whether you need a min-heap or max-heap based on what should be removed first.
- For Top K problems, keep the heap at size K to control complexity.
- Store pairs when value alone is not enough to reconstruct the answer.

## Related Problems
- LC 21 Merge Two Sorted Lists
- LC 215 Kth Largest Element in an Array
