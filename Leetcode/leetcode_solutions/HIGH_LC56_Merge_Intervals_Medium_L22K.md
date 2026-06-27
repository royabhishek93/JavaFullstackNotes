# LC 56: Merge Intervals

**Link**: [leetcode.com/problems/merge-intervals](https://leetcode.com/problems/merge-intervals/)

## Problem
Given an array of intervals where intervals[i] = [starti, endi], merge all overlapping intervals, and return an array of the non-overlapping intervals that cover all the intervals in the input.

### Examples
- Input: intervals = [[1,3],[2,6],[8,10],[15,18]] → Output: [[1,6],[8,10],[15,18]]
- Input: intervals = [[1,4],[4,5]] → Output: [[1,5]]
- Input: intervals = [[0,0]] → Output: [[0,0]]

## Optimized Approach: Sort + Greedy Merge

```java
public int[][] merge(int[][] intervals) {
    if (intervals == null || intervals.length == 0) {
        return new int[0][0];
    }

    // Sort by start time
    Arrays.sort(intervals, (a, b) -> a[0] - b[0]);

    List<int[]> merged = new ArrayList<>();
    int[] current = intervals[0];

    for (int i = 1; i < intervals.length; i++) {
        int[] next = intervals[i];

        if (next[0] <= current[1]) {
            // Overlapping: extend current interval
            current[1] = Math.max(current[1], next[1]);
        } else {
            // Non-overlapping: save current, start new
            merged.add(current);
            current = next;
        }
    }

    // Don't forget last interval
    merged.add(current);

    return merged.toArray(new int[merged.size()][]);
}
```

**Time Complexity**: O(n log n) - sorting dominates  
**Space Complexity**: O(1) or O(n) for output

## Key Insights
- **Sort essential**: By start time to check overlaps sequentially
- **Overlap check**: next[0] <= current[1]
- **Merge**: Take max end point
- **Greedy works**: Always merge overlapping intervals optimally

## Interview Walkthrough
1. **Problem**: Merge all overlapping intervals
2. **Key insight**: Sort by start, then merge greedily
3. **Algorithm**:
   - Sort intervals by start time
   - Iterate and check overlap with current
   - If overlap, extend current's end
   - If not, save current and start new
4. **Example**: [[1,3],[2,6],[8,10],[15,18]]
   ```
   After sort: [[1,3],[2,6],[8,10],[15,18]]
   
   current=[1,3]
   Check [2,6]: 2<=3? YES → extend to [1,6]
   Check [8,10]: 8<=6? NO → save [1,6], current=[8,10]
   Check [15,18]: 15<=10? NO → save [8,10], current=[15,18]
   Save [15,18]
   Result: [[1,6],[8,10],[15,18]]
   ```

## Why This Approach (Optimal)
- ✅ **O(n log n) time**: Sorting is necessary
- ✅ **Greedy works**: Always best to merge overlapping
- ✅ **O(1) extra space**: Modify in-place possible
- ✅ **Simple**: Clear logic

## Common Mistakes
- Forgetting to save last interval
- Wrong overlap condition (should be <=, not <)
- Not sorting first
- Modifying while iterating unsafely

## Tips and Tricks
- "Sort by start time first"
- "Check if next interval overlaps: next[0] <= current[1]"
- "If overlap, extend current end"
- "Remember: always add last interval after loop"

## Greedy Justification
```
After sorting, checking intervals in order:
If interval i and i+1 overlap, always merge
This is optimal: merges maximum overlaps
```

## Related Problems
- **LC 57**: Insert Interval (insert then merge)
- **LC 228**: Summary Ranges (similar logic)
- **LC 452**: Minimum Number of Arrows (similar greedy)
