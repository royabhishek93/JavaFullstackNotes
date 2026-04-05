# Problem: House Robber
# Link: https://leetcode.com/problems/house-robber/
# Difficulty: Medium
#
# Description:
# You are a professional robber planning to rob houses along a street.
# Each house has a certain amount of money stashed.
# Adjacent houses have security systems connected, so you can't rob adjacent houses.
# Given an integer array nums representing the amount of money of each house,
# return the maximum amount of money you can rob tonight without alerting the police.
#
# Approach:
# 1D Linear DP - At each house, decide: rob it (skip previous) or skip it (take previous best)
# dp[i] = max(dp[i-1], dp[i-2] + nums[i])
#
# Time Complexity: O(n)
# Space Complexity: O(n)

class Solution:
    def rob(self, nums):
        if not nums:
            return 0
        if len(nums) == 1:
            return nums[0]

        dp = [0] * len(nums)
        dp[0] = nums[0]
        dp[1] = max(nums[0], nums[1])

        for i in range(2, len(nums)):
            dp[i] = max(dp[i - 1], dp[i - 2] + nums[i])

        return dp[-1]

# Test cases
if __name__ == "__main__":
    solution = Solution()
    
    # Example 1: [1,2,3,1]
    # Rob house 1 (1) + house 3 (3) = 4
    assert solution.rob([1, 2, 3, 1]) == 4
    
    # Example 2: [2,7,9,3,1]
    # Rob house 1 (2) + house 3 (9) + house 5 (1) = 12
    assert solution.rob([2, 7, 9, 3, 1]) == 12
    
    # Edge case: single house
    assert solution.rob([5]) == 5
    
    print("✅ All test cases passed!")
