# IIFE — Cheat Sheet
> **Topic:** IIFE | **Level:** Reference

```js
// ─────────────────────────────────────────────────────────────
// SYNTAX VARIANTS
// ─────────────────────────────────────────────────────────────

// Standard — function expression wrapped in parens
(function() {
  // code runs immediately
})();

// Crockford variant — invocation inside outer parens
(function() {
  // code runs immediately
}());

// Arrow function IIFE
(() => {
  // code runs immediately
})();

// Async IIFE
(async () => {
  const data = await fetch('/api/config');
  // use data
})();

// IIFE with arguments
(function(global, doc) {
  // use global and doc
})(window, document);

// IIFE with return value
const PI = (function() {
  return 3.14159;
})();

// Parser alternative forms (common in minified code)
!function() { /* ... */ }();
void function() { /* ... */ }();

// ─────────────────────────────────────────────────────────────
// MODULE PATTERN
// ─────────────────────────────────────────────────────────────

const CartService = (function() {
  // PRIVATE — accessible only through returned methods
  let _items = [];
  let _discount = 0;

  function _calculateSubtotal() {
    return _items.reduce((sum, item) => sum + item.price, 0);
  }

  // PUBLIC API
  return {
    addItem(item) {
      _items.push(item);
    },
    applyDiscount(pct) {
      _discount = pct;
    },
    getTotal() {
      const sub = _calculateSubtotal();
      return sub - (sub * _discount / 100);
    },
    clear() {
      _items = [];
      _discount = 0;
    }
  };
})();

CartService.addItem({ name: 'Biryani', price: 220 });
CartService.applyDiscount(10);
console.log(CartService.getTotal());   // 198
console.log(CartService._items);       // undefined — private

// ─────────────────────────────────────────────────────────────
// ASYNC IIFE — Node.js script initialization
// ─────────────────────────────────────────────────────────────

(async () => {
  const conn = await db.connect();
  try {
    const records = await conn.find({ migrated: false });
    await processInBatches(records, 100);
    console.log(`Migrated ${records.length} records`);
  } finally {
    await conn.close();
  }
})().catch(err => {
  console.error('Fatal:', err.message);
  process.exit(1);
});

// ─────────────────────────────────────────────────────────────
// UMD PATTERN — recognising it in the wild
// ─────────────────────────────────────────────────────────────

(function(global, factory) {
  if (typeof exports !== 'undefined') {
    module.exports = factory();        // CommonJS / Node.js
  } else if (typeof define === 'function' && define.amd) {
    define([], factory);               // AMD / RequireJS
  } else {
    global.MyLibrary = factory();      // Browser global
  }
})(typeof globalThis !== 'undefined' ? globalThis : this, function() {
  // library implementation
  return { version: '1.0.0' };
});

// ─────────────────────────────────────────────────────────────
// WHEN TO USE — DECISION RULE
// ─────────────────────────────────────────────────────────────
// IIFE module pattern   →  singleton with private state, no build tool
// Async IIFE            →  top-level await in CommonJS / script files
// UMD IIFE              →  library that must run in browser AND Node.js
// ES module             →  any project with a bundler or Node 14+ ESM
// Class + private #     →  multiple instances needed, modern environment
//
// READING IIFE IN THE WILD:
// 1. Find the outer ( — that marks the function expression start
// 2. Find the matching ) and trailing () — that is the invocation
// 3. Arguments to the invocation tell you what the IIFE receives
// 4. The return value (if any) is what gets exported
```

## Two Approaches — When to Choose

| | IIFE | ES Module |
|---|---|---|
| **What it is** | Function expression invoked immediately; creates a temporary or closure-based private scope | A file with its own module scope; uses `import`/`export` for explicit dependency contracts |
| **Strength** | Works in any environment without a build step; enables the module pattern (singleton with private state); readable async initialization; UMD cross-environment compatibility | Statically analyzable by bundlers for tree-shaking; explicit dependency graph; native browser support; works with TypeScript types; top-level `await` in ES2022 |
| **Weakness** | No static analysis; circular dependencies are invisible; global namespace must be managed manually; cannot tree-shake unused code | Requires `type="module"` or a bundler; CORS restrictions on `<script type="module">`; top-level `await` not available in CommonJS; adds build complexity |
| **Use when** | Legacy browser environments; scripts loaded via tag managers or CDN without bundling; inline Node.js scripts in CommonJS; reading/maintaining pre-2015 code | All new greenfield projects; React/Next.js/Vite apps; Node.js 14+ with `"type": "module"`; any project with a build step |
| **Real example** | Google Analytics snippet, payment SDK vendor files, Webpack runtime bootstrap, Angular 1.x service pattern | React component files, Express route modules, any file in a modern Node.js or browser project |
