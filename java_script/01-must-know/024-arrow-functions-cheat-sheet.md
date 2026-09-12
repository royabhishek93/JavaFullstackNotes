# Arrow Functions — Cheat Sheet
> **Topic:** Arrow Functions | **Level:** Reference

```js
// ─────────────────────────────────────────────────────────────
// SYNTAX
// ─────────────────────────────────────────────────────────────

// Regular
function add(a, b) { return a + b; }

// Arrow — full form
const add = (a, b) => { return a + b; };

// Arrow — implicit return (no curly braces)
const add = (a, b) => a + b;

// Arrow — single param, parens optional
const double = x => x * 2;

// Arrow — no params
const greet = () => "Hello";

// Arrow — returning an object literal (wrap in parens or it parses as block)
const toDTO = user => ({ id: user.id, name: user.name });

// ─────────────────────────────────────────────────────────────
// THIS BINDING
// ─────────────────────────────────────────────────────────────

// PROBLEM: regular function loses this when detached
class Form extends React.Component {
  handleSubmit() {             // prototype method
    this.setState({ sent: true }); // this = undefined when called by React
  }
  render() {
    return <button onClick={this.handleSubmit} />; // detached!
  }
}

// FIX 1: Arrow class field (preferred for React handlers)
class Form extends React.Component {
  handleSubmit = () => {        // instance property
    this.setState({ sent: true }); // this = always the component instance ✓
  };
}

// FIX 2: Constructor bind
class Form extends React.Component {
  constructor(props) {
    super(props);
    this.handleSubmit = this.handleSubmit.bind(this);
  }
}

// FIX 3: setTimeout — use arrow callback
componentDidMount() {
  setTimeout(() => {
    this.setState({ loaded: true }); // this = component instance ✓
  }, 1000);
}

// ─────────────────────────────────────────────────────────────
// WHEN ARROW FUNCTIONS BREAK
// ─────────────────────────────────────────────────────────────

// Object literal method — arrow captures outer (window/undefined), not obj
const config = {
  env: 'prod',
  getEnv: () => this.env,  // ✗ this = outer scope, not config
  getEnvCorrect() { return this.env; }  // ✓ regular method
};

// Prototype override — arrow field blocks it
class Base {
  format = () => 'base';         // instance property, NOT prototype
}
class Child extends Base {}
const c = new Child();
c.format();                     // 'base' — cannot override via prototype

// Constructor — arrow functions cannot use new
const Foo = () => {};
new Foo(); // TypeError: Foo is not a constructor

// ─────────────────────────────────────────────────────────────
// ARGUMENTS OBJECT
// ─────────────────────────────────────────────────────────────

function sum() {
  return [...arguments].reduce((a, b) => a + b, 0); // works
}

const sum = (...args) => args.reduce((a, b) => a + b, 0); // arrow equivalent

// ─────────────────────────────────────────────────────────────
// ASYNC ARROW
// ─────────────────────────────────────────────────────────────

const fetchOrders = async (userId) => {
  const res = await fetch(`/api/orders/${userId}`);
  return res.json();
};

// As Express handler
app.get('/orders', async (req, res) => {
  const orders = await OrderService.find(req.user.id);
  res.json(orders);
});

// ─────────────────────────────────────────────────────────────
// DECISION RULE
// ─────────────────────────────────────────────────────────────
// Arrow class field  →  handler/callback, never overridden
// Regular method     →  inherited, mocked via prototype, uses super
// Inline arrow       →  simple callback expression (< 3 lines)
// Named function     →  complex callback (3+ lines), needs stack trace/test
```

## Two Approaches — When to Choose

| | Arrow Function | Regular Function |
|---|---|---|
| **What it is** | Expression assigned to a variable; no own `this`, `arguments`, or `prototype` | Declaration or expression with its own `this` binding determined at call time |
| **Strength** | Lexical `this` makes it safe to pass as a callback; implicit return for single expressions; concise syntax | Can be used as constructor; participates in prototype chain; hoisted (declarations); has `arguments` object; works with `super` |
| **Weakness** | Cannot be used with `new`; does not work as a reliable override in subclasses; instance property when used as class field (memory per-instance) | `this` is lost when detached from its object; requires `.bind()` or wrapper for use as callbacks |
| **Use when** | Callbacks passed to `setTimeout`, array methods, event listeners; React event handlers; Express route lambdas | Object methods that must be inherited; constructors; generator functions; code that uses `arguments`; prototype-level testing |
| **Real example** | `handleClick = () => this.setState(...)` as a React class field; `users.filter(u => u.isActive)` | `class EventEmitter { emit(event) { ... } }` — subclasses need to override `emit` |
