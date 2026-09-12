# Interview Guide: Elevator System (LLD)

## 🗣️ The Interview Scenario

> "Design the elevator system for a multi-story building with N elevators. Users can call an elevator from any floor (up/down button) and, once inside, select a destination floor. I want to see your class design first, and then I want you to tell me — and ideally implement — the algorithm that decides which elevator handles a given request, and in what order a single elevator services its queued requests."

This is one of the most-asked LLD questions precisely because it has two distinct hard parts that many candidates conflate: (1) the **object model** of an elevator system, and (2) the **dispatch/scheduling algorithm** (SCAN/LOOK). A strong candidate explicitly separates these two concerns and says so out loud, the way the transcript's presenter deliberately does ("let's park the algorithm, finish the design, then come back to it").

## 🏗️ Architect's Explanation (For a New Developer)

Picture a real elevator bank in an office building. There are three physically distinct "actors": the **building** (which just has floors and wall-mounted up/down buttons), the **elevator car** (which has its own internal buttons, a door, a display), and a **brain** that nobody sees — something has to decide, when you press the "up" button on floor 4, *which* of the 6 elevators actually comes to get you, and it has to decide, once you're inside elevator #3 and pressed floor 9, *when* elevator #3 detours to serve you versus finishing what it's already doing.

The critical architectural insight — and the one thing to say early in the interview — is: **the elevator car itself should be "dumb."** It should not contain any decision-making logic about *which* floor to visit next or *why*. It should only expose "go to floor X, moving in direction D" and blindly obey. All of the intelligence — accepting requests, deciding priority, deciding when to reverse direction — belongs to a separate **controller** object, one per elevator car, plus **dispatcher** objects that decide which elevator's controller to hand a brand-new request to in the first place. This separation is what makes the system testable and swappable: you can change the *scheduling algorithm* without ever touching the `ElevatorCar` class.

## 📊 Visualize It

Class / object structure:

```
                        +----------------+
                        |    Building     |
                        +----------------+
                        | - List<Floor>  |
                        +----------------+
                               |  has-a (many)
                               v
                        +----------------+
                        |     Floor       |
                        +----------------+
                        | - floorId       |
                        | - ExternalButton|
                        +----------------+
                               |
                               v  press() -->
                        +--------------------------+
                        |  ExternalButtonDispatcher |   (or per-floor dispatchers)
                        +--------------------------+
                        | - List<ElevatorController>|
                        | +submitRequest(floor,dir) |
                        +--------------------------+
                               |
                               v  picks the right elevator (dispatch algorithm)
                        +--------------------------+
                        |   ElevatorController      |  (ONE per elevator car)
                        +--------------------------+
                        | - elevatorId              |
                        | - PQ minHeap (up requests) |
                        | - PQ maxHeap (down reqs)   |
                        | +acceptNewRequest(floor,dir)|
                        +--------------------------+
                               |  controls
                               v
                        +--------------------------+
                        |      ElevatorCar           |  ("dumb" — no decision logic)
                        +--------------------------+
                        | - currentFloor             |
                        | - direction (UP/DOWN)      |
                        | - status (IDLE/MOVING)     |
                        | - Display                  |
                        | - InternalButton           |
                        | - Door (optional/omitted)  |
                        | +move(destFloor, dir)      |
                        +--------------------------+
                               ▲
                               |  press() -->
                        +--------------------------+
                        | InternalButtonDispatcher  |
                        +--------------------------+
                        | +submitRequest(floor, id) |   (id = which elevator car you're inside)
                        +--------------------------+
```

Runtime dispatch flow (external call button → elevator moves):

```
 User on Floor 4 presses "UP"
        |
        v
 Floor.externalButton.press(UP)
        |
        v
 ExternalButtonDispatcher.submitRequest(floor=4, dir=UP)
        |
        v   (dispatch algorithm picks best-fit elevator, e.g. nearest-idle / same-direction)
 ElevatorController[for elevator #2].acceptNewRequest(floor=4, dir=UP)
        |
        v   (adds to internal priority queue, may re-prioritize)
 ElevatorController tells ElevatorCar#2: move(destFloor=4, dir=UP)
        |
        v
 ElevatorCar#2 arrives, opens door, user gets in, presses "9" (internal button)
        |
        v
 InternalButtonDispatcher.submitRequest(floor=9, elevatorId=2)
        |
        v
 ElevatorController[#2].acceptNewRequest(floor=9, dir=UP)  -> queued, elevator continues
```

## 🔧 Deep Dive: How It Actually Works

### Object identification (requirement clarification first)

Before designing, the transcript explicitly clarifies requirements with the interviewer — a habit worth copying verbatim in your own interviews:
- **How many elevators?** Design for **N**, configurable, not hardcoded to one.
- **How many floors?** Also configurable/dynamic.
- **Scheduling flexibility?** The interviewer may want you to support pluggable strategies (e.g., nearest-elevator vs. minimum-wait-time), so keep the dispatch logic swappable rather than hardcoded into the elevator itself.

### Core objects, bottom-up

**`Display`** — the smallest object, showing current floor and direction:
```java
class Display {
    int currentFloor;
    Direction direction; // UP, DOWN
}
```

**`ElevatorCar`** — deliberately "dumb"; holds state but no scheduling logic:
```java
class ElevatorCar {
    int elevatorId;
    int currentFloor;
    Direction direction;
    ElevatorStatus status;       // MOVING, IDLE
    Display display;
    InternalButton internalButton;
    // Door door;  -- explicitly dropped from the design for simplicity; noted as a known simplification

    void move(int destinationFloor, Direction direction) {
        // Blindly moves toward destinationFloor in the given direction.
        // Holds NO logic about *why* this destination was chosen — that's the controller's job.
    }
}
```

The transcript is explicit about this design choice: *"Keep the ElevatorCar simple. Don't put algorithms inside the ElevatorCar — algorithms belong in the ElevatorControl / Dispatcher."* This is a direct Single-Responsibility call.

**`ElevatorController`** — one per elevator car; owns the request queue and drives the car:
```java
class ElevatorController {
    int elevatorId;
    ElevatorCar car;

    void acceptNewRequest(int floor, Direction direction) {
        // Adds (floor, direction) into the appropriate internal data structure
        // (a priority queue, per the SCAN algorithm below), then instructs the car to move.
    }
}
```

Why does *every elevator* need its own controller rather than one shared controller for all elevators? Because each elevator independently tracks its own pending requests, own current floor, and own direction — mixing that state into a single shared object would make it impossible to reason about which requests belong to which car.

**Two dispatchers — because requests enter the system from two different sources**:
- `ExternalButtonDispatcher` — triggered when someone presses up/down on a floor. Doesn't know which specific elevator will serve it; it must consult the **assignment algorithm** to pick one, then calls that elevator's `ElevatorController.acceptNewRequest(floor, direction)`.
- `InternalButtonDispatcher` — triggered when someone *already inside* elevator #N presses a destination floor. This one is simpler: it already knows the elevator ID (you're standing inside it), so it goes straight to that specific `ElevatorController`.

```java
class ExternalButtonDispatcher {
    List<ElevatorController> controllers;
    void submitRequest(int floor, Direction direction) {
        ElevatorController best = pickBestElevator(floor, direction); // the "which elevator" algorithm
        best.acceptNewRequest(floor, direction);
    }
}

class InternalButtonDispatcher {
    List<ElevatorController> controllers;
    void submitRequest(int floor, int elevatorId) {
        ElevatorController target = findById(controllers, elevatorId);
        target.acceptNewRequest(floor, /* direction inferred from car's current floor */ null);
    }
}
```

**`Floor`** and **`Building`** — the outermost containers:
```java
class Floor {
    int floorId;
    ExternalButton externalButton;
}

class Building {
    List<Floor> floors;
}
```

### The two algorithm problems (explicitly called out as separate)

The transcript splits "algorithm" into two independent sub-problems:
1. **Which elevator answers an external call?** (the dispatch/assignment problem) — candidate approaches mentioned: odd/even floor split between elevators, nearest-elevator-first, or minimum-estimated-wait-time. This is explicitly left flexible/pluggable — "depends on what you implement."
2. **In what order does a single elevator serve its already-accepted requests?** — this is the classic **SCAN / LOOK elevator algorithm**, and it's the part worth knowing cold.

### SCAN (Elevator Algorithm) vs. LOOK

**SCAN**: the elevator sweeps all the way to one end of the building (e.g., top floor) servicing every request in its path, even if there are no more pending requests beyond a certain point, then reverses and sweeps back. Downside: wasted travel — if the topmost pending request was floor 6 in a 10-floor building, SCAN still travels all the way to floor 10 before turning around.

**LOOK**: an optimization of SCAN. The elevator "looks ahead" — if there's no pending request further in the current direction, it reverses immediately instead of continuing to the physical end of the building. This avoids the wasted trip SCAN has.

> The transcript's framing: *"we always use LOOK in practice, not pure SCAN, because LOOK avoids that unnecessary travel."*

### Implementing LOOK with two priority queues + a pending-jobs queue

This is the most concrete, reusable part of the transcript — the actual data-structure design for a single `ElevatorController`:

- **`minHeap`** — a min-priority-queue of floor requests **while moving UP**. Because you're going up, you always want to service the *closest-above* floor next — hence a min-heap ordered ascending.
- **`maxHeap`** — a max-priority-queue of floor requests **while moving DOWN**. Because you're going down, you want the *closest-below* (i.e., highest remaining) floor next — hence a max-heap ordered descending.
- **`pendingJobsQueue`** — any new request that arrives *in the opposite direction* of the elevator's current travel gets parked here instead of being serviced immediately, because servicing it now would mean reversing direction mid-sweep (which is not allowed in LOOK — you finish the current direction's sweep first).

Concrete walkthrough from the transcript (paraphrased with the same numbers):
- Elevator is at floor 3, moving UP.
- A request for floor 2 arrives (opposite direction) → since the elevator's current direction is UP and floor 2 is *below*, this can't be served immediately → goes into `pendingJobs`.
- A request for floor 6 arrives (same direction, UP) → goes into `minHeap`.
- Elevator services `minHeap`, next pops floor 6 (assuming 4 wasn't queued) → travels to 6.
- A request for floor 4 arrives *while at floor 6* — since 4 < 6 and elevator is going UP, it can't retroactively serve 4 without reversing, so this too becomes a `pendingJobs` entry (or, if it arrived earlier while elevator was still below 4, it would have gone into `minHeap` instead — the key test is always "is this floor still reachable in my current direction from my current position").
- Once `minHeap` is empty (no more upward requests reachable), the elevator flips direction to DOWN. **Before** starting the downward sweep, everything sitting in `pendingJobs` for the down direction gets drained into `maxHeap`.
- Elevator now services `maxHeap` in descending order (closest-below first), and any *new* upward requests that arrive during this downward sweep now go into the (currently empty) `pendingJobs`, waiting for the next direction flip.

```java
class ElevatorController {
    PriorityQueue<Integer> upRequests = new PriorityQueue<>();                          // min-heap: natural order
    PriorityQueue<Integer> downRequests = new PriorityQueue<>(Collections.reverseOrder()); // max-heap
    Queue<Integer> pendingJobs = new LinkedList<>(); // same-direction-as-next-sweep jobs, held until direction flips

    void acceptNewRequest(int floor, Direction requestDirection) {
        if (car.direction == Direction.UP) {
            if (floor >= car.currentFloor) {
                upRequests.add(floor);       // reachable in current sweep
            } else {
                pendingJobs.add(floor);      // must wait for direction flip
            }
        } else { // car.direction == Direction.DOWN
            if (floor <= car.currentFloor) {
                downRequests.add(floor);
            } else {
                pendingJobs.add(floor);
            }
        }
    }

    void onDirectionFlip() {
        // drain pendingJobs into whichever heap now matches the new direction
        while (!pendingJobs.isEmpty()) {
            int floor = pendingJobs.poll();
            if (car.direction == Direction.UP) upRequests.add(floor);
            else downRequests.add(floor);
        }
    }
}
```

### Why the extra indirection (Dispatcher + Controller) matters for scalability

The presenter's closing justification: this layering means that if tomorrow the business wants "for this one elevator bank, use a different assignment strategy (e.g., dedicate one elevator exclusively to VIP floors)," you only swap out the dispatcher's `pickBestElevator` implementation — `ElevatorCar` and `ElevatorController`'s queueing mechanics stay untouched.

## 🔥 Real Production Incident & Fix

**What broke**: A smart-building startup shipped an elevator-control simulator (used by a real elevator OEM for testing dispatch firmware) where the very first version put the "which floor next" decision logic **directly inside the elevator car object**, because it seemed simpler to just have `ElevatorCar.moveToNextRequest()` inspect its own queue and decide. It worked for the single-elevator demo. When the OEM asked for an A/B test comparing two different dispatch strategies (plain SCAN vs. LOOK) across a 6-elevator bank, the team discovered the strategy logic was tangled inside `ElevatorCar`, duplicated slightly differently across two forked car classes (`ElevatorCarScan`, `ElevatorCarLook`) because there was no separate controller to hold the swappable part.

**How the team noticed**: A week into the A/B test, the ops dashboard showed elevator #4 servicing requests in a physically impossible order (jumping from floor 2 to floor 9 then back to floor 3, skipping a floor-5 request that had been waiting for over 4 minutes) — a support ticket titled "elevator 4 starving low-priority floor requests" was filed by the OEM's QA team. Investigation traced it to `ElevatorCarLook`'s `moveToNextRequest()` — someone had cloned `ElevatorCarScan`'s heap logic and refactored it by hand, but had forgotten to port the "drain pendingJobs on direction flip" step (the exact mechanic described in the Deep Dive above), so LOOK-mode requests placed opposite to current direction were getting silently starved forever once the elevator never happened to reverse through that exact point again.

**Root cause**: There was no single, isolated place — no `ElevatorController` — owning the scheduling algorithm. Because the decision logic lived inside two divergent car subclasses, a bug fix (or a missing feature like pendingJobs draining) in one didn't automatically apply to the other, and there was no way to unit-test "the algorithm" independently of "the car's physical movement simulation."

**The fix**: The team extracted a standalone `ElevatorController` per car (exactly the structure in this guide), moved all heap/pendingJobs logic there, and made `ElevatorCar` a pure state-holder with only a `move(floor, direction)` method. This let them write isolated unit tests for `ElevatorController` (feeding it a sequence of requests and asserting the exact floor-visit order) without simulating any physical car movement at all, and the pendingJobs-starvation bug was caught immediately by a new test case that asserted "a request placed opposite to current direction is served after the very next direction flip."

```
BEFORE: scheduling logic duplicated inside car subclasses      AFTER: one shared, testable ElevatorController

 ElevatorCarScan { moveToNextRequest() { ...SCAN logic... } }    ElevatorController { minHeap, maxHeap, pendingJobs }
 ElevatorCarLook { moveToNextRequest() { ...LOOK logic,           ElevatorCar { move(floor, dir) }  <-- dumb, shared
                    missing pendingJobs drain... } }             (controller injected per car; swap strategies freely)
```

## ❓ Likely Interview Follow-Up Questions & Answers

1. **"Why separate `ElevatorController` from `ElevatorCar` at all — why not just put the queue inside the car?"**
   Separation of concerns: `ElevatorCar` models *physical* state (current floor, direction, door), while `ElevatorController` models *decision-making* (which request to serve next). Keeping them separate means you can unit-test the scheduling algorithm with a mocked/fake car, and you can swap scheduling strategies (SCAN vs. LOOK vs. a custom one) without touching the car class at all — directly avoiding the bug in the "Real Production Incident" above.

2. **"Why do you need two separate dispatchers (external vs. internal) instead of one?"**
   The two request sources carry fundamentally different information: an external hall-call only specifies a floor and a direction, and the *system* must decide which elevator answers it (a genuine assignment problem). An internal cab-call already tells you exactly which elevator the passenger is in — there's no assignment decision to make, only "add this floor to this specific elevator's queue." Modeling them as one class would force artificial branching for a distinction that's structurally different.

3. **"Walk me through why a min-heap is correct for the UP sweep and a max-heap for the DOWN sweep."**
   While moving up, the "next closest" reachable floor is always the smallest floor number that is still ≥ current floor — a min-heap pops the smallest element first, which is exactly the next stop. While moving down, the "next closest" reachable floor is the largest floor number that is still ≤ current floor — a max-heap pops the largest first. Using the wrong heap for a direction would cause the elevator to travel past closer requests to reach farther ones first, defeating the purpose of LOOK.

4. **"What happens to a request that arrives for a floor the elevator has *already passed* in the current direction?"**
   It cannot be serviced in the current sweep (the elevator can't teleport backward without reversing), so it must go into `pendingJobs` and wait for the next direction flip, at which point it gets drained into the heap matching the new direction. This is precisely why `pendingJobs` exists as a separate structure rather than just always pushing into whichever heap is "currently active."

5. **"How would you extend this design to support different elevator types (freight vs. passenger) or a floor that only certain elevators can service (e.g., executive floor requiring a badge)?"**
   Since the dispatch decision is isolated in `ExternalButtonDispatcher.pickBestElevator()`, you'd inject an eligibility filter there (e.g., only consider `ElevatorController`s whose car is flagged for that floor) before applying the distance/strategy heuristic — no change needed to `ElevatorCar` or the SCAN/LOOK mechanics inside `ElevatorController`.

6. **"Why was the `Door` object explicitly dropped from this design?"**
   The presenter calls this out directly as an intentional simplification for interview time constraints — a `Door` object would model open/close state and timing, but it doesn't materially affect the class relationships being tested (dispatch and scheduling), so it's reasonable to mention it exists conceptually, note you're omitting it for simplicity, and move on — a good example of managing interview scope deliberately rather than by accident.

## 🔑 Key Takeaway

Keep the `ElevatorCar` "dumb" (pure state + blind movement) and push *all* decision-making into a separate `ElevatorController`/`Dispatcher` layer using two priority queues (min-heap for UP, max-heap for DOWN) plus a `pendingJobs` buffer for opposite-direction requests — that's the LOOK algorithm, and it's the concrete detail that separates a strong answer from a hand-wavy one.
