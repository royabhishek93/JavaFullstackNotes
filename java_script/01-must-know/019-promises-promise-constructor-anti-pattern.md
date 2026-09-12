# Promise Constructor Anti-Pattern
> **Topic:** Promises | **Level:** Senior Trap | **Frequency:** Medium

## The Setup

Code review. A team member submits this Express route handler:

```js
app.get('/user/:id', (req, res) => {
  const p = new Promise((resolve, reject) => {
    User.findById(req.params.id)
      .then(user => resolve(user))
      .catch(err => reject(err));
  });
  p.then(user => res.json(user))
   .catch(err => res.status(500).json({ error: err.message }));
});
```

## The Question

What is wrong with this code? What is the anti-pattern called and what is the correct version?

## Diagram

```
Anti-pattern (Promise constructor wrapping a Promise):
  new Promise((resolve, reject) => {    <- outer Promise, unnecessary
    existingPromise                     <- already a Promise
      .then(v => resolve(v))            <- just re-wrapping resolve
      .catch(e => reject(e))            <- just re-wrapping reject
  })

  If existingPromise rejects AND .catch is missing from inner chain,
  you get an unhandled rejection INSIDE the constructor. Doubly bad.

Correct: just use the Promise that already exists
  existingPromise
    .then(...)
    .catch(...)
```

## Model Answer (15 YOE)

This is the "Promise constructor anti-pattern" (also called the "explicit Promise construction anti-pattern" or "deferred anti-pattern"). The code wraps a function that already returns a Promise — `User.findById()` — in a `new Promise()` constructor. It is redundant, adds error surface area, and obscures the intent.

The correct version using `.then()` style:

```js
app.get('/user/:id', (req, res) => {
  User.findById(req.params.id)
    .then(user => res.json(user))
    .catch(err => res.status(500).json({ error: err.message }));
});
```

Or with `async/await`, which reads more naturally in Express handlers:

```js
app.get('/user/:id', async (req, res) => {
  try {
    const user = await User.findById(req.params.id);
    res.json(user);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});
```

The anti-pattern is worth catching in code review because it signals the author does not understand the Promise chain. It also introduces a subtle bug: if an exception is thrown synchronously inside the `new Promise()` executor before `.then()` is reached, it is silently swallowed in some older runtimes. Only use `new Promise()` when you are wrapping something that is genuinely callback-based and has no Promise interface.

## Follow-up

**Q:** When is `new Promise()` the correct choice?

**A:** When wrapping a callback-based API that has no Promise interface — for example, `setTimeout`, a legacy `EventEmitter`, or an old library using `(err, result)` callbacks. If the underlying function already returns a Promise, never wrap it in `new Promise`.

## Why It's a Trap

Candidates who have learned Promise syntax without understanding the underlying model instinctively reach for `new Promise()` as "the way to create async code." They see `.then()` and `.catch()` already in the code and assume the `new Promise()` constructor is required to "start" the chain. In reality, `User.findById()` already returns a Promise — you can call `.then()` directly on it.

## What NOT to Say

- "The code works fine, it's just extra ceremony." — It does work, but it hides understanding and adds real error surface area. A senior reviewer rejects this.
- "You need `new Promise()` to handle async code." — No. You only need it to convert callback APIs.
- "The `.then(v => resolve(v))` pattern is a safe pattern." — It is the anti-pattern pattern. It adds a potential unhandled rejection vector if an error occurs inside the constructor before the inner `.catch` is registered.
