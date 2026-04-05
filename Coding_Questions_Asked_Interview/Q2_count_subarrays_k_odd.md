# Q2: Count Subarrays with K Odd Numbers (LeetCode 1248)

**Study Time:** 10-12 minutes | **Frequency:** 60% in interviews 🔥 | **Difficulty:** ⭐⭐⭐⭐⭐

**LeetCode:** [Count Subarrays With K Odd Numbers](https://leetcode.com/problems/count-subarrays-with-k-odd-numbers/)

---

## Problem Statement

Given an array `nums` and an integer `k`, return the **number of subarrays** that contain exactly `k` odd numbers.

### Examples

```
Example 1:
Input: nums = [1,1,2,1,1], k = 3
Output: 2
Explanation: Subarrays [1,1,2,1,1] and [1,1,2,1,1] have exactly 3 odd numbers
             (indices 0-4 and 1-4)

Example 2:
Input: nums = [2,4,6], k = 1
Output: 0
Explanation: No subarray has exactly 1 odd number (all are even)

Example 3:
Input: nums = [1,2,1,2,1], k = 2
Output: 2
Explanation: Subarrays [1,2,1] and [2,1,2,1] have exactly 2 odd numbers
```

---

## Wrong Approaches

### ❌ WRONG Approach 1: Brute Force O(n²)

```java
public int numberOfSubarrays(int[] nums, int k) {
    int count = 0;
    
    // Check every subarray
    for (int i = 0; i < nums.length; i++) {
        int oddCount = 0;
        
        for (int j = i; j < nums.length; j++) {
            // Count odds in this subarray
            if (nums[j] % 2 == 1) {
                oddCount++;
            }
            
            // If exactly k odds, increment count
            if (oddCount == k) {
                count++;
            }
            
            // Early termination if too many odds
            if (oddCount > k) {
                break;
            }
        }
    }
    
    return count;
}

// Time: O(n²)
// Space: O(1)
// Problems:
// - Too slow for large arrays (10^5 elements)
// - Interview expects O(n) solution
```

---

### ❌ WRONG Approach 2: Using HashMap (Still O(n²) Worst Case)

```java
public int numberOfSubarrays(int[] nums, int k) {
    Map<Integer, Integer> oddCountMap = new HashMap<>();
    oddCountMap.put(0, 1);  // Base case
    
    int count = 0;
    int oddsSoFar = 0;
    
    for (int num : nums) {
        if (num % 2 == 1) {
            oddsSoFar++;
        }
        
        // Count subarrays with exactly k odds
        if (oddCountMap.containsKey(oddsSoFar - k)) {
            count += oddCountMap.get(oddsSoFar - k);
        }
        
        oddCountMap.put(oddsSoFar, oddCountMap.getOrDefault(oddsSoFar, 0) + 1);
    }
    
    return count;
}

// While this is O(n) and works, it's not the sliding window approach
// Interviews often expect sliding window for "count of subarrays" problems
```

---

## ✅ RIGHT Approach: Sliding Window (atMost Technique)

### Intuition

Use the **"atMost" technique**:
- Count subarrays with **at most k** odd numbers
- Count subarrays with **at most k-1** odd numbers
- Subtract: `atMost(k) - atMost(k-1)` = **exactly k** odd numbers

Why? Because:
```
atMost(k) includes:
  - Subarrays with 0 odds
  - Subarrays with 1 odd
  - ...
  - Subarrays with k odds

atMost(k-1) includes:
  - Subarrays with 0 odds
  - ...
  - Subarrays with k-1 odds

Difference = only subarrays with exactly k odds!
```

### Implementation

```java
public int numberOfSubarrays(int[] nums, int k) {
    return atMost(nums, k) - atMost(nums, k - 1);
}

private int atMost(int[] nums, int k) {
    int left = 0;
    int count = 0;  // Current odd count
    int result = 0; // Total subarrays
    
    for (int right = 0; right < nums.length; right++) {
        // If current element is odd, decrement k
        if (nums[right] % 2 == 1) {
            k--;
        }
        
        // Shrink window if odd count exceeds k
        while (k < 0) {
            if (nums[left] % 2 == 1) {
                k++;
            }
            left++;
        }
        
        // All subarrays ending at right with at most k odds
        // Window is [left...right], so:
        // subarrays ending at right: [left...right], [left+1...right], ..., [right...right]
        // Total: right - left + 1
        result += right - left + 1;
    }
    
    return result;
}

// Complexity:
// Time: O(n) - left and right pointers each traverse once
// Space: O(1) - only pointers
```

---

## Step-by-Step Example

### Input
```
nums = [1, 1, 2, 1, 1], k = 3
```

### Calculate atMost(3)

```
Finding subarrays with AT MOST 3 odd numbers

left=0, right=0: nums[0]=1 (odd) → k=2 → result += 0-0+1 = 1
                 subarrays: [1]

left=0, right=1: nums[1]=1 (odd) → k=1 → result += 1-0+1 = 3
                 subarrays: [1,1], [1], [1]  (Wait, this counts [1,1] from position 0-1)

left=0, right=2: nums[2]=2 (even) → k=1 → result += 2-0+1 = 6
                 subarrays: [1,1,2], [1,2], [2]

left=0, right=3: nums[3]=1 (odd) → k=0 → result += 3-0+1 = 10
                 subarrays: [1,1,2,1], [1,2,1], [2,1], [1]

left=0, right=4: nums[4]=1 (odd) → k=-1
                 k < 0, so SHRINK:
                 nums[0]=1 (odd) → k=0, left=1
                 result += 4-1+1 = 14

Final atMost(3) = 14
```

### Calculate atMost(2)

```
Finding subarrays with AT MOST 2 odd numbers

left=0, right=0: nums[0]=1 (odd) → k=1 → result += 0-0+1 = 1
left=0, right=1: nums[1]=1 (odd) → k=0 → result += 1-0+1 = 3
left=0, right=2: nums[2]=2 (even) → k=0 → result += 2-0+1 = 6
left=0, right=3: nums[3]=1 (odd) → k=-1
                 nums[0]=1 (odd) → k=0, left=1
                 result += 3-1+1 = 9
left=1, right=4: nums[4]=1 (odd) → k=-1
                 nums[1]=1 (odd) → k=0, left=2
                 result += 4-2+1 = 12

Final atMost(2) = 12
```

### Answer
```
atMost(3) - atMost(2) = 14 - 12 = 2 ✓
```

---

## Detailed Window Logic

```
The key insight:

When window is [left...right]:
  - It contains subarrays ending at right:
    * [left, right]
    * [left+1, right]
    * [left+2, right]
    * ...
    * [right, right]
  
  - Total count: right - left + 1

Why this works:
  Every subarray starting from any position 
  between left and right, ending at right,
  has at most k odd numbers (because left pointer
  ensures we don't exceed k).
```

---

## Complete Working Code

```java
public class CountSubarraysKOdds {
    
    public int numberOfSubarrays(int[] nums, int k) {
        return atMost(nums, k) - atMost(nums, k - 1);
    }
    
    private int atMost(int[] nums, int k) {
        int left = 0;
        int result = 0;
        
        for (int right = 0; right < nums.length; right++) {
            // Count odd numbers
            if (nums[right] % 2 == 1) {
                k--;
            }
            
            // Shrink window if too many odds
            while (k < 0) {
                if (nums[left] % 2 == 1) {
                    k++;
                }
                left++;
            }
            
            // Add all subarrays ending at right
            result += right - left + 1;
        }
        
        return result;
    }
    
    public static void main(String[] args) {
        CountSubarraysKOdds solution = new CountSubarraysKOdds();
        
        // Test case 1
        int[] nums1 = {1, 1, 2, 1, 1};
        System.out.println(solution.numberOfSubarrays(nums1, 3));  // Output: 2
        
        // Test case 2
        int[] nums2 = {2, 4, 6};
        System.out.println(solution.numberOfSubarrays(nums2, 1));  // Output: 0
        
        // Test case 3
        int[] nums3 = {1, 2, 1, 2, 1};
        System.out.println(solution.numberOfSubarrays(nums3, 2));  // Output: 2
        
        // Test case 4: All odds
        int[] nums4 = {1, 1, 1, 1};
        System.out.println(solution.numberOfSubarrays(nums4, 2));  // Output: 3
    }
}
```

---

## Interview Q&A

### Q1: "Why use atMost(k) - atMost(k-1) instead of direct counting?"

**Answer:**
```
Direct counting is harder:
  - Need to track when we reach exactly k
  - Hard to know when to include/exclude boundaries

"atMost" technique is cleaner:
  - atMost(k) is easy: expand window while ≤k
  - atMost(k-1) is same logic, different boundary
  - Difference gives exactly k

Example:
atMost(3) = {0 odds, 1 odd, 2 odds, 3 odds}
atMost(2) = {0 odds, 1 odd, 2 odds}
Difference = {3 odds exactly}

This is a common pattern for "exactly X" problems.
```

---

### Q2: "What if k = 0? (Find subarrays with 0 odd numbers)"

**Answer:**
```
atMost(0) - atMost(-1)

atMost(0) = subarrays with 0 or fewer odds
          = subarrays with only evens

atMost(-1) = subarrays with -1 or fewer odds
           = impossible state, always 0

So: atMost(0) - 0 = subarrays with only evens ✓

Edge case: If k=0, need to handle atMost(-1)
Add guard: if (k < 0) return 0;
```

---

### Q3: "Why does result += right - left + 1 work?"

**Answer:**
```
When we're at right pointer:

[a, b, c, d, e, f] where left=b, right=f
          ↑left    ↑right

Subarrays ending at f with ≤k odds:
  - [b, f] ✓
  - [c, f] ✓
  - [d, f] ✓
  - [e, f] ✓
  - [f, f] ✓

Count: How many starting positions from left to right?
      = right - left + 1
      = f_index - b_index + 1 ✓

This counts ALL valid subarrays ending at current right!
```

---

### Q4: "Is there a way without the atMost trick?"

**Answer:**
```
Yes, using HashMap (prefix sum approach):

public int numberOfSubarrays(int[] nums, int k) {
    Map<Integer, Integer> oddCountMap = new HashMap<>();
    oddCountMap.put(0, 1);
    
    int count = 0;
    int oddsSoFar = 0;
    
    for (int num : nums) {
        if (num % 2 == 1) oddsSoFar++;
        
        if (oddCountMap.containsKey(oddsSoFar - k)) {
            count += oddCountMap.get(oddsSoFar - k);
        }
        
        oddCountMap.put(oddsSoFar, oddCountMap.getOrDefault(oddsSoFar, 0) + 1);
    }
    
    return count;
}

This works because:
  If current prefix has X odds,
  and we've seen prefix with X-k odds before,
  then subarrays between them have exactly k odds.

Both O(n), sliding window is more elegant.
```

---

## Common Mistakes

```java
❌ MISTAKE 1: Forgetting result += right - left + 1
while (k < 0) {
    if (nums[left] % 2 == 1) k++;
    left++;
}
// Missing: result += right - left + 1;

✅ CORRECT: Add counting step

❌ MISTAKE 2: Using k < 0 instead of while loop
if (k < 0) {  // Only checks once
    if (nums[left] % 2 == 1) k++;
    left++;
}

✅ CORRECT: Use while loop to fully shrink window
while (k < 0) {
    if (nums[left] % 2 == 1) k++;
    left++;
}

❌ MISTAKE 3: Not handling k=0 case
numberOfSubarrays(nums, 0) calls atMost(0) - atMost(-1)
If atMost(-1) is called with infinite loop

✅ CORRECT: Handle negative k
private int atMost(int[] nums, int k) {
    if (k < 0) return 0;  // Guard clause
    ...
}
```

---

## Complexity Comparison

| Approach | Time | Space | Notes |
|----------|------|-------|-------|
| Brute Force | O(n²) | O(1) | Times out |
| HashMap | O(n) | O(n) | Works, less elegant |
| Sliding Window | O(n) | O(1) | Optimal, elegant |

---

## Interview Answer

**Q: "Count subarrays with exactly k odd numbers. Optimize for time."**

**Answer:**

> "I'll use the **'atMost' sliding window technique** because finding 'exactly k'
> directly is awkward, but finding 'at most k' is natural.
> 
> **Key insight:** Any subarray with exactly k odds can be expressed as:
> (subarray with ≤k odds) - (subarray with ≤k-1 odds)
> 
> **Algorithm:**
> 1. Count subarrays with at most k odd numbers
> 2. Count subarrays with at most k-1 odd numbers
> 3. Return the difference
> 
> **'At Most' counting using two-pointer window:**
> - Expand right pointer, count odds
> - When odds > k, shrink left pointer
> - For each right position, all subarrays from [left...right] 
>   have ≤k odds, so add (right - left + 1) to result
> 
> **Why this works:**
> - Each subarray ending at right with left boundary ensures ≤k odds
> - Window [left...right] generates (right-left+1) valid subarrays
> 
> **Complexity:**
> - Time: O(n) - left and right pointers each move once
> - Space: O(1) - only pointers, no extra data structure"
> 
> **Code:** [implementation provided above]"

---

## Key Takeaways

| Concept | Why It Matters | Interview Score |
|---------|----------------|-----------------|
| **atMost trick** | Transforms exact → easier problem | ⭐⭐⭐⭐⭐ |
| **Sliding window** | Two-pointer efficiency | ⭐⭐⭐⭐⭐ |
| **Counting subarrays** | result += right - left + 1 pattern | ⭐⭐⭐⭐⭐ |
| **When to shrink** | k < 0 condition | ⭐⭐⭐⭐ |
| **Why while not if** | Multiple elements might be odd | ⭐⭐⭐ |

