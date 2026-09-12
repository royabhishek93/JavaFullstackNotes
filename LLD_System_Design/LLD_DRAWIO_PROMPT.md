# LLD draw.io Diagram Prompt
> Copy this entire prompt into Claude Code or GitHub Copilot Chat.
> Replace `{SOURCE_FILE}` with the actual `.md` file path before running.

---

## PROMPT (copy below this line)

---

**Task:** Create a 2-page draw.io diagram from one LLD design `.md` file.
- Page 1: UML Class Diagram (all interfaces, classes, relationships)
- Page 2: Sequence Diagram (main operation flow — happy path + failure path)

**Source file:** `{SOURCE_FILE}`
Example: `/Users/I771246/Abhi Personal/JavaFullstackNotes/LLD_System_Design/01_Rate_Limiter.md`

---

### STEP 1 — Read the FULL source file

Before writing any XML:
1. Read the ENTIRE `.md` file from line 1 to the last line — do NOT stop at 200 lines.
2. Extract and note:
   - Every interface name + its methods
   - Every concrete class name + its fields + its methods
   - All inheritance relationships (A extends B)
   - All composition/association relationships (A has-a B)
   - Design patterns explicitly mentioned (Factory, Strategy, Observer, Singleton, etc.)
   - The main operation flow (the primary use-case method call chain)
   - Any failure/rejection path described
3. Only proceed to Step 2 after reading the complete file.

---

### STEP 2 — Create the subfolder and move the source file

1. Derive the folder name from the source filename by removing the `.md` extension.
   - Example: `01_Rate_Limiter.md` → folder name `01_Rate_Limiter`
2. Create the folder at the same location as the source file.
3. Move the source `.md` file INTO that new folder.
   - Final location: `LLD_System_Design/01_Rate_Limiter/01_Rate_Limiter.md`

---

### STEP 3 — Generate the `.drawio` file

Create `{folder_name}.drawio` inside the new subfolder.

File structure: `LLD_System_Design/01_Rate_Limiter/01_Rate_Limiter.drawio`

The file must be valid XML with exactly **2 `<diagram>` tags**: one for the Class Diagram and one for the Sequence Diagram.

---

#### Page 1 — Class Diagram

**Layout rules:**
- Interfaces in the top row, concrete classes below them, utility/config classes at the bottom
- Leave at least 40px gap between cells
- Group related classes visually (e.g., all algorithm implementations in a column)

**Cell styles to use:**

| Element | draw.io style |
|---|---|
| Interface | `swimlane;fontStyle=3;startSize=40;fillColor=#dae8fc;strokeColor=#6c8ebf;` |
| Concrete class | `swimlane;startSize=30;fillColor=#fff2cc;strokeColor=#d6b656;` |
| Utility / config | `swimlane;startSize=30;fillColor=#d5e8d4;strokeColor=#82b366;` |
| Field / method row | `text;align=left;verticalAlign=top;spacingLeft=4;overflow=hidden;` |
| Extends (hollow arrow) | `endArrow=block;endFill=0;` edge="1" |
| Implements (dashed hollow) | `endArrow=block;endFill=0;dashed=1;` edge="1" |
| Composition (diamond) | `endArrow=ERmandOne;startArrow=ERmanyToOne;` edge="1" |
| Association (plain) | `endArrow=open;` edge="1" |

**Class cell structure:**
```xml
<!-- Interface example -->
<mxCell id="iface_RateLimiter" value="«interface»&#xa;RateLimiter" style="swimlane;fontStyle=3;startSize=40;fillColor=#dae8fc;strokeColor=#6c8ebf;" vertex="1" parent="1">
  <mxGeometry x="200" y="80" width="200" height="120" as="geometry"/>
</mxCell>
<mxCell id="iface_RateLimiter_m1" value="+ allowRequest(userId: String): boolean" style="text;align=left;verticalAlign=top;spacingLeft=4;overflow=hidden;" vertex="1" parent="iface_RateLimiter">
  <mxGeometry y="40" width="200" height="30" as="geometry"/>
</mxCell>

<!-- Concrete class example -->
<mxCell id="class_TokenBucket" value="TokenBucketRateLimiter" style="swimlane;startSize=30;fillColor=#fff2cc;strokeColor=#d6b656;" vertex="1" parent="1">
  <mxGeometry x="200" y="260" width="200" height="150" as="geometry"/>
</mxCell>
<mxCell id="class_TokenBucket_f1" value="- tokens: int" style="text;align=left;verticalAlign=top;spacingLeft=4;overflow=hidden;" vertex="1" parent="class_TokenBucket">
  <mxGeometry y="30" width="200" height="25" as="geometry"/>
</mxCell>

<!-- Implements arrow -->
<mxCell id="edge_TokenBucket_impl" style="endArrow=block;endFill=0;dashed=1;" edge="1" source="class_TokenBucket" target="iface_RateLimiter" parent="1">
  <mxGeometry relative="1" as="geometry"/>
</mxCell>
```

**Requirements:**
- Every interface from the `.md` must appear as a cell with `«interface»` in the value
- Every concrete class must appear with all its fields (prefix `-`) and methods (prefix `+`)
- Every relationship in the `.md` must have a corresponding edge cell
- Add a label to edges where a design pattern is involved (e.g., `«creates»` on Factory edges)

---

#### Page 2 — Sequence Diagram

**What to show:**
- The main operation flow (e.g., for Rate Limiter: `allowRequest()` call chain)
- Participants (lifelines): Client, Factory/Service, Algorithm, Storage (Redis/DB)
- Happy path: request allowed
- Failure/rejection path: request denied or limit exceeded
- Use `alt` / `opt` frame for conditional branches

**Cell styles to use:**

| Element | draw.io style |
|---|---|
| Lifeline header | `shape=umlLifeline;perimeter=mxPerimeter.RectanglePerimeter;whiteSpace=wrap;` |
| Activation box | `shape=activation;` |
| Message arrow (sync) | `endArrow=block;endFill=1;` edge="1" |
| Return arrow (dashed) | `endArrow=open;dashed=1;` edge="1" |
| Alt/opt frame | `swimlane;startSize=20;fillColor=none;dashed=1;` |

**Sequence cell structure:**
```xml
<!-- Lifeline -->
<mxCell id="life_Client" value="Client" style="shape=umlLifeline;perimeter=mxPerimeter.RectanglePerimeter;whiteSpace=wrap;" vertex="1" parent="1">
  <mxGeometry x="80" y="40" width="100" height="400" as="geometry"/>
</mxCell>

<!-- Message arrow -->
<mxCell id="msg_1" value="allowRequest(userId)" style="endArrow=block;endFill=1;" edge="1" source="life_Client" target="life_RateLimiter" parent="1">
  <mxGeometry relative="1" as="geometry">
    <Array as="points"/>
  </mxGeometry>
</mxCell>

<!-- Return arrow -->
<mxCell id="ret_1" value="true / false" style="endArrow=open;dashed=1;" edge="1" source="life_RateLimiter" target="life_Client" parent="1">
  <mxGeometry relative="1" as="geometry"/>
</mxCell>
```

---

### STEP 3 — Full XML template

Use this skeleton and fill in all cells derived from Step 1:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<mxfile host="Electron" modified="2024-01-01T00:00:00.000Z" agent="Claude" version="21.0.0">
  <diagram name="Class Diagram" id="page1">
    <mxGraphModel dx="1422" dy="762" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="1654" pageHeight="1169" math="0" shadow="0">
      <root>
        <mxCell id="0" />
        <mxCell id="1" parent="0" />

        <!-- ═══════════════════════════════════════════════════ -->
        <!--   INTERFACES  (top row, fillColor=#dae8fc)          -->
        <!-- ═══════════════════════════════════════════════════ -->

        <!-- INSERT INTERFACE CELLS HERE -->

        <!-- ═══════════════════════════════════════════════════ -->
        <!--   CONCRETE CLASSES  (middle rows, fillColor=#fff2cc) -->
        <!-- ═══════════════════════════════════════════════════ -->

        <!-- INSERT CLASS CELLS HERE -->

        <!-- ═══════════════════════════════════════════════════ -->
        <!--   UTILITY / CONFIG  (bottom, fillColor=#d5e8d4)     -->
        <!-- ═══════════════════════════════════════════════════ -->

        <!-- INSERT UTILITY CELLS HERE -->

        <!-- ═══════════════════════════════════════════════════ -->
        <!--   RELATIONSHIPS (edges)                             -->
        <!-- ═══════════════════════════════════════════════════ -->

        <!-- INSERT EDGE CELLS HERE -->

      </root>
    </mxGraphModel>
  </diagram>
  <diagram name="Sequence Diagram" id="page2">
    <mxGraphModel dx="1422" dy="762" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="1654" pageHeight="1169" math="0" shadow="0">
      <root>
        <mxCell id="0" />
        <mxCell id="1" parent="0" />

        <!-- ═══════════════════════════════════════════════════ -->
        <!--   LIFELINES  (one per participant)                  -->
        <!-- ═══════════════════════════════════════════════════ -->

        <!-- INSERT LIFELINE CELLS HERE -->

        <!-- ═══════════════════════════════════════════════════ -->
        <!--   MESSAGES (numbered in call order)                 -->
        <!-- ═══════════════════════════════════════════════════ -->

        <!-- INSERT MESSAGE EDGE CELLS HERE -->

        <!-- ═══════════════════════════════════════════════════ -->
        <!--   ALT FRAME (happy path vs. rejection)              -->
        <!-- ═══════════════════════════════════════════════════ -->

        <!-- INSERT ALT FRAME CELLS HERE -->

      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
```

---

### STEP 4 — Verify

Run these checks after creating the file:

1. **XML validity**: Parse the XML — confirm no unclosed tags, no unescaped `&` or `<` in values (use `&amp;` and `&lt;`).

2. **Diagram count**: Count `<diagram` tags in the file — must be exactly **2**.

3. **Class coverage**: Re-read the source `.md`. List every interface and class name. Confirm each appears as a cell `id` or `value` in Page 1.

4. **Relationship coverage**: List every "extends", "implements", "has-a" from the source `.md`. Confirm each has a corresponding edge cell in Page 1.

5. **Sequence coverage**: Confirm Page 2 shows the main operation's full call chain — from the entry point down to storage and back up to the caller.

6. **File location**: Confirm the `.drawio` file is inside the new subfolder, and the source `.md` was moved into that same subfolder.

7. **Render test**: Open the `.drawio` file in [diagrams.net](https://app.diagrams.net) or the draw.io desktop app. Both pages must render without errors.

---

### EXPECTED OUTPUT STRUCTURE

```
LLD_System_Design/
  01_Rate_Limiter/
    01_Rate_Limiter.md        ← moved here from parent folder
    01_Rate_Limiter.drawio    ← NEW: 2-page draw.io XML
```

---

### NOTES FOR CLAUDE MULTI-AGENT

When running in Claude Code with multi-agent support:
- Step 1 (read file) must complete BEFORE any other step.
- Step 2 (create folder + move file) must complete BEFORE Step 3.
- Step 3 (generate XML) and Step 4 (verify) run sequentially — draw.io XML must be complete before verification.

When running in GitHub Copilot Chat:
- Run all steps sequentially.
- After Step 3, explicitly ask Copilot to count `<diagram>` tags and list all class names before closing.

### NOTES FOR IDs

All `mxCell id` values must be **unique within the file**. Use a naming convention:
- Interfaces: `iface_{ClassName}`
- Classes: `class_{ClassName}`
- Fields: `{parentId}_f{N}` (e.g., `class_TokenBucket_f1`)
- Methods: `{parentId}_m{N}` (e.g., `iface_RateLimiter_m1`)
- Edges: `edge_{source}_{target}` or `edge_{description}`
- Lifelines: `life_{ParticipantName}`
- Messages: `msg_{N}` (numbered in call order)
- Returns: `ret_{N}`

---
*Prompt version: 1.0 | Repo: JavaFullstackNotes/LLD_System_Design*
