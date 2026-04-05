# LC 35: Search Insert Position

**Link**: [leetcode.com/problems/search-insert-position](https://leetcode.com/problems/search-insert-position/)

## Problem
Given a sorted array and a target value, return the index if the target is found. If not, return the index where it would be if it were inserted in order. You must write an algorithm with O(log n) runtime complexity.

### Examples
- Input: nums = [1,3,5,6], target = 5 → Output: 2
- Input: nums = [1,3,5,6], target = 2 → Output: 1 (insert at index 1)
- Input: nums = [1,3,5,6], target = 7 → Output: 4 (insert at end)
- Input: nums = [1,3,5,6], target = 0 → Output: 0 (insert at start)

## Optimized Approach: Standard Binary Search (Left Pointer is Answer)

```java
public int searchInsert(int[] nums, int target) {
    int left = 0, right = nums.length - 1;

    while (left <= right) {
        int mid = left + (right - left) / 2;

        if (nums[mid] == target) {
            return mid;  // Found
        } else if (nums[mid] < target) {
            left = mid + 1;
        } else {
            right = mid - 1;
        }
    }

    // Not found: left pointer is insertion point
    return left;
}
```

**Time Complexity**: O(log n)  
**Space Complexity**: O(1)

## Key Insights
- **Standard binary search with twist**: When not found, return left
- **Why left is correct**: At end of loop, left > right
  - left points to first element >= target
  - If target > all elements, left = length
  - If target < all elements, left = 0
- **Guaranteed correctness**: Binary search invariant maintains this

## Interview Walkthrough
1. **Problem**: Find index or insertion position (simple!)
2. **Insight**: Standard binary search works
3. **Extra piece**: When not found, left is insertion point
4. **Why**: Binary search guarantees left > right at end
   - left is where we need to insert
5. **Examples**:
   ```
   [1,3,5,6], target=2: 
   left=0,right=3,mid=1 → nums[1]=3>2, right=0
   left=0,right=0,mid=0 → nums[0]=1<2, left=1
   Loop ends with left=1
   return 1 ✓
   
   [1,3,5,6], target=7:
   left=0,right=3,mid=1 → nums[1]=3<7, left=2
   ... search continues
   Eventually left=4 (past end)
   return 4 ✓
   ```

## Why This Approach (Optimal)
- ✅ **O(log n) time**: Binary search
- ✅ **O(1) space**: Only pointers
- ✅ **Simple**: Reuses binary search
- ✅ **Elegant**: Left pointer naturally gives insertion point

## Common Mistakes
- Returning wrong value when not found
- Confusion about left vs right at end
- Off-by-one when target > all or < all
- Overthinking (it's just binary search!)

## Tips and Tricks
- "Just standard binary search"
- "The trick: when not found, left IS the insertion point"
- "Binary search guarantees this property naturally"
- "Test edge cases: before all, after all, in middle"

## Binary Search Pattern
```
After loop with left > right:
- left = insertion point (first >= target)
- right = last < target position
```

## Related Problems
- **LC 704**: Binary Search (basic)
- **LC 34**: Find First and Last Position
- **LC 33**: Search in Rotated Sorted Array
