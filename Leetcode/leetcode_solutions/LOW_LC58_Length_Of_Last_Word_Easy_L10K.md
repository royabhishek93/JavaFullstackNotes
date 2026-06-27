# LC 58: Length of Last Word

**Link**: [leetcode.com/problems/length-of-last-word](https://leetcode.com/problems/length-of-last-word/)

## Problem
Given a string `s` consisting of words and spaces, return the length of the last word.

## Optimized Approach: Reverse Scan

```java
public int lengthOfLastWord(String s) {
    int i = s.length() - 1;

    while (i >= 0 && s.charAt(i) == ' ') i--;

    int len = 0;
    while (i >= 0 && s.charAt(i) != ' ') {
        len++;
        i--;
    }

    return len;
}
```

**Time Complexity**: O(n)  
**Space Complexity**: O(1)

## Key Insights
- Skip trailing spaces first
- Count characters until next space

## Tips and Tricks
- Single-pass scanning problems usually become easy once you define the stopping condition.
- Trim or skip irrelevant characters early to keep the core logic linear.
- Think carefully about what should happen at the end of the scan, not just during it.

## Related Problems
- LC 151 Reverse Words in a String
