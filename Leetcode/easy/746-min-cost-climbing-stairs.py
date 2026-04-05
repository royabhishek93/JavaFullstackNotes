# Problem: Min Cost Climbing Stairs
# Link: https://leetcode.com/problems/min-cost-climbing-stairs/
# Difficulty: Easy
#
# Description:
# You are given an array cost where cost[i] is the cost of ith step on a staircase.
# Once you pay the cost, you can either climb one or two steps.
# You can start from the step with index 0, or the step with index 1.
# Return the minimum cost to reach the top of the floor.
#
# Approach:
# 1D Linear DP - Min cost to reach step i = min(cost from i-1, cost from i-2) + cost[i]
# dp[i] = min(dp[i-1] + cost[i-1], dp[i-2] + cost[i-2])
#
# Time Complexity: O(n)
# Space Complexity: O(n)

class Solution:
    def minCostClimbingStairs(self, cost):
        n = len(cost)
        dp = [0] * (n + 1)

        for i in range(2, n + 1):
            dp[i] = min(
                dp[i - 1] + cost[i - 1],
                dp[i - 2] + cost[i - 2]
            )

        return dp[n]

# Test cases
if __name__ == "__main__":
    solution = Solution()
    
    # Example 1
    assert solution.minCostClimbingStairs([10, 15, 20]) == 15
    
    # Example 2
    assert solution.minCostClimbingStairs([1, 100, 1, 1, 1, 100, 1, 1, 100, 1]) == 6
    
    print("✅ All test cases passed!")
