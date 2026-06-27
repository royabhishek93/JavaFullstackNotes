# LC 131: Palindrome Partitioning

**Link**: [leetcode.com/problems/palindrome-partitioning](https://leetcode.com/problems/palindrome-partitioning/)

## Problem
Given a string `s`, partition `s` so every substring of the partition is a palindrome. Return all possible palindrome partitionings.

## Optimized Approach: Backtracking + Palindrome Check

```java
public List<List<String>> partition(String s) {
    List<List<String>> result = new ArrayList<>();
    backtrack(0, s, new ArrayList<>(), result);
    return result;
}

private void backtrack(int start, String s, List<String> path, List<List<String>> result) {
    if (start == s.length()) {
        result.add(new ArrayList<>(path));
        return;
    }

    for (int end = start; end < s.length(); end++) {
        if (isPalindrome(s, start, end)) {
            path.add(s.substring(start, end + 1));
            backtrack(end + 1, s, path, result);
            path.remove(path.size() - 1);
        }
    }
}

private boolean isPalindrome(String s, int l, int r) {
    while (l < r) {
        if (s.charAt(l++) != s.charAt(r--)) return false;
    }
    return true;
}
```

**Time Complexity**: O(n * 2^n)  
**Space Complexity**: O(n)

## Key Insights
- Try each cut point from current index
- Only proceed when substring is palindrome

## Tips and Tricks
- Use the pattern: choose, recurse, undo.
- Prune branches as early as possible to avoid combinatorial explosion.
- Copy the current path only at a valid terminal state, not on every recursive call.

## Related Problems
- LC 5 Longest Palindromic Substring
- LC 647 Palindromic Substrings
