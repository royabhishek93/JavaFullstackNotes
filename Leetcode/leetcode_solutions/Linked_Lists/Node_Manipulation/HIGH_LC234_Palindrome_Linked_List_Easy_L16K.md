# LC 234: Palindrome Linked List

**Link**: [leetcode.com/problems/palindrome-linked-list](https://leetcode.com/problems/palindrome-linked-list/)

## Problem
Given the head of a singly linked list, return true if it is a palindrome or false otherwise.

### Examples
- Input: head = [1,2,2,1] → Output: true
- Input: head = [1,2] → Output: false
- Input: head = [1] → Output: true
- Input: head = [9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9] → Output: true

## Optimized Approach: Find Middle + Reverse Second Half + Compare

```java
public boolean isPalindrome(ListNode head) {
    if (head == null || head.next == null) {
        return true;
    }

    // Step 1: Find middle of list
    ListNode slow = head, fast = head;
    while (fast != null && fast.next != null) {
        slow = slow.next;
        fast = fast.next.next;
    }

    // Step 2: Reverse second half
    ListNode secondHalf = reverseList(slow);

    // Step 3: Compare first half with reversed second half
    ListNode ptr1 = head;
    ListNode ptr2 = secondHalf;

    while (ptr2 != null) {  // ptr2 might be shorter
        if (ptr1.val != ptr2.val) {
            return false;
        }
        ptr1 = ptr1.next;
        ptr2 = ptr2.next;
    }

    return true;
}

private ListNode reverseList(ListNode head) {
    ListNode prev = null;
    ListNode curr = head;
    while (curr != null) {
        ListNode next = curr.next;
        curr.next = prev;
        prev = curr;
        curr = next;
    }
    return prev;
}
```

**Time Complexity**: O(n) - three passes (middle, reverse, compare)  
**Space Complexity**: O(1) - only pointers (in-place modifications)

## Key Insights
- **Three phases**: Find middle, reverse second half, compare
- **Slow/fast pointers**: Elegant way to find middle without length
- **In-place reversal**: Modify structure, not values
- **One-sided comparison**: Compare from both ends inward

## Interview Walkthrough
1. **Problem**: Check if linked list is palindromic
2. **Can't use array**: Would use O(n) space
3. **Approach**:
   - Find middle using slow/fast pointers
   - Reverse second half (in-place)
   - Compare first half with reversed second half
4. **Example**: [1,2,2,1]
   ```
   Phase 1: Find middle
     Slow reaches node 2 (first 2)
   Phase 2: Reverse from first 2 onward
     Original: 1→2→2→1
     Reverse second half: 1→2, becomes 1←2←1
   Phase 3: Compare
     First: 1,2  vs  Second: 1,2
     All match → true
   ```
5. **Example**: [1,2,3,2,1]
   ```
   Phase 1: Slow at middle 3
   Phase 2: Reverse [3,2,1] → becomes 2←1
   Phase 3: Compare 1,2,3 with 1,2
            Need to handle odd-length
   ```

## Why This Approach (Optimal)
- ✅ **O(1) space**: No extra data structures (arrays, stacks)
- ✅ **O(n) time**: Three linear passes
- ✅ **In-place**: Modifies list structure, not data
- ✅ **Elegant**: Three clear phases

## Common Mistakes
- Using stack/array (uses O(n) space)
- Incorrect middle finding for odd-length lists
- Not reversing second half correctly
- Wrong comparison logic (comparing wrong halves)
- Not handling null pointers in comparison

## Tips and Tricks
- "We can modify the list, so reverse second half in-place"
- "Three phases: find middle (slow/fast), reverse, compare"
- "For odd length, slow points to middle, skip it in compare"
- "One pointer from start, one from reversed second"

## Alternative Approaches
```
Approach 1: Use stack O(n) space
Approach 2: Recursion O(n) space  
Approach 3: Reverse entire list (this approach) O(1) space ✅
```

## Edge Cases
- Single node
- Two nodes (equal or not)
- Odd-length list (middle element)
- Even-length list
- All same values
- Large list

## Related Problems
- **LC 206**: Reverse Linked List (used as subroutine)
- **LC 141**: Linked List Cycle (two pointers, middle detection)
- **LC 125**: Valid Palindrome (array version)
