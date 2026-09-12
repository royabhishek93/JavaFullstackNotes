# Interview Guide: File System LLD (Composite Design Pattern)

## 🗣️ The Interview Scenario

> "Design a simplified file system: a directory can contain files, and it can also contain other directories, which themselves can contain files or more directories, recursively. Give me an `ls`-style method that prints out the full contents of a directory, no matter how deeply nested it is — and I don't want to see `instanceof` checks scattered through your code."

That last constraint is the real test: it's specifically designed to surface whether you know the **Composite Design Pattern**.

## 🏗️ Architect's Explanation (For a New Developer)

The instructor's opening definition is the simplest way to internalize this pattern: **"object inside object."** Picture a tree — not the data structure necessarily, but literally a tree in nature: a trunk splits into branches, and each branch can split into more branches or end in a leaf. **Any time a problem can be naturally drawn as this kind of branching structure, where a "container" can hold either simple, indivisible things or *more containers just like itself*, you're looking at a Composite pattern problem.**

Three real-world analogies given directly in the transcript, all sharing the same shape:
- **A company org chart**: CEO → Director → Manager → (an individual IT engineer, *or* an entire marketing team which itself contains more people/sub-teams).
- **A shipping/delivery box**: a box can directly contain a product, *or* it can contain a smaller box — which itself can contain a product or an even smaller box.
- **A file system**: a directory can contain a file, *or* it can contain another directory — which can again contain files or more directories.

The engineering problem this creates, if you *don't* use Composite: your code that needs to process "whatever's inside this container" has to ask, at every level, "is this thing in front of me a simple leaf, or is it another container?" — and branch its logic accordingly with `instanceof` checks. The Composite pattern's trick: **make the leaf and the container implement the exact same interface.** Then the code that processes contents doesn't need to ask "what are you?" at all — it just calls the shared method, and whether that call quietly returns a simple result (leaf) or recursively fans out into more calls (container), the calling code neither knows nor cares.

## 📊 Visualize It

### Class structure (component / leaf / composite)

```
        <<interface>> FileSystem
        + ls()
             ▲                    ▲
             │                    │
           File                Directory
        (LEAF — simple)    (COMPOSITE — contains itself)
        + name              + name
        + ls() → print name  + List<FileSystem> children
                              + ls() → iterate children,
                                       call ls() on each
                                       (no instanceof needed!)
```

### Before vs. after — where `instanceof` disappears

```
BEFORE (no shared interface):                AFTER (Composite pattern):
Directory.ls() {                             Directory.ls() {
  for (Object obj : contents) {                for (FileSystem fs : children) {
    if (obj instanceof File)                       fs.ls();   // ✅ polymorphic call
        ((File) obj).ls();                          // works whether fs is a File
    else if (obj instanceof Directory)               // (leaf, prints & stops)
        ((Directory) obj).ls();                       // or a Directory (composite,
  }                                                     // recurses further)
}                                             }
   ❌ every container-processing method
      needs type-checking logic
```

### Recursive tree example (traced in the transcript)

```
movie/                      <-- Directory
 ├─ border                  <-- File (leaf)
 └─ comedy_movies/           <-- Directory (nested)
      └─ hulchul             <-- File (leaf)

ls(movie) →
   print "border"
   ls(comedy_movies) →         (movie's child is itself a Directory — recurse)
        print "hulchul"
```

## 🔧 Deep Dive: How It Actually Works

### 1. The naive/problem version first

The instructor deliberately shows the "how most people first attempt it" version to make the pain point concrete:

```java
class File {
    String name;
    File(String name) { this.name = name; }
    void ls() { System.out.println(name); }
}

class Directory {
    String name;
    List<Object> objects;   // could hold File OR Directory — untyped!
    Directory(String name) { this.name = name; this.objects = new ArrayList<>(); }

    void ls() {
        for (Object obj : objects) {
            if (obj instanceof File) {
                File f = (File) obj;      // manual typecast required
                f.ls();
            } else if (obj instanceof Directory) {
                Directory d = (Directory) obj;  // manual typecast required
                d.ls();
            }
        }
    }
}
```
The explicit complaint: *"this is the problem statement that we have to put if-else condition here — instance of, instance of, or any other if-else condition to determine what object I need to type cast into, so that I can do an appropriate operation."*

### 2. Applying Composite to fix it

Step 1 — introduce a shared interface (the "component") that **both** leaf and composite implement:
```java
public interface FileSystem {
    void ls();
}
```

Step 2 — the **leaf** (`File`) implements it simply, with no children:
```java
public class File implements FileSystem {
    private String name;
    public File(String name) { this.name = name; }
    public void ls() { System.out.println(name); }
}
```

Step 3 — the **composite** (`Directory`) implements it too, but internally holds a list of the *same interface type* — not a list of `Object`, and not separate lists for files vs. directories:
```java
public class Directory implements FileSystem {
    private String name;
    private List<FileSystem> fileSystemList;   // <-- the key change

    public Directory(String name) {
        this.name = name;
        this.fileSystemList = new ArrayList<>();
    }

    public void ls() {
        for (FileSystem fs : fileSystemList) {
            fs.ls();   // polymorphic — no instanceof, no typecast, ever
        }
    }
}
```

The instructor's explicit callout of the crucial difference: *"you notice the difference between the problem [naive version] and the one which we are saying in the [Composite] program statement — we [had] a list of object... because they don't have any parent. Now we have created an interface `FileSystem`, and `Directory` is also a child of `FileSystem`, then normal `File` is also a child of `FileSystem` — that's why in the directory I am creating a list of `FileSystem`s."*

### 3. Traced example run

Built structure: a `movie` directory containing a file `border`, and a nested directory `comedy_movies` which itself contains a file `hulchul`.

Calling `movie.ls()`:
- Iterates `movie`'s `fileSystemList`: first element is `border` (a `File`) → its `ls()` prints `"border"` directly (leaf — nothing to recurse into).
- Second element is `comedy_movies` (a `Directory`) → calling `.ls()` on it **re-enters the same method** — it iterates *its own* list and finds `hulchul` (a `File`) → prints `"hulchul"`.
- No branch of this traversal code ever asked "are you a File or a Directory?" — the call `fs.ls()` was identical at every level; polymorphism (dynamic dispatch) did the routing automatically.

### 4. A second worked example: arithmetic expression tree (calculator)

The instructor deliberately shows a **second, structurally identical** application to cement the pattern-recognition skill — evaluating an expression like `2 * (1 + 7)`:

```java
public interface ArithmeticExpression {
    int evaluate();
}

// Leaf: a plain number, nothing to recurse into
public class Number implements ArithmeticExpression {
    private int value;
    public Number(int value) { this.value = value; }
    public int evaluate() { return value; }
}

// Composite: an expression made of two sub-expressions and an operator
public class Expression implements ArithmeticExpression {
    private ArithmeticExpression left, right;
    private Operation operation;  // enum: ADD, SUBTRACT, MULTIPLY, DIVIDE

    public Expression(ArithmeticExpression left, ArithmeticExpression right, Operation operation) {
        this.left = left; this.right = right; this.operation = operation;
    }

    public int evaluate() {
        int leftVal = left.evaluate();     // recursively resolves, whether left is
        int rightVal = right.evaluate();   // a Number (leaf) or another Expression (composite)
        switch (operation) {
            case ADD: return leftVal + rightVal;
            case MULTIPLY: return leftVal * rightVal;
            // ... SUBTRACT, DIVIDE
        }
        throw new IllegalStateException();
    }
}
```

Traced construction for `2 * (1 + 7)`:
```java
ArithmeticExpression innerExpr = new Expression(new Number(1), new Number(7), Operation.ADD);
ArithmeticExpression parentExpr = new Expression(new Number(2), innerExpr, Operation.MULTIPLY);
parentExpr.evaluate(); // → 16
```
Walkthrough exactly as narrated: `parentExpr.evaluate()` sees operation = MULTIPLY, so it calls `left.evaluate()` (a `Number`, returns `2`) and `right.evaluate()` (the `innerExpr`, itself an `Expression` — recurses: sees ADD, evaluates `Number(1)` → `1` and `Number(7)` → `7`, returns `8`) → outer multiply: `2 * 8 = 16`. The instructor's explicit framing: *"just think our recursion — if you are good in recursion you will definitely get to know what I am doing"* — Composite traversal and recursion are the same mental model.

### 5. The generalized recognition rule

> *"Any problem statement which can be constructed in a tree form, you know that which design pattern will be helpful for you."*

## 🔥 Real Production Incident & Fix

**What broke:** A cloud storage product's backend "folder size calculator" (used to show users how much space a folder occupies, including nested subfolders) was implemented with an untyped `List<Object> contents` per folder and manual `instanceof File` / `instanceof Folder` branching to recursively sum sizes — mirroring the exact "naive" version shown at the start of this transcript. When a new content type was introduced (a "Shortcut/Symlink" object, pointing at another file elsewhere), engineers had to hunt down **every single method that processed folder contents** across the codebase (size calculator, search indexer, the `ls`-equivalent UI listing, a permissions-checker) and manually add a new `else if (obj instanceof Shortcut)` branch to each one.

**How the team noticed:** Two of those five methods were missed during the rollout — the search indexer was updated, but the permissions-checker was not. This surfaced as a security-adjacent bug report: shortcuts to restricted files were appearing in search results for users who shouldn't have had access, because the permissions-checker's `instanceof` chain silently fell through its missing `else if` branch, treating an un-recognized `Shortcut` object as if it had no restrictions to check.

**Root cause:** Because content types were routed via scattered `instanceof` conditionals rather than a shared polymorphic interface, adding a new type required **coordinated, manual updates across every consumer of the type hierarchy** — there was no single point that guaranteed a new type would be "seen" by all existing processing logic. This is precisely the situation Composite (and polymorphism generally) is designed to prevent.

**The fix:** The team refactored to the same shared-interface Composite structure from this transcript: a `FolderItem` interface with `getSize()`, implemented by `File`, `Folder` (composite, recursively summing children), and the new `Shortcut` (which delegates `getSize()` to its target). Every existing consumer — size calculator, indexer, UI listing, permissions-checker — was rewritten to call `item.getSize()` (or the equivalent operation) polymorphically instead of branching on type. Adding `Shortcut` required implementing the interface **once**; every consumer automatically handled it correctly because none of them branch on concrete type anymore.

```
BEFORE: instanceof-based dispatch,          AFTER: shared interface, polymorphic
scattered across 5+ consumer methods         dispatch — new type "just works"
 everywhere it's used
                                             interface FolderItem { int getSize(); }
if (obj instanceof File) ...                 class Shortcut implements FolderItem {
else if (obj instanceof Folder) ...             getSize() { return target.getSize(); }
// forgot: Shortcut case in one method! ❌   }
                                              // every consumer calls item.getSize()
   ❌ silent security gap in one consumer        ✅ automatically correct everywhere
```

## ❓ Likely Interview Follow-Up Questions & Answers

**Q1: How is the Composite pattern different from just using recursion with a tree data structure?**
A: They're deeply related — Composite is really "recursion expressed as an object-oriented type hierarchy" rather than a data structure you manually recurse over externally. The pattern's specific contribution is defining a **common interface** shared by both leaves and composites, so that *calling code* doesn't need to know or check which kind of node it's dealing with — the recursion is baked into the composite's own implementation of the shared method, invisible to the caller.

**Q2: What's the actual harm of `instanceof` checks, beyond "it looks ugly"?**
A: Every time you add a new leaf or composite type (a new piece type, a new file-system entry type, a new expression node), you must find and update **every single place** that has an `instanceof` chain for that hierarchy — this violates the Open/Closed Principle (code should be open for extension, closed for modification) and, as in the production incident above, it's very easy to miss one call site, silently breaking correctness or security rather than failing loudly.

**Q3: In the `Directory` class, why is `fileSystemList` typed as `List<FileSystem>` rather than having two separate lists — one for files, one for sub-directories?**
A: Two separate lists would force every consumer of `Directory` to process both lists separately (defeating the purpose), and it wouldn't scale if you added a third composite/leaf type later (you'd need a third list everywhere). A single list of the shared interface type lets you add arbitrarily many kinds of `FileSystem` implementers without ever touching `Directory`'s iteration logic.

**Q4: How would you compute the total size of a directory (including all nested subdirectories) using this Composite structure?**
A: Add a `getSize()` method to the `FileSystem` interface. `File.getSize()` returns its own stored size directly (leaf case). `Directory.getSize()` sums `fs.getSize()` over every element in its `fileSystemList` — since some of those elements may themselves be `Directory` instances, this recursively (and transparently) rolls up nested sizes, with zero `instanceof` checks, exactly mirroring how `ls()` works.

**Q5: Is the arithmetic-expression example (calculator) really the "same" pattern as the file system, or just superficially similar?**
A: It's genuinely the same structural pattern: `Number` is the leaf (an indivisible value, `evaluate()` just returns itself), and `Expression` is the composite (it holds two `ArithmeticExpression` references — which could themselves be `Number` or further `Expression`s — and its `evaluate()` recursively resolves both sides before combining them with an operator). The instructor uses this second example specifically to train the pattern-recognition skill: any time a value is built from smaller values of the *same conceptual type*, in a nested/tree fashion, Composite applies — regardless of the domain.

**Q6: What's a case where Composite would be the wrong choice?**
A: If the "container" and "leaf" concepts don't actually share a meaningful common operation/interface (e.g., a container needs entirely different behavior than what leaves expose, with little polymorphic overlap), forcing them into one shared interface creates awkward, half-empty implementations (methods that must throw `UnsupportedOperationException` for one side). Composite earns its value specifically when leaves and composites can genuinely support the *same* operation signature meaningfully — as `ls()`/`evaluate()`/`getSize()` do here.

## 🔑 Key Takeaway

Whenever a problem can be visualized as a tree — a container that holds either simple leaf items or more containers just like itself — define one shared interface for both, so consuming code calls a single polymorphic method and never needs `instanceof` checks to know what it's dealing with.
