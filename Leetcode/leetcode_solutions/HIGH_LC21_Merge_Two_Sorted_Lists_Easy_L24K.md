# LC 21: Merge Two Sorted Lists

**Link**: [leetcode.com/problems/merge-two-sorted-lists](https://leetcode.com/problems/merge-two-sorted-lists/)

## Problem
You are given the heads of two sorted linked lists list1 and list2. Merge the two lists in a one sorted list. The list should be made by splicing together the nodes of the two lists. Return the head of the merged list.

### Examples
- Input: list1 = [1,2,4], list2 = [1,3,4] → Output: [1,1,2,3,4,4]
- Input: list1 = [], list2 = [] → Output: []
- Input: list1 = [], list2 = [0] → Output: [0]

## Optimized Approach: Single Pass Merge (Two Pointers)

```java
public ListNode mergeTwoLists(ListNode list1, ListNode list2) {
    ListNode dummy = new ListNode(0);
    ListNode current = dummy;

    // Compare and merge
    while (list1 != null && list2 != null) {
        if (list1.val <= list2.val) {
            current.next = list1;
            list1 = list1.next;
        } else {
            current.next = list2;
            list2 = list2.next;
        }
        current = current.next;
    }

    // Attach remaining nodes
    if (list1 != null) {
        current.next = list1;
    } else {
        current.next = list2;
    }

    return dummy.next;
}
```

**Time Complexity**: O(n + m) where n, m are lengths of lists  
**Space Complexity**: O(1) - only relink existing nodes

## Key Insights
- **No extra nodes**: Relink existing nodes, don't create new ones
- **Pointer comparison**: Always attach smaller node first
- **Remaining nodes**: After one list exhausted, attach rest of other
- **Dummy node**: Avoids special case for first node

## Interview Walkthrough
1. **Problem**: Merge two sorted linked lists maintaining order
2. **Constraint**: Can modify the lists (relink, not copy)
3. **Algorithm**:
   - Two pointers walk both lists
   - Always take smaller node, advance its pointer
   - When one list exhausted, attach rest of other
4. **Example**: [1,2,4] merged with [1,3,4]
   ```
   Compare 1 vs 1: take first 1, list1 advances
   Compare 2 vs 1: take second 1, list2 advances
   Compare 2 vs 3: take 2, list1 advances
   Compare 4 vs 3: take 3, list2 advances
   List1 exhausted: attach [4] to end
   Result: [1,1,2,3,4,4]
   ```

## Why This Approach (Optimal)
- ✅ **O(n+m) time**: Visit each node once
- ✅ **O(1) space**: Relink existing, no new nodes
- ✅ **In-place**: Modifies structure, preserves nodes
- ✅ **Simple**: Linear comparison logic

## Common Mistakes
- Creating new nodes instead of relinking
- Forgetting to advance one or both pointers
- Not handling null lists correctly
- Not attaching remaining nodes
- Off-by-one null check

## Tips and Tricks
- "We can modify lists, so relink existing nodes"
- "At each step: compare heads, take smaller, advance"
- "After one list empty, just attach other list's tail"
- "Dummy node makes this uniform — no head exception"

## Edge Cases
- One or both lists empty
- All elements in one list smaller/larger than other
- Lists of different lengths
- Single node lists

## Related Problems
- **LC 23**: Merge k Sorted Lists (k lists, similar approach)
- **LC 2**: Add Two Numbers (linked list operation)
- **LC 88**: Merge Sorted Array (array version)
