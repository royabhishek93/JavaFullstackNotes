/**
 * Problem: Minimum Size Subarray Sum
 * Link: https://leetcode.com/problems/minimum-size-subarray-sum/
 * Difficulty: Medium
 *
 * Description:
 * Given an array of positive integers nums and a positive integer target,
 * return the minimal length of a contiguous subarray of which the sum >= target.
 * If no such subarray exists, return 0.
 *
 * Approach:
 * Sliding Window (Two Pointers) - O(n) optimal solution
 * 
 * Core Logic:
 * 1. Expand window by moving right pointer, adding elements to sum
 * 2. Once sum >= target, try shrinking from left to find minimum length
 * 3. Keep tracking minimum length during shrinking
 * 4. Continue until right pointer traverses entire array
 *
 * Why Sliding Window Works:
 * - All numbers are positive
 * - Expanding window → sum increases (predictable behavior)
 * - Shrinking window → sum decreases (predictable behavior)
 * 
 * CRITICAL: Use >= not > in while condition
 * - Problem asks for sum >= target (at least target)
 * - Using > will miss cases where sum exactly equals target
 * - Example: target=7, if sum=7 exactly, must count it!
 *
 * Why USE 'while' NOT 'if':
 * - Must keep shrinking as long as condition holds to find minimum
 * - 'if' would shrink only once → might miss smaller valid window
 *
 * Time Complexity: O(n) - Each element visited at most twice (right + left pointers)
 * Space Complexity: O(1) - Only using constant extra space
 */

class Solution {
    public int minSubArrayLen(int target, int[] nums) {
        int left = 0;
        int sum = 0;
        int minLength = Integer.MAX_VALUE;  // Start with max value for minimum comparison
        
        // Expand window with right pointer
        for (int right = 0; right < nums.length; right++) {
            sum += nums[right];  // Add element to window
            
            // Shrink window while condition is met
            // IMPORTANT: >= not > (must include equal case)
            while (sum >= target) {
                // Update minimum length before shrinking
                minLength = Math.min(minLength, right - left + 1);
                
                // Shrink window from left
                sum -= nums[left];
                left++;
            }
        }
        
        // Return 0 if no valid subarray found
        return minLength == Integer.MAX_VALUE ? 0 : minLength;
    }

    // Test cases
    public static void main(String[] args) {
        Solution solution = new Solution();
        
        // Example 1: Standard case
        // [2,3,1,2,4,3], target=7
        // Window [4,3] gives sum=7 with length=2
        assert solution.minSubArrayLen(7, new int[]{2, 3, 1, 2, 4, 3}) == 2 
            : "Test case 1 failed";
        
        // Example 2: Single element satisfies
        // [1,4,4], target=4
        // Window [4] gives sum=4 with length=1
        assert solution.minSubArrayLen(4, new int[]{1, 4, 4}) == 1 
            : "Test case 2 failed";
        
        // Example 3: Need entire array
        // [1,1,1,1,1,1,1,1], target=11
        // No subarray sum >= 11, return 0
        assert solution.minSubArrayLen(11, new int[]{1, 1, 1, 1, 1, 1, 1, 1}) == 0 
            : "Test case 3 failed";
        
        // Edge case 1: Single element equals target
        assert solution.minSubArrayLen(5, new int[]{5}) == 1 
            : "Edge case 1 failed";
        
        // Edge case 2: Entire array needed
        assert solution.minSubArrayLen(15, new int[]{1, 2, 3, 4, 5}) == 5 
            : "Edge case 2 failed";
        
        // Edge case 3: Target greater than sum of all elements
        assert solution.minSubArrayLen(100, new int[]{1, 2, 3}) == 0 
            : "Edge case 3 failed";
        
        System.out.println("✅ All test cases passed!");
    }
}

// =============================================================================
// ALTERNATIVE SOLUTIONS FOR ARRAYS WITH NEGATIVE NUMBERS
// =============================================================================

class SolutionWithNegatives {
    /**
     * When array contains negative numbers, sliding window breaks.
     * These approaches work for both positive and negative numbers.
     */
    
    // Approach 1: Prefix Sum + Binary Search
    // Time: O(n log n), Space: O(n)
    public int minSubArrayLen_BinarySearch(int target, int[] nums) {
        /*
         * Why this works:
         * - Build cumulative sum array (prefix sum)
         * - For each position i, binary search for smallest j where
         *   prefix[j] - prefix[i] >= target
         * - This gives us sum(nums[i:j]) >= target
         */
        int n = nums.length;
        
        // Build prefix sum array: prefix[i] = sum of nums[0:i]
        long[] prefix = new long[n + 1];
        for (int i = 0; i < n; i++) {
            prefix[i + 1] = prefix[i] + nums[i];
        }
        
        int minLength = Integer.MAX_VALUE;
        
        // For each starting position
        for (int i = 0; i < n; i++) {
            // Find smallest j where prefix[j] - prefix[i] >= target
            // Which means prefix[j] >= target + prefix[i]
            long toFind = target + prefix[i];
            
            // Binary search in prefix array
            int left = i + 1, right = n + 1;
            while (left < right) {
                int mid = left + (right - left) / 2;
                if (prefix[mid] >= toFind) {
                    right = mid;
                } else {
                    left = mid + 1;
                }
            }
            
            // If found valid endpoint
            if (left != n + 1) {
                minLength = Math.min(minLength, left - i);
            }
        }
        
        return minLength == Integer.MAX_VALUE ? 0 : minLength;
    }
    
    
    // Approach 2: Monotonic Deque (Most Optimal for Negatives)
    // Time: O(n), Space: O(n)
    public int minSubArrayLen_MonotonicDeque(int target, int[] nums) {
        /*
         * Based on LeetCode 862: Shortest Subarray with Sum at Least K
         * 
         * Why this works:
         * - Use deque to maintain indices with increasing prefix sums
         * - For each position, check if we can form valid subarray
         * - Remove indices that won't lead to optimal solution
         * 
         * Key insight:
         * - If prefix[i] >= prefix[j] and i < j, we never use j as start
         * - Because using i gives longer subarrays with same/better sum
         */
        int n = nums.length;
        
        // Build prefix sum
        long[] prefix = new long[n + 1];
        for (int i = 0; i < n; i++) {
            prefix[i + 1] = prefix[i] + nums[i];
        }
        
        int minLength = Integer.MAX_VALUE;
        java.util.Deque<Integer> dq = new java.util.ArrayDeque<>();
        
        for (int i = 0; i <= n; i++) {
            // Check if we can form valid subarray ending at i
            // Pop from front while we found valid subarrays
            while (!dq.isEmpty() && prefix[i] - prefix[dq.peekFirst()] >= target) {
                minLength = Math.min(minLength, i - dq.pollFirst());
            }
            
            // Maintain increasing order in deque
            // Remove indices with larger prefix sums (won't be optimal)
            while (!dq.isEmpty() && prefix[i] <= prefix[dq.peekLast()]) {
                dq.pollLast();
            }
            
            dq.offerLast(i);
        }
        
        return minLength == Integer.MAX_VALUE ? 0 : minLength;
    }
    
    
    // Test alternative solutions
    public static void main(String[] args) {
        SolutionWithNegatives solution = new SolutionWithNegatives();
        
        // Test with mixed positive/negative numbers
        System.out.println("\nTesting alternative solutions with negative numbers:");
        
        // Test case 1: [3, -2, 5], target = 3
        // Valid subarrays: [3] (sum=3), [5] (sum=5), [3,-2,5] (sum=6)
        // Minimum length = 1
        int[] test1 = {3, -2, 5};
        int result1_bs = solution.minSubArrayLen_BinarySearch(3, test1);
        int result1_dq = solution.minSubArrayLen_MonotonicDeque(3, test1);
        System.out.println("Test 1: [3,-2,5], target=3");
        System.out.println("  Binary Search: " + result1_bs + ", Deque: " + result1_dq + " (Expected: 1)");
        
        // Test case 2: [2, -1, 2], target = 3
        int[] test2 = {2, -1, 2};
        int result2_bs = solution.minSubArrayLen_BinarySearch(3, test2);
        int result2_dq = solution.minSubArrayLen_MonotonicDeque(3, test2);
        System.out.println("Test 2: [2,-1,2], target=3");
        System.out.println("  Binary Search: " + result2_bs + ", Deque: " + result2_dq + " (Expected: 3)");
        
        // Test case 3: [-1, 2, 3], target = 5
        int[] test3 = {-1, 2, 3};
        int result3_bs = solution.minSubArrayLen_BinarySearch(5, test3);
        int result3_dq = solution.minSubArrayLen_MonotonicDeque(5, test3);
        System.out.println("Test 3: [-1,2,3], target=5");
        System.out.println("  Binary Search: " + result3_bs + ", Deque: " + result3_dq + " (Expected: 2)");
        
        System.out.println("\n✅ Alternative solution examples completed!");
    }
}

/*
 * INTERVIEW CROSS-QUESTIONS & ANSWERS:
 *
 * Q1: Why does sliding window work here?
 * A: Because all numbers are positive:
 *    - Expanding → sum increases (predictable)
 *    - Shrinking → sum decreases (predictable)
 *    If negative numbers exist, this logic breaks!
 *
 * Q2: What if array contains negative numbers?
 * A: Sliding window fails. Must use:
 *    - Prefix Sum + Binary Search (O(n log n))
 *    - Or Monotonic Queue (O(n)) - See LC 862
 *
 * Q3: Why is time complexity O(n) with nested loop?
 * A: Each element visited at most twice:
 *    - Right pointer: n movements
 *    - Left pointer: at most n movements
 *    Total: 2n operations → O(n)
 *
 * Q4: Why initialize minLength with Integer.MAX_VALUE?
 * A: Finding minimum. If initialized to 0:
 *    - Math.min(0, any_positive) = 0 → always wrong
 *    - MAX_VALUE ensures first valid window updates it
 *
 * Q5: Can you solve with binary search?
 * A: Yes! O(n log n) approach:
 *    - Build prefix sum array: O(n)
 *    - For each index, binary search smallest index where sum >= target
 *    - Total: O(n log n)
 *
 * Q6: What if we need MAXIMUM length instead?
 * A: Logic changes completely:
 *    - Still use sliding window
 *    - But shrink only when sum > target (not >=)
 *    - Track maximum instead of minimum
 *
 * Q7: What if we need EXACT sum (not >=)?
 * A: For positive numbers: sliding window works with sum == target
 *    For mixed numbers: use prefix sum + hashmap
 *
 * COMMON MISTAKE THAT FAILS INTERVIEWS:
 * ❌ while(sum > target)  // WRONG - misses exact matches
 * ✅ while(sum >= target) // CORRECT - includes sum == target case
 *
 * DRY RUN EXAMPLE:
 * Input: target = 7, nums = [2,3,1,2,4,3]
 * 
 * Step  Right  Sum   Left  Window    minLength  Action
 * 1     0      2     0     [2]       INF        sum < 7, continue
 * 2     1      5     0     [2,3]     INF        sum < 7, continue
 * 3     2      6     0     [2,3,1]   INF        sum < 7, continue
 * 4     3      8     0     [2,3,1,2] 4          sum >= 7, shrink
 *             6     1     [3,1,2]   INF        sum < 7, stop shrink
 * 5     4      10    1     [3,1,2,4] 4          sum >= 7, shrink
 *             7     2     [1,2,4]   3          sum >= 7, shrink
 *             5     3     [2,4]     INF        sum < 7, stop shrink
 * 6     5      8     3     [2,4,3]   3          sum >= 7, shrink
 *             6     4     [4,3]     2          sum < 7, stop shrink
 * 
 * Final Answer: 2 (window [4,3] with sum = 7)
 */
