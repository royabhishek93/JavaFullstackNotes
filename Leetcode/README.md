# 🎯 LeetCode Solutions

Personal collection of LeetCode problem solutions with detailed explanations and test cases.

## 📊 Progress Tracker

![](https://img.shields.io/badge/Easy-2-green)
![](https://img.shields.io/badge/Medium-2-orange)
![](https://img.shields.io/badge/Hard-0-red)
![](https://img.shields.io/badge/Total-4-blue)

## 📚 Problems by Topic

### Dynamic Programming (1D Linear)

| # | Problem | Difficulty | Solution | Topics |
|---|---------|------------|----------|--------|
| 70 | [Climbing Stairs](https://leetcode.com/problems/climbing-stairs/) | Easy | [Python](easy/70-climbing-stairs.py) · [Java](easy/70-climbing-stairs.java) | DP, Fibonacci |
| 746 | [Min Cost Climbing Stairs](https://leetcode.com/problems/min-cost-climbing-stairs/) | Easy | [Python](easy/746-min-cost-climbing-stairs.py) · [Java](easy/746-min-cost-climbing-stairs.java) | DP, Greedy |
| 198 | [House Robber](https://leetcode.com/problems/house-robber/) | Medium | [Python](medium/198-house-robber.py) · [Java](medium/198-house-robber.java) | DP, Array |

### Sliding Window (Two Pointers)

| # | Problem | Difficulty | Solution | Topics |
|---|---------|------------|----------|--------|
| 209 | [Minimum Size Subarray Sum](https://leetcode.com/problems/minimum-size-subarray-sum/) | Medium | [Python](medium/209-minimum-size-subarray-sum.py) · [Java](medium/209-minimum-size-subarray-sum.java) | Sliding Window, Array |

## 📁 Repository Structure

```
.
├── easy/           # Easy difficulty problems
├── medium/         # Medium difficulty problems
├── hard/           # Hard difficulty problems
└── README.md       # This file
```

## 🎓 Pattern Templates

### 1D Linear DP Template
```python
# Base cases
dp[0] = base_case_0
dp[1] = base_case_1

# Recurrence relation
for i in range(2, n + 1):
    dp[i] = f(dp[i-1], dp[i-2])
```

**When to use:** Problems where current state depends on previous 1-2 states
- Climbing Stairs: `dp[i] = dp[i-1] + dp[i-2]`
- Min Cost: `dp[i] = min(dp[i-1] + cost[i-1], dp[i-2] + cost[i-2])`
- House Robber: `dp[i] = max(dp[i-1], dp[i-2] + nums[i])`

### Sliding Window Template
```python
left = 0
window_sum = 0
result = initial_value

for right in range(len(array)):
    window_sum += array[right]  # Expand window
    
    # Shrink window while condition is met
    while condition_met(window_sum):
        result = update_result(result, window)
        window_sum -= array[left]  # Shrink from left
        left += 1

return result
```

**When to use:** Contiguous subarray/substring problems with constraint optimization
- **Works only if:** Elements are positive OR mixed but with monotonic property
- **Key insight:** Expand right, shrink left when condition met
- **Common patterns:** Min/max length with sum/count constraint
- Minimum Size Subarray Sum: Find shortest subarray where `sum >= target`

**Critical points:**
- Use `>=` vs `>` carefully based on problem requirement
- Use `while` not `if` to fully optimize window size
- Time: O(n) - each element visited at most twice

## 🚀 How to Use

1. **Browse problems** - Click on any problem name in the table to view on LeetCode
2. **View solution** - Click the language link (e.g., "Python") to see the implementation
3. **Run locally** - Each file includes test cases:
   ```bash
   python easy/70-climbing-stairs.py
   ```

## 💡 Solution Format

Each solution includes:
- Problem description and LeetCode link
- Algorithm approach explanation
- Time and space complexity analysis
- Complete working code
- Test cases with expected outputs

## 📈 Stats by Difficulty

| Difficulty | Solved | Percentage |
|------------|--------|------------|
| Easy       | 2      | 50%        |
| Medium     | 2      | 50%        |
| Hard       | 0      | 0%         |

---

**Last Updated:** February 12, 2026
