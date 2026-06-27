# LC 146: LRU Cache

**Link**: [leetcode.com/problems/lru-cache](https://leetcode.com/problems/lru-cache/)

## Problem
Design a data structure that follows the constraints of a Least Recently Used (LRU) cache.

## Optimized Approach: HashMap + Doubly Linked List

```java
class LRUCache {
    private class Node {
        int key, value;
        Node prev, next;
        Node(int key, int value) {
            this.key = key;
            this.value = value;
        }
    }

    private final int capacity;
    private final Map<Integer, Node> map;
    private final Node head; // dummy head (most recent after head)
    private final Node tail; // dummy tail (least recent before tail)

    public LRUCache(int capacity) {
        this.capacity = capacity;
        this.map = new HashMap<>();
        this.head = new Node(0, 0);
        this.tail = new Node(0, 0);
        head.next = tail;
        tail.prev = head;
    }

    public int get(int key) {
        Node node = map.get(key);
        if (node == null) return -1;
        moveToFront(node);
        return node.value;
    }

    public void put(int key, int value) {
        if (map.containsKey(key)) {
            Node node = map.get(key);
            node.value = value;
            moveToFront(node);
            return;
        }

        Node node = new Node(key, value);
        map.put(key, node);
        addFirst(node);

        if (map.size() > capacity) {
            Node lru = removeLast();
            map.remove(lru.key);
        }
    }

    private void moveToFront(Node node) {
        remove(node);
        addFirst(node);
    }

    private void addFirst(Node node) {
        node.next = head.next;
        node.prev = head;
        head.next.prev = node;
        head.next = node;
    }

    private void remove(Node node) {
        node.prev.next = node.next;
        node.next.prev = node.prev;
    }

    private Node removeLast() {
        Node node = tail.prev;
        remove(node);
        return node;
    }
}
```

**Time Complexity**: O(1) for `get` and `put`  
**Space Complexity**: O(capacity)

## Key Insights
- HashMap provides O(1) node lookup
- Doubly linked list maintains usage order
- Move accessed/updated node to front (MRU)
- Evict from back (LRU)

## Tips and Tricks
- Clarify the required operations and their target time complexities first.
- Choose data structures by operation cost, not by familiarity.
- For mutable design problems, test repeated updates and edge-case sequences.

## Related Problems
- LC 460 LFU Cache
