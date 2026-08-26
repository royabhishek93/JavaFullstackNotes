# Flow API — Reactive Streams (Java 9)

**Interview Priority:** Senior: 👍 GOOD TO KNOW | Mid: 📚 AWARENESS

---

## Scenario

**Given this code, what happens when the producer is faster than the consumer?**

```java
// Producer pushes 1 million items instantly
// Consumer processes 1 item per second
queue.offer(item); // unbounded — OutOfMemoryError incoming
```

**Problem:** Without backpressure, a fast producer overwhelms a slow consumer.

---

## Key Principle

**`java.util.concurrent.Flow` defines the standard Reactive Streams interfaces in Java. Backpressure lets consumers control how fast producers send data.**

---

## Why It Happens (Simple English)

Reactive Streams solve the producer/consumer speed mismatch. The consumer tells the producer "give me N items" via `request(n)`. The producer only sends what was requested. This is called backpressure, and it keeps memory bounded.

---

## The Four Interfaces

```java
// java.util.concurrent.Flow (Java 9+)

Flow.Publisher<T>    // source of data
Flow.Subscriber<T>  // consumer of data
Flow.Subscription   // control link between publisher and subscriber
Flow.Processor<T,R> // both publisher and subscriber (transform stage)
```

---

## Subscriber Contract

```java
public class PrintSubscriber implements Flow.Subscriber<String> {
    private Flow.Subscription subscription;

    @Override
    public void onSubscribe(Flow.Subscription subscription) {
        this.subscription = subscription;
        subscription.request(1); // ask for first item
    }

    @Override
    public void onNext(String item) {
        System.out.println("Received: " + item);
        subscription.request(1); // ask for next item (backpressure)
    }

    @Override
    public void onError(Throwable throwable) {
        throwable.printStackTrace();
    }

    @Override
    public void onComplete() {
        System.out.println("Stream complete");
    }
}
```

---

## SubmissionPublisher (Built-in Publisher)

Java 9 ships one concrete `Publisher`: `SubmissionPublisher`.

```java
import java.util.concurrent.SubmissionPublisher;

public class FlowExample {
    public static void main(String[] args) throws Exception {
        SubmissionPublisher<String> publisher = new SubmissionPublisher<>();
        PrintSubscriber subscriber = new PrintSubscriber();

        publisher.subscribe(subscriber);

        publisher.submit("Item 1");
        publisher.submit("Item 2");
        publisher.submit("Item 3");

        publisher.close(); // signals onComplete
        Thread.sleep(100); // let async delivery finish
    }
}
```

---

## Processor Example (Transform Stage)

```java
public class UpperCaseProcessor
        extends SubmissionPublisher<String>
        implements Flow.Processor<String, String> {

    private Flow.Subscription subscription;

    @Override
    public void onSubscribe(Flow.Subscription subscription) {
        this.subscription = subscription;
        subscription.request(1);
    }

    @Override
    public void onNext(String item) {
        submit(item.toUpperCase()); // emit transformed item downstream
        subscription.request(1);
    }

    @Override
    public void onError(Throwable t) { closeExceptionally(t); }

    @Override
    public void onComplete() { close(); }
}

// Wire up: publisher → processor → subscriber
publisher.subscribe(processor);
processor.subscribe(subscriber);
```

---

## Backpressure in Action

```java
// subscriber controls the rate
subscription.request(10);   // "send me 10 items"
subscription.request(Long.MAX_VALUE); // "send everything" (no backpressure)
subscription.cancel();      // "stop sending"
```

---

## Flow vs Reactive Libraries

| | `java.util.concurrent.Flow` | RxJava / Project Reactor |
|---|---|---|
| What it is | Standard interfaces only | Full implementations |
| Operators | None built-in | Hundreds (map, filter, zip…) |
| Use directly | Only with `SubmissionPublisher` | Yes |
| Spring WebFlux | Uses Reactor | Built on Reactor |

`Flow` defines the contract. Libraries like Reactor and RxJava implement it.

---

## Wrong vs Right

| ❌ Wrong | ✅ Right |
|---|---|
| Unbounded queue from fast producer | `request(n)` to control flow |
| `request(Long.MAX_VALUE)` always | `request(1)` and re-request in `onNext` for slow consumers |
| Blocking in `onNext` | Offload to a separate thread if processing is heavy |

---

## Interview Tip (Exact Answer)

"`java.util.concurrent.Flow` defines the four Reactive Streams interfaces (`Publisher`, `Subscriber`, `Subscription`, `Processor`). The key is backpressure: the subscriber calls `request(n)` to tell the publisher how many items it can handle, keeping memory bounded when producers are faster than consumers."

---

## Quick Checklist

- Always call `subscription.request(n)` in `onSubscribe` to start receiving.
- Call `request(1)` again in `onNext` for pull-based backpressure.
- `SubmissionPublisher` is the only concrete publisher in the JDK.
- For real work use Reactor (`Mono`/`Flux`) or RxJava — `Flow` is just the contract.

---

## Critical Pitfalls

- Forgetting `subscription.request()` means `onNext` is never called.
- `SubmissionPublisher.submit()` blocks the caller when subscriber buffers are full (that IS the backpressure).
- Do NOT do heavy blocking work in `onNext` — it stalls delivery to all other subscribers.

---

## Follow-up Questions & Answers

**Q:** What is backpressure?

**A:** It is a feedback mechanism where the consumer signals to the producer how many items it can handle, preventing the producer from overwhelming it. In `Flow`, this is done via `subscription.request(n)`.

**Q:** Is Java's `Flow` API used directly in production?

**A:** Rarely. It defines the standard interfaces so libraries can interoperate. In practice, Spring WebFlux and Project Reactor (which implement the contract) are used instead.

---

## How to Use for Interviews

- Define backpressure first, then explain how `request(n)` implements it.
- Show the 4 interfaces and their roles.
- Mention that `Flow` is an interface contract; Reactor/RxJava are the implementations.

---

**Last Updated:** August 18, 2026
