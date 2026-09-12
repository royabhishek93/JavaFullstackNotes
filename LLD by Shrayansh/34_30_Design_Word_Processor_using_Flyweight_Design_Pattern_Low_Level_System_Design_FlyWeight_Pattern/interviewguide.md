# Interview Guide: Flyweight Design Pattern (Word Processor / Text Editor)

## 🗣️ The Interview Scenario

> "Design the core character-storage model for a word processor like Google Docs. A document can contain millions of characters, each with a font type and size. Assume memory is a hard constraint — say, we only have 16GB available. Naively creating one object per character would consume dozens of gigabytes. How would you redesign the character model to drastically cut memory usage, and what specific technique would you use to guarantee two identical letters don't waste duplicate memory?"

The interviewer is deliberately signaling "memory is limited" — a strong hint to recognize the **Flyweight pattern**. They want you to (1) identify which parts of a character's data are shared vs. unique, (2) design an immutable flyweight class, and (3) design a caching factory that guarantees reuse.

## 🏗️ Architect's Explanation (For a New Developer)

Imagine you're printing the word "**THIS**" a thousand times across a document. Every capital "T" you ever render looks *visually identical* — same font, same size, same shape — the only thing that differs is *where on the page* it appears (its row/column coordinates). It would be wasteful to build a brand-new "T" glyph object (with all its font-rendering data) every single time you type a "T" — you should build the "T" glyph **once**, cache it, and simply tell it a new position each time you reuse it.

That's the entire idea behind the **Flyweight pattern**: split every object's data into two buckets —
- **Intrinsic data**: the data that's *identical* across many objects and never changes once set (e.g., character value, font type, font size). This is the expensive, "worth sharing" part.
- **Extrinsic data**: the data that's *different* for every instance and comes from the caller at the moment of use (e.g., row, column — where to draw it). This can never be shared.

You keep only intrinsic data inside the shared object (make it immutable), pass extrinsic data as a *method parameter* at the moment of use, and use a **factory with a cache** so that requesting "give me a T" the second time returns the *same* object instead of building a new one.

## 📊 Visualize It

**Class structure:**
```
          <<interface>>
             Letter
        +display(row, col)
                ▲
                │ implements
         ┌──────┴───────┐
         │  Character     │   (Flyweight object — INTRINSIC data only)
         ├───────────────┤
         │ -charValue     │   e.g. 'T'
         │ -fontType      │   e.g. "Arial"     (immutable — getters only, no setters)
         │ -fontSize      │   e.g. 10
         ├───────────────┤
         │ +display(      │◄── row, col passed in as EXTRINSIC parameters,
         │   row, col)    │    NOT stored on the object
         └───────────────┘

         ┌─────────────────────────┐
         │      LetterFactory        │
         ├─────────────────────────┤
         │ -cache: Map<Char,         │   key = charValue (the intrinsic identity)
         │           Character>      │
         ├─────────────────────────┤
         │ +createLetter(charValue): │
         │   Character               │
         │   if cache.contains(key)  │
         │       return cached obj   │──► REUSE, no new object
         │   else                    │
         │       build + cache + ret │──► build ONCE
         └─────────────────────────┘
```

**Memory usage before vs. after Flyweight (typing "THIS...58 chars, 7 T's, 3 H's..."):**
```
BEFORE (no Flyweight):                    AFTER (Flyweight + cache):
58 characters typed                       58 characters typed
  → 58 separate Character objects           → only as many DISTINCT Character objects
  → each carries full font/size data          as there are DISTINCT letters (e.g., ~20)
  → 7 "T" objects, all IDENTICAL data        → 1 shared "T" object, reused 7 times
  → massive duplicate memory                 → row/col passed fresh each display() call
```

**Runtime sequence — first request vs. cached request:**
```
Client: LetterFactory.createLetter('T')
   cache.contains('T')? NO
   → build new Character('T', "Arial", 10)
   → cache.put('T', obj)
   → return obj
   obj.display(row=0, col=0)      // renders T at (0,0)

Client: LetterFactory.createLetter('T')   // second T anywhere in the document
   cache.contains('T')? YES
   → return SAME cached obj   (no new allocation)
   obj.display(row=0, col=6)      // same object, different position
```

## 🔧 Deep Dive: How It Actually Works

### The problem, quantified (from the transcript's own numbers)
The lecturer first illustrates the issue with a **gaming example** (an army of 5 lakh humanoid robots + 5 lakh robotic-dog robots = 10 lakh total objects), where each object naively stores:
- `x`, `y` coordinates (extrinsic — 4 bytes each)
- `type` (intrinsic — ~50 bytes)
- `Sprite` (intrinsic — a heavy 2D bitmap array, estimated ~30KB)

Rough math: ~31KB per object × 10 lakh (1 million) objects ≈ **31GB** — far beyond a stated 16–25GB memory budget. This "do the arithmetic out loud" step is exactly what interviewers want to see: quantify the pain before proposing the fix.

### Applying the same principle to the word processor
```java
// Step 1: identify intrinsic vs extrinsic data
// Intrinsic (shared, never changes once set): character value, font type, font size
// Extrinsic (per-usage, supplied by caller):   row, column

// Step 2: build an immutable flyweight — private fields, GETTERS ONLY, no setters
interface Letter {
    void display(int row, int col);
}

class DocumentCharacter implements Letter {
    private final char charValue;
    private final String fontType;
    private final int fontSize;

    DocumentCharacter(char charValue, String fontType, int fontSize) {
        this.charValue = charValue;
        this.fontType = fontType;
        this.fontSize = fontSize;
    }

    @Override
    public void display(int row, int col) {           // extrinsic data passed as PARAMETER
        System.out.println(charValue + " at (" + row + "," + col + ") font=" + fontType);
    }
}
```

### Step 3: the caching factory — this is the mechanism that actually delivers the memory savings
```java
class LetterFactory {
    private static final Map<Character, Letter> cache = new HashMap<>();

    static Letter createLetter(char c) {
        if (cache.containsKey(c)) {
            return cache.get(c);                        // REUSE existing flyweight
        }
        Letter letter = new DocumentCharacter(c, "Arial", 10);
        cache.put(c, letter);
        return letter;
    }
}
```
The key used in the cache map is the **intrinsic identity** — here just the character value (in a more advanced version, a composite key of `charValue + fontType + fontSize`, since the lecture notes that if font/size *can* vary per usage, the cache key must include them too).

### Step 4: driving it end-to-end
```java
Letter t1 = LetterFactory.createLetter('T');   // cache miss → constructs a new object
t1.display(0, 0);
Letter t2 = LetterFactory.createLetter('T');   // cache hit  → same object as t1
t2.display(0, 6);                              // same object, different position rendered
// t1 == t2 is true — proven object reuse
```

### The four-step recipe (explicitly given in the transcript — worth memorizing verbatim for interviews)
1. **Remove all extrinsic data from the object**, keeping only intrinsic data — the resulting class is called the **flyweight object**.
2. **Make the class immutable** — private fields with getters only, no setters (assign once via constructor).
3. **Pass extrinsic data as a method parameter** at the point of use (e.g., `display(row, col)`), never stored on the object.
4. **Cache and reuse** the constructed flyweight object via a factory, keyed by the intrinsic identity.

### When to reach for Flyweight — the three diagnostic signals
- Interviewer explicitly says **memory is limited**.
- Many objects **share identical data** (intrinsic fields are the same across instances).
- **Object creation is expensive** (e.g., building a `Sprite`/bitmap, or heavy font metadata).

## 🔥 Real Production Incident & Fix

**What broke:** A collaborative document-editing service (conceptually similar to this word processor) modeled every single character in every document as its own Java object with fields for glyph metadata, font family, size, and color — no sharing. When a customer imported a 400-page legal contract (~1.2 million characters, almost entirely one font/size/color), the editing service's JVM heap usage spiked and the pod was OOM-killed by Kubernetes mid-edit, corrupting the user's in-progress autosave.

**How the team noticed:** Kubernetes events showed repeated `OOMKilled` restarts for the editor-service pods correlating with large-document uploads; a heap dump (triggered via `-XX:+HeapDumpOnOutOfMemoryError`) revealed **millions of near-identical `CharacterGlyph` objects**, each independently storing the same font name string and size integer, dominating retained heap.

**Root cause:** The character model conflated intrinsic data (font family, size, glyph shape — identical for the vast majority of characters in a typical document) with extrinsic data (row/column position, which is unique per character), so every character paid the full memory cost of the shared font metadata redundantly.

**The fix:** The team refactored `CharacterGlyph` into a Flyweight: font/glyph metadata became an immutable, interned `GlyphStyle` object cached in a `Map<StyleKey, GlyphStyle>` factory (keyed by font+size+color), and each character in the document became a lightweight record of just `(charValue, row, col, styleRef)`. Retained heap for the same 1.2M-character document dropped by roughly 85%, and the OOM kills stopped entirely.

```
BEFORE:                                          AFTER:
1.2M x CharacterGlyph {                          1 x GlyphStyle { fontFamily, size, color }  (shared)
    char, fontFamily, size, color,                1.2M x CharacterRef { char, row, col,
    row, col                                                             styleRef -> GlyphStyle }
}   ← each ~200 bytes, all duplicated font data   ← each ~40 bytes, font data shared once
= ~240 MB retained just for style duplication     = ~48 MB total, style paid for once
```

## ❓ Likely Interview Follow-Up Questions & Answers

**Q1: What's the actual mechanism that saves memory here — is it just "fewer objects," or something more specific?**
It's specifically about **de-duplicating identical intrinsic state**: instead of N objects each carrying a full copy of shared data (font, type, image), you have far fewer distinct flyweight objects (one per unique intrinsic combination) and N lightweight references/parameters carrying only the unique extrinsic data. Memory savings scale with how much duplication existed in the intrinsic fields, not merely with object count.

**Q2: How do you decide what counts as "intrinsic" if font size, say, could occasionally vary per character?**
Intrinsic vs. extrinsic isn't fixed by the field name — it's determined by whether the *value* is actually shared across many usages in your real workload. If font size can vary per character, it must move to the cache key (and become part of what's passed/looked-up), not stay in a single hardcoded flyweight; the transcript explicitly calls this out ("if font type can be different, size can be different, then that could be another key").

**Q3: Is Flyweight thread-safe by default? What would you need to add for a multi-threaded editor?**
The flyweight objects themselves are safe because they're immutable, but the **factory's cache** (a shared `HashMap` in the example) is not thread-safe under concurrent writes. In production you'd use a `ConcurrentHashMap` and its atomic `computeIfAbsent()` to avoid a race where two threads simultaneously miss the cache and construct duplicate objects for the same key.

**Q4: How is Flyweight different from simple object pooling?**
An object pool reuses *mutable* objects that get "checked out," modified, and "checked back in" (state resets between uses) — the pool doesn't care what data is shared vs. unique. Flyweight is about permanently sharing **immutable, identical intrinsic state** across many logical instances simultaneously (many characters point at the *same* style object *at the same time*, not one after another).

**Q5: What's a real risk of misapplying Flyweight?**
If you flyweight-share an object whose "intrinsic" data isn't actually guaranteed to always be identical (e.g., two callers thinking they share the same cached "T" but expecting different font sizes), a caller could mutate shared state and corrupt every other reference — which is exactly why immutability (no setters) is a non-negotiable part of the pattern, not an optional nicety.

**Q6: When would you NOT use Flyweight even if you have lots of similar objects?**
If memory isn't actually constrained, or if the objects don't genuinely share meaningful data (little to no overlap between instances), the added complexity of a factory + cache + intrinsic/extrinsic split isn't worth it — the transcript explicitly notes "if there's no issue for memory, generally it can be avoided" and "if two objects don't share any data, you can't use Flyweight."

## 🔑 Key Takeaway
Flyweight is triggered by three signals together — limited memory, shared data across many objects, expensive object creation — and the mechanism is always the same: split intrinsic (shared, immutable, cached) from extrinsic (per-call, passed as a parameter), and let a factory cache guarantee true reuse.
