# LC 71: Simplify Path

**Link**: [leetcode.com/problems/simplify-path](https://leetcode.com/problems/simplify-path/)

## Problem
Given an absolute Unix path, simplify it.

## Optimized Approach: Stack of Path Components

```java
public String simplifyPath(String path) {
    Deque<String> stack = new ArrayDeque<>();
    String[] parts = path.split("/");

    for (String part : parts) {
        if (part.equals("") || part.equals(".")) {
            continue;
        }
        if (part.equals("..")) {
            if (!stack.isEmpty()) stack.pop();
        } else {
            stack.push(part);
        }
    }

    if (stack.isEmpty()) return "/";

    StringBuilder sb = new StringBuilder();
    while (!stack.isEmpty()) {
        sb.append("/").append(stack.removeLast());
    }
    return sb.toString();
}
```

**Time Complexity**: O(n)  
**Space Complexity**: O(n)

## Key Insights
- Ignore empty and "." segments
- ".." means pop previous folder when possible

## Tips and Tricks
- Ask what the stack or queue is storing: values, indices, or states.
- Monotonic structures are about preserving an ordering invariant after every push.
- If boundaries matter, storing indices is usually safer than storing raw values.

## Related Problems
- LC 20 Valid Parentheses
