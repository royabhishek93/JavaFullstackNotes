# LC 57: Insert Interval

**Link**: [leetcode.com/problems/insert-interval](https://leetcode.com/problems/insert-interval/)

## Problem
Given non-overlapping intervals sorted by start time, insert a new interval and merge if needed.

## Optimized Approach: Linear Merge Scan

```java
public int[][] insert(int[][] intervals, int[] newInterval) {
    List<int[]> result = new ArrayList<>();
    int i = 0;

    while (i < intervals.length && intervals[i][1] < newInterval[0]) {
        result.add(intervals[i++]);
    }

    while (i < intervals.length && intervals[i][0] <= newInterval[1]) {
        newInterval[0] = Math.min(newInterval[0], intervals[i][0]);
        newInterval[1] = Math.max(newInterval[1], intervals[i][1]);
        i++;
    }
    result.add(newInterval);

    while (i < intervals.length) {
        result.add(intervals[i++]);
    }

    return result.toArray(new int[result.size()][]);
}
```

**Time Complexity**: O(n)  
**Space Complexity**: O(n)

## Tips and Tricks
- Sorting order determines correctness for most interval problems.
- Merge or selection logic should be expressed in terms of overlap conditions.
- Always test touching boundaries like [1,4] and [4,5] according to the problem definition.

## Related Problems
- LC 56 Merge Intervals
