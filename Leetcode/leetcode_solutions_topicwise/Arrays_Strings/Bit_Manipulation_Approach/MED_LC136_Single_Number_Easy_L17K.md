# LC 136: Single Number

**Link**: [leetcode.com/problems/single-number](https://leetcode.com/problems/single-number/)

## Problem
Given a non-empty array of integers where every element appears twice except for one, find that single one. Must be O(n) time and O(1) extra space.

## Optimized Approach: XOR Bit Manipulation

```java
public int singleNumber(int[] nums) {
    int result = 0;
    for (int num : nums) {
        result ^= num;
    }
    return result;
}
```

**Time Complexity**: O(n)  
**Space Complexity**: O(1)

## Key Insights
- XOR is commutative and associative: `a ^ a = 0`, `a ^ 0 = a`
- Every pair cancels out; only the single element survives

## Tips and Tricks
- "XOR of a number with itself is 0; XOR of a number with 0 is the number itself"
- "All paired values cancel, leaving just the single"

## Related Problems
- LC 137 Single Number II
- LC 260 Single Number III
