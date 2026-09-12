# Java 21 Sequenced Collections

## What is this? (Plain English)

Before Java 21, if you wanted "the first element" or "the last element" of a collection, every collection type had its own, completely different way of asking for it: `list.get(0)` for a `List`, `deque.getFirst()` for a `Deque`, manual iteration for a `LinkedHashSet`, `treeSet.first()` for a `TreeSet`. There was no common vocabulary. **Sequenced Collections introduce one shared interface** — `SequencedCollection`, `SequencedSet`, `SequencedMap` — so that "give me the first/last element," "add to the front/back," and "give me a reversed view" work the same way no matter which collection you're holding.

**Real-world analogy:** imagine every appliance in your house having a different word for "turn on" — the TV says "activate," the fridge says "power up," the lamp says "illuminate." Sequenced Collections is like standardizing every appliance to just use "on" and "off," regardless of brand.

## The Problem It Solves

A collection qualifies to be "sequenced" only if it satisfies **all three** of these conditions:
1. **Predictable iteration** — the collection maintains either insertion order or sorted order, so repeated iteration always yields elements in the same, well-defined sequence.
2. **First/last access and manipulation** — you can get, add, and remove the first and last elements.
3. **Reversible view** — you can obtain a reversed *view* of the same underlying collection (not a copy) via one common method.

Collections that fail condition 1 (no defined order at all) — `HashSet`, `HashMap`, `Hashtable`, `PriorityQueue` — are excluded entirely, since first/last/reverse are meaningless without a defined order. `Queue` is excluded too: it only supports FIFO access (add at tail, remove from head) — there's no "get/add/remove last" or a defined reverse operation.

## The New Hierarchy

```
                     ┌─────────────┐
                     │ Collection  │
                     └──────┬──────┘
                            │
                            ▼
                 ┌───────────────────────┐
                 │ SequencedCollection   │
                 └───┬─────────┬─────┬───┘
                     │         │     │
                     ▼         ▼     ▼
                ┌──────┐  ┌──────┐ ┌───────────────┐
                │ List │  │ Deque│ │ SequencedSet  │
                └──────┘  └──────┘ └───┬───────┬───┘
                                       │       │
                                       ▼       ▼
                              ┌──────────────┐ ┌───────────┐
                              │ LinkedHashSet│ │ SortedSet │
                              └──────────────┘ └─────┬─────┘
                                                      │
                                                      ▼
                                                ┌──────────┐
                                                │ TreeSet  │
                                                └──────────┘

                     ┌─────────────┐
                     │     Map     │
                     └──────┬──────┘
                            │
                            ▼
                    ┌────────────────┐
                    │ SequencedMap   │
                    └───┬────────┬───┘
                        │        │
                        ▼        ▼
               ┌──────────────┐ ┌───────────┐
               │ LinkedHashMap│ │ SortedMap │
               └──────────────┘ └─────┬─────┘
                                       │
                                       ▼
                                 ┌──────────┐
                                 │ TreeMap  │
                                 └──────────┘

  ┌───────────────────────────────────────────────────────────┐
  │ Queue / PriorityQueue / HashSet / HashMap                  │
  │ — EXCLUDED (no defined order)                              │
  └───────────────────────────────────────────────────────────┘
```

*(Full Mermaid source: see [mermaid-diagrams.md](mermaid-diagrams.md))*

**Why a separate `SequencedSet` instead of just using `SequencedCollection` everywhere?** Because a plain collection allows duplicates but a `Set` must not. `SequencedSet` extends `SequencedCollection` and additionally enforces uniqueness — that's the entire reason it exists as its own interface rather than folding `LinkedHashSet`/`TreeSet` directly under `SequencedCollection`.

## The Common Methods (Now Shared Across All Sequenced Types)

| Operation | Method |
|---|---|
| Get first / last | `getFirst()` / `getLast()` |
| Add at front / back | `addFirst(e)` / `addLast(e)` |
| Remove first / last | `removeFirst()` / `removeLast()` |
| Reversed view | `reversed()` |

For **map** types the equivalent is `firstEntry()`, `lastEntry()`, `putFirst(k,v)`, `putLast(k,v)`, `pollFirstEntry()`, `pollLastEntry()`, `reversed()`.

```java
List<String> list = new ArrayList<>(List.of("B", "C", "D"));
list.addFirst("A");      // [A, B, C, D]
list.addLast("E");       // [A, B, C, D, E]
list.removeFirst();      // [B, C, D, E]
List<String> rev = list.reversed(); // a VIEW, not a copy

LinkedHashSet<String> set = new LinkedHashSet<>(List.of("B", "C", "D"));
set.addFirst("A");
set.getFirst();          // "A"
```

**Important exception — sorted types:** `addFirst`/`addLast` (and `putFirst`/`putLast`) throw `UnsupportedOperationException` on `TreeSet`/`TreeMap` — because those collections decide element position based on sort order, not insertion position, so "insert at the front" is a contradiction. You can still `add`/`put` normally (position is auto-determined) and still use `getFirst`/`getLast`/`reversed()`.

## Interview Q&A

**Q: Why were `Queue` and `PriorityQueue` left out of the sequenced hierarchy?**
A: `Queue` only defines FIFO access (add at tail, poll from head) — there's no meaningful "last element" or reverse view. `PriorityQueue` doesn't maintain any consistent iteration order at all — it internally uses a heap and only guarantees the head is the min/max, not that the rest of the elements are sorted or stable across iterations.

**Q: Why is `LinkedHashSet` a child of `SequencedSet` and not directly of `SequencedCollection`?**
A: Because `SequencedCollection` alone doesn't forbid duplicates. `SequencedSet` is the interface that additionally guarantees uniqueness while still exposing all the same first/last/reverse operations — that's specifically why it needed to exist as its own interface.

**Q: What real problem do these interfaces solve, if the underlying functionality (getting the first/last element) already existed on most collections?**
A: The functionality existed, but every collection type exposed it through a *different* method name and API shape (`list.get(0)` vs `deque.getFirst()` vs manual `iterator()` on `LinkedHashSet`). Sequenced Collections don't add new capability so much as they unify the vocabulary, so code that works with "the first/last element of anything sequenced" doesn't need to special-case each collection type.

**Q: Does `list.reversed()` create a new list?**
A: No — it returns a *view* backed by the same underlying data. Changes made through the reversed view are reflected in the original collection, and vice versa.

**Q: Why does calling `addFirst()` on a `TreeSet` throw an exception?**
A: A `TreeSet` determines every element's position by its sort order, not by insertion order — "add at the front" has no well-defined meaning there. Only `add()` (which lets the sort order decide placement) is valid; `addFirst`/`addLast` are explicitly unsupported on sorted types.
