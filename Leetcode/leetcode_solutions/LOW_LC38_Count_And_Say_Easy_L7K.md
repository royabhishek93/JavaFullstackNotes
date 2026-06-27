# LC 38: Count and Say

**Link**: [leetcode.com/problems/count-and-say](https://leetcode.com/problems/count-and-say/)

## Problem
The count-and-say sequence is defined as: read off the digits of the previous term and say how many of each digit. Return the `n`th term.

## Optimized Approach: Iterative RLE

```java
public String countAndSay(int n) {
    String result = "1";

    for (int i = 1; i < n; i++) {
        StringBuilder next = new StringBuilder();
        int j = 0;

        while (j < result.length()) {
            char ch = result.charAt(j);
            int count = 0;

            while (j < result.length() && result.charAt(j) == ch) {
                j++;
                count++;
            }

            next.append(count).append(ch);
        }

        result = next.toString();
    }

    return result;
}
```

**Time Complexity**: O(n × L) where L is max string length  
**Space Complexity**: O(L)

## Key Insights
- Run-Length Encoding (RLE) applied repeatedly
- Scan current string, count consecutive same digits, append count+digit to next

## Example
```
1 → "1"
2 → "11"    (one 1)
3 → "21"    (two 1s)
4 → "1211"  (one 2, one 1)
5 → "111221" (one 1, one 2, two 1s)
```

## Tips and Tricks
- Use StringBuilder when repeated concatenation would be costly.
- Simulate exactly what the prompt describes before looking for shortcuts.
- Validate the transformation on one manual example to catch ordering mistakes.

## Related Problems
- LC 443 String Compression
