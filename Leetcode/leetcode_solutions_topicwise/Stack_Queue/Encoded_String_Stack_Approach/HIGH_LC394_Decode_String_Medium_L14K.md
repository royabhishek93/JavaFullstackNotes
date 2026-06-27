# LC 394: Decode String

**Link**: [leetcode.com/problems/decode-string](https://leetcode.com/problems/decode-string/)

## Problem
Given an encoded string like `3[a2[c]]`, return the decoded string `accaccacc`. The encoding rule is `k[encoded_string]`.

## Optimized Approach: Stack

```java
public String decodeString(String s) {
    Deque<Integer> countStack = new ArrayDeque<>();
    Deque<StringBuilder> strStack = new ArrayDeque<>();
    StringBuilder current = new StringBuilder();
    int k = 0;

    for (char ch : s.toCharArray()) {
        if (Character.isDigit(ch)) {
            k = k * 10 + (ch - '0');
        } else if (ch == '[') {
            countStack.push(k);
            strStack.push(current);
            current = new StringBuilder();
            k = 0;
        } else if (ch == ']') {
            int repeat = countStack.pop();
            StringBuilder prev = strStack.pop();
            String inner = current.toString();
            for (int i = 0; i < repeat; i++) prev.append(inner);
            current = prev;
        } else {
            current.append(ch);
        }
    }

    return current.toString();
}
```

**Time Complexity**: O(maxK^depth × n) — proportional to decoded length  
**Space Complexity**: O(depth)

## Key Insights
- Two stacks: one for repeat counts, one for string built so far before `[`
- On `]`, repeat inner string and append to previous context

## Example Trace
```
"3[a2[c]]"
  '3' → k=3
  '[' → push(3), push(""), current="", k=0
  'a' → current="a"
  '2' → k=2
  '[' → push(2), push("a"), current="", k=0
  'c' → current="c"
  ']' → repeat=2, prev="a", current="a"+"cc" = "acc"
  ']' → repeat=3, prev="", current="" + "accaccacc"
```

## Tips and Tricks
- Ask what the stack or queue is storing: values, indices, or states.
- Monotonic structures are about preserving an ordering invariant after every push.
- If boundaries matter, storing indices is usually safer than storing raw values.

## Related Problems
- LC 150 Evaluate Reverse Polish Notation
- LC 20 Valid Parentheses
