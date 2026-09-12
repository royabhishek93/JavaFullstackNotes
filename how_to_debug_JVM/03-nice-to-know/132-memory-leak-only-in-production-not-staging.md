# #132 — Memory Leak That Only Reproduces in Production

> **Category:** Heap Dump Analysis | **Type:** Advanced Scenario Q&A | **Priority:** ⚙️ Expert/Niche

## 🗣️ The Interview Question
"OOM reproduces only in production. Staging has same heap size, same load. How do you find the difference?"

## 😊 Explain It Simply (for anyone)
Imagine two identical-looking kitchens (production and staging) that are supposed to be running the exact same recipe, but only one of them keeps catching fire. Since the recipe (code) is the same, something about the INGREDIENTS or the SETTINGS must actually be different — maybe the real kitchen (production) is fed genuinely large or oddly-shaped ingredients (real customer data with edge cases) that the test kitchen (staging) never sees because it uses cheap fake ingredients (mock data).

Or maybe someone quietly turned on an extra oven setting (a feature flag or config property) only in the real kitchen. Instead of guessing, you compare EVERY setting side-by-side between the two kitchens until you spot the one dial that's turned differently.

## 📊 Visualize It
```
STAGING                         PRODUCTION
  same heap size (Xmx)            same heap size (Xmx)
  same code version                same code version
  mock downstream responses  ≠     real downstream responses
  synthetic test data        ≠     real data (nulls, huge payloads)
  cache.enabled = false      ≠     cache.enabled = true   ← the diff!

Diff process:
  jcmd VM.flags            (staging)  vs  jcmd VM.flags            (prod)
  jcmd VM.system_properties (staging) vs  jcmd VM.system_properties (prod)
  MAT: File → Compare Baselines (staging.hprof vs prod.hprof)
       → prod-only object types reveal the divergent code path
```

## 🏭 The Real Production Answer (15-YOE Level)

This is a classic tracer investigation. The difference is almost always one of:
1. **Data volume** — production data has edge cases (null fields, large payloads, specific encodings) that staging doesn't have
2. **Configuration difference** — prod has a feature flag enabled that causes different code paths
3. **External system difference** — prod calls a real service that returns large responses; staging uses mocks
4. **Time-based** — leak only manifests after N hours; staging tests are shorter

Approach:
```bash
# 1. Diff JVM flags between environments
# prod vs staging: compare -XX flags, system properties
jcmd <pid> VM.flags > /tmp/jvm_flags_prod.txt  # On each env
diff jvm_flags_staging.txt jvm_flags_prod.txt

# 2. Diff application config
jcmd <pid> VM.system_properties | sort > /tmp/props_prod.txt

# 3. Capture heap dumps from BOTH environments after same time window
# Compare object histogram — what's different in prod?
# MAT: File → Compare Baselines → select both .hprof files

# 4. Enable verbose heap allocation sampling in staging with prod data
# Use async-profiler with production DB read replica traffic mirrored
```

Key insight: Use `jcmd <pid> VM.system_properties` to compare full config. A single property like `cache.enabled=true` only in prod can be the entire cause.

## 🔑 Key Takeaway
When a leak won't reproduce outside prod, diff the JVM flags, system properties, and data shape between environments instead of re-reading the code — the difference is usually one config flag or one data edge case.
