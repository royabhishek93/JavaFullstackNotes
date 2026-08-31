# #71 — Producer-Consumer Deadlock

> **Category:** Thread Dump Analysis | **Type:** Scenario Q&A | **Priority:** 👍 Good-to-Know

## 🗣️ The Interview Question
"A message processing system deadlocks occasionally. Both Producer and Consumer threads use synchronized methods on shared state. How do you find and fix it?"

## 😊 Explain It Simply (for anyone)
Picture two people passing notes through a mail slot, but the rule is: to send a note you must first grab the "sending pen," then also grab the "reading pen" before you drop the note in. The person receiving notes has the opposite rule: grab the "reading pen" first, then the "sending pen." If both people try to swap notes at exactly the same moment, sender grabs the sending pen while receiver grabs the reading pen — now sender is stuck waiting for the reading pen (which receiver has) and receiver is stuck waiting for the sending pen (which sender has). Nobody can move. Forever.

This is a **lock ordering deadlock** — it happens specifically because the two sides grab the same two locks in *opposite* order. The fix is either strict discipline (always grab locks in the same order, no exceptions) or, even better, using a purpose-built "mailbox" tool (a `BlockingQueue`) that already handles all the passing-notes safety internally, so nobody needs to juggle two pens at all.

## 📊 Visualize It
```
producer-thread-1                consumer-thread-1
┌──────────────┐                 ┌──────────────┐
│ holds:        │                 │ holds:        │
│ producerLock  │◄───wants───────►│ consumerLock  │
└──────────────┘                 └──────────────┘
   wants consumerLock                wants producerLock
        (OPPOSITE acquisition order = deadlock)
```

## 🏭 The Real Production Answer (15-YOE Level)
"This is the classic producer-consumer deadlock. Here's the code pattern that causes it:

```java
class MessageQueue {
    private final Object producerLock = new Object();
    private final Object consumerLock = new Object();

    // Producer acquires producerLock then consumerLock
    public synchronized void produce(Message m) {
        synchronized(consumerLock) { // nested lock acquisition
            queue.add(m);
            notifyConsumer();
        }
    }

    // Consumer acquires consumerLock then producerLock (OPPOSITE ORDER!)
    public synchronized void consume() {
        synchronized(producerLock) { // opposite order — deadlock!
            return queue.poll();
        }
    }
}
```

jstack shows:
```
Found 1 deadlock.
"producer-thread-1":
  waiting to lock <0x00000006c1> (consumerLock)
  held by "consumer-thread-1"
"consumer-thread-1":
  waiting to lock <0x00000006c2> (producerLock)
  held by "producer-thread-1"
```

Fix: always acquire locks in the same order. Or better, eliminate nested locks by using `java.util.concurrent.BlockingQueue` which handles thread-safety internally without any explicit synchronization needed by callers:

```java
class MessageQueue {
    private final BlockingQueue<Message> queue =
        new LinkedBlockingQueue<>(1000);

    public void produce(Message m) throws InterruptedException {
        queue.put(m); // blocks if full, no explicit lock needed
    }

    public Message consume() throws InterruptedException {
        return queue.take(); // blocks if empty, no explicit lock needed
    }
}
```"

## 🔑 Key Takeaway
Nested locks acquired in opposite order between producer and consumer is the textbook deadlock recipe — enforce a single global lock order, or better, swap to a `BlockingQueue` that removes the need for manual locking entirely.
