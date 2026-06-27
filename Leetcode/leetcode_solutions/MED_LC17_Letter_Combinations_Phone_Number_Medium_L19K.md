# LC 17: Letter Combinations of a Phone Number

**Link**: [leetcode.com/problems/letter-combinations-of-a-phone-number](https://leetcode.com/problems/letter-combinations-of-a-phone-number/)

## Problem
Given a string containing digits 2-9, return all possible letter combinations that the number could represent (phone keypad mapping).

## Optimized Approach: Backtracking

```java
private static final String[] KEYS = {"", "", "abc", "def", "ghi", "jkl", "mno", "pqrs", "tuv", "wxyz"};

public List<String> letterCombinations(String digits) {
    List<String> result = new ArrayList<>();
    if (digits == null || digits.isEmpty()) return result;

    backtrack(digits, 0, new StringBuilder(), result);
    return result;
}

private void backtrack(String digits, int idx, StringBuilder path, List<String> result) {
    if (idx == digits.length()) {
        result.add(path.toString());
        return;
    }

    String letters = KEYS[digits.charAt(idx) - '0'];
    for (char ch : letters.toCharArray()) {
        path.append(ch);
        backtrack(digits, idx + 1, path, result);
        path.deleteCharAt(path.length() - 1);
    }
}
```

**Time Complexity**: O(4^n × n) where n is digits length  
**Space Complexity**: O(n)

## Key Insights
- Each digit maps to 2-4 letters (7 and 9 have 4)
- Classic multi-choice backtracking: pick one letter per digit, then recurse

## Tips and Tricks
- Use the pattern: choose, recurse, undo.
- Prune branches as early as possible to avoid combinatorial explosion.
- Copy the current path only at a valid terminal state, not on every recursive call.

## Related Problems
- LC 22 Generate Parentheses
- LC 46 Permutations
