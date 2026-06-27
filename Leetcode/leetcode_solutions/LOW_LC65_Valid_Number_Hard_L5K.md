# LC 65: Valid Number

**Link**: [leetcode.com/problems/valid-number](https://leetcode.com/problems/valid-number/)

## Problem
A valid number can be an integer or a decimal, optionally followed by an exponent part (`e` or `E` with an integer). Determine if the input string `s` is a valid number.

**Valid examples**: `"2"`, `"0089"`, `"-0.1"`, `"+3.14"`, `"4."`, `"-.9"`, `"2e10"`, `"-90E3"`, `"3e+7"`, `"+6e-1"`, `"53.5e93"`, `"-123.456e789"`  
**Invalid examples**: `"abc"`, `"1a"`, `"1e"`, `"e3"`, `"99e2.5"`, `"--6"`

## Approach: Flag-Based Scan

```java
public boolean isNumber(String s) {
    s = s.trim();
    boolean numSeen = false;
    boolean dotSeen = false;
    boolean eSeen   = false;
    boolean numAfterE = true; // vacuously true until e appears

    for (int i = 0; i < s.length(); i++) {
        char c = s.charAt(i);

        if (Character.isDigit(c)) {
            numSeen = true;
            if (eSeen) numAfterE = true;

        } else if (c == '.') {
            if (dotSeen || eSeen) return false; // dup dot or dot after e
            dotSeen = true;

        } else if (c == 'e' || c == 'E') {
            if (eSeen || !numSeen) return false; // dup e or e without prior digit
            eSeen = true;
            numAfterE = false;

        } else if (c == '+' || c == '-') {
            if (i != 0 && s.charAt(i - 1) != 'e' && s.charAt(i - 1) != 'E') return false;

        } else {
            return false; // any other character
        }
    }

    return numSeen && numAfterE;
}
```

**Time Complexity**: O(n)  
**Space Complexity**: O(1)

## Key State Flags

| Flag | Purpose |
|------|---------|
| `numSeen` | At least one digit appeared |
| `dotSeen` | Decimal point appeared (can only appear once, not after e) |
| `eSeen` | Exponent marker appeared (only once) |
| `numAfterE` | At least one digit after the exponent marker |

## Edge Cases
- `"."` → invalid (dot but no digit)
- `"4."` → valid (dot without trailing digit is OK)
- `".5"` → valid (dot without leading digit is OK)
- `"e3"` → invalid (e without prior number)
- `"3e+7"` → valid (sign after e is legal)
- `"--6"` → invalid (sign not at start or after e)

## Tips and Tricks
- List the valid token rules before coding the parser.
- Flags for sign, digit, decimal point, and exponent often make edge cases manageable.
- Trim and validate boundaries first so the main scan stays simple.

## Related Problems
- LC 8 String to Integer (atoi)
