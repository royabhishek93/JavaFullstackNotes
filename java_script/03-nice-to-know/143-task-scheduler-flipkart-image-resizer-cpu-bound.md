# Flipkart Image Resizer — Controlling CPU-Bound Concurrency
> **Topic:** Task Scheduler | **Level:** Intermediate | **Frequency:** Medium

## The Setup

Flipkart product uploads require generating 4 thumbnail sizes per image. 500 images arrive simultaneously. The image resizing library is CPU-bound and saturates the CPU at 4 concurrent resizes. This scenario tests whether the candidate understands the difference between I/O concurrency (DB connections, network) and CPU concurrency (compute-bound tasks), and whether they scope the scheduler correctly.

## The Question

"Flipkart product uploads need to generate 4 thumbnail sizes per image. 500 images arrive simultaneously. The image resizing library saturates the CPU at 4 concurrent resizes. How do you cap total concurrency at 4, not just 4 per upload?"

## Diagram

```
WRONG SCOPE (per-upload scheduler):
=====================================
  Upload 1: new TaskScheduler(4) → 4 resizes
  Upload 2: new TaskScheduler(4) → 4 resizes
  ...
  Upload 500: new TaskScheduler(4) → 4 resizes
  Total simultaneous resizes: 500 × 4 = 2000  ← CPU thrashes

CORRECT SCOPE (shared scheduler):
===================================
  const imageScheduler = new TaskScheduler(4)  ← one shared instance

  Upload 1: 4 tasks → imageScheduler
  Upload 2: 4 tasks → imageScheduler
  Upload 500: 4 tasks → imageScheduler
  Total tasks queued: 2000
  Total running at any moment: 4  ← CPU stays calm
```

## Model Answer (15 YOE)

```js
// Shared scheduler — created ONCE at module/service level
const imageScheduler = new TaskScheduler(4);  // CPU limit, not I/O limit

async function processUpload(imageBuffer, productId) {
  const sizes = [64, 128, 256, 512];

  // schedule all 4 resizes — but globally, at most 4 total run simultaneously
  const thumbnails = await Promise.all(
    sizes.map(size =>
      imageScheduler.addTask(() => resizeImage(imageBuffer, size))
    )
  );

  await saveThumbnails(productId, thumbnails);
}

// 500 uploads call processUpload concurrently
// Each spawns 4 resize tasks = 2000 tasks total
// imageScheduler ensures only 4 resizes run simultaneously at any time
await Promise.all(uploads.map(upload => processUpload(upload.buffer, upload.id)));
```

The key insight: the scheduler is shared across all upload calls. It limits total concurrency of the shared resource (CPU), not per-upload concurrency. A per-upload scheduler would only limit concurrency within one upload — 500 uploads with per-upload `concurrency=4` gives 2,000 simultaneous resizes.

**I/O vs CPU concurrency limits:**

| Bottleneck | Limiting factor | Typical limit |
|---|---|---|
| DB connection pool | Pool size | Pool size − headroom (e.g. 15 of 20) |
| External API | Rate limit (req/s) | API docs |
| CPU-bound (image resize, crypto) | CPU cores | Number of cores (e.g. 4 on a 4-core machine) |
| Memory-bound | Available RAM | Depends on per-task memory footprint |

For CPU-bound tasks, setting `concurrency` above the number of physical cores does not help — it just causes context-switching overhead with no throughput gain.

## Follow-up

**Q:** "If the image resizer is in a separate worker thread or child process, does the concurrency limit change?"

**A:** Yes. If resizing happens in worker threads (`worker_threads` module), the main thread is not blocked. You can set `concurrency` equal to the number of worker threads in the pool. The scheduler still limits how many resize jobs are in-flight, but the bottleneck is now thread availability, not main-thread CPU.

**Q:** "Why does one upload's `Promise.all` not resolve until all 4 of its resizes complete, even if they're spread across many scheduler cycles?"

**A:** Each `imageScheduler.addTask(...)` returns a Promise. `Promise.all` waits for all 4 Promises to settle. Those Promises settle whenever the resize tasks actually run — which may be delayed by the queue. The upload function pauses at `await Promise.all(...)` until all 4 thumbnails are done, regardless of how long they waited in the queue.
