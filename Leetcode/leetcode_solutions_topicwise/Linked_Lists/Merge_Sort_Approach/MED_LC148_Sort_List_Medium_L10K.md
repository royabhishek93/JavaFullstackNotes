# LC 148: Sort List

**Link**: [leetcode.com/problems/sort-list](https://leetcode.com/problems/sort-list/)

## Problem
Given the head of a linked list, return the list sorted in ascending order.

## Optimized Approach: Merge Sort (Bottom-Up for O(1) Space)

```java
public ListNode sortList(ListNode head) {
    if (head == null || head.next == null) return head;

    // Split at middle
    ListNode mid = getMid(head);
    ListNode right = mid.next;
    mid.next = null;

    ListNode leftSorted = sortList(head);
    ListNode rightSorted = sortList(right);

    return merge(leftSorted, rightSorted);
}

private ListNode getMid(ListNode head) {
    ListNode slow = head, fast = head.next;
    while (fast != null && fast.next != null) {
        slow = slow.next;
        fast = fast.next.next;
    }
    return slow;
}

private ListNode merge(ListNode l1, ListNode l2) {
    ListNode dummy = new ListNode(0);
    ListNode cur = dummy;

    while (l1 != null && l2 != null) {
        if (l1.val <= l2.val) { cur.next = l1; l1 = l1.next; }
        else                  { cur.next = l2; l2 = l2.next; }
        cur = cur.next;
    }

    cur.next = (l1 != null) ? l1 : l2;
    return dummy.next;
}
```

**Time Complexity**: O(n log n)  
**Space Complexity**: O(log n) recursion stack (O(1) with iterative bottom-up)

## Key Insights
- Merge sort is ideal for linked lists: O(n log n) without random access
- `fast = head.next` (not `head`) ensures the left half is longer for odd-length lists

## Tips and Tricks
- State the core invariant before coding so the implementation follows the idea directly.
- Test the smallest edge cases first because they expose most off-by-one bugs.
- When explaining in interviews, lead with the optimized idea and then justify complexity clearly.

## Related Problems
- LC 21 Merge Two Sorted Lists
- LC 23 Merge k Sorted Lists
