# LC 155: Min Stack

**Link**: [leetcode.com/problems/min-stack](https://leetcode.com/problems/min-stack/)

## Problem
Design a stack that supports `push`, `pop`, `top`, and retrieving minimum element in constant time.

## Optimized Approach: Value Stack + Min Stack

```java
class MinStack {
    private Deque<Integer> stack;
    private Deque<Integer> minStack;

    public MinStack() {
        stack = new ArrayDeque<>();
        minStack = new ArrayDeque<>();
    }

    public void push(int val) {
        stack.push(val);
        if (minStack.isEmpty() || val <= minStack.peek()) {
            minStack.push(val);
        }
    }

    public void pop() {
        int removed = stack.pop();
        if (removed == minStack.peek()) {
            minStack.pop();
        }
    }

    public int top() {
        return stack.peek();
    }

    public int getMin() {
        return minStack.peek();
    }
}
```

**Time Complexity**: O(1) for all operations  
**Space Complexity**: O(n)

## Key Insights
- `minStack` tracks running minima
- Pop from `minStack` only when removed value equals current min

## Tips and Tricks
- Ask what the stack or queue is storing: values, indices, or states.
- Monotonic structures are about preserving an ordering invariant after every push.
- If boundaries matter, storing indices is usually safer than storing raw values.

## Related Problems
- LC 20 Valid Parentheses
- LC 146 LRU Cache
