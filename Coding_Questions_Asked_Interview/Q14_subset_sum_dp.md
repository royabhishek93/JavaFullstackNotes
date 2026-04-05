# Q14: Subset Sum Using 1D Dynamic Programming

**Study Time:** 8-10 minutes | **Frequency:** 70% in DSA interviews 🔥 | **Difficulty:** ⭐⭐⭐⭐

---

## Scenario

You are given an array of positive integers and a target sum.

Interview asks:
"Can you determine whether any subset of the array adds exactly to target, without generating all subsets?"

```java
int[] arr = {1, 2, 3, 7};
int target = 6;
// Output: true (subset {1,2,3})
```

Brute force checks all subsets in O(2^n), which is too slow for larger inputs.

---

## Key Principle

Use DP where:

- `dp[s] = true` means sum `s` is achievable using processed elements.
- Start with `dp[0] = true` because empty subset always makes sum 0.
- For each number `num`, update from right to left:
  - `dp[s] = dp[s] || dp[s - num]`

Why right to left?

If you go left to right, current number can be reused in the same iteration (wrong for subset, correct for unbounded coin change). Right-to-left guarantees each element is used at most once.

---

## Java Solution

```java
public class SubsetSumDP {

    public static boolean subsetSum(int[] arr, int target) {
        boolean[] dp = new boolean[target + 1];

        dp[0] = true; // sum 0 is always possible

        for (int num : arr) {
            // Traverse backward to avoid reusing same number in current iteration
            for (int i = target; i >= num; i--) {
                dp[i] = dp[i] || dp[i - num];
            }
        }

        return dp[target];
    }

    public static void main(String[] args) {
        int[] arr = {1, 2, 3, 7};
        int target = 6;

        System.out.println(subsetSum(arr, target)); // true
    }
}
```

---

## Step-by-Step (Quick)

Input:

```text
arr = [1, 2, 3, 7], target = 6
```

Initialize:

```text
dp[0] = true, others false
```

After processing `1`: sum 1 becomes possible.

After processing `2`: sums 2 and 3 become possible.

After processing `3`: sums 3, 4, 5, 6 become possible.

`dp[6] = true` so answer is true.

---

## Complexity

- Time: O(n * target)
- Space: O(target)

Compared to 2D DP O(n * target) space, this 1D optimization is interview-friendly and production-friendly.

---

## Interview Q&A

1. Why not iterate forward in inner loop?

Forward iteration may reuse the same number multiple times in one pass, which breaks subset constraints.

2. What if target is 0?

Always true because empty subset makes 0.

3. Does this work with negative numbers?

Not directly. This DP index design assumes non-negative sums. For negatives, use offset-based DP or set-based approaches.

4. Related LeetCode problems?

- 416. Partition Equal Subset Sum
- 494. Target Sum (variation)
