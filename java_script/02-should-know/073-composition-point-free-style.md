# Point-Free Style in a Node.js API Transform Layer
> **Topic:** Composition | **Level:** Intermediate | **Frequency:** Medium

## The Setup
A Paytm backend engineer wrote a user-data transformation layer where every function explicitly receives and names its `user` argument. A senior asked her to rewrite it "point-free." She has no idea what that means and asked you.

## The Question
Explain point-free style, show a before/after, and say when NOT to use it.

## Diagram

```
Pointed style (explicit argument threading):
  const process = user => formatForApi(enrichWithDefaults(sanitize(user)));

Point-free style (no argument named — the composition IS the function):
  const process = compose(formatForApi, enrichWithDefaults, sanitize);

  The data "point" is implicit — it flows through the pipeline without being named.

  When it works:    unary pure functions -> compose/pipe handles argument passing
  When it breaks:   multi-arg functions, async stages, branching logic
```

## Model Answer (15 YOE)

Point-free (also called tacit) style means writing a function without explicitly mentioning its argument. Instead of `x => f(g(x))`, you write `compose(f, g)`. The data flows implicitly through the pipeline:

```js
// Pointed — user is named at every level
const getDisplayName = user => user.name.trim().toLowerCase();

// Point-free — compose handles the threading
const trim  = str => str.trim();
const lower = str => str.toLowerCase();
const getName = user => user.name;

const getDisplayName = compose(lower, trim, getName);

// Real pipeline — user data transform
const sanitize    = u => ({ ...u, email: u.email?.toLowerCase().trim() });
const addDefaults = u => ({ role: 'viewer', ...u });
const toApiShape  = u => ({ id: u.id, email: u.email, role: u.role });

const processUser = pipe(sanitize, addDefaults, toApiShape);
// No 'user' argument named anywhere — point-free
```

Point-free reads well when every function is unary and the pipeline is a straight sequence. It degrades badly when: (a) you need to branch — `if (user.isAdmin) ...` needs the argument; (b) you compose functions with different arities — partial application or currying is needed first; (c) the pipeline is long enough that the implicit flow obscures what type is being passed. In a team codebase, I enforce point-free at the module boundary (the exported `processUser`) and keep individual stages pointed internally for clarity and debuggability.

## Follow-up

**Q:** How does currying enable point-free style for multi-argument functions?

**A:** Currying converts `fn(a, b)` into `fn(a)(b)` — a chain of unary functions. Once curried, you can partially apply the first argument and get a unary function suitable for a compose pipeline. For example: `const add = a => b => a + b; const add10 = add(10);` — `add10` is unary, composable, point-free-friendly. Libraries like Ramda curry all their functions automatically, which is why Ramda-style code is almost entirely point-free.
