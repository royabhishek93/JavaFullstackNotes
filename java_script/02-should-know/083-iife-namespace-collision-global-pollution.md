# Namespace Isolation — Two Libraries Colliding in a Legacy App
> **Topic:** IIFE | **Level:** Intermediate | **Frequency:** Medium

## The Setup

You inherit a large e-commerce frontend that loads twelve third-party JavaScript files via `<script>` tags in `index.html`. A production bug report says the search autocomplete stopped working after a new chat widget was added. Debugging reveals that both the search library and the chat widget declare `var utils = { ... }` at the top level, and the second one overwrites the first.

## The Question

Explain why this collision happens, how IIFE was used historically to prevent it, and what the modern equivalent is.

## Diagram

```
┌──────────────────────────────────────────────────────────────┐
│            GLOBAL NAMESPACE COLLISION                        │
│                                                              │
│  Without IIFE — both scripts run in global scope:            │
│  ┌─────────────────┐    ┌─────────────────┐                  │
│  │  search.js      │    │  chat.js        │                  │
│  │  var utils = {  │    │  var utils = {  │ ← overwrites     │
│  │    debounce,    │    │    throttle,    │                  │
│  │    highlight    │    │    format       │                  │
│  │  }              │    │  }              │                  │
│  └────────┬────────┘    └────────┬────────┘                  │
│           └─────────┬────────────┘                           │
│                     ▼                                        │
│            window.utils = chat's utils   ← search broken     │
│                                                              │
│  With IIFE — each script has its own scope:                  │
│  ┌─────────────────────────────────────────┐                 │
│  │  // search.js                           │                 │
│  │  (function() {                          │                 │
│  │    var utils = { debounce, highlight }; │ ← local         │
│  │    window.SearchWidget = { init, query };                 │
│  │  })();                                  │                 │
│  └─────────────────────────────────────────┘                 │
│  ┌─────────────────────────────────────────┐                 │
│  │  // chat.js                             │                 │
│  │  (function() {                          │                 │
│  │    var utils = { throttle, format };    │ ← local         │
│  │    window.ChatWidget = { open, send };  │                 │
│  │  })();                                  │                 │
│  └─────────────────────────────────────────┘                 │
│                                                              │
│  window.utils = undefined  (never exposed)                   │
│  window.SearchWidget and window.ChatWidget both intact  ✓    │
└──────────────────────────────────────────────────────────────┘
```

## Model Answer (15 YOE)

The root cause is `var` hoisting and global scope. In a browser, all `var` declarations outside a function land on the `window` object. When `chat.js` loads after `search.js`, its `var utils = ...` creates a new `window.utils`, silently replacing the one from `search.js`. There is no error — JavaScript does not prevent reassignment of global `var` declarations.

The IIFE fix is to wrap each library in an immediately-invoked function. Variables declared with `var` inside a function are local to that function, so each library gets its own `utils` that never reaches `window`. The only things that land on `window` are what the library intentionally exports: `window.SearchWidget`, `window.ChatWidget`. The variable names used internally are invisible to each other.

This pattern is why virtually every serious JavaScript library written before 2015 is wrapped in an IIFE. jQuery wraps in an IIFE. Google Analytics loads with an IIFE. The Facebook Pixel is an IIFE. Any SDK that must be loaded via a `<script>` tag on a page with arbitrary other scripts uses this pattern to protect its internals.

The modern equivalent is ES modules. When a file is loaded as `<script type="module">`, the browser gives it a completely separate module scope. Variables declared in a module file do not appear on `window` at all unless you explicitly assign them. In a build-tool environment — Webpack, Vite, Rollup — every file is automatically module-scoped regardless of whether you use ES module syntax, because the bundler wraps each module in its own IIFE or scope block.

## Follow-up

**Q:** You cannot change the third-party scripts, but you can control the HTML. What is the fastest way to fix this collision today without a bundler?

**A:** Load both scripts as `type="module"`. A `<script type="module">` gives each file its own module scope, so `var utils` in each stays local. If the scripts use `var` at the top level and rely on `window.utils` internally, that approach would break them. In that case, the safest immediate fix is to load them in an `<iframe>` with `sandbox` attributes — each iframe has its own `window`, completely isolated. It is heavy-handed but requires zero changes to the scripts. The proper long-term fix is to replace them with versions that use ES modules or are wrapped in IIFE internally.
