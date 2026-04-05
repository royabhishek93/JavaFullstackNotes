/**
 * Problem: Climbing Stairs
 * Link: https://leetcode.com/problems/climbing-stairs/
 * Difficulty: Easy
 *
 * Description:
 * You are climbing a staircase. It takes n steps to reach the top.
 * Each time you can either climb 1 or 2 steps. In how many distinct ways can you climb to the top?
 *
 * Approach:
 * 1D Linear DP - Ways to reach step i = ways from (i-1) + ways from (i-2)
 * This follows the Fibonacci pattern: dp[i] = dp[i-1] + dp[i-2]
 *
 * Time Complexity: O(n)
 * Space Complexity: O(n)
 */

class Solution {
    public int climbStairs(int n) {
        if (n <= 1) return 1;

        int[] dp = new int[n + 1];
        dp[0] = 1;
        dp[1] = 1;

        for (int i = 2; i <= n; i++) {
            dp[i] = dp[i - 1] + dp[i - 2];
        }
        return dp[n];
    }

    // Test cases
    public static void main(String[] args) {
        Solution solution = new Solution();
        
        // Example 1: n = 2
        // Output: 2 (1+1, 2)
        assert solution.climbStairs(2) == 2 : "Test case 1 failed";
        
        // Example 2: n = 3
        // Output: 3 (1+1+1, 1+2, 2+1)
        assert solution.climbStairs(3) == 3 : "Test case 2 failed";
        
        // Example 3: n = 5
        // Output: 8
        assert solution.climbStairs(5) == 8 : "Test case 3 failed";
        
        System.out.println("✅ All test cases passed!");
    }
}
