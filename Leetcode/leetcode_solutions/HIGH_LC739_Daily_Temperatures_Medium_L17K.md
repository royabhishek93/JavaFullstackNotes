# LC 739: Daily Temperatures

**Link**: [leetcode.com/problems/daily-temperatures](https://leetcode.com/problems/daily-temperatures/)

## Problem
Given an array of integers `temperatures`, return an array `answer` where `answer[i]` is the number of days until a warmer temperature. If no future warmer day exists, `answer[i] = 0`.

## Optimized Approach: Monotonic Decreasing Stack

```java
public int[] dailyTemperatures(int[] temperatures) {
    int n = temperatures.length;
    int[] answer = new int[n];
    Deque<Integer> stack = new ArrayDeque<>(); // stack of indices

    for (int i = 0; i < n; i++) {
        // Pop all days that are colder than today
        while (!stack.isEmpty() && temperatures[i] > temperatures[stack.peek()]) {
            int idx = stack.pop();
            answer[idx] = i - idx;
        }
        stack.push(i);
    }

    return answer;
}
```

**Time Complexity**: O(n)  
**Space Complexity**: O(n)

## Key Insights
- Maintain a stack of indices whose "warmer day" hasn't been found yet
- When current day is warmer, resolve all colder days on the stack

## Example
```
temperatures = [73, 74, 75, 71, 69, 72, 76, 73]

i=0 (73): stack=[0]
i=1 (74): 74>73 → pop 0, answer[0]=1. stack=[1]
i=2 (75): 75>74 → pop 1, answer[1]=1. stack=[2]
i=3 (71): stack=[2,3]
i=4 (69): stack=[2,3,4]
i=5 (72): 72>69 → pop 4, answer[4]=1; 72>71 → pop 3, answer[3]=2. stack=[2,5]
i=6 (76): 76>72→pop5 answer[5]=1; 76>75→pop2 answer[2]=4. stack=[6]
i=7 (73): stack=[6,7]
```

## Tips and Tricks
- Ask what the stack or queue is storing: values, indices, or states.
- Monotonic structures are about preserving an ordering invariant after every push.
- If boundaries matter, storing indices is usually safer than storing raw values.

## Related Problems
- LC 84 Largest Rectangle in Histogram
- LC 239 Sliding Window Maximum
