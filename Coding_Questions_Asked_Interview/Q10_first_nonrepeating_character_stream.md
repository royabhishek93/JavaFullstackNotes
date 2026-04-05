# Q10: First Non-Repeating Character in Stream

**Study Time:** 10-12 minutes | **Frequency:** 70% in interviews | **Difficulty:** ⭐⭐⭐⭐

---

## 🤔 Problem Statement

Design a data structure that reads characters from a **continuous stream** and efficiently returns the **first non-repeating character** at any point.

**Example:**
```
Stream: a, a, b, c, b
Queries:
- Read 'a' → First non-repeating: 'a'
- Read 'a' → First non-repeating: null (no unique chars)
- Read 'b' → First non-repeating: 'b'
- Read 'c' → First non-repeating: 'b' ('b' came before 'c')
- Read 'b' → First non-repeating: 'c' ('b' is now repeated)
```

**Constraints:**
- Characters arrive one at a time (streaming)
- Must support efficient queries after each character
- Must track order of arrival
- Must track frequency

---

## 🧠 Key Principle: LinkedHashSet + Frequency Map

**Challenge:** Balance between:
1. Finding first non-repeating: Need **order**
2. Checking if character repeats: Need **frequency**
3. Efficiently removing characters: Need **fast removal**

**Data Structures Needed:**
- **HashMap**: Track character frequency
- **LinkedHashSet** (or Doubly Linked List): Maintain insertion order of unique chars
- Alternative: **Queue + HashMap** for explicit order

---

## ✅ Solution 1: LinkedHashSet Approach

```java
class FirstUniqueCharStream {
    
    // Frequency map: character → count
    private Map<Character, Integer> freqMap;
    
    // Maintains insertion order of non-repeating characters
    private LinkedHashSet<Character> uniqueChars;
    
    public FirstUniqueCharStream() {
        freqMap = new HashMap<>();
        uniqueChars = new LinkedHashSet<>();
    }
    
    // Add character to stream - O(1)
    public void add(char ch) {
        // Update frequency
        freqMap.put(ch, freqMap.getOrDefault(ch, 0) + 1);
        
        if (freqMap.get(ch) == 1) {
            // First occurrence: add to unique set
            uniqueChars.add(ch);
        } else {
            // Repeated: remove from unique set
            uniqueChars.remove(ch);
        }
    }
    
    // Get first non-repeating character - O(1)
    public Character getFirstUnique() {
        // LinkedHashSet maintains insertion order
        // First element is the first unique character
        if (uniqueChars.isEmpty()) {
            return null;
        }
        return uniqueChars.iterator().next();
    }
}
```

**Time Complexity:**
- `add()`: O(1) - HashMap put + LinkedHashSet add/remove
- `getFirstUnique()`: O(1) - Get first element from LinkedHashSet

**Space Complexity:** O(n) where n = unique characters seen

---

## 🚀 Solution 2: Queue + HashMap (More Explicit)

```java
class FirstUniqueCharStreamQueue {
    
    // Frequency map: character → count
    private Map<Character, Integer> freqMap;
    
    // Queue maintains order of all characters (including repeating)
    private Queue<Character> queue;
    
    public FirstUniqueCharStreamQueue() {
        freqMap = new HashMap<>();
        queue = new LinkedList<>();
    }
    
    // Add character to stream - O(1)
    public void add(char ch) {
        freqMap.put(ch, freqMap.getOrDefault(ch, 0) + 1);
        queue.offer(ch);
    }
    
    // Get first non-repeating character - O(n) worst case
    public Character getFirstUnique() {
        // Remove repeated characters from front of queue
        while (!queue.isEmpty() && freqMap.get(queue.peek()) > 1) {
            queue.poll();
        }
        
        return queue.isEmpty() ? null : queue.peek();
    }
}
```

**Time Complexity:**
- `add()`: O(1)
- `getFirstUnique()`: O(n) worst case (if many repeated chars at front)
  - But **amortized O(1)**: Each character removed at most once

**Space Complexity:** O(n) where n = total characters seen

---

## 🎯 Solution 3: Doubly Linked List + HashMap (Most Explicit)

For interviews where you want to show full control:

```java
class FirstUniqueCharStreamDLL {
    
    // Node for doubly linked list
    private static class Node {
        char ch;
        Node prev, next;
        Node(char ch) {
            this.ch = ch;
        }
    }
    
    // Frequency map: character → count
    private Map<Character, Integer> freqMap;
    
    // Position map: character → node in DLL
    private Map<Character, Node> posMap;
    
    // Doubly linked list for order
    private Node head, tail;
    
    public FirstUniqueCharStreamDLL() {
        freqMap = new HashMap<>();
        posMap = new HashMap<>();
        head = new Node('\0');
        tail = new Node('\0');
        head.next = tail;
        tail.prev = head;
    }
    
    // Add character to stream - O(1)
    public void add(char ch) {
        freqMap.put(ch, freqMap.getOrDefault(ch, 0) + 1);
        
        if (freqMap.get(ch) == 1) {
            // First occurrence: add to end of DLL
            Node node = new Node(ch);
            addToTail(node);
            posMap.put(ch, node);
        } else if (freqMap.get(ch) == 2) {
            // Second occurrence: remove from DLL
            Node node = posMap.get(ch);
            if (node != null) {
                removeNode(node);
                posMap.remove(ch);
            }
        }
        // If count > 2, already removed, do nothing
    }
    
    // Get first non-repeating character - O(1)
    public Character getFirstUnique() {
        if (head.next == tail) {
            return null;  // List is empty
        }
        return head.next.ch;
    }
    
    // Helper: Add node before tail
    private void addToTail(Node node) {
        node.prev = tail.prev;
        node.next = tail;
        tail.prev.next = node;
        tail.prev = node;
    }
    
    // Helper: Remove node from DLL
    private void removeNode(Node node) {
        node.prev.next = node.next;
        node.next.prev = node.prev;
    }
}
```

**Time Complexity:**
- `add()`: O(1) - All operations are O(1)
- `getFirstUnique()`: O(1) - Direct access to head

**Space Complexity:** O(n) where n = unique characters

---

## 📊 Step-by-Step Walkthrough

### Example: Stream = `a, a, b, c, b`

**Using LinkedHashSet Approach:**

| Step | Character | freqMap | uniqueChars | getFirstUnique() |
|------|-----------|---------|-------------|------------------|
| 0 | - | {} | {} | null |
| 1 | 'a' | {a:1} | {a} | 'a' |
| 2 | 'a' | {a:2} | {} | null |
| 3 | 'b' | {a:2, b:1} | {b} | 'b' |
| 4 | 'c' | {a:2, b:1, c:1} | {b, c} | 'b' |
| 5 | 'b' | {a:2, b:2, c:1} | {c} | 'c' |

**Key Observations:**
- 'a' added then removed when second 'a' arrives
- 'b' added first, so it appears before 'c'
- When 'b' repeats, it's removed, leaving 'c' as first unique

---

## 📊 Test Cases

### Test Case 1: Basic Stream
```java
FirstUniqueCharStream stream = new FirstUniqueCharStream();
stream.add('a');
System.out.println(stream.getFirstUnique());  // 'a'

stream.add('a');
System.out.println(stream.getFirstUnique());  // null

stream.add('b');
System.out.println(stream.getFirstUnique());  // 'b'

stream.add('c');
System.out.println(stream.getFirstUnique());  // 'b'

stream.add('b');
System.out.println(stream.getFirstUnique());  // 'c'
```

### Test Case 2: All Unique
```java
FirstUniqueCharStream stream = new FirstUniqueCharStream();
stream.add('a');
stream.add('b');
stream.add('c');
System.out.println(stream.getFirstUnique());  // 'a'
```

### Test Case 3: All Repeating
```java
FirstUniqueCharStream stream = new FirstUniqueCharStream();
stream.add('a');
stream.add('a');
stream.add('b');
stream.add('b');
System.out.println(stream.getFirstUnique());  // null
```

### Test Case 4: Unique After Many Repeats
```java
FirstUniqueCharStream stream = new FirstUniqueCharStream();
stream.add('a');
stream.add('a');
stream.add('b');
stream.add('b');
stream.add('c');
System.out.println(stream.getFirstUnique());  // 'c'
```

### Test Case 5: Alternating Pattern
```java
FirstUniqueCharStream stream = new FirstUniqueCharStream();
stream.add('a');
stream.add('b');
stream.add('a');
stream.add('c');
stream.add('b');
System.out.println(stream.getFirstUnique());  // 'c'
```

---

## Interview Q&A

### Q1: "Why LinkedHashSet instead of regular HashSet?"

**Answer:**
```
HashSet:
- Stores elements in random order (based on hash)
- Can't determine which unique character came first
- Example: {b, c, a} → which is first? Unknown!

LinkedHashSet:
- Maintains insertion order (internally uses doubly linked list)
- First element added is always at the "beginning"
- Example: {b, c, a} → 'b' was added first
- iterator().next() returns first inserted element

TreeSet (NOT suitable):
- Maintains sorted order (alphabetical)
- Example: {c, a, b} → returns 'a' (alphabetically first)
- But we need insertion order, not sorted order!

Example demonstrating the difference:
Stream: b, c, a
- LinkedHashSet: {b, c, a} → first = 'b' ✓
- HashSet: {a, b, c} (random) → first = unknown ✗
- TreeSet: {a, b, c} (sorted) → first = 'a' ✗ (wrong! 'b' came first)
```

### Q2: "Compare LinkedHashSet vs Queue approach. Which is better?"

**Answer:**
```
LinkedHashSet Approach:
Pros:
- O(1) getFirstUnique() - always
- Clean code, easy to understand
- Automatic ordering

Cons:
- Can't see intermediate states easily
- Less explicit about "stream" concept

Queue Approach:
Pros:
- More intuitive for "stream" problems
- Amortized O(1) despite worst-case O(n)
- Shows streaming nature explicitly

Cons:
- getFirstUnique() seemingly O(n)
- Need to explain amortized complexity

Performance Comparison:
For stream: a,a,b,c,b,d,e,f,...

LinkedHashSet:
- add('a'): O(1)
- add('a'): O(1) remove from set
- Every operation: O(1)

Queue:
- add('a'): O(1)
- add('a'): O(1)
- getFirstUnique after 'b': O(2) to remove 'a','a'
- But total removals ≤ total additions → amortized O(1)

Recommendation: Use LinkedHashSet for cleaner code in interviews.
```

### Q3: "What if we need to return top K unique characters, not just first?"

**Answer:**
```java
public List<Character> getFirstKUnique(int k) {
    List<Character> result = new ArrayList<>();
    Iterator<Character> it = uniqueChars.iterator();
    
    int count = 0;
    while (it.hasNext() && count < k) {
        result.add(it.next());
        count++;
    }
    
    return result;
}

// Time Complexity: O(k)
// LinkedHashSet maintains order, so first k iterations give first k unique

Example:
Stream: a, b, c, d, e (all unique)
- getFirstKUnique(3) → ['a', 'b', 'c']
```

### Q4: "How would you handle deletion of old characters (sliding window)?"

**Answer:**
```java
class FirstUniqueCharStreamWithExpiry {
    
    private Map<Character, Integer> freqMap;
    private Queue<Character> orderQueue;  // All characters with timestamps
    private Queue<Long> timestampQueue;   // Corresponding timestamps
    private long currentTime;
    private long windowSize;  // E.g., keep only last 10 characters
    
    public FirstUniqueCharStreamWithExpiry(long windowSize) {
        freqMap = new HashMap<>();
        orderQueue = new LinkedList<>();
        timestampQueue = new LinkedList<>();
        currentTime = 0;
        this.windowSize = windowSize;
    }
    
    public void add(char ch) {
        currentTime++;
        
        // Remove expired characters
        while (!timestampQueue.isEmpty() && 
               currentTime - timestampQueue.peek() >= windowSize) {
            char expired = orderQueue.poll();
            timestampQueue.poll();
            
            int freq = freqMap.get(expired);
            if (freq == 1) {
                freqMap.remove(expired);
            } else {
                freqMap.put(expired, freq - 1);
            }
        }
        
        // Add new character
        freqMap.put(ch, freqMap.getOrDefault(ch, 0) + 1);
        orderQueue.offer(ch);
        timestampQueue.offer(currentTime);
    }
    
    public Character getFirstUnique() {
        for (char ch : orderQueue) {
            if (freqMap.get(ch) == 1) {
                return ch;
            }
        }
        return null;
    }
}

// Use case: Real-time log analysis with time-based windows
```

### Q5: "What's the space complexity in worst case?"

**Answer:**
```
Worst Case: All characters are unique

Example: Stream of 1000 unique characters
- freqMap: 1000 entries → O(1000)
- uniqueChars (LinkedHashSet): 1000 entries → O(1000)
- Total: O(2000) = O(n)

Best Case: All characters repeat

Example: aaaa... (1000 times)
- freqMap: {a: 1000} → O(1)
- uniqueChars: {} (empty after first repeat) → O(0)
- Total: O(1)

Average Case: Mix of unique and repeating
- If k unique characters out of n total: O(k)
- In practice: k << n, so much less than O(n)

Memory optimization:
If we know the character set is limited (e.g., lowercase English letters):
- Use int[26] instead of HashMap → O(1) space
- Still need LinkedHashSet for order → O(26) = O(1)
```

---

## Common Mistakes

### ❌ Mistake 1: Using HashMap Without Order Tracking
```java
// WRONG - Can't find "first" unique
Map<Character, Integer> freqMap = new HashMap<>();

public void add(char ch) {
    freqMap.put(ch, freqMap.getOrDefault(ch, 0) + 1);
}

public Character getFirstUnique() {
    for (Map.Entry<Character, Integer> entry : freqMap.entrySet()) {
        if (entry.getValue() == 1) {
            return entry.getKey();  // Random order!
        }
    }
    return null;
}

// HashMap doesn't maintain insertion order!
// Stream: b, c, a → might return 'a' instead of 'b'
```

### ❌ Mistake 2: Not Removing From UniqueChars on Second Occurrence
```java
// WRONG - Doesn't remove repeated characters
public void add(char ch) {
    freqMap.put(ch, freqMap.getOrDefault(ch, 0) + 1);
    
    if (freqMap.get(ch) == 1) {
        uniqueChars.add(ch);
    }
    // Missing: remove from uniqueChars if count > 1!
}

// Stream: a, a → uniqueChars = {a} (wrong! 'a' is repeated)
// Should be: uniqueChars = {}
```

### ❌ Mistake 3: O(n) getFirstUnique Without Lazy Deletion
```java
// INEFFICIENT - Scans entire queue every time
public Character getFirstUnique() {
    for (char ch : queue) {
        if (freqMap.get(ch) == 1) {
            return ch;
        }
    }
    return null;
}

// If queue has 1M characters but only last one is unique, scans all!
// Better: Remove repeated characters from front lazily
while (!queue.isEmpty() && freqMap.get(queue.peek()) > 1) {
    queue.poll();
}
return queue.isEmpty() ? null : queue.peek();
```

### ❌ Mistake 4: Thread Safety Issues
```java
// WRONG - Not thread-safe for concurrent streams
// Multiple threads calling add() simultaneously can corrupt state

// CORRECT - Use synchronization if needed
public synchronized void add(char ch) {
    // ... existing code
}

public synchronized Character getFirstUnique() {
    // ... existing code
}

// Or use ConcurrentHashMap + careful synchronization
```

---

## Complete Working Code

```java
import java.util.*;

// Solution 1: LinkedHashSet (Recommended)
class FirstUniqueCharStream {
    
    private Map<Character, Integer> freqMap;
    private LinkedHashSet<Character> uniqueChars;
    
    public FirstUniqueCharStream() {
        freqMap = new HashMap<>();
        uniqueChars = new LinkedHashSet<>();
    }
    
    public void add(char ch) {
        freqMap.put(ch, freqMap.getOrDefault(ch, 0) + 1);
        
        if (freqMap.get(ch) == 1) {
            uniqueChars.add(ch);
        } else {
            uniqueChars.remove(ch);
        }
    }
    
    public Character getFirstUnique() {
        if (uniqueChars.isEmpty()) {
            return null;
        }
        return uniqueChars.iterator().next();
    }
}

// Solution 2: Queue (Alternative)
class FirstUniqueCharStreamQueue {
    
    private Map<Character, Integer> freqMap;
    private Queue<Character> queue;
    
    public FirstUniqueCharStreamQueue() {
        freqMap = new HashMap<>();
        queue = new LinkedList<>();
    }
    
    public void add(char ch) {
        freqMap.put(ch, freqMap.getOrDefault(ch, 0) + 1);
        queue.offer(ch);
    }
    
    public Character getFirstUnique() {
        while (!queue.isEmpty() && freqMap.get(queue.peek()) > 1) {
            queue.poll();
        }
        return queue.isEmpty() ? null : queue.peek();
    }
}

// Test
public class Main {
    public static void main(String[] args) {
        FirstUniqueCharStream stream = new FirstUniqueCharStream();
        
        stream.add('a');
        System.out.println(stream.getFirstUnique());  // 'a'
        
        stream.add('a');
        System.out.println(stream.getFirstUnique());  // null
        
        stream.add('b');
        System.out.println(stream.getFirstUnique());  // 'b'
        
        stream.add('c');
        System.out.println(stream.getFirstUnique());  // 'b'
        
        stream.add('b');
        System.out.println(stream.getFirstUnique());  // 'c'
    }
}
```

---

## Key Takeaways

| Concept | Why Important | Interview Score |
|---------|---------------|-----------------|
| Streaming data handling | Real-time systems | ⭐⭐⭐⭐⭐ |
| LinkedHashSet for order | Data structure choice | ⭐⭐⭐⭐⭐ |
| Amortized complexity analysis | Understanding performance | ⭐⭐⭐⭐ |
| Lazy deletion pattern | Optimization technique | ⭐⭐⭐⭐ |
| Multiple solution approaches | Problem-solving flexibility | ⭐⭐⭐⭐ |

---

**Priority:** 🔥 MUST KNOW (Tests streaming algorithms, common in system design)

**Related Problems:**
- First Unique Character in a String (static version)
- Design a Data Structure with First Unique Number
- LRU Cache (similar data structure pattern)

---

**Last Updated:** March 1, 2026
