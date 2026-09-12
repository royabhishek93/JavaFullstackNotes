# Senior Trap — What Does `this` Refer to in an Arrow Function at the Module's Top Level?
> **Topic:** Arrow Functions | **Level:** Senior Trap | **Frequency:** Low

## The Setup

You are reviewing a utility module written by a library author who wants to support both browser and Node.js environments. They have written `const getContext = () => this;` at the top level of the file and claim it returns the global object. The library ships in three formats: ES module, CommonJS, and a browser `<script>` tag bundle.

## The Question

What does `this` refer to in an arrow function defined at the top level of a module, and does the answer change depending on the module system?

## Model Answer (15 YOE)

It depends entirely on the module system — and the three environments the library targets give three different answers.

In an ES module — which is what you get from `<script type="module">`, a Vite/Webpack/Rollup output marked as ESM, or a Node.js `.mjs` file — the top-level `this` is `undefined`. The spec explicitly defines this. ES modules have their own module scope and the top-level `this` is not bound to any object.

In CommonJS — Node.js `.cjs` files or any file loaded with `require` — the top-level `this` is the `module.exports` object. This is a Node.js-specific behaviour from the wrapping that Node applies to every CommonJS file. An arrow function at the top of a CommonJS file will capture `module.exports` as its `this`, which is almost never what you want.

In a classic browser `<script>` tag (non-module), top-level `this` is `window`. An arrow function here captures the global object.

So the library author's claim is wrong for two of the three targets. The correct way to access the global object portably is `globalThis`, which is defined in ES2020 and available in all modern environments. An arrow function that closes over `globalThis` works correctly everywhere, whereas one that closes over `this` is environment-dependent in a way that will silently produce wrong behaviour in ESM consumers.

This is a real failure mode in library code. I have seen SDKs that worked fine as script-tag embeds but returned `undefined` for `this`-based global references when consumed as ESM imports.

## Why It's a Trap

Most candidates answer "the global object" — correct for script tags, wrong for ES modules (where it's `undefined`) and CommonJS (where it's `module.exports`). The module system changes the answer.

## What NOT to Say

"Top-level `this` is always `window`" — this is only true in non-module browser scripts. In ES modules and Node.js CommonJS, `this` at the top level is something else entirely.

## Follow-up

**Q:** How do you write a module that needs to access the global object and works correctly in all three environments?

**A:** Use `globalThis`. It was standardised in ES2020 and is available in Node.js 12+, all modern browsers, and Web Workers. `globalThis` is always the global object regardless of module format, strict mode, or execution context. For environments that predate `globalThis` (Node.js < 12, IE), the idiom was `(typeof globalThis !== 'undefined' ? globalThis : typeof window !== 'undefined' ? window : global)` — exactly the pattern you see in UMD bundles. Modern code should just use `globalThis` and set the minimum Node.js version accordingly.
