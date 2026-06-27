# LC 44: Wildcard Matching

**Link**: [leetcode.com/problems/wildcard-matching](https://leetcode.com/problems/wildcard-matching/)

## Problem
Given an input string `s` and a pattern `p`, implement wildcard pattern matching that supports `?` (matches any single char) and `*` (matches any sequence including empty).

## Optimized Approach: 2D Dynamic Programming

```java
public boolean isMatch(String s, String p) {
    int m = s.length(), n = p.length();
    boolean[][] dp = new boolean[m + 1][n + 1];

    dp[0][0] = true; // empty string matches empty pattern

    // "*" can match empty prefix
    for (int j = 1; j <= n; j++) {
        if (p.charAt(j - 1) == '*') dp[0][j] = dp[0][j - 1];
    }

    for (int i = 1; i <= m; i++) {
        for (int j = 1; j <= n; j++) {
            char sc = s.charAt(i - 1);
            char pc = p.charAt(j - 1);

            if (pc == '*') {
                // '*' matches empty (skip *) OR matches one char (keep *)
                dp[i][j] = dp[i][j - 1] || dp[i - 1][j];
            } else if (pc == '?' || pc == sc) {
                dp[i][j] = dp[i - 1][j - 1];
            }
            // else: dp[i][j] = false (default)
        }
    }

    return dp[m][n];
}
```

**Time Complexity**: O(m × n)  
**Space Complexity**: O(m × n)

## Key Insights

| Transition | Condition | Meaning |
|---|---|---|
| `dp[i][j] = dp[i][j-1]` | `pc == '*'` | `*` matches empty |
| `dp[i][j] = dp[i-1][j]` | `pc == '*'` | `*` consumes one more char |
| `dp[i][j] = dp[i-1][j-1]` | `pc == '?' or pc == sc` | character match |

## Difference from LC 10 (Regex Matching)
- LC 10: `*` means "zero or more of preceding element" (e.g., `a*`)
- LC 44: `*` independently matches any sequence

## Tips and Tricks
- Define the DP state in one sentence before writing transitions.
- Initialize base cases carefully because most DP bugs come from wrong starting values.
- Check whether the transition depends on previous row, previous column, or previous index only.

## Related Problems
- LC 10 Regular Expression Matching
