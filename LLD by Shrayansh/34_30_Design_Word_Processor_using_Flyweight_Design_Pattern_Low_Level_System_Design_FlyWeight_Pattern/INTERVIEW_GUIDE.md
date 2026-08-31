# 📄 Word Processor - Low Level Design Interview Guide
## _15 YOE Architect-Level Conversational Script_

---

## 📋 **Table of Contents**
1. [Architecture Diagram](#1-architecture-diagram)
2. [API Design](#2-api-design)
3. [ER Diagram & Database Design](#3-er-diagram--database-design)
4. [Sequence Diagrams](#4-sequence-diagrams)
5. [Scenario-First Explanations](#5-scenario-first-explanations)
6. [Cross Questions](#6-cross-questions)
7. [Trade-offs](#7-trade-offs)
8. [Senior Trap Questions](#8-senior-trap-questions)
9. [Technology Choices](#9-technology-choices)

---

## **Design Pattern Used**: Flyweight Pattern

**Interviewer**: "Design a Word Processor (like MS Word) focusing on text rendering and memory efficiency."

**You**: "This is THE classic **Flyweight Pattern** interview question! Core insight: **A document with 100,000 characters would need 100,000 character objects if done naively. But most characters share the SAME formatting (font, size, color) - so we can SHARE the immutable formatting data across characters.**"

---

## 1. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                 WORD PROCESSOR ARCHITECTURE                          │
└─────────────────────────────────────────────────────────────────────┘

                    ┌──────────────────┐
                    │     DOCUMENT      │
                    │                  │
                    │  List<CharacterInstance>│  ◄── Extrinsic state (position)
                    └────────┬─────────┘
                             │
                             ▼
              ┌──────────────────────────┐
              │   CharacterInstance        │  (Context - holds extrinsic state)
              │                            │
              │  char: 'H'                 │
              │  row: 0, col: 0            │
              │  style: → CharacterStyle   │──────┐
              └────────────────────────────┘      │
                                                   │ SHARED reference!
              ┌──────────────────────────┐      │
              │   CharacterStyleFactory    │      │
              │      (Flyweight Factory)   │      │
              │                            │      │
              │  Map<StyleKey,             │◄─────┘
              │      CharacterStyle> cache │
              │                            │
              │  getStyle(font,size,color, │
              │           bold,italic)     │
              │  → Returns CACHED instance  │
              │    if exists, else creates   │
              └────────────┬───────────────┘
                            │
                            ▼
              ┌──────────────────────────┐
              │   CharacterStyle           │  (Flyweight - Intrinsic/shared state)
              │      (IMMUTABLE)           │
              │                            │
              │  font: "Arial"              │
              │  size: 12                  │
              │  color: "Black"             │
              │  bold: false                │
              │  italic: false              │
              └────────────────────────────┘

    MEMORY SAVINGS EXAMPLE:
    Document: 100,000 characters, but only 5 DISTINCT styles used
    
    ❌ Without Flyweight: 100,000 × sizeof(style) = 100,000 × 40 bytes = 4MB
    ✅ With Flyweight: 5 × 40 bytes (shared) + 100,000 × 8 bytes (reference) = 800KB
    
    ~80% memory reduction!
```

---

## 2. API Design

```http
POST /api/v1/documents/{docId}/characters
Request:
{
  "char": "H",
  "position": {"row": 0, "col": 0},
  "style": {"font": "Arial", "size": 12, "bold": true, "color": "black"}
}

Response: 201 CREATED
{"characterId": "char-1", "styleId": "style-hash-abc123"}  // Reused if same style exists

---

PUT /api/v1/documents/{docId}/characters/{charId}/style
Request: {"style": {"font": "Times New Roman", "size": 14, "bold": false}}
Response: 200 OK
{"characterId": "char-1", "newStyleId": "style-hash-def456"}

---

GET /api/v1/documents/{docId}/stats
Response: 200 OK
{
  "totalCharacters": 100000,
  "distinctStyles": 5,
  "memorySaved": "3.2 MB (80% reduction via Flyweight)"
}
```

---

## 3. ER Diagram & Database Design

```sql
-- Styles stored ONCE, referenced by many characters (mirrors Flyweight in DB!)
CREATE TABLE character_styles (
    style_id VARCHAR(50) PRIMARY KEY,  -- Hash of style attributes
    font VARCHAR(50) NOT NULL,
    size INT NOT NULL,
    color VARCHAR(20) NOT NULL,
    bold BOOLEAN DEFAULT FALSE,
    italic BOOLEAN DEFAULT FALSE,
    underline BOOLEAN DEFAULT FALSE,
    
    UNIQUE (font, size, color, bold, italic, underline)  -- Ensures no duplicate styles
);

CREATE TABLE document_characters (
    char_instance_id VARCHAR(50) PRIMARY KEY,
    document_id VARCHAR(50) NOT NULL,
    character CHAR(1) NOT NULL,
    row_position INT NOT NULL,
    col_position INT NOT NULL,
    style_id VARCHAR(50) NOT NULL,  -- FK reference, not embedded style data!
    
    FOREIGN KEY (style_id) REFERENCES character_styles(style_id),
    INDEX idx_document_position (document_id, row_position, col_position)
);
```

**You**: "Notice the schema MIRRORS the Flyweight Pattern - `character_styles` table has UNIQUE constraint ensuring no duplicate style rows, and `document_characters` REFERENCES styles by foreign key rather than embedding style columns directly. This is Flyweight applied to database design!"

---

## 4. Sequence Diagrams

```
User    Document   CharacterStyleFactory   StyleCache(Map)
  │        │               │                    │
  │─typeChar('H', Arial-12-Bold)▶│                    │
  │        ├─getStyle(Arial,12,Bold)─▶│                    │
  │        │               ├─computeKey()─────▶│                    │
  │        │               │  key = "Arial-12-Bold"       │
  │        │               ├─cache.get(key)───────────────▶│
  │        │               │◀─── null (not cached) ────────│
  │        │               │  Create NEW CharacterStyle    │
  │        │               ├─cache.put(key, newStyle)──────▶│
  │        │◀style─────────│                    │
  │        │  Create CharacterInstance('H', pos, style)    │
  │        │                                                │
  │─typeChar('e', Arial-12-Bold)▶│                    │        (Same style again!)
  │        ├─getStyle(Arial,12,Bold)─▶│                    │
  │        │               ├─cache.get(key)───────────────▶│
  │        │               │◀─── EXISTING style object! ───│
  │        │◀style (SHARED reference)│                    │
  │        │  Create CharacterInstance('e', pos, SAME style)│
```

**You**: "Second character reuses the EXACT SAME `CharacterStyle` object reference - no new allocation! This is the core Flyweight optimization."

---

## 5. Scenario-First Explanations

### **5.1 Why Separate Intrinsic (Shared) from Extrinsic (Unique) State?**

**You**: "This distinction IS the Flyweight Pattern:

```java
// INTRINSIC state (shared, immutable) - the Flyweight
class CharacterStyle {
    private final String font;
    private final int size;
    private final String color;
    private final boolean bold;
    private final boolean italic;
    
    // Immutable - no setters! Once created, never changes
    CharacterStyle(String font, int size, String color, boolean bold, boolean italic) {
        this.font = font;
        this.size = size;
        this.color = color;
        this.bold = bold;
        this.italic = italic;
    }
    
    void render(char c, int row, int col) {  // Extrinsic passed as parameters!
        // Rendering logic using shared style + unique position
    }
}

// EXTRINSIC state (unique per character) - the Context
class CharacterInstance {
    private final char character;      // Unique to this instance
    private int row, col;              // Unique position
    private CharacterStyle style;      // SHARED reference to Flyweight!
    
    void render() {
        style.render(character, row, col);  // Delegate, passing unique data
    }
}

// Flyweight Factory - ensures sharing
class CharacterStyleFactory {
    private static Map<String, CharacterStyle> styleCache = new ConcurrentHashMap<>();
    
    static CharacterStyle getStyle(String font, int size, String color, 
                                    boolean bold, boolean italic) {
        String key = font + "-" + size + "-" + color + "-" + bold + "-" + italic;
        
        return styleCache.computeIfAbsent(key, k -> 
            new CharacterStyle(font, size, color, bold, italic)
        );
    }
}
```

**Key rule**: If ALL characters had unique font/size/color combinations, Flyweight provides ZERO benefit. Flyweight only helps when there's **significant repetition** in the shared state - which is realistic for documents (most text uses 2-5 distinct styles: body text, headers, bold emphasis, etc.)"

### **5.2 Why Immutability of Flyweight Objects is Critical**

**You**: "If `CharacterStyle` were mutable and shared across 1000 characters, changing ONE character's style would accidentally affect all 999 others sharing that reference!

```java
// ❌ DANGEROUS if CharacterStyle were mutable:
CharacterStyle sharedBoldStyle = factory.getStyle("Arial", 12, "black", true, false);
charA.setStyle(sharedBoldStyle);
charB.setStyle(sharedBoldStyle);  // Both share SAME object

sharedBoldStyle.setColor("red");  // 🔥 OOPS! Both charA AND charB turn red!
```

**Solution**: Style objects are IMMUTABLE. To 'change' a character's style, you get a DIFFERENT flyweight from the factory (or create new), you never mutate the shared object:

```java
// ✅ CORRECT: Changing style = getting a NEW flyweight reference
void changeCharacterColor(CharacterInstance instance, String newColor) {
    CharacterStyle oldStyle = instance.getStyle();
    CharacterStyle newStyle = factory.getStyle(
        oldStyle.getFont(), oldStyle.getSize(), newColor,  // New color!
        oldStyle.isBold(), oldStyle.isItalic()
    );
    instance.setStyle(newStyle);  // Just swap the REFERENCE, old style untouched
}
```"

---

## 6. Cross Questions

**Interviewer**: "How does this design handle 'select all bold text and change to italic'?"

**You**: "Iterate all CharacterInstances, filter by style.isBold(), and batch-update:

```java
class DocumentFormatter {
    void applyItalicToAllBold(Document doc) {
        for (CharacterInstance instance : doc.getCharacters()) {
            if (instance.getStyle().isBold()) {
                CharacterStyle newStyle = factory.getStyle(
                    instance.getStyle().getFont(),
                    instance.getStyle().getSize(),
                    instance.getStyle().getColor(),
                    true,  // Keep bold
                    true   // Add italic
                );
                instance.setStyle(newStyle);
            }
        }
    }
}
```

Since styles are cached by the factory, if 500 characters were bold-Arial-12, they now all share ONE new bold-italic-Arial-12 flyweight instead of 500 separate updates each allocating memory."

---

## 7. Trade-offs

### **Flyweight vs Simple Per-Character Objects**

| Aspect | Flyweight (Shared Style) | Naive (Style per Character) |
|--------|----------------------------|---------------------------------|
| **Memory** | O(distinct styles) + O(N) references | O(N) full style objects |
| **Complexity** | Higher (factory, caching) | Lower |
| **Best for** | Large documents, repeated formatting | Tiny documents (memory not a concern) |

**You**: "For a 500-page document (millions of characters) with typical formatting reuse, Flyweight saves gigabytes of memory. For a 10-character text field, the pattern is overkill."

---

## 8. Senior Trap Questions

### **Trap: "Just cache everything in one global HashMap, simpler!"**

**✅ Senior**: "The factory-based caching (`computeIfAbsent` on a key derived from ALL style attributes) is exactly the right approach - but the KEY GENERATION matters. If you use `style.hashCode()` naively without ensuring `equals()`/`hashCode()` contracts are correctly implemented (all attributes included, consistent ordering), you'll get either FALSE cache hits (bug: two different styles collide) or ZERO cache hits (no memory savings). Must implement proper structural equality."

---

## 9. Technology Choices

**You**: "For collaborative editing (Google Docs style) on top of this: **Operational Transformation (OT)** or **CRDTs** for conflict-free concurrent edits, **WebSocket** for real-time sync. The Flyweight pattern for styling remains valid regardless of the collaboration layer."

---

## 🎓 **Final Tips**

1. **Flyweight = Intrinsic (shared) vs Extrinsic (unique) state separation**
2. **Factory ensures sharing**: `computeIfAbsent` pattern for cache-or-create
3. **Immutability is mandatory**: Shared objects must never be mutated
4. **Real memory savings**: Calculate and mention actual numbers (80%+ reduction typical)

Good luck! Word Processor is THE canonical Flyweight Pattern question - memory efficiency through sharing immutable state. 🚀
