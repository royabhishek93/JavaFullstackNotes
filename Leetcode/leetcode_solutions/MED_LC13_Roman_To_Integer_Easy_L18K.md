# LC 13: Roman to Integer

**Link**: [leetcode.com/problems/roman-to-integer](https://leetcode.com/problems/roman-to-integer/)

## Problem
Convert a Roman numeral string to an integer.

## Optimized Approach: Right-to-Left Scan

```java
public int romanToInt(String s) {
    Map<Character, Integer> map = new HashMap<>();
    map.put('I', 1); map.put('V', 5); map.put('X', 10);
    map.put('L', 50); map.put('C', 100); map.put('D', 500); map.put('M', 1000);

    int total = 0;
    int prev = 0;

    for (int i = s.length() - 1; i >= 0; i--) {
        int cur = map.get(s.charAt(i));
        if (cur < prev) total -= cur;
        else total += cur;
        prev = cur;
    }

    return total;
}
```

**Time Complexity**: O(n)  
**Space Complexity**: O(1)

## Key Insights
- If smaller value appears before larger value, subtract
- Right-to-left avoids explicit pair checks

## Tips and Tricks
- List the valid token rules before coding the parser.
- Flags for sign, digit, decimal point, and exponent often make edge cases manageable.
- Trim and validate boundaries first so the main scan stays simple.

## Related Problems
- LC 12 Integer to Roman
