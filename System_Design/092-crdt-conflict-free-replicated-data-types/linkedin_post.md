# CRDTs: Conflict-Free Replicated Data Types — LinkedIn Post

## Post Text (copy-paste ready)

A 10,000-character document with 50,000 keystrokes of edit history can silently carry 40,000+ dead "tombstone" nodes — invisible to the user, but still eating memory and still transmitted on every sync.

- Naive list merging resurrects deleted items — you need tombstones ("milk, bought") instead of hard deletes, or a crossed-off item can reappear from the other replica's stale copy
- A single shared counter with +1 increments is a lost-update race condition waiting to happen across a network partition — CRDTs fix this by giving each replica its own slot and merging with element-wise max()
- Per-character CRDT metadata (replica ID + logical clock + parent ref + tombstone flag) runs 33+ bytes/char — dwarfing the 1-2 bytes of actual text content — until you run garbage collection
- CvRDT (state-based) ships full state every sync — 50-150KB for a 5,000-char document; CmRDT (op-based) ships single ops at 40-60 bytes each, but needs guaranteed at-least-once delivery or edits silently vanish
- Figma's multiplayer canvas uses a custom CRDT-like system — proof that "CRDT" is a family of techniques, not one fixed algorithm

Swipe to see: G-Counter merge walkthrough, RGA tie-break logic, and the CRDT vs OT vs LWW decision table.

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
40,000+ invisible "tombstone" nodes can hide inside a 10K-character doc. Here's how CRDTs merge offline edits without ever talking to a server 👇

### Variant B — Long (400–600 chars)
CRDTs let two offline replicas edit independently and merge back together with zero central coordinator — as long as the merge function is commutative, associative, and idempotent. The catch nobody warns you about: deletions can't be physically removed immediately, so tombstones pile up — 40,000+ dead nodes in a heavily-edited 10K-character document is normal without a garbage-collection pass. Figma's multiplayer canvas, Automerge, and Yjs all solve this differently, but the core tradeoff is the same: network simplicity in exchange for a heavier per-item metadata footprint.

---

## Best Time to Post
Tuesday, 9:00–10:00 AM IST (deep architecture posts perform best early-to-mid week when engineers are actively problem-solving)

## Engagement Hook
"Have you ever had to explain to a PM why a 'simple' document merge feature needs a garbage-collection strategy? What convinced them?"
