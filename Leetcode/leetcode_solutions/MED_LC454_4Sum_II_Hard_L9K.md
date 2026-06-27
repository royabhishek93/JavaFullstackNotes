# LC 454: 4Sum II

**Link**: [leetcode.com/problems/4sum-ii](https://leetcode.com/problems/4sum-ii/)

## Problem
Given four integer arrays A, B, C, D of equal length, return the number of tuples (i, j, k, l) such that A[i] + B[j] + C[k] + D[l] == 0.

### Examples
- Input: A = [1,2], B = [-2,-1], C = [-1,2], D = [0,2]
  → Output: 2
  Explanation: 
  - (0, 0, 0, 1): A[0] + B[0] + C[0] + D[1] = 1 + (-2) + (-1) + 2 = 0
  - (1, 1, 0, 0): A[1] + B[1] + C[0] + D[0] = 2 + (-1) + (-1) + 0 = 0

- Input: A = [0], B = [0], C = [0], D = [0]
  → Output: 1

## Optimized Approach: HashMap on Split Arrays

```java
public int fourSumCount(int[] A, int[] B, int[] C, int[] D) {
    // Step 1: Store all sums from first two arrays (A + B)
    // Key = sum, Value = count of how many ways to make that sum
    Map<Integer, Integer> sumCount = new HashMap<>();
    for (int a : A) {
        for (int b : B) {
            int sumAB = a + b;
            sumCount.put(sumAB, sumCount.getOrDefault(sumAB, 0) + 1);
        }
    }

    // Step 2: Iterate through remaining arrays (C + D)
    // Find complements in the HashMap
    int result = 0;
    for (int c : C) {
        for (int d : D) {
            // We need: A[i] + B[j] + C[k] + D[l] == 0
            // So: A[i] + B[j] == -(C[k] + D[l])
            int sumCD = c + d;
            int complement = -sumCD;

            // Count how many (A+B) combinations make this complement
            result += sumCount.getOrDefault(complement, 0);
        }
    }

    return result;
}
```

**Time Complexity**: O(n²) - O(n²) for building map + O(n²) for searching  
**Space Complexity**: O(n²) - HashMap stores up to n² pairs

## Key Insights
- **Divide and Conquer**: Split 4 arrays into two groups of 2
- **HashMap as Counter**: Store counts of pair sums, not just existence
- **Complement Search**: For each CD pair, find how many AB pairs sum to -(CD)
- **Order Independence**: Order of checking A,B vs C,D doesn't matter
- **Count collisions**: Use getOrDefault to handle duplicate sums

## Interview Walkthrough
1. **Problem**: Count 4-tuples where sum of one element from each array = 0
2. **Brute Force**: "4 nested loops would be O(n⁴) - too slow"
3. **Optimization Insight**: "Split into two groups: (A+B) and (C+D)"
4. **Strategy**:
   - Build HashMap: map[a+b] = count of ways to make (a+b)
   - For each (c,d), check if complement -(c+d) exists
   - Add count to result
5. **Example**: A=[1,2], B=[-2,-1], C=[-1,2], D=[0,2]
   ```
   AB sums map:
   - 1+(-2) = -1
   - 1+(-1) = 0
   - 2+(-2) = 0
   - 2+(-1) = 1
   
   Map: {-1: 1, 0: 2, 1: 1}
   
   For CD pairs:
   - C[0]+D[0] = -1+0 = -1, need 1 → found 1 (from 2+(-1))
   - C[0]+D[1] = -1+2 = 1, need -1 → found 1 (from 1+(-2))
   - C[1]+D[0] = 2+0 = 2, need -2 → found 0
   - C[1]+D[1] = 2+2 = 4, need -4 → found 0
   
   Result: 2
   ```

## Why This Approach (Optimal)
- ✅ **O(n²) time**: Only 2 nested loops vs 4
- ✅ **Practical**: Reduces 4-sum to manageable problem
- ✅ **Scalable**: Same approach works for any even number of arrays
- ⚠️ **Space-heavy**: O(n²) HashMap for storing pair sums

## Critical Details
- **Use getOrDefault**: Handle missing keys gracefully
- **Count, not check**: Use Integer count, not Boolean
- **Negative complement**: If we want sum=0, complement of (c+d) is -(c+d)
- **Duplicate sums matter**: Multiple (a,b) pairs may sum to same value

## Common Mistakes
- Forgetting to negate the complement (should be -sumCD, not sumCD)
- Using simple HashMap.get() instead of getOrDefault() → NullPointerException
- Thinking HashMap stores single values (should store counts for duplicates)
- Starting result at 0 and not incrementing properly
- Missing that order of split doesn't matter (could also do (C+D) map, then search (A+B))

## Tips and Tricks
- "Brute force O(n⁴) won't work - need to optimize"
- "Split into two groups - each group has n² pairs"
- "Use HashMap to store sums from first group with their frequencies"
- "Search second group for complements, adding counts to result"
- "This technique works for any even number of arrays"

## Variations
- **LC 18**: 4Sum (with specific target, return unique quads)
- **LC 15**: 3Sum (extension of 2Sum with sorting)
- **Extension**: kSum with 2k arrays (divide into k groups of 2)
