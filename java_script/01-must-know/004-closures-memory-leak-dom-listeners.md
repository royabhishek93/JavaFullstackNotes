# Memory Leak — Closure Holding a DOM Reference
> **Topic:** Closures | **Level:** Intermediate | **Frequency:** Medium

## The Setup
You are architecting the frontend for Flipkart's product listing page, which is a long-lived single-page application. Performance monitoring shows heap size climbing steadily over a user session. An engineer suspects event listeners attached to product cards are leaking. Each card registers a `mouseover` handler that closes over the full product object including a 2MB image blob.

## The Question
Explain the memory leak mechanism and what architectural pattern prevents it.

## Diagram
```
  Product Card Renders (1000 items)
  ┌────────────────────────────────────────────────┐
  │  for each product:                             │
  │    card.addEventListener('mouseover',          │
  │      function handler() {                      │
  │        preview(product); // closes over        │
  │      }                   // full product obj   │
  │    )                                           │
  └────────────────────────────────────────────────┘

  GC CANNOT COLLECT:
  ┌──────────┐    holds    ┌───────────────┐
  │ DOM node │────────────▶│ handler fn    │
  └──────────┘             └───────┬───────┘
                                   │ closure
                                   ▼
                           ┌───────────────┐
                           │ product obj   │ ← 2MB blob STUCK
                           │ (2MB image)   │   as long as DOM
                           └───────────────┘   node is reachable

  FIX: Store only the ID in closure, fetch lazily
  handler closes over productId (string) → not the full object
```

## Model Answer (15 YOE)
The leak has two compounding factors. First, the event listener holds a reference to the handler function. Second, the handler function's closure holds a reference to the full product object, including the image blob. The DOM node → listener → closure → large object chain is fully reachable as long as the card is in the DOM. The GC correctly keeps all of it alive.

On a listing page where users scroll through hundreds of products, you are holding hundreds of 2MB blobs in memory simultaneously. If users navigate away without a full page reload — standard in an SPA — and the component unmounts without removing listeners, those DOM nodes become detached but still held in memory by the listeners. Now you have a genuine detached-DOM leak.

Two architectural fixes I apply in production: First, close over only the minimum data — a product ID or a small config object, never the full entity. Fetch the full product on hover if needed. Second, use event delegation — attach a single listener to the container, read `event.target.dataset.productId` at event time, and look up the product then. This means zero listeners on individual cards, zero closures holding product objects, and trivially correct cleanup on unmount.

At Flipkart's scale with virtualized lists, closures holding references also prevent the virtualizer from discarding off-screen node data. Event delegation is not optional — it is a correctness requirement.

```js
// BAD — closes over full product object (2MB blob included)
products.forEach(product => {
  card.addEventListener('mouseover', () => preview(product));
});

// GOOD FIX 1 — close over only the ID, fetch lazily
products.forEach(product => {
  card.dataset.productId = product.id;
  card.addEventListener('mouseover', () => {
    const p = productCache.get(product.id);
    preview(p);
  });
});

// GOOD FIX 2 — event delegation, zero per-card closures
container.addEventListener('mouseover', (event) => {
  const id = event.target.closest('[data-product-id]')?.dataset.productId;
  if (id) preview(productCache.get(id));
});
```

## Follow-up
**Q:** How do you detect a closure-induced memory leak in production?

**A:** Chrome DevTools heap snapshot is the primary tool. Take a baseline snapshot, perform the suspected leaking action repeatedly, take another snapshot, then compare — filter for "Detached DOM tree" nodes. If you see detached nodes with retaining paths through closure environments, that confirms it. In Node.js, `--expose-gc` plus periodic `global.gc()` and heap diff via `v8.getHeapStatistics()` is the equivalent.
