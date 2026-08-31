# Why does a Redis node crash wipe out your cache even though you thought it was durable?

**Type:** Trap Question
**Topic:** Redis Architecture — Persistence Misunderstandings
**Level:** Senior Interview (8–12+ YOE) — common gotcha

## Direct Answer
Because, by default, Redis keeps data **in memory**, and without explicitly configuring persistence (RDB snapshots and/or AOF append-only logging), a crash or restart loses everything that hasn't been separately backed up. Many teams assume "it's a database, so it must save to disk automatically" — but Redis's core design principle is speed via in-memory storage, and durability is an opt-in feature you must configure, not a default guarantee.

## Easy Explanation
Redis's default behavior is like a whiteboard: extremely fast to read and write, but if the power goes out, everything on it is gone unless someone took a photo of it first (a snapshot) or was continuously writing every stroke to a notebook as backup (an append-only log). People sometimes assume "it's called a data store, so it must remember things forever" — but Redis's speed advantage specifically comes *from* not treating every write as something that must survive a crash unless you tell it to.

## Diagram
```
Default Redis (no persistence configured):

Write:  SET session:42 "active"   -> stored in RAM only
                                        |
                                  Redis process crashes / server reboots
                                        |
                                        v
                                 RAM is cleared -> session:42 is GONE, no way to recover

With persistence configured:

Option A: RDB snapshot          -> periodic point-in-time dump to disk (some recent data loss possible)
Option B: AOF (append-only file) -> every write logged to disk as it happens (minimal data loss)
Option C: RDB + AOF combined     -> fast restart from snapshot + replay recent log entries

                                  Redis process crashes / server reboots
                                        |
                                        v
                              Redis reloads from RDB/AOF on startup -> data restored
```

## Production Example
A team relied on Redis to store shopping-cart sessions "because it's our database," without enabling any persistence. A routine server patch triggered a restart, and every active shopping cart across the platform vanished instantly, with no way to recover them — a very costly and avoidable incident.

```conf
# redis.conf — enabling durability explicitly
appendonly yes
appendfsync everysec
save 900 1
save 300 10
```

Teams that need cache-only behavior often accept this trade-off intentionally (losing the cache just means slower reads until it repopulates); teams that need durability must explicitly configure RDB/AOF and test their recovery process, not assume it "just works."

## Why Interviewers Ask This
It's one of the most damaging real-world misunderstandings about Redis. This question checks whether a candidate treats persistence as a conscious architectural decision (with real trade-offs) rather than an assumed default.
