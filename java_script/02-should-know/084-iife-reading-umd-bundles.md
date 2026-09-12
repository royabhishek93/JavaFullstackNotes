# Legacy Codebase Audit — Reading a UMD Bundle
> **Topic:** IIFE | **Level:** Intermediate | **Frequency:** Medium

## The Setup

You join a fintech company as a staff engineer. The team is migrating from a legacy monolith to a React microfrontend architecture. During the audit, you open `payment-sdk.js`, a vendor library loaded via `<script>` tag. The entire file is wrapped in a large IIFE that accepts `window` and a factory function as arguments. A junior engineer asks you what the pattern is and why it was written that way.

## The Question

What is UMD, why does it use an IIFE, and what problem does the outer parameter structure solve?

## Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                  UMD BUNDLE STRUCTURE                        │
│                                                              │
│  (function(global, factory) {                                │
│    if (typeof exports !== 'undefined') {                     │
│      // CommonJS (Node.js / Webpack)                         │
│      module.exports = factory(require('dependency'));        │
│    } else if (typeof define === 'function' && define.amd) { │
│      // AMD (RequireJS)                                      │
│      define(['dependency'], factory);                        │
│    } else {                                                  │
│      // Browser global (<script> tag)                        │
│      global.PaymentSDK = factory(global.Dependency);        │
│    }                                                         │
│  })(typeof globalThis !== 'undefined' ? globalThis : this,  │
│     function(Dependency) {                                   │
│       // actual library code                                 │
│       return { charge, refund };                             │
│     });                                                      │
│                                                              │
│  Why IIFE:                                                   │
│  ┌───────────────────────────────────────────────────────┐   │
│  │ • Library internals never leak to global scope        │   │
│  │ • Works in any environment — no import/require needed │   │
│  │ • One file, zero build tool requirements              │   │
│  └───────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

## Model Answer (15 YOE)

UMD stands for Universal Module Definition. It is a pattern that lets a single JavaScript file run correctly in three different module environments: CommonJS (Node.js), AMD (RequireJS, which was popular around 2012–2016), and a plain browser `<script>` tag with no module system at all. The IIFE is the vehicle that makes this work.

The outer wrapping function receives `global` — the environment's global object — and `factory` — the actual library code expressed as a function. Inside the IIFE, it detects the environment by checking for `exports`, `define`, or falling back to `global`. This detection runs immediately when the file is parsed, before any application code runs.

The reason for passing `global` as an explicit parameter rather than referencing `window` directly is portability. In Node.js, `window` does not exist. In a web worker, `window` does not exist either. By receiving the global object as an argument, the bundle stays environment-agnostic. Old Lodash, jQuery, Moment.js, and virtually every analytics SDK shipped in this format.

What I tell the junior engineer: you do not need to write UMD today — bundlers like Webpack and Rollup generate it automatically from ES module source. But you need to read it fluently because you will encounter it in vendor audits, security reviews of third-party scripts, and when you are debugging a minified SDK in a production incident. The IIFE wrapper is the first thing to identify so you know where the library's internal scope begins and ends.

## Follow-up

**Q:** When migrating this library to an ES module, what is the first thing you check before removing the IIFE wrapper?

**A:** Whether any consumer is loading it via a `<script>` tag without a bundler. If yes, an ES module requires `<script type="module">` and has different CORS and caching behavior. I would check the CDN setup, any CMS integrations, and whether any partner sites embed the script directly. The IIFE version works everywhere with zero configuration; the ES module version requires a capable environment. Migration often means shipping both and deprecating the IIFE form over a release cycle rather than a hard cutover.
