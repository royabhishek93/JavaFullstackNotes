# LC 118: Pascal's Triangle

**Link**: [leetcode.com/problems/pascals-triangle](https://leetcode.com/problems/pascals-triangle/)

## Problem
Given an integer `numRows`, return the first `numRows` of Pascal's triangle.

## Optimized Approach: Build Row-by-Row

```java
public List<List<Integer>> generate(int numRows) {
    List<List<Integer>> result = new ArrayList<>();

    for (int i = 0; i < numRows; i++) {
        List<Integer> row = new ArrayList<>();
        row.add(1);

        List<Integer> prev = i > 0 ? result.get(i - 1) : null;
        for (int j = 1; j < i; j++) {
            row.add(prev.get(j - 1) + prev.get(j));
        }

        if (i > 0) row.add(1);
        result.add(row);
    }

    return result;
}
```

**Time Complexity**: O(numRows^2)  
**Space Complexity**: O(numRows^2)

## Key Insights
- Each inner element is sum of two elements directly above
- First and last elements of every row are always 1

## Tips and Tricks
- Define the DP state in one sentence before writing transitions.
- Initialize base cases carefully because most DP bugs come from wrong starting values.
- Check whether the transition depends on previous row, previous column, or previous index only.

## Related Problems
- LC 119 Pascal's Triangle II
