# LC 24: Swap Nodes in Pairs

**Link**: [leetcode.com/problems/swap-nodes-in-pairs](https://leetcode.com/problems/swap-nodes-in-pairs/)

## Problem
Given a linked list, swap every two adjacent nodes and return its head. You must solve the problem without modifying the values in the list's nodes (i.e., only nodes themselves may be changed).

### Examples
- Input: head = [1,2,3,4] → Output: [2,1,4,3]
- Input: head = [] → Output: []
- Input: head = [1] → Output: [1]
- Input: head = [1,2,3] → Output: [2,1,3]

## Optimized Approach: Iterative Two Pointers

```java
public ListNode swapPairs(ListNode head) {
    ListNode dummy = new ListNode(0);
    dummy.next = head;
    ListNode prev = dummy;

    // Swap pairs until list exhausted
    while (prev.next != null && prev.next.next != null) {
        ListNode first = prev.next;      // First node of pair
        ListNode second = prev.next.next; // Second node of pair

        // Swap: prev → second → first → rest
        prev.next = second;
        first.next = second.next;
        second.next = first;

        // Move to next pair
        prev = first;
    }

    return dummy.next;
}
```

**Time Complexity**: O(n) - single pass  
**Space Complexity**: O(1) - only pointers

## Key Insights
- **Pointer manipulation**: 4 pointers for 2-node swap (prev, first, second, next)
- **Visual pattern**: prev → second → first → rest becomes the new structure
- **No modification needed**: Only change next pointers, not values
- **Dummy node**: Essential for handling head edge case

## Interview Walkthrough
1. **Problem**: Swap adjacent pairs without changing node values
2. **Constraint**: Only 4 pointers allowed (implied by O(1) space)
3. **Swap mechanism**:
   ```
   Before: prev → first → second → next
   After:  prev → second → first → next
   ```
4. **Algorithm**:
   - prev.next = second (skip first)
   - first.next = second.next (link first to what's after second)
   - second.next = first (link second back to first)
   - Advance prev to first (for next iteration)

5. **Example**: [1,2,3,4]
   ```
   Iteration 1: prev=dummy, first=1, second=2
     dummy→2→1→3→4 (prev is now 1)
   Iteration 2: prev=1, first=3, second=4
     dummy→2→1→4→3 (swap 3,4)
   Result: [2,1,4,3]
   ```

## Why This Approach (Optimal)
- ✅ **O(n) time**: Single pass
- ✅ **O(1) space**: Fixed pointers
- ✅ **In-place**: Modifies structure only
- ✅ **Elegant**: Clean pointer swapping

## Common Mistakes
- Modifying values instead of pointers (violates constraint)
- Losing reference to nodes (breaking chain)
- Not checking if pair exists (need both nodes)
- Advancing pointer after only first node
- Off-by-one in null checks

## Tips and Tricks
- "Only change pointers, never modify node values"
- "Think of 4 positions: prev, first, second, next"
- "Draw the pointers: helps visualize swapping"
- "Dummy node handles head case elegantly"
- "Check BOTH nodes exist before swapping"

## Edge Cases
- List with odd number of nodes (last node alone)
- Empty list
- Single node
- Two nodes

## Related Problems
- **LC 25**: Reverse Nodes in k-Group (generalization)
- **LC 19**: Remove Nth Node From End
- **LC 206**: Reverse Linked List (similar pointer work)
