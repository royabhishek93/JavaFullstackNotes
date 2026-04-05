# LC 43: Multiply Strings

**Link**: [leetcode.com/problems/multiply-strings](https://leetcode.com/problems/multiply-strings/)

## Problem
Given two non-negative integers `num1` and `num2` represented as strings, return their product as a string. Do not use BigInteger or direct conversion to integer.

## Optimized Approach: Grade-School Multiplication

```java
public String multiply(String num1, String num2) {
    int m = num1.length(), n = num2.length();
    int[] pos = new int[m + n];

    for (int i = m - 1; i >= 0; i--) {
        for (int j = n - 1; j >= 0; j--) {
            int mul = (num1.charAt(i) - '0') * (num2.charAt(j) - '0');
            int p1 = i + j, p2 = i + j + 1;
            int sum = mul + pos[p2];

            pos[p2] = sum % 10;
            pos[p1] += sum / 10;
        }
    }

    StringBuilder sb = new StringBuilder();
    for (int p : pos) {
        if (!(sb.length() == 0 && p == 0)) sb.append(p);
    }

    return sb.length() == 0 ? "0" : sb.toString();
}
```

**Time Complexity**: O(m × n)  
**Space Complexity**: O(m + n)

## Key Insights
- `num1[i] × num2[j]` contributes to positions `i+j` and `i+j+1` in result
- Accumulate in int array, handle carry naturally

## Tips and Tricks
- Look for structure that lets you cut the problem size in half or jump by blocks.
- When using formulas, verify off-by-one handling with a tiny example.
- If multiplication or powers are involved, think about overflow and integer division carefully.

## Related Problems
- LC 415 Add Strings
- LC 67 Add Binary
