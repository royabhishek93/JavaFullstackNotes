# Async IIFE — Top-Level Initialization in a Node.js Script
> **Topic:** IIFE | **Level:** Fundamental | **Frequency:** High

## The Setup

You are writing a one-off data migration script for a Node.js service. The script needs to connect to a database, fetch records in batches, transform them, and write results to a new collection — all sequentially. The environment is Node.js 14, which does not support top-level `await` in CommonJS modules.

## The Question

How do you write sequential async code at the top level of a Node.js script without wrapping everything in a named function and then calling it, and why is that pattern still relevant even in Node.js 18+?

## Diagram

```
┌──────────────────────────────────────────────────────────────┐
│              ASYNC IIFE EXECUTION FLOW                       │
│                                                              │
│  Without IIFE (Node 14 CommonJS):                            │
│  ┌─────────────────────────────────────────────────────┐     │
│  │  const data = await db.find(...);  // SyntaxError   │     │
│  │  // await is not allowed here                       │     │
│  └─────────────────────────────────────────────────────┘     │
│                                                              │
│  Named function workaround (verbose):                        │
│  ┌─────────────────────────────────────────────────────┐     │
│  │  async function migrate() {                         │     │
│  │    const data = await db.find(...);                 │     │
│  │    // ...                                           │     │
│  │  }                                                  │     │
│  │  migrate(); // ← easy to forget; no error if missed │     │
│  └─────────────────────────────────────────────────────┘     │
│                                                              │
│  Async IIFE (self-contained):                                │
│  ┌─────────────────────────────────────────────────────┐     │
│  │  (async () => {                                     │     │
│  │    const conn = await db.connect();                 │     │
│  │    const records = await conn.find({});             │     │
│  │    await processInBatches(records);                 │     │
│  │    await conn.close();                              │     │
│  │  })();   ← cannot forget to call it                │     │
│  └─────────────────────────────────────────────────────┘     │
│                                                              │
│  Error handling — always attach:                             │
│  (async () => { ... })().catch(err => {                      │
│    console.error('Migration failed:', err);                  │
│    process.exit(1);                                          │
│  });                                                         │
└──────────────────────────────────────────────────────────────┘
```

## Model Answer (15 YOE)

The async IIFE solves the top-level `await` problem by wrapping initialization code in an immediately-invoked async function. You write `(async () => { ... })()` and everything inside behaves as though it were at the top level, with full `await` support.

The advantage over a named function is self-containment: there is no possibility of defining the function and forgetting to call it. In a migration script that runs in CI or a cron job, that class of bug — function defined but never invoked — is silent and costly. The IIFE pattern is structurally impossible to forget.

Even in Node.js 18 with native top-level `await` in ES modules, the async IIFE remains relevant in three situations. First, in CommonJS files — the `.cjs` extension or a `package.json` without `"type": "module"` — top-level `await` is still not available. Many enterprise Node.js codebases are still CommonJS. Second, in inline scripts in CI pipelines or Lambda handlers where you cannot control the module format. Third, when you want explicit control over the entry point's error boundary: the `.catch()` appended to the IIFE invocation is a clean pattern for process exit handling that is harder to express cleanly with module-level top-level `await`.

One thing I always add is the `.catch()` handler. An unhandled rejection in a migration script can exit with code 0 in some Node.js versions, which means CI thinks the job succeeded. `(async () => { ... })().catch(err => { console.error(err); process.exit(1); })` makes failure explicit and auditable.

## Follow-up

**Q:** How would you handle cleanup (like closing a database connection) if the async IIFE throws halfway through?

**A:** With a `try/finally` block inside the IIFE. Put `conn = await db.connect()` before the try, and `await conn.close()` in the finally block. The finally runs whether the body throws or completes normally. Alternatively, in Node.js codebases using `pg` or `mongoose`, register a `process.on('exit')` handler outside the IIFE for cleanup as a safety net. The two patterns are complementary — finally handles expected error paths, the process exit handler catches anything that slips through.
