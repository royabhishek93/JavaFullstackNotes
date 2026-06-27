# LC 62: Unique Paths

**Link**: [leetcode.com/problems/unique-paths](https://leetcode.com/problems/unique-paths/)

## Problem
There is a robot on an m x n grid. The robot is initially at the top-left corner (0, 0) and tries to move to the bottom-right corner (m - 1, n - 1). The robot can only move right or down. How many unique paths exist?

### Examples
- Input: m = 3, n = 7 → Output: 28
- Input: m = 3, n = 2 → Output: 3 (right-right-down, right-down-right, down-right-right)
- Input: m = 1, n = 1 → Output: 1

## Optimized Approach: Dynamic Programming (Bottom-Up)

```java
public int uniquePaths(int m, int n) {
    // dp[i][j] = unique paths to reach (i, j)
    int[][] dp = new int[m][n];

    // Initialize: first row and column
    for (int i = 0; i < m; i++) {
        dp[i][0] = 1;  // Only one way down first column
    }
    for (int j = 0; j < n; j++) {
        dp[0][j] = 1;  // Only one way right first row
    }

    // Fill entire table
    for (int i = 1; i < m; i++) {
        for (int j = 1; j < n; j++) {
            // Can come from above or left
            dp[i][j] = dp[i - 1][j] + dp[i][j - 1];
        }
    }

    return dp[m - 1][n - 1];
}
```

**Space-Optimized (O(n)) - RECOMMENDED:**
```java
public int uniquePaths(int m, int n) {
    int[] dp = new int[n];
    Arrays.fill(dp, 1);  // Initialize first row: all 1s
    
    for (int i = 1; i < m; i++) {
        for (int j = 1; j < n; j++) {
            dp[j] = dp[j] + dp[j-1];
            // dp[j] (before update) = value from above (previous row)
            // dp[j-1] (already updated) = value from left (current row)
        }
    }
    
    return dp[n - 1];
}
```

**Time Complexity**: O(m*n)  
**Space Complexity**: O(m*n) or O(n) optimized

---

## 🎯 DETAILED STEP-BY-STEP EXPLANATION (Space-Optimized Solution)

### Problem Visualization
```
Grid: m=3 rows, n=4 columns
Goal: Count paths from START to END (only RIGHT or DOWN moves)

START → → → 
  ↓   ↓   ↓   ↓
  ↓   ↓   ↓   ↓
  ↓   ↓   ↓   END
```

### 🔑 KEY CONCEPT: Rolling Array Technique

**Important:** We only store ONE array with `n` elements, NOT the entire 2D grid!

The 2D grid shown below is what we COMPUTE (conceptually), but we only STORE one row at a time in memory.

```
What we COMPUTE (conceptual 2D grid):
     0   1   2   3
  ┌───┬───┬───┬───┐
0 │ 1 │ 1 │ 1 │ 1 │
  ├───┼───┼───┼───┤
1 │ 1 │ 2 │ 3 │ 4 │
  ├───┼───┼───┼───┤
2 │ 1 │ 3 │ 6 │10 │ ← Answer: 10 paths
  └───┴───┴───┴───┘

What we STORE (in memory):
dp[] array gets reused for each row:
  Initially:   [1, 1, 1, 1]  (Row 0)
  After Row 1: [1, 2, 3, 4]  (Row 0 overwritten!)
  After Row 2: [1, 3, 6, 10] (Row 1 overwritten!)
                       ↑
                   Answer = 10
```

---

### 📝 STEP-BY-STEP TRACE

#### **INITIALIZATION**
```java
int[] dp = new int[n];  // n=4
Arrays.fill(dp, 1);
```

**Memory State:**
```
dp = [1, 1, 1, 1]
     ↑  ↑  ↑  ↑
    Col0 Col1 Col2 Col3

Represents Row 0: [1, 1, 1, 1]
```
**Why all 1s?** First row has only 1 path to each cell (keep moving right).

---

#### **PROCESSING ROW 1** (i=1)

**Before processing:**
```
dp = [1, 1, 1, 1]  ← Contains Row 0 values
```

**Loop: for(int j=1; j<n; j++)**

##### j=1:
```java
dp[1] = dp[1] + dp[0]
      = 1     + 1      = 2
```
**Memory:**
```
dp = [1, 2, 1, 1]
      ↑  ↑
      │  └─ UPDATED: 1(above) + 1(left) = 2
      └─ First column stays 1 (not updated)
```

##### j=2:
```java
dp[2] = dp[2] + dp[1]
      = 1     + 2      = 3
```
**Memory:**
```
dp = [1, 2, 3, 1]
            ↑
            └─ UPDATED: 1(above) + 2(left) = 3
```

##### j=3:
```java
dp[3] = dp[3] + dp[2]
      = 1     + 3      = 4
```
**Memory:**
```
dp = [1, 2, 3, 4]  ← Now represents Row 1
               ↑
               └─ UPDATED: 1(above) + 3(left) = 4
```

**After Row 1 Complete:**
```
dp = [1, 2, 3, 4]  ← Row 0 is GONE, only Row 1 remains in memory
```

---

#### **PROCESSING ROW 2** (i=2)

**Before processing:**
```
dp = [1, 2, 3, 4]  ← Contains Row 1 values
```

##### j=1:
```java
dp[1] = dp[1] + dp[0]
      = 2     + 1      = 3
```
**Memory:**
```
dp = [1, 3, 3, 4]
      ↑  ↑
      │  └─ UPDATED: 2(above, old dp[1]) + 1(left) = 3
      └─ First column stays 1
```

**🔍 Important:** `dp[1]` had value 2 from Row 1, now becomes 3 for Row 2.

##### j=2:
```java
dp[2] = dp[2] + dp[1]
      = 3     + 3      = 6
```
**Memory:**
```
dp = [1, 3, 6, 4]
            ↑
            └─ UPDATED: 3(above, old dp[2]) + 3(left, NEW dp[1]) = 6
```

**🔍 Magic Moment:**
- `dp[2]` (before update) = 3 = value from Row 1 (above)
- `dp[1]` (already updated) = 3 = value from Row 2 (left)
- Result: Same as 2D formula `dp[i][j] = dp[i-1][j] + dp[i][j-1]`

##### j=3:
```java
dp[3] = dp[3] + dp[2]
      = 4     + 6      = 10
```
**Memory:**
```
dp = [1, 3, 6, 10]  ← Final answer!
               ↑
               └─ UPDATED: 4(above) + 6(left) = 10
```

**After Row 2 Complete:**
```
dp = [1, 3, 6, 10]  ← Only Row 2 remains in memory
                ↑
            Answer = 10 unique paths
```

---

### 🎯 WHY THIS WORKS: The Rolling Array Trick

```
Traditional 2D DP Formula:
dp[i][j] = dp[i-1][j] + dp[i][j-1]
           └─ above      └─ left

Space-Optimized 1D DP:
dp[j] = dp[j] + dp[j-1]
        │       └─ LEFT value (already updated in current row)
        └─ ABOVE value (old value from previous row, before update)
```

**Key Insight:**
When we process left-to-right:
1. `dp[j]` (right side, before assignment) still contains the OLD value from previous row = "above"
2. `dp[j-1]` was already updated in this iteration = "left"
3. We can safely overwrite `dp[j]` with the new value!

**Example for dp[2] in Row 2:**
```
Before: dp = [1, 3, 3, 4]
                  ↑  ↑
                  │  └─ dp[2] = 3 (from Row 1, "above")
                  └──── dp[1] = 3 (just updated, "left")

Calculation: dp[2] = 3 + 3 = 6

After:  dp = [1, 3, 6, 4]
                    ↑
                   Updated!
```

---

### 💾 MEMORY EFFICIENCY COMPARISON

**2D Approach (Naive):**
```java
int[][] dp = new int[m][n];  
// Space: O(m × n)
// For m=3, n=4: stores 12 numbers
```

**1D Optimized Approach (Your Code):**
```java
int[] dp = new int[n];
// Space: O(n)
// For m=3, n=4: stores only 4 numbers!
// 3x less memory usage!
```

---

### 🎓 FINAL RETURN

```java
return dp[n-1];  // dp[3] = 10
```

We return the **last element** which contains the number of paths to the **bottom-right corner** (destination).

## Key Insights
- **Movement constraints**: Only right or down
- **DP state**: dp[i][j] = ways to reach cell (i,j)
- **Recurrence**: dp[i][j] = dp[i-1][j] + dp[i][j-1]
- **Base case**: First row and column all 1

## Interview Walkthrough
1. **Problem**: Count paths from top-left to bottom-right
2. **Constraints**: Only right (R) or down (D) moves
3. **DP insight**: Paths = paths from above + paths from left
4. **Example**: 3x2 grid
   ```
   dp[0][0]=1, dp[0][1]=1
   dp[1][0]=1, dp[2][0]=1
   
   dp[1][1] = dp[0][1] + dp[1][0] = 1 + 1 = 2
   dp[2][1] = dp[1][1] + dp[2][0] = 2 + 1 = 3
   
   Paths: RDD, DRD, DDR
   ```

## Why This Approach (Optimal)
- ✅ **O(m*n) time**: Fill grid once
- ✅ **O(n) space**: Space-optimized with single row
- ✅ **Simple**: Clear DP transition
- ✅ **Correct**: Covers all possibilities

## Combinatorial Insight
```
Total moves = m-1 down + n-1 right = m+n-2
Choose which m-1 are down (rest are right)
Answer = C(m+n-2, m-1) = (m+n-2)! / ((m-1)!(n-1)!)
```

## Common Mistakes
- Wrong DP transition
- Not initializing first row/column
- Off-by-one in array indexing
- Forgetting to add both sources

## Tips and Tricks
- "DP[i][j] = ways to reach cell i,j"
- "Can only come from above or left"
- "First row and column are base cases (all 1)"
- "Space optimization: only need previous row"

## Related Problems
- **LC 63**: Unique Paths II (with obstacles)
- **LC 64**: Minimum Path Sum (different goal)
- **LC 174**: Dungeon Game (harder variant)
