# Database Sharding: Range, Hash & Consistent Hashing — YouTube Script
Duration: ~10 min | Target: Engineers 3–10 YOE | Episode: 6 of 20

## HOOK (0:00–0:30)
"You add a fourth shard to your three-shard cluster. One line of code changes: modulo 3 becomes modulo 4. And that one line just triggered a migration of seventy-five percent of your entire dataset — every shard, all at once, because plain hash sharding remaps almost everything the moment the shard count changes. Today I'll show you the technique that fixes this completely: consistent hashing, and why it's the backbone of Cassandra, DynamoDB, and Redis Cluster."

[Screen cue: A big "% 3 → % 4" text flip, then a red flash over "75% OF DATA MUST MOVE".]

## THE PROBLEM (0:30–2:00)
"Think about it this way — imagine a library with ten million books on one sagging shelf. You split it into ten shelves. The question becomes: which book goes on which shelf? Sharding is exactly this — horizontal partitioning, splitting ROWS of a table across multiple database servers, where each server is a shard. The value you shard on — user ID, order ID — is your shard key, and picking it wrong is the number one mistake, because you can't change it later without migrating everything."

[Screen cue: Draw one overloaded shelf splitting into ten balanced shelves.]

## THE SOLUTION (2:00–5:00)
"Now watch what happens with each strategy. Range sharding splits by value range — user IDs one to two million on shard one, two to four million on shard two. Great for range queries, terrible in practice, because ALL new signups always land on the newest shard — that shard becomes a hot shard while the others sit idle. Hash sharding fixes the hotspot: shard equals hash of user ID modulo N gives you even distribution across all shards. But range queries now have to scatter-gather across every single shard, and worse, adding a shard changes the modulo, which reassigns almost every key at once. Consistent hashing solves THIS specific problem. Picture the shards arranged on a circle instead of a flat list. Each shard sits at a position on the ring, and each key routes to the nearest shard clockwise. When you add a new shard, only the keys between the new shard's position and its counterclockwise neighbor need to move — everything else on the ring stays exactly where it was. That's roughly one over N of your data moving, not seventy-five percent. And to keep load proportional across shards of different sizes, you give each physical shard multiple virtual node positions on the ring — Cassandra uses one hundred fifty virtual nodes per physical node by default."

[Screen cue: Draw the ring with 3 nodes, then add a 4th node and highlight only the small arc of keys that actually move.]

## DEEP DIVE — WHERE ENGINEERS GET IT WRONG (5:00–8:00)
"Here's the trap: choosing the wrong shard key up front, and there are exactly four criteria a good one must satisfy. High cardinality — country code with two hundred values is a bad shard key, because you can never get more than two hundred shards' worth of distribution. Even distribution — user ID for a B2B app where ten enterprise customers make up ninety percent of the data will hotspot no matter what hashing you use. Present in most queries — if your WHERE clause never filters by the shard key, every query scatter-gathers across all shards. And immutable — email as a shard key is a disaster, because changing a row's shard key means physically migrating that row to a different shard. Second trap: cross-shard JOINs simply don't work. If users live on shard one and orders live on shard three, you cannot JOIN them in SQL. The fixes are co-location — shard both tables by the same key, like user ID, so a user's data and their orders always land together — application-level joins, which are expensive but sometimes unavoidable, or denormalization, embedding the user's name directly in the orders table, which is what most high-scale systems actually do in production. And when you DO need to reshard, never do it as a single cutover — use a four-phase migration: dual-write to both old and new shard layouts, backfill the new layout in the background, cut reads over once backfill lag hits zero, then stop the dual-write."

[Screen cue: Split screen — cross-shard JOIN with a red X, then the four-phase migration timeline (dual-write → backfill → cutover → stop dual-write).]

## REAL WORLD (8:00–9:30)
"Think about a payments table at a PhonePe or Paytm scale — five hundred million rows, sharded by account ID using consistent hashing, because with modulo hashing, adding one shard to grow the cluster would mean migrating seventy-five to ninety percent of the data all at once, which is simply not viable at that scale. A cross-shard transfer — debiting account A on one shard, crediting account B on another — can't use a single database transaction, so it needs a Saga pattern with a compensating refund if the credit fails. Think about Flipkart's user and order data — co-located by user ID so a user's order history JOIN stays on a single shard, while sharding by category for the product catalog keeps category browsing fast. And Redis Cluster itself, used everywhere from Swiggy to Zomato for caching, uses a modified consistent hashing scheme with sixteen thousand three hundred eighty-four hash slots instead of a pure ring — adding a node just means moving a subset of slots, not rehashing everything."

[Screen cue: Three logo-style cards — "PhonePe/Paytm: consistent hashing for 500M-row payments", "Flipkart: co-located user+order shards", "Redis Cluster: 16,384 hash slots".]

## OUTRO + NEXT EPISODE (9:30–10:00)
"So remember: range sharding gives you range queries but risks hot shards, hash sharding gives you even distribution but breaks on resharding, and consistent hashing gives you both even distribution AND cheap resharding — which is exactly why Cassandra, DynamoDB, and Redis Cluster all use it. Subscribe for Episode 7, where I dig into read replica lag and the exact reason your own post disappears for two seconds right after you publish it."

[Screen cue: "NEXT: Episode 7 — Read Replica Lag & Read-Your-Own-Writes" title card with subscribe animation.]
