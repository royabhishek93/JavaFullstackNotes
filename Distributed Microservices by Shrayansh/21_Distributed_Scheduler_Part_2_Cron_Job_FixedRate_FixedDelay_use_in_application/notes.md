# Distributed Scheduler Part 2 — Cron Job, FixedRate & FixedDelay in Spring Boot

## What is this? (Plain English)

Think of three different ways a manager could ask an employee to file a recurring report:
- **"File a report every 5 minutes, starting from when you began your shift"** — that's **fixedRate**: the clock ticks based on *when the previous report started*, no matter how long writing it took.
- **"Wait 5 minutes after you finish one report before starting the next"** — that's **fixedDelay**: the clock only starts counting once the previous work is actually *done*.
- **"File a report at the top of every hour, on the wall clock, no matter what"** — that's a **cron job**: it follows an actual wall-clock schedule (like an alarm clock ringing at :00, :10, :20...), not a countdown relative to the last report.

Spring Boot doesn't invent any new scheduling engine for these — it's just a thin wrapper (`@Scheduled` + `@EnableScheduling`) around the exact same `ScheduledThreadPoolExecutor` internals covered in Part 1 (`schedule()`, `scheduleAtFixedRate()`, `scheduleWithFixedDelay()`). If you understood how the single-threaded delay queue picks up and re-queues tasks in Part 1, cron jobs in Spring Boot are just "the same re-queueing mechanism, but the next-execution-time formula is computed from the wall clock instead of from the previous start/finish time."

## The Problem It Solves

Given a recurring task, you need to answer: **"when exactly does the next run happen, especially if a run takes longer than the interval between runs?"** The three scheduling styles answer this differently:

- **fixedRate**: next run = *previous start time* + interval. It doesn't care how long the task took — it just keeps ticking off intervals from the last start. (Because the underlying executor is single-threaded/single-task-in-queue, an overrunning task still delays the *next* pickup even though the "ideal" next-run time may have already passed — the next execution isn't run in parallel.)
- **fixedDelay**: next run = *previous finish time* + interval. This guarantees a "cool-down gap" between the end of one run and the start of the next — useful when back-to-back execution could overload a downstream system.
- **cron**: next run = *next matching wall-clock tick* (e.g. every 10th minute: :00, :10, :20...) — completely independent of when the previous run started or finished. If a run takes so long that it overruns one or more ticks, those ticks are simply **skipped** (missed), and the task re-queues itself for the *next future tick* after it finishes.

## Timing Diagram — FixedRate vs FixedDelay vs Cron (task runs longer than its interval)

> Note: the original diagram here was a Mermaid `gantt` chart (not one of the standard flowchart/state/sequence/class/ER types) — converted to an equivalent timeline table below, preserving every run label and timestamp.

```
FixedRate (interval = 3s, formula: next = prevStart + interval)
  Run1: 10:00 -> 10:04  (takes 4min, overruns the 3s interval)
  Run2: ideal tick was 10:03 (missed, queued right after Run1) -> runs 10:04 to 10:08
  Run3: ideal tick was 10:06 (missed again, same pattern)      -> runs 10:08 to 10:12

FixedDelay (interval = 3s AFTER finish, formula: next = prevFinish + interval)
  Run1: 10:00 -> 10:04  (takes 4min, finishes 10:04)
  Run2: starts at finish(10:04) + 3 = 10:07 -> 10:11
  Run3: starts at finish(10:11) + 3 = 10:14 -> 10:18

Cron (every 10 min wall clock: :00 :10 :20 :30..., task takes 25 min)
  Run1: 10:00 -> 10:25  (task overruns; 10:10 and 10:20 ticks are MISSED)
  Run2: next wall-clock tick after finish(10:25) is 10:30 -> 10:55
```
*(Full Mermaid source: see [mermaid-diagrams.md](mermaid-diagrams.md))*

Key takeaway from the diagram: **fixedRate and fixedDelay both "drift" relative to a fixed origin** once a task overruns (because there's only ever one task instance queued at a time — no parallel re-entry). **Cron never drifts** — it always re-aligns to the next real wall-clock tick, but it can *skip* ticks entirely if the task runs long.

## Key Code / Config

### 0. Prerequisite — enable scheduling

```java
@SpringBootApplication
@EnableScheduling // required: scans for @Scheduled annotations and loads scheduler beans.
public class SchedulerDemoApplication {
    public static void main(String[] args) {
        SpringApplication.run(SchedulerDemoApplication.class, args);
    }
}
```
Without `@EnableScheduling`, Spring Boot never scans for `@Scheduled` methods — they simply won't run.

### 1. Fixed Rate

```java
@Component
public class FixedRateTask {

    // Internally wraps ScheduledThreadPoolExecutor#scheduleAtFixedRate.
    // initialDelay: wait 3s after app startup before the first run (default is 0 if omitted).
    // fixedRate: next run = previous START time + 5000ms, regardless of how long the task took.
    @Scheduled(initialDelay = 3000, fixedRate = 5000)
    public void run() {
        System.out.println("FixedRate task executed at: " + LocalTime.now());
    }
}
```
Example observed output: app starts at `:38` → first run at `:41` (3s initial delay) → next run `41 + 5 = :46` → `46 + 5 = :51` → `51 + 5 = :56` ...

### 2. Fixed Delay

```java
@Component
public class FixedDelayTask {

    // Internally wraps ScheduledThreadPoolExecutor#scheduleWithFixedDelay.
    // initialDelay: 1s after startup before the first run (default 0 if omitted).
    // fixedDelay: next run = previous FINISH time + 5000ms.
    @Scheduled(initialDelay = 1000, fixedDelay = 5000)
    public void run() {
        long start = System.currentTimeMillis();
        try {
            Thread.sleep(3000); // simulate work
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
        long end = System.currentTimeMillis();
        System.out.println("Started: " + start + ", Finished: " + end);
    }
}
```
Example observed output: app starts at `:31` → first run starts `:32` (1s initial delay), sleeps 3s → finishes `:35` → next run starts `35 + 5 = :40`, finishes `:43` → next run starts `43 + 5 = :48` ...

### 3. One-Time Scheduling

The one-time equivalent of the plain `schedule()` method from Part 1 (not a repeating `@Scheduled` mode — Spring's repeating annotation always needs `fixedRate`/`fixedDelay`/`cron`). It runs exactly once, after a mandatory initial delay:

```java
@Component
public class OneTimeTask {

    @Autowired
    private TaskScheduler taskScheduler;

    public void scheduleOnce(long initialDelayMillis) {
        // initialDelay is mandatory here — omitting it throws an exception,
        // unlike fixedRate/fixedDelay where it silently defaults to 0.
        taskScheduler.schedule(this::run, Instant.now().plusMillis(initialDelayMillis));
    }

    public void run() {
        System.out.println("One-time task executed at: " + LocalTime.now());
    }
}
```
Pass `0` to run immediately, or e.g. `2000` to run once after 2 seconds.

### 4. Cron Job

```java
@Component
public class CronTask {

    // Runs every 3 seconds (six-part cron: second minute hour day-of-month month day-of-week).
    @Scheduled(cron = "*/3 * * * * *")
    public void run() {
        System.out.println("Cron task executed at: " + LocalTime.now());
    }
}
```
Example observed output ticks: `:12`, `:15`, `:18`, `:21` ...

## Cron Expression Syntax

A Spring cron expression has **six space-separated fields**:

| Field | Allowed values |
|---|---|
| Second | 0–59 |
| Minute | 0–59 |
| Hour | 0–23 |
| Day of month | 1–31 |
| Month | 1–12 or `JAN`–`DEC` |
| Day of week | 0–7 (both `0` and `7` = Sunday, `1`=Monday ... `6`=Saturday) or `SUN`–`SAT` |

### Special characters

| Symbol | Meaning | Example |
|---|---|---|
| `*` | "every" — matches every value in that field | `* * * * * *` → every second |
| `,` | list — specific multiple values | `0,20 * * * * *` → run only at second 0 and second 20 |
| `-` | range | `9-15` in the hour field → every hour from 9 a.m. to 3 p.m. inclusive |
| `/` | step (`start/step`) | `4/10` in the second field → start at second 4, then every 10s: 4,14,24,34,44,54 |
| `L` | "last" — only valid in day-of-month or day-of-week | `L` in day-of-month → last day of that month (28/29/30/31 depending on month); `FRI L`/day+`L` → last occurrence of that weekday in the month |
| `?` | "no specific value" — ignore this field; only valid in day-of-month or day-of-week | Used to remove ambiguity when the other of the two day-fields is meaningfully constrained |

### Why `?` exists — the ambiguity problem

If you set day-of-month to `*` (every day) **and** day-of-week to `MON`, it's ambiguous: does it mean "every day, but only if it's Monday" or something else? The fix is to explicitly say "ignore" one of the two day fields with `?`. Example: *"every weekday at 9 a.m."* → set day-of-month to `?` (ignored) and day-of-week to `MON-FRI`, so only the weekday field constrains execution.

### Practical examples

| Requirement | Cron expression | Reasoning |
|---|---|---|
| Every 5 seconds | `*/5 * * * * *` | step of 5 in the second field: 0,5,10,15... |
| Every 4 minutes | `0 */4 * * * *` | step of 4 in the minute field: 0,4,8,12... |
| Every day at 11:15 a.m. | `0 15 11 * * *` | second=0, minute=15, hour=11, every day |
| Every weekday at 9:00 a.m. | `0 0 9 ? * MON-FRI` | day-of-month ignored (`?`), day-of-week restricted to Mon–Fri |
| Every Sunday at midnight | `0 0 0 ? * SUN` | day-of-month ignored, day-of-week = Sunday, time = 00:00:00 |
| Runs at midnight on the first day of every month | `0 0 0 1 * ?` | day-of-month = 1, day-of-week ignored |
| Last day of every month at midnight | `0 0 0 L * ?` | day-of-month = `L` (last day, adapts to 28/29/30/31), day-of-week ignored |

## Wall-Clock Behavior — Worked Example

Requirement: cron job every 10 minutes, wall-clock ticks are `:00 :10 :20 :30 :40 :50`. Task starts at `10:10` and takes 25 minutes to run:

1. `10:10` — task starts (this tick is consumed).
2. `10:10` (still running) — nothing happens; there's only one task instance in the queue, so the timer occurring while the task is already running is simply missed (it doesn't spawn a second concurrent run).
3. `10:20` — tick occurs, but task is still running → **missed**.
4. `10:25` — task finishes. Now the next execution time must be recomputed: the next *future* wall-clock tick after `10:25` is `10:30` (the `10:10` and `10:20` ticks are gone forever — cron does not "catch up" on missed ticks).
5. `10:30` — task is picked up and runs again.

This contrasts with fixedRate/fixedDelay, where the next-run time is always computed relative to the *previous run itself* (start or finish time) rather than an absolute wall-clock grid — so those two never "skip" a tick, they just drift later and later.

## Important Concepts

- **`@EnableScheduling`**: Mandatory annotation that turns on scanning for `@Scheduled` methods and loads the scheduler infrastructure beans.
- **Spring Boot adds no new engine**: `@Scheduled(fixedRate=...)`, `@Scheduled(fixedDelay=...)`, and `@Scheduled(cron=...)` are thin wrappers over `ScheduledThreadPoolExecutor#scheduleAtFixedRate`, `#scheduleWithFixedDelay`, and a cron-aware re-queueing loop, respectively (all covered internally in Part 1).
- **fixedRate formula**: next execution = previous **start** time + interval.
- **fixedDelay formula**: next execution = previous **finish** time + interval.
- **cron formula**: next execution = next matching **wall-clock tick**, independent of previous start/finish — missed ticks during a long-running task are skipped, not queued up.
- **Single task in the queue**: same as Part 1 — there's only ever one instance of a given scheduled task in the delay queue; it's re-queued with a newly computed execution time only after it completes, so overlapping/concurrent runs of the same task never happen.
- **`?` (no-value) wildcard**: only valid in day-of-month/day-of-week, exists specifically to resolve ambiguity when only one of those two fields should constrain the schedule.
- **`L` (last)**: only valid in day-of-month (last day of that month) or day-of-week (last occurrence of a weekday in the month).

## Interview Q&A

**Q1: What's the exact formula difference between `fixedRate` and `fixedDelay`, and why does it matter?**
A: `fixedRate`'s next execution = previous **start** time + interval; `fixedDelay`'s next execution = previous **finish** time + interval. It matters because with `fixedRate`, a slow task doesn't get extra breathing room before the next one is due (it can only ever run one instance at a time regardless, but the "ideal" next tick keeps moving forward at a fixed cadence from start times). `fixedDelay` guarantees a real cool-down gap after the task actually finishes — useful when you need the downstream system to rest before being hit again.

**Q2: If a `@Scheduled` cron task takes longer than the cron interval, do missed ticks queue up and fire back-to-back once the task finishes?**
A: No. Cron scheduling recomputes the *next future* wall-clock tick after the task finishes — any ticks that occurred while the task was still running are simply skipped/lost, not queued or batched. E.g. every-10-minute cron, task runs 10:10–10:25, the next run is 10:30, not a rapid-fire replay of 10:10/10:20.

**Q3: Why is `initialDelay` mandatory for one-time scheduling but optional (defaulting to 0) for `fixedRate`/`fixedDelay`?**
A: For repeating schedules, an omitted `initialDelay` has an unambiguous, safe default: start immediately (0ms) and then repeat. A pure one-time task has no repeat semantics to fall back on, so Spring requires you to be explicit about when it should fire — hence it throws an exception if `initialDelay` isn't provided.

**Q4: What do `0` and `7` both mean in the day-of-week cron field, and why does that range go 0–7 for only 7 days?**
A: Both `0` and `7` represent Sunday (the field supports two representations for Sunday to accommodate both 0-indexed and "end of week" conventions); `1`–`6` map to Monday–Saturday.

**Q5: Why does Spring's cron syntax need a `?` character when `*` already means "every value"?**
A: `?` isn't "every value," it means "no specific value / ignore this field." It's needed to break ambiguity between day-of-month and day-of-week, since a cron expression can only meaningfully constrain execution by *one* of those two day-related fields at a time. E.g. "every weekday at 9am" only makes sense if day-of-month is explicitly ignored (`?`) while day-of-week carries the real constraint (`MON-FRI`) — using `*` for day-of-month there would be misleading about intent even though it happens to also match every day.
