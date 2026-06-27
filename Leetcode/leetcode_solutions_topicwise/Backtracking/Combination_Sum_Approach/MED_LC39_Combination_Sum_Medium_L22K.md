# LC 39: Combination Sum

**Link**: [leetcode.com/problems/combination-sum](https://leetcode.com/problems/combination-sum/)

## Problem
Given an array of distinct integers candidates and a target integer target, return all unique combinations where the chosen numbers sum to target. You may return the combinations in any order. The same number may be chosen from candidates an unlimited number of times.

### Examples
- Input: candidates = [2,3,6,7], target = 7 → Output: [[2,2,3],[7]]
- Input: candidates = [2,3,5], target = 8 → Output: [[2,2,2,2],[2,3,3],[3,5]]
- Input: candidates = [2], target = 1 → Output: []

## Optimized Approach: Backtracking with Reuse

```java
public List<List<Integer>> combinationSum(int[] candidates, int target) {
    List<List<Integer>> result = new ArrayList<>();
    backtrack(result, new ArrayList<>(), candidates, target, 0);
    return result;
}

private void backtrack(List<List<Integer>> result, List<Integer> current,
                       int[] candidates, int remaining, int start) {
    // Base case: found valid combination
    if (remaining == 0) {
        result.add(new ArrayList<>(current));
        return;
    }

    // Prune: remaining negative
    if (remaining < 0) {
        return;
    }

    // Try each candidate starting from start
    for (int i = start; i < candidates.length; i++) {
        current.add(candidates[i]);
        // Use i (not i+1) to allow reuse
        backtrack(result, current, candidates, remaining - candidates[i], i);
        current.remove(current.size() - 1);
    }
}
```

**Time Complexity**: O(N^(T/M)) where N = candidates count, T = target, M = min value  
**Space Complexity**: O(T/M) - recursion depth

## Key Insights
- **Reuse allowed**: Pass i (not i+1) to allow same candidate again
- **Prune early**: If remaining < 0, backtrack
- **Start parameter**: Prevents duplicate combinations
- **Avoid duplicates**: Each combo counted once due to start indexing

## Interview Walkthrough
1. **Problem**: Find all combinations summing to target with unlimited reuse
2. **Key difference from LC 40**: Can reuse candidates
3. **Algorithm**:
   - For each candidate from start to end
   - Add to current, recurse with same start (allow reuse)
   - Backtrack by removing candidate
4. **Example**: candidates = [2,3,7], target = 7
   ```
   try 2: current=[2], remaining=5
     try 2: current=[2,2], remaining=3
       try 2: remaining=1, prune
       try 3: remaining=0, add [2,2,3] ✓
       try 7: remaining=-5, prune
     try 3: current=[2,3], remaining=2, prune...
     try 7: remaining=-2, prune
   try 3: current=[3], remaining=4
     try 3: current=[3,3], remaining=1, prune
   try 7: current=[7], remaining=0, add [7] ✓
   ```

## Why This Approach (Optimal)
- ✅ **Pruning**: Early exit if remaining < 0
- ✅ **Reuse handling**: Pass i to allow same candidate
- ✅ **No duplicates**: Start parameter maintains order
- ✅ **Backtracking**: Clear pattern

## Common Mistakes
- Using i+1 (doesn't allow reuse)
- Forgetting to backtrack
- Not pruning (inefficient)
- Wrong base case condition

## Tips and Tricks
- "Key difference: start with i, not i+1"
- "This allows same candidate multiple times"
- "Prune when remaining < 0"
- "Backtrack: remove before trying next"

## Related Problems
- **LC 40**: Combination Sum II (no reuse, duplicates exist)
- **LC 216**: Combination Sum III (with constraints)
- **LC 377**: Combination Sum IV (DP version)
