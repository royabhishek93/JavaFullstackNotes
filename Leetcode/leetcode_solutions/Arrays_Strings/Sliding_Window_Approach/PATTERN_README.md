# Sliding Window Approach: HashMap/Set Pattern

## 🎯 When to Use
- "Substring" or "Subarray" problems
- Need to find contiguous sequence with property
- Window can expand/shrink based on condition
- Keywords: longest, shortest, contains, without repeating

## 📝 Master Template

```java
public int slidingWindowTemplate(String s) {
    // Step 1: Data structure to track window contents
    Map<Character, Integer> window = new HashMap<>();
    
    // Step 2: Initialize pointers and result
    int left = 0;
    int result = 0;  // or Integer.MAX_VALUE for minimum
    
    // Step 3: Expand window with right pointer
    for (int right = 0; right < s.length(); right++) {
        char rightChar = s.charAt(right);
        
        // Add to window
        window.put(rightChar, window.getOrDefault(rightChar, 0) + 1);
        
        // Step 4: Shrink window if condition violated
        while (/* condition is violated */) {
            char leftChar = s.charAt(left);
            window.put(leftChar, window.get(leftChar) - 1);
            if (window.get(leftChar) == 0) {
                window.remove(leftChar);
            }
            left++;
        }
        
        // Step 5: Update result with valid window
        result = Math.max(result, right - left + 1);  // For maximum
        // result = Math.min(result, right - left + 1);  // For minimum
    }
    
    return result;
}
```

## 🔄 Problem Variations & Modifications

### ✅ LC 3: Longest Substring Without Repeating Characters (IMPLEMENTED)
**What changes**: Use HashMap to track last seen index, jump left pointer
**Difficulty**: Medium
**Key Modification**:
```java
Map<Character, Integer> lastSeen = new HashMap<>();
int left = 0, maxLength = 0;

for (int right = 0; right < s.length(); right++) {
    char c = s.charAt(right);
    
    // If seen before and within current window
    if (lastSeen.containsKey(c)) {
        left = Math.max(left, lastSeen.get(c) + 1);
    }
    
    lastSeen.put(c, right);
    maxLength = Math.max(maxLength, right - left + 1);
}
```
**Key Point**: Use Math.max for left pointer (handles overlapping characters)

---

### LC 76: Minimum Window Substring ⭐ HARD
**What changes**: Track target character counts, shrink when all found
**Difficulty**: Hard
**Modification**:
```java
public String minWindow(String s, String t) {
    Map<Character, Integer> target = new HashMap<>();
    Map<Character, Integer> window = new HashMap<>();
    
    // Build target map
    for (char c : t.toCharArray()) {
        target.put(c, target.getOrDefault(c, 0) + 1);
    }
    
    int left = 0, minLen = Integer.MAX_VALUE, minStart = 0;
    int matched = 0;  // How many unique chars have met requirement
    
    for (int right = 0; right < s.length(); right++) {
        char rightChar = s.charAt(right);
        window.put(rightChar, window.getOrDefault(rightChar, 0) + 1);
        
        // If this char count matches target, increment matched
        if (target.containsKey(rightChar) && 
            window.get(rightChar).equals(target.get(rightChar))) {
            matched++;
        }
        
        // Shrink window when all chars matched
        while (matched == target.size()) {
            // Update result
            if (right - left + 1 < minLen) {
                minLen = right - left + 1;
                minStart = left;
            }
            
            // Shrink from left
            char leftChar = s.charAt(left);
            window.put(leftChar, window.get(leftChar) - 1);
            
            if (target.containsKey(leftChar) && 
                window.get(leftChar) < target.get(leftChar)) {
                matched--;
            }
            left++;
        }
    }
    
    return minLen == Integer.MAX_VALUE ? "" : s.substring(minStart, minStart + minLen);
}
```
**Key Changes**:
- Two maps: target and window
- Track "matched" count
- Shrink when all characters satisfied
- Minimize window length

---

### LC 438: Find All Anagrams in a String
**What changes**: Fixed window size, track when window matches pattern
**Difficulty**: Medium
**Modification**:
```java
public List<Integer> findAnagrams(String s, String p) {
    List<Integer> result = new ArrayList<>();
    if (s.length() < p.length()) return result;
    
    Map<Character, Integer> target = new HashMap<>();
    Map<Character, Integer> window = new HashMap<>();
    
    // Build target map
    for (char c : p.toCharArray()) {
        target.put(c, target.getOrDefault(c, 0) + 1);
    }
    
    int windowSize = p.length();
    
    for (int right = 0; right < s.length(); right++) {
        // Expand window
        char rightChar = s.charAt(right);
        window.put(rightChar, window.getOrDefault(rightChar, 0) + 1);
        
        // Shrink window if size exceeded
        if (right >= windowSize) {
            char leftChar = s.charAt(right - windowSize);
            window.put(leftChar, window.get(leftChar) - 1);
            if (window.get(leftChar) == 0) {
                window.remove(leftChar);
            }
        }
        
        // Check if window matches target
        if (window.equals(target)) {
            result.add(right - windowSize + 1);
        }
    }
    
    return result;
}
```
**Key Changes**:
- Fixed window size = pattern length
- Slide window by removing left character
- Check if entire window matches target

---

## 📊 Pattern Recognition

| Problem | Data Structure | Condition | Window Type |
|---------|---|---|---|
| LC 3 | HashMap (chars) | No duplicates | Variable, expand/shrink |
| LC 76 | 2 HashMaps | All chars covered | Variable, minimize |
| LC 438 | HashMap + fixed size | Window matches | Fixed, slide |

## 💡 Key Insights

- Two pointers (left/right) move in different directions
- Right always expands; left shrinks when condition violated
- Use HashMap to track character frequencies
- For fixed windows, update result AFTER shrinking

## Tips and Tricks

1. **Identify the window constraint**: What makes a window valid?
2. **Use right pointer to expand**: Add characters to window
3. **Use left pointer to shrink**: Remove characters until valid
4. **Handle edge cases**: Empty strings, single character, etc.
