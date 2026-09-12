# #149 — "eBPF Profiling Has Zero Overhead, So Just Leave It Always On Everywhere" (Trap)

> **Category:** Modern Observability (2026) | **Type:** Senior Trap Question | **Priority:** 📘 Advanced (2026 additions)

## 🗣️ The Interview Question
"eBPF-based continuous profiling is marketed as 'near-zero overhead.' So we should just enable it fleet-wide, at max sampling frequency, on every service, all the time, right?"

## 😊 Explain It Simply (for anyone)
Imagine a security camera company says their cameras use "almost no extra electricity." That's true for one camera — but if you're told to install 10,000 of them recording in ultra-high-definition, at every angle, all running at once, the "almost no" electricity per camera adds up to a genuinely large power bill, and you also now need to ask the building's electrician (security/compliance team) for permission to wire that many cameras into every room, including ones with sensitive documents. "Low overhead per instance" does not mean "zero cost to deploy everywhere blindly, at maximum settings, without asking anyone."

## 📊 Visualize It
```
"Near-zero overhead" claim breaks down once you consider:

┌───────────────────────────────────────────────────────────┐
│ 1. SAMPLING FREQUENCY MATTERS                                │
│    99Hz (default-ish) CPU sampling  ≈ 1-3% overhead          │
│    High-freq off-CPU/lock-contention profiling ≈ 5%+          │
│    "Always on everywhere at max detail" ≠ "always negligible" │
├───────────────────────────────────────────────────────────┤
│ 2. PRIVILEGE REQUIREMENTS                                     │
│    Needs CAP_BPF / CAP_SYS_ADMIN + often hostPID: true        │
│    = security review required in regulated environments        │
├───────────────────────────────────────────────────────────┤
│ 3. STORAGE/INGEST COST AT FLEET SCALE                          │
│    300 pods × continuous profile pushes = real backend cost   │
├───────────────────────────────────────────────────────────┤
│ 4. THE AGENT ITSELF CAN FAIL/CRASH                             │
│    A privileged DaemonSet bug can affect EVERY pod on a node   │
└───────────────────────────────────────────────────────────┘
```

## 🏭 The Real Production Answer (15-YOE Level)
"'Near-zero overhead' is a marketing simplification of 'low overhead at sane default settings, on a reasonable number of instances' — and treating it as literally free changes the rollout plan entirely:

**1. Overhead is real and tunable, not zero.** Default CPU sampling (commonly ~19-99Hz depending on the tool) typically costs 1-3% CPU per instrumented process — genuinely low, and usually an acceptable trade for the visibility gained. But overhead scales with sampling frequency and with *what* you profile: enabling off-CPU/lock-contention profiling (which needs to hook scheduler events, not just periodic stack sampling) is meaningfully more expensive than plain CPU sampling. 'Always on, everywhere, at max detail' is a different cost profile than the benchmark number in the vendor's blog post, which is almost always measured at conservative default settings.

**2. Privilege escalation is a security conversation, not a config flag.** eBPF profilers need `CAP_BPF`/`CAP_SYS_ADMIN` (or the newer, narrower eBPF-specific capabilities on recent kernels) and frequently `hostPID: true` to see all processes on a node. In a PCI-DSS or HIPAA-scoped environment, granting a DaemonSet that level of node access to every namespace, including ones handling regulated data, is exactly the kind of change that needs a security review and a scoped rollout (start on non-regulated namespaces, expand after sign-off) — not a fleet-wide day-one enablement.

**3. Ingest/storage cost compounds at fleet scale.** One pod profiling continuously is cheap. Three hundred pods, each pushing compressed profiles every 10-15 seconds, 24/7, is a real and continuous cost on the profiling backend (Pyroscope/Parca storage, or the SaaS vendor's continuous-profiler line item) — worth sizing before flipping it on everywhere, same as you'd size any other new telemetry pipeline.

**4. The agent is itself a new failure domain.** Because the profiling agent runs privileged and node-wide (one DaemonSet pod serving every workload on that node), a bug or resource spike in the agent itself can affect every single pod co-located on that node — it's a blast-radius trade-off you're accepting in exchange for the visibility, and it deserves the same canary rollout discipline (one node pool first, watch for a week, then expand) that any other privileged infrastructure change gets.

**What I actually recommend:** enable continuous profiling incrementally — start with your highest-value, highest-incident-rate services on a subset of nodes, confirm real overhead numbers in *your* environment (not the vendor's benchmark), get the security sign-off for the required capabilities, then expand fleet-wide. Treat it like any other privileged, always-on infrastructure component — because that's exactly what it is."

## 🔑 Key Takeaway
"Near-zero overhead" describes conservative default settings on a reasonable footprint — fleet-wide, max-detail, day-one rollout of a privileged, node-wide profiling agent is a real cost, security-review, and blast-radius decision that deserves a canary rollout, not a single config flag flipped everywhere at once.
