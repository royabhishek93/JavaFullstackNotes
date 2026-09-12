# LRU Cache — Cheat Sheet
> **Topic:** LRU Cache | **Level:** Reference

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 DATA STRUCTURES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  HashMap (Map)       →  O(1) key-to-node lookup
  Doubly Linked List  →  O(1) node detach + reinsert (prev+next = no scan)
  Sentinel head/tail  →  no null checks; every node always has neighbors

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 INVARIANTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  head.next  = MRU node (most recently used)
  tail.prev  = LRU node (least recently used, first to evict)
  map.size   ≤ capacity at the end of every put()
  map[key]   = the live list node for key (never a stale evicted node)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 OPERATIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  get(key):
    1. map.has(key)?  No → return -1
    2. node = map.get(key)
    3. removeNode(node)    // detach
    4. insertAtHead(node)  // promote to MRU
    5. return node.value

  put(key, value):
    1. key exists?  removeNode(map.get(key))   // remove old node first
    2. node = new Node(key, value)
    3. insertAtHead(node)
    4. map.set(key, node)
    5. map.size > capacity?
         lru = tail.prev
         removeNode(lru)
         map.delete(lru.key)    ← why Node stores key

  removeNode(node):          // 2 pointer writes
    node.prev.next = node.next
    node.next.prev = node.prev

  insertAtHead(node):        // 4 pointer writes — all 4 are required
    node.next           = head.next   // (1)
    node.prev           = head        // (2)
    head.next.prev      = node        // (3) ← #1 candidate mistake
    head.next           = node        // (4)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 COMMON BUGS (interview landmines)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Bug 1:  Missing  head.next.prev = node  in insertAtHead
          → backward links broken; removeNode silently corrupts the list

  Bug 2:  Not storing key in Node
          → eviction requires O(n) Map scan to find which key to delete

  Bug 3:  Calling insertAtHead before removeNode on an existing key in put()
          → node appears twice in the list; eviction count is off by one

  Bug 4:  Checking map.size > capacity before map.set()
          → eviction fires one step too early (off-by-one on capacity)

  Bug 5:  TTL check after insertAtHead
          → expired node gets promoted to MRU before it is caught; survives
            longer than its TTL

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 REDIS EVICTION POLICIES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  allkeys-lru      evict LRU from all keys            ← default for most apps
  volatile-lru     evict LRU from keys with TTL set
  allkeys-lfu      evict LFU from all keys            ← Big Billion Day hot items
  volatile-lfu     evict LFU from keys with TTL set
  allkeys-random   random eviction
  noeviction       reject writes when full (safest, no data loss)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 ONE-LINE DECISION RULE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  "Recently accessed = likely needed again"  →  LRU   (sessions, live feeds)
  "Frequently accessed = always needed"      →  LFU   (catalog, config, DNS)
  "Access pattern does not matter"           →  FIFO  (queues, write buffers)
```
