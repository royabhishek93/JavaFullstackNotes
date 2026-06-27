# LC 150: Evaluate Reverse Polish Notation

**Link**: [leetcode.com/problems/evaluate-reverse-polish-notation](https://leetcode.com/problems/evaluate-reverse-polish-notation/)

## Problem
Evaluate the value of an arithmetic expression in Reverse Polish Notation.

## Optimized Approach: Stack Evaluation

```java
public int evalRPN(String[] tokens) {
    Deque<Integer> stack = new ArrayDeque<>();

    for (String t : tokens) {
        switch (t) {
            case "+": {
                int b = stack.pop(), a = stack.pop();
                stack.push(a + b);
                break;
            }
            case "-": {
                int b = stack.pop(), a = stack.pop();
                stack.push(a - b);
                break;
            }
            case "*": {
                int b = stack.pop(), a = stack.pop();
                stack.push(a * b);
                break;
            }
            case "/": {
                int b = stack.pop(), a = stack.pop();
                stack.push(a / b);
                break;
            }
            default:
                stack.push(Integer.parseInt(t));
        }
    }

    return stack.pop();
}
```

**Time Complexity**: O(n)  
**Space Complexity**: O(n)

## Key Insights
- Operator consumes top two values from stack
- Order matters for subtraction and division

## Tips and Tricks
- Ask what the stack or queue is storing: values, indices, or states.
- Monotonic structures are about preserving an ordering invariant after every push.
- If boundaries matter, storing indices is usually safer than storing raw values.

## Related Problems
- LC 20 Valid Parentheses
- LC 224 Basic Calculator
