# Auto-Save with Debounce and maxWait — Google Docs Scenario
> **Topic:** Debounce & Throttle | **Level:** Intermediate | **Frequency:** Medium

## The Setup
You are designing the auto-save feature for a collaborative document editor (Google Docs, Notion, or any rich-text editor). The requirement: save on every keystroke to avoid data loss, but debounce saves so a fast typist does not hammer the server. However, product requires a hard guarantee: data must be saved at least every 5 seconds even if the user never stops typing.

## The Question
Pure debounce with a 1-second delay could postpone saving indefinitely for a fast typist. How do you implement auto-save that is debounced but also guarantees a save at least every 5 seconds?

## Diagram

```
PURE DEBOUNCE (1s delay) — FAILS for continuous typing:
typing: |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
        ← never a 1s gap → never fires → DATA LOSS RISK

DEBOUNCE + maxWait=5s — CORRECT:
typing: ||||||| ||||||| ||||||||||||||||||||||||||||||||||||||||||||||||
        [1s gap]        [no gap, but 5s elapsed since last save]
                ↑                                                ↑
             fires (1s silence)                    forced flush at 5s mark
```

## Model Answer (15 YOE)

`maxWait` is the difference between debounce and a leaky-bucket rate limiter. With `maxWait`, debounce says: "Wait for 1 second of silence, but no matter what, fire at least once every 5 seconds." Lodash's `debounce` supports `maxWait` natively.

```ts
import { debounce } from 'lodash';

const autoSave = debounce(
  async (content: string) => {
    await fetch('/api/doc/save', {
      method: 'POST',
      body: JSON.stringify({ content }),
    });
  },
  1000,            // wait 1s after last keystroke
  { maxWait: 5000 } // force save after 5s even if still typing
);

// In the editor's onChange handler:
editor.on('change', (content) => autoSave(content));
```

**How `maxWait` works internally:**

Lodash tracks `lastInvokeTime` — the last time the function actually executed. On each call, it checks two conditions:
1. Has `delay` ms passed since the last call? → trailing-edge debounce fire
2. Has `maxWait` ms passed since `lastInvokeTime`? → forced flush

Whichever condition is met first triggers execution. This is essentially a rate limiter with a burst allowance.

**Conflict resolution in collaborative editing:**

Auto-save creates a version history challenge. If two users are editing simultaneously and saves happen every 1-5 seconds, you need server-side last-write-wins or operational transformation (OT). `maxWait` ensures your save intervals are predictable — useful for planning version snapshot frequency.

**Cleanup on component unmount:**

```ts
useEffect(() => {
  return () => {
    autoSave.flush(); // force a final save before unmount, or use autoSave.cancel()
  };
}, []);
```

Lodash debounce also exposes `.flush()` — immediately execute the pending call and reset. Useful for "force save before navigate away."

## Follow-up

**Q:** What is the difference between `debounce.cancel()` and `debounce.flush()`?
**A:** `cancel()` clears the pending timer without executing the function — the pending call is discarded. `flush()` immediately executes the pending call (if any) and clears the timer. For auto-save, `.flush()` on the `beforeunload` event or route change ensures the user's last keystrokes are not lost. `.cancel()` is for cases where the pending call is no longer relevant, such as component unmount when the document has been explicitly closed.

**Q:** How is `debounce` with `maxWait` different from `throttle`?
**A:** With `throttle`, the function fires at a fixed rate regardless of silence — there is no "wait for settling." With `debounce + maxWait`, the function prefers to fire after silence (better for batch efficiency) but falls back to a rate-limited schedule when silence never arrives. The user experience differs: throttle fires predictably during bursts; debounce+maxWait fires in bursts but with a ceiling on how long it can delay.
