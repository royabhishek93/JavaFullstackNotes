# LC 238: Product of Array Except Self

**Link**: [leetcode.com/problems/product-of-array-except-self](https://leetcode.com/problems/product-of-array-except-self/)

## Problem
Given an integer array `nums`, return an array `answer` such that `answer[i]` is equal to the product of all elements except `nums[i]`. Must run in O(n) without using the division operator.

## Optimized Approach: Prefix × Suffix in O(1) Extra Space

```java
public int[] productExceptSelf(int[] nums) {
    int n = nums.length;
    int[] result = new int[n];

    // Pass 1: prefix products in result
    result[0] = 1;
    for (int i = 1; i < n; i++) {
        result[i] = result[i - 1] * nums[i - 1];
    }

    // Pass 2: multiply suffix in from right
    int suffix = 1;
    for (int i = n - 1; i >= 0; i--) {
        result[i] *= suffix;
        suffix *= nums[i];
    }

    return result;
}
```

**Time Complexity**: O(n)  
**Space Complexity**: O(1) extra (output array excluded)

## Key Insights
- `result[i] = prefix product of [0..i-1] × suffix product of [i+1..n-1]`
- Build prefix left-to-right, then fold in suffix right-to-left in a single pass

## Tips and Tricks
- Prefix and suffix arrays help when each position depends on everything except itself.
- Decide whether you really need full arrays or just rolling values.
- When excluding the current index, write the left and right contribution separately first.

## Related Problems
- LC 42 Trapping Rain Water
