# Snowflake ID: Distributed Unique ID Generation
### How Twitter, Discord, and Instagram generate sortable unique IDs across thousands of machines without asking a central server for permission

---

## PART 1 — THE STUDENT CONVERSATION

Imagine you run a chain of 500 bakeries, and every bakery needs to stamp a unique receipt number on every order. If all 500 bakeries had to call one central office and ask "what's the next number?" before printing a receipt, that central office becomes a bottleneck — a line of 500 bakeries all waiting on one phone line. And if that office's phone line goes down, nobody can print a receipt anywhere in the world.

So instead, corporate gives every bakery a fixed ID (bakery #1 through #500) stamped on a wall plaque. Each bakery keeps its own local counter for the day. The receipt number is then built from three parts, jammed together: **today's date-and-time**, **this bakery's ID**, and **this bakery's local counter reset every millisecond**. No two bakeries can ever produce the same receipt number, because either their bakery ID differs, or if two bakeries somehow print at the exact same millisecond, their local counters still make the full number unique. And nobody had to phone anyone.

That's a Snowflake ID. It's a 64-bit integer built by gluing together a timestamp, a worker/machine ID, and a per-millisecond sequence counter. No central coordinator is consulted per-ID — each machine mints its own IDs locally, using only its own clock and its own pre-assigned worker ID. The "coordination" happens once, up front, when each machine is told its worker ID (the wall plaque), not on every single ID generation.

The reason this beats a random UUID (which also needs no coordination) is subtle but matters enormously at scale: because the timestamp is the *highest-order bits*, Snowflake IDs are roughly increasing over time. If you use this ID as a primary key in a B-tree index (like a MySQL InnoDB clustered index), new rows are always inserted at the "right edge" of the tree, which is cache-friendly and avoids the random-insertion page-splitting that a UUIDv4 primary key causes (see [041-uuid-as-primary-key-why-its-bad.md](041-uuid-as-primary-key-why-its-bad.md)). And because it's a single 64-bit long instead of a 128-bit UUID, it's half the storage and comparison cost, indexes packs twice as many keys per B-tree page.

---

## PART 2 — THE SNOWFLAKE ARCHITECTURE DIAGRAMS

### Bit Layout: Anatomy of a 64-bit Snowflake ID

```
 64-bit signed long (fits in Java's `long`, SQL BIGINT)

 Bit:   63           62                                  22          12         0
        │             │                                   │           │          │
        ▼             ▼                                   ▼           ▼          ▼
      ┌───┬──────────────────────────────────────────┬──────────┬──────────────┐
      │ 0 │        41 bits: TIMESTAMP (ms)            │ 10 bits: │  12 bits:    │
      │   │        milliseconds since custom epoch    │ WORKER   │  SEQUENCE    │
      │sgn│        (e.g. 2020-01-01T00:00:00Z)         │   ID     │  (per ms)    │
      └───┴──────────────────────────────────────────┴──────────┴──────────────┘
        1                    41                            10           12
      bit                  bits                           bits         bits
                                                       (= 1024 workers) (= 4096 ids/ms)

 Field breakdown:
 ┌─────────────┬───────┬──────────────────────────────────────────────────────┐
 │ Field       │ Bits  │ Meaning                                              │
 ├─────────────┼───────┼──────────────────────────────────────────────────────┤
 │ Sign bit    │ 1     │ Always 0 — keeps the value a positive signed long    │
 │ Timestamp   │ 41    │ ms since custom epoch. 2^41 ms ≈ 69.7 years of range │
 │ Worker ID   │ 10    │ 2^10 = 1024 unique machines/shards/pods              │
 │             │       │ (often split further: 5 bits datacenter + 5 bits    │
 │             │       │  machine — Twitter's original split)                │
 │ Sequence    │ 12    │ 2^12 = 4096 IDs mintable per worker per millisecond  │
 └─────────────┴───────┴──────────────────────────────────────────────────────┘

 Total: 1 + 41 + 10 + 12 = 64 bits
```

### Decoding a Real Example ID

```
Snowflake ID:  1541815603606036480

Step 1 — Convert to binary (64 bits, zero-padded):
  0 00000001101011101011010100010101110001100001 0000000001 000000000000
  │ └───────────────────41 bits──────────────────┘└─10 bits┘└──12 bits──┘
 sign         timestamp (ms since epoch)            worker    sequence

Step 2 — Extract timestamp (bits 63-22, right-shifted by 22):
  binary: 00000001101011101011010100010101110001100001
  decimal: 118654660577  (milliseconds since custom epoch 2020-01-01T00:00:00Z)
  wall-clock time = epoch_start + 118654660577 ms
                  = 2023-10-19T08:44:20.577Z

Step 3 — Extract worker ID (bits 21-12, mask with 0x3FF):
  (id >> 12) & 0x3FF = 1
  → generated by worker/shard #1

Step 4 — Extract sequence (bits 11-0, mask with 0xFFF):
  id & 0xFFF = 0
  → the 1st ID minted by worker #1 in that millisecond

Human-readable decode:
  "The 1st ID minted at 2023-10-19T08:44:20.577Z by worker #1"

Java decode snippet:
  long id = 1541815603606036480L;
  long epoch = 1577836800000L; // 2020-01-01T00:00:00Z in epoch millis
  long timestampMs = (id >> 22) + epoch;
  long workerId     = (id >> 12) & 0x3FF;
  long sequence     = id & 0xFFF;
```

### Throughput and Clock-Drift Handling

```
Single-worker throughput ceiling:
  12 sequence bits = 4096 distinct IDs per millisecond, per worker
  4096 IDs/ms × 1000 ms/sec = 4,096,000 IDs/sec  (~4.1M IDs/sec) per worker

  With 1024 workers (10 worker-ID bits) running in parallel:
  4.1M IDs/sec × 1024 workers ≈ 4.2 BILLION IDs/sec system-wide theoretical ceiling
  (in practice limited by network/DB write throughput downstream, not ID minting)

Sequence exhaustion within one millisecond (>4096 requests in <1ms):
  ┌─────────────────────────────────────────────────────────────┐
  │ t = 100ms, seq = 4095  → mint ID, seq++ → seq = 4096 (overflow)│
  │ seq >= 4096 → BUSY-WAIT until clock ticks to t = 101ms        │
  │ then reset seq = 0, mint next ID at new millisecond           │
  └─────────────────────────────────────────────────────────────┘

Clock going BACKWARDS (NTP correction, VM migration, leap second):
  ┌────────────────────────────────────────────────────────────────┐
  │ lastTimestamp = 100ms (last ID minted at t=100)                 │
  │ System clock now reads t = 98ms  (clock skewed backward by NTP) │
  │                                                                  │
  │ Option A — REJECT (Twitter's original approach):                │
  │   throw new ClockMovedBackwardsException(                       │
  │       "Refusing to generate id for " + (100 - 98) + "ms")       │
  │   → caller must retry / alert fires / worker restarts            │
  │                                                                  │
  │ Option B — WAIT (common in Sonyflake / some Snowflake forks):    │
  │   while (currentTimestamp() < lastTimestamp) { Thread.sleep(1); }│
  │   → blocks new ID generation until clock catches back up         │
  │   → safe but stalls this worker's ID minting for the drift window│
  │                                                                  │
  │ Both approaches favor CORRECTNESS (never reuse a timestamp+seq   │
  │ pair) over AVAILABILITY during the drift window.                │
  └────────────────────────────────────────────────────────────────┘
```

---

## PART 3 — INTERNALS, IMPLEMENTATION, AND REAL NUMBERS

### Reference Java Implementation

```java
public class SnowflakeIdGenerator {

    private static final long EPOCH = 1577836800000L; // 2020-01-01T00:00:00Z
    private static final long WORKER_ID_BITS = 10L;
    private static final long SEQUENCE_BITS = 12L;

    private static final long MAX_WORKER_ID = ~(-1L << WORKER_ID_BITS); // 1023
    private static final long MAX_SEQUENCE = ~(-1L << SEQUENCE_BITS);   // 4095

    private static final long WORKER_ID_SHIFT = SEQUENCE_BITS;                  // 12
    private static final long TIMESTAMP_SHIFT = SEQUENCE_BITS + WORKER_ID_BITS; // 22

    private final long workerId;
    private long sequence = 0L;
    private long lastTimestamp = -1L;

    public SnowflakeIdGenerator(long workerId) {
        if (workerId > MAX_WORKER_ID || workerId < 0) {
            throw new IllegalArgumentException(
                "Worker ID must be between 0 and " + MAX_WORKER_ID);
        }
        this.workerId = workerId;
    }

    public synchronized long nextId() {
        long timestamp = System.currentTimeMillis();

        if (timestamp < lastTimestamp) {
            // Clock moved backwards — reject rather than risk a duplicate ID.
            throw new IllegalStateException(String.format(
                "Clock moved backwards. Refusing to generate id for %d ms",
                lastTimestamp - timestamp));
        }

        if (timestamp == lastTimestamp) {
            sequence = (sequence + 1) & MAX_SEQUENCE;
            if (sequence == 0) {
                // Sequence exhausted this millisecond; spin until the clock ticks.
                timestamp = waitForNextMillis(lastTimestamp);
            }
        } else {
            sequence = 0L;
        }

        lastTimestamp = timestamp;

        return ((timestamp - EPOCH) << TIMESTAMP_SHIFT)
             | (workerId << WORKER_ID_SHIFT)
             | sequence;
    }

    private long waitForNextMillis(long lastTimestamp) {
        long timestamp = System.currentTimeMillis();
        while (timestamp <= lastTimestamp) {
            timestamp = System.currentTimeMillis();
        }
        return timestamp;
    }
}
```

### Worker ID Assignment: ZooKeeper-Coordinated

```
Startup sequence for a new pod joining a Kubernetes deployment:

1. Pod boots, connects to ZooKeeper ensemble.
2. Pod creates an EPHEMERAL_SEQUENTIAL znode under /snowflake/workers/
     → ZK assigns: /snowflake/workers/worker-0000000042
3. Pod parses the sequence suffix: workerId = 42
4. Pod checks: 42 <= MAX_WORKER_ID (1023)? Yes → proceed with workerId = 42
5. If ZK connection drops and pod restarts:
     → ephemeral znode is auto-deleted, pod re-registers, may get a NEW worker ID
     → this is safe: old worker ID becomes available for reuse only after
       enough time has passed that no duplicate (timestamp, seq) pairs collide

# Example ZooKeeper CLI interaction:
$ zkCli.sh -server zk1:2181
[zk: zk1:2181] create -e -s /snowflake/workers/worker- ""
Created /snowflake/workers/worker-0000000042
```

### Worker ID Assignment: Static Config (Simpler, No ZK Dependency)

```yaml
# application.yml — worker ID baked in per-pod via Kubernetes StatefulSet ordinal
snowflake:
  # StatefulSet guarantees pod-0, pod-1, pod-2... with stable identity
  # POD_NAME env var like "id-generator-3" → parse trailing ordinal as workerId
  worker-id: ${WORKER_ID:0}
```

```yaml
# Kubernetes StatefulSet snippet — injects ordinal-derived worker ID
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: id-generator
spec:
  serviceName: id-generator
  replicas: 8
  template:
    spec:
      containers:
        - name: id-generator
          env:
            - name: POD_NAME
              valueFrom:
                fieldRef:
                  fieldPath: metadata.name
          # entrypoint script extracts ordinal from POD_NAME (id-generator-0..7)
          # and exports WORKER_ID=<ordinal> before starting the JVM
```

```
Trade-off: static config is operationally simpler (no ZK/etcd dependency,
no extra moving part to fail), but caps you at a fixed, manually-managed
worker pool. ZooKeeper-coordinated assignment scales elastically (autoscaling
adds workers without a config change) but adds a hard dependency: if ZK is
unreachable at pod startup, new pods cannot mint IDs at all.
```

### Real-World Throughput Numbers

```
Discord's Snowflake (epoch 2015-01-01, same 41/10/12 layout as Twitter's):
  - Single Rust/Go worker: >4M IDs/sec generation rate (CPU-bound only on
    the atomic increment + bit-shift, no I/O)
  - Production message IDs regularly exceed 10^18 in magnitude by 2023,
    consistent with ~8 years × 41-bit ms timestamp range

Instagram's approach (76 bits total, sharded across Postgres logical shards):
  - 41 bits timestamp (ms, custom epoch)
  - 13 bits shard ID (8192 logical shards, mapped many-to-one onto physical DBs)
  - 10 bits per-shard sequence (1024 IDs/ms/shard) generated via a Postgres
    PL/pgSQL function on each shard — coordination-free because each row
    write only ever talks to its own shard's sequence.

Rule of thumb sizing:
  10 worker-ID bits is enough for 1024 machines — comfortably covers most
  single-region deployments. If you need more machines than sequence
  headroom allows, widen worker bits and shrink sequence bits (e.g. Discord
  keeps 10/12 like Twitter; some forks use 8 worker bits / 14 sequence bits
  for fewer-but-busier workers).
```

---

## PART 4 — THE INTERVIEW CONVERSATION

**Interviewer:** "We're sharding our orders table across 200 database nodes. We need a primary key that's unique across all shards, doesn't require a round-trip to a central ID service, and ideally sorts roughly by creation time so recent orders cluster together on disk. How would you design this?"

**You (architect answer):**

> "I'd use a Snowflake-style ID generator rather than UUIDs or an auto-increment sequence. An auto-increment primary key doesn't work once you have 200 independent shards — you'd need a single global counter, which becomes a write bottleneck and a single point of failure. UUIDv4 solves the coordination problem, since it's generated locally with no communication, but it comes at a real cost: it's 128 bits versus 64, and it's randomly distributed, so as a clustered index key it causes random-order B-tree inserts — that means page splits and poor cache locality on every insert, which shows up as write amplification once your tables get large.
>
> Snowflake fixes both problems. I'd lay out a 64-bit long as: 1 unused sign bit, 41 bits for a millisecond timestamp since a custom epoch — giving about 69 years of range — 10 bits for a worker ID, and 12 bits for a per-millisecond sequence counter. Each of the 200 shard-writer processes gets a unique worker ID assigned at startup, either via a static config injected by our Kubernetes StatefulSet ordinal, or dynamically through a ZooKeeper ephemeral sequential znode if we want elastic autoscaling. Because the timestamp occupies the highest bits, IDs generated later are numerically larger — which means as a primary key, new rows always insert at the tail of the B-tree instead of scattering randomly across pages.
>
> Throughput-wise, 12 sequence bits gives us 4096 IDs per millisecond per worker, or about 4.1 million IDs per second per worker — vastly more than any single shard-writer will realistically need, so contention on the sequence counter isn't a concern.
>
> The one production issue I'd flag upfront is clock drift. If NTP corrects a machine's clock backward, or a VM migrates and its clock jumps, you risk generating a duplicate ID if you naively use the current system time. My mitigation: the generator tracks the last timestamp it used, and if `System.currentTimeMillis()` ever returns something earlier than that, it throws immediately rather than minting an ID — we fail loudly and let the caller retry, instead of silently risking a duplicate primary key. I'd also alert on that exception in production, because repeated clock-backward events usually indicate an NTP or hypervisor issue worth investigating, not just noise to swallow."

---

## PART 5 — DECISION FRAMEWORK

### Snowflake vs Alternatives for Distributed Unique IDs

| Approach | How It Works | Consistency/Tradeoff | Index Locality | Size | When It Fails |
|---|---|---|---|---|---|
| **Snowflake ID** | Timestamp + worker ID + sequence, minted locally | No coordination per-ID; needs unique worker-ID assignment once | Excellent — roughly monotonic | 64 bits | Clock drift can force wait/reject; worker-ID exhaustion at >1024 nodes |
| **UUIDv4 (random)** | 122 random bits + version/variant bits | Fully coordination-free, collision-probability based | Poor — random B-tree inserts | 128 bits | Never "fails," but write amplification hurts at scale |
| **UUIDv7 (time-ordered)** | Unix timestamp (ms) prefix + random suffix | Coordination-free | Good — time-ordered like Snowflake | 128 bits | Larger than Snowflake; still 2x storage cost |
| **Central sequence/counter service** | Single service hands out next integer | Strongly consistent, single source of truth | Perfect (strictly sequential) | 64 bits (or less) | Bottleneck + SPOF; round-trip latency per ID |
| **DB auto-increment (per-shard)** | Each shard has its own AUTO_INCREMENT | Locally consistent, globally NOT unique without shard-prefixing | Perfect within a shard | 32-64 bits | IDs collide across shards unless you embed shard ID in the key |

### When Snowflake Is the Right Choice

```
Use Snowflake IDs when:
  ✓ You're sharding across many nodes and need globally unique keys
  ✓ You want IDs that sort roughly by creation time (chat messages, feed
    items, orders — anything queried "most recent first")
  ✓ You care about primary-key index locality and storage size (64 bits
    vs 128 for UUID) at high write volume
  ✓ You can tolerate a one-time worker-ID assignment step per machine/pod
  ✓ You need to decode "when was this created" directly from the ID
    without a DB lookup (useful for debugging, sharding-by-time-range)

Skip Snowflake when:
  ✗ You need IDs that reveal NOTHING about creation order or count
    (Snowflake leaks approximate creation time and can leak system
    throughput if sequence bits are exposed — use UUIDv4 for
    security-sensitive public identifiers like password-reset tokens)
  ✗ Your fleet exceeds 1024 concurrent ID-minting workers (10 bits) —
    widen worker bits or shard by a different key
  ✗ You have no way to reliably assign unique worker IDs (no ZK/etcd,
    no static config management) — coordination-free UUIDv4 is simpler
  ✗ Clock synchronization (NTP) is unreliable in your environment — every
    clock-backward event either stalls or rejects ID generation
```

---

## QUICK REFERENCE CARD

```
BIT LAYOUT (64 bits total):
  1 bit   sign (always 0)
  41 bits timestamp (ms since custom epoch, ~69.7 yr range: 2^41 / (1000*60*60*24*365.25))
  10 bits worker ID   (2^10 = 1024 workers)
  12 bits sequence    (2^12 = 4096 ids/ms/worker)

ID CONSTRUCTION:
  id = ((now_ms - EPOCH) << 22) | (workerId << 12) | sequence

DECODE:
  timestamp = (id >> 22) + EPOCH
  workerId  = (id >> 12) & 0x3FF
  sequence  = id & 0xFFF

THROUGHPUT:
  4096 ids/ms/worker × 1000 ms = ~4.1M ids/sec/worker
  × 1024 workers = ~4.2B ids/sec theoretical system ceiling

CLOCK-BACKWARDS HANDLING:
  now < lastTimestamp → REJECT (throw) or WAIT (spin until clock catches up)

WORKER-ID ASSIGNMENT:
  ZooKeeper: EPHEMERAL_SEQUENTIAL znode → parse suffix as workerId
  Static:    Kubernetes StatefulSet ordinal → env var WORKER_ID
```
