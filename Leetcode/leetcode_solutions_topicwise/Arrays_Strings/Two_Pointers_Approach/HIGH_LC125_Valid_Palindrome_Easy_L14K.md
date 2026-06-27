# LC 125: Valid Palindrome

**Link**: [leetcode.com/problems/valid-palindrome](https://leetcode.com/problems/valid-palindrome/)

## Problem
A phrase is a palindrome if, after converting all uppercase letters into lowercase and removing all non-alphanumeric characters, it reads the same forward and backward.

## Optimized Approach: Two Pointers + Skip Non-Alnum

```java
public boolean isPalindrome(String s) {
    int left = 0, right = s.length() - 1;

    while (left < right) {
        while (left < right && !Character.isLetterOrDigit(s.charAt(left))) left++;
        while (left < right && !Character.isLetterOrDigit(s.charAt(right))) right--;

        if (Character.toLowerCase(s.charAt(left)) != Character.toLowerCase(s.charAt(right))) {
            return false;
        }

        left++;
        right--;
    }

    return true;
}
```

**Time Complexity**: O(n)  
**Space Complexity**: O(1)

## Key Insights
- Process in-place; no cleaned string needed
- Skip punctuation/spaces, compare lowercase chars

## Tips and Tricks
- State what each pointer represents and how movement changes the invariant.
- If the array is sorted, use pointer movement to eliminate search space instead of nested loops.
- Handle duplicates explicitly when the problem asks for unique answers.

## Related Problems
- LC 680 Valid Palindrome II
