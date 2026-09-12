# DB Cursor — Resource-Safe Streaming from PostgreSQL to S3
> **Topic:** Generator Functions | **Level:** Intermediate | **Frequency:** Medium

## The Setup

A data pipeline job must stream 10 million rows from PostgreSQL to S3 as NDJSON. Loading all rows into memory causes an OOM crash. The job must also guarantee the DB connection is released even if the consumer crashes mid-stream. This scenario tests async generator resource management via `finally`.

## The Question

"You need to stream 10 million rows from PostgreSQL to S3 as NDJSON without OOM-killing the process. How do you structure this, and how do you guarantee the database connection is released even if the consumer throws an error halfway through?"

## Diagram

```
  for await (const batch of pgCursor(query))
       │
       │  consumer writes batch to S3 stream
       │
  <generator resumes at await client.query('FETCH ...')>
       │
       │  network call to Postgres happens HERE
       │
  yield rows  (batch of 1000)
       │
  ...repeats...
       │
  Consumer exits loop (done, break, OR throw)
       │
       v
  generator's finally block runs
  client.release() called — connection returned to pool
  ALWAYS — regardless of how the loop ended
```

## Model Answer (15 YOE)

```js
async function* pgCursor(query, batchSize = 1000) {
  const client = await pool.connect();
  try {
    await client.query('BEGIN');
    await client.query(`DECLARE cur CURSOR FOR ${query}`);

    while (true) {
      const { rows } = await client.query(`FETCH ${batchSize} FROM cur`);
      if (rows.length === 0) break;
      yield rows;
    }

    await client.query('COMMIT');
  } finally {
    client.release(); // always releases — even if consumer throws mid-iteration
  }
}

async function exportToS3(s3Key) {
  const s3Stream = createS3WriteStream(s3Key);

  for await (const batch of pgCursor('SELECT * FROM events ORDER BY created_at')) {
    for (const row of batch) {
      s3Stream.write(JSON.stringify(row) + '\n');
    }
  }

  s3Stream.end();
}
```

The critical guarantee: the `finally` block in the generator runs when the consumer exits the `for await...of` loop — whether naturally (`done: true`), by `break`, or by an unhandled exception thrown inside the loop. This makes generators the correct tool for resource management in streaming scenarios.

This is something plain async functions cannot provide: an async function that yields control mid-execution has no mechanism for the caller to inject a "cleanup now" signal. Generators do: `generator.return()` triggers the `finally` block.

Memory profile: at most `batchSize` rows in memory at any time — 1,000 rows, not 10,000,000.

## Follow-up

**Q:** "What if the S3 write fails on row 5,000,000? Does the DB connection leak?"

**A:** No. When `s3Stream.write()` throws, the exception propagates out of the `for await...of` loop body. The loop exits with an error, which internally calls `generator.return()` on the async generator. The `finally` block runs, `client.release()` is called, the connection is returned to the pool. The connection never leaks.

**Q:** "Why use a DB cursor (`DECLARE CURSOR / FETCH`) instead of `LIMIT / OFFSET` pagination?"

**A:** `LIMIT/OFFSET` with large offsets is O(offset) in Postgres — the DB must scan and discard `offset` rows each time. A cursor holds a server-side iterator position and is O(batchSize) per fetch. For 10M rows, cursor is the only viable approach.
