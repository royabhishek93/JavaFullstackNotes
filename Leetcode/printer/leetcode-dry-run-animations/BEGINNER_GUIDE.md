# Beginner's Guide: LeetCode Code-Level Dry-Run Visualizers

## What Are These Visualizers?

These are **interactive step-by-step code execution animations** that show you exactly what happens when Java code runs. Unlike static code examples, these visualizers let you:

- 👀 **Watch** each line of code execute in real-time
- 📊 **See** how data structures change after every statement
- 🎯 **Understand** why the algorithm works through plain English explanations
- 🎮 **Control** the pace with play/pause and step-by-step buttons

Think of it as having a debugger that explains everything it's doing!

## How to Use

### Opening a Visualizer

1. Navigate to: `/Leetcode/printer/leetcode-dry-run-animations/`
2. Double-click any HTML file (e.g., `01-lc-146-lru-cache-dry-run.html`)
3. The page opens in your default web browser

### Understanding the Interface

```
┌─────────────────────────────────────────────────────────────┐
│ LC 146 LRU Cache | VISUAL CODE DRY RUN                      │
├─────────────────────────────────────────────────────────────┤
│ Step Pills: [1. Initialize] [2. put(1,1)] [3. get(1)]      │ ← Click any step
├────────────────────────┬────────────────────────────────────┤
│ Algorithm State        │ Full Java Code                      │
│ ─────────────────────  │ ──────────────────────────          │
│ list: [head ⇄ tail]   │ 1. class LRUCache {                 │
│ map: {}                │ 2.   class Node {                   │
│ capacity: 2            │ 3.     int key, value;              │ ← Highlighted line
│                        │ 4.     Node prev, next;             │   is executing
│                        │ ...                                 │
├────────────────────────┼────────────────────────────────────┤
│ What Changed?          │ Problem Statement                   │
│ ──────────────────     │ ─────────────────                   │
│ Created empty cache    │ Design an LRU cache...              │
│                        │                                     │
│ Why:                   │                                     │
│ HashMap + DLL gives    │                                     │
│ O(1) for both ops      │                                     │
└────────────────────────┴────────────────────────────────────┘
[Pause] [Previous] [Next] [Reset]                    Step 1/29
```

### Controls

| Button | Function |
|--------|----------|
| **Pause** | Stops auto-play (button becomes "Play" to resume) |
| **Previous** | Go back one step |
| **Next** | Advance one step |
| **Reset** | Jump back to step 1 |
| **Step Pills** | Click any pill to jump directly to that step |

## Reading the Visualizations

### 1. Algorithm State Panel (Top Left)

This shows the **actual data** in memory after each step executes:

**Example - LRU Cache:**
```
list: [head ⇄ 1(val:1) ⇄ 2(val:2) ⇄ tail]
map: {1 → node@1, 2 → node@2}
hot: node@1  ← Most recently used
```

**Example - Graph DFS:**
```
graph: {0:[1,2], 1:[3], 2:[3], 3:[]}
visited: {0, 1, 3}  ← Already explored
current: 2  ← Visiting now
path: [0, 1, 3, 2]
```

**Example - Sliding Window:**
```
Input: [1,3,-1,-3,5,3,6,7]
left: 2, right: 4
window: [-1, -3, 5]
current_max: 5
```

### 2. Full Java Code Panel (Top Right)

- **White text** = Not executing yet
- **Highlighted line** = Currently executing (yellow background)
- **Auto-scroll** = The highlighted line stays visible

The line numbers help you correlate state changes with specific code.

### 3. What Changed Panel (Bottom Left)

Two parts:

**"What Changed?"** - Plain English summary
```
Removed node(1) from old position and added to head
```

**"Why:"** - Algorithm invariant explanation
```
Most recently accessed item must be at head for O(1) access
```

This section answers: "Why did we just do that?"

### 4. Problem Statement Panel (Bottom Right)

The original LeetCode problem description for reference.

## Learning Workflows

### Workflow 1: First Time Seeing the Problem

1. **Read** the problem statement (bottom right)
2. **Scan** the full Java code (top right) - don't try to understand it yet
3. **Click "Next"** through each step slowly
4. **Watch** the "Algorithm State" change after each line
5. **Read** "What Changed?" to understand the action
6. **Read** "Why:" to understand the correctness proof
7. **Repeat** steps 3-6 until you reach the end

**Goal:** Build intuition for what the algorithm does

### Workflow 2: Testing Your Understanding

1. **Click a step** in the middle (e.g., step 15)
2. **Before clicking "Next"**, predict:
   - What will the next highlighted line be?
   - How will the state change?
3. **Click "Next"** and check if you were right
4. If wrong, read the "Why:" section again

**Goal:** Verify you can predict algorithm behavior

### Workflow 3: Studying for Interviews

1. **Close the browser tab** after watching once
2. **Try to code** the solution yourself
3. **Get stuck?** Open the visualizer and jump to the step where you're stuck
4. **Watch** that step and the "Why:" explanation
5. **Close and retry** coding

**Goal:** Use visualizer as a just-in-time hint system

### Workflow 4: Comparing Approaches

1. Open two problems with similar patterns:
   - `02-lc-207-course-schedule-dry-run.html` (BFS topological sort)
   - `51-lc-994-rotting-oranges-dry-run.html` (BFS grid traversal)
2. **Compare** their "Algorithm State" panels:
   - Both use `queue` for BFS
   - Both track `visited` to avoid cycles
   - Different state representations (graph vs grid)
3. **Notice** the shared BFS pattern

**Goal:** Recognize patterns across problems

## Problem Patterns and What to Watch

### Pattern: HashMap / Two Pointers
**Examples:** Two Sum, 3Sum
**Watch for:**
- How the map grows: `map: {}` → `map: {1:0, 3:1}` → ...
- When we check `map.containsKey()` before adding
- How indices move: `i: 0` → `i: 1` → ...

### Pattern: Sliding Window
**Examples:** Min Window Substring, Max Subarray
**Watch for:**
- Window expansion: `right++`
- Window contraction: `left++`
- When the window is "valid" vs "invalid"
- How `best` is updated

### Pattern: DFS/Backtracking
**Examples:** Number of Islands, Word Search
**Watch for:**
- Recursion depth (state shows current node)
- `visited` set changes
- Backtracking: when a node is removed from `visited`
- Base case detection

### Pattern: BFS
**Examples:** Course Schedule, Rotting Oranges
**Watch for:**
- Queue operations: `queue.offer()` and `queue.poll()`
- Level tracking (all nodes at distance N)
- When neighbors are added to the queue

### Pattern: Dynamic Programming
**Examples:** Coin Change, Word Break
**Watch for:**
- DP table initialization
- How each cell is computed from previous cells
- The recurrence relation in action
- Base cases

## Common Questions

### Q: Why does the highlighted line sometimes stay the same for multiple steps?

**A:** Some lines contain multiple operations. For example:
```java
if (--indegree[next] == 0) queue.offer(next);
```
This might generate 3 steps:
1. Read `indegree[next]`
2. Decrement it
3. Check if zero and add to queue

Each step shows a different state change.

### Q: What does the "line: N" number mean?

**A:** It's the 0-indexed position in the `codeLines` array. Line 0 is the first line of code. This is used internally for highlighting.

### Q: Some steps seem to jump backward in the code?

**A:** This happens during:
- **Loops:** Code returns to the loop condition
- **Recursion:** We enter a helper method
- **Method calls:** Jump to the called method's first line

Watch the "What Changed?" panel to understand why we jumped.

### Q: Why do some visualizers have more steps than others?

**A:** More complex algorithms or longer canonical examples require more steps. LRU Cache has 29 steps because it shows constructor, put operations, get operations, and eviction.

### Q: Can I run the Java code myself?

**A:** Yes! All code is complete and executable:
1. Copy the code from the visualization
2. Wrap in a test harness with the example input
3. Compile with `javac` and run with `java`
4. The output should match what the visualizer shows

## Tips for Maximum Learning

1. **Don't rush** - Spend 30-60 seconds on each step understanding the state change
2. **Verbalize** - Say out loud what's happening: "Now we're adding node 2 to the head..."
3. **Predict** - Before clicking "Next", predict what will change
4. **Compare** - Open similar problems side-by-side to see pattern similarities
5. **Test yourself** - After watching, try to recreate the state changes on paper

## Verification Your Understanding

After watching a visualizer, you should be able to:

✅ Explain what data structure(s) the algorithm uses
✅ Describe the main invariant (the "why")
✅ Walk through the algorithm on a different input
✅ Identify the time and space complexity
✅ Code the solution without looking at the visualizer

## Example Learning Session

**Problem:** LC 146 - LRU Cache

**Session plan (30 minutes):**
```
00:00-05:00  Read problem, understand requirements
05:00-15:00  Watch visualization start to finish (auto-play paused)
15:00-20:00  Re-watch focusing on the "Why:" sections
20:00-25:00  Try to code solution yourself
25:00-30:00  Compare your code to the visualizer's code
```

**Follow-up:**
- Next day: Watch again and try to predict each step
- Week later: Code from memory without visualizer

## Getting Help

If you encounter issues:

1. **JavaScript Errors:** Open browser console (F12) and report errors
2. **Visual Glitches:** Try a different browser (Chrome recommended)
3. **Broken Steps:** Check TEST_COVERAGE_REPORT.md for known issues
4. **Conceptual Questions:** Focus on the "Why:" sections - they explain correctness

## Advanced Usage

### For Instructors
- Share these visualizers in coding bootcamps
- Use as pre-interview prep material
- Project on screen during algorithm lectures

### For Self-Study
- Integrate into spaced repetition schedule
- Create personal notes mapping each step to time complexity
- Build variant visualizers for follow-up questions

### For Interview Prep
- Watch 1-2 visualizers per day in the week before interviews
- Focus on Tier 1 (problems 1-12) first
- Use as reference when solving practice problems

---

**Remember:** These visualizers show you **how code executes**. The goal isn't to memorize the exact steps—it's to build intuition for **why the algorithm works**. Focus on the invariants explained in the "Why:" sections!
