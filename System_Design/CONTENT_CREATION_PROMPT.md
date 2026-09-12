# Content Creation Prompt — System Design Topic
> Copy this entire prompt into Claude Code or GitHub Copilot Chat.
> Replace `{SOURCE_FILE}` with the actual file path before running.

---

## PROMPT (copy below this line)

---

**Task:** Create LinkedIn post, YouTube script, and visual HTML carousel for one system design topic. Use parallel agents. Verify everything after creation.

**Source file:** `{SOURCE_FILE}`
Example: `/Users/I771246/Abhi Personal/JavaFullstackNotes/System_Design/003-database-scaling-sharding.md`

---

### STEP 1 — Read the FULL source file

Before writing anything:
1. Read the ENTIRE source `.md` file from line 1 to the last line — do NOT stop at 200 lines.
2. Extract and note:
   - Every scenario with its problem + solution
   - Every trap/anti-pattern
   - All technology comparisons
   - The cheat sheet / interview quote at the end
   - All real-world company examples with numbers
3. Only proceed to Step 2 after reading the complete file.

---

### STEP 2 — Create the folder and move the source file

1. Derive the folder name from the source filename by removing the `.md` extension.
   - Example: `003-database-scaling-sharding.md` → folder name `003-database-scaling-sharding`
2. Create the folder at the same location as the source file.
3. Move the source `.md` file INTO that new folder.
   - Final location: `{folder}/003-database-scaling-sharding.md`

---

### STEP 3 — Create 3 files IN PARALLEL using 3 agents

Launch 3 agents simultaneously. Each agent reads the source file independently and creates one output file inside the new folder.

---

#### Agent 1 — `youtube_script.md`

Write a full narrated YouTube video script, 8–12 minutes, targeting engineers with 3–10 YOE.

Structure (include exact timestamps and screen cues):

```
# {Topic Name} — YouTube Script
Duration: ~10 min | Target: Engineers 3–10 YOE | Episode: {N} of 20

## HOOK (0:00–0:30)
[Shocking opening — a real outage, a real failure, a surprising number]
[Screen cue: what to show on screen]

## THE PROBLEM (0:30–2:00)
[Plain English — what breaks without understanding this concept]
[Conversational, no jargon. "Think about it this way..."]
[Screen cue: describe the diagram]

## THE SOLUTION (2:00–5:00)
[Step-by-step explanation. "Now watch what happens when..."]
[Cover ALL scenarios from the source file]
[Screen cue: describe live diagram to draw]

## DEEP DIVE — WHERE ENGINEERS GET IT WRONG (5:00–8:00)
[Every trap, anti-pattern, edge case from the source file]
[Real numbers. Real company examples.]
[Screen cue: comparison table or state machine]

## REAL WORLD (8:00–9:30)
[2–3 Indian tech company examples: Swiggy/Flipkart/Paytm/Zomato/PhonePe]
[Include specific numbers: latency, throughput, scale]
[Screen cue: company logo + numbers]

## OUTRO + NEXT EPISODE (9:30–10:00)
[Subscribe hook. Tease next episode by name.]
```

Rules:
- Write as actual spoken words. Conversational. "Now, here's the thing..."
- Every scenario from the source `.md` must appear somewhere in the script.
- Every trap from the source `.md` must be covered in the Deep Dive section.
- Include specific numbers from the source file (latency, row counts, percentages).

---

#### Agent 2 — `linkedin_post.md`

Write a LinkedIn post that makes an engineer stop scrolling.

```markdown
# {Topic Name} — LinkedIn Post

## Post Text (copy-paste ready)

{Hook line — pain point or surprising stat. 1 sentence. Max 120 chars.}

{3–5 bullet points covering the core insight. Short. No fluff.}

{1 line describing what the carousel shows — "Swipe → to see:"}

{CTA: "Save this. You'll need it in your next system design interview."}

{hashtags: #SystemDesign #SoftwareArchitecture #InterviewPrep #Backend}

---

## Caption Variants

### Variant A — Short (150 chars max)
{punchy caption for sharing the video link}

### Variant B — Long (400–600 chars)
{standalone post that works without a video or carousel}

---

## Best Time to Post
{Day + time for Indian tech audience}

## Engagement Hook
{A question to add at the end to drive comments}
```

Rules:
- Hook must reference a specific failure, number, or counterintuitive fact from the source file.
- Bullets must come directly from the source file's scenarios and traps — not generic advice.
- Must include at least one real company + real number from the source file.

---

#### Agent 3 — `carousel.html`

Create a self-contained HTML file with visual slides. 8–10 slides. Dark theme (#1a1a2e background).

**Visual requirements (mandatory):**
- Database icons: CSS-drawn cylinders (top ellipse + body rectangle + bottom ellipse) with color themes
- Redis: circular red (#d82c20) icon with "R" label
- Server boxes: CSS rectangles with horizontal lines
- Polyglot persistence icons: labeled colored squares (PG=blue, CAS=yellow, ES=green, Redis=red)
- Arrows connecting components (CSS text arrows or borders)
- NO generic emoji as primary visuals — use CSS-drawn components

**Slide structure (derive from source file):**
- Slide 1: HOOK — shocking stat or failure story from source file
- Slide 2: THE PROBLEM — visual diagram showing the bottleneck
- Slides 3–N: One slide per major scenario/concept from the source file
- Second-to-last slide: Technology comparison table or polyglot overview
- Last slide: Decision tree + exact interview quote from source file's cheat sheet

**HTML technical requirements:**
- Arrow key navigation (← →) + Prev/Next buttons
- Slide counter (e.g. "3 / 10")
- `@media print` with `@page { size: 540px 540px; margin: 0; }` — each slide prints as one page
- `-webkit-print-color-adjust: exact` and `print-color-adjust: exact` on all slide elements
- Self-contained: no external CDN, no external fonts
- All 8–10 slides visible and navigable

**Coverage rule:** Every scenario, every trap, every technology comparison in the source `.md` must appear in at least one slide.

---

### STEP 4 — Verify (after all 3 agents complete)

Run these checks:

1. **Coverage check**: Read the source `.md` file again. List every scenario and trap. Confirm each one appears in the carousel AND the YouTube script.

2. **File check**: Confirm all 3 files exist in the new folder:
   - `{folder}/youtube_script.md` — check it has all 6 sections with timestamps
   - `{folder}/linkedin_post.md` — check hook is present, bullets are specific (not generic), CTA is there
   - `{folder}/carousel.html` — check slide count, CSS icons are present, print CSS is present

3. **Source file location check**: Confirm the original `.md` was moved into the folder (not left at the original location).

4. **Fix anything missing**: If a scenario from the source file is missing from any output, add it before reporting done.

---

### EXPECTED OUTPUT STRUCTURE

```
System_Design/
  003-database-scaling-sharding/
    003-database-scaling-sharding.md    ← moved here from parent
    youtube_script.md
    linkedin_post.md
    carousel.html
```

---

### NOTES FOR CLAUDE MULTI-AGENT

When running in Claude Code with multi-agent support:
- Step 1 (read file) and Step 2 (create folder + move file) must complete BEFORE launching agents.
- Step 3: launch all 3 agents in a single parallel call — they each re-read the source file independently.
- Step 4: run verification sequentially after all 3 agents complete.

When running in GitHub Copilot Chat:
- Run steps 1–4 sequentially (Copilot does not support parallel agents).
- After step 3, explicitly ask Copilot to verify coverage before closing.

---
*Prompt version: 1.0 | Repo: JavaFullstackNotes/System_Design*
