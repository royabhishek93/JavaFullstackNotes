# LC 134: Gas Station

**Link**: [leetcode.com/problems/gas-station](https://leetcode.com/problems/gas-station/)

## Problem
There are `n` gas stations; `gas[i]` is fuel at station `i`, `cost[i]` is cost to go to next station. Return the starting station index if you can travel around once, else `-1`.

## Optimized Approach: Greedy Single Pass

```java
public int canCompleteCircuit(int[] gas, int[] cost) {
    int total = 0;
    int tank = 0;
    int start = 0;

    for (int i = 0; i < gas.length; i++) {
        int diff = gas[i] - cost[i];
        total += diff;
        tank += diff;

        if (tank < 0) {
            start = i + 1;
            tank = 0;
        }
    }

    return total >= 0 ? start : -1;
}
```

**Time Complexity**: O(n)  
**Space Complexity**: O(1)

## Key Insights
- If total gas < total cost, impossible
- If fail at `i`, no station in current segment can be valid start

## Tips and Tricks
- A greedy choice is valid only if you can justify why local optimality leads to global optimality.
- When unsure, compare the greedy idea with a DP formulation to validate it.
- Track the exact invariant that each greedy update preserves.

## Related Problems
- LC 55 Jump Game
