/**
 * Problem: House Robber
 * Link: https://leetcode.com/problems/house-robber/
 * Difficulty: Medium
 *
 * Description:
 * You are a professional robber planning to rob houses along a street.
 * Each house has a certain amount of money stashed.
 * Adjacent houses have security systems connected, so you can't rob adjacent houses.
 * Given an integer array nums representing the amount of money of each house,
 * return the maximum amount of money you can rob tonight without alerting the police.
 *
 * Approach:
 * 1D Linear DP - At each house, decide: rob it (skip previous) or skip it (take previous best)
 * dp[i] = max(dp[i-1], dp[i-2] + nums[i])
 *
 * Time Complexity: O(n)
 * Space Complexity: O(n)
 */

class Solution {
    public int rob(int[] nums) {
        if (nums.length == 0) return 0;
        if (nums.length == 1) return nums[0];

        int[] dp = new int[nums.length];
        dp[0] = nums[0];
        dp[1] = Math.max(nums[0], nums[1]);

        for (int i = 2; i < nums.length; i++) {
            dp[i] = Math.max(dp[i - 1], dp[i - 2] + nums[i]);
        }
        return dp[nums.length - 1];
    }

    // Test cases
    public static void main(String[] args) {
        Solution solution = new Solution();
        
        // Example 1: [1,2,3,1]
        // Rob house 1 (1) + house 3 (3) = 4
        assert solution.rob(new int[]{1, 2, 3, 1}) == 4 
            : "Test case 1 failed";
        
        // Example 2: [2,7,9,3,1]
        // Rob house 1 (2) + house 3 (9) + house 5 (1) = 12
        assert solution.rob(new int[]{2, 7, 9, 3, 1}) == 12 
            : "Test case 2 failed";
        
        // Edge case: single house
        assert solution.rob(new int[]{5}) == 5 
            : "Test case 3 failed";
        
        System.out.println("✅ All test cases passed!");
    }
}
