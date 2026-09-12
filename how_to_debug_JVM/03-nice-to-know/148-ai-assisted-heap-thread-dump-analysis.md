# #148 — Using AI/LLMs to Accelerate Heap & Thread Dump Root Cause Analysis

> **Category:** Modern Observability (2026) | **Type:** Advanced Scenario Q&A | **Priority:** 📘 Advanced (2026 additions)

## 🗣️ The Interview Question
"You have a 4GB heap dump from a production OOM, and a stakeholder wants a root cause in 30 minutes, not the usual 2 hours of manual MAT clicking. How do you responsibly use AI tooling to speed this up, without just guessing?"

## 😊 Explain It Simply (for anyone)
Imagine handing a huge pile of financial statements to a smart junior analyst and asking them to circle anything that looks suspicious, before the senior auditor spends their limited time double-checking only those circled items. The junior analyst doesn't sign off on the final report — they just make the senior auditor's search 10x faster by narrowing 200 possible pages down to 5 worth a close look. Using an LLM on a heap dump works the same way: it doesn't replace understanding the dominator tree or GC roots (file #005) — it reads the *summary report* MAT already generates and helps you rank hypotheses faster, so you spend your 30 minutes verifying the top 2 suspects instead of manually reading through 200 candidate classes.

## 📊 Visualize It
```
4GB heap dump (hprof, BINARY — an LLM cannot ingest this directly)
        │
        ▼
Eclipse MAT batch mode (offline, scriptable):
  ./ParseHeapDump.sh heapdump.hprof \
      org.eclipse.mat.api:suspects \
      org.eclipse.mat.api:overview
        │
        ▼
Structured TEXT/HTML report:
  - Leak Suspects (top classes by retained size)
  - Instance counts, GC root paths
  - Dominator tree summary
        │
        ▼
Feed EXTRACTED TEXT (not the binary) + recent git diff
into an LLM: "rank these leak suspects against this diff"
        │
        ▼
Ranked hypotheses  →  human verifies top 1-2 against actual code
        │
        ▼
Confirmed root cause (human signs off, not the AI)
```

## 🏭 The Real Production Answer (15-YOE Level)
"The key nuance interviewers want to hear: **you cannot feed a 4GB binary `.hprof` file to an LLM** — there's no context window that fits it, and even if there were, an LLM can't parse the JVM heap dump binary format. What actually works is a two-stage pipeline where MAT (or a similar heap analyzer) does the heavy structural analysis first, and the LLM operates only on the *extracted, structured summary*:

**Step 1 — Extract, don't upload raw:** run Eclipse MAT's batch/headless mode to generate its automated Leak Suspects report without opening the GUI:
```bash
./ParseHeapDump.sh /tmp/heapdump.hprof \
  org.eclipse.mat.api:suspects \
  org.eclipse.mat.api:overview
```
This produces an HTML/text report with the top classes by retained size, instance counts, and GC root paths — the same data I'd manually click through in MAT's UI (dominator tree, shallow vs retained heap from file #005), just already summarized.

**Step 2 — Give the LLM structured context, not raw data:** I copy the top 10-15 leak-suspect entries (class name, retained size, instance count, GC root type) as plain text into the prompt, alongside the service's recent `git log`/diff for the affected module and its known dependency-version bumps. I ask it explicitly to correlate: 'given these leak suspects and this diff, which change is the most plausible root cause, and why?' This is genuinely useful because an LLM can spot a pattern like 'the #2 suspect class was introduced by the caching library bumped in this diff three days before the incident' faster than I can manually cross-reference a changelog against 200 candidate classes.

**Step 3 — Verify, don't trust.** The LLM's ranked hypothesis is a **lead, not a verdict**. I always go back into MAT and manually confirm the GC root chain for whatever the LLM flagged as most likely — because LLMs can and do produce confident-sounding but wrong explanations when given an incomplete GC root chain or when they don't actually understand shallow-vs-retained heap semantics (they'll happily explain it wrong if you don't check). The human is still the one who signs off on the root cause in the postmortem.

**Where else I've used this pattern (equally valid to mention):** asking an LLM to draft an Arthas OGNL expression (file #141) I don't remember the exact syntax for, or a JFR/JMC query for a specific event type — using AI as a **syntax co-pilot** for tools you use rarely, always followed by running it against a real system and confirming the output makes sense, not blindly pasting and trusting.

**The governance point that separates a senior answer from a junior one:** never upload a raw production heap dump — which can contain live customer PII sitting in String/byte[] objects on the heap — to a public LLM API. Either redact to class-level metadata only (as above, which contains no actual object *values*, just class names/sizes/counts), or use an internal/on-prem model approved by your security team for anything closer to raw data. This is a real compliance conversation in regulated shops (finance, healthcare) and interviewers notice when you raise it unprompted."

## 🔑 Key Takeaway
AI accelerates heap dump root-causing by ranking hypotheses from MAT's *extracted, structured* leak-suspects report cross-referenced with recent code changes — never by ingesting the raw binary dump — and the human always verifies the GC root chain before signing off, because LLMs can produce confident-sounding wrong answers on incomplete data.
