# LC 82: Remove Duplicates from Sorted List II

**Link**: [leetcode.com/problems/remove-duplicates-from-sorted-list-ii](https://leetcode.com/problems/remove-duplicates-from-sorted-list-ii/)

## Problem
Given the head of a sorted linked list, delete all nodes that have duplicate numbers, leaving only distinct numbers from the original list.

## Optimized Approach: Dummy Node + Skip Duplicates

```java
public ListNode deleteDuplicates(ListNode head) {
    ListNode dummy = new ListNode(0);
    dummy.next = head;
    ListNode prev = dummy;

    while (prev.next != null) {
        ListNode cur = prev.next;

        // Check if current node has duplicates
        if (cur.next != null && cur.val == cur.next.val) {
            int dupVal = cur.val;
            // Skip all nodes with dupVal
            while (prev.next != null && prev.next.val == dupVal) {
                prev.next = prev.next.next;
            }
        } else {
            prev = prev.next;
        }
    }

    return dummy.next;
}
```

**Time Complexity**: O(n)  
**Space Complexity**: O(1)

## Key Insights
- Unlike LC 83 (keep one copy), here we remove ALL occurrences of duplicated values
- Dummy node avoids head-removal edge case

## Tips and Tricks
- Advance pointers with a clear invariant, not by intuition.
- Dummy heads and sentinel nodes simplify boundary handling.
- When two pointers traverse different lengths, resetting can align them without extra space.

## Related Problems
- LC 83 Remove Duplicates from Sorted List (keep one copy)
