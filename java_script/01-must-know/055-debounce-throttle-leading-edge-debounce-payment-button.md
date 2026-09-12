# Leading-Edge Debounce — Instant First Click on Payment Button
> **Topic:** Debounce & Throttle | **Level:** Intermediate | **Frequency:** Medium

## The Setup
A payment confirmation button must feel instant — the user clicks "Pay ₹4,999" and expects immediate visual feedback. But the form must not submit twice if the user double-clicks or clicks again while the network call is in flight. Standard trailing-edge debounce waits 3 seconds before firing, which makes the button feel broken.

## The Question
Explain the difference between trailing-edge and leading-edge debounce. When would you use leading-edge? Implement a leading-edge debounce from scratch.

## Diagram

```
TRAILING (default):
  Clicks:  E   E   E   E   E         [3s silence]
                                           ↑
                                       fires HERE
  User sees nothing for 3+ seconds → feels broken for payment UX

LEADING (what we want):
  Clicks:  E   E   E   E   E         [3s silence]
           ↑
       fires HERE (immediately)
       remaining clicks ignored for 3s
  User sees instant feedback → UX feels correct
```

## Model Answer (15 YOE)

**Trailing vs Leading:**

- **Trailing** (default): Fire after the burst ends. The function fires at the *end* of the silence gap. Best for search and auto-save where you want the final settled value.
- **Leading**: Fire on the *first* call, then ignore subsequent calls for the delay window. Best for "do this once and lock it" — payments, form submissions, one-time API mutations.

**From-scratch implementation:**

```ts
function debounceLeading<T extends (...args: any[]) => void>(fn: T, delay: number): T {
  let timerId: ReturnType<typeof setTimeout> | undefined;

  return function (this: unknown, ...args: Parameters<T>) {
    const isFirstCall = timerId === undefined; // no pending timer = window is open
    clearTimeout(timerId);
    timerId = setTimeout(() => {
      timerId = undefined; // reset: window is open again
    }, delay);

    if (isFirstCall) {
      fn.apply(this, args); // fire immediately on the FIRST call only
    }
    // subsequent calls within delay are ignored
  } as T;
}
```

**Lodash equivalent (preferred in production):**

```ts
import { debounce } from 'lodash';

const handlePayment = debounce(
  submitPaymentAPI,
  3000,
  { leading: true, trailing: false }
  //              ↑ do not fire again at the end of the window
);
```

`trailing: false` is critical — without it, Lodash fires once at the leading edge AND once at the trailing edge, causing a double submission.

**React integration:**

```tsx
function PaymentButton({ amount }: { amount: number }) {
  const handleClick = useRef(
    debounce(
      () => submitPaymentAPI(amount),
      3000,
      { leading: true, trailing: false }
    )
  ).current;

  useEffect(() => () => handleClick.cancel(), [handleClick]);

  return (
    <button onClick={handleClick}>
      Pay ₹{amount}
    </button>
  );
}
```

## Follow-up

**Q:** How is leading-edge debounce different from throttle?
**A:** Both fire on the first call and block subsequent calls. The difference is what happens after the window expires: throttle fires the next qualifying event immediately (it is always open after the interval); leading-edge debounce requires a silence gap equal to the delay before it "resets." In practice they behave identically for single clicks separated by more than the window, but differently in rapid bursts followed by a slow second attempt. For a payment button the distinction rarely matters — either works.

**Q:** Should the button also be visually disabled during the 3-second lock?
**A:** Yes, always. Rate-limiting in JS is silent — the user has no way to know their click was received. Disable the button and show a spinner or "Processing..." label for the duration of the lock. This communicates state to the user and reduces the urge to click again. The JS throttle/debounce is the hard guard; the visual disabled state is the UX complement.
