# LC 22: Generate Parentheses

**Link**: [leetcode.com/problems/generate-parentheses](https://leetcode.com/problems/generate-parentheses/)

## Problem
Given n pairs of parentheses, write a function to generate all combinations of well-formed parentheses.

### Examples
- Input: n = 3 → Output: ["((()))","(()())","(())()","()((()))","()()()"]
- Input: n = 1 → Output: ["()"]
- Input: n = 0 → Output: [""]

## Optimized Approach: Backtracking with Valid Constraints

```java
public List<String> generateParenthesis(int n) {
    List<String> result = new ArrayList<>();
    backtrack(result, "", 0, 0, n);
    return result;
}

private void backtrack(List<String> result, String current, 
                       int open, int close, int n) {
    // Base case: valid combination
    if (current.length() == 2 * n) {
        result.add(current);
        return;
    }

    // Add opening parenthesis if we haven't exceeds limit
    if (open < n) {
        backtrack(result, current + "(", open + 1, close, n);
    }

    // Add closing parenthesis if it doesn't exceed opening count
    if (close < open) {
        backtrack(result, current + ")", open, close + 1, n);
    }
}
```

**Time Complexity**: O(4^n / sqrt(n)) - Catalan number  
**Space Complexity**: O(n) - recursion depth

## Key Insights
- **Valid constraint**: Close count never exceeds open count
- **Prune early**: Only add ')' when close < open
- **Only add '(' while open < n**: Prevents too many opens
- **Catalan number**: C_n = (2n)! / (n+1)! * n!

## Interview Walkthrough
1. **Problem**: Generate all valid parenthesis combinations
2. **Constraint**: For each combination, must be well-formed
3. **Backtracking approach**:
   - Track open and close counts
   - Add '(' if open < n (not exceeding limit)
   - Add ')' if close < open (valid ordering)
4. **Example**: n = 2
   ```
   Start: "", open=0, close=0
   Add '(': "(", open=1, close=0
     Add '(': "((", open=2, close=0
       Add ')': "(()", open=2, close=1
         Add ')': "(())", open=2, close=2 → valid!
     Add ')': "()", open=1, close=1
       Add '(': "()(", open=2, close=1
         Add ')': "()()" → valid!
   ```

## Why This Approach (Optimal)
- ✅ **Prunes invalid**: Never generates invalid combinations
- ✅ **Efficient**: Eliminates huge search space
- ✅ **Catalan optimal**: Can't beat Catalan number growth
- ✅ **Simple logic**: Two easy constraints

## Common Mistakes
- Generating all strings then filtering (wasteful)
- Wrong constraint logic (allowing invalid generation)
- Not tracking separate open/close counters
- Off-by-one in n comparison

## Tips and Tricks
- "Two constraints: open < n, and close < open"
- "Close can never exceed open (always valid ordering)"
- "Prune early: don't generate invalid combinations"
- "Use backtracking with two counters"

## Pruning Intuition
```
Without pruning: Generate 2^(2n) combinations, filter valid
With pruning: Generate only valid combinations (Catalan)

Results in exponential speedup!
```

## Edge Cases
- n = 0 ([""])
- n = 1 (["()"])
- Large n (observe Catalan growth)

## Related Problems
- **LC 17**: Letter Combinations (backtracking)
- **LC 39**: Combination Sum (backtracking)
- **LC 46**: Permutations (backtracking)
