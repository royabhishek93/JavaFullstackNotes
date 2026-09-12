# Load More Button with Session-Scoped Generator — Swiggy Order History
> **Topic:** Generator Functions | **Level:** Intermediate | **Frequency:** Medium

## The Setup

The "Load More" button on a Swiggy restaurant's order history page fetches the next batch only when clicked. The naive implementation stores `currentPage` in component state, which leaks pagination logic into the UI layer and requires a reset handler. A generator encapsulates all pagination state and exposes a single `.next()` method.

## The Question

"The 'Load More' button should fetch the next batch only when clicked. Each click should resume from where the last one left off. How do you model this without managing page numbers in component state?"

## Diagram

```
Session lifecycle:
  Component mounts
       │
       v
  orderPaginator = fetchOrderHistory('rest-42')  ← one generator per session
       │
  [click #1] → orderPaginator.next() → fetches page 0 → yields 20 orders
  [click #2] → orderPaginator.next() → fetches page 1 → yields 20 orders
  [click #3] → orderPaginator.next() → { done: true } → disables button
       │
  Component unmounts → generator discarded (GC)
  Component remounts → new generator created → starts from page 0
```

## Model Answer (15 YOE)

```js
async function* fetchOrderHistory(restaurantId, pageSize = 20) {
  let page = 0;
  while (true) {
    const { orders, hasMore } = await api.getOrders(restaurantId, page, pageSize);
    if (!hasMore && orders.length === 0) return;
    yield orders;
    if (!hasMore) return;
    page++;
  }
}

// Component initialisation — generator created ONCE per session
const orderPaginator = fetchOrderHistory('rest-42', 20);

loadMoreBtn.addEventListener('click', async () => {
  loadMoreBtn.disabled = true;

  const { value: orders, done } = await orderPaginator.next();

  if (done) {
    loadMoreBtn.textContent = 'No more orders';
    return;
  }

  renderOrders(orders);
  loadMoreBtn.disabled = false;
});
```

What the component does NOT need:
- No `currentPage` in useState/Redux
- No `hasMore` boolean to track manually
- No reset logic when the component unmounts and remounts — create a new generator

The generator IS the cursor. It remembers where it is. The UI just calls `.next()`.

In a React context, the generator would live in a `useRef` (so it persists across renders without triggering re-renders) or be created once on component mount inside a `useEffect`. On unmount, the cleanup function calls `orderPaginator.return()` to run any `finally` blocks.

## Follow-up

**Q:** "How do you handle the case where the user scrolls back to the top and wants to restart from page 0?"

**A:** Call the generator function again: `orderPaginator = fetchOrderHistory('rest-42', 20)`. A completed or mid-flight generator cannot be rewound. A new generator object starts fresh. Store it in a ref and replace it on reset.

**Q:** "What happens if the user clicks 'Load More' twice before the first request resolves?"

**A:** The second `.next()` call is made on an already-awaiting generator. In an async generator, calling `.next()` while the previous `.next()` has not resolved queues the second call. This is safe but can lead to out-of-order rendering. Disable the button until the first call resolves (as shown above) to prevent this.
