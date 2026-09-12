# LRU Cache - Complete Interview Conversational Script

**Interview Duration: 45 minutes | Difficulty: Medium | Must-Know: ⭐⭐⭐**

---

## TABLE OF CONTENTS

1. Requirements Clarification (3 min)
2. High-Level Approach & Data Structures (5 min)
3. Class Design (5 min)
4. Core Implementation (20 min)
5. Walkthrough with Examples (5 min)
6. Advanced Features (5 min)
7. Follow-up Q&A (2 min)

---

## PHASE 1: REQUIREMENTS CLARIFICATION (3 minutes)

**Interviewer:** "Design an LRU Cache."

**You:** "Great! Let me make sure I understand the requirements correctly. An LRU Cache is a Least Recently Used cache - when it's full and we need to add a new item, we remove the item that was accessed least recently. Is that right?"

**Interviewer:** "Yes, exactly."

**You:** "Perfect. Let me clarify both functional and non-functional requirements."

### Functional Requirements

**You:** "For functional requirements, the cache should support:"
- "A fixed capacity that's set at initialization"
- "`get(key)` operation - retrieve value for a key, return null if not found"
- "`put(key, value)` operation - insert or update a key-value pair"
- "When cache is full and we put a new key, evict the least recently used item"
- "Both get and put should update the 'recently used' status"

**You:** "Quick question - should we support null keys or null values?"

**Interviewer:** "No null keys. Null values are acceptable."

**You:** "Got it. What about the time complexity expectations?"

**Interviewer:** "Both get and put should be O(1) - constant time."

**You:** "Perfect. That's the key constraint. For non-functional requirements, I'm thinking:"
- "Thread-safe operations for concurrent access"
- "Memory efficient - don't store more than capacity items"
- "Handle edge cases like capacity = 1, duplicate keys, negative capacity"

**Interviewer:** "Yes, thread safety is important. Show me your design."

**You:** "Excellent. Let me explain my approach."

---

## PHASE 2: HIGH-LEVEL APPROACH (5 minutes)

**You:** "To achieve O(1) for both get and put with LRU eviction, I need to solve two problems: fast lookup and fast reordering. Let me explain my data structure choice."

**You speaking:**

**💡 MUST DRAW ON BOARD:**

```
LRU CACHE - THE CORE INSIGHT

Problem 1: Fast Lookup (O(1))
──────────────────────────────────────────
Need to find if key exists → HashMap

Problem 2: Fast Reordering (O(1))
──────────────────────────────────────────
Need to:
  - Move accessed item to "most recent" position
  - Remove least recent item
→ Doubly Linked List

Solution: Combine Both!
──────────────────────────────────────────
HashMap<K, Node<K,V>>  +  Doubly Linked List
    ↓                            ↓
  O(1) lookup              O(1) add/remove
```

**You:** "Why doubly linked list and not array? Because array operations like insert/remove are O(n) due to shifting. With a doubly linked list, if I have a pointer to a node, I can remove it in O(1) by just updating pointers."

**You:** "Let me draw the complete structure:"

**💡 MUST DRAW THIS DIAGRAM:**

```
LRU CACHE STRUCTURE

┌────────────────────────────────────────────────────────┐
│              DOUBLY LINKED LIST                        │
│                                                         │
│  DUMMY HEAD                               DUMMY TAIL   │
│      ↓                                         ↓        │
│    ┌───┐   ┌───────┐   ┌───────┐   ┌───────┐ ┌───┐   │
│    │   │←─→│  MRU  │←─→│       │←─→│  LRU  │←→│   │   │
│    │ H │   │ k1:v1 │   │ k2:v2 │   │ k3:v3 │  │ T │   │
│    └───┘   └───────┘   └───────┘   └───────┘ └───┘   │
│              ↑                          ↑               │
│         Most Recently Used      Least Recently Used    │
└────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────┐
│                     HASHMAP                             │
│                                                         │
│  Key  →  Node Reference                                │
│  ──────────────────────────                            │
│  k1   →  Node(k1,v1) ────────┐                        │
│  k2   →  Node(k2,v2) ─────────┼────┐                  │
│  k3   →  Node(k3,v3) ─────────┼────┼────┐             │
│                               ↓    ↓    ↓             │
│                     [Points to nodes in list]          │
└────────────────────────────────────────────────────────┘

Why Dummy Nodes?
────────────────────────────────────────────────────────
✓ Simplifies boundary conditions (no null checks)
✓ Head.next = first real node
✓ Tail.prev = last real node
✓ Empty list: head.next = tail, tail.prev = head
```

**You:** "The dummy head and tail nodes are crucial - they eliminate all the edge case null pointer checks. When the list is empty, head points to tail and vice versa. When we add the first item, it goes between head and tail."

**You:** "Now let me explain the operations:"

**You speaking:**

```
OPERATION FLOWS

get(key):
─────────────────────────────────────────────
1. Look up in HashMap → O(1)
2. If found:
   - Remove node from current position → O(1)
   - Add node right after head (MRU position) → O(1)
   - Return value
3. If not found:
   - Return null
Total: O(1)


put(key, value):
─────────────────────────────────────────────
1. Look up in HashMap → O(1)
2. If key exists:
   - Update node value
   - Move to head (MRU) → O(1)
3. If key doesn't exist:
   - Create new node
   - Add to head → O(1)
   - Add to HashMap → O(1)
   - If size > capacity:
     * Remove node before tail (LRU) → O(1)
     * Remove from HashMap → O(1)
Total: O(1)
```

**You:** "Notice that every operation is O(1) because we're just updating pointers and using HashMap operations."

**Interviewer:** "Good. Show me the actual code structure."

---

## PHASE 3: CLASS DESIGN (5 minutes)

**You:** "Let me design the classes. I'll use generics so it works with any key-value types."

**You speaking:**

**💡 CLASS STRUCTURE TO WRITE:**

```
CLASS DESIGN

┌─────────────────────────────────────────────┐
│         Node<K, V>                          │
├─────────────────────────────────────────────┤
│  Fields:                                    │
│    - K key                                  │
│    - V value                                │
│    - Node<K,V> prev                         │
│    - Node<K,V> next                         │
│                                             │
│  Purpose:                                   │
│    - Holds data + doubly linked pointers    │
│    - No behavior, just data                 │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│      LRUCache<K, V>                         │
├─────────────────────────────────────────────┤
│  Fields:                                    │
│    - int capacity                           │
│    - Map<K, Node<K,V>> cache                │
│    - Node<K,V> head  (dummy)                │
│    - Node<K,V> tail  (dummy)                │
│                                             │
│  Public Methods:                            │
│    + V get(K key)                           │
│    + void put(K key, V value)               │
│    + int size()                             │
│    + void clear()                           │
│                                             │
│  Private Helpers:                           │
│    - void moveToHead(Node node)             │
│    - void removeNode(Node node)             │
│    - void addToHead(Node node)              │
│    - Node removeTail()                      │
└─────────────────────────────────────────────┘
```

**You:** "The design is clean - Node is just a data holder, LRUCache manages all the logic. The private helper methods handle the low-level linked list operations, while the public methods implement the cache interface."

---

## PHASE 4: CORE IMPLEMENTATION (20 minutes)

**You:** "Now let me implement the complete solution. I'll start with the Node class, then build the LRUCache."

### Step 1: Node Class

**You:** "First, the simple Node class. This is just a container for data and pointers."

**You speaking:**

**💡 WRITE THIS CODE:**

```java
public class Node<K, V> {
    K key;        // Need key to remove from HashMap during eviction
    V value;
    Node<K, V> prev;
    Node<K, V> next;

    public Node(K key, V value) {
        this.key = key;
        this.value = value;
    }
}
```

**You:** "Notice I'm storing the key in the node as well. This is important - when we evict the tail node, we need to know its key to remove it from the HashMap."

### Step 2: LRUCache Constructor

**You:** "Now the LRUCache constructor. This sets up the initial state."

**You speaking:**

**💡 CRITICAL INITIALIZATION:**

```java
import java.util.HashMap;
import java.util.Map;

public class LRUCache<K, V> {
    private final int capacity;
    private final Map<K, Node<K, V>> cache;
    private final Node<K, V> head;  // Dummy head
    private final Node<K, V> tail;  // Dummy tail

    public LRUCache(int capacity) {
        // Validate capacity
        if (capacity <= 0) {
            throw new IllegalArgumentException(
                "Capacity must be positive"
            );
        }
        
        this.capacity = capacity;
        this.cache = new HashMap<>();
        
        // Create dummy nodes
        this.head = new Node<>(null, null);
        this.tail = new Node<>(null, null);
        
        // Link them: head ←→ tail
        head.next = tail;
        tail.prev = head;
    }
```

**You:** "The dummy nodes start out pointing to each other. This means the list is empty but we never have to deal with null pointers. Every operation just manipulates these links."

### Step 3: Get Operation

**You:** "Now the get operation. This is where we update the recently-used status."

**You speaking:**

**💡 MUST WRITE - GET METHOD:**

```java
/**
 * Get value for key
 * - If exists: move to head (most recent) and return
 * - If not: return null
 * Time: O(1)
 */
public synchronized V get(K key) {
    Node<K, V> node = cache.get(key);  // HashMap lookup: O(1)
    
    if (node == null) {
        return null;  // Key not found
    }
    
    // Key found - mark as recently used by moving to head
    moveToHead(node);  // O(1) operation
    return node.value;
}
```

**You:** "The synchronized keyword makes this thread-safe. Multiple threads can call get() simultaneously, and the first one locks the method. HashMap lookup is O(1), moving to head is O(1), so total is O(1)."

### Step 4: Put Operation

**You:** "The put operation is more complex - it handles both updates and insertions, plus eviction."

**You speaking:**

**💡 MUST WRITE - PUT METHOD:**

```java
/**
 * Put key-value pair
 * - If key exists: update value, move to head
 * - If new key: create node, add to head
 * - If full: evict LRU (tail) first
 * Time: O(1)
 */
public synchronized void put(K key, V value) {
    Node<K, V> node = cache.get(key);
    
    if (node != null) {
        // Case 1: Key exists - update and move to head
        node.value = value;
        moveToHead(node);
    } else {
        // Case 2: New key - create new node
        Node<K, V> newNode = new Node<>(key, value);
        
        // Add to HashMap
        cache.put(key, newNode);
        
        // Add to head of list (most recent)
        addToHead(newNode);
        
        // Check if we exceeded capacity
        if (cache.size() > capacity) {
            // Evict least recently used (tail)
            Node<K, V> lruNode = removeTail();
            cache.remove(lruNode.key);  // Remove from HashMap too!
        }
    }
}
```

**You:** "Notice the eviction happens AFTER we add the new node. So for a moment, we have capacity + 1 items, then we evict. This is fine because we immediately clean up."

**You:** "Also critical - when we evict, we must remove from BOTH the list AND the HashMap. If we forget the HashMap removal, we have a memory leak."

### Step 5: Private Helper Methods

**You:** "Now the helper methods that do the actual linked list manipulation. These are the building blocks."

**You speaking:**

**💡 IMPORTANT HELPERS:**

```java
/**
 * Move existing node to head (most recent position)
 */
private void moveToHead(Node<K, V> node) {
    removeNode(node);  // Remove from current position
    addToHead(node);   // Add to head
}

/**
 * Remove node from its current position in the list
 * Updates prev and next pointers of neighbors
 */
private void removeNode(Node<K, V> node) {
    node.prev.next = node.next;  // Bypass node
    node.next.prev = node.prev;
}

/**
 * Add node right after head (most recently used position)
 * Four pointer updates:
 *   head ←→ newNode ←→ oldFirst
 */
private void addToHead(Node<K, V> node) {
    node.next = head.next;      // newNode → oldFirst
    node.prev = head;           // newNode ← head
    head.next.prev = node;      // oldFirst ← newNode
    head.next = node;           // head → newNode
}

/**
 * Remove and return node before tail (LRU node)
 */
private Node<K, V> removeTail() {
    Node<K, V> lruNode = tail.prev;  // Get LRU node
    removeNode(lruNode);             // Remove it
    return lruNode;                  // Return for HashMap cleanup
}
```

**You:** "The addToHead method has four pointer updates - this looks complex but it's systematic. Let me explain:"

**You speaking while drawing:**

```
Adding to Head (4 pointer updates)

Before:
  head ←→ oldFirst ←→ ... ←→ tail

After adding newNode:
  head ←→ newNode ←→ oldFirst ←→ ... ←→ tail

Updates:
1. node.next = head.next      (newNode → oldFirst)
2. node.prev = head           (newNode ← head)
3. head.next.prev = node      (oldFirst ← newNode)
4. head.next = node           (head → newNode)

Order matters! Update node's pointers first, then update neighbors.
```

**You:** "If you do these in the wrong order, you can lose references and corrupt the list."

### Step 6: Utility Methods

**You:** "Let me add some utility methods for completeness."

**You speaking:**

```java
/**
 * Get current size of cache
 */
public int size() {
    return cache.size();
}

/**
 * Check if cache is empty
 */
public boolean isEmpty() {
    return cache.isEmpty();
}

/**
 * Clear all entries
 */
public synchronized void clear() {
    cache.clear();
    head.next = tail;  // Reset list to empty state
    tail.prev = head;
}

/**
 * Display cache for debugging (MRU → LRU order)
 */
public void display() {
    System.out.println("\n=== LRU Cache ===");
    System.out.println("Capacity: " + capacity);
    System.out.println("Size: " + cache.size());
    System.out.print("Order (MRU → LRU): ");
    
    Node<K, V> current = head.next;
    while (current != tail) {
        System.out.print("[" + current.key + ":" + 
                        current.value + "] ");
        current = current.next;
    }
    System.out.println("\n==================\n");
}
```

**Interviewer:** "Good implementation. Walk me through a concrete example."

---

## PHASE 5: STEP-BY-STEP WALKTHROUGH (5 minutes)

**You:** "Let me trace through an example with capacity = 3. I'll show you the state after each operation."

**You speaking:**

**💡 DRAW THIS WALKTHROUGH:**

```
EXAMPLE: LRUCache<Integer, String> capacity = 3

Initial State:
──────────────────────────────────────────────
HashMap: {}
List:    head ←→ tail


Operation 1: put(1, "Apple")
──────────────────────────────────────────────
HashMap: {1 → Node(1,"Apple")}
List:    head ←→ [1:Apple] ←→ tail
                  ↑ MRU & LRU


Operation 2: put(2, "Banana")
──────────────────────────────────────────────
HashMap: {1 → Node(1,"Apple"), 2 → Node(2,"Banana")}
List:    head ←→ [2:Banana] ←→ [1:Apple] ←→ tail
                  ↑ MRU                ↑ LRU


Operation 3: put(3, "Cherry")
──────────────────────────────────────────────
HashMap: {1→..., 2→..., 3→Node(3,"Cherry")}
List:    head ←→ [3:Cherry] ←→ [2:Banana] ←→ [1:Apple] ←→ tail
                  ↑ MRU                              ↑ LRU
Cache is now FULL (3/3)


Operation 4: get(1) - Access existing key
──────────────────────────────────────────────
1. Look up in HashMap → found Node(1,"Apple")
2. Remove [1:Apple] from current position (tail.prev)
3. Add [1:Apple] right after head

HashMap: {1→..., 2→..., 3→...}
List:    head ←→ [1:Apple] ←→ [3:Cherry] ←→ [2:Banana] ←→ tail
                  ↑ MRU (moved!)                    ↑ LRU
Return: "Apple"


Operation 5: put(4, "Date") - Cache full, must evict!
──────────────────────────────────────────────
1. Key 4 not in cache
2. Create Node(4,"Date")
3. Add to head
4. Size = 4 > capacity = 3
5. Evict LRU: removeTail() → [2:Banana]
6. Remove key 2 from HashMap

HashMap: {1→..., 3→..., 4→Node(4,"Date")}
List:    head ←→ [4:Date] ←→ [1:Apple] ←→ [3:Cherry] ←→ tail
                  ↑ MRU                            ↑ LRU
Evicted: [2:Banana]


Operation 6: get(2) - Try to get evicted key
──────────────────────────────────────────────
Look up in HashMap → not found
Return: null


Operation 7: put(1, "Avocado") - Update existing
──────────────────────────────────────────────
1. Key 1 exists in cache
2. Update value: "Apple" → "Avocado"
3. Move to head

HashMap: {1→Node(1,"Avocado"), 3→..., 4→...}
List:    head ←→ [1:Avocado] ←→ [4:Date] ←→ [3:Cherry] ←→ tail
                  ↑ MRU (moved!)                     ↑ LRU
```

**You:** "See how every get or put makes the item most recently used by moving it to the head. The tail always points to the item that was accessed longest ago."

---

## PHASE 6: THREAD SAFETY & EDGE CASES (3 minutes)

**You:** "Let me discuss thread safety and edge cases."

**You speaking:**

### Thread Safety

**You:** "I've used `synchronized` on get and put methods, which is simple but has limitations."

**💡 THREAD SAFETY OPTIONS:**

```java
// Option 1: Method-level synchronization (current approach)
public synchronized V get(K key) { ... }
public synchronized void put(K key, V value) { ... }

Pros: Simple, correct
Cons: Coarse-grained locking, blocks all operations


// Option 2: ReentrantReadWriteLock (better performance)
private final ReadWriteLock lock = new ReentrantReadWriteLock();

public V get(K key) {
    lock.readLock().lock();  // Multiple readers allowed
    try {
        Node<K, V> node = cache.get(key);
        if (node == null) return null;
        
        // Problem: moveToHead() is a write operation!
        // Need to upgrade to write lock
        lock.readLock().unlock();
        lock.writeLock().lock();
        try {
            moveToHead(node);
            return node.value;
        } finally {
            lock.writeLock().unlock();
        }
    } finally {
        if (lock.readLock().tryLock()) {
            lock.readLock().unlock();
        }
    }
}

Pros: Better read concurrency
Cons: More complex, lock upgrade tricky


// Option 3: ConcurrentHashMap + fine-grained locking
private final ConcurrentHashMap<K, Node<K,V>> cache;
private final ReentrantLock listLock = new ReentrantLock();

public V get(K key) {
    Node<K, V> node = cache.get(key);  // Lock-free read
    if (node == null) return null;
    
    listLock.lock();  // Only lock for list operations
    try {
        moveToHead(node);
    } finally {
        listLock.unlock();
    }
    return node.value;
}

Pros: Best performance
Cons: Most complex
```

**You:** "For an interview, method-level synchronization is sufficient. In production, I'd use ConcurrentHashMap with fine-grained locking for the list operations."

### Edge Cases

**You:** "Let me cover the edge cases:"

```
EDGE CASES TO HANDLE

1. Capacity = 0 or negative
──────────────────────────────────────────────
✓ Throw IllegalArgumentException in constructor


2. Capacity = 1
──────────────────────────────────────────────
cache.put(1, "A");  // [1:A]
cache.put(2, "B");  // [2:B], evicts 1 immediately
cache.get(1);       // null - was evicted

Works correctly! Eviction happens on every put.


3. Null keys
──────────────────────────────────────────────
HashMap allows null keys, but cache.get(key) when 
key is null would be ambiguous with "not found".
✓ Add validation:
if (key == null) 
    throw new IllegalArgumentException("Null keys not allowed");


4. Null values
──────────────────────────────────────────────
✓ Allowed in our implementation
cache.put(1, null);  // Valid
cache.get(1);        // Returns null - but key exists!

Problem: Can't distinguish between "not found" and "value is null"
Solution: Return Optional<V> instead of V


5. Get on empty cache
──────────────────────────────────────────────
cache.get(1);  // Returns null
✓ Works correctly


6. Put same key twice
──────────────────────────────────────────────
cache.put(1, "A");
cache.put(1, "B");  // Updates value, moves to head
✓ Works correctly


7. Concurrent access
──────────────────────────────────────────────
Thread 1: cache.put(1, "A");
Thread 2: cache.get(1);  // Might see stale or new value

✓ Handled by synchronized methods
```

---

## PHASE 7: ADVANCED FEATURES (3 minutes)

**You:** "Let me show some advanced variations you might be asked about."

**Interviewer:** "How would you add TTL support?"

**You:** "TTL means time-to-live - entries expire after a certain duration. Here's how:"

**You speaking:**

```java
public class LRUCacheWithTTL<K, V> extends LRUCache<K, V> {
    private final Map<K, Long> expirationMap;
    private final long ttlMillis;

    public LRUCacheWithTTL(int capacity, long ttlMillis) {
        super(capacity);
        this.expirationMap = new ConcurrentHashMap<>();
        this.ttlMillis = ttlMillis;
    }

    @Override
    public synchronized V get(K key) {
        // Check expiration before returning
        if (isExpired(key)) {
            // Remove expired entry
            cache.remove(key);
            expirationMap.remove(key);
            return null;
        }
        return super.get(key);
    }

    @Override
    public synchronized void put(K key, V value) {
        super.put(key, value);
        // Record expiration time
        expirationMap.put(key, 
            System.currentTimeMillis() + ttlMillis);
    }

    private boolean isExpired(K key) {
        Long expiration = expirationMap.get(key);
        return expiration != null && 
               System.currentTimeMillis() > expiration;
    }
    
    // Background cleanup thread
    public void startCleanupThread() {
        ScheduledExecutorService executor = 
            Executors.newSingleThreadScheduledExecutor();
        
        executor.scheduleAtFixedRate(() -> {
            for (K key : new HashSet<>(expirationMap.keySet())) {
                if (isExpired(key)) {
                    cache.remove(key);
                    expirationMap.remove(key);
                }
            }
        }, 0, 1, TimeUnit.SECONDS);
    }
}
```

**You:** "The key is checking expiration on every get. Optionally, we can have a background thread that cleans up expired entries proactively."

**Interviewer:** "What about tracking statistics like hit rate?"

**You:** "Good question! Here's a statistics wrapper:"

```java
public class LRUCacheWithStats<K, V> extends LRUCache<K, V> {
    private final AtomicLong hitCount = new AtomicLong(0);
    private final AtomicLong missCount = new AtomicLong(0);

    public LRUCacheWithStats(int capacity) {
        super(capacity);
    }

    @Override
    public synchronized V get(K key) {
        V value = super.get(key);
        
        if (value != null) {
            hitCount.incrementAndGet();
        } else {
            missCount.incrementAndGet();
        }
        
        return value;
    }

    public double getHitRate() {
        long total = hitCount.get() + missCount.get();
        return total == 0 ? 0.0 : 
               (double) hitCount.get() / total;
    }

    public void printStats() {
        System.out.println("=== Cache Statistics ===");
        System.out.println("Hits: " + hitCount.get());
        System.out.println("Misses: " + missCount.get());
        System.out.println("Hit Rate: " + 
            String.format("%.2f%%", getHitRate() * 100));
    }
}
```

**You:** "Using AtomicLong ensures thread-safe counter updates without additional synchronization."

---

## PHASE 8: FOLLOW-UP Q&A (5 minutes)

**Interviewer:** "How would you implement LFU (Least Frequently Used) instead?"

**You:** "LFU evicts the item with the lowest access count, not the oldest access. Here's the approach:"

**You speaking:**

```
LFU CACHE APPROACH

Data Structures:
────────────────────────────────────────────
1. HashMap<K, Node<K,V>>  - key → node mapping
2. HashMap<Integer, LinkedHashSet<K>>  - frequency → keys
3. int minFrequency  - track minimum frequency

Node Structure:
────────────────────────────────────────────
class Node {
    K key;
    V value;
    int frequency;  // Access count
}

Operations:
────────────────────────────────────────────
get(key):
  1. Get node from HashMap
  2. Increment frequency
  3. Move key from old frequency set to new frequency set
  4. Update minFrequency if needed

put(key, value):
  1. If exists: update value, increment frequency
  2. If new:
     - Add with frequency = 1
     - If full: evict key from minFrequency set

Time: O(1) for both operations
```

**You:** "The tricky part is maintaining minFrequency correctly. When you increment the last key at minFrequency, you need to update minFrequency to the next level."

---

**Interviewer:** "How would you distribute this cache across multiple servers?"

**You:** "Distributed caching! Here's my approach:"

**You speaking:**

```
DISTRIBUTED LRU CACHE

Architecture:
────────────────────────────────────────────
Client → Consistent Hashing → Cache Nodes

┌─────────┐
│ Client  │
└────┬────┘
     │
     ↓
┌────────────────┐
│ ConsistentHash │  hash(key) → Node
└────────────────┘
     │
     ├──────────┬─────────┬──────────┐
     ↓          ↓         ↓          ↓
┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
│ Node 1 │ │ Node 2 │ │ Node 3 │ │ Node N │
│ LRU    │ │ LRU    │ │ LRU    │ │ LRU    │
└────────┘ └────────┘ └────────┘ └────────┘

Consistent Hashing:
────────────────────────────────────────────
- Maps keys to nodes
- When node fails, only 1/N keys remapped
- Virtual nodes for better distribution

Challenges:
────────────────────────────────────────────
1. Node failure → Data loss
   Solution: Replication (2-3 copies)

2. Hot keys → One node overloaded
   Solution: Key splitting or local cache

3. Cache invalidation
   Solution: Pub/Sub for invalidation events

4. Capacity management
   Solution: Global LRU across all nodes (complex)
```

**You:** "In practice, companies use Redis or Memcached for distributed caching. They handle all these challenges with battle-tested implementations."

---

**Interviewer:** "What about size-based eviction instead of count-based?"

**You:** "Good question! Some caches evict based on total byte size rather than item count."

**You speaking:**

```java
public class LRUCacheWithSize<K, V> {
    private final long maxSizeBytes;
    private long currentSizeBytes = 0;
    
    private static class Node<K, V> {
        K key;
        V value;
        long sizeBytes;  // Size of this entry
        Node<K, V> prev, next;
    }
    
    public synchronized void put(K key, V value) {
        long entrySize = estimateSize(key, value);
        
        // Evict until we have space
        while (currentSizeBytes + entrySize > maxSizeBytes) {
            Node<K, V> lru = removeTail();
            currentSizeBytes -= lru.sizeBytes;
            cache.remove(lru.key);
        }
        
        // Add new entry
        Node<K, V> node = new Node<>(key, value, entrySize);
        addToHead(node);
        cache.put(key, node);
        currentSizeBytes += entrySize;
    }
    
    private long estimateSize(K key, V value) {
        // Rough estimate - in production use instrumentation
        return 16 + // object overhead
               key.toString().length() * 2 +   // key size
               value.toString().length() * 2;  // value size
    }
}
```

**You:** "Size estimation is tricky in Java because object sizes vary. In production, you'd use Java instrumentation or tools like JOL (Java Object Layout) for accurate sizing."

---

## PHASE 9: COMPLEXITY ANALYSIS & KEY TAKEAWAYS

**You:** "Let me summarize the complexity and key points."

**💡 FINAL SUMMARY - REMEMBER THESE:**

```
TIME COMPLEXITY
────────────────────────────────────────────
Operation    Average    Worst Case    Explanation
─────────────────────────────────────────────────────
get(key)       O(1)        O(1)       HashMap + list ops
put(key,val)   O(1)        O(1)       HashMap + list ops
evict()        O(1)        O(1)       Remove tail node


SPACE COMPLEXITY
────────────────────────────────────────────
- O(capacity) total
- HashMap: O(capacity) 
- Doubly Linked List: O(capacity)
- No extra space beyond the stored items


WHY THIS DATA STRUCTURE?
────────────────────────────────────────────
HashMap:
  ✓ O(1) key lookup
  ✓ O(1) insertion/deletion
  ✗ Doesn't maintain order

Doubly Linked List:
  ✓ O(1) insertion/deletion with pointer
  ✓ Maintains order (MRU → LRU)
  ✗ O(n) search without HashMap

Combined = Perfect! O(1) lookup + O(1) reordering


ALTERNATIVES CONSIDERED
────────────────────────────────────────────
1. Array + HashMap
   ✗ Array shift is O(n)

2. Single LinkedList only
   ✗ Finding node is O(n)

3. TreeMap (ordered map)
   ✗ O(log n) operations

4. LinkedHashMap (Java built-in)
   ✓ Perfect! Same approach under the hood
```

**You:** "In fact, Java's LinkedHashMap has an LRU mode built-in. But implementing it from scratch shows you understand the underlying mechanics."

---

## MUST REMEMBER FOR INTERVIEW

### ✅ Key Points to Mention:

1. **"I'll use HashMap for O(1) lookup and Doubly Linked List for O(1) reordering"**
2. **"Dummy head and tail nodes simplify boundary conditions"**
3. **"Most recently used goes at head, least recently used at tail"**
4. **"Every access (get or put) moves item to head"**
5. **"When evicting, remove from BOTH list AND HashMap"**
6. **"Synchronized methods for thread safety"**

### ❌ Common Mistakes to Avoid:

- ❌ Forgetting to update HashMap when evicting from list
- ❌ Not storing key in Node (can't remove from HashMap later)
- ❌ Using singly linked list (can't remove node in O(1))
- ❌ Not handling capacity = 1 edge case
- ❌ Incorrect pointer updates in addToHead/removeNode
- ❌ Not thread-safe in concurrent environment
- ❌ Forgetting to validate capacity in constructor

---

## REAL-WORLD APPLICATIONS

**You:** "LRU caches are everywhere in production systems:"

```
WHERE LRU IS USED

1. CPU Cache (L1, L2, L3)
   - Hardware implements LRU for cache lines

2. Operating System (Page Replacement)
   - Virtual memory management
   - OS uses variant called CLOCK algorithm

3. Database Query Cache
   - MySQL, PostgreSQL cache query results
   - Evict old queries when memory is full

4. Web Browser Cache
   - Chrome, Firefox cache web pages
   - Evict least visited pages

5. CDN Edge Caching
   - CloudFlare, Akamai cache content
   - LRU ensures popular content stays cached

6. Redis Cache
   - allkeys-lru eviction policy
   - Used by millions of applications

7. HTTP Proxies
   - Nginx, Varnish cache responses
   - LRU for memory management
```

---

## TRADE-OFFS & ALTERNATIVES

**You:** "Let me explain why LRU and when other policies might be better."

**💡 CACHE EVICTION POLICIES COMPARISON:**

```
EVICTION POLICIES

LRU (Least Recently Used)
────────────────────────────────────────────
Evicts: Oldest accessed item
Pros:
  ✓ Simple to implement
  ✓ Good for temporal locality
  ✓ O(1) operations
Cons:
  ✗ Doesn't consider access frequency
  ✗ Scan-resistant is weak
Use when: Recency matters more than frequency


LFU (Least Frequently Used)
────────────────────────────────────────────
Evicts: Least accessed item
Pros:
  ✓ Better for frequency-based access
  ✓ Handles scan patterns well
Cons:
  ✗ More complex implementation
  ✗ Old items can stay forever
Use when: Frequency matters more than recency


MRU (Most Recently Used)
────────────────────────────────────────────
Evicts: Most recently accessed
Pros:
  ✓ Good for sequential scans
Cons:
  ✗ Counter-intuitive for most workloads
Use when: Scanning large datasets


FIFO (First In First Out)
────────────────────────────────────────────
Evicts: Oldest added item
Pros:
  ✓ Simplest to implement
Cons:
  ✗ Ignores access patterns completely
Use when: All items equally important


Random
────────────────────────────────────────────
Evicts: Random item
Pros:
  ✓ Very simple, very fast
  ✓ No worst-case behavior
Cons:
  ✗ No intelligence
Use when: Access patterns are truly random


ARC (Adaptive Replacement Cache)
────────────────────────────────────────────
Evicts: Adaptive between LRU and LFU
Pros:
  ✓ Best of both worlds
  ✓ Self-tuning
Cons:
  ✗ Complex implementation
  ✗ Patent concerns
Use when: Maximum hit rate needed
```

---

**END OF LRU CACHE INTERVIEW GUIDE**

**Final Advice:** This is a **fundamental data structures question** that tests:
- Data structure knowledge (HashMap + Linked List)
- Pointer manipulation skills
- Time complexity analysis  
- Thread safety understanding
- System design thinking (distributed cache)

Practice implementing this 2-3 times until you can write it fluently. Many companies (Google, Facebook, Amazon, Microsoft) ask this or variations!
