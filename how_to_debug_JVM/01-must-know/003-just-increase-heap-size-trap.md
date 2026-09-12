# #3 — "Just Increase Heap Size" — The Trap

> **Category:** Heap Dump Analysis | **Type:** Senior Trap Question | **Priority:** 🔥 Must-Know

## 🗣️ The Interview Question
"We're hitting OOM every 6 hours. If we double the heap from 4 GB to 8 GB, that fixes it, right?"

## 😊 Explain It Simply (for anyone)
Imagine your kitchen trash can fills up every 6 hours because someone keeps quietly stuffing bags of trash inside a locked cabinet that never gets emptied (a memory leak). Someone suggests, "let's just buy a bigger trash can!" But that doesn't stop the person stuffing bags into the locked cabinet — it just means it takes a bit longer (maybe 12 hours instead of 6) before the bigger can ALSO overflows.

Worse, when you finally do empty a giant trash can, it takes way longer to sort through everything (a longer Full GC pause) than emptying a small one — so you've made the eventual mess-cleaning event even more disruptive, while not fixing the actual stuffing problem at all.

## 📊 Visualize It
```
BEFORE (4GB heap):        AFTER just doubling (8GB heap):
0h [■□□□] 20%              0h  [■□□□□□□□] 10%
2h [■■□□] 50%              6h  [■■■■□□□□] 50%
4h [■■■□] 85%             12h  [■■■■■■■□] 85%
6h [■■■■] 100% → OOM      18h [■■■■■■■■] 100% → OOM (same leak, later)

  Leak rate unchanged → only the TIME TO CRASH changed.
  Also: bigger heap = longer Full GC pause when it finally triggers.

Correct move: heap dump → dominator tree → retention root → fix leak
```

## 🏭 The Real Production Answer (15-YOE Level)

No — that's the most common mistake I see from mid-level engineers. Doubling the heap changes the *time to OOM*, not the cause. A leak that fills 4 GB in 6 hours will fill 8 GB in 12 hours. You've just delayed your page by 6 hours.

Worse, a larger heap means longer Full GC pauses when the GC does kick in — a 8 GB heap Full GC with CMS could pause for 10+ seconds, which is harder to hide from users than a smaller heap with more frequent minor GCs.

The correct approach: capture a heap dump, identify the retention root, fix the leak. Heap sizing should be based on the *steady-state* object graph size, not on leak rate.

**When is increasing heap legitimate?** When your application genuinely needs more working memory for the load it handles — e.g., you migrated to larger payloads and the heap is correctly sized too small. But even then, you confirm this with object histogram analysis showing steady-state growth, not runaway growth.

## 🔑 Key Takeaway
Bigger heap only buys time against a leak — it never fixes it, and it makes the eventual Full GC pause worse.
