# LC 60: Permutation Sequence

**Link**: [leetcode.com/problems/permutation-sequence](https://leetcode.com/problems/permutation-sequence/)

## Problem
The set `[1, 2, ..., n]` contains `n!` unique permutations. Given `n` and `k`, return the k-th permutation sequence (1-indexed).

## Optimized Approach: Factorial Number System

```java
public String getPermutation(int n, int k) {
    int[] factorial = new int[n + 1];
    factorial[0] = 1;
    for (int i = 1; i <= n; i++) factorial[i] = factorial[i - 1] * i;

    List<Integer> digits = new ArrayList<>();
    for (int i = 1; i <= n; i++) digits.add(i);

    k--; // convert to 0-indexed

    StringBuilder sb = new StringBuilder();
    for (int i = n; i >= 1; i--) {
        int idx = k / factorial[i - 1];
        sb.append(digits.get(idx));
        digits.remove(idx);
        k %= factorial[i - 1];
    }

    return sb.toString();
}
```

**Time Complexity**: O(n²) — `list.remove()` is O(n) per call  
**Space Complexity**: O(n)

## Key Insights
- n digits → n! permutations. First block of `(n-1)!` starts with digit 1, next with digit 2, etc.
- `idx = (k-1) / (n-1)!` gives which digit occupies position 1
- Recurse on remaining digits with updated k

## Trace Example
```
n=4, k=9

factorial = [1, 1, 2, 6, 24]
digits    = [1, 2, 3, 4]
k = 9-1 = 8 (0-indexed)

i=4: idx=8/6=1 → pick digits[1]=2, k=8%6=2, digits=[1,3,4]
i=3: idx=2/2=1 → pick digits[1]=3, k=2%2=0, digits=[1,4]
i=2: idx=0/1=0 → pick digits[0]=1, k=0%1=0, digits=[4]
i=1: idx=0/1=0 → pick digits[0]=4

Result: "2314"
```

## Tips and Tricks
- Look for structure that lets you cut the problem size in half or jump by blocks.
- When using formulas, verify off-by-one handling with a tiny example.
- If multiplication or powers are involved, think about overflow and integer division carefully.

## Related Problems
- LC 31 Next Permutation
- LC 46 Permutations
