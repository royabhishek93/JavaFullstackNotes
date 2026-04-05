# LC 560: Subarray Sum Equals K

**Link**: [leetcode.com/problems/subarray-sum-equals-k](https://leetcode.com/problems/subarray-sum-equals-k/)

## Problem
Given an integer array `nums` and an integer `k`, return the total number of subarrays whose sum equals `k`.

## Optimized Approach: Prefix Sum + HashMap

```java
public int subarraySum(int[] nums, int k) {
    Map<Integer, Integer> prefixCount = new HashMap<>();
    prefixCount.put(0, 1); // empty prefix

    int sum = 0, count = 0;

    for (int num : nums) {
        sum += num;
        count += prefixCount.getOrDefault(sum - k, 0);
        prefixCount.put(sum, prefixCount.getOrDefault(sum, 0) + 1);
    }

    return count;
}
```

**Time Complexity**: O(n)  
**Space Complexity**: O(n)

## Key Insights
- `sum[i..j] = k` ↔ `prefix[j] - prefix[i-1] = k` ↔ `prefix[i-1] = prefix[j] - k`
- Count previously seen prefix sums equal to `sum - k`

## Tips and Tricks
- Use hashing when constant-time membership or frequency lookup matters more than order.
- Be explicit about what the key represents: value, index relation, or prefix state.
- Frequency maps and prefix maps solve many array problems that look quadratic at first.

## Related Problems
- LC 1 Two Sum (same hash-lookup pattern)
- LC 325 Maximum Size Subarray Sum Equals k
