# When Would You NOT Use Function Composition?
> **Topic:** Composition | **Level:** Senior Trap | **Frequency:** Medium

## The Setup
You have just given a polished explanation of compose and pipe with real-world examples. The interviewer follows up: "You clearly like composition. Tell me when you would deliberately NOT use it."

## The Question
When would you NOT use function composition?

## Diagram

```
Cases where composition is the wrong tool:

  BRANCHING LOGIC:
  if (user.isPremium) applyPremiumPricing()   <-- pipeline is a straight line
  else applyStandardPricing()                 <-- branching = explicit code, not pipe

  ERROR CONTEXT:
  pipe(parse, validate, enrich, save)
  -- if validate throws, which record failed? what input caused it?
  -- a thrown exception loses stage context unless you wrap every stage
  -- at that point the pipe abstraction adds noise, not clarity

  TINY PIPELINES:
  pipe(f, g)(x)   vs   g(f(x))               <-- ceremony > benefit at 1-2 stages

  TEAM UNFAMILIARITY:
  const process = pipe(sanitize, addDefaults, toApiShape);
  -- a team new to FP needs to decode this
  -- named for-loop block is more readable to that team
```

## Model Answer (15 YOE)

Four cases where I deliberately avoid function composition:

**First, branching logic.** A pipeline is a straight line. When a stage has `if (user.isPremium) applyPremiumPricing()`, the condition requires access to the argument — you need explicit code, not a pipeline. Trying to force branching into compose leads to awkward `ifElse` combinators (Ramda has one) that are harder to read than a plain conditional.

**Second, when you need rich error context mid-pipeline.** A `throw` inside any stage rejects or propagates up with the error message, but you lose which stage failed, what the input was, and what the intermediate state looked like. Wrapping every stage in try/catch defeats the abstraction. For pipelines where failure diagnosis matters — payment processing, data ingestion with user-facing error messages — I prefer explicit `try/catch` blocks with structured logging between stages.

**Third, pipelines with only one or two stages.** `pipe(f, g)(x)` is more ceremony than `g(f(x))`. The compose pattern earns its keep at three or more stages where the linear readability or testability benefit becomes visible.

**Fourth, onboarding a team new to functional patterns.** A well-named sequential function block is more readable to that team than a compose chain they need to decode. I introduce the pattern incrementally — extract one stage as a named function first, show the unit test benefit, then propose the `pipe` call once they understand why the stages exist.

## Follow-up

**Q:** Is there a middle ground between full composition and a monolithic function?

**A:** Yes — named sequential calls without a `pipe` utility. Extract each stage as a pure named function, call them sequentially with explicit variable assignment between steps. This gives you the testability of composition (each stage independently testable) without the `pipe` abstraction overhead. It is the right choice when the team is unfamiliar with FP or when intermediate values need logging or type assertions between steps.

## Why It's a Trap

This question separates engineers who understand the tool from those who use it everywhere. A confident "I always use composition" answer signals a pattern zealot. The interviewer wants to hear that you understand the trade-offs and apply judgment, not enthusiasm.

## What NOT to Say

- "I always use compose — it's always better than alternatives" — signals dogmatic thinking
- "I can't think of a case where I wouldn't use it" — shows limited experience with real codebases
- Listing only trivial cases ("for short functions") without mentioning branching, error context, or team dynamics
