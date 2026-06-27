# Two Pointers Approach: HashMap Complement Lookup & Multi-Sum Pattern

## 🎯 When to Use
- Need to find pairs/complements that satisfy a condition
- "Two elements that sum to X"
- "Find matching pair"
- Multiple elements summing to target
- O(n) to O(n²) time with flexible space usage

## 📝 Master Template

```java
public int[] twoSum(int[] nums, int target) {
    // Step 1: Create HashMap to store value -> index
    Map<Integer, Integer> map = new HashMap<>();
    
    // Step 2: Iterate through array
    for (int i = 0; i < nums.length; i++) {
        // Step 3: Calculate what we're looking for
        int complement = target - nums[i];
        
        // Step 4: Check if complement exists
        if (map.containsKey(complement)) {
            return new int[]{map.get(complement), i};
        }
        
        // Step 5: Store current element
        map.put(nums[i], i);
    }
    
    return new int[]{};  // No solution
}
```

## 🔄 Problem Variations & Modifications

### ✅ LC 1: Two Sum (IMPLEMENTED)
**What changes**: Nothing - this IS the template
**Difficulty**: Easy
**Key Points**: 
- Add element AFTER checking (prevents using same element twice)
- Return indices, not values

---

### LC 167: Two Sum II - Input Array Is Sorted
**What changes**: Can use two pointers instead of HashMap
**Difficulty**: Easy
**Modification**:
```java
public int[] twoSum(int[] nums, int target) {
    int left = 0, right = nums.length - 1;
    
    while (left < right) {
        int sum = nums[left] + nums[right];
        if (sum == target) {
            return new int[]{left + 1, right + 1};  // 1-indexed!
        } else if (sum < target) {
            left++;
        } else {
            right--;
        }
    }
    return new int[]{};
}
```
**Trade-off**: O(1) space but requires sorted input

---

### ✅ LC 15: 3Sum (IMPLEMENTED with Two Pointers)
**What changes**: Add outer loop, use two pointers for inner two
**Difficulty**: Medium
**Modification**:
```java
public List<List<Integer>> threeSum(int[] nums) {
    Arrays.sort(nums);  // Required for two pointers
    List<List<Integer>> result = new ArrayList<>();
    
    for (int i = 0; i < nums.length - 2; i++) {
        if (i > 0 && nums[i] == nums[i-1]) continue;  // Skip duplicates
        
        // Two Sum on remaining elements with target = -nums[i]
        int left = i + 1, right = nums.length - 1;
        int target = -nums[i];
        
        while (left < right) {
            int sum = nums[left] + nums[right];
            if (sum == target) {
                result.add(Arrays.asList(nums[i], nums[left], nums[right]));
                // Skip duplicates
                while (left < right && nums[left] == nums[left+1]) left++;
                while (left < right && nums[right] == nums[right-1]) right--;
                left++; right--;
            } else if (sum < target) {
                left++;
            } else {
                right--;
            }
        }
    }
    return result;
}
```
**Key Addition**: Duplicate handling at all three positions

---

### LC 454: 4Sum II
**What changes**: Split into two groups, use HashMap for one half
**Difficulty**: Medium
**Modification**:
```java
public int fourSumCount(int[] A, int[] B, int[] C, int[] D) {
    // Store all sums from A and B
    Map<Integer, Integer> map = new HashMap<>();
    for (int a : A) {
        for (int b : B) {
            map.put(a + b, map.getOrDefault(a + b, 0) + 1);
        }
    }
    
    // Find complements in C and D
    int count = 0;
    for (int c : C) {
        for (int d : D) {
            int complement = -(c + d);
            count += map.getOrDefault(complement, 0);
        }
    }
    return count;
}
```
**Key Change**: Nested loops for each half, count instead of indices

---

## 📊 Complexity Comparison

| Problem | Time | Space | Notes |
|---------|------|-------|-------|
| LC 1 | O(n) | O(n) | HashMap approach |
| LC 167 | O(n) | O(1) | Two pointers on sorted |
| LC 15 | O(n²) | O(1) | Sort + Two pointers |
| LC 454 | O(n²) | O(n²) | HashMap for pair sums |

## 🎓 Learning Path

1. **Start**: LC 1 (Two Sum) - Master the template
2. **Variation**: LC 167 - Learn two pointer alternative
3. **Extension**: LC 15 (3Sum) - Add outer loop
4. **Advanced**: LC 454 - Multiple arrays

## 💡 Key Insights

### When HashMap is Better:
- Unsorted input
- Need to preserve indices
- Single pass preferred

### When Two Pointers is Better:
- Input is sorted (or can be sorted)
- Don't need original indices
- Want O(1) space

### Common Pitfalls:
1. ❌ Adding element before checking (uses same element twice)
2. ❌ Not handling duplicates in 3Sum/4Sum
3. ❌ Forgetting that sorting loses original indices
4. ❌ Not considering integer overflow for large sums

## 🔗 Related Problems

- LC 18: 4Sum (3Sum + outer loop)
- LC 259: 3Sum Smaller (count instead of collect)
- LC 16: 3Sum Closest (track closest instead of exact)
- LC 611: Valid Triangle Number (similar 3Sum structure)

## 📝 Practice Checklist

- [ ] Implement LC 1 from memory
- [ ] Convert LC 1 solution to handle sorted input (LC 167)
- [ ] Extend to 3Sum (LC 15)
- [ ] Handle 4 arrays (LC 454)
- [ ] Solve without looking at notes

## Tips and Tricks

1. **Always start with brute force**: "I could check all pairs in O(n²)..."
2. **Then optimize**: "Using a HashMap, I can reduce to O(n)..."
3. **Discuss trade-offs**: "This uses O(n) space for O(n) time..."
4. **Mention alternatives**: "If input were sorted, I could use two pointers..."
5. **Handle edge cases**: Empty array, no solution, duplicates
