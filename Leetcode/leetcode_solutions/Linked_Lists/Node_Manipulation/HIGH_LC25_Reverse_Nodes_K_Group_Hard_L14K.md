# LC 25: Reverse Nodes in k-Group

**Link**: [leetcode.com/problems/reverse-nodes-in-k-group](https://leetcode.com/problems/reverse-nodes-in-k-group/)

## Problem
Given the head of a linked list, reverse the nodes of the list k at a time, and return the modified list. k is a positive integer and is less than or equal to the length of the linked list. If the number of nodes is not a multiple of k then left-out nodes, in the end, should remain as is.

### Examples
- Input: head = [1,2,3,4,5], k = 2 → Output: [2,1,4,3,5]
- Input: head = [1,2,3,4,5], k = 3 → Output: [3,2,1,4,5]
- Input: head = [1,2,3,4,5], k = 1 → Output: [1,2,3,4,5]

## Optimized Approach: Reverse k-Groups with Pointers

```java
public ListNode reverseKGroup(ListNode head, int k) {
    // Check if k nodes exist
    ListNode curr = head;
    for (int i = 0; i < k; i++) {
        if (curr == null) return head;
        curr = curr.next;
    }

    // Reverse first k nodes
    ListNode prev = null;
    curr = head;
    for (int i = 0; i < k; i++) {
        ListNode next = curr.next;
        curr.next = prev;
        prev = curr;
        curr = next;
    }

    // Recursively reverse k nodes in rest of list
    head.next = reverseKGroup(curr, k);

    return prev;
}
```

**Time Complexity**: O(n) - visit each node once  
**Space Complexity**: O(n/k) - recursion depth

## Key Insights
- **Check before reverse**: Verify k nodes exist before processing
- **Local reversal**: Reverse exactly k nodes, link to recursion result
- **Recursive structure**: After reversing k nodes, solve rest recursively
- **Remaining nodes**: If < k nodes remain, leave as-is

## Interview Walkthrough
1. **Problem**: Reverse every k consecutive nodes
2. **Challenges**:
   - Don't reverse if fewer than k nodes remain
   - Link reversed groups together
   - Handle partial last group
3. **Algorithm**:
   - **Phase 1**: Check k nodes exist
   - **Phase 2**: Reverse those k nodes in-place
   - **Phase 3**: Link to reverseKGroup(next, k)
4. **Example**: [1,2,3,4,5], k=2
   ```
   Phase 1: Check 2 nodes exist (1→2) ✓
   Phase 2: Reverse 1,2 → prev=2, head=1
   Phase 3: 1.next = reverseKGroup(3, 2)
   
   Recursion: reverseKGroup(3, 2)
   Phase 1: Check 2 nodes exist (3→4) ✓
   Phase 2: Reverse 3,4 → prev=4, head=3
   Phase 3: 3.next = reverseKGroup(5, 2)
   
   Recursion: reverseKGroup(5, 2)
   Phase 1: Check 2 nodes exist? 5 is alone ✗
   Return 5 (no reverse)
   
   Result: [2,1,4,3,5]
   ```

## Why This Approach (Optimal)
- ✅ **O(n) time**: Each node visited once
- ✅ **O(n/k) space**: Recursion depth, not O(n)
- ✅ **Clean logic**: Clear phases (check, reverse, recurse)
- ✅ **Partial groups handled**: Natural base case

## Common Mistakes
- Reversing without checking k nodes exist
- Not linking reversed group to recursion result
- Off-by-one in checking k nodes
- Reversing partial groups (leaving wrong length)
- Losing reference during reversal

## Tips and Tricks
- "Always check k nodes exist before processing"
- "Three phases: check → reverse → link to recursion"
- "Remaining < k nodes stay in place naturally"
- "Recursive structure is elegant — solve k, then rest"
- "Similar to LC 24 (k=2), but generalized"

## Iterative Approach (Alternative)
```java
// More complex but avoids recursion
// Use dummy node and track group boundaries
```

## Edge Cases
- k = 1 (no reversal needed)
- k = length (reverse entire list)
- k > length (no reversal)
- k = length + 1 (return as-is)

## Related Problems
- **LC 24**: Swap Nodes in Pairs (k=2 special case)
- **LC 206**: Reverse Linked List (reverse entire, k=n)
- **LC 92**: Reverse Linked List II (specific range)
