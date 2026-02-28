# Q1: Maximum Length of Repeated Subarray (LeetCode 718)

**Study Time:** 8-10 minutes | **Frequency:** 65% in interviews 🔥 | **Difficulty:** ⭐⭐⭐⭐

**LeetCode:** [Maximum Length of Repeated Subarray](https://leetcode.com/problems/maximum-length-of-repeated-subarray/)

---

## Problem Statement

Given two integer arrays `nums1` and `nums2`, return the **length of the longest common subarray** (must be contiguous).

### Examples

```
Example 1:
Input: nums1 = [1,2,3,2,1], nums2 = [3,2,1,4,7]
Output: 3
Explanation: The longest common subarray is [3,2,1]

Example 2:
Input: nums1 = [0,0,0,0,0], nums2 = [0,0,0,0,0]
Output: 5
Explanation: Both arrays are identical

Example 3:
Input: nums1 = [1,2,3], nums2 = [4,5,6]
Output: 0
Explanation: No common subarray
```

---

## Wrong Approaches

### ❌ WRONG Approach 1: Brute Force (O(n³))

```java
public int findLength(int[] nums1, int[] nums2) {
    int maxLength = 0;
    
    // Check every starting position in nums1
    for (int i = 0; i < nums1.length; i++) {
        // Check every length
        for (int len = 1; len <= nums1.length - i; len++) {
            // Check if this subarray exists in nums2
            boolean found = false;
            for (int j = 0; j <= nums2.length - len; j++) {
                boolean match = true;
                // Compare characters
                for (int k = 0; k < len; k++) {
                    if (nums1[i + k] != nums2[j + k]) {
                        match = false;
                        break;
                    }
                }
                if (match) {
                    found = true;
                    break;
                }
            }
            if (found) {
                maxLength = Math.max(maxLength, len);
            }
        }
    }
    
    return maxLength;
}

// Problems:
// - 4 nested loops: O(n³) or O(n⁴) in worst case
// - Times out on large inputs
// - Not optimal for interviews
```

---

### ❌ WRONG Approach 2: Using indexOf in substring

```java
public int findLength(int[] nums1, int[] nums2) {
    int maxLength = 0;
    
    for (int i = 0; i < nums1.length; i++) {
        for (int len = nums1.length - i; len >= 1; len--) {
            // Convert to string and use indexOf
            String sub1 = Arrays.toString(Arrays.copyOfRange(nums1, i, i + len));
            String sub2 = Arrays.toString(nums2);
            
            if (sub2.contains(sub1)) {
                return len;  // Found max immediately
            }
        }
    }
    
    return 0;
}

// Problems:
// - String conversion overhead
// - Still O(n³) due to contains() checking
// - Inefficient memory usage
// - Harder to understand the algorithm
```

---

## ✅ RIGHT Approach: Dynamic Programming

### Intuition

Use **DP** to build up solutions from smaller subproblems:
- `dp[i][j]` = length of common subarray ending at `nums1[i-1]` and `nums2[j-1]`
- If elements match: `dp[i][j] = dp[i-1][j-1] + 1`
- If elements don't match: `dp[i][j] = 0` (subarray broken)
- Track max length found

### Implementation

```java
public int findLength(int[] nums1, int[] nums2) {
    int m = nums1.length;
    int n = nums2.length;
    
    // dp[i][j] = length of common subarray ending at nums1[i-1], nums2[j-1]
    int[][] dp = new int[m + 1][n + 1];
    int maxLength = 0;
    
    // Fill DP table
    for (int i = 1; i <= m; i++) {
        for (int j = 1; j <= n; j++) {
            // If elements match, extend the previous subarray
            if (nums1[i - 1] == nums2[j - 1]) {
                dp[i][j] = dp[i - 1][j - 1] + 1;
                maxLength = Math.max(maxLength, dp[i][j]);
            }
            // If not match, reset (subarray is broken)
            // dp[i][j] stays 0 by default
        }
    }
    
    return maxLength;
}

// Complexity:
// Time: O(m * n) - fill m x n table
// Space: O(m * n) - DP table
```

---

## Step-by-Step Example

### Input
```
nums1 = [1, 2, 3, 2, 1]
nums2 = [3, 2, 1, 4, 7]
```

### DP Table Building

```
        ""  3  2  1  4  7
    ""  0   0  0  0  0  0
    1   0   0  0  0  0  0
    2   0   0  1  0  0  0
    3   0   1  0  1  0  0
    2   0   0  2  0  0  0
    1   0   0  0  3  0  0

Step-by-step:
i=1, j=1: nums1[0]=1, nums2[0]=3 → not match → dp[1][1]=0
i=1, j=2: nums1[0]=1, nums2[1]=2 → not match → dp[1][2]=0
i=1, j=3: nums1[0]=1, nums2[2]=1 → match! → dp[1][3]=dp[0][2]+1=1 ✓
i=2, j=1: nums1[1]=2, nums2[0]=3 → not match → dp[2][1]=0
i=2, j=2: nums1[1]=2, nums2[1]=2 → match! → dp[2][2]=dp[1][1]+1=1 ✓
i=2, j=3: nums1[1]=2, nums2[2]=1 → not match → dp[2][3]=0
i=3, j=1: nums1[2]=3, nums2[0]=3 → match! → dp[3][1]=dp[2][0]+1=1 ✓
i=3, j=2: nums1[2]=3, nums2[1]=2 → not match → dp[3][2]=0
i=3, j=3: nums1[2]=3, nums2[2]=1 → not match → dp[3][3]=0
i=4, j=1: nums1[3]=2, nums2[0]=3 → not match → dp[4][1]=0
i=4, j=2: nums1[3]=2, nums2[1]=2 → match! → dp[4][2]=dp[3][1]+1=2 ✓
i=4, j=3: nums1[3]=2, nums2[2]=1 → not match → dp[4][3]=0
i=5, j=1: nums1[4]=1, nums2[0]=3 → not match → dp[5][1]=0
i=5, j=2: nums1[4]=1, nums2[1]=2 → not match → dp[5][2]=0
i=5, j=3: nums1[4]=1, nums2[2]=1 → match! → dp[5][3]=dp[4][2]+1=3 ✓

maxLength = 3
Subarray: [3, 2, 1]
```

---

## Space Optimization

### Optimized to O(n) Space

```java
public int findLength(int[] nums1, int[] nums2) {
    // Only need current and previous row
    int[] prev = new int[nums2.length + 1];
    int[] curr = new int[nums2.length + 1];
    int maxLength = 0;
    
    for (int i = 1; i <= nums1.length; i++) {
        for (int j = 1; j <= nums2.length; j++) {
            if (nums1[i - 1] == nums2[j - 1]) {
                curr[j] = prev[j - 1] + 1;
                maxLength = Math.max(maxLength, curr[j]);
            }
        }
        // Swap rows
        int[] temp = prev;
        prev = curr;
        curr = temp;
        Arrays.fill(curr, 0);
    }
    
    return maxLength;
}

// Space: O(n) instead of O(m*n)
// Time: Still O(m*n)
```

---

## Complete Working Code

```java
public class MaxRepeatedSubarray {
    
    public int findLength(int[] nums1, int[] nums2) {
        int m = nums1.length;
        int n = nums2.length;
        int[][] dp = new int[m + 1][n + 1];
        int maxLength = 0;
        
        for (int i = 1; i <= m; i++) {
            for (int j = 1; j <= n; j++) {
                if (nums1[i - 1] == nums2[j - 1]) {
                    dp[i][j] = dp[i - 1][j - 1] + 1;
                    maxLength = Math.max(maxLength, dp[i][j]);
                }
            }
        }
        
        return maxLength;
    }
    
    public static void main(String[] args) {
        MaxRepeatedSubarray solution = new MaxRepeatedSubarray();
        
        // Test case 1
        int[] nums1 = {1, 2, 3, 2, 1};
        int[] nums2 = {3, 2, 1, 4, 7};
        System.out.println(solution.findLength(nums1, nums2));  // Output: 3
        
        // Test case 2
        int[] nums1_2 = {0, 0, 0, 0, 0};
        int[] nums2_2 = {0, 0, 0, 0, 0};
        System.out.println(solution.findLength(nums1_2, nums2_2));  // Output: 5
        
        // Test case 3
        int[] nums1_3 = {1, 2, 3};
        int[] nums2_3 = {4, 5, 6};
        System.out.println(solution.findLength(nums1_3, nums2_3));  // Output: 0
    }
}
```

---

## Interview Q&A

### Q1: "Why reset dp[i][j] to 0 when elements don't match?"

**Answer:**
```
The subarray MUST be contiguous.

If current elements don't match:
  → The continuous subarray is broken
  → We can't carry forward previous length
  → Must reset to 0

Example:
[1,2,3] and [1,2,4]
  → [1,2] match (length 2)
  → but [3] ≠ [4]
  → Can't say length is 3!
  → Reset and start fresh if match occurs again
```

---

### Q2: "Could we use sliding window instead?"

**Answer:**
```
No, sliding window works for different problems.

Sliding window: Good for subarrays with specific properties
  Example: "Find subarray with sum = k"
  Can shrink/expand window based on conditions

This problem: Need to match exact subarrays
  Must check all positions in both arrays
  DP is optimal

DP is better here because:
  - Need to compare ALL pairs of positions
  - Sliding window can't efficiently do this
```

---

### Q3: "What if arrays have negative numbers or duplicates?"

**Answer:**
```
Still works!

Algorithm doesn't care about values:
  - Only compares: nums1[i-1] == nums2[j-1]
  - Negative numbers: Still comparable
  - Duplicates: No problem [1,1,1] and [1,1,1] → returns 3

The algorithm is value-agnostic.
```

---

## Common Mistakes

```java
❌ MISTAKE 1: Forgetting to update maxLength in loop
for (int i = 1; i <= m; i++) {
    for (int j = 1; j <= n; j++) {
        if (nums1[i - 1] == nums2[j - 1]) {
            dp[i][j] = dp[i - 1][j - 1] + 1;
            // MISSING: maxLength = Math.max(maxLength, dp[i][j]);
        }
    }
}
// Would return 0 always!

✅ CORRECT: Update maxLength inside if block

❌ MISTAKE 2: Not handling 1-indexed DP
if (nums1[i] == nums2[j]) {  // Wrong indices!
    dp[i][j] = dp[i - 1][j - 1] + 1;
}

✅ CORRECT: Use i-1 and j-1 to access array
if (nums1[i - 1] == nums2[j - 1]) {
    dp[i][j] = dp[i - 1][j - 1] + 1;
}

❌ MISTAKE 3: Not initializing DP table
int[][] dp = new int[m][n];  // Should be m+1, n+1
// IndexOutOfBoundsException!

✅ CORRECT: 1-indexed to handle base case
int[][] dp = new int[m + 1][n + 1];
```

---

## Complexity Analysis

| Approach | Time | Space | Notes |
|----------|------|-------|-------|
| Brute Force | O(n⁴) | O(1) | Too slow, times out |
| DP (2D) | O(m*n) | O(m*n) | Optimal, interview best |
| DP (1D) | O(m*n) | O(n) | Space optimized |
| Suffix Array | O((m+n) log(m+n)) | O(m+n) | Advanced, overkill |

---

## Interview Answer

**Q: "Given two arrays, find the longest common subarray. Explain your approach."**

**Answer:**

> "I'll use dynamic programming because the subarray must be contiguous.
> 
> **Key insight:** I create a 2D DP table where `dp[i][j]` represents
> the length of the common subarray ending exactly at `nums1[i-1]` 
> and `nums2[j-1]`.
> 
> **Logic:**
> - If elements match: Extend previous subarray by 1: `dp[i][j] = dp[i-1][j-1] + 1`
> - If don't match: Reset to 0 (contiguity broken)
> - Track the maximum length seen
> 
> **Example:** nums1=[1,2,3,2,1], nums2=[3,2,1,4,7]
> When we find nums1[2]=3 matches nums2[0]=3, dp[3][1]=1
> When nums1[3]=2 matches nums2[1]=2, dp[4][2]=2
> When nums1[4]=1 matches nums2[2]=1, dp[5][3]=3 ✓
> 
> **Complexity:**
> - Time: O(m*n) - fill entire table
> - Space: O(m*n) - DP table
> - Can optimize space to O(n) if needed
> 
> **Code:** [implementation provided above]"

---

## Key Takeaways

| Concept | Why It Matters | Interview Score |
|---------|----------------|-----------------|
| **DP state definition** | Core of solution | ⭐⭐⭐⭐⭐ |
| **Resetting on mismatch** | Understanding contiguity | ⭐⭐⭐⭐ |
| **1-indexed DP table** | Handling base case | ⭐⭐⭐⭐ |
| **Space optimization** | Shows advanced thinking | ⭐⭐⭐ |
| **Why not sliding window** | Algorithm choice reasoning | ⭐⭐⭐⭐ |

