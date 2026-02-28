# Q3: Move Zeros to the Right (LeetCode 283)

**Study Time:** 5-7 minutes | **Frequency:** 75% in interviews 🔥 | **Difficulty:** ⭐⭐⭐

**LeetCode:** [Move Zeroes](https://leetcode.com/problems/move-zeroes/)

---

## Problem Statement

Given an integer array `nums`, move all zeros to the **end** while maintaining the **relative order** of non-zero elements. **Do this in-place** (don't create a new array).

### Examples

```
Example 1:
Input: nums = [0, 1, 0, 3, 12]
Output: [1, 3, 12, 0, 0]
Explanation: Zeros moved to end, non-zeros keep their relative order

Example 2:
Input: nums = [0]
Output: [0]
Explanation: Single zero stays

Example 3:
Input: nums = [1, 2, 3]
Output: [1, 2, 3]
Explanation: No zeros, array unchanged

Example 4:
Input: nums = [0, 0, 1]
Output: [1, 0, 0]
Explanation: All zeros moved to end
```

---

## Wrong Approaches

### ❌ WRONG Approach 1: Using Extra Space

```java
public void moveZeroes(int[] nums) {
    // Create new array with size
    List<Integer> result = new ArrayList<>();
    
    // Add all non-zeros
    for (int num : nums) {
        if (num != 0) {
            result.add(num);
        }
    }
    
    // Count zeros
    int zeros = nums.length - result.size();
    
    // Add zeros
    for (int i = 0; i < zeros; i++) {
        result.add(0);
    }
    
    // Copy back to original array
    for (int i = 0; i < result.size(); i++) {
        nums[i] = result.get(i);
    }
}

// Problems:
// - Uses extra space O(n) - interview asks for in-place!
// - Inefficient, unnecessary ArrayList operations
// - Violates constraint: "modify in-place"
```

---

### ❌ WRONG Approach 2: Swap with Every Zero

```java
public void moveZeroes(int[] nums) {
    // Find each zero and swap with non-zero
    for (int i = 0; i < nums.length; i++) {
        if (nums[i] == 0) {
            // Find next non-zero
            for (int j = i + 1; j < nums.length; j++) {
                if (nums[j] != 0) {
                    // Swap
                    int temp = nums[i];
                    nums[i] = nums[j];
                    nums[j] = temp;
                    break;
                }
            }
        }
    }
}

// Problems:
// - O(n²) worst case (all zeros except last element)
// - Inefficient nested loops
// - Works but far slower than optimal
```

---

## ✅ RIGHT Approach: Two-Pointer (Insertion Position)

### Intuition

Use two pointers:
- **insertPos:** Points to where the next non-zero should be placed
- **i:** Traverses the array

**Strategy:**
1. Scan the array
2. When we find a non-zero, place it at insertPos
3. Move insertPos forward
4. After scanning, fill remaining positions with zeros

```java
public void moveZeroes(int[] nums) {
    int insertPos = 0;
    
    // Step 1: Place all non-zeros at the front
    for (int i = 0; i < nums.length; i++) {
        if (nums[i] != 0) {
            nums[insertPos] = nums[i];
            insertPos++;
        }
    }
    
    // Step 2: Fill remaining positions with zeros
    while (insertPos < nums.length) {
        nums[insertPos] = 0;
        insertPos++;
    }
}

// Complexity:
// Time: O(n) - two simple passes
// Space: O(1) - only pointers, no extra data
```

---

## Step-by-Step Example

### Input
```
nums = [0, 1, 0, 3, 12]
```

### Step 1: Place Non-Zeros

```
Initial:        [0, 1, 0, 3, 12]
insertPos: 0

i=0: nums[0]=0, skip
     [0, 1, 0, 3, 12]
     
i=1: nums[1]=1 ≠ 0
     nums[0] = 1
     insertPos = 1
     [1, 1, 0, 3, 12]
     
i=2: nums[2]=0, skip
     [1, 1, 0, 3, 12]
     
i=3: nums[3]=3 ≠ 0
     nums[1] = 3
     insertPos = 2
     [1, 3, 0, 3, 12]
     
i=4: nums[4]=12 ≠ 0
     nums[2] = 12
     insertPos = 3
     [1, 3, 12, 3, 12]
```

### Step 2: Fill Remaining with Zeros

```
After step 1: [1, 3, 12, 3, 12]
insertPos: 3

insertPos=3: nums[3] = 0
             [1, 3, 12, 0, 12]
             
insertPos=4: nums[4] = 0
             [1, 3, 12, 0, 0]

Done!
```

---

## Optimized Version (Swap Instead of Two Passes)

```java
public void moveZeroes(int[] nums) {
    int insertPos = 0;
    
    for (int i = 0; i < nums.length; i++) {
        if (nums[i] != 0) {
            // Swap if not at insertPos (only when needed)
            if (i != insertPos) {
                int temp = nums[i];
                nums[i] = nums[insertPos];
                nums[insertPos] = temp;
            }
            insertPos++;
        }
    }
}

// Benefits:
// - Only one pass (not two)
// - Same O(n) time but fewer operations
// - Avoids unnecessary assignments
// - Maintains relative order automatically
```

### Example with Swap Optimization

```
nums = [0, 1, 0, 3, 12]

i=0: nums[0]=0, skip

i=1: nums[1]=1 ≠ 0, insertPos=0
     i ≠ insertPos, so swap nums[1] and nums[0]
     [1, 0, 0, 3, 12]
     insertPos = 1

i=2: nums[2]=0, skip

i=3: nums[3]=3 ≠ 0, insertPos=1
     i ≠ insertPos, so swap nums[3] and nums[1]
     [1, 3, 0, 0, 12]
     insertPos = 2

i=4: nums[4]=12 ≠ 0, insertPos=2
     i ≠ insertPos, so swap nums[4] and nums[2]
     [1, 3, 12, 0, 0]
     insertPos = 3

Done in one pass!
```

---

## Complete Working Code

```java
public class MoveZeroes {
    
    // Approach 1: Two-pointer with two passes
    public void moveZeroes_TwoPasses(int[] nums) {
        int insertPos = 0;
        
        // Place all non-zeros
        for (int i = 0; i < nums.length; i++) {
            if (nums[i] != 0) {
                nums[insertPos] = nums[i];
                insertPos++;
            }
        }
        
        // Fill zeros
        while (insertPos < nums.length) {
            nums[insertPos] = 0;
            insertPos++;
        }
    }
    
    // Approach 2: Two-pointer with swap (optimized, one pass)
    public void moveZeroes_Swap(int[] nums) {
        int insertPos = 0;
        
        for (int i = 0; i < nums.length; i++) {
            if (nums[i] != 0) {
                if (i != insertPos) {
                    int temp = nums[i];
                    nums[i] = nums[insertPos];
                    nums[insertPos] = temp;
                }
                insertPos++;
            }
        }
    }
    
    // Test helper
    private static void printArray(int[] arr) {
        System.out.println(Arrays.toString(arr));
    }
    
    public static void main(String[] args) {
        MoveZeroes solution = new MoveZeroes();
        
        // Test case 1
        int[] nums1 = {0, 1, 0, 3, 12};
        solution.moveZeroes_Swap(nums1);
        printArray(nums1);  // Output: [1, 3, 12, 0, 0]
        
        // Test case 2
        int[] nums2 = {0};
        solution.moveZeroes_Swap(nums2);
        printArray(nums2);  // Output: [0]
        
        // Test case 3
        int[] nums3 = {1, 2, 3};
        solution.moveZeroes_Swap(nums3);
        printArray(nums3);  // Output: [1, 2, 3]
        
        // Test case 4
        int[] nums4 = {0, 0, 1};
        solution.moveZeroes_Swap(nums4);
        printArray(nums4);  // Output: [1, 0, 0]
        
        // Test case 5: All zeros
        int[] nums5 = {0, 0, 0};
        solution.moveZeroes_Swap(nums5);
        printArray(nums5);  // Output: [0, 0, 0]
        
        // Test case 6: No zeros
        int[] nums6 = {1, 2, 3, 4};
        solution.moveZeroes_Swap(nums6);
        printArray(nums6);  // Output: [1, 2, 3, 4]
    }
}
```

---

## Interview Q&A

### Q1: "Why use insertPos instead of just swapping with zeros?"

**Answer:**
```
Swapping doesn't work efficiently:

❌ Bad approach: Swap with zeros
for (int i = 0; i < nums.length; i++) {
    if (nums[i] == 0) {
        for (int j = i + 1; j < nums.length; j++) {
            if (nums[j] != 0) {
                swap(i, j);
                break;
            }
        }
    }
}
Worst case: O(n²) if array is [0,0,0,...,0,1]

✅ Good approach: insertPos pointer
Track where to place next non-zero
Place each non-zero once, fill zeros after
O(n) guaranteed
```

---

### Q2: "Why is the swap optimization important?"

**Answer:**
```
Two-pass approach:
  1. Move all non-zeros forward
  2. Fill remaining with zeros
  Works fine, clear logic O(n)

Swap optimization:
  1. Move non-zeros with swap only when needed
  Fewer write operations

Trade-off:
  - Two-pass: clearer logic, more writes
  - Swap: fewer writes, slightly harder to understand

Both O(n), swap is slightly more efficient in practice.
Use whichever is clearer in interview.
```

---

### Q3: "What if we need to preserve relative order of zeros too?"

**Answer:**
```
Current algorithm already maintains relative order!

Example:
[0, 1, 0, 2, 0, 3]
     ↓
[1, 2, 3, 0, 0, 0]

Non-zeros [1, 2, 3] maintain their order
Zeros stay together at end

Actually, any in-place solution moving items forward
naturally maintains relative order.
```

---

### Q4: "How would you modify this to move zeros to the left instead?"

**Answer:**
```
Mirror the logic:

public void moveZeroesLeft(int[] nums) {
    int insertPos = nums.length - 1;
    
    for (int i = nums.length - 1; i >= 0; i--) {
        if (nums[i] != 0) {
            nums[insertPos] = nums[i];
            insertPos--;
        }
    }
    
    while (insertPos >= 0) {
        nums[insertPos] = 0;
        insertPos--;
    }
}

Or with swap optimization:
public void moveZeroesLeft(int[] nums) {
    int insertPos = nums.length - 1;
    
    for (int i = nums.length - 1; i >= 0; i--) {
        if (nums[i] != 0) {
            if (i != insertPos) {
                int temp = nums[i];
                nums[i] = nums[insertPos];
                nums[insertPos] = temp;
            }
            insertPos--;
        }
    }
}
```

---

## Common Mistakes

```java
❌ MISTAKE 1: Modifying array while iterating backwards
for (int i = 0; i < nums.length; i++) {
    if (nums[i] == 0) {
        // Removing/shifting elements
        // This changes indices, breaks loop
    }
}

✅ CORRECT: Only read during iteration, write with pointers

❌ MISTAKE 2: Creating new array (violates in-place constraint)
int[] result = new int[nums.length];
// Copy non-zeros
// Copy zeros
// This uses extra O(n) space

✅ CORRECT: Modify original array with pointers

❌ MISTAKE 3: Not handling consecutive zeros
[0, 0, 1] → [1, 0, 0]
If only swap adjacent, loops forever

✅ CORRECT: Skip zeros entirely, jump insertPos
```

---

## Complexity Analysis

| Approach | Time | Space | Notes |
|----------|------|-------|-------|
| Extra Space | O(n) | O(n) | Violates constraint ❌ |
| Swap adjacent | O(n²) | O(1) | Too slow |
| Two-pointer (2 pass) | O(n) | O(1) | ✓ Optimal |
| Two-pointer (swap 1 pass) | O(n) | O(1) | ✓ Optimal & efficient |

---

## Interview Answer

**Q: "Move all zeros to the end in-place while maintaining order of non-zeros."**

**Answer:**

> "I'll use a **two-pointer** approach:
> 
> **Intuition:** Use one pointer (insertPos) to track where 
> the next non-zero element should be placed, and traverse 
> with another pointer (i) to find non-zero elements.
> 
> **Algorithm:**
> 1. Scan through array with pointer i
> 2. When we find a non-zero element, place it at insertPos
> 3. Increment insertPos
> 4. After scanning, fill remaining positions with zeros
> 
> **Example:** [0, 1, 0, 3, 12]
> - i moves through array, insertPos starts at 0
> - Skip nums[0]=0
> - Place nums[1]=1 at nums[0], insertPos=1
> - Skip nums[2]=0
> - Place nums[3]=3 at nums[1], insertPos=2
> - Place nums[4]=12 at nums[2], insertPos=3
> - Fill positions 3,4 with 0
> - Result: [1, 3, 12, 0, 0] ✓
> 
> **Complexity:**
> - Time: O(n) - two simple passes through array
> - Space: O(1) - in-place, only pointers
> 
> **Optimization:** Use swap if insertPos != i 
> to avoid unnecessary writes (still O(n) but fewer operations)"

---

## Key Takeaways

| Concept | Why It Matters | Interview Score |
|---------|----------------|-----------------|
| **In-place constraint** | Interview requirement | ⭐⭐⭐⭐⭐ |
| **Two-pointer pattern** | Core technique | ⭐⭐⭐⭐⭐ |
| **insertPos tracking** | Core of solution | ⭐⭐⭐⭐⭐ |
| **Why avoid swaps** | Efficiency | ⭐⭐⭐ |
| **Relative order** | Natural consequence | ⭐⭐⭐ |

