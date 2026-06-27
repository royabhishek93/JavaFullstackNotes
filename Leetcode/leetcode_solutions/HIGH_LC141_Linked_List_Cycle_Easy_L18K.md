# LC 141: Linked List Cycle

**Link**: [leetcode.com/problems/linked-list-cycle](https://leetcode.com/problems/linked-list-cycle/)

## Problem
Given head of a linked list, determine if the linked list has a cycle in it. There is a cycle in a linked list if there is some node in the list that can be reached again by continuously following the next pointer. Return true if there is a cycle in the linked list. Otherwise, return false.

### Examples
- Input: head = [3,2,0,-4], pos = 1 (cycle at node 1) → Output: true
- Input: head = [1,2], pos = -1 (no cycle) → Output: false
- Input: head = [1], pos = -1 (single node, no cycle) → Output: false

## Optimized Approach: Floyd's Cycle Detection (Tortoise-Hare)

```java
public boolean hasCycle(ListNode head) {
    if (head == null || head.next == null) {
        return false;
    }

    ListNode slow = head;
    ListNode fast = head;

    // If cycle exists, fast will meet slow
    while (fast != null && fast.next != null) {
        slow = slow.next;           // Move 1 step
        fast = fast.next.next;      // Move 2 steps

        if (slow == fast) {
            return true;            // Cycle detected
        }
    }

    return false;                   // No cycle
}
```

**Time Complexity**: O(n) - at most n steps  
**Space Complexity**: O(1) - only two pointers

## Key Insights
- **Floyd's Algorithm**: Two pointers (1x and 2x speed) must meet in cycle
- **Why it works**: If cycle exists, fast eventually catches slow
- **No extra space**: Can't use HashSet (O(n) space violates constraint)
- **Speed difference matters**: Gap closes by 1 per iteration

## Mathematical Proof
- If cycle exists with length c, fast gains 1 position per iteration
- After at most m + c iterations (m = pre-cycle length), they meet
- If no cycle, fast reaches null first

## Interview Walkthrough
1. **Problem**: Detect if linked list has a cycle
2. **Constraint**: Can't use extra space (HashSet not allowed)
3. **Human intuition**: "If I follow 2 pointers at different speeds..."
4. **Floyd's Algorithm**:
   - Slow: 1 step/iteration
   - Fast: 2 steps/iteration
   - If cycle exists, they must meet (fast catches slow)
5. **Example**: [3,2,0,-4] with cycle at node 1
   ```
   Iteration 1: slow=2, fast=0
   Iteration 2: slow=0, fast=-4
   Iteration 3: slow=-4, fast=2 (cycle: -4→2 detected)
   Iteration 4: slow=2, fast=0 (same node!)
   Return true
   ```

## Why This Approach (Optimal)
- ✅ **O(1) space**: Only two pointers
- ✅ **O(n) time**: At most n + c iterations
- ✅ **Elegant**: Mathematical guarantee
- ✅ **No HashSet needed**: Solves space constraint

## Common Mistakes
- Using HashSet/Set (uses O(n) space)
- Off-by-one in fast pointer (should be .next.next)
- Not checking null before fast.next.next
- Returning early without full check

## Tips and Tricks
- "Can't use HashSet — need O(1) space"
- "Use two pointers: one moves 1 step, one moves 2"
- "If cycle exists, they MUST meet"
- "Check fast and fast.next both not null"

## Edge Cases
- Single node with self-cycle
- Empty list
- Cycle at beginning
- Cycle at end
- Very long list with cycle

## Related Problems
- **LC 142**: Linked List Cycle II (find cycle start)
- **LC 287**: Find the Duplicate Number (same algorithm, array)
- **LC 19**: Remove Nth Node From End (two pointers, no cycle)
