# LC 40: Combination Sum II

**Link**: [leetcode.com/problems/combination-sum-ii](https://leetcode.com/problems/combination-sum-ii/)

## Problem
Given `candidates` (may contain duplicates) and `target`, find all unique combinations that sum to target. Each candidate may only be used once.

## Optimized Approach: Backtracking + Skip Duplicates

```java
public List<List<Integer>> combinationSum2(int[] candidates, int target) {
    Arrays.sort(candidates);
    List<List<Integer>> result = new ArrayList<>();
    backtrack(candidates, target, 0, new ArrayList<>(), result);
    return result;
}

private void backtrack(int[] candidates, int remaining, int start,
                       List<Integer> path, List<List<Integer>> result) {
    if (remaining == 0) {
        result.add(new ArrayList<>(path));
        return;
    }

    for (int i = start; i < candidates.length; i++) {
        if (candidates[i] > remaining) break; // pruning

        // Skip duplicates at the same recursion level
        if (i > start && candidates[i] == candidates[i - 1]) continue;

        path.add(candidates[i]);
        backtrack(candidates, remaining - candidates[i], i + 1, path, result);
        path.remove(path.size() - 1);
    }
}
```

**Time Complexity**: O(2^n)  
**Space Complexity**: O(n)

## Key Insights
- Sort first so duplicates are adjacent
- Skip `candidates[i] == candidates[i-1]` at the same `start` level to avoid duplicate combinations
- Pass `i + 1` (not `i`) since each element used at most once

## Tips and Tricks
- Use the pattern: choose, recurse, undo.
- Prune branches as early as possible to avoid combinatorial explosion.
- Copy the current path only at a valid terminal state, not on every recursive call.

## Related Problems
- LC 39 Combination Sum (unlimited reuse)
- LC 216 Combination Sum III
