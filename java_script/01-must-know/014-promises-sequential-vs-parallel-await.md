# Sequential vs Parallel await — The Dashboard Slowdown
> **Topic:** Promises | **Level:** Intermediate | **Frequency:** High

## The Setup

A junior engineer on your team refactored the dashboard to use `async/await`. Page load time went from 400 ms to 1.2 s. The network tab shows three sequential requests that used to fire in parallel.

## The Question

The engineer shows you this code and asks what is wrong:

```js
async function loadDashboard(userId) {
  const user     = await fetchUser(userId);
  const orders   = await fetchOrders(userId);
  const notifs   = await fetchNotifications(userId);
  renderDashboard(user, orders, notifs);
}
```

## Diagram

```
Sequential (broken):
  t=0ms  [fetchUser    starts]
  t=120ms              [fetchUser done]  [fetchOrders starts]
  t=280ms                               [fetchOrders done]  [fetchNotifs starts]
  t=400ms                                                   [fetchNotifs done]
  Total: 400ms

Parallel (correct):
  t=0ms  [fetchUser starts] [fetchOrders starts] [fetchNotifs starts]
  t=120ms [all done - slowest wins]
  Total: 120ms
```

## Model Answer (15 YOE)

The three fetches are entirely independent — none of them needs the previous one's result. Writing three sequential `await` calls forces them to run one after another. The JS engine only starts `fetchOrders` after `fetchUser` resolves, which is the opposite of what you want.

The fix is `Promise.all`, which fires all three simultaneously and awaits the slowest:

```js
async function loadDashboard(userId) {
  const [user, orders, notifs] = await Promise.all([
    fetchUser(userId),
    fetchOrders(userId),
    fetchNotifications(userId),
  ]);
  renderDashboard(user, orders, notifs);
}
```

The important distinction: `await promise` suspends the current async function until that one Promise settles. `Promise.all([p1, p2, p3])` creates a single Promise that only suspends once — when all three are done. This is not a micro-optimization. On a page with six independent data sources each taking 200 ms, sequential await costs 1200 ms; `Promise.all` costs 200 ms.

The one trade-off: `Promise.all` short-circuits on the first rejection. If `fetchOrders` fails, you lose the user and notifs data even if those succeeded. For a dashboard where partial data is acceptable, `Promise.allSettled` is safer.

## Follow-up

**Q:** When would you choose `Promise.allSettled` over `Promise.all`?

**A:** When partial success is acceptable — for example, a dashboard widget grid where each widget is independent. `Promise.all` is all-or-nothing; `Promise.allSettled` gives you an array of `{ status: 'fulfilled', value }` or `{ status: 'rejected', reason }` for each input, so you can render the widgets that loaded and show error states for the ones that failed, rather than showing nothing at all.
