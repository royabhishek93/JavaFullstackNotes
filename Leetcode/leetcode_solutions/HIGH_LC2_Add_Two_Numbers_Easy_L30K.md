# LC 2: Add Two Numbers

**Link**: [leetcode.com/problems/add-two-numbers](https://leetcode.com/problems/add-two-numbers/)

## Problem
You are given two non-empty linked lists representing two non-negative integers. The digits are stored in reverse order, and each of their nodes contains a single digit. Add the two numbers and return the sum as a linked list. You may assume the two numbers do not contain any leading zero, except the number 0 itself.

### Examples
- Input: l1 = [2,4,3], l2 = [5,6,4] → Output: [7,0,8] (342 + 465 = 807)
- Input: l1 = [0], l2 = [0] → Output: [0]
- Input: l1 = [9,9,9,9,9,9,9], l2 = [9,9,9,9] → Output: [8,9,9,9,0,0,0,1] (9999999 + 9999 = 10009998)

## Optimized Approach: Single Pass with Carry

```java
public ListNode addTwoNumbers(ListNode l1, ListNode l2) {
    ListNode dummy = new ListNode(0);
    ListNode current = dummy;
    int carry = 0;

    // Traverse both lists simultaneously
    while (l1 != null || l2 != null || carry != 0) {
        int val1 = (l1 != null) ? l1.val : 0;
        int val2 = (l2 != null) ? l2.val : 0;

        // Calculate sum and carry
        int sum = val1 + val2 + carry;
        carry = sum / 10;
        int digit = sum % 10;

        // Create new node with digit
        current.next = new ListNode(digit);
        current = current.next;

        // Move pointers forward
        l1 = (l1 != null) ? l1.next : null;
        l2 = (l2 != null) ? l2.next : null;
    }

    return dummy.next;
}
```

**Time Complexity**: O(max(m, n)) where m, n are lengths of lists  
**Space Complexity**: O(max(m, n)) for result list

## Key Insights
- **Reverse order simplifies**: Process digit-by-digit from LSB, same as addition
- **Carry handling**: sum / 10 for next carry, sum % 10 for current digit
- **Dummy node**: Always create dummy to avoid null handling for head
- **Continue while carry exists**: Different length lists + final carry

## Interview Walkthrough
1. **Problem**: Add two numbers stored in reverse in linked lists
2. **Key Insight**: Reverse storage means we process from LSB (natural for addition)
3. **Algorithm**:
   - Walk both lists simultaneously
   - At each node: sum = val1 + val2 + carry from previous
   - Store digit (sum % 10), update carry (sum / 10)
   - Continue if either list has nodes OR carry remains
4. **Example**: [2,4,3] + [5,6,4]
   ```
   2+5+0=7 (digit=7, carry=0)
   4+6+0=10 (digit=0, carry=1)
   3+4+1=8 (digit=8, carry=0)
   Result: [7,0,8]
   ```

## Why This Approach (Optimal)
- ✅ **O(n) time**: Single pass, efficient
- ✅ **Handles variable lengths**: Null checks allow different list lengths
- ✅ **Carry propagation**: Naturally handled in loop condition
- ✅ **Clean code**: Dummy node eliminates edge cases

## Common Mistakes
- Forgetting carry in sum calculation
- Not continuing loop if carry remains after both lists end
- Not handling different length lists
- Creating head specially instead of using dummy
- Not updating carry/pointers correctly

## Tips and Tricks
- "Numbers are in reverse order, so LSB is first node"
- "Carry propagates naturally — continue while carry exists"
- "Use dummy node to simplify: no special head case"
- "Walk through example showing carry from 4+6=10"

## Edge Cases
- Lists of different lengths (shorter list treated as 0s)
- Final carry (e.g., 999 + 1 = 1000)
- Single node lists
- Lists with zeros

## Related Problems
- **LC 445**: Add Two Numbers II (forward order)
- **LC 67**: Add Binary (strings, not lists)
- **LC 415**: Add Strings (string version)
