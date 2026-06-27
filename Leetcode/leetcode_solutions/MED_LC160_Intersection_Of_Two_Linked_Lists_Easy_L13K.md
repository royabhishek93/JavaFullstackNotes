# LC 160: Intersection of Two Linked Lists

**Link**: [leetcode.com/problems/intersection-of-two-linked-lists](https://leetcode.com/problems/intersection-of-two-linked-lists/)

## Problem
Given the heads of two singly linked lists `headA` and `headB`, return the node at which they intersect, or `null` if they do not intersect.

## Optimized Approach: Two Pointers with Reset

```java
public ListNode getIntersectionNode(ListNode headA, ListNode headB) {
    ListNode a = headA, b = headB;

    while (a != b) {
        a = (a == null) ? headB : a.next;
        b = (b == null) ? headA : b.next;
    }

    return a;
}
```

**Time Complexity**: O(m + n)  
**Space Complexity**: O(1)

## Key Insights
- Both pointers travel the same total distance: `lenA + lenB`
- When one reaches null it jumps to the other list's head
- They meet at the intersection node or both reach null together

## Step-by-Step
```
List A: 4 → 1 → 8 → 4 → 5
List B: 5 → 6 → 1 → 8 → 4 → 5

Pointer a: 4,1,8,4,5,null → 5,6,1, [8]
Pointer b: 5,6,1,8,4,5,null → 4,1,[8]  ← meet here
```

## Tips and Tricks
- Advance pointers with a clear invariant, not by intuition.
- Dummy heads and sentinel nodes simplify boundary handling.
- When two pointers traverse different lengths, resetting can align them without extra space.

## Related Problems
- LC 141 Linked List Cycle
- LC 142 Linked List Cycle II
