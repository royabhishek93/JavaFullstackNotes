# LC 69: Sqrt(x)

**Link**: [leetcode.com/problems/sqrtx](https://leetcode.com/problems/sqrtx/)

## Problem
Given a non-negative integer `x`, return the square root of `x` rounded down to the nearest integer.

## Optimized Approach: Binary Search

```java
public int mySqrt(int x) {
    if (x < 2) return x;

    int left = 1, right = x / 2;
    int ans = 1;

    while (left <= right) {
        int mid = left + (right - left) / 2;
        long sq = (long) mid * mid;

        if (sq == x) return mid;

        if (sq < x) {
            ans = mid;
            left = mid + 1;
        } else {
            right = mid - 1;
        }
    }

    return ans;
}
```

**Time Complexity**: O(log x)  
**Space Complexity**: O(1)

## Key Insights
- Search on value range `[1, x/2]`
- Use `long` for `mid * mid` to avoid overflow

## Tips and Tricks
- Binary search the answer only when the search space is monotonic.
- Be explicit about whether the range is inclusive or half-open.
- When debugging, print low, mid, high and check which side is safely discarded.

## Related Problems
- LC 50 Pow(x, n)
