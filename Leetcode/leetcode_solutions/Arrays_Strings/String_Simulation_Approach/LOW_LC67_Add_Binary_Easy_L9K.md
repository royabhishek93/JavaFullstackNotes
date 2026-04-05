# LC 67: Add Binary

**Link**: [leetcode.com/problems/add-binary](https://leetcode.com/problems/add-binary/)

## Problem
Given two binary strings `a` and `b`, return their sum as a binary string.

## Optimized Approach: Two Pointers + Carry

```java
public String addBinary(String a, String b) {
    StringBuilder sb = new StringBuilder();
    int i = a.length() - 1, j = b.length() - 1;
    int carry = 0;

    while (i >= 0 || j >= 0 || carry != 0) {
        int sum = carry;
        if (i >= 0) sum += a.charAt(i--) - '0';
        if (j >= 0) sum += b.charAt(j--) - '0';

        sb.append(sum % 2);
        carry = sum / 2;
    }

    return sb.reverse().toString();
}
```

**Time Complexity**: O(max(n, m))  
**Space Complexity**: O(max(n, m))

## Key Insights
- Same as decimal addition with base-2 arithmetic
- Build in reverse, then reverse once

## Tips and Tricks
- Use StringBuilder when repeated concatenation would be costly.
- Simulate exactly what the prompt describes before looking for shortcuts.
- Validate the transformation on one manual example to catch ordering mistakes.

## Related Problems
- LC 415 Add Strings
