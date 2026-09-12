# Redux Middleware — compose in the Store Enhancer Chain
> **Topic:** Composition | **Level:** Intermediate | **Frequency:** High

## The Setup
A Swiggy payments team is setting up a Redux store with `redux-thunk`, a custom `analyticsMiddleware`, a `crashReporter`, and Redux DevTools. A new engineer wired them with nested `applyMiddleware` calls and got a broken store.

## The Question
Explain how Redux's `compose` works and why it is the right tool here.

## Diagram

```
Redux store enhancer chain using compose:

  compose(DevTools.instrument(), applyMiddleware(thunk, analytics, crashReporter))

  = DevTools.instrument()(applyMiddleware(thunk, analytics, crashReporter)(createStore))

  Execution order (right to left):
  createStore
       |
       v
  applyMiddleware(thunk, analytics, crashReporter)   <-- runs first
       |
       v
  DevTools.instrument()                              <-- wraps the result
       |
       v
  enhancedStore
```

## Model Answer (15 YOE)

Redux ships its own `compose` — the same `reduceRight` implementation we write from scratch. The store creator API expects a single enhancer function. When you have multiple enhancers, `compose` collapses them into one:

```js
import { createStore, compose, applyMiddleware } from 'redux';
import thunk from 'redux-thunk';

const analyticsMiddleware = store => next => action => {
  analytics.track(action.type);
  return next(action);
};

const crashReporter = store => next => action => {
  try { return next(action); }
  catch (e) { Sentry.captureException(e, { extra: action }); throw e; }
};

const store = createStore(
  rootReducer,
  compose(
    applyMiddleware(thunk, analyticsMiddleware, crashReporter),
    window.__REDUX_DEVTOOLS_EXTENSION__ ? window.__REDUX_DEVTOOLS_EXTENSION__() : f => f
  )
);
```

`compose` runs right-to-left: `applyMiddleware` wraps `createStore` first, then DevTools wraps that result. Each enhancer is a function from `createStore` to `createStore` — exactly the unary signature compose requires. The middleware inside `applyMiddleware` are themselves composed (left-to-right via `reduceRight` in reverse) — `thunk` intercepts first, then `analyticsMiddleware`, then `crashReporter`. The nested call that the new engineer wrote was doing the same thing but manually, error-prone, and unreadable.

## Follow-up

**Q:** Why does middleware order matter inside `applyMiddleware`?

**A:** Each middleware wraps `dispatch`. `thunk` must come first because it intercepts function-typed actions before they reach the actual dispatch. If `logger` is first, it logs the function object (unhelpful) instead of the resolved action. `crashReporter` should be last in the chain (first in the wrap order) so it catches errors thrown by any middleware below it. Order encodes intent — that is a design decision, not an implementation detail.
