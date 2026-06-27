# LC 66: Plus One

**Link**: [leetcode.com/problems/plus-one](https://leetcode.com/problems/plus-one/)

## Problem
Given a non-empty array of digits representing a non-negative integer, increment the integer by one and return the resulting array.

## Optimized Approach: Carry from Right

```java
public int[] plusOne(int[] digits) {
    for (int i = digits.length - 1; i >= 0; i--) {
        if (digits[i] < 9) {
            digits[i]++;
            return digits;
        }
        digits[i] = 0;
    }

    int[] result = new int[digits.length + 1];
    result[0] = 1;
    return result;
}
```

**Time Complexity**: O(n)  
**Space Complexity**: O(1) or O(n) when overflow happens

## Key Insights
- First non-9 from right stops carry propagation
- All 9s case needs one extra digit

## Tips and Tricks
- Simulation problems reward careful state updates more than clever formulas.
- Track carry, overflow, or boundary transitions explicitly.
- Small manual examples catch most mistakes faster than debugging large inputs.

## Related Problems
- LC 67 Add Binary
