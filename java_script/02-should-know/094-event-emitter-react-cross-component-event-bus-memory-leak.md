# React Cross-Component Event Bus and Memory Leak
> **Topic:** Event Emitter | **Level:** Intermediate | **Frequency:** High

## The Setup
A React app has a `CartIcon` component in the header (shows the item count badge) and a `ProductGrid` deep in the component tree. When the user adds an item, the cart count must update. Lifting state requires threading props through 6 levels. Context causes the full subtree to re-render on every cart change. The team decides to use a module-level EventEmitter as a lightweight event bus.

## The Question
Implement the cross-component event bus pattern in React. Then explain the memory leak that this pattern is prone to and show the correct fix.

## Diagram

```
Module-level singleton (lives for the app's lifetime):
  eventBus = new EventEmitter()

CartIcon (header, mounted once)        ProductGrid (nested, mounted/unmounted)
  │                                      │
  useEffect → bus.on('cart.updated',     handleAddToCart →
              handler)                   bus.emit('cart.updated', { itemCount })
  │
  cleanup → bus.off('cart.updated', handler)   ← MUST EXIST

LEAK SCENARIO (no cleanup):
  Mount 1: listeners['cart.updated'] = [handler]
  Unmount → cleanup missing → handler stays
  Mount 2: listeners['cart.updated'] = [handler, handler]  ← duplicate!
  emit → setCount called twice → cart badge shows 2x the real count
  After N re-mounts: N copies → N× updates per emit
```

## Model Answer (15 YOE)

```ts
// lib/eventBus.ts — module-level singleton
export const eventBus = new EventEmitter();

// CartIcon.tsx — subscriber
function CartIcon() {
  const [count, setCount] = useState(0);

  useEffect(() => {
    // Named handler — same reference used in both on() and off()
    const handler = ({ itemCount }: { itemCount: number }) => setCount(itemCount);

    eventBus.on('cart.updated', handler);

    // CRITICAL: return cleanup to prevent memory leak on unmount
    return () => eventBus.off('cart.updated', handler);
  }, []); // empty deps: subscribe once on mount, cleanup on unmount

  return <span className="cart-count">{count}</span>;
}

// ProductGrid.tsx — emitter
function ProductGrid() {
  const handleAddToCart = (product: Product) => {
    addToCartAPI(product.id).then(cart => {
      eventBus.emit('cart.updated', { itemCount: cart.totalItems });
    });
  };

  return <ProductList onAdd={handleAddToCart} />;
}
```

**The leak anatomy — why `off()` must receive the same reference:**

`off()` uses `fn !== listener` filter — it compares function references by identity. The `handler` variable defined inside `useEffect` is captured by both the `on` call and the cleanup closure. Because it is a named `const` in the same closure scope, both the `on` call and the `return () => off(handler)` reference the exact same function object. If you define an inline arrow function in the cleanup instead, it creates a new function object with a different identity — `off()` silently fails.

**Why the empty dependency array is correct:**

`[]` means "run this effect once when the component mounts and run cleanup when it unmounts." This is the intended lifecycle for an event subscription. Adding dependencies would re-run the effect (and re-subscribe) whenever those dependencies change, creating duplicate subscriptions.

## Follow-up

**Q:** Why not use React Context for this instead of an event bus?
**A:** Context is the right tool when many components need to *read* the same value reactively. But Context re-renders the entire subtree of its Provider on every value change. For a cart count that changes frequently, this is expensive. The event bus pattern surgically updates only `CartIcon` — no other component re-renders. Event bus is better for "push notifications between unrelated components." Context is better for "shared state that many components display simultaneously."

**Q:** What if `CartIcon` needs to show the count immediately on mount (server-side rendered initial value)?
**A:** Initialize `useState` with the SSR-provided count: `useState(initialCount)`. The event bus handles subsequent updates. The bus does not need to emit on mount — the initial value comes from props or SSR data, and the bus handles live deltas.
