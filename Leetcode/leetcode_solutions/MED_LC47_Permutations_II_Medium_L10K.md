# LC 47: Permutations II

**Link**: [leetcode.com/problems/permutations-ii](https://leetcode.com/problems/permutations-ii/)

## Problem
Given a collection of numbers that might contain duplicates, return all possible unique permutations.

## Optimized Approach: Sort + Backtracking with Used Array

```java
public List<List<Integer>> permuteUnique(int[] nums) {
    Arrays.sort(nums);
    List<List<Integer>> result = new ArrayList<>();
    boolean[] used = new boolean[nums.length];
    backtrack(nums, used, new ArrayList<>(), result);
    return result;
}

private void backtrack(int[] nums, boolean[] used, List<Integer> path, List<List<Integer>> result) {
    if (path.size() == nums.length) {
        result.add(new ArrayList<>(path));
        return;
    }

    for (int i = 0; i < nums.length; i++) {
        if (used[i]) continue;

        // Skip duplicate: same value as previous AND previous was not used in this path
        if (i > 0 && nums[i] == nums[i - 1] && !used[i - 1]) continue;

        used[i] = true;
        path.add(nums[i]);
        backtrack(nums, used, path, result);
        path.remove(path.size() - 1);
        used[i] = false;
    }
}
```

**Time Complexity**: O(n! × n)  
**Space Complexity**: O(n)

## Key Insights
- Sort to group duplicates
- Skip `nums[i] == nums[i-1] && !used[i-1]`: ensures duplicates are only placed in one particular order across recursive calls

## Tips and Tricks
- Use the pattern: choose, recurse, undo.
- Prune branches as early as possible to avoid combinatorial explosion.
- Copy the current path only at a valid terminal state, not on every recursive call.

## Related Problems
- LC 46 Permutations
- LC 40 Combination Sum II
