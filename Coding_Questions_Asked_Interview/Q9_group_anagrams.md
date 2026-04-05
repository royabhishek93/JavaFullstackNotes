# Q9: Group Anagrams

**Study Time:** 8-10 minutes | **Frequency:** 80% in interviews | **Difficulty:** ⭐⭐⭐

---

## 🤔 Problem Statement

Given an array of strings, **group all anagrams together**. An anagram is a word formed by rearranging the letters of another word.

**Example:**
```
Input:  ["eat","tea","tan","ate","nat","bat"]
Output: [["eat","tea","ate"],["tan","nat"],["bat"]]

Explanation:
- "eat", "tea", "ate" are anagrams (all contain e, a, t)
- "tan", "nat" are anagrams (all contain t, a, n)
- "bat" is alone
```

**Note:** 
- Order of groups doesn't matter
- Order within each group doesn't matter

---

## 🧠 Key Principle: Hash by Canonical Form

**Core Insight:** Anagrams have the **same characters with same frequencies**.

**Two approaches to create a unique key:**
1. **Sorted string**: "eat" → "aet", "tea" → "aet", "ate" → "aet" (same key!)
2. **Character frequency**: "eat" → "e1a1t1", "tea" → "e1a1t1" (same key!)

**Algorithm:**
1. Create a HashMap: `key → list of anagrams`
2. For each string, compute canonical key
3. Add string to the list for that key
4. Return all values from HashMap

---

## ✅ Solution 1: Sorted String as Key

```java
public static List<List<String>> groupAnagrams(String[] strs) {
    if (strs == null || strs.length == 0) {
        return new ArrayList<>();
    }
    
    // Map: sorted string → list of anagrams
    Map<String, List<String>> map = new HashMap<>();
    
    for (String str : strs) {
        // Create canonical form by sorting
        char[] chars = str.toCharArray();
        Arrays.sort(chars);
        String key = new String(chars);
        
        // Add to map
        map.putIfAbsent(key, new ArrayList<>());
        map.get(key).add(str);
    }
    
    return new ArrayList<>(map.values());
}
```

**Time Complexity:** O(n × k log k)
- n = number of strings
- k = maximum length of a string
- Sorting each string: O(k log k)

**Space Complexity:** O(n × k)
- Storing all strings in the map

---

## 🚀 Solution 2: Character Count as Key (Optimized)

Instead of sorting (O(k log k)), use character frequency (O(k)):

```java
public static List<List<String>> groupAnagramsOptimized(String[] strs) {
    if (strs == null || strs.length == 0) {
        return new ArrayList<>();
    }
    
    Map<String, List<String>> map = new HashMap<>();
    
    for (String str : strs) {
        // Create key from character frequencies
        int[] count = new int[26];  // Assuming lowercase English letters
        for (char c : str.toCharArray()) {
            count[c - 'a']++;
        }
        
        // Convert count array to string key
        // E.g., "eat" → "1#0#0#0#1#0...#1#0..." (e=1, a=1, t=1)
        StringBuilder keyBuilder = new StringBuilder();
        for (int i = 0; i < 26; i++) {
            keyBuilder.append(count[i]).append('#');
        }
        String key = keyBuilder.toString();
        
        // Add to map
        map.putIfAbsent(key, new ArrayList<>());
        map.get(key).add(str);
    }
    
    return new ArrayList<>(map.values());
}
```

**Time Complexity:** O(n × k)
- n = number of strings
- k = maximum length of a string
- Counting frequencies: O(k)
- Building key: O(26) = O(1)

**Space Complexity:** O(n × k)
- Same as Solution 1

---

## 📊 Step-by-Step Walkthrough

### Example: `["eat","tea","tan","ate","nat","bat"]`

**Using Sorted Key Approach:**

| Step | String | Sort | Key | Map State |
|------|--------|------|-----|-----------|
| 1 | "eat" | "aet" | "aet" | `{"aet": ["eat"]}` |
| 2 | "tea" | "aet" | "aet" | `{"aet": ["eat","tea"]}` |
| 3 | "tan" | "ant" | "ant" | `{"aet": ["eat","tea"], "ant": ["tan"]}` |
| 4 | "ate" | "aet" | "aet" | `{"aet": ["eat","tea","ate"], "ant": ["tan"]}` |
| 5 | "nat" | "ant" | "ant" | `{"aet": ["eat","tea","ate"], "ant": ["tan","nat"]}` |
| 6 | "bat" | "abt" | "abt" | `{"aet": [...], "ant": [...], "abt": ["bat"]}` |

**Final Groups:** `[["eat","tea","ate"], ["tan","nat"], ["bat"]]`

---

## 📊 Test Cases

### Test Case 1: Basic Example
```java
String[] strs = {"eat","tea","tan","ate","nat","bat"};
List<List<String>> result = groupAnagrams(strs);
System.out.println(result);
```
**Expected Output:**
```
[["eat","tea","ate"], ["tan","nat"], ["bat"]]
```
(Order may vary)

### Test Case 2: Empty Strings
```java
String[] strs = {""};
List<List<String>> result = groupAnagrams(strs);
System.out.println(result);
```
**Expected Output:**
```
[[""]]
```

### Test Case 3: Single Character Strings
```java
String[] strs = {"a"};
List<List<String>> result = groupAnagrams(strs);
System.out.println(result);
```
**Expected Output:**
```
[["a"]]
```

### Test Case 4: All Same Anagrams
```java
String[] strs = {"abc","bca","cab"};
List<List<String>> result = groupAnagrams(strs);
System.out.println(result);
```
**Expected Output:**
```
[["abc","bca","cab"]]
```

### Test Case 5: No Anagrams
```java
String[] strs = {"abc","def","ghi"};
List<List<String>> result = groupAnagrams(strs);
System.out.println(result);
```
**Expected Output:**
```
[["abc"], ["def"], ["ghi"]]
```
(Order may vary)

### Test Case 6: Duplicates
```java
String[] strs = {"eat","eat","tea"};
List<List<String>> result = groupAnagrams(strs);
System.out.println(result);
```
**Expected Output:**
```
[["eat","eat","tea"]]
```

---

## Interview Q&A

### Q1: "Why is sorting approach O(n × k log k) and not O(n log n)?"

**Answer:**
```
Common Misconception: "We're sorting n strings, so O(n log n)"
- Wrong! We're not sorting the array of strings.
- We're sorting the CHARACTERS within each string.

Correct Analysis:
- n strings in array
- Each string has k characters
- Sorting k characters: O(k log k)
- Do this n times: O(n × k log k)

Example:
strs = ["eat", "tea", "tan"] (n=3)
- "eat": sort 3 chars → O(3 log 3)
- "tea": sort 3 chars → O(3 log 3)
- "tan": sort 3 chars → O(3 log 3)
Total: O(3 × 3 log 3) = O(n × k log k)

NOT sorting the array ["eat","tea","tan"] which would be O(n log n).
```

### Q2: "Why does the character count approach use '#' delimiter?"

**Answer:**
```
Problem: Without delimiter, different frequencies create same key:

Example 1:
"aab" → count = [2,1,0,...] → key = "210..."
"aba" → count = [2,1,0,...] → key = "210..." ✓ Same (correct, they're anagrams)

Example 2 (PROBLEM):
String with 'a' appearing 12 times and 'b' appearing 1 time:
count = [12,1,0,...] → key = "1210..." without delimiter

String with 'a' appearing 1 time and 'b' appearing 21 times:
count = [1,21,0,...] → key = "1210..." without delimiter

These are NOT anagrams but have the same key! ❌

Solution with delimiter:
[12,1,0,...] → "12#1#0#..."
[1,21,0,...] → "1#21#0#..."
Different keys! ✓

Alternative: Use fixed-width formatting
[12,1,0] → "012001000" (3 digits per count)
But delimiter is simpler and more flexible.
```

### Q3: "Can we use the count array itself as a HashMap key?"

**Answer:**
```java
// ATTEMPT 1: Using int[] as key (DOESN'T WORK!)
Map<int[], List<String>> map = new HashMap<>();
int[] count1 = {1,0,0,...};
int[] count2 = {1,0,0,...};

map.put(count1, new ArrayList<>());
System.out.println(map.containsKey(count2));  // FALSE! ❌

// Why? Arrays use reference equality, not content equality
// count1 and count2 are different objects even with same values

// ATTEMPT 2: Convert to List (Works but inefficient)
Map<List<Integer>, List<String>> map = new HashMap<>();
List<Integer> key = Arrays.stream(count).boxed().collect(Collectors.toList());
map.putIfAbsent(key, new ArrayList<>());
// Works ✓ but creates many Integer objects (slow)

// ATTEMPT 3: Use String as key (BEST)
StringBuilder keyBuilder = new StringBuilder();
for (int c : count) {
    keyBuilder.append(c).append('#');
}
String key = keyBuilder.toString();
// Works ✓ and efficient

Conclusion: Strings are better HashMap keys for this problem.
```

### Q4: "What if the strings contain Unicode characters, not just lowercase English?"

**Answer:**
```java
// Sorted approach (Works for ANY characters)
public static List<List<String>> groupAnagramsUnicode(String[] strs) {
    Map<String, List<String>> map = new HashMap<>();
    
    for (String str : strs) {
        char[] chars = str.toCharArray();
        Arrays.sort(chars);  // Sorts ANY characters
        String key = new String(chars);
        
        map.putIfAbsent(key, new ArrayList<>());
        map.get(key).add(str);
    }
    
    return new ArrayList<>(map.values());
}

// Character count approach (Needs modification)
// Can't use int[26] for Unicode (too many possible characters!)
// Use HashMap<Character, Integer> instead:

public static List<List<String>> groupAnagramsUnicodeOptimized(String[] strs) {
    Map<String, List<String>> map = new HashMap<>();
    
    for (String str : strs) {
        // Count with HashMap
        Map<Character, Integer> count = new HashMap<>();
        for (char c : str.toCharArray()) {
            count.put(c, count.getOrDefault(c, 0) + 1);
        }
        
        // Convert to sorted key (important: must be sorted for consistency)
        StringBuilder keyBuilder = new StringBuilder();
        count.entrySet().stream()
            .sorted(Map.Entry.comparingByKey())
            .forEach(e -> keyBuilder.append(e.getKey()).append(e.getValue()).append('#'));
        String key = keyBuilder.toString();
        
        map.putIfAbsent(key, new ArrayList<>());
        map.get(key).add(str);
    }
    
    return new ArrayList<>(map.values());
}

Recommendation: For Unicode, sorting is simpler and faster in practice.
```

### Q5: "What's the space complexity breakdown?"

**Answer:**
```
Space Complexity: O(n × k)

Breakdown:
1. HashMap: O(n)
   - At most n entries (each string could be unique)
   
2. Lists in HashMap: O(n × k_avg)
   - All strings stored in lists: n strings × k characters each
   
3. Keys in HashMap: O(n × k)
   - Each key is a string of length k (sorted or count-based)
   
4. Temporary variables: O(k)
   - char[] for sorting: O(k)
   - int[26] for counting: O(1)
   - StringBuilder for key: O(26) or O(k)

Total: O(n × k) dominated by storing the actual strings

Can we do better? NO
- Must store all n strings in output
- Each string has k characters
- Minimum space: O(n × k)
```

---

## Common Mistakes

### ❌ Mistake 1: Comparing Unsorted Strings
```java
// WRONG - Tries to compare strings directly
for (String s1 : strs) {
    for (String s2 : strs) {
        if (areAnagrams(s1, s2)) {
            // Group them
        }
    }
}
// Time Complexity: O(n²) for comparisons + O(k) per comparison = O(n² × k)
// Too slow!

// CORRECT - Use HashMap with canonical key
// Time Complexity: O(n × k log k) or O(n × k)
```

### ❌ Mistake 2: Using Array as HashMap Key
```java
// WRONG - Arrays don't work as HashMap keys
int[] count = new int[26];
map.put(count, list);  // Uses reference equality, not content!

// CORRECT - Convert to String
String key = Arrays.toString(count);  // or use StringBuilder
map.put(key, list);
```

### ❌ Mistake 3: Not Handling Empty Strings
```java
// POTENTIAL ISSUE
String[] strs = {"", "a", ""};
// Empty strings should group together: [["", ""], ["a"]]

// Code handles this correctly (sorted "" = "", count of "" = "0#0#...")
// But test it!
```

### ❌ Mistake 4: Modifying Input Array
```java
// WRONG - Modifying input (if not allowed)
for (int i = 0; i < strs.length; i++) {
    strs[i] = sortedString(strs[i]);  // Corrupts input!
}

// CORRECT - Don't modify input
for (String str : strs) {
    String key = sortedString(str);  // Use key, keep str unchanged
    // ...
}
```

---

## Complete Working Code

```java
import java.util.*;

public class GroupAnagrams {
    
    // Solution 1: Sorted String as Key
    public static List<List<String>> groupAnagrams(String[] strs) {
        if (strs == null || strs.length == 0) {
            return new ArrayList<>();
        }
        
        Map<String, List<String>> map = new HashMap<>();
        
        for (String str : strs) {
            char[] chars = str.toCharArray();
            Arrays.sort(chars);
            String key = new String(chars);
            
            map.putIfAbsent(key, new ArrayList<>());
            map.get(key).add(str);
        }
        
        return new ArrayList<>(map.values());
    }
    
    // Solution 2: Character Count as Key (Optimized)
    public static List<List<String>> groupAnagramsOptimized(String[] strs) {
        if (strs == null || strs.length == 0) {
            return new ArrayList<>();
        }
        
        Map<String, List<String>> map = new HashMap<>();
        
        for (String str : strs) {
            int[] count = new int[26];
            for (char c : str.toCharArray()) {
                count[c - 'a']++;
            }
            
            StringBuilder keyBuilder = new StringBuilder();
            for (int i = 0; i < 26; i++) {
                keyBuilder.append(count[i]).append('#');
            }
            String key = keyBuilder.toString();
            
            map.putIfAbsent(key, new ArrayList<>());
            map.get(key).add(str);
        }
        
        return new ArrayList<>(map.values());
    }

    public static void main(String[] args) {
        // Test case 1
        String[] strs1 = {"eat","tea","tan","ate","nat","bat"};
        System.out.println(groupAnagrams(strs1));
        // Output: [["eat","tea","ate"], ["tan","nat"], ["bat"]]
        
        // Test case 2
        String[] strs2 = {""};
        System.out.println(groupAnagrams(strs2));
        // Output: [[""]]
        
        // Test case 3
        String[] strs3 = {"a"};
        System.out.println(groupAnagrams(strs3));
        // Output: [["a"]]
        
        // Test case 4 - Optimized approach
        String[] strs4 = {"abc","bca","cab"};
        System.out.println(groupAnagramsOptimized(strs4));
        // Output: [["abc","bca","cab"]]
    }
}
```

---

## Key Takeaways

| Concept | Why Important | Interview Score |
|---------|---------------|-----------------|
| HashMap grouping pattern | Common problem-solving technique | ⭐⭐⭐⭐⭐ |
| Canonical form (sorting) | String normalization | ⭐⭐⭐⭐⭐ |
| Character frequency optimization | Time complexity improvement | ⭐⭐⭐⭐ |
| Delimiter in key generation | Avoiding collision bugs | ⭐⭐⭐⭐ |
| Complexity analysis | Understanding tradeoffs | ⭐⭐⭐⭐ |

---

**Priority:** 🔥 MUST KNOW (Asked in 80% of interviews, tests HashMap skills)

**Related Problems:**
- Valid Anagram
- Find All Anagrams in a String
- Group Shifted Strings

---

**Last Updated:** March 1, 2026
