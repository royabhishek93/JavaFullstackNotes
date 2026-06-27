# LC 206: Reverse Linked List

**Link**: [leetcode.com/problems/reverse-linked-list](https://leetcode.com/problems/reverse-linked-list/)

## Problem
Given the head of a singly linked list, reverse the list, and return the reversed list.

### Examples
- Input: head = [1,2,3,4,5] → Output: [5,4,3,2,1]
- Input: head = [1,2] → Output: [2,1]
- Input: head = [] → Output: []

## Optimized Approach: Iterative with Three Pointers

```java
public ListNode reverseList(ListNode head) {
    ListNode prev = null;      // Previous node (starts as null)
    ListNode current = head;   // Current node (starts at head)

    while (current != null) {
        ListNode nextTemp = current.next;  // Step 1: Save next node before we modify current.next
        current.next = prev;               // Step 2: Reverse the link (point to previous)
        prev = current;                    // Step 3: Move prev forward
        current = nextTemp;                // Step 4: Move current forward using saved next
    }

    return prev;  // prev is now the new head of reversed list
}
```

**Time Complexity**: O(n) - single pass through list  
**Space Complexity**: O(1) - only using 3 pointers

## Key Insights
- **Three Pointers Pattern**: prev, current, next
- **Save Next First**: CRITICAL - Always save next before modifying current.next
- **Reverse in One Pass**: Walk through list once, reversing links as we go
- **New Head**: After loop, `prev` points to new head (old tail)
- **Original Head becomes Tail**: After reversing, head.next becomes null

## Interview Walkthrough
1. **Problem**: Reverse a singly linked list (change direction of all pointers)
2. **Visualization**: 1 → 2 → 3 → null becomes null ← 1 ← 2 ← 3
3. **Key Challenge**: Must save next pointer BEFORE changing current.next
4. **Algorithm**:
   - Initialize prev = null, current = head
   - For each node:
     - Save its next (will be lost after we change current.next)
     - Point current.next to prev (reverse the link)
     - Move prev forward to current
     - Move current forward using saved next
5. **Example with [1,2,3]**:
   ```
   Start: prev=null, current=1→2→3
   Step 1: nextTemp=2, 1.next=null, prev=1, current=2
   Step 2: nextTemp=3, 2.next=1, prev=2, current=3
   Step 3: nextTemp=null, 3.next=2, prev=3, current=null
   Return: prev (which is 3) → 3→2→1→null
   ```

## Why This Approach (Optimal)
- ✅ **O(1) space**: Only 3 variables, no recursion stack
- ✅ **O(n) time**: Single pass through list
- ✅ **Production ready**: Best for real systems (no stack overflow risk)
- ✅ **Interview friendly**: Easy to code, easy to trace

## Common Mistakes
- **Forgetting nextTemp**: Causes current.next become unreachable (infinite loop or null reference)
- **Wrong order**: Modifying current.next BEFORE saving next → lose reference to rest of list
- **Returning wrong pointer**: Returning head (which is now tail) instead of prev
- **Off-by-one errors**: Wrong initialization of prev or current

## Tips and Tricks
- "The key is we must save next pointer before we reverse the link"
- "Three pointers: prev (where we point), current (what we're processing), nextTemp (save for next iteration)"
- "Walk through [1,2,3] step by step to show you understand"
- "This uses O(1) space - better than recursive O(n) stack space"
- "Verify: after loop, original head.next should be null"
