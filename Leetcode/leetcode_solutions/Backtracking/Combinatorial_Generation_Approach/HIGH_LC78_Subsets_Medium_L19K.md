# LC 78: Subsets

**Link**: [leetcode.com/problems/subsets](https://leetcode.com/problems/subsets/)

## Problem
Given an integer array nums of unique elements, return all possible subsets (the power set). The solution set must not contain duplicate subsets. Return the solution in any order.

### Examples
- Input: nums = [1,2,3] → Output: [[],[1],[2],[1,2],[3],[1,3],[2,3],[1,2,3]]
- Input: nums = [0] → Output: [[],[0]]

## Optimized Approach: Backtracking/Iterative Building

```java
public List<List<Integer>> subsets(int[] nums) {
    List<List<Integer>> result = new ArrayList<>();
    backtrack(result, new ArrayList<>(), nums, 0);
    return result;
}

private void backtrack(List<List<Integer>> result, List<Integer> current,
                       int[] nums, int start) {
    // Add current subset
    result.add(new ArrayList<>(current));

    // Try adding each remaining element
    for (int i = start; i < nums.length; i++) {
        current.add(nums[i]);
        backtrack(result, current, nums, i + 1);
        current.remove(current.size() - 1);  // Backtrack
    }
}
```

**Alternative Iterative:**
```java
public List<List<Integer>> subsets(int[] nums) {
    List<List<Integer>> result = new ArrayList<>();
    result.add(new ArrayList<>());  // Empty subset

    for (int num : nums) {
        int size = result.size();
        for (int i = 0; i < size; i++) {
            List<Integer> newSubset = new ArrayList<>(result.get(i));
            newSubset.add(num);
            result.add(newSubset);
        }
    }

    return result;
}
```

**Time Complexity**: O(n * 2^n) - 2^n subsets, O(n) to copy  
**Space Complexity**: O(n) - recursion depth (not counting output)

## Key Insights
- **All subsets**: Every element either in subset or not
- **Add before exploring**: Include current subset before extending
- **Backtracking**: Remove element after recursing
- **Iterative insight**: Each element doubles subset count

## Interview Walkthrough
1. **Problem**: Generate all subsets
2. **Observation**: 2^n total subsets (each element: in or out)
3. **Backtracking approach**:
   - Start with empty set
   - At each step, add current subset to result
   - Try adding each remaining element
   - Backtrack by removing element
4. **Example**: [1,2]
   ```
   Start: []
   Add []: result = [[]]
   Try adding 1:
     current = [1], add to result
     Try adding 2:
       current = [1,2], add to result
       Backtrack: current = [1]
     Backtrack: current = []
   Try adding 2:
     current = [2], add to result
     Backtrack: current = []
   Final: [[], [1], [1,2], [2]]
   ```

## Why This Approach (Optimal)
- ✅ **O(2^n) time**: Optimal for generating all subsets
- ✅ **O(n) space**: Recursion depth only
- ✅ **Natural**: Backtracking pattern clear
- ✅ **Iterative alternative**: Avoids recursion if preferred

## Common Mistakes
- Forgetting to add subset before exploring
- Not backtracking (removing element)
- Modifying result list incorrectly
- Off-by-one in loop bounds

## Tips and Tricks
- "2^n subsets total: each element in or out"
- "Add current subset BEFORE exploring further"
- "Loop from start to avoid duplicates"
- "Backtrack by removing last element"

## Iterative vs Recursive
```
Recursive: Intuitive, clear backtracking pattern
Iterative: Build up by doubling with each element
Both O(2^n) but different clarity
```

## Related Problems
- **LC 90**: Subsets II (with duplicates)
- **LC 39**: Combination Sum (similar)
- **LC 46**: Permutations (similar pattern)
