# LC 74: Search a 2D Matrix

**Link**: [leetcode.com/problems/search-a-2d-matrix](https://leetcode.com/problems/search-a-2d-matrix/)

## Problem
Write an efficient algorithm that searches for a value target in an m x n integer matrix. Integers in each row are sorted from left to right. The first integer of each row is greater than the last integer of the previous row.

### Examples
- Input: matrix = [[1,3,5,7],[10,11,16,20],[23,24,25,29]], target = 13 → Output: false
- Input: matrix = [[1,3,5,7],[10,11,16,20],[23,24,25,29]], target = 13 → Output: false
- Input: matrix = [[1]], target = 1 → Output: true

## Optimized Approach: Binary Search on Flattened Index

```java
public boolean searchMatrix(int[][] matrix, int target) {
    if (matrix == null || matrix.length == 0) {
        return false;
    }

    int rows = matrix.length;
    int cols = matrix[0].length;

    int left = 0;
    int right = rows * cols - 1;

    while (left <= right) {
        int mid = left + (right - left) / 2;
        
        // Convert 1D index to 2D coordinates
        int row = mid / cols;
        int col = mid % cols;
        int midValue = matrix[row][col];

        if (midValue == target) {
            return true;
        } else if (midValue < target) {
            left = mid + 1;
        } else {
            right = mid - 1;
        }
    }

    return false;
}
```

**Time Complexity**: O(log(m*n)) - binary search  
**Space Complexity**: O(1) - only pointers

## Key Insights
- **Treat as 1D**: Flatten matrix logically using index conversion
- **Index conversion**: row = index / cols, col = index % cols
- **No actual array**: Conversion is O(1), no extra space
- **Sorted property**: Works because matrix is completely sorted

## Interview Walkthrough
1. **Problem**: Search in 2D matrix efficiently
2. **Observation**: Matrix is sorted as if it were one long 1D array
3. **Insight**: Can use binary search on flattened indices
4. **Conversion**: mid → (mid / cols, mid % cols)
5. **Example**: [[1,3,5,7],[10,11,16,20],[23,24,25,29]], target = 13
   ```
   rows=3, cols=4, total=12
   left=0, right=11, mid=5
   row=5/4=1, col=5%4=1
   matrix[1][1]=11 < 13
   left=6
   
   left=6, right=11, mid=8
   row=8/4=2, col=8%4=0
   matrix[2][0]=23 > 13
   right=7
   
   left=6, right=7, mid=6
   row=6/4=1, col=6%4=2
   matrix[1][2]=16 > 13
   right=5
   
   left=6 > right=5
   return false
   ```

## Why This Approach (Optimal)
- ✅ **O(log(m*n)) time**: Binary search
- ✅ **O(1) space**: Only pointers
- ✅ **Simple**: Converts 2D to 1D logically
- ✅ **Elegant**: No actual flattening needed

## Common Mistakes
- Wrong index conversion formula
- Trying to use nested loops (O(m+n), not O(log))
- Not converting correctly back to 2D
- Edge case: empty matrix

## Tips and Tricks
- "Flatten logically: treat as 1D sorted array"
- "Convert index: row = mid / cols, col = mid % cols"
- "Index conversion is O(1), no extra space"
- "Standard binary search after conversion"

## Alternative: Two Binary Searches
```java
// First find row using binary search
// Then find column using binary search
// More complex than index conversion
```

## Related Problems
- **LC 704**: Binary Search (1D version)
- **LC 240**: Search a 2D Matrix II (different property)
