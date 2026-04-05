# LC 49: Group Anagrams

**Link**: [leetcode.com/problems/group-anagrams](https://leetcode.com/problems/group-anagrams/)

## Problem
Given an array of strings `strs`, group the anagrams together.

## Optimized Approach: HashMap + Sorted Key

```java
public List<List<String>> groupAnagrams(String[] strs) {
    Map<String, List<String>> map = new HashMap<>();

    for (String s : strs) {
        char[] chars = s.toCharArray();
        Arrays.sort(chars);
        String key = new String(chars);

        map.computeIfAbsent(key, k -> new ArrayList<>()).add(s);
    }

    return new ArrayList<>(map.values());
}
```

**Time Complexity**: O(n * k log k)  
**Space Complexity**: O(n * k)

## Key Insights
- Anagrams share same sorted-character representation
- HashMap groups strings by canonical key

## Tips and Tricks
- Use hashing when constant-time membership or frequency lookup matters more than order.
- Be explicit about what the key represents: value, index relation, or prefix state.
- Frequency maps and prefix maps solve many array problems that look quadratic at first.

## Related Problems
- LC 438 Find All Anagrams in a String
