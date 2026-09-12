# What Does try/catch Wrap With Multiple awaits?
> **Topic:** Promises | **Level:** Senior Trap | **Frequency:** Medium

## The Setup

You are reviewing a service function that performs three sequential async operations, each with different failure semantics. The function uses a single `try/catch` around all three `await` calls.

## The Question

What does one `try/catch` wrap when it contains multiple `await` calls? What are the trade-offs, and when do you need individual `try/catch` blocks?

## Diagram

```
  async function loadData() {
    try {
      const a = await fetchA();   // if this rejects → jump to catch, b and c never run
      const b = await fetchB();   // if this rejects → jump to catch, c never runs
      const c = await fetchC();   // if this rejects → jump to catch
    } catch (err) {
      // catches error from whichever await rejected first
      // you cannot tell which step failed without inspecting err
    }
  }

  Error propagation:
    fetchA rejects ──→ catch(err)     err = fetchA's rejection reason
    fetchB rejects ──→ catch(err)     err = fetchB's rejection reason
    fetchC rejects ──→ catch(err)     err = fetchC's rejection reason
    None rejects   ──→ catch never runs
```

## Model Answer (15 YOE)

One `try/catch` around multiple `await` calls catches the rejection from whichever `await` rejects first — then skips all subsequent `await` calls and jumps directly to the `catch` block.

```js
async function loadData() {
  try {
    const a = await fetchA();   // if this throws, b and c never run
    const b = await fetchB();   // if this throws, c never runs
    const c = await fetchC();
  } catch (err) {
    // catches error from whichever await rejected first
    // you cannot tell which one failed without inspecting err
  }
}
```

This is correct for "fail fast" flows — if any step fails, the whole operation should fail. The trade-off is granularity: you cannot tell which step failed without inspecting the error object itself.

For flows where each step has different error handling, wrap each `await` individually:

```js
async function loadData() {
  let user;
  try {
    user = await fetchUser();
  } catch (err) {
    // specific handling: show login prompt
    redirectToLogin();
    return;
  }

  let orders;
  try {
    orders = await fetchOrders(user.id);
  } catch (err) {
    // specific handling: orders are optional, continue with empty list
    orders = [];
  }

  return { user, orders };
}
```

A middle-ground pattern for identifying which step failed:

```js
const user   = await fetchUser().catch(err => { throw new Error(`fetchUser failed: ${err.message}`); });
const orders = await fetchOrders(user.id).catch(err => { throw new Error(`fetchOrders failed: ${err.message}`); });
```

## Follow-up

**Q:** If `fetchA` and `fetchC` succeed but `fetchB` rejects, do `fetchA`'s results get lost?

**A:** Yes — in the single `try/catch` pattern, `fetchA`'s result is already in the local variable `a`, but once the `catch` block runs you are out of the try scope. If you need the successful results even on partial failure, use `Promise.allSettled` for parallel operations, or individually-wrapped `await` calls for sequential ones.

## Why It's a Trap

Candidates often assume that a single `try/catch` around multiple `await` calls somehow tracks which step failed or handles each step independently. It does not. It is identical to wrapping a chain of synchronous calls in one `try/catch` — the first throw wins, and everything after it is skipped.

## What NOT to Say

- "The `catch` block knows which `await` threw." — It does not, unless the error object itself carries identifying information.
- "You should always use one `try/catch` per function for cleanliness." — Cleanliness matters, but if each step has different recovery logic, separate `try/catch` blocks are the correct tool.
- "The other `await` calls still run after one rejects." — They do not. Execution jumps immediately to the `catch` block.
