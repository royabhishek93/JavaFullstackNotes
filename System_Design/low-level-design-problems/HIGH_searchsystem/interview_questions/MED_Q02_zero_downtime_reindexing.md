# MED Q02 - Zero-Downtime Reindexing

## Scenario
You need to change analyzer/tokenization for an index with live traffic.

## Correct Approach
1. Build new index version in parallel.
2. Backfill all documents.
3. Dual-write during migration window.
4. Atomically switch alias to new index.
5. Retire old index after verification.

## Interview One-Liner
Reindexing without aliases causes downtime or inconsistent reads.
