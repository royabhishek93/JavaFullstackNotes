# How does replica failover prevent total data loss when the Redis master crashes?

**Type:** Advanced Scenario-Based
**Topic:** Redis Architecture — Replication & High Availability
**Level:** Staff Interview (10–15+ YOE)

## Direct Answer
Data written to the master is continuously **replicated** to one or more replica ("slave") nodes. If the master crashes, a replica already holding a near-real-time copy of the data can be promoted to become the new master (manually, or automatically via Redis Sentinel/Cluster), so the system keeps running with minimal data loss instead of losing everything a single node held.

## Easy Explanation
Imagine one person (the master) is the only one keeping notes during a meeting, and if they suddenly leave the room, all their notes are gone. Now imagine a second person (a replica) is silently copying every note the first person writes, in near real-time. If the first person leaves, the second person already has (almost) everything and can immediately take over as the note-taker — the meeting doesn't lose its history, and barely misses a beat.

## Diagram
```
Normal operation:
Client --writes--> [ Redis MASTER ] --replicates continuously--> [ Redis REPLICA ]
Client --reads-->  [ Redis MASTER ]  (or replica, for read scaling)

Master crashes:
Client --writes--> [ Redis MASTER: DOWN ]         [ Redis REPLICA: has near-current copy ]
                                                            |
                                          Sentinel/Cluster detects failure,
                                          promotes replica to new master
                                                            |
                                                            v
Client --writes--> [ Redis REPLICA (now MASTER) ]   <- system recovers, minimal data loss
```

## Production Example
A production Redis deployment runs with one master and two replicas, monitored by Redis Sentinel. When the master's underlying VM has a hardware failure, Sentinel detects the outage within seconds, elects the replica with the most up-to-date data as the new master, and reconfigures clients to point at it — all without a human needing to intervene at 3 AM. Some data written in the final moments before the crash (anything not yet replicated) can still be lost, which is why critical write paths often also require acknowledging the write on at least one replica (`WAIT` command) before considering it "durable."

## Why Interviewers Ask This
It tests whether a candidate understands that replication provides **availability** and **reduced** data-loss risk — not a 100% guarantee against any data loss — and whether they know the operational pieces (Sentinel/Cluster) that actually perform the failover, rather than assuming replication alone is a complete high-availability solution.
