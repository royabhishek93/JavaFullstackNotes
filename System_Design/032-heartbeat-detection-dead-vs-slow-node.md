# Heartbeat Detection
### How a Node Knows a Peer Is Dead vs Just Slow

---

## PART 1 — THE STUDENT CONVERSATION

**Imagine you're working in an office. Your colleague usually sends you a message every hour.**

If you don't hear from them for 2 hours, you might think: "They're busy." After 8 hours: "Something's wrong." After 24 hours: "They might have quit." You don't know for certain — they could be in a meeting, on vacation, or in the hospital.

Distributed systems face the exact same problem. **You can never truly know if a remote node is dead or just slow.** This is the fundamental challenge called the "detection problem" in distributed systems.

A **heartbeat** is a periodic "I'm alive" message. If a node stops receiving heartbeats from a peer, it suspects that peer is down. After a timeout, it declares the peer dead and takes action (promote a replica, reroute traffic, re-replicate data).

The challenge: **set the timeout too short → false failures. Set it too long → real failures go undetected for too long.**

---

## PART 2 — HOW HEARTBEATS WORK

```
Basic heartbeat mechanism:
────────────────────────────────────────────────────────────────

  Node A (Primary)              Node B (Replica/Monitor)
  ────────────────              ────────────────────────

  every 1 second:
  ──────────────►  "PING: alive, epoch=42, load=30%"
  ◄──────────────  "PONG: received"

  every 1 second:
  ──────────────►  "PING: alive, epoch=42, load=31%"
  ◄──────────────  "PONG: received"

  Node A goes down (crash, OOM killer, power loss):

  1s later:  Node B waits... no PING.
  2s later:  Node B waits... timeout counter = 2
  3s later:  Node B waits... timeout counter = 3
  (after timeout threshold, e.g., 5 seconds):
  5s later:  Node B: "Node A missed 5 heartbeats. Mark as SUSPECT."
  10s later: Node B: "Still no heartbeat for 10s. Declare DEAD. Begin failover."

Timeline:
  t=0:   Node A dies
  t=10s: Node B declares A dead, begins promoting itself
  t=10s: Downtime begins for writes
  t=15s: Failover complete, Node B is primary
  Total undetected downtime: 10-15 seconds
```

### Network Slowness vs Death

```
The detection problem:
──────────────────────────────────────────────────────────────

  Scenario A: Node A is dead
  ──────────────────────────
  Node A: [DEAD — no process, no network]
  Node B: no heartbeat after 5s → correct! A is dead.

  Scenario B: Node A is alive but network is slow
  ────────────────────────────────────────────────
  Node A: [ALIVE — sending heartbeats]
  Network: congested, heartbeat delayed by 6 seconds
  Node B: no heartbeat for 6s → marks A as dead → WRONG (false positive)
  Node B promotes itself → SPLIT BRAIN!

  This is why timeout tuning matters:
  Too low (1s): normal network jitter triggers false failover
  Too high (60s): real failures take 60s+ to detect → long downtime

  Production values used by real systems:
  Redis Sentinel:   down-after-milliseconds = 30000 (30s)
  Kubernetes:       liveness probe: failureThreshold=3, periodSeconds=10 → 30s
  MySQL Orchestrator: detection within ~15s
  etcd:             election timeout 1s, heartbeat 100ms
```

---

## PART 3 — GOSSIP PROTOCOL (SCALABLE HEARTBEAT)

```
Problem with naive heartbeat at scale:
────────────────────────────────────────────────────────────────

  100 node cluster, each node sends heartbeat to every other node:
  → 100 × 99 = 9,900 heartbeat messages per second
  → O(N²) — doesn't scale

  Solution: Gossip Protocol (used by Cassandra, Consul, Redis Cluster)

Gossip works like rumours in an office:
  Instead of everyone telling everyone:
  → Each node tells 3 random peers its state every 1 second
  → Those 3 peers merge the info and tell 3 more random peers
  → Within log(N) rounds, all nodes know everyone's state

  100 nodes, 3 peers each round:
  Round 1: 3 nodes know A's state
  Round 2: 9 nodes know A's state
  Round 3: 27 nodes know A's state
  Round 4: 81 nodes know A's state
  Round 5: 100 nodes know A's state
  → O(log N) rounds, O(N log N) total messages — far better than O(N²)
```

### Gossip Payload: What Gets Exchanged

```
Cassandra gossip message (simplified):
────────────────────────────────────────────────────────────────

  Node A sends to Node B:
  {
    "node_states": {
      "10.0.0.1": { status: "UP", generation: 42, version: 1001, load: "30%" },
      "10.0.0.2": { status: "UP", generation: 38, version: 992,  load: "45%" },
      "10.0.0.3": { status: "DOWN", generation: 15, version: 200, load: "0%" },
      "10.0.0.4": { status: "UP", generation: 51, version: 1500, load: "60%" }
    }
  }

  Node B merges: takes highest version for each node
  If B has newer info about a node → keeps its version
  If A has newer info → updates from A's info

  "generation" = monotonically increasing integer assigned when node restarts
                 (a restarted node has higher generation → its own info wins)

Fields used for failure detection:
  version: incremented every heartbeat → if version stops increasing → node is DOWN
  generation: resets to new value on restart → distinguish "just restarted" from "long-running"
```

---

## PART 4 — ACCRUAL FAILURE DETECTOR (PHI ACCRUAL)

> Used by Cassandra and Akka. More sophisticated than simple timeouts.

```
Simple timeout: "If I don't hear for 10s, node is dead." (binary: alive or dead)

Phi accrual: outputs a SUSPICION LEVEL (a number), not a binary decision
             "Node A's suspicion score is 4.5 — probably slow, not dead"
             "Node A's suspicion score is 12 — almost certainly dead"

How it works:
  Tracks the statistical distribution of heartbeat intervals:
  Historical intervals: [1.0s, 1.1s, 0.9s, 1.0s, 1.2s, 0.8s]
  Mean: 1.0s, StdDev: 0.13s

  When time-since-last-heartbeat = 3.0s:
  Phi = -log10(P(interval > 3.0s))
  P is very small (3.0s is 15 standard deviations away from mean)
  Phi ≈ 10 → high suspicion → declare dead

  When time-since-last-heartbeat = 1.5s:
  P is moderate (1.5s is ~3.8 std devs)
  Phi ≈ 2 → low suspicion → just slow, not dead

Benefits:
  Adapts to network conditions automatically
  Slow network with 200ms jitter → threshold adjusts upward
  Fast network → threshold is tight, fast detection
  Avoids false positives on GC pauses (Java GC can pause for 5–30s)
```

---

## PART 5 — THE INTERVIEW CONVERSATION

**Interviewer:** "Your distributed rate limiter Redis cluster has a primary that becomes slow due to GC. What happens?"

**You (architect answer):**

> "This is the 'dead vs slow' detection problem. A Java GC pause can last 5–30 seconds on
> a heavily loaded JVM. If Redis Sentinel's heartbeat timeout is 30 seconds, a GC pause could
> trigger a false failover — Sentinel declares the primary dead, promotes a replica, and now
> we have two primaries briefly.
>
> The proper fix has two parts.
>
> First, tune the GC: for a Redis process, I'd use a non-JVM implementation or ensure the
> JVM running any sidecar is tuned for low-pause GC (G1GC or ZGC with -XX:MaxGCPauseMillis=200).
>
> Second, tune Sentinel's detection: set down-after-milliseconds conservatively — I'd use 10-15
> seconds rather than the default 30 to detect real failures faster, but test against the actual
> GC behavior in staging. If GC pauses are under 2 seconds, 10 second timeout gives us 8 seconds
> of buffer.
>
> The third option — which I'd use for a critical rate limiter — is to use Redis Cluster instead
> of Sentinel, combined with the min-replicas-to-write safeguard. This way, a primary that's
> GC-pausing and can't replicate stops accepting writes rather than staying live with stale state."

---

## PART 6 — HEARTBEAT VALUES IN REAL SYSTEMS

```
System                  │ Heartbeat interval │ Timeout / Detection
────────────────────────┼────────────────────┼────────────────────────────────
Redis Sentinel          │ 1s PING            │ down-after-milliseconds (30s default)
Kubernetes liveness     │ periodSeconds=10   │ failureThreshold=3 → 30s total
etcd (Raft)             │ 100ms heartbeat    │ 1000ms election timeout
ZooKeeper               │ tickTime=2000ms    │ 4 × tickTime = 8s (initLimit)
Cassandra (gossip)      │ 1s gossip round    │ Phi > 8 → marked DOWN (phi_convict_threshold)
MySQL Orchestrator      │ 1s check           │ 3 consecutive failures → suspect
Consul                  │ 1s                 │ 10s (default)
Kafka (broker)          │ 3s                 │ session.timeout.ms = 30s (consumer)

Production recommendation:
  heartbeat interval = 1s
  timeout = 3× to 10× of heartbeat (3s–30s depending on network stability)
  failure confirmation = require 3 missed heartbeats (not 1) to avoid flapping
```

---

## QUICK REFERENCE CARD

```
Heartbeat: periodic "I'm alive" message (usually 1s interval)
Timeout: how long to wait before declaring dead (usually 10–30s)

False positive (wrongly declared dead):
  Cause: slow network, GC pause, CPU spike
  Effect: unnecessary failover → split brain risk
  Fix: increase timeout, use phi accrual (adapts to network behavior)

False negative (real failure not detected):
  Cause: timeout too high
  Effect: long downtime before failover
  Fix: decrease timeout (but test against GC/network jitter)

Gossip protocol:
  Each node gossips to ~3 random peers each second
  State propagates in O(log N) rounds
  O(N log N) messages total — scales to thousands of nodes

Phi Accrual (used by Cassandra, Akka):
  Not binary alive/dead — outputs a suspicion score
  Adapts to actual observed network latency distribution
  Threshold configurable: phi_convict_threshold=8 (Cassandra default)

Interview one-liner:
"You can never know for certain if a remote node is dead or just slow.
Heartbeat detection is a statistical bet: if I haven't heard in N seconds,
it's more likely dead than slow. The timeout trades false positives
(unnecessary failovers) against false negatives (slow failure detection)."
```

---

## WHERE THIS PATTERN APPEARS IN YOUR SYSTEM DESIGN INTERVIEWS

> **For the 2-year developer:** Every distributed system needs to know when a node dies — heartbeat is how, and the timeout value is a real trade-off you'll be asked to justify.

| System | Why This Pattern Is Needed Here |
|--------|----------------------------------|
| **02 — Rate Limiter** | Redis Sentinel heartbeat timeout: too short → false failover during GC pause → counter state lost → rate limit resets. Phi Accrual detector adapts to Redis GC pauses instead of using a fixed threshold. |
| **04 — Chat** | WebSocket server detects client disconnects via heartbeat ping/pong. 3 missed pings → mark offline → update presence. Critical for "last seen" accuracy. |
| **07 — Payment** | Payment service instances heartbeat to load balancer. Crashed instance stops heartbeating → LB stops routing within timeout → no payments lost to dead instance. |

**Architect's one-liner for the interview:**
*"Heartbeat timeout is a bet: short timeout catches failures fast but causes false positives on slow nodes; long timeout reduces false positives but leaves traffic routing to a dead node for longer — tune it to the cost of each error."*
