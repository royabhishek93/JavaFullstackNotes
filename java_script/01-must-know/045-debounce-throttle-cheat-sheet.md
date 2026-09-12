# Debounce & Throttle — Cheat Sheet
> **Topic:** Debounce & Throttle | **Level:** Reference | **Frequency:** High

```
DEBOUNCE
────────
What:    Fire AFTER a gap of silence. Every new event resets the timer.
When:    Search input, auto-save, resize handler, form validation
Pattern: "Wait until things settle"

function debounce(fn, delay) {
  let timerId;
  const debounced = function(...args) {
    clearTimeout(timerId);
    timerId = setTimeout(() => fn.apply(this, args), delay);
  };
  debounced.cancel = () => clearTimeout(timerId);
  return debounced;
}

React safe pattern:
  const fn = useRef(debounce(apiCall, 300)).current;
  useEffect(() => () => fn.cancel(), [fn]);


THROTTLE
────────
What:    Fire AT MOST ONCE per window. Timer ignores new calls.
When:    Scroll, mousemove, button click guard, analytics, game input
Pattern: "Slow down the rate"

function throttle(fn, limit) {
  let lastCall = 0;
  return function(...args) {
    const now = Date.now();
    if (now - lastCall >= limit) {
      lastCall = now;
      fn.apply(this, args);
    }
  };
}


KEY DIFFERENCES
───────────────
                 Debounce              Throttle
Timer resets     On every call         Never (expires on own schedule)
When fires       After gap of silence  During activity, at fixed rate
Misses           All intermediate      All within-window calls
Guarantees       One call post-burst   At most one per interval
Mental model     "Wait for done"       "Allow maximum N per second"


SENIOR TRAPS
────────────
1. Component unmount: pending setTimeout still holds closure → call .cancel() in useEffect cleanup
2. Debounce inside render body: new closure per render breaks the timer → use useRef
3. Throttle drops last event: use Lodash throttle (has trailing call by default)
4. Leading edge: debounce(fn, n, { leading: true, trailing: false }) fires first, locks rest
5. maxWait: debounce(fn, 300, { maxWait: 1000 }) forces flush after 1s even if still typing


LODASH (production default)
────────────────────────────
import { debounce, throttle } from 'lodash';

debounce(fn, 300)                               // trailing edge (default)
debounce(fn, 300, { leading: true })            // leading edge
debounce(fn, 300, { maxWait: 1000 })            // forced flush
throttle(fn, 200)                               // leading + trailing (default)
throttle(fn, 200, { leading: true, trailing: false }) // leading only


REAL-WORLD MAPPING
──────────────────
  Swiggy search box             → debounce(searchAPI, 300)
  Flipkart Add to Cart          → throttle(addToCart, 2000)
  Scroll progress indicator     → throttle(updateBar, 100)
  Window resize layout recalc   → debounce(recalculate, 250)
  Auto-save document            → debounce(save, 1000, { maxWait: 5000 })
  Username availability check   → debounce(checkUsername, 500)
  Payment button guard          → debounce(submit, 3000, { leading: true, trailing: false })
  Real-time GPS position update → throttle(updateMap, 200)
```
