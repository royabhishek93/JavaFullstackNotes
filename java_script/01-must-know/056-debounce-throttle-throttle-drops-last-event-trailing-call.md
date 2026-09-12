# Throttle Drops the Last Event in a Burst
> **Topic:** Debounce & Throttle | **Level:** Senior Trap | **Frequency:** Medium

## The Setup
A candidate implements a correct timestamp-comparison throttle and applies it to a search box (wrong choice, but set that aside). They notice that the user's final query character is sometimes never sent — the search fires mid-word and then stops. They ask why.

## The Question
Basic throttle silently drops all events within the window, including the last one. When does that matter? What is the fix?

## Diagram

```
BASIC THROTTLE (fires first, drops the rest):
User types "b-i-r-y-a-n-i" — 7 keystrokes over 600ms, throttle limit=500ms

  b    i    r    y    a    n    i
  ↑    ✗    ✗    ✗    ✗    ✗    ✗
fires  |←────── all dropped ──────→|

Query sent: "b"  ← incomplete, wrong result shown

THROTTLE WITH TRAILING CALL:
  b    i    r    y    a    n    i
  ↑                              scheduled
fires                            at t=500ms
                                 ↑
                              fires "biryani" — correct
```

## Model Answer (15 YOE)

**When dropped trailing events matter:**

For a scroll progress bar, dropping events is fine — the bar shows a slightly stale position, corrects on the next tick, nobody notices. For any handler where the *final* value in a burst is semantically important (search queries, form field validation, position reporting), the last dropped event is a correctness bug.

**The fix — trailing call throttle:**

```ts
function throttleWithTrailing<T extends (...args: any[]) => void>(fn: T, limit: number): T {
  let lastCall = 0;
  let trailingTimer: ReturnType<typeof setTimeout> | undefined;

  return function (this: unknown, ...args: Parameters<T>) {
    const now = Date.now();
    const remaining = limit - (now - lastCall);

    clearTimeout(trailingTimer);

    if (remaining <= 0) {
      // Window has expired — fire immediately
      lastCall = now;
      fn.apply(this, args);
    } else {
      // Still within window — schedule the last call for when window expires
      trailingTimer = setTimeout(() => {
        lastCall = Date.now();
        fn.apply(this, args);
      }, remaining);
    }
  } as T;
}
```

**How it works:** Every call within the window clears the previous trailing timer and schedules a new one for `remaining` ms from now. Only the *last* call's arguments are captured in the closure — earlier ones are overwritten. When the window expires, the trailing timer fires with the most recent arguments.

**Lodash `throttle` does this by default:**

```ts
import { throttle } from 'lodash';

// Default: leading=true, trailing=true
// Fires immediately AND fires again at the end of the window with the last args
const throttled = throttle(fn, 500);

// Leading only (drops trailing — basic throttle behaviour):
const throttledLeadingOnly = throttle(fn, 500, { trailing: false });
```

**Choosing the right variant:**

| Use case | Correct variant |
|---|---|
| Scroll progress bar | leading only (`trailing: false`) — stale values acceptable |
| Button click guard | leading only — extra trailing call would re-fire the action |
| Search box (if throttled, not debounced) | trailing=true — final query must be sent |
| Window resize layout | trailing=true — final dimensions must trigger recalc |

## Why It's a Trap

Candidates who implement basic throttle (timestamp comparison, no trailing timer) believe they have solved the problem. They have not — they have created a version that silently drops the most important event in any burst. This goes unnoticed in demos with slow, deliberate input. It surfaces in real users' hands.

The trap deepens because Lodash throttle (the production standard) has trailing calls enabled by default. A candidate who has only used Lodash never hits this bug. A candidate who rolls their own does, if they do not know to add the trailing timer.

## What NOT to Say

- "Throttle always drops some events and that's expected." — True for intermediate events; the *final* event has special importance in many use cases.
- "I would just use debounce instead." — A correct answer for search boxes, but misses the point: the question is about throttle specifically and what its correct production form looks like.

## Follow-up

**Q:** If both leading and trailing are enabled, can the function fire twice for a single click?
**A:** Yes — one on the leading edge and one on the trailing edge after the window. For a button click guard this is wrong: it fires the action immediately and then fires it again after the limit expires. Always set `{ trailing: false }` for click guards. Trailing is useful when you need the *last* value in a burst (resize, search), not when you are guarding against duplicate actions.
