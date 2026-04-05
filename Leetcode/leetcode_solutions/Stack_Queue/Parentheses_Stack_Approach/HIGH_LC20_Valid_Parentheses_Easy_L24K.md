# LC 20: Valid Parentheses

**Link**: [leetcode.com/problems/valid-parentheses](https://leetcode.com/problems/valid-parentheses/)

## Problem
Given a string containing just `'('`, `')'`, `'{'`, `'}'`, `'['`, `']'`, determine if input string is valid.

## Optimized Approach: Stack

```java
public boolean isValid(String s) {
    Deque<Character> stack = new ArrayDeque<>();

    for (char ch : s.toCharArray()) {
        if (ch == '(') stack.push(')');
        else if (ch == '{') stack.push('}');
        else if (ch == '[') stack.push(']');
        else {
            if (stack.isEmpty() || stack.pop() != ch) {
                return false;
            }
        }
    }

    return stack.isEmpty();
}
```

**Time Complexity**: O(n)  
**Space Complexity**: O(n)

## Key Insights
- Push expected closing bracket, not opening bracket
- On closing bracket, top must match
- Stack must be empty at end

## Tips and Tricks
- Ask what the stack or queue is storing: values, indices, or states.
- Monotonic structures are about preserving an ordering invariant after every push.
- If boundaries matter, storing indices is usually safer than storing raw values.

## Related Problems
- LC 155 Min Stack
- LC 224 Basic Calculator
