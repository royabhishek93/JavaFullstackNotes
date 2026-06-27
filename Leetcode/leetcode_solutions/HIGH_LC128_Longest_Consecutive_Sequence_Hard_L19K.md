# LC 128: Longest Consecutive Sequence

**Link**: [leetcode.com/problems/longest-consecutive-sequence](https://leetcode.com/problems/longest-consecutive-sequence/)

## Problem
Given an unsorted array of integers `nums`, return the length of the longest consecutive elements sequence.

## Optimized Approach: HashSet (Start-from-Sequence-Head)

```java
public int longestConsecutive(int[] nums) {
    Set<Integer> set = new HashSet<>();
    for (int num : nums) set.add(num);

    int best = 0;
    for (int num : set) {
        // Only start counting from sequence head
        if (!set.contains(num - 1)) {
            int current = num;
            int len = 1;

            while (set.contains(current + 1)) {
                current++;
                len++;
            }

            best = Math.max(best, len);
        }
    }

    return best;
}
```

**Time Complexity**: O(n) average  
**Space Complexity**: O(n)

## Key Insights
- Avoid recounting by only expanding numbers that have no predecessor
- HashSet gives O(1) average membership check

## Tips and Tricks
- Use hashing when constant-time membership or frequency lookup matters more than order.
- Be explicit about what the key represents: value, index relation, or prefix state.
- Frequency maps and prefix maps solve many array problems that look quadratic at first.

## Related Problems
- LC 217 Contains Duplicate
