# Implement Debounce from Scratch
> **Topic:** Debounce & Throttle | **Level:** Fundamental | **Frequency:** High

## The Setup
Classic whiteboard/coding-round question. The interviewer wants to verify you understand the internals, not just the use cases. Asked at Google, Meta, Flipkart, Swiggy, and virtually every senior front-end role.

## The Question
Implement a `debounce(fn, delay)` function from scratch in JavaScript. The returned function should:
1. Delay execution of `fn` by `delay` ms after the last call
2. Reset the timer on every new call
3. Preserve the `this` context and all arguments
4. Expose a `.cancel()` method to abort the pending call

## Diagram

```
Calls arriving:   call   call   call         call
                   ↓      ↓      ↓             ↓
Timer:          [---300ms]
                       [---300ms]
                              [---300ms]                 FIRES ↑
                                            [---300ms]        FIRES ↑

Each new call clears the previous timer and starts a fresh one.
Only the last call in a burst actually executes fn.
```

## Model Answer (15 YOE)

```ts
function debounce<T extends (...args: any[]) => void>(fn: T, delay: number) {
  let timerId: ReturnType<typeof setTimeout>;

  const debounced = function (this: unknown, ...args: Parameters<T>) {
    clearTimeout(timerId);                            // cancel any pending call
    timerId = setTimeout(() => fn.apply(this, args), delay); // schedule new call
  };

  debounced.cancel = () => clearTimeout(timerId);    // expose manual cancellation

  return debounced;
}
```

**Why each line matters:**

- `clearTimeout(timerId)` — this is the core of debounce. Every call cancels the previous scheduled execution before scheduling a new one. Without this, you just have a delayed function, not a debounced one.
- `fn.apply(this, args)` — preserves the calling context (`this`) and all arguments. Using `fn(...args)` would lose `this` if the debounced function is called as a method.
- `debounced.cancel` — without this, a React component that unmounts while a call is pending has no way to prevent the stale `setTimeout` from firing after unmount.
- TypeScript generics — `Parameters<T>` ensures the returned function has the same signature as `fn`, giving callers full type safety.

**Usage:**

```ts
const debouncedSearch = debounce((query: string) => {
  fetch(`/api/search?q=${query}`);
}, 300);

input.addEventListener('input', (e) => debouncedSearch(e.target.value));

// On cleanup:
debouncedSearch.cancel();
```

## Follow-up

**Q:** Why use `fn.apply(this, args)` inside `setTimeout` instead of just calling `fn(...args)`?
**A:** Arrow functions passed to `setTimeout` capture `this` from the enclosing scope (the `debounced` function's `this`). Using `fn.apply(this, args)` explicitly forwards that context to `fn`. If `debounced` is called as a method on an object, `this` inside `fn` will correctly refer to that object. Using `fn(...args)` loses `this` in strict mode — it becomes `undefined`.

**Q:** How would you add a `maxWait` option so the function is forced to fire after a maximum delay even if events keep coming?
**A:** Track a `lastInvokeTime`. On each call, check if `Date.now() - lastInvokeTime >= maxWait`. If yes, execute immediately and reset `lastInvokeTime`. This is what Lodash's `debounce` with `{ maxWait }` does — it turns debounce into a hybrid that behaves like throttle at the maxWait boundary. Useful for auto-save: debounce fires after 1s of silence but is guaranteed to fire after 5s even if the user never stops typing.
