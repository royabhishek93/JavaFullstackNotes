# LC 92: Reverse Linked List II

**Link**: [leetcode.com/problems/reverse-linked-list-ii](https://leetcode.com/problems/reverse-linked-list-ii/)

## Problem
Reverse a linked list from position `left` to `right` (1-indexed) and return the modified head.

## Optimized Approach: Head Insertion in Sublist

```java
public ListNode reverseBetween(ListNode head, int left, int right) {
    if (head == null || left == right) return head;

    ListNode dummy = new ListNode(0);
    dummy.next = head;
    ListNode prev = dummy;

    for (int i = 1; i < left; i++) {
        prev = prev.next;
    }

    ListNode curr = prev.next;
    for (int i = 0; i < right - left; i++) {
        ListNode next = curr.next;
        curr.next = next.next;
        next.next = prev.next;
        prev.next = next;
    }

    return dummy.next;
}
```

**Time Complexity**: O(n)  
**Space Complexity**: O(1)

## Key Insights
- Keep `prev` fixed before sublist
- Repeatedly take `curr.next` and move it to sublist front

## Tips and Tricks
- Advance pointers with a clear invariant, not by intuition.
- Dummy heads and sentinel nodes simplify boundary handling.
- When two pointers traverse different lengths, resetting can align them without extra space.

## Related Problems
- LC 206 Reverse Linked List
- LC 25 Reverse Nodes in k-Group
