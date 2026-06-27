# Dynamic Programming & BFS: Coin Change Pattern

## 🎯 When to Use
- Minimum/maximum coins to reach target amount
- DP unbounded knapsack variation
- Can be solved with DP or BFS (queue-based)
- State: remaining amount, transitions: each coin

## 📝 Master Template - DP Approach

```java
public int coinChange(int[] coins, int amount) {
    // DP[i] = minimum coins needed to make amount i
    int[] dp = new int[amount + 1];
    
    // Initialize with impossible value
    Arrays.fill(dp, amount + 1);
    dp[0] = 0;  // Base case: 0 coins needed for amount 0
    
    // For each amount from 1 to target
    for (int i = 1; i <= amount; i++) {
        // Try each coin
        for (int coin : coins) {
            if (coin <= i) {
                dp[i] = Math.min(dp[i], dp[i - coin] + 1);
            }
        }
    }
    
    return dp[amount] > amount ? -1 : dp[amount];
}
```

## 📝 Master Template - BFS Approach

```java
public int coinChangeBFS(int[] coins, int amount) {
    if (amount == 0) return 0;
    
    Queue<Integer> queue = new LinkedList<>();
    boolean[] visited = new boolean[amount + 1];
    
    queue.add(0);
    visited[0] = true;
    int steps = 0;
    
    while (!queue.isEmpty()) {
        int size = queue.size();
        steps++;
        
        for (int i = 0; i < size; i++) {
            int current = queue.poll();
            
            for (int coin : coins) {
                int next = current + coin;
                
                if (next == amount) return steps;
                
                if (next < amount && !visited[next]) {
                    visited[next] = true;
                    queue.add(next);
                }
            }
        }
    }
    
    return -1;
}
```

## 🔄 Problem Variations & Modifications

### ✅ LC 322: Coin Change (IMPLEMENTED - DP)
**What changes**: Nothing - this IS the DP template
**Difficulty**: Medium
**Approach**: Bottom-up DP, O(n * m) time, O(n) space

---

### LC 518: Coin Change 2 (Count Combinations)
**What changes**: Count ways instead of minimum coins
**Difficulty**: Medium
```java
public int change(int amount, int[] coins) {
    // dp[i] = number of ways to make amount i
    int[] dp = new int[amount + 1];
    dp[0] = 1;  // One way to make 0: no coins
    
    // For each coin (order matters for combinations)
    for (int coin : coins) {
        // For each amount that can use this coin
        for (int i = coin; i <= amount; i++) {
            dp[i] += dp[i - coin];
        }
    }
    
    return dp[amount];
}
```
**Key Change**: Outer loop is coins (not amount), ensures combinations not permutations

---

### LC 377: Combination Sum IV (Permutations)
**What changes**: Count permutations (order matters)
**Difficulty**: Medium
```java
public int combinationSum4(int[] nums, int target) {
    // dp[i] = number of ways to make i
    int[] dp = new int[target + 1];
    dp[0] = 1;
    
    // For each amount (outer loop for permutations)
    for (int i = 1; i <= target; i++) {
        // For each number that can reach this amount
        for (int num : nums) {
            if (num <= i) {
                dp[i] += dp[i - num];
            }
        }
    }
    
    return dp[target];
}
```
**Key Change**: Outer loop is amount (not coins), counts permutations

---

## 📊 DP vs BFS Comparison

| Aspect | DP | BFS |
|--------|----|----|
| Time | O(amount × coins) | O(amount × coins) |
| Space | O(amount) | O(amount) |
| Approach | Bottom-up | Level-by-level |
| Best for | Multiple queries | Single answer |
| Intuition | "How to reach this amount?" | "Shortest path to amount" |

## 💡 Key Insights

### DP Approach:
```java
dp[i] = minimum coins for amount i
dp[i] = min(dp[i], dp[i - coin] + 1) for each coin
```

### BFS Approach:
- Each level = using one more coin
- Breadth-first guarantees minimum steps
- Stop when amount reached

### Combinations vs Permutations:
- **Combinations**: Outer loop coins → `[1,2,2]` and `[2,1,2]` counted once
- **Permutations**: Outer loop amount → `[1,2,2]`, `[2,1,2]`, `[2,2,1]` all counted

## Tips and Tricks

1. **DP is more standard**: Usually ask for coin change
2. **BFS is graph intuition**: "Think of amounts as nodes..."
3. **Discuss initialization**: "Why amount+1 as impossible value?"
4. **Handle edge cases**: amount = 0, no solution, single coin
5. **Compare approaches**: "BFS is easier to understand but DP scales better..."
