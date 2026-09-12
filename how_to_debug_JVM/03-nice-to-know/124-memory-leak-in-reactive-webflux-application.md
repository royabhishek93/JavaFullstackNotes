# #124 — Memory Leak in Reactive/WebFlux Application

> **Category:** Memory Leaks End-to-End | **Type:** Advanced Scenario Q&A | **Priority:** 📘 Advanced

## 🗣️ The Interview Question
"How do memory leak patterns differ in a reactive (Project Reactor) application vs. a thread-per-request model?"

## 😊 Explain It Simply (for anyone)
In a traditional app, each request is like a single relay racer running the whole track themselves — when they cross the finish line, their leg of the race is naturally "over" and everything they carried is dropped. In reactive programming (a style where work is broken into small async steps chained together, instead of one continuous thread), it's more like a bucket brigade passing a bucket hand-to-hand down a line of people — there's no single racer whose "finish" cleans everything up. If someone in the middle of that chain never passes the bucket along (never "completes" or "disposes" their piece), everyone behind them in line keeps standing there holding their arms out forever, and the objects each of them is holding never get released.

## 📊 Visualize It
```
 Thread-per-request:
   [stack frame] -> [stack frame] -> [stack frame] -> return -> freed

 Reactive pipeline (Project Reactor):
   flux.subscribe()  <-- Disposable not stored/disposed
        |
        v
   [operator1] -> [operator2] -> [operator3] ... never torn down
        (whole chain stays alive, even after "logical" completion)

   onBackpressureBuffer() with NO size limit:
   producer -----> [buffer: grows unbounded] -----> slow consumer
```

## 🏭 The Real Production Answer (15-YOE Level)

In a traditional thread-per-request model, the request's call stack is a natural scope — objects on the stack are freed when the method returns. In reactive code, there is no call stack spanning the request; instead, a pipeline of lambdas is assembled and executed asynchronously.

Leak patterns specific to reactive:

1. **Subscription not disposed**: if you call `flux.subscribe()` without keeping the `Disposable` and calling `dispose()`, the subscription and all its upstream operators remain live. In a long-lived service, each call to `subscribe()` without cleanup adds to Reactor's internal operator chain.

2. **Context propagation through Reactor Context**: Reactor's `Context` (replacing ThreadLocal in reactive) can accumulate data if chained carelessly — each `contextWrite` adds a layer, and if objects stored in context are large, the entire chain holds them.

3. **Backpressure ignored**: if a producer emits faster than a consumer consumes and you use `onBackpressureBuffer()` without a size limit, the buffer grows unbounded:
```java
// LEAK: unbounded buffer
source.onBackpressureBuffer().subscribe(consumer);

// Fix: bounded buffer with drop or error strategy
source.onBackpressureBuffer(10_000, BufferOverflowStrategy.DROP_OLDEST)
      .subscribe(consumer);
```

4. **Hot publisher subscribers**: connecting to a hot `ConnectableFlux` and never calling `dispose` on the subscriber means the subscription chain keeps the upstream alive.

Diagnosis: Reactor has built-in leak detection. Enable it:
```java
Hooks.onOperatorDebug(); // dev only, expensive
// Or in production:
ReactorDebugAgent.init(); // ByteBuddy-based, lower overhead
```

## 🔑 Key Takeaway
Reactive pipelines have no natural "stack unwind" cleanup — always store and dispose `Disposable`s, and bound backpressure buffers explicitly.
