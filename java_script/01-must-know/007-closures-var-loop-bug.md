# The `var` Loop Bug in a Cart Renderer
> **Topic:** Closures | **Level:** Intermediate | **Frequency:** Medium

## The Setup
A junior engineer at Amazon is dynamically rendering "Add to Cart" buttons for a list of products. They attach click handlers in a `for` loop using `var`. In QA, every button adds the last product in the list to the cart regardless of which button was clicked.

## The Question
Diagnose the bug precisely, explain the closure mechanism causing it, and give two production fixes.

## Diagram
```
  BROKEN (var is function-scoped, not block-scoped)
  ┌────────────────────────────────────────────────┐
  │  for (var i = 0; i < products.length; i++) {  │
  │    buttons[i].onclick = function() {           │
  │      addToCart(products[i]); // closes over i  │
  │    };                                          │
  │  }                                             │
  │  // loop finishes: i === products.length       │
  │  // ALL callbacks share the SAME i             │
  └────────────────────────────────────────────────┘

  All 3 handlers point to the same i in the same scope:
  ┌──────────┐   ┌──────────┐   ┌──────────┐
  │ onclick0 │   │ onclick1 │   │ onclick2 │
  └────┬─────┘   └────┬─────┘   └────┬─────┘
       └──────────────┴──────────────┘
                       │ all read same var i
                       ▼
                  i === 3 (after loop ends)

  FIX 1: let (block-scoped — new binding per iteration)
  ┌──────────┐   ┌──────────┐   ┌──────────┐
  │ onclick0 │   │ onclick1 │   │ onclick2 │
  └────┬─────┘   └────┬─────┘   └────┬─────┘
       │              │              │
       ▼              ▼              ▼
     i=0            i=1            i=2   (each iteration = own binding)
```

## Model Answer (15 YOE)
The root cause is that `var` is function-scoped. There is one single `i` variable shared across all iterations of the loop and all closures created inside it. By the time any click handler fires, the loop has already completed and `i` equals `products.length` — pointing past the end of the array. Every handler reads that same final value.

The idiomatic fix in modern JavaScript is to replace `var` with `let`. The `let` keyword is block-scoped, and a `for` loop's block is re-entered on each iteration. The JavaScript spec creates a new binding of `i` for every iteration — each closure captures a distinct, independent `i`. This is not just a syntactic preference; it is a semantic difference in how the variable is bound.

The pre-ES6 fix — worth knowing for legacy codebases — is an IIFE that creates a new function scope per iteration: `(function(capturedI) { btn.onclick = function() { addToCart(products[capturedI]); } })(i)`. This works because function scope is respected by `var`, so `capturedI` inside the IIFE is a new variable per call.

The deeper production lesson: prefer `const` and `let` everywhere. Reserve `var` for nothing — there is no modern scenario where `var` is the right choice. When I review PRs I flag any `var` in a loop body with an event handler or callback inside it as a latent bug, not a style issue.

```js
// BROKEN
for (var i = 0; i < products.length; i++) {
  buttons[i].onclick = function() {
    addToCart(products[i]); // i is always products.length when clicked
  };
}

// FIX 1: let (preferred)
for (let i = 0; i < products.length; i++) {
  buttons[i].onclick = function() {
    addToCart(products[i]); // each iteration has its own i binding
  };
}

// FIX 2: IIFE (legacy codebases)
for (var i = 0; i < products.length; i++) {
  (function(capturedI) {
    buttons[capturedI].onclick = function() {
      addToCart(products[capturedI]);
    };
  })(i);
}
```

## Follow-up
**Q:** Does `const` in a for-of loop have the same per-iteration binding behavior as `let` in a for loop?

**A:** Yes. In a `for...of` loop, each iteration creates a new binding for the loop variable regardless of whether you use `const` or `let`. The `const` version is actually preferable for `for...of` when you do not need to reassign the variable inside the loop body, because it makes the intent explicit. The classic `for (var i...)` loop is the specific problematic form.
