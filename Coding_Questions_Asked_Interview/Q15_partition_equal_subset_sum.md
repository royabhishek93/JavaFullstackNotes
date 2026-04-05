# Q15: Partition Equal Subset Sum (LeetCode 416)

**Study Time:** 10-12 minutes | **Frequency:** 75% in DSA interviews 🔥 | **Difficulty:** ⭐⭐⭐⭐

**LeetCode:** [Partition Equal Subset Sum](https://leetcode.com/problems/partition-equal-subset-sum/)

---

## Scenario

Given an integer array, can you split it into two subsets with equal sum?

```java
int[] nums = {1, 5, 11, 5};
// true -> {1,5,5} and {11}
```

Interview trap: many candidates start with recursive subset generation O(2^n).

---

## Key Principle

If total sum is odd, answer is immediately false.

If total sum is even, the problem becomes:

"Can we find a subset with sum = totalSum / 2?"

That is exactly the Subset Sum Problem.

---

## Java Solution (1D DP)

```java
public class PartitionEqualSubsetSum {

    public static boolean canPartition(int[] nums) {
        int totalSum = 0;
        for (int num : nums) {
            totalSum += num;
        }

        // Odd sum can never be split into two equal integers
        if (totalSum % 2 != 0) {
            return false;
        }

        int target = totalSum / 2;
        boolean[] dp = new boolean[target + 1];
        dp[0] = true;

        for (int num : nums) {
            // Backward iteration ensures each number is used once
            for (int s = target; s >= num; s--) {
                dp[s] = dp[s] || dp[s - num];
            }
        }

        return dp[target];
    }

    public static void main(String[] args) {
        int[] nums1 = {1, 5, 11, 5};
        int[] nums2 = {1, 2, 3, 5};

        System.out.println(canPartition(nums1)); // true
        System.out.println(canPartition(nums2)); // false
    }
}
```

---

## Step-by-Step (Quick)

Input:

```text
nums = [1, 5, 11, 5]
totalSum = 22
target = 11
```

Now check if subset sum 11 is possible:

- After processing `1`: sum 1 possible
- After processing `5`: sums 5 and 6 possible
- After processing `11`: sum 11 possible -> success

Hence partition exists.

---

## Complexity

- Time: O(n * target)
- Space: O(target)

Where `target = totalSum / 2`.

---

## Interview Q&A

1. Why reduce to target `totalSum / 2`?

If two subsets are equal, each must hold half of total sum.

2. Why return false for odd total sum immediately?

An odd integer cannot be split into two equal integers.

3. Is this same as Subset Sum Problem?

Yes. Partition Equal Subset Sum is a constrained subset sum where target is fixed to half of total sum.

4. Top optimization to mention in interviews?

Use 1D DP with backward traversal instead of 2D DP to reduce space.
