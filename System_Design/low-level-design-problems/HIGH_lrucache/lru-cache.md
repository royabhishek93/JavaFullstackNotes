# Designing a LRU Cache

## Requirements
1. The LRU cache should support the following operations:
- put(key, value): Insert a key-value pair into the cache. If the cache is at capacity, remove the least recently used item before inserting the new item.
- get(key): Get the value associated with the given key. If the key exists in the cache, move it to the front of the cache (most recently used) and return its value. If the key does not exist, return -1.
2. The cache should have a fixed capacity, specified during initialization.
3. The cache should be thread-safe, allowing concurrent access from multiple threads.
4. The cache should be efficient in terms of time complexity for both put and get operations, ideally O(1).

## UML Class Diagram

![](diagrams/lrucache-class-diagram.png)

## Implementations
#### [Java Implementation](lrucache/) 

## Classes, Interfaces and Enumerations
1. The **Node** class represents a node in the doubly linked list, containing the key, value, and references to the previous and next nodes.
2. The **LRUCache** class implements the LRU cache functionality using a combination of a hash map (cache) and a doubly linked list (head and tail).
3. The get method retrieves the value associated with a given key. If the key exists in the cache, it is moved to the head of the linked list (most recently used) and its value is returned. If the key does not exist, null is returned.
4. The put method inserts a key-value pair into the cache. If the key already exists, its value is updated, and the node is moved to the head of the linked list. If the key does not exist and the cache is at capacity, the least recently used item (at the tail of the linked list) is removed, and the new item is inserted at the head.
5. The addToHead, removeNode, moveToHead, and removeTail methods are helper methods to manipulate the doubly linked list.
6. The synchronized keyword is used on the get and put methods to ensure thread safety, allowing concurrent access from multiple threads.
7. The **LRUCacheDemo** class demonstrates the usage of the LRU cache by creating an instance of LRUCache with a capacity of 3, performing various put and get operations, and printing the results.
---

## Interview Discussion Points

### Common Interview Questions

1. **Why use a doubly linked list instead of a singly linked list?**
   - Need to remove nodes from middle in O(1)
   - With single link, removal is O(n) (need to find previous node)
   - Double link allows direct access to previous and next nodes

2. **Why HashMap + LinkedList? Why not just LinkedHashMap?**
   - **LinkedHashMap**: Java provides this, which internally uses HashMap + doubly linked list
   - **Custom implementation**: Shows understanding of data structures
   - Interview often wants you to implement from scratch
   - Custom allows more control (e.g., custom eviction policies)

3. **How would you make this thread-safe?**
   ```java
   // Option 1: Synchronized methods
   public synchronized V get(K key) { ... }
   
   // Option 2: ReentrantReadWriteLock
   private final ReadWriteLock lock = new ReentrantReadWriteLock();
   
   // Option 3: ConcurrentHashMap + custom synchronization
   ```

4. **How would you implement LFU (Least Frequently Used) instead?**
   - Add frequency counter to each node
   - Use HashMap<Frequency, DoublyLinkedList> for each frequency bucket
   - Track min frequency for O(1) eviction

5. **How would you add TTL (Time To Live) to cache entries?**
   ```java
   class Node {
       K key;
       V value;
       long expiryTime;
       Node prev, next;
   }
   // Background thread to clean expired entries
   // Or lazy cleanup on get()
   ```

### Implementation Comparison

| Approach | Time (Get) | Time (Put) | Space | Notes |
|----------|-----------|-----------|-------|-------|
| **HashMap + DoublyLinkedList** | O(1) | O(1) | O(n) | Best, used in production |
| **Array + Linear Search** | O(n) | O(n) | O(n) | Too slow |
| **TreeMap (ordered)** | O(log n) | O(log n) | O(n) | Slower than needed |
| **LinkedHashMap (Java)** | O(1) | O(1) | O(n) | Built-in, interview may not allow |

### Design Trade-offs

| Decision | Why Chosen | Trade-off |
|----------|------------|-----------|
| **Fixed capacity** | Prevents unbounded memory growth | Can't grow dynamically with load |
| **Doubly linked list** | O(1) insert/delete at any position | Extra memory for two pointers |
| **HashMap for lookups** | O(1) key lookup | Extra memory, no ordering |
| **Synchronized methods** | Thread safety | Performance overhead |

### Complexity Analysis

| Operation | Time Complexity | Explanation |
|-----------|----------------|-------------|
| **get(key)** | O(1) | HashMap lookup + move to front |
| **put(key, value)** | O(1) | HashMap insert + add to front + evict if needed |
| **evict()** | O(1) | Remove from tail of linked list |
| **Space** | O(capacity) | HashMap + LinkedList nodes |

### Visual Example

```
Initial: capacity = 3
Put(1, A): [1:A]
Put(2, B): [2:B] <-> [1:A]
Put(3, C): [3:C] <-> [2:B] <-> [1:A]
Get(1):    [1:A] <-> [3:C] <-> [2:B]  // 1 moved to front
Put(4, D): [4:D] <-> [1:A] <-> [3:C]  // 2 evicted (LRU)
```

### Real-World Use Cases

1. **Browser Cache**: Store web pages, images
2. **Database Query Cache**: Cache frequent query results
3. **CDN**: Cache static assets closer to users
4. **CPU Cache**: L1, L2, L3 caches (hardware level)
5. **Redis**: Distributed in-memory cache with LRU eviction

### Follow-up Features
- **Cache Statistics**: Hit rate, miss rate, eviction count
- **Adaptive Size**: Adjust capacity based on available memory
- **Tiered Eviction**: Combine LRU + LFU + TTL
- **Distributed Cache**: Partition across multiple nodes (consistent hashing)
- **Monitoring & Alerts**: Alert when hit rate drops below threshold
