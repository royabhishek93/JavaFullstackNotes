# Q8: String Compression (In-place)

**Study Time:** 7-9 minutes | **Frequency:** 60% in interviews | **Difficulty:** ⭐⭐⭐

---

## 🤔 Problem Statement

Given an array of characters, **compress it in-place** by replacing consecutive duplicate characters with the character followed by the count of repetitions.

**Rules:**
- Modify the array in-place (no extra array)
- If count is 1, write only the character (not "a1")
- Return the new length of the compressed array
- Final compressed array should occupy the first part of the input array

**Example:**
```
Input:  ['a','a','a','b','b','c']
Output: 5 → ['a','3','b','2','c']
Explanation: "aaa" becomes "a3", "bb" becomes "b2", "c" stays "c"

Input:  ['a','b','c']
Output: 3 → ['a','b','c']
Explanation: No compression (all single occurrences)

Input:  ['a','a','a','a','a','a','a','a','a','a','a','a']
Output: 4 → ['a','1','2']
Explanation: 12 a's become "a12" (3 characters: 'a', '1', '2')
```

---

## 🧠 Key Principle: Two-Pointer Write Strategy

**Algorithm:**
1. **Read pointer**: Traverse through input array
2. **Write pointer**: Track where to write compressed output
3. Count consecutive characters
4. Write character + count (if > 1) to write pointer position
5. Return write pointer position (new length)

**Critical Insight:**
- Compressed output never gets longer than the input
- So we can safely overwrite from left to right
- `write` never goes past `read`

---

## ✅ Correct Solution

```java
public static int compress(char[] chars) {
    if (chars == null || chars.length == 0) {
        return 0;
    }
    
    int write = 0;  // Position to write compressed output
    int read = 0;   // Position to read input
    
    while (read < chars.length) {
        char currentChar = chars[read];
        int count = 0;
        
        // Count consecutive occurrences
        while (read < chars.length && chars[read] == currentChar) {
            read++;
            count++;
        }
        
        // Write character
        chars[write++] = currentChar;
        
        // Write count if > 1
        if (count > 1) {
            // Convert count to characters
            String countStr = String.valueOf(count);
            for (char c : countStr.toCharArray()) {
                chars[write++] = c;
            }
        }
    }
    
    return write;
}
```

---

## 📊 Step-by-Step Walkthrough

### Example: `['a','a','a','b','b','c']`

| Step | read | write | currentChar | count | Action | Array State |
|------|------|-------|-------------|-------|--------|-------------|
| 0 | 0 | 0 | 'a' | 0 | Start | `[a,a,a,b,b,c]` |
| 1 | 3 | 0 | 'a' | 3 | Count a's (read 0→3) | `[a,a,a,b,b,c]` |
| 2 | 3 | 1 | 'a' | 3 | Write 'a' at write=0 | `[a,a,a,b,b,c]` |
| 3 | 3 | 2 | 'a' | 3 | Write '3' at write=1 | `[a,3,a,b,b,c]` |
| 4 | 5 | 2 | 'b' | 2 | Count b's (read 3→5) | `[a,3,a,b,b,c]` |
| 5 | 5 | 3 | 'b' | 2 | Write 'b' at write=2 | `[a,3,b,b,b,c]` |
| 6 | 5 | 4 | 'b' | 2 | Write '2' at write=3 | `[a,3,b,2,b,c]` |
| 7 | 6 | 4 | 'c' | 1 | Count c's (read 5→6) | `[a,3,b,2,b,c]` |
| 8 | 6 | 5 | 'c' | 1 | Write 'c' at write=4 | `[a,3,b,2,c,c]` |
| 9 | 6 | 5 | - | - | Done (count=1, skip) | `[a,3,b,2,c,c]` |

**Final Result:** 
- Compressed length: 5
- Valid output: `['a','3','b','2','c']` (first 5 elements)

---

## 📊 Test Cases

### Test Case 1: Basic Compression
```java
char[] input = {'a','a','a','b','b','c'};
int newLength = compress(input);
System.out.println(newLength);  // 5
System.out.println(Arrays.toString(Arrays.copyOf(input, newLength)));
```
**Expected Output:** 
```
5
[a, 3, b, 2, c]
```

### Test Case 2: No Compression Needed
```java
char[] input = {'a','b','c'};
int newLength = compress(input);
System.out.println(newLength);  // 3
System.out.println(Arrays.toString(Arrays.copyOf(input, newLength)));
```
**Expected Output:**
```
3
[a, b, c]
```

### Test Case 3: Large Count (Multi-digit)
```java
char[] input = new char[12];
Arrays.fill(input, 'a');  // ['a','a','a','a','a','a','a','a','a','a','a','a']
int newLength = compress(input);
System.out.println(newLength);  // 3
System.out.println(Arrays.toString(Arrays.copyOf(input, newLength)));
```
**Expected Output:**
```
3
[a, 1, 2]
```

### Test Case 4: All Same Character (Small Count)
```java
char[] input = {'a','a'};
int newLength = compress(input);
System.out.println(newLength);  // 2
System.out.println(Arrays.toString(Arrays.copyOf(input, newLength)));
```
**Expected Output:**
```
2
[a, 2]
```

### Test Case 5: Single Character
```java
char[] input = {'a'};
int newLength = compress(input);
System.out.println(newLength);  // 1
System.out.println(Arrays.toString(Arrays.copyOf(input, newLength)));
```
**Expected Output:**
```
1
[a]
```

### Test Case 6: Alternating Characters
```java
char[] input = {'a','b','a','b','a','b'};
int newLength = compress(input);
System.out.println(newLength);  // 6
System.out.println(Arrays.toString(Arrays.copyOf(input, newLength)));
```
**Expected Output:**
```
6
[a, b, a, b, a, b]
```

---

## Interview Q&A

### Q1: "What's the time and space complexity?"

**Answer:**
```
Time Complexity: O(n)
- We scan the array once with `read`
- Each character is processed once
- Converting `count` to digits is O(log n)

Space Complexity: O(1)
- Only a few variables are used
- The input array is modified in place
- `String.valueOf(count)` creates a small temporary string (O(log n))

Pure O(1) space (no String.valueOf):
while (count > 0) {
        chars[write++] = (char)('0' + count % 10);
        count /= 10;
}
// Digits are reversed; reverse that range if needed.
```

### Q2: "Why is it safe to overwrite the input array from left to right?"

**Answer:**
```
Key Observation: Compressed length ≤ Original length

Case 1: Single occurrence
- Original: 1 character
- Compressed: 1 character
- Same length!

Case 2: Two consecutive characters
- Original: 2 characters ("aa")
- Compressed: 2 characters ("a2")
- Same length!

Case 3: Three or more consecutive characters
- Original: n characters ("aaa...")
- Compressed: 1 char + digits (e.g., "a3", "a10", "a100")
- For n = 3-9: 2 chars (e.g., "a3") < 3+ original
- For n = 10-99: 3 chars (e.g., "a10") < 10+ original
- Always: compressed < original

Example proving safety:
['a','a','a','b','b','c']
     ^                    read at index 0-2 (reading 'a's)
 ^                        write at index 0 (safe, read ahead)
 ['a','3','a','b','b','c']
         ^                write at index 1 (still safe)

`write` never exceeds `read`, so overwriting is safe.
```

### Q3: "How do you handle counts with multiple digits?"

**Answer:**
```java
// Approach 1: Using String.valueOf (Simple)
if (count > 1) {
    String countStr = String.valueOf(count);
    for (char c : countStr.toCharArray()) {
        chars[write++] = c;
    }
}

// Example: count = 123
// countStr = "123"
// Writes: '1', '2', '3' sequentially

// Approach 2: Manual digit extraction (Pure O(1) space)
if (count > 1) {
    int start = write;
    
    // Extract digits (writes in reverse)
    while (count > 0) {
        chars[write++] = (char)('0' + count % 10);
        count /= 10;
    }
    
    // Reverse the digits
    reverse(chars, start, write - 1);
}

private void reverse(char[] chars, int left, int right) {
    while (left < right) {
        char temp = chars[left];
        chars[left] = chars[right];
        chars[right] = temp;
        left++;
        right--;
    }
}

// Example: count = 123
// After while loop: chars[write...] = ['3','2','1']
// After reverse: chars[write...] = ['1','2','3']
```

### Q4: "What if compression makes the array longer?"

**Answer:**
```
Problem states: Return new length of compressed array.
Interpretation: Always perform compression, even if longer.

But in real-world scenarios, you might want:

public static int compressOptimized(char[] chars) {
    int write = 0;
    int read = 0;
    int originalLength = chars.length;
    
    // First pass: calculate compressed length
    int compressedLength = 0;
    int i = 0;
    while (i < chars.length) {
        int count = 1;
        while (i + count < chars.length && chars[i + count] == chars[i]) {
            count++;
        }
        compressedLength++;  // Character
        if (count > 1) {
            compressedLength += String.valueOf(count).length();
        }
        i += count;
    }
    
    // If compression doesn't save space, return original
    if (compressedLength >= originalLength) {
        return originalLength;
    }
    
    // Otherwise, compress normally
    // ... (same compression logic)
}

Example where compression makes it longer:
['a','b','c'] → would become ['a','b','c'] (no change, already optimal)
NOT ['a','1','b','1','c','1'] (that would be wasteful)
```

### Q5: "How do you test this in an interview?"

**Answer:**
```
Always test these cases:

1. All same characters: ['a','a','a','a','a']
   - Tests basic compression: ['a','5']

2. No compression needed: ['a','b','c']
   - Tests single occurrences: ['a','b','c']

3. Multi-digit count: ['a' × 12]
   - Tests digit handling: ['a','1','2']

4. Alternating: ['a','b','a','b']
   - Tests no compression: ['a','b','a','b']

5. Two of each: ['a','a','b','b']
   - Tests count=2: ['a','2','b','2']

6. Edge: ['a']
   - Tests single element: ['a']

7. Edge: []
   - Tests empty array: []

Walk through one manually during interview to show understanding!
```

---

## Common Mistakes

### ❌ Mistake 1: Not Handling Multi-Digit Counts
```java
// WRONG - Only handles single digit counts
if (count > 1) {
    chars[write++] = (char)('0' + count);  // Breaks for count > 9!
}

// CORRECT
if (count > 1) {
    String countStr = String.valueOf(count);
    for (char c : countStr.toCharArray()) {
        chars[write++] = c;
    }
}

// Example: count = 12
// Wrong: chars[write] = (char)('0' + 12) = (char)(48 + 12) = ':' (wrong!)
// Correct: chars[write...] = ['1','2']
```

### ❌ Mistake 2: Writing Count for Single Occurrence
```java
// WRONG - Writes "a1" instead of "a"
chars[write++] = currentChar;
String countStr = String.valueOf(count);
for (char c : countStr.toCharArray()) {
    chars[write++] = c;  // Always writes count!
}

// CORRECT - Only write count if > 1
chars[write++] = currentChar;
if (count > 1) {
    String countStr = String.valueOf(count);
    for (char c : countStr.toCharArray()) {
        chars[write++] = c;
    }
}
```

### ❌ Mistake 3: Not Returning Correct Length
```java
// WRONG - Returns original length
return chars.length;

// CORRECT - Returns compressed length
return write;

// Example: ['a','a','a','b','b','c']
// After compression: ['a','3','b','2','c','c']
// Should return: 5 (not 6!)
```

### ❌ Mistake 4: Infinite Loop with Wrong Condition
```java
// WRONG - Doesn't advance read pointer
while (read < chars.length && chars[read] == currentChar) {
    count++;
    // Missing: read++
}

// CORRECT
while (read < chars.length && chars[read] == currentChar) {
    count++;
    read++;
}
```

---

## Complete Working Code

```java
import java.util.*;

public class StringCompression {
    
    public static int compress(char[] chars) {
        if (chars == null || chars.length == 0) {
            return 0;
        }
        
        int write = 0;
        int read = 0;
        
        while (read < chars.length) {
            char currentChar = chars[read];
            int count = 0;
            
            // Count consecutive occurrences
            while (read < chars.length && chars[read] == currentChar) {
                read++;
                count++;
            }
            
            // Write character
            chars[write++] = currentChar;
            
            // Write count if > 1
            if (count > 1) {
                String countStr = String.valueOf(count);
                for (char c : countStr.toCharArray()) {
                    chars[write++] = c;
                }
            }
        }
        
        return write;
    }
    
    // Helper to print compressed array
    public static void printCompressed(char[] chars) {
        int newLength = compress(chars);
        System.out.println("Length: " + newLength);
        System.out.println("Array: " + Arrays.toString(Arrays.copyOf(chars, newLength)));
    }

    public static void main(String[] args) {
        // Test case 1
        char[] test1 = {'a','a','a','b','b','c'};
        printCompressed(test1);  // 5, [a, 3, b, 2, c]
        
        // Test case 2
        char[] test2 = {'a','b','c'};
        printCompressed(test2);  // 3, [a, b, c]
        
        // Test case 3
        char[] test3 = new char[12];
        Arrays.fill(test3, 'a');
        printCompressed(test3);  // 3, [a, 1, 2]
        
        // Test case 4
        char[] test4 = {'a','a'};
        printCompressed(test4);  // 2, [a, 2]
        
        // Test case 5
        char[] test5 = {'a'};
        printCompressed(test5);  // 1, [a]
    }
}
```

---

## Key Takeaways

| Concept | Why Important | Interview Score |
|---------|---------------|-----------------|
| Two-pointer technique | In-place modification | ⭐⭐⭐⭐⭐ |
| Write-ahead safety | Array manipulation | ⭐⭐⭐⭐ |
| Multi-digit handling | Edge case awareness | ⭐⭐⭐⭐ |
| O(1) space solution | Space optimization | ⭐⭐⭐⭐ |
| Careful counting logic | Avoiding off-by-one errors | ⭐⭐⭐⭐ |

---

**Priority:** ✅ SHOULD KNOW (Common problem, tests in-place algorithm skills)

**Related Problems:**
- String Compression II
- Encode and Decode Strings
- Run Length Encoding

---

**Last Updated:** March 1, 2026
