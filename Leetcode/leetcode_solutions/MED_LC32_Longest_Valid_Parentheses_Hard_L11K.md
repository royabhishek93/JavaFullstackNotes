# LC 32: Longest Valid Parentheses

**Link**: [leetcode.com/problems/longest-valid-parentheses](https://leetcode.com/problems/longest-valid-parentheses/)

## Problem
Given a string containing only `'('` and `')'`, return the length of the longest valid (well-formed) parentheses substring.

## Optimized Approach: Stack with Base Index

```java
public int longestValidParentheses(String s) {
    Deque<Integer> stack = new ArrayDeque<>();
    stack.push(-1); // base index

    int maxLen = 0;

    for (int i = 0; i < s.length(); i++) {
        if (s.charAt(i) == '(') {
            stack.push(i);
        } else {
            stack.pop(); // match with top

            if (stack.isEmpty()) {
                stack.push(i); // new base
            } else {
                maxLen = Math.max(maxLen, i - stack.peek());
            }
        }
    }

    return maxLen;
}
```

**Time Complexity**: O(n)  
**Space Complexity**: O(n)

## Key Insights
- Stack stores indices; bottom of stack is the "last unmatched" boundary
- When `)` has no match (stack becomes empty), push its index as new base
- Length = current index − top of stack (boundary)

## Trace Example
```
s = ")(())"
stack = [-1]

i=0 ')': pop -1, stack empty → push 0, stack=[0]
i=1 '(': push 1, stack=[0,1]
i=2 '(': push 2, stack=[0,1,2]
i=3 ')': pop 2, peek=1, len=3-1=2
i=4 ')': pop 1, peek=0, len=4-0=4  ← answer
```

## Alternative: Two-Pass L-R Scan (O(1) space)
```java
public int longestValidParentheses(String s) {
    int left = 0, right = 0, max = 0;
    for (char c : s.toCharArray()) {
        if (c == '(') left++; else right++;
        if (left == right) max = Math.max(max, 2 * right);
        else if (right > left) { left = 0; right = 0; }
    }
    left = 0; right = 0;
    for (int i = s.length() - 1; i >= 0; i--) {
        char c = s.charAt(i);
        if (c == '(') left++; else right++;
        if (left == right) max = Math.max(max, 2 * left);
        else if (left > right) { left = 0; right = 0; }
    }
    return max;
}
```

## Tips and Tricks
- Ask what the stack or queue is storing: values, indices, or states.
- Monotonic structures are about preserving an ordering invariant after every push.
- If boundaries matter, storing indices is usually safer than storing raw values.

## Related Problems
- LC 20 Valid Parentheses
- LC 22 Generate Parentheses
