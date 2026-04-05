# Problem: Minimum Size Subarray Sum
# Link: https://leetcode.com/problems/minimum-size-subarray-sum/
# Difficulty: Medium
#
# Description:
# Given an array of positive integers nums and a positive integer target,
# return the minimal length of a contiguous subarray of which the sum >= target.
# If no such subarray exists, return 0.
#
# Approach:
# Sliding Window (Two Pointers) - O(n) optimal solution
# 
# Core Logic:
# 1. Expand window by moving right pointer, adding elements to sum
# 2. Once sum >= target, try shrinking from left to find minimum length
# 3. Keep tracking minimum length during shrinking
# 4. Continue until right pointer traverses entire array
#
# Why Sliding Window Works:
# - All numbers are positive
# - Expanding window → sum increases (predictable behavior)
# - Shrinking window → sum decreases (predictable behavior)
# 
# CRITICAL: Use >= not > in while condition
# - Problem asks for sum >= target (at least target)
# - Using > will miss cases where sum exactly equals target
# - Example: target=7, if sum=7 exactly, must count it!
#
# Why USE 'while' NOT 'if':
# - Must keep shrinking as long as condition holds to find minimum
# - 'if' would shrink only once → might miss smaller valid window
#
# Time Complexity: O(n) - Each element visited at most twice (right + left pointers)
# Space Complexity: O(1) - Only using constant extra space

class Solution:
    def minSubArrayLen(self, target: int, nums: list[int]) -> int:
        left = 0
        current_sum = 0
        min_length = float('inf')  # Start with infinity for minimum comparison
        
        # Expand window with right pointer
        for right in range(len(nums)):
            current_sum += nums[right]  # Add element to window
            
            # Shrink window while condition is met
            # IMPORTANT: >= not > (must include equal case)
            while current_sum >= target:
                # Update minimum length before shrinking
                min_length = min(min_length, right - left + 1)
                
                # Shrink window from left
                current_sum -= nums[left]
                left += 1
        
        # Return 0 if no valid subarray found
        return 0 if min_length == float('inf') else min_length


# Test cases
if __name__ == "__main__":
    solution = Solution()
    
    # Example 1: Standard case
    # [2,3,1,2,4,3], target=7
    # Window [4,3] gives sum=7 with length=2
    assert solution.minSubArrayLen(7, [2, 3, 1, 2, 4, 3]) == 2
    
    # Example 2: Single element satisfies
    # [1,4,4], target=4
    # Window [4] gives sum=4 with length=1
    assert solution.minSubArrayLen(4, [1, 4, 4]) == 1
    
    # Example 3: Need entire array
    # [1,1,1,1,1,1,1,1], target=11
    # No subarray sum >= 11, return 0
    assert solution.minSubArrayLen(11, [1, 1, 1, 1, 1, 1, 1, 1]) == 0
    
    # Edge case 1: Single element equals target
    assert solution.minSubArrayLen(5, [5]) == 1
    
    # Edge case 2: Entire array needed
    assert solution.minSubArrayLen(15, [1, 2, 3, 4, 5]) == 5
    
    # Edge case 3: Target greater than sum of all elements
    assert solution.minSubArrayLen(100, [1, 2, 3]) == 0
    
    print("✅ All test cases passed!")


# =============================================================================
# ALTERNATIVE SOLUTIONS FOR ARRAYS WITH NEGATIVE NUMBERS
# =============================================================================

class SolutionWithNegatives:
    """
    When array contains negative numbers, sliding window breaks.
    These approaches work for both positive and negative numbers.
    """
    
    # Approach 1: Prefix Sum + Binary Search
    # Time: O(n log n), Space: O(n)
    def minSubArrayLen_BinarySearch(self, target: int, nums: list[int]) -> int:
        """
        Why this works:
        - Build cumulative sum array (prefix sum)
        - For each position i, binary search for smallest j where
          prefix[j] - prefix[i] >= target
        - This gives us sum(nums[i:j]) >= target
        """
        n = len(nums)
        
        # Build prefix sum array: prefix[i] = sum of nums[0:i]
        prefix = [0] * (n + 1)
        for i in range(n):
            prefix[i + 1] = prefix[i] + nums[i]
        
        min_length = float('inf')
        
        # For each starting position
        for i in range(n):
            # Find smallest j where prefix[j] - prefix[i] >= target
            # Which means prefix[j] >= target + prefix[i]
            to_find = target + prefix[i]
            
            # Binary search in prefix array
            left, right = i + 1, n + 1
            while left < right:
                mid = (left + right) // 2
                if prefix[mid] >= to_find:
                    right = mid
                else:
                    left = mid + 1
            
            # If found valid endpoint
            if left != n + 1:
                min_length = min(min_length, left - i)
        
        return 0 if min_length == float('inf') else min_length
    
    
    # Approach 2: Monotonic Deque (Most Optimal for Negatives)
    # Time: O(n), Space: O(n)
    def minSubArrayLen_MonotonicDeque(self, target: int, nums: list[int]) -> int:
        """
        Based on LeetCode 862: Shortest Subarray with Sum at Least K
        
        Why this works:
        - Use deque to maintain indices with increasing prefix sums
        - For each position, check if we can form valid subarray
        - Remove indices that won't lead to optimal solution
        
        Key insight:
        - If prefix[i] >= prefix[j] and i < j, we never use j as start
        - Because using i gives longer subarrays with same/better sum
        """
        from collections import deque
        
        n = len(nums)
        
        # Build prefix sum
        prefix = [0] * (n + 1)
        for i in range(n):
            prefix[i + 1] = prefix[i] + nums[i]
        
        min_length = float('inf')
        dq = deque()  # Store indices
        
        for i in range(n + 1):
            # Check if we can form valid subarray ending at i
            # Pop from front while we found valid subarrays
            while dq and prefix[i] - prefix[dq[0]] >= target:
                min_length = min(min_length, i - dq.popleft())
            
            # Maintain increasing order in deque
            # Remove indices with larger prefix sums (won't be optimal)
            while dq and prefix[i] <= prefix[dq[-1]]:
                dq.pop()
            
            dq.append(i)
        
        return 0 if min_length == float('inf') else min_length


# Test alternative solutions
if __name__ == "__main__" and False:  # Set to True to test
    solution_neg = SolutionWithNegatives()
    
    # Test with mixed positive/negative numbers
    # Example: [3, -2, 5], target = 3
    # Valid subarrays: [3] (sum=3), [5] (sum=5), [3,-2,5] (sum=6)
    # Minimum length = 1
    
    test_cases = [
        ([3, -2, 5], 3, 1),
        ([2, -1, 2], 3, 3),
        ([-1, 2, 3], 5, 2),
        ([1, 2, 3, 4, 5], 11, 3),
    ]
    
    print("\nTesting alternative solutions with negative numbers:")
    for nums, target, expected in test_cases:
        result1 = solution_neg.minSubArrayLen_BinarySearch(target, nums)
        result2 = solution_neg.minSubArrayLen_MonotonicDeque(target, nums)
        print(f"nums={nums}, target={target}")
        print(f"  Binary Search: {result1}, Deque: {result2}, Expected: {expected}")
        assert result1 == expected and result2 == expected


# INTERVIEW CROSS-QUESTIONS & ANSWERS:
#
# Q1: Why does sliding window work here?
# A: Because all numbers are positive:
#    - Expanding → sum increases (predictable)
#    - Shrinking → sum decreases (predictable)
#    If negative numbers exist, this logic breaks!
#
# Q2: What if array contains negative numbers?
# A: Sliding window fails. Must use:
#    - Prefix Sum + Binary Search (O(n log n))
#    - Or Monotonic Queue (O(n)) - See LC 862
#
# Q3: Why is time complexity O(n) with nested loop?
# A: Each element visited at most twice:
#    - Right pointer: n movements
#    - Left pointer: at most n movements
#    Total: 2n operations → O(n)
#
# Q4: Why initialize min_length with infinity?
# A: Finding minimum. If initialized to 0:
#    - min(0, any_positive) = 0 → always wrong
#    - infinity ensures first valid window updates it
#
# Q5: Can you solve with binary search?
# A: Yes! O(n log n) approach:
#    - Build prefix sum array: O(n)
#    - For each index, binary search smallest index where sum >= target
#    - Total: O(n log n)
#
# Q6: What if we need MAXIMUM length instead?
# A: Logic changes completely:
#    - Still use sliding window
#    - But shrink only when sum > target (not >=)
#    - Track maximum instead of minimum
#
# Q7: What if we need EXACT sum (not >=)?
# A: For positive numbers: sliding window works with sum == target
#    For mixed numbers: use prefix sum + hashmap
