# Senior Trap — "Arrow Functions Always Run Faster Because They Skip `this` Binding"
> **Topic:** Arrow Functions | **Level:** Senior Trap | **Frequency:** Medium

## The Setup

A developer justifies rewriting all service methods as arrow class fields in a performance PR: "Arrow functions are faster because they skip the `this` binding step that regular functions have to do on every call."

## The Question

Is it true that arrow functions are faster than regular functions due to skipping `this` binding? How would you respond to this in a code review?

## Model Answer (15 YOE)

This is wrong both at the engine level and as a practical concern, and it is a textbook example of cargo-cult optimisation.

Arrow functions do not skip `this` binding — they perform a scope chain lookup to find `this`, which is itself a runtime operation. The reason they do not create a new `this` binding is semantic, not a performance shortcut. The spec defines a different lookup strategy, not a faster one.

In practice, V8 and SpiderMonkey inline and optimise both function forms similarly in hot paths. JIT compilers are extremely good at optimising this specific pattern. I have profiled Node.js services handling tens of thousands of requests per second and the function declaration style has never shown up as a meaningful contributor to latency. Function call overhead in general is measured in nanoseconds; application latency is measured in milliseconds. The delta between arrow and regular functions is several orders of magnitude below the noise floor.

The right reason to choose an arrow function is lexical `this` semantics or cleaner syntax in a specific context — not speed. Optimisation decisions at this level require a profiler, a production load profile, and a reproducible benchmark. "Arrow functions are faster" from a listicle is not any of those things.

My code review comment would be: "The `this` binding argument is not accurate at the engine level — V8 optimises both forms similarly. What is the actual profiler output that flagged this as a bottleneck? If there is none, the refactor should be justified on readability or correctness grounds, not performance."

## Why It's a Trap

It sounds plausible — arrow functions are described as "lighter" in many tutorials — and it reveals a tendency to apply cargo-cult optimisations without profiling data.

## What NOT to Say

Agreeing that arrow functions are faster and elaborating confidently. That signals the candidate learned it from a blog post rather than from profiling real production traffic.

## Follow-up

**Q:** When would you actually profile function call overhead in a JavaScript application?

**A:** Only when a profiler — Chrome DevTools Performance panel, Node.js `--prof`, or `clinic.js` — shows a specific function appearing as a hot path consuming a significant fraction of CPU time. Even then, the first optimisation is usually algorithmic: an O(n²) operation inside a loop, an unnecessary re-render cycle, a synchronous I/O call. Raw function call overhead becomes relevant only in extremely tight computational loops, such as a physics engine ticking thousands of objects per frame or a parser processing gigabytes of data. For typical API servers and React UIs, it is never the bottleneck.
