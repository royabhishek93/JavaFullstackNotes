# LC 142: Linked List Cycle II

**Link**: [leetcode.com/problems/linked-list-cycle-ii](https://leetcode.com/problems/linked-list-cycle-ii/)

## Problem
Given the head of a linked list, return the node where the cycle begins. If there is no cycle, return null. There is a cycle in a linked list if there is some node in the list that can be reached again by continuously following the next pointer.

### Examples
- Input: head = [3,2,0,-4], pos = 1 → Output: Node 2 (cycle at 1, detected at node whose value is 2)
- Input: head = [1,2], pos = -1 → Output: null (no cycle)
- Input: head = [1], pos = -1 → Output: null

## Optimized Approach: Floyd's Cycle + Phase 2 (Pointers Meet at Start)

```java
public ListNode detectCycle(ListNode head) {
    if (head == null || head.next == null) {
        return null;
    }

    ListNode slow = head;
    ListNode fast = head;

    // Phase 1: Detect cycle using Floyd's algorithm
    while (fast != null && fast.next != null) {
        slow = slow.next;
        fast = fast.next.next;

        if (slow == fast) {
            // Cycle detected, find start
            // Phase 2: One pointer from head, one from meeting point
            ListNode ptr1 = head;
            ListNode ptr2 = slow;

            while (ptr1 != ptr2) {
                ptr1 = ptr1.next;
                ptr2 = ptr2.next;
            }

            return ptr1;  // Cycle start found
        }
    }

    return null;  // No cycle
}
```

**Time Complexity**: O(n) - Phase 1: n, Phase 2: n  
**Space Complexity**: O(1) - only pointers

## Key Insights
- **Phase 1**: Floyd's algorithm detects cycle
- **Phase 2 critical**: When slow and fast meet, they're in the cycle
- **Distance property**: Distance from head to cycle start = distance from meeting point back
- **Why it works**: The distances balance perfectly due to speed ratio (2:1)

## Mathematical Proof
If a = distance from head to cycle start, b = distance from cycle start to meeting point:
- Slow travels: a + b
- Fast travels: a + b + c (where c = rest of cycle)
- Since fast = 2 × slow: 2(a + b) = a + b + c
- Therefore: a + b = c, which means a = c - b
- Placing one pointer at head, one at meeting point, they meet at cycle start

## Interview Walkthrough
1. **Problem**: Find WHERE cycle starts, not just detect it
2. **Previous knowledge**: Floyd's detects cycle (LC 141)
3. **New insight**: The meeting point tells us about cycle structure
4. **Phase 1**: Run Floyd's algorithm
5. **Phase 2**: Two pointers from head and meeting point
   - They meet exactly at cycle start
6. **Example**: [3,2,0,-4] with cycle at node 1
   ```
   Phase 1: Detect cycle, slow & fast meet at some node
   Phase 2: Move one pointer from head, one from meeting point
           They meet at node with value 2
   ```

## Why This Approach (Optimal)
- ✅ **O(n) time**: Two phases, each O(n)
- ✅ **O(1) space**: No extra data structures
- ✅ **Elegant**: Leverages speed ratio property
- ✅ **Proven**: Mathematical guarantee

## Common Mistakes
- Skipping Phase 2 (just returning meeting point, wrong!)
- Wrong distance formula in explanation
- Using HashSet (uses O(n) space)
- Not detecting cycle first

## Tips and Tricks
- "Phase 1: Detect cycle (same as LC 141)"
- "Phase 2: CRITICAL — use two pointers from different starts"
- "They meet at cycle beginning, not at meeting point"
- "Distance from head to cycle = distance from meeting to cycle"
- "Explain speed difference leads to distance property"

## Critical Distinction
```
LC 141: "Is there a cycle?" → boolean
LC 142: "Where does cycle start?" → ListNode

LC 142 Hard because Phase 2 is unintuitive and needs explanation
```

## Edge Cases
- No cycle (return null)
- Cycle at beginning
- Cycle at end
- Single node cycle
- Very long pre-cycle segment

## Related Problems
- **LC 141**: Linked List Cycle (just detection, no finding)
- **LC 287**: Find the Duplicate Number (same algorithm on arrays)
- **LC 19**: Remove Nth Node From End (two pointers)
