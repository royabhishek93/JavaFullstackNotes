# LC 50: Pow(x, n)

**Link**: [leetcode.com/problems/powx-n](https://leetcode.com/problems/powx-n/)

## Problem
Implement `pow(x, n)`, which calculates `x` raised to the power `n`.

## Optimized Approach: Fast Exponentiation (Binary Exponentiation)

```java
public double myPow(double x, int n) {
    long exp = n; // use long to handle Integer.MIN_VALUE
    if (exp < 0) {
        x = 1 / x;
        exp = -exp;
    }

    double result = 1.0;
    while (exp > 0) {
        if ((exp & 1) == 1) {
            result *= x;
        }
        x *= x;
        exp >>= 1;
    }

    return result;
}
```

**Time Complexity**: O(log n)  
**Space Complexity**: O(1)

## Key Insights
- Repeated squaring cuts exponent in half each step
- Handle negative exponent by reciprocal
- Convert `n` to `long` to avoid overflow for `Integer.MIN_VALUE`

## Tips and Tricks
- Look for structure that lets you cut the problem size in half or jump by blocks.
- When using formulas, verify off-by-one handling with a tiny example.
- If multiplication or powers are involved, think about overflow and integer division carefully.

## Related Problems
- LC 69 Sqrt(x)
