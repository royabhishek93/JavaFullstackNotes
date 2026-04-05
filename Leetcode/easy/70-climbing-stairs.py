# Problem: Climbing Stairs
# Link: https://leetcode.com/problems/climbing-stairs/
# Difficulty: Easy
#
# Description:
# You are climbing a staircase. It takes n steps to reach the top.
# Each time you can either climb 1 or 2 steps. In how many distinct ways can you climb to the top?
#
# Approach:
# 1D Linear DP - Ways to reach step i = ways from (i-1) + ways from (i-2)
# This follows the Fibonacci pattern: dp[i] = dp[i-1] + dp[i-2]
#
# Time Complexity: O(n)
# Space Complexity: O(n)

class Solution:
    def climbStairs(self, n: int) -> int:
        if n <= 1:
            return 1

        dp = [0] * (n + 1)
        dp[0] = 1
        dp[1] = 1

        for i in range(2, n + 1):
            dp[i] = dp[i - 1] + dp[i - 2]

        return dp[n]

# Test cases
if __name__ == "__main__":
    solution = Solution()
    
    # Example 1: n = 2
    # Output: 2 (1+1, 2)
    assert solution.climbStairs(2) == 2
    
    # Example 2: n = 3
    # Output: 3 (1+1+1, 1+2, 2+1)
    assert solution.climbStairs(3) == 3
    
    # Example 3: n = 5
    # Output: 8
    assert solution.climbStairs(5) == 8
    
    print("✅ All test cases passed!")
