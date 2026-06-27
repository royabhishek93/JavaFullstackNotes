# LC 91: Decode Ways

**Link**: [leetcode.com/problems/decode-ways](https://leetcode.com/problems/decode-ways/)

## Problem
Given string `s` containing digits, return number of ways to decode it using `1->A` ... `26->Z`.

## Optimized Approach: 1D DP

```java
public int numDecodings(String s) {
    if (s == null || s.length() == 0 || s.charAt(0) == '0') return 0;

    int n = s.length();
    int[] dp = new int[n + 1];
    dp[0] = 1;
    dp[1] = 1;

    for (int i = 2; i <= n; i++) {
        char one = s.charAt(i - 1);
        int two = Integer.parseInt(s.substring(i - 2, i));

        if (one != '0') dp[i] += dp[i - 1];
        if (two >= 10 && two <= 26) dp[i] += dp[i - 2];
    }

    return dp[n];
}
```

**Time Complexity**: O(n)  
**Space Complexity**: O(n)

## Tips and Tricks
- Define the DP state in one sentence before writing transitions.
- Initialize base cases carefully because most DP bugs come from wrong starting values.
- Check whether the transition depends on previous row, previous column, or previous index only.

## Related Problems
- LC 639 Decode Ways II
