# Interview Guide: Consistent Hashing

## 🗣️ The Interview Scenario

> "You're building the sharding layer for a distributed key-value store. Today you run 3 database nodes and you shard data across them using `hash(key) % 3`. Traffic is growing and you're about to add a 4th node. Walk me through what breaks when you do that, and how you'd redesign the sharding scheme so that adding or removing a node doesn't force you to move almost all of your data."

This is a scenario question, not a definition question — the interviewer wants to see if you understand **why** simple hashing fails under node churn, not just that "consistent hashing exists."

## 🏗️ Architect's Explanation (For a New Developer)

Think of hashing like a **coat-check counter with numbered pegs**. A hash function takes something of arbitrary size — a name, a URL, a user ID — and boils it down to a fixed-size number. "Mod hashing" is the trick of taking that number and doing `% N` (where `N` is the number of pegs/servers you have) to decide which peg an item hangs on.

That works beautifully as long as **the number of pegs never changes**. The moment you add or remove a peg, `N` changes, and `hash(key) % N` gives a *completely different* answer for almost every key — even though the key itself never changed. It's like a coat-check clerk suddenly deciding "everyone move three pegs to the left" the instant a new peg is installed. Every coat has to be found and re-hung. In distributed systems terms, this is called **rebalancing**, and doing it for millions or billions of records because you added *one* server is a disaster.

Consistent hashing solves this with a different picture: instead of numbered pegs in a row, imagine a **circular clock face** (a "ring"). Both your servers and your data keys get a position on this ring (using the same hash function). To find which server owns a key, you just **walk clockwise from the key's position until you hit the first server**. Now, when you add or remove a server, only the small arc of keys *between that server and its neighbor* need to move — everything else on the ring is untouched.

## 📊 Visualize It

**Basic ring assignment (clockwise ownership):**

```
                     0
              11  ┌─────┐  1
                  │       │
            10 ───┤  RING ├─── 2      Ring size = 12 (mod 12)
                  │       │
             9  ──┤       ├── 3       S1, S2, S3 placed on ring
                  │       │           by hashing their server IDs
             8    └─────┘  4
                     |
              7      6      5

Placed:  S1 @ pos 2   S2 @ pos 5   S3 @ pos 11

Keys walk CLOCKWISE to find their owner:
  key1(pos1) -> S1      key5(pos4) -> S2
  key2(pos2) -> S1      key6(pos6) -> S3
  key3(pos3) -> S1      key7(pos7) -> S3   (wraps to S1 only after S3)
  key4(pos4) -> S2
```

**Before/after adding a node (only a small slice moves):**

```
BEFORE (S1,S2,S3):                AFTER adding S4 (between S2 and S3):

 K1,K2 -> S1  (unchanged)          K1,K2 -> S1  (unchanged)
 K5    -> S2  (unchanged)          K5    -> S2  (unchanged)
 K6,K3,K4 -> S3                    K6,K3,K4 -> S3  (unchanged)
 K7    -> S2                       K7    -> S4  <-- ONLY this key moved!
```

Only the keys sitting in the arc between the new node and its clockwise neighbor get reassigned. Everything else stays exactly where it was.

## 🔧 Deep Dive: How It Actually Works

### 1. Why plain (mod) hashing breaks
- Mod hashing works perfectly when the hash table / server count is **fixed**.
- Real systems have **dynamic** node counts: application servers behind a load balancer can scale up/down, and DB shards can be added/removed for horizontal sharding.
- Example from the walkthrough: 3 servers, routing uses `hash(key) % 3`. Add a 4th server → routing becomes `hash(key) % 4`. A key that used to resolve to node 1 might now resolve to node 2 — but the *data* is still physically sitting on node 1. The application looks in the "new" node, finds nothing, and the request fails until a full **rebalance** moves the data.
- At small scale (3 keys) this looks trivial. At real scale — millions/billions of DB rows, or thousands of user-ID → server mappings — a single node addition or removal can force you to re-shuffle almost the entire dataset.

### 2. The formula consistent hashing guarantees
- Consistent hashing's whole purpose: when a node is added **or** removed, minimize how much data must move.
- The bound it targets: **on average, only `(1/N) × 100%` of total keys should need rebalancing**, where `N` = number of active nodes.
- Compare that to plain mod hashing, where a single node change can force near-100% of keys to move. This ratio (`1/N` vs "almost everything") is the single most quotable fact in this topic.

### 3. Building the ring
- Take a **virtual ring** of fixed size (in the example, size 12 — positions 0 through 11, wrapping back to 0). This size is independent of how many servers you currently have.
- Hash each **server** (using the same hash function, e.g., `hash(serverName) % 12`) to get its position on the ring.
- Hash each **key** the same way to get its position.
- **Ownership rule:** starting from a key's position, walk **clockwise**; the first server you encounter owns that key.

### 4. What happens on add / remove
- **Add a node:** insert it at its hashed position on the ring. Only keys that fall between the new node and its counter-clockwise neighbor (i.e., keys that used to route past that gap to the *next* server) get reassigned to the new node. Every other key/server pairing is untouched.
- **Remove a node:** its keys simply fall through to the *next* server clockwise. Again, only that node's keys move — nobody else's assignment changes.
- This is exactly how the `1/N` bound is achieved in practice — the "blast radius" of a topology change is local to the ring, not global.

### 5. The disadvantage: uneven distribution
- If servers happen to land close together on the ring (e.g., all three cluster in one arc), one server ends up owning a disproportionately large arc — and therefore a disproportionate share of keys/traffic. The whole point of hashing (spreading load evenly) is defeated.
- Concretely: if S1, S2, S3 all hash close together, walking clockwise from most keys hits **S1** first almost every time — S1 gets overloaded while S2/S3 sit idle.

### 6. The fix: virtual nodes (replicas)
- Solution: **replicate each physical server at multiple random points on the ring** ("virtual nodes"). Instead of hashing a server once, hash it 2–3+ times (or append salts/counters) and place each resulting position on the ring, all pointing back to the same physical server.
- Example: Server 1 gets placed at positions 2, 8, and 11. Server 2 at 6 and 10. Server 3 at 1 and 9. Now the ring has many small, interleaved arcs instead of a few large lopsided ones, and load spreads far more evenly across the *real* servers.
- **How many replicas do you need?** Enough virtual points that the actual observed rebalancing/load-distribution matches the target `1/N` percentage. More virtual nodes → smoother distribution, at the cost of more ring bookkeeping.

### 7. Where it's used
- Anywhere nodes are **dynamic** and you need to divide traffic/data evenly: load balancing across application servers, and horizontal sharding of databases (the two examples used throughout). Real systems like DynamoDB and Cassandra rely on this exact mechanism.
- If node count is **static** and never changes, plain hashing is fine — consistent hashing earns its complexity only when nodes come and go.

## 🔥 Real Production Incident & Fix

**What broke:** A caching layer (Redis-backed, sharded across nodes using a custom consistent-hashing client) was scaled from 4 nodes to 5 nodes ahead of an expected traffic spike. Within minutes of the new node joining, on-call got paged for a spike in database read latency and a collapse in cache hit ratio (from ~92% down to ~55%).

**How it was diagnosed:** Dashboards showed cache hit rate dropping cluster-wide, not just on the new node — that ruled out "new node is just cold." Digging into per-node key distribution metrics revealed the new node had been hashed to a ring position that landed it *right next to* an existing heavily-loaded node, and — because the client library used **only one hash point per physical node** (no virtual nodes) — the new node inherited a huge, uneven arc of keys instead of a proportional ~20% slice. Meanwhile, because ring positions are deterministic from server identity, adding the node shifted ownership for a large contiguous arc of keys away from their previous owners, invalidating a large swath of the cache all at once (not just 1/N of it).

**Root cause:** The consistent-hashing implementation didn't use virtual nodes/replicas. With so few hash points (one per server), the ring was lumpy — some servers legitimately owned much bigger arcs than others — so adding a single physical node could still displace a disproportionate number of keys, and, worse, could rehash a chunk of "hot" keys instead of spreading the disruption evenly.

**The fix:** Re-deployed the caching layer's hashing scheme with **150 virtual nodes per physical server** (a common production default), redistributed the ring, and added a dashboard panel tracking per-node key-count as % of total (alerting if any node deviates more than ~15% from `1/N`). Cache hit ratio recovered within 10 minutes of the rollout, and the next node addition (a 6th node, added a week later) caused a barely visible 2% dip in hit ratio instead of a 40-point crash.

```
BEFORE (1 hash point/server, lumpy ring):     AFTER (150 virtual nodes/server):

  S5(new) lands next to S2's big arc          S5's virtual points scattered evenly
  → inherits a huge, uneven slice             → each server owns ~1/N of ring
  → mass cache invalidation, hit rate crash   → smooth, small, even rebalance
```

## ❓ Likely Interview Follow-Up Questions & Answers

**Q1: What's the actual difference in rebalancing cost between mod hashing and consistent hashing?**
With mod hashing, changing the node count from N to N±1 changes the divisor for every single key's routing, so in the worst case nearly 100% of keys must move. Consistent hashing bounds this to roughly `1/N` of keys on average, because only the ring arc adjacent to the changed node is affected — every other key-to-server mapping is geometrically untouched.

**Q2: Why do we need virtual nodes at all — isn't hashing servers onto the ring enough?**
A single hash point per server can, by chance, cluster servers unevenly on the ring, giving some servers much larger arcs (and therefore much more load) than others. Virtual nodes hash each physical server multiple times to multiple ring positions, which statistically smooths out the arc sizes so load distributes close to evenly, independent of unlucky hash collisions in placement.

**Q3: How many virtual nodes should you use per physical server?**
Enough that the empirical load distribution converges close to `1/N` per server — in practice this is often in the range of 100–200+ virtual nodes per physical node for large clusters, tuned by monitoring per-node key/traffic share and increasing replicas if any node consistently skews high.

**Q4: How does consistent hashing handle an unplanned node failure (crash), not just a graceful removal?**
Mechanically it's the same ring operation as removal — the crashed node's arc of keys now resolves to the next node clockwise. The operational difference is you need failure *detection* (health checks/heartbeats) to trigger removing the dead node from the ring quickly, otherwise requests keep routing to a server that's actually down.

**Q5: If a node's data must be moved during rebalancing, isn't there a window where reads/writes to those keys fail or see stale data?**
Yes — that's why production systems (DynamoDB, Cassandra) layer **replication** on top of consistent hashing: each key is stored on the next R servers clockwise (not just one), so even mid-rebalance there are still live replicas serving the data while the ring transitions.

**Q6: How would you detect in production that your ring has become unevenly loaded before it causes an incident?**
Track per-node share of total keys/traffic as a percentage and alert when any node's share deviates significantly from the ideal `1/N` (e.g., more than a chosen tolerance). This catches "lumpy ring" problems (too few virtual nodes, or a bad hash function with poor distribution) before they turn into a hot-node outage.

## 🔑 Key Takeaway

Say this out loud in the interview: **"Consistent hashing bounds the blast radius of adding or removing a node to about `1/N` of the keys, instead of nearly all of them like plain mod hashing — and virtual nodes are what make that bound actually hold up evenly in practice."**
