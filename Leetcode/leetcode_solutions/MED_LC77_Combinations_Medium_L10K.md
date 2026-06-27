# LC 77: Combinations

**Link**: [leetcode.com/problems/combinations](https://leetcode.com/problems/combinations/)

## Problem
Given two integers `n` and `k`, return all possible combinations of `k` numbers chosen from `1..n`.

## Optimized Approach: Backtracking

```java
public List<List<Integer>> combine(int n, int k) {
    List<List<Integer>> result = new ArrayList<>();
    backtrack(1, n, k, new ArrayList<>(), result);
    return result;
}

private void backtrack(int start, int n, int k, List<Integer> path, List<List<Integer>> result) {
    if (path.size() == k) {
        result.add(new ArrayList<>(path));
        return;
    }

    // Prune upper bound to keep enough remaining numbers
    int need = k - path.size();
    for (int num = start; num <= n - need + 1; num++) {
        path.add(num);
        backtrack(num + 1, n, k, path, result);
        path.remove(path.size() - 1);
    }
}
```

**Time Complexity**: O(C(n, k) * k)  
**Space Complexity**: O(k)

## Key Insights
- Choose current number or skip by loop progression
- Pruning avoids unnecessary branches

## Tips and Tricks
- Use the pattern: choose, recurse, undo.
- Prune branches as early as possible to avoid combinatorial explosion.
- Copy the current path only at a valid terminal state, not on every recursive call.

## Related Problems
- LC 78 Subsets
- LC 46 Permutations
