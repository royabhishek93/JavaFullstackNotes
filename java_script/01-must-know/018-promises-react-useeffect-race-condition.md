# React useEffect Race Condition and AbortController
> **Topic:** Promises | **Level:** Intermediate | **Frequency:** Medium

## The Setup

Your React app has an order details page. Users navigate quickly between orders. Sometimes the wrong order's data appears. A junior files a bug saying "the API is returning wrong data."

## The Question

The API is fine. What is happening in this code, and how do you fix it?

```js
function OrderDetail({ orderId }) {
  const [order, setOrder] = useState(null);

  useEffect(() => {
    fetch(`/api/orders/${orderId}`)
      .then(res => res.json())
      .then(data => setOrder(data));   // <-- problem here
  }, [orderId]);
}
```

## Diagram

```
  User navigates:  Order 1 -> Order 2 -> Order 3

  Request 1 (order 1) starts at t=0ms
  Request 2 (order 2) starts at t=50ms    (fast navigation)
  Request 3 (order 3) starts at t=100ms

  Response 3 arrives at t=200ms  -> setOrder(order3) ✓
  Response 1 arrives at t=350ms  -> setOrder(order1) ✗  WRONG DATA SHOWN
  Response 2 arrives at t=400ms  -> setOrder(order2) ✗  WRONG DATA SHOWN

  Responses arrive out of order. Whichever resolves last wins.
```

## Model Answer (15 YOE)

This is the classic async race condition in React. Each re-render with a new `orderId` fires a fetch. When responses arrive out of order, the last `setOrder` call wins — which may be for an old `orderId`. The component displays stale data from a previous navigation.

The fix uses the cleanup function returned from `useEffect` to set a cancellation flag and abort the in-flight request:

```js
useEffect(() => {
  let cancelled = false;
  const controller = new AbortController();

  fetch(`/api/orders/${orderId}`, { signal: controller.signal })
    .then(res => res.json())
    .then(data => {
      if (!cancelled) setOrder(data);
    })
    .catch(err => {
      if (err.name !== 'AbortError') console.error(err);
    });

  return () => {
    cancelled = true;
    controller.abort();   // cancels the in-flight request at the network level
  };
}, [orderId]);
```

When `orderId` changes, React runs the cleanup for the previous effect before starting the new one. `controller.abort()` cancels the in-flight fetch (if the browser supports it). The `cancelled` flag guards against the case where the response was already received but `setOrder` has not yet been called — the flag ensures the stale data is silently discarded.

In a production React codebase, data-fetching libraries like React Query or SWR handle this cancellation automatically. But understanding the underlying mechanism — cleanup functions, `AbortController`, and why stale closures cause wrong data — is what separates a senior from a junior.

## Follow-up

**Q:** How does React Query solve this?

**A:** React Query tracks query keys and deduplicates in-flight requests. When a key changes, it automatically cancels stale requests (using `AbortController` internally), manages loading/error states, and handles background refetching, caching, and stale-while-revalidate. You are essentially getting the cleanup pattern above for free, plus caching, retry, and devtools.
