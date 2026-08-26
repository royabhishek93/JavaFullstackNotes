# React & JavaScript — 15 YOE Interview Prep Bundle

**2026 Edition | All files: conversational script + ASCII diagrams + scenario-based Q&As + senior trap questions + production TypeScript code**

---

## Interview Files (Priority Order)

| # | File | Topic | Stars | Study Time |
|---|------|--------|-------|------------|
| 01 | [01_react_hooks_internals_interview.md](01_react_hooks_internals_interview.md) | React Hooks & Fiber Internals | ⭐⭐⭐⭐⭐ | 50 min |
| 02 | [02_react_performance_optimization_interview.md](02_react_performance_optimization_interview.md) | React Performance Optimization | ⭐⭐⭐⭐⭐ | 50 min |
| 03 | [03_state_management_interview.md](03_state_management_interview.md) | State Management (Redux/Zustand/React Query) | ⭐⭐⭐⭐⭐ | 50 min |
| 04 | [04_typescript_advanced_interview.md](04_typescript_advanced_interview.md) | TypeScript Advanced (Generics, Utility Types) | ⭐⭐⭐⭐ | 45 min |
| 05 | [05_javascript_core_async_interview.md](05_javascript_core_async_interview.md) | JavaScript Core & Async (Event Loop, Closures) | ⭐⭐⭐⭐⭐ | 50 min |
| 06 | [06_react_architecture_patterns_interview.md](06_react_architecture_patterns_interview.md) | React Architecture Patterns | ⭐⭐⭐⭐ | 45 min |
| 07 | [07_testing_react_interview.md](07_testing_react_interview.md) | Testing React (RTL, Jest/Vitest, Playwright) | ⭐⭐⭐⭐ | 40 min |
| 08 | [08_nextjs_ssr_interview.md](08_nextjs_ssr_interview.md) | Next.js & SSR/RSC | ⭐⭐⭐⭐⭐ | 50 min |
| 09 | [09_build_tooling_web_performance_interview.md](09_build_tooling_web_performance_interview.md) | Build Tooling & Web Performance | ⭐⭐⭐⭐ | 40 min |
| 10 | [10_security_auth_interview.md](10_security_auth_interview.md) | Security & Authentication | ⭐⭐⭐⭐ | 40 min |

---

## What Each File Contains

Every file includes:
- **Big Picture ASCII diagram** — architecture, data flow, decision trees
- **Conversational script** — exactly how a 15-YOE engineer speaks in an interview
- **8+ Scenario Q&As** — production-context questions with full answers
- **4+ Advanced scenario Q&As** — deep-dive system design and internals
- **6+ Senior Trap Questions** — common mistakes named, correct answers explained
- **Production TypeScript code** — real-world examples, <20 lines each
- **Interview Cheat Sheet** — quick-reference tables and one-paragraph summaries

---

## 2-Day Prep Plan

**Day 1 (must-do):** 01 Hooks → 02 Performance → 05 JS Core → 08 Next.js

**Day 2 (round out):** 03 State Management → 04 TypeScript → 06 Architecture → 10 Security

**Quick refresh:** Read only the Cheat Sheet at the bottom of each file (2 min each)

---

## Key Numbers to Know Cold

| Metric | Value |
|--------|-------|
| LCP good threshold | < 2.5s |
| INP good threshold | < 200ms |
| CLS good threshold | < 0.1 |
| React.memo overhead | Shallow comparison of all props every render |
| useMemo cache | Stores exactly 1 value — last args + result |
| JWT access token lifetime | 15 min (short) — refresh token: 7–30 days |
| Virtualize lists at | > 100 items (DOM is the bottleneck) |
| Code split threshold | > 30KB — worth a separate chunk |
| Bundle size target | < 200KB initial JS (gzipped) |
| Context re-render scope | All consumers re-render on ANY value change |

---

## Architect-Level Topics (Missing Coverage — Added)

| # | File | Topic | Stars | Study Time |
|---|------|--------|-------|------------|
| 11 | [11_accessibility_a11y_interview.md](11_accessibility_a11y_interview.md) | Accessibility (WCAG, ARIA, Focus, Screen Readers) | ⭐⭐⭐⭐⭐ | 45 min |
| 12 | [12_realtime_patterns_interview.md](12_realtime_patterns_interview.md) | Real-Time (WebSocket, SSE, CRDTs, Presence) | ⭐⭐⭐⭐ | 45 min |
| 13 | [13_graphql_react_interview.md](13_graphql_react_interview.md) | GraphQL with React (Apollo, Codegen, Subscriptions) | ⭐⭐⭐⭐ | 45 min |
| 14 | [14_internationalization_i18n_interview.md](14_internationalization_i18n_interview.md) | Internationalization (i18next, RTL, Pluralization) | ⭐⭐⭐⭐ | 40 min |
| 15 | [15_monorepo_enterprise_tooling_interview.md](15_monorepo_enterprise_tooling_interview.md) | Monorepo & Enterprise Tooling (Turborepo, Nx, pnpm) | ⭐⭐⭐⭐ | 40 min |
| 16 | [16_design_system_architecture_interview.md](16_design_system_architecture_interview.md) | Design System Architecture (Tokens, Storybook, Versioning) | ⭐⭐⭐⭐ | 45 min |
| 17 | [17_react19_compiler_interview.md](17_react19_compiler_interview.md) | React 19 & Compiler (use(), Actions, Compiler) | ⭐⭐⭐⭐⭐ | 45 min |
| 18 | [18_frontend_observability_interview.md](18_frontend_observability_interview.md) | Frontend Observability (Sentry, RUM, Feature Flags) | ⭐⭐⭐⭐ | 40 min |
| 19 | [19_css_architecture_scale_interview.md](19_css_architecture_scale_interview.md) | CSS Architecture at Scale (Tailwind, Vanilla Extract, Tokens) | ⭐⭐⭐⭐ | 40 min |

---

## Legacy Files (Compilation Basics)

| File | Topic |
|------|-------|
| [Q1_typescript_jsx_compilation.md](Q1_typescript_jsx_compilation.md) | TypeScript + JSX compilation process |
| [Q2_tsx_compilation_pipeline.md](Q2_tsx_compilation_pipeline.md) | TSX compilation pipeline |
