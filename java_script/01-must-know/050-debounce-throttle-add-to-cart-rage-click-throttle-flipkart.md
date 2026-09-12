# Add-to-Cart Rage Click with Throttle — Flipkart Scenario
> **Topic:** Debounce & Throttle | **Level:** Intermediate | **Frequency:** High

## The Setup
Flipkart Big Billion Days flash sale. The page feels slow under load. Users rage-click "Add to Cart" — 8 clicks in 1.5 seconds. Each click fires a POST to `/api/cart`. The cart service is not idempotent at the network layer; it processes all 8 requests and the user ends up with 8 units of the same item. Customer support tickets spike.

## The Question
You need to protect the "Add to Cart" button from rapid duplicate clicks. Walk through your choice of debounce vs throttle, explain why, and implement a solution in React.

## Diagram

```
Timeline (user rage-clicks "Add to Cart"):
click  click  click  click  click  click  click  click
t=0    t=200  t=400  t=600  t=800  t=1000 t=1500 t=2100
 ↑      ✗      ✗      ✗      ✗      ✗      ✗      ↑
fires                                              fires (2s window expired)

WITHOUT throttle: 8 POST requests → 8 cart items added
WITH throttle(2000): 2 POST requests → 1 item added (expected) + 1 at t=2100
```

## Model Answer (15 YOE)

**Why throttle, not debounce:**

Debounce would wait for the user to *stop* clicking — which could be 2-3 seconds, creating a sluggish UX where the user wonders if the click registered at all. Throttle fires the first click immediately (instant feedback) and silently blocks duplicates for the next 2 seconds.

```ts
function throttle<T extends (...args: any[]) => void>(fn: T, limit: number): T {
  let lastCall = 0;

  return function (this: unknown, ...args: Parameters<T>) {
    const now = Date.now();
    if (now - lastCall >= limit) {
      lastCall = now;
      fn.apply(this, args);
    }
    // Calls within the window are silently dropped — no timer reset
  } as T;
}

// ProductCard.tsx
const throttledAddToCart = useMemo(
  () => throttle((productId: string) => {
    dispatch(addToCartAction(productId));
    analytics.track('add_to_cart', { productId });
  }, 2000),
  []
);

function ProductCard({ product }: { product: Product }) {
  return (
    <button onClick={() => throttledAddToCart(product.id)}>
      Add to Cart
    </button>
  );
}
```

**`useMemo` with empty deps** is appropriate here because the throttled function has no dependencies — it closes over `dispatch` and `analytics` which are stable references. `useRef` also works.

**The UX complement:** Disable the button visually for the throttle window to communicate that the click was registered:

```ts
const [isThrottled, setIsThrottled] = useState(false);

const handleClick = () => {
  if (isThrottled) return;
  setIsThrottled(true);
  dispatch(addToCartAction(product.id));
  setTimeout(() => setIsThrottled(false), 2000);
};
```

**Defence in depth:** Throttle on the client prevents the UX problem. The server-side cart endpoint should also be idempotent (keyed on `userId + productId + requestId`) to guard against network retries and multiple tabs.

## Follow-up

**Q:** A PM says the 2-second lock feels too long for power users. How would you tune it?
**A:** 2 seconds is conservative. 500ms to 1s is usually sufficient for click deduplication — it covers double-clicks and impatient triple-clicks but does not feel like a lock. A/B test with `analytics.track` to measure false positive rate (real users clicking twice to add 2 items vs rage-clicks adding 1).

**Q:** What if the user legitimately wants to add 2 units of the same item quickly?
**A:** Throttle the button but add a quantity selector input. The quantity input is not throttled — it is a deliberate user action with a discrete value. The "Add to Cart" button throttle targets click spam, not intentional quantity changes.
