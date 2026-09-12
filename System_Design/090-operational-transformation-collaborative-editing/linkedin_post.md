# Operational Transformation — LinkedIn Post

## Post Text (copy-paste ready)

16 milliseconds. That's the entire time budget Google Docs gives itself to make your keystroke feel instant — before the server has even seen it. Here's the algorithm behind it, and the 3 traps that quietly broke it for Google Wave.

- The index-shift problem: Alice inserts "X" at position 2, Bob deletes at position 3 — both against the same starting document. Apply Bob's delete blindly and you cut the wrong character, because Alice's insert already shifted everything
- The fix is a transform function (xform) that rewrites one concurrent operation so both replicas converge on the identical document no matter the order applied — a provable guarantee called TP2, not "it worked in testing"
- Offline-reconnect trap: a client that drops for 8 seconds and queues 3 local ops must transform its OWN queued ops against what it missed, or the user's screen visibly "jumps" — a classic bug seen in early Etherpad and Google Wave clients
- Transform cost is O(N) against missed operations — normally N is 1-5, but a client reconnecting after 10 minutes offline on a busy doc can face N in the hundreds; production systems snapshot the document instead of replaying the full op log
- Google Wave's own transform-correctness bugs were a documented contributor to the project's struggles — a subtly wrong transform doesn't crash, it silently diverges the document

Swipe → to see the full convergence walkthrough (Hello → HeXllo → HeXlo) and the OT vs CRDT decision table.

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
16ms to feel instant, then a transform function that must converge every replica — here's how Google Docs resolves concurrent edits 👇

### Variant B — Long (400–600 chars)
Two people type in the same sentence at the same time — how does Google Docs make sure they don't corrupt each other's work? Operational Transformation tags every edit as insert(pos,text) or delete(pos,length), then a server-side transform function rewrites concurrent ops so every client converges on the identical document (the TP2 property). The traps that catch teams: offline clients whose queued ops "jump" on reconnect, O(N) transform cost blowing up after long disconnects, and silently-wrong transform functions — the kind of bug that was a real, documented factor in Google Wave's downfall.

---

## Best Time to Post
Tuesday, 10:00–11:00 AM IST (deep algorithmic/system-design breakdowns perform best early-to-mid week when engineers are actively browsing for interview prep content)

## Engagement Hook
"Have you ever built (or debugged) a collaborative editing feature — did you reach for OT, CRDTs, or just accept last-write-wins? What broke first?"
