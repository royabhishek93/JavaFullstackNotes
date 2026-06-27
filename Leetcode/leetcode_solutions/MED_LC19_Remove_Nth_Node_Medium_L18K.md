# LC 19: Remove Nth Node From End of List

**Link**: [leetcode.com/problems/remove-nth-node-from-end-of-list](https://leetcode.com/problems/remove-nth-node-from-end-of-list/)

## Problem
Given the head of a linked list, remove the nth node from the end of the list and return the head of the list.

### Examples
- Input: head = [1,2,3,4,5], n = 2 → Output: [1,2,3,5]
- Input: head = [1], n = 1 → Output: []
- Input: head = [1,2], n = 1 → Output: [1]
- Input: head = [1,2], n = 2 → Output: [2]

## Optimized Approach: Two-Pass with Dummy Node

```java
public ListNode removeNthFromEnd(ListNode head, int n) {
    // Dummy node handles removing head case
    ListNode dummy = new ListNode(0);
    dummy.next = head;

    // First pass: count total length
    ListNode current = head;
    int length = 0;
    while (current != null) {
        length++;
        current = current.next;
    }

    // Calculate position to remove from start
    int targetPos = length - n;

    // Second pass: find node before target
    current = dummy;
    for (int i = 0; i < targetPos; i++) {
        current = current.next;
    }

    // Remove target node
    current.next = current.next.next;

    return dummy.next;
}
```

**Optimized (One-Pass Two-Pointer):**
```java
public ListNode removeNthFromEnd(ListNode head, int n) {
    ListNode dummy = new ListNode(0);
    dummy.next = head;
    
    ListNode first = dummy;
    ListNode second = dummy;

    // Move first pointer n+1 steps ahead
    for (int i = 0; i <= n; i++) {
        first = first.next;
    }

    // Move both pointers until first reaches end
    while (first != null) {
        first = first.next;
        second = second.next;
    }

    // Remove target node
    second.next = second.next.next;

    return dummy.next;
}
```

**Time Complexity**: O(n) - single pass  
**Space Complexity**: O(1) - only pointers

## Key Insights
- **Dummy node critical**: Handles case when removing head (n == length)
- **n+1 gap strategy**: When first reaches null, second is before target
- **One pass optimal**: Keep pointers n nodes apart, move together
- **Edge cases**: Removing head, single node, n = length

## Interview Walkthrough
1. **Problem**: Remove nth node from END (not from start)
2. **Challenge**: Don't know length upfront, need to find node to remove
3. **Dummy node**: Allows uniform handling (even when removing head)
4. **Two-pointer approach**:
   - Create gap of n between pointers
   - Move both simultaneously to end
   - When first reaches null, second is before target
5. **Example**: [1,2,3,4,5], n=2 (remove 4)
   ```
   Gap = 2, dummy.next points to 1
   First: 0→1→2→3→4→5→null
   Second: 0→1→2→3
   second.next = second.next.next removes node 4
   ```

## Why This Approach (Optimal)
- ✅ **O(n) time**: Single pass
- ✅ **O(1) space**: Only pointers
- ✅ **Elegant**: Two-pointer maintains gap
- ✅ **Handles all cases**: Dummy makes head removal uniform

## Common Mistakes
- Forgetting dummy node (fails when removing head)
- Off-by-one error in gap distance
- Not handling single node list
- Trying to remove before finding position
- Confusion about "nth from end" vs "nth from start"

## Tips and Tricks
- "Dummy node handles removing head elegantly"
- "Create n+1 gap between pointers, move together"
- "When first reaches null, second is BEFORE target node"
- "Walk through: if n=2, need gap of 2 to reach second-before-last"

## Related Problems
- **LC 237**: Delete Node in a Linked List (direct node given)
- **LC 2**: Add Two Numbers (linked list manipulation)
- **LC 206**: Reverse Linked List (pointer manipulation)
