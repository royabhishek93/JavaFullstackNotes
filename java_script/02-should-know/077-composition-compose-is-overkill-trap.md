# "Compose is Overkill for Real Apps" — Defending Composition Pragmatically
> **Topic:** Composition | **Level:** Senior Trap | **Frequency:** Low

## The Setup
Mid-interview, the interviewer leans back and says: "Honestly, I think function composition is just for functional programming fanatics. It's overkill for real production apps. I've shipped five products without it. Convince me otherwise."

## The Question
Is function composition just a style preference, or does it have concrete practical value?

## Diagram

```
200-line processProduct (before):
  function processProduct(raw) {
    // parse...         25 lines
    // validate...      40 lines
    // enrichGst...     20 lines
    // normalize...     30 lines
    // formatForDb...   85 lines
    // all entangled — one change requires reading 200 lines
  }

pipe(parse, validate, enrichGst, normalize, formatForDb) (after):
  - 5 functions, 5-20 lines each
  - 5 independent unit tests: input -> output, no mocks, no DB
  - GST rate change: touch enrichGst only
  - Add normalizeBrand: insert between normalize and formatForDb
  - Reorder steps: change one line (the pipe call)
```

## Model Answer (15 YOE)

Compose is not a style preference — it is a maintenance tool. When a data pipeline has five sequential transforms, writing them as five small functions with a `pipe` call gives you: five independent unit tests (no integration setup), a single line to add/remove/reorder a step, and a self-documenting sequence. The alternative — one function or a chain of imperatives — fails all three.

Concrete evidence: I have shipped compose-based pipelines in payments and catalog services. The junior engineers on those teams found the patterns easier to work with, not harder. The onboarding question changed from "which part of this 200-line function handles GST?" to "read `enrichGst`." That is the return on investment.

The critique that composition is "FP fanatic" territory usually comes from seeing it misused — someone composing three trivial one-liners for style points. The tool earns its keep when the pipeline has 4+ stages, changes frequently, or is tested by a team rather than a sole author.

To be clear: I also know when not to use it. One or two stages: just call them in sequence. Branching logic: a compose pipeline is a straight line, so explicit `if` statements are the right tool. New team unfamiliar with FP: a named sequential function block is more readable. Compose is a tool with a job profile, not a universal hammer.

## Follow-up

**Q:** How do you make the case for compose to a team that is resistant to "functional style"?

**A:** Frame it around the problems they already feel, not the pattern name. "Our `processProduct` function is hard to test in isolation" — that is the pain. Propose extracting one stage as a named function with a unit test. Show the test: five lines, no setup. That lands better than "we should use functional composition." Once they see the testability improvement, the compose call is a natural next step.

## Why It's a Trap

The interviewer is baiting you into either: (a) defending composition dogmatically without business justification, or (b) agreeing that it's overkill to avoid conflict. Both are wrong. The strong answer defends it pragmatically with concrete evidence while acknowledging the cases where it genuinely is overkill.

## What NOT to Say

- "Composition is fundamental to functional programming and every serious JS engineer should know it" — sounds dogmatic, not persuasive
- "You're right, it's probably overkill for most apps" — shows no conviction, no depth
- "Ramda and fp-ts are the industry standard" — library names do not answer the business question
