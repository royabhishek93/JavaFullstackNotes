# Debounce vs Throttle — Define Both and Draw a Timeline
> **Topic:** Debounce & Throttle | **Level:** Fundamental | **Frequency:** High

## The Setup
A front-end technical phone screen. You are 10 minutes in. The interviewer says: "Before we get to code, just talk me through debounce and throttle — what are they and when do you reach for each?" This is the gateway question: if you conflate them, the rest of the interview goes poorly.

## The Question
Define debounce and throttle. What problem does each solve? Draw a timeline showing how each handles a burst of events arriving roughly every 100ms over a 1-second window, with a 300ms window applied.

## Diagram

```
EVENTS ARRIVING OVER TIME
t=0   t=100 t=200 t=300 t=400 t=500 t=600 t=700 t=800 t=900 t=1000
 |     |     |     |     |            |     |           |
 E     E     E     E     E            E     E           E
 (user typing rapidly)       (pause)  (burst)           (lone event)

──────────────────────────────────────────────────────────────────────

DEBOUNCE (wait=300ms — resets on each event)
 E     E     E     E     E            E     E           E
                                 ↑                 ↑         ↑
                            fired at            fired at  fired at
                             t=750              t=1050     t=1300
  [every new E pushes the fire point 300ms into the future]
  [only fires when there is a 300ms gap of silence]

──────────────────────────────────────────────────────────────────────

THROTTLE (limit=300ms — timer NOT reset by events)
 E     E     E     E     E            E     E           E
 ↑                 ↑                  ↑                  ↑
fired             fired              fired              fired
t=0              t=300              t=600              t=900
  [fires at t=0, gate closes until t=300, next event after t=300 fires]
  [intermediate events E at t=100,200,400 are silently dropped]

──────────────────────────────────────────────────────────────────────

KEY DIFFERENCE:
  Debounce fire point MOVES RIGHT with each event.
  Throttle fire points are FIXED on the clock — events don't move them.
```

## Model Answer (15 YOE)

The browser fires events as fast as physics allows. Your job is not to stop events — it is to control how often your *code* reacts to them. Both debounce and throttle reduce execution frequency, but they solve different problems.

**Debounce** means: "I will act only after you stop talking." Every new event resets the wait timer. The function fires exactly once, after a gap of silence equal to the delay. The fire point is not anchored to the clock — it trails the last event by the delay window. If events keep coming, the function never fires. Debounce is for situations where you only care about the *final* state after activity settles: search input, auto-save, window resize recalculation.

**Throttle** means: "I will act at most once per interval, no matter how loud you shout." The first event fires immediately, then the gate closes for the window duration. Subsequent events within the window are silently dropped. The fire points are anchored to the clock, not to event timing. Throttle is for continuous events where intermediate states have meaning: scroll position, mouse coordinates, button click guards.

The confusion in interviews comes from people conflating "less often" with "the same thing." They are not. One fires at the *end* of activity. The other fires at a *controlled rate during* activity.

**Decision shortcut:**
- "I only care about the final value" → Debounce
- "I need updates during the activity" → Throttle
- "First click must feel instant, ignore the rest" → Throttle (or leading-edge debounce)

## Follow-up

**Q:** What is leading-edge vs trailing-edge debounce?
**A:** Trailing-edge (default) fires after the silence gap — the last event triggers it. Leading-edge fires on the *first* event in a burst and ignores subsequent events for the delay window. Use leading-edge for "Submit Payment" buttons: you want instant feedback on the first click, not a 3-second delay before anything happens.

**Q:** Can you combine debounce and throttle on the same handler?
**A:** Rarely needed, but possible: `debounce(throttle(fn, 100), 300)` throttles during bursts and then waits for silence. In practice, choose one — mixing them creates hard-to-debug timing behavior. If you need both rate-limiting during a burst and a guaranteed final call, use Lodash's `maxWait` option on debounce instead.
