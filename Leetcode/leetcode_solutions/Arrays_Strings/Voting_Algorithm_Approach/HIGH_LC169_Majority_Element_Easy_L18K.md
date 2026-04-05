# LC 169: Majority Element

**Link**: [leetcode.com/problems/majority-element](https://leetcode.com/problems/majority-element/)

## Problem
Given an array `nums` of size `n`, return the majority element. The majority element appears more than `⌊n / 2⌋` times. You may assume it always exists.

## Optimized Approach: Boyer-Moore Voting

```java
public int majorityElement(int[] nums) {
    int candidate = nums[0];
    int count = 1;

    for (int i = 1; i < nums.length; i++) {
        if (count == 0) {
            candidate = nums[i];
            count = 1;
        } else if (nums[i] == candidate) {
            count++;
        } else {
            count--;
        }
    }

    return candidate;
}
```

**Time Complexity**: O(n)  
**Space Complexity**: O(1)

## Key Insights
- Majority element appears > n/2 times; it "survives" all cancellations
- Each non-match decrements count; candidate resets when count hits 0

## Tips and Tricks
- "It's like voting: majority cancels all opposition and still has votes left"

## Related Problems
- LC 229 Majority Element II
