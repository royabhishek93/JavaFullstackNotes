# Design System Architecture — 15-YOE React Architect Interview Prep

> Target role: Staff / Principal Frontend Engineer, Design Systems Architect
> Experience level: 15+ years, expected to drive org-wide decisions

---

## 1. Big Picture — Design System Layers (ASCII Diagram)

```
╔══════════════════════════════════════════════════════════════════════════╗
║                    DESIGN SYSTEM ARCHITECTURE LAYERS                     ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║   ┌─────────────────────────────────────────────────────────────────┐   ║
║   │  LAYER 5 — TEMPLATES / PAGE SHELLS                              │   ║
║   │  DashboardShell, AuthLayout, SettingsLayout                     │   ║
║   │  Slot-based composition, routing-aware, skeleton loaders        │   ║
║   └──────────────────────────┬──────────────────────────────────────┘   ║
║                              │ composes                                  ║
║   ┌──────────────────────────▼──────────────────────────────────────┐   ║
║   │  LAYER 4 — PATTERNS (Feature-Agnostic Assemblies)               │   ║
║   │  DataTable, SearchAndFilter, FormWithValidation, CardGrid        │   ║
║   │  Combine multiple components into repeatable UX flows           │   ║
║   └──────────────────────────┬──────────────────────────────────────┘   ║
║                              │ assembles                                 ║
║   ┌──────────────────────────▼──────────────────────────────────────┐   ║
║   │  LAYER 3 — COMPONENTS (Accessible, Polymorphic)                 │   ║
║   │  Button, Input, Modal, Select, Tooltip, Badge, Avatar           │   ║
║   │  Compound components, compound variants, forward refs           │   ║
║   └──────────────────────────┬──────────────────────────────────────┘   ║
║                              │ styled with                               ║
║   ┌──────────────────────────▼──────────────────────────────────────┐   ║
║   │  LAYER 2 — PRIMITIVES (Unstyled Building Blocks)                │   ║
║   │  Box, Stack, Grid, Text, Icon, VisuallyHidden, Portal           │   ║
║   │  Layout contracts, spacing scale, typography scale              │   ║
║   └──────────────────────────┬──────────────────────────────────────┘   ║
║                              │ consumes                                  ║
║   ┌──────────────────────────▼──────────────────────────────────────┐   ║
║   │  LAYER 1 — DESIGN TOKENS (Single Source of Truth)               │   ║
║   │  Reference Tokens:  blue.500, gray.200, spacing.4, radius.md    │   ║
║   │  Semantic Tokens:   color.action.primary, color.text.muted      │   ║
║   │  Component Tokens:  button.primary.bg, input.border.focus       │   ║
║   │  Output targets:    CSS vars, JS/TS constants, Android, iOS     │   ║
║   └─────────────────────────────────────────────────────────────────┘   ║
║                                                                          ║
║   TOOLCHAIN ACROSS ALL LAYERS:                                           ║
║   Style Dictionary → CSS custom props → Component library (tsup/Rollup) ║
║   Storybook → Chromatic → npm publish (Changesets) → Consuming apps     ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝

TOKEN HIERARCHY DETAIL:
─────────────────────────────────────────────────────────────────────────
  Reference Token          Semantic Token                Component Token
  ─────────────────        ─────────────────────         ──────────────────
  blue.500 = #3B82F6  →   color.action.primary     →   button.primary.bg
  blue.600 = #2563EB  →   color.action.primaryHover →  button.primary.bgHover
  gray.700 = #374151  →   color.text.default        →   input.text.color
  gray.200 = #E5E7EB  →   color.border.default      →   input.border.color
  spacing.4 = 16px    →   space.component.sm        →   button.padding.sm
─────────────────────────────────────────────────────────────────────────

MULTI-PLATFORM TOKEN OUTPUT (Style Dictionary):
  tokens/
  ├── src/
  │   ├── reference/      # primitive values
  │   └── semantic/       # mapped meanings
  ├── build/
  │   ├── web/
  │   │   ├── tokens.css           # :root { --color-action-primary: ... }
  │   │   └── tokens.js            # export const colorActionPrimary = ...
  │   ├── ios/
  │   │   └── StyleDictionaryColor.swift
  │   └── android/
  │       └── colors.xml
  └── style-dictionary.config.js
```

---

## 2. Conversational Interview Script — Pitching a Design System to Stakeholders

### Opening Framing (use this when asked "Why invest in a design system?")

> "I've led or contributed to design systems at three different scales — a startup, a mid-size product company, and an enterprise. The common thread is that design systems pay off faster than people expect, but only when you treat them as a *product*, not a project. Let me explain what I mean.
>
> A project has a ship date. A design system has users — every developer and designer on every product team. It needs versioning, documentation, support channels, and a deprecation policy. When you frame it as a product, you get buy-in from engineering leadership because there's a clear ROI story: every hour a product team spends re-implementing a button is an hour they didn't spend on user value."

### Stakeholder Pitch Structure (executive audience, 5 minutes)

**Open with the business problem:**
> "Right now, three product teams have each built their own date picker. They look slightly different, they have different accessibility bugs, and when legal asked us to update the cookie consent copy, it took six weeks to propagate. A shared design system makes that a one-line change, deployed in hours."

**Show the math:**
> "If a mid-level engineer spends 2 hours per sprint on component rework that a shared library would eliminate, and we have 20 product engineers, that's 40 engineer-hours per sprint — roughly one full-time engineer of capacity — returned to feature work."

**Manage the fear:**
> "Teams worry about losing autonomy. The answer is: the design system owns *how* things look and behave. Product teams own *what* gets built. Customization happens through well-defined extension points — theming, composition, slot props — not forking."

**Propose the incremental model:**
> "We don't build all 200 components before we ship. We identify the 10 most-duplicated components across teams, build those first, and prove value fast. From day one, Storybook is the living documentation so teams can see exactly what they're getting."

### When asked "How do you handle adoption?"

> "Adoption is a social problem disguised as a technical one. The technical piece — npm install, TypeScript types, autocomplete — is table stakes. The real work is embedding with product teams. I personally spend time in their sprint ceremonies to understand their pain points. When a team hits a gap in the design system, we have a fast path: RFC in the design system repo, design review within a sprint, component delivered in two sprints. That feedback loop is what drives adoption faster than any documentation."

### When asked "How do you handle breaking changes?"

> "Our contract with consumers is semantic versioning — strict. A patch is a bug fix. A minor adds capability without breaking anything. A major breaks the API. For major versions, I write a codemod using `jscodeshift` or the `@ast-types` API so teams can migrate with a single command. We never drop support for a major version until all internal consumers have migrated, and we give external consumers a six-month deprecation window. The key insight is: a breaking change is not a failure. Refusing to make breaking changes when the API is wrong — that's the failure."

---

## 3. Scenario Q&As — Production Context (8 Questions)

---

### Q1: How do you structure design tokens for a multi-brand product?

**Context**: Same React component library powering three brands with different visual identities.

**Answer**:

> "The rule is: reference tokens are shared, semantic tokens are brand-specific, component tokens derive from semantic tokens. Every brand gets its own semantic token file. Brand A maps `color.action.primary` to its orange. Brand B maps it to its teal. The component library only ever references semantic tokens — it never hardcodes `orange.500`. At runtime, we load the brand's CSS custom property file, and every component updates automatically.
>
> For implementation: each brand has a `@brand-a/tokens` package that exports a `<ThemeProvider>` injecting a CSS custom property block. Switching brands at runtime means swapping that provider — zero component changes."

**Follow-up**: "What about font families and icon sets?"

> "Those are also tokens — `font.family.brand` and `asset.icon.set`. For icons, we expose them as SVG sprite tokens so brands can swap icon libraries without changing component source."

---

### Q2: A product team wants to use a completely different color palette in their section. How do you allow that without breaking the system?

**Answer**:

> "CSS custom properties cascade. The design system establishes defaults at `:root`. A product team can override at any ancestor element — a specific `<section>` or a route-level wrapper. They wrap their section in `<div data-theme="product-custom">` and we define that selector in the token system. The components inside automatically pick up the overrides because they read from `var(--color-action-primary)` — they don't need to know which value is active.
>
> We call this 'scoped theming' and it's the correct answer to 'we need a special section'. It's not a fork — it's composition."

---

### Q3: Your Button component is rendered 10,000 times in a virtual list. A developer reports jank. What do you investigate?

**Answer**:

> "First, I profile in the React DevTools Profiler. The most common causes in a component library Button are: (1) new object references for `style` or `sx` props on every render — fix with `useMemo` or moving the object outside the component; (2) context re-renders — if Button consumes a ThemeContext that re-renders on unrelated state changes, memoize the context value; (3) CSS-in-JS runtime cost — if we're using a runtime CSS-in-JS library, that's serial style computation on every render. The fix is to move to zero-runtime CSS (vanilla-extract, Panda CSS) or ensure styles are static and cached.
>
> For the virtual list specifically, I'd also check that the row component wrapping Button is wrapped in `React.memo` so unchanged rows don't re-render at all."

---

### Q4: How do you design a `Select` component that works as both controlled and uncontrolled?

**Answer**:

> "This is the 'uncontrolled fallback' pattern. You maintain internal state with `useState` initialized to `defaultValue`. If the consumer passes `value`, you treat it as controlled — the internal state is irrelevant. The trick is the `useControllableState` hook: it checks whether `value` is defined (`!== undefined`). If defined, external wins. If undefined, internal state wins. You never mix them — that's the bug. The hook surfaces a single `[state, setState]` pair to the component internals, and the component doesn't know which mode it's in."

Code example is in Section 6.

---

### Q5: Describe your Storybook setup for a mature design system.

**Answer**:

> "Our Storybook structure has three levels of story: Docs (MDX-driven, prose plus live examples), Component stories (one per variant, args-driven), and Interaction tests (play functions that simulate user events and assert on behavior). We use these addons: Controls (for live prop manipulation), a11y (axe-core runs on every story, fails the story if there's a violation), and Chromatic for visual regression. Every PR triggers a Chromatic build — baseline is the merged main branch. Reviewers approve or reject visual diffs before merge. We also have a custom addon that shows the design token values applied to the component — designers can verify tokens without reading source."

---

### Q6: How do you publish a design system package and manage versioning?

**Answer**:

> "We use a monorepo with Changesets. Developers write a changeset file alongside their PR — it specifies which packages changed and the semver bump type plus a human-readable summary. On merge to main, the Changesets bot opens a 'Version Packages' PR that aggregates all pending changesets, bumps versions, and writes the CHANGELOG. When that PR merges, a CI step publishes to npm. This gives us: automated changelogs, consistent semver bumps, and no human remembering to update package.json. For internal packages, we publish to a private npm registry. For open-source, we publish to npm.org. Peer dependencies are listed in peerDependencies — not bundled — so consumers don't get duplicate React."

---

### Q7: A team has forked a component from the design system because it didn't meet their needs. How do you handle this?

**Answer**:

> "First, I don't treat the fork as a failure — it means we missed a use case. I schedule a design system office hour with that team to understand the gap. Usually it falls into one of three categories: (1) the component lacks an extension point they needed — fix is adding a slot prop or an `as` prop; (2) the component has a bug we haven't prioritized — fix is fast-tracking the bug; (3) the use case is genuinely out of scope — the fork is legitimate and we document it as an exception. In case three, the team owns the fork and its accessibility — they can't come to us for support on it. The most important thing is to have the conversation quickly, because a fork that lives for six months becomes the de facto 'real' component in that team's minds."

---

### Q8: How do you enforce design token usage across consuming apps?

**Answer**:

> "We ship an ESLint plugin with the design system package — `eslint-plugin-design-tokens`. It has two rules: (1) `no-hardcoded-colors` — flags hex values or rgb() in JSX style props or CSS modules; (2) `prefer-token-import` — flags using raw CSS variable strings like `'var(--color-action-primary)'` and suggests the typed token constant instead. The typed constants give autocomplete in IDEs and fail at build time if a token is renamed. We also have a Stylelint plugin for projects using CSS modules or plain CSS. These run in CI and as pre-commit hooks. Enforcement is the 'pit of success' — it's easier to use tokens than to fight the linter."

---

## 4. Advanced Scenario Q&As (4 Questions)

---

### A1: Explain how you'd implement a polymorphic component with full TypeScript inference.

**The Problem**: A `Text` component that renders as `<p>`, `<span>`, `<h1>`, etc., with the `as` prop, while TypeScript infers the correct HTML attributes for each element.

**Answer**:

> "The key is a generic type parameter constrained to `React.ElementType`. The component's props type is a union of your custom props and the native element's props via `React.ComponentPropsWithoutRef<T>`. You extract the `ref` type separately to support `forwardRef`. The `as` prop defaults to `'p'`.
>
> The dangerous pitfall is ref forwarding with generics — `forwardRef` doesn't play well with generic parameters in older TypeScript. The workaround is a type cast on the forwarded ref, or using a separate type assertion on the exported component.
>
> At 15 years, I've seen teams over-engineer this. My rule: polymorphic `as` for primitive layout components (Box, Text, Stack) only. For interactive components like Button, the polymorphic API is tempting but creates accessibility traps — a button rendered as an anchor needs explicit role management. I prefer a dedicated `ButtonLink` component instead."

Code in Section 6.

---

### A2: Walk me through a design token migration when you need to rename tokens.

**Context**: `color.brand.primary` is being renamed to `color.action.primary` for semantic clarity. 200 components and 15 apps consume the old token.

**Answer**:

> "Step one: Dual-publish. Before the minor release, add the new semantic token pointing to the same reference value. Both tokens exist and work. This is a minor version bump. Step two: Deprecate the old token — add a CSS comment, a TypeScript `@deprecated` JSDoc, and log a warning in the ESLint rule when the old name is used. Step three: Write a codemod using `jscodeshift` that replaces all occurrences of the string `'color.brand.primary'` and the CSS variable `--color-brand-primary` across TypeScript, CSS, and SCSS files. Teams run `npx ds-codemod rename-token`. Step four: After all consumers have migrated (tracked via adoption metrics in our internal dashboard), remove the old token in the next major version.
>
> The tracking piece is often skipped and causes problems. We use a simple scanner in CI that reports which token names appear in each repo — this feeds a dashboard so we know exactly who has migrated."

---

### A3: How do you test design system components differently from application components?

**Answer**:

> "Design system components need four layers of testing that application components often skip:
>
> 1. **Accessibility tests** — axe-core via `jest-axe` in unit tests AND the Storybook a11y addon running against every story. We fail CI if any story has an a11y violation.
>
> 2. **Visual regression** — Chromatic snapshots every story on every PR. Application code doesn't typically warrant this investment, but design system changes affect every consumer, so a pixel drift in a button is a real bug.
>
> 3. **Interaction tests** — Storybook play functions simulate user interactions (type into an input, open a dropdown, navigate with keyboard) and assert on DOM state. These replace e2e tests for component-level interaction coverage.
>
> 4. **Type tests** — we use `tsd` or `expect-type` to assert TypeScript types don't regress. A polymorphic `as` prop that stops inferring correctly is a breaking change that unit tests won't catch.
>
> The ratio I use: 70% interaction tests (play functions), 20% visual regression (Chromatic), 10% unit tests for pure logic. Unit test coverage numbers mean very little for UI — I care about story coverage (every variant has a story) and a11y pass rate."

---

### A4: Describe the RFC (Request for Comments) process for adding a new component.

**Answer**:

> "An RFC is required for any new component or any breaking API change. It's a markdown file in the `rfcs/` directory of the design system repo, opened as a PR. The template has these sections: Problem Statement, Prior Art (what do other design systems do?), Proposed API (TypeScript types of props), Accessibility Considerations, Open Questions.
>
> The review process: the RFC sits open for one sprint (two weeks). Any engineer or designer can comment. The design system team reviews it in a weekly design review meeting. We look for: does this solve a real, recurring problem across at least two teams? Is the API consistent with existing components? Are there accessibility edge cases we haven't addressed?
>
> Rejected RFCs don't mean the problem doesn't get solved — they mean the solution isn't right yet. A rejected RFC gets a 'more info needed' label and specific questions to answer before resubmission.
>
> The most important cultural rule: no component ships without an RFC. This prevents 'I'll add it quickly and we'll figure out the API later' — the API is the hardest part to change after the fact."

---

## 5. Senior Trap Questions (6 Questions)

---

### TRAP 1: "Let's just copy components from Shadcn/MUI into our design system"

**The Trap**: Sounds like a productivity win — you get battle-tested components for free.

**The Correct Answer**:

> "I've heard this proposal and I always push back hard. When you copy source code — whether from Shadcn, which is literally designed for copying, or from MUI — you own every line of that code from that moment forward. You own the accessibility bugs. You own the security patches. You own the React 19 migration. Shadcn's model only works if you're an application team copying components into your application and accepting that maintenance burden — it's explicit in their design.
>
> For a design system that serves 20 teams, you are a library author. You need to understand every component from first principles. Start with Radix UI or Ariakit for the accessibility primitives — those are maintained packages you're importing, not forking. Layer your design tokens on top. The delta between 'use Radix as a dependency' and 'copy Shadcn source' seems small but the long-term maintenance difference is enormous.
>
> There is one legitimate use of Shadcn: as a reference implementation to understand how to compose Radix primitives correctly. Read it, learn from it, write your own."

---

### TRAP 2: "The design system is a UI kit, not a real product"

**The Trap**: If stakeholders believe this, the design system gets no dedicated headcount, no roadmap, no support SLA, and eventually gets abandoned.

**The Correct Answer**:

> "This framing is the single most common reason design systems fail. A UI kit is a Figma file. A design system is a product with users — every developer and designer who consumes it — and it needs everything a product needs: a roadmap, versioning, documentation, a support channel, and someone whose job it is to maintain it.
>
> When a product team reports a bug in our Button component, they expect a response time. When they need a new component, they need a process to request it. When we release a breaking change, they need migration guidance. None of that happens if the design system is treated as a side project.
>
> The measurement is adoption rate and satisfaction (we run a quarterly survey with product teams). If adoption is dropping, it's a product problem — something in our API, docs, or support model is wrong. Treating it as a product means we have the discipline to measure and improve."

---

### TRAP 3: "We can use CSS variables for everything, including in media queries and calc()"

**The Trap**: CSS custom properties are very powerful but have real limitations that trip up even senior engineers.

**The Correct Answer**:

> "CSS custom properties — `var()` — cannot be used as values inside media query conditions. `@media (min-width: var(--breakpoint-md))` doesn't work. Media query conditions are resolved before the cascade, so custom properties — which are cascade-resolved — are not available at that point. This is a spec-level limitation, not a browser bug.
>
> Second limitation: in older browsers (pre-Chrome 49, and some edge cases), `calc()` with `var()` can have precision issues. In modern browsers this is mostly resolved, but if you're supporting a corporate intranet with locked-down Chrome 45, this bites you.
>
> The practical answer: breakpoints live as JavaScript constants (or PostCSS variables), not CSS custom properties. Everything else — colors, spacing, typography, radius — works great as CSS custom properties. For calc() with spacing tokens, test your actual browser matrix before committing."

---

### TRAP 4: "Design tokens are just renamed CSS variables"

**The Trap**: Underestimates the semantic naming problem and the multi-platform nature of tokens.

**The Correct Answer**:

> "The variables are the easy part. The naming is the hard part, and getting it wrong creates technical debt that's extremely expensive to unwind.
>
> Here's the distinction: `--blue-500` is a variable. `--color-action-primary` is a design token. The token carries *intent* — it says 'this color is used for primary actions.' When you rebrand from blue to teal, you change the value that `--color-action-primary` points to. Every component using `--color-action-primary` updates automatically. If you'd hardcoded `--blue-500` everywhere, you've got a global find-and-replace and a 50% chance of missing something.
>
> Second: design tokens are multi-platform. The same token system generates CSS custom properties for web, a Swift color extension for iOS, and a colors.xml for Android. That's only possible because the token file is a platform-agnostic data format (JSON), not CSS.
>
> Third: the two-tier naming (reference tokens and semantic tokens) is load-bearing architecture. Reference tokens (`blue.500`) are never used directly in components. Only semantic tokens are. This gives you the ability to do theme switching — the dark theme just remaps semantic tokens to different reference values — without touching component code."

---

### TRAP 5: "We'll build all the components before we launch the design system"

**The Trap**: This leads to months of upfront investment with no user feedback, then a launch that misses half the real use cases.

**The Correct Answer**:

> "I've made this mistake. We spent six months building a comprehensive component library and launched to crickets, because teams had already solved their problems their own way and weren't motivated to migrate.
>
> The right approach is incremental delivery with real consumers. Find one product team willing to be the 'lighthouse' team. Build the components they need first — usually Button, Input, Typography, Card, Modal. Ship those. Get them using it in production. The bugs they find in real usage are worth more than any internal review cycle.
>
> The governance principle that makes this work: 'eat your own dog food.' The design system team builds a reference app using only design system components. If a component is painful to use, we feel it immediately and fix it before shipping to others.
>
> Components that aren't driven by real usage are almost always wrong. The API feels right until a developer tries to use it in a real form, discovers the controlled/uncontrolled behavior is broken, and the component needs a redesign anyway. Ship early, ship often, iterate."

---

### TRAP 6: "Let's just put all design system components in a shared folder in our monorepo"

**The Trap**: Internal shared folder vs. properly packaged library — the difference seems like overhead until it isn't.

**The Correct Answer**:

> "A shared folder in the monorepo means no versioning, no changelog, no ability for external teams to consume it, and no forced API discipline. When team A changes the Button to fit their use case, team B's usage breaks silently — there's no version boundary that makes the change visible.
>
> A separate package — even inside the monorepo — enforces a contract. Teams import `@company/ui` at a version. Changesets write a changelog. Semver tells consuming teams whether they need to take action. TypeScript types are compiled and shipped separately from source.
>
> The packaging overhead (Changesets, tsup build) is maybe two days of setup. The benefit is permanent. I've seen companies skip this and spend months untangling implicit dependencies. Package it correctly from day one."

---

## 6. Production TypeScript/React Code Examples

---

### Example 1: Design Token Types with Autocomplete

```typescript
// tokens.ts — generated from Style Dictionary
export const tokens = {
  color: {
    action: {
      primary: 'var(--color-action-primary)',
      primaryHover: 'var(--color-action-primary-hover)',
    },
    text: {
      default: 'var(--color-text-default)',
      muted: 'var(--color-text-muted)',
    },
    border: {
      default: 'var(--color-border-default)',
    },
  },
  spacing: {
    1: 'var(--spacing-1)',
    2: 'var(--spacing-2)',
    4: 'var(--spacing-4)',
  },
} as const;

export type ColorToken = typeof tokens['color']['action']['primary'];
// Usage: tokens.color.action.primary → full autocomplete
```

---

### Example 2: Polymorphic Component with TypeScript

```typescript
// Polymorphic.tsx
type AsProp<T extends React.ElementType> = { as?: T };

type PolymorphicProps<T extends React.ElementType, P = {}> =
  AsProp<T> & Omit<React.ComponentPropsWithoutRef<T>, keyof P | 'as'> & P;

type TextProps<T extends React.ElementType = 'p'> = PolymorphicProps<
  T,
  { size?: 'sm' | 'md' | 'lg'; muted?: boolean }
>;

function Text<T extends React.ElementType = 'p'>({
  as,
  size = 'md',
  muted = false,
  className,
  ...props
}: TextProps<T>) {
  const Tag = as ?? 'p';
  return (
    <Tag
      className={[styles.text, styles[size], muted && styles.muted, className]
        .filter(Boolean)
        .join(' ')}
      {...props}
    />
  );
}
// <Text as="h1" size="lg"> → infers h1 HTML attributes
// <Text as="span" muted> → infers span HTML attributes
```

---

### Example 3: useControllableState Hook

```typescript
// useControllableState.ts
function useControllableState<T>(
  controlledValue: T | undefined,
  defaultValue: T,
  onChange?: (value: T) => void,
): [T, (value: T) => void] {
  const [internalValue, setInternalValue] = React.useState<T>(defaultValue);
  const isControlled = controlledValue !== undefined;
  const value = isControlled ? controlledValue : internalValue;

  const setValue = React.useCallback(
    (next: T) => {
      if (!isControlled) setInternalValue(next);
      onChange?.(next);
    },
    [isControlled, onChange],
  );

  return [value, setValue];
}
// Supports both <Select value={x} onChange={y}> (controlled)
// and <Select defaultValue="a"> (uncontrolled)
```

---

### Example 4: Compound Component Pattern — Tabs

```typescript
// Tabs.tsx — compound component
const TabsContext = React.createContext<{
  active: string;
  setActive: (id: string) => void;
} | null>(null);

function Tabs({ defaultTab, children }: { defaultTab: string; children: React.ReactNode }) {
  const [active, setActive] = React.useState(defaultTab);
  return (
    <TabsContext.Provider value={{ active, setActive }}>
      <div role="tablist">{children}</div>
    </TabsContext.Provider>
  );
}

function Tab({ id, children }: { id: string; children: React.ReactNode }) {
  const ctx = React.useContext(TabsContext)!;
  return (
    <button role="tab" aria-selected={ctx.active === id} onClick={() => ctx.setActive(id)}>
      {children}
    </button>
  );
}

Tabs.Tab = Tab;
// <Tabs defaultTab="profile"><Tabs.Tab id="profile">Profile</Tabs.Tab></Tabs>
```

---

### Example 5: CSS Custom Property Theme Provider

```typescript
// ThemeProvider.tsx
const themes = {
  light: {
    '--color-action-primary': '#3B82F6',
    '--color-text-default': '#111827',
    '--color-bg-surface': '#FFFFFF',
  },
  dark: {
    '--color-action-primary': '#60A5FA',
    '--color-text-default': '#F9FAFB',
    '--color-bg-surface': '#1F2937',
  },
} as const;

type Theme = keyof typeof themes;

function ThemeProvider({ theme, children }: { theme: Theme; children: React.ReactNode }) {
  const cssVars = themes[theme];
  return (
    <div style={cssVars as React.CSSProperties} data-theme={theme}>
      {children}
    </div>
  );
}
// Injects CSS custom properties at the wrapper level
// All child components inherit via var() lookups
```

---

### Example 6: Forward Ref with TypeScript

```typescript
// Button.tsx
interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = 'primary', size = 'md', isLoading, children, disabled, ...props }, ref) => (
    <button
      ref={ref}
      disabled={disabled || isLoading}
      aria-busy={isLoading}
      data-variant={variant}
      data-size={size}
      {...props}
    >
      {isLoading ? <Spinner size={size} aria-hidden /> : children}
    </button>
  ),
);
Button.displayName = 'Button';
```

---

### Example 7: Storybook Play Function (Interaction Test)

```typescript
// Button.stories.tsx
import { userEvent, within, expect } from '@storybook/test';

export const ClickHandled: Story = {
  args: { children: 'Submit', variant: 'primary' },
  play: async ({ canvasElement, args }) => {
    const canvas = within(canvasElement);
    const button = canvas.getByRole('button', { name: /submit/i });
    await userEvent.click(button);
    // If onClick spy passed via args:
    await expect(args.onClick).toHaveBeenCalledTimes(1);
  },
};

export const DisabledWhenLoading: Story = {
  args: { children: 'Submit', isLoading: true },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const button = canvas.getByRole('button');
    await expect(button).toBeDisabled();
    await expect(button).toHaveAttribute('aria-busy', 'true');
  },
};
```

---

### Example 8: tsup Build Config (tree-shakeable ESM + CJS)

```typescript
// tsup.config.ts
import { defineConfig } from 'tsup';

export default defineConfig({
  entry: ['src/index.ts'],
  format: ['esm', 'cjs'],
  dts: true,
  splitting: true,      // per-component chunks → tree shaking works
  sourcemap: true,
  clean: true,
  external: ['react', 'react-dom'],  // peer deps — never bundle these
  esbuildOptions(options) {
    options.jsx = 'automatic';      // React 17+ transform
  },
});
// Output: dist/index.js (CJS), dist/index.mjs (ESM), dist/index.d.ts
// Consumers get full tree shaking — import Button → only Button code
```

---

### Example 9: ESLint Plugin Rule — No Hardcoded Colors

```typescript
// eslint-plugin-design-tokens/no-hardcoded-colors.ts
const HEX_PATTERN = /#[0-9a-fA-F]{3,8}/;

module.exports = {
  create(context) {
    return {
      Literal(node) {
        if (typeof node.value === 'string' && HEX_PATTERN.test(node.value)) {
          context.report({
            node,
            message: `Hardcoded color "${node.value}" detected. Use a design token instead.`,
            suggest: [
              {
                desc: 'Replace with token import from @company/tokens',
                fix: (fixer) => fixer.replaceText(node, 'tokens.color.action.primary'),
              },
            ],
          });
        }
      },
    };
  },
};
```

---

### Example 10: Changeset Configuration (Monorepo)

```json
// .changeset/config.json
{
  "changelog": "@changesets/changelog-github",
  "commit": false,
  "linked": [],
  "access": "restricted",
  "baseBranch": "main",
  "updateInternalDependencies": "patch",
  "ignore": ["@company/design-system-docs"]
}
```

```bash
# Workflow a developer runs:
pnpm changeset          # CLI prompt: which packages changed? what semver bump? what did you change?
# Creates: .changeset/violet-dogs-eat.md
# On PR merge → Changesets bot opens "Version Packages" PR
# That PR merges → CI publishes to npm registry
```

---

### Example 11: Style Dictionary Multi-Platform Config

```javascript
// style-dictionary.config.js
module.exports = {
  source: ['tokens/src/**/*.json'],
  platforms: {
    css: {
      transformGroup: 'css',
      prefix: 'ds',
      buildPath: 'tokens/build/web/',
      files: [{ destination: 'tokens.css', format: 'css/variables' }],
    },
    js: {
      transformGroup: 'js',
      buildPath: 'tokens/build/web/',
      files: [{ destination: 'tokens.js', format: 'javascript/es6' }],
    },
    ios: {
      transformGroup: 'ios-swift',
      buildPath: 'tokens/build/ios/',
      files: [{ destination: 'StyleDictionaryColor.swift', format: 'ios-swift/class.swift' }],
    },
  },
};
```

---

## 7. Interview Cheat Sheet

### The 3 Rules I Lead With

```
1. A design system is a PRODUCT, not a project.
2. Build tokens → primitives → components — in that order.
3. Adoption is a social problem. Solve it with embedding, not docs.
```

---

### Design Token Quick Reference

| Term | Definition | Example |
|------|-----------|---------|
| Reference token | Raw value with no semantic meaning | `blue.500 = #3B82F6` |
| Semantic token | Maps intent to a reference token | `color.action.primary → blue.500` |
| Component token | Component-specific alias | `button.primary.bg → color.action.primary` |
| CSS custom property | Browser runtime variable | `--color-action-primary: #3B82F6` |

**Key Constraint**: CSS custom properties CANNOT be used inside `@media` query conditions. Use JS constants for breakpoints.

---

### Component API Design Checklist

```
[ ] Controlled AND uncontrolled support via useControllableState
[ ] forwardRef for all interactive elements
[ ] aria-* props not swallowed — spread {...props} after explicit props
[ ] as prop for primitives only (Box, Text, Stack)
[ ] Compound component pattern for complex multi-part UIs (Tabs, Accordion)
[ ] data-* attributes for styling hooks (not className overrides)
[ ] size and variant props use union string literals, not enum
[ ] children typed as React.ReactNode, not JSX.Element
```

---

### Theming Quick Reference

```
Dark mode approaches:
  1. prefers-color-scheme media query → automatic, no JS needed
  2. data-theme="dark" on <html> → manual toggle, JS required
  3. Both: default to prefers-color-scheme, allow manual override via localStorage

Implementation:
  :root { --color-bg: #fff; }
  @media (prefers-color-scheme: dark) { :root { --color-bg: #1F2937; } }
  [data-theme="dark"] { --color-bg: #1F2937; }   /* overrides media query */
  [data-theme="light"] { --color-bg: #fff; }
```

---

### Library Distribution Checklist

```
[ ] tsup or Rollup with ESM + CJS output
[ ] splitting: true for per-component tree shaking
[ ] react and react-dom in peerDependencies (NOT dependencies)
[ ] dts: true for TypeScript declarations
[ ] sourcemap: true for debuggability in consumer apps
[ ] exports field in package.json for modern bundler resolution
[ ] sideEffects: false in package.json (enables tree shaking in webpack)
```

---

### Versioning & Breaking Change Policy

```
Patch  0.0.x  — Bug fix, no API change, no migration needed
Minor  0.x.0  — New component or prop added, backward compatible
Major  x.0.0  — Breaking API change, requires consumer code change

Breaking change process:
  1. Add new API in minor version
  2. Deprecate old API in minor version (JSDoc @deprecated + console.warn in dev)
  3. Remove old API in next major version (+ jscodeshift codemod)
  4. Six-month deprecation window minimum for external consumers
```

---

### Storybook Testing Matrix

```
Coverage type      Tool              Failure blocks merge?
─────────────────  ────────────────  ─────────────────────
Accessibility      a11y addon        YES — zero violations policy
Visual regression  Chromatic         YES — requires reviewer approval
Interaction        play functions    YES — assertion failures = CI failure
Type correctness   tsd / expect-type YES — part of build check
```

---

### Monorepo Structure (Reference)

```
design-system/
├── packages/
│   ├── tokens/          # @company/tokens — Style Dictionary output
│   ├── icons/           # @company/icons — SVG icon components
│   ├── components/      # @company/ui — React component library
│   └── eslint-plugin/   # eslint-plugin-design-tokens
├── apps/
│   └── storybook/       # Storybook + Chromatic target
├── .changeset/          # Changesets config + pending changesets
├── turbo.json           # Turborepo build pipeline
└── pnpm-workspace.yaml
```

---

### Multi-Brand Token Strategy

```
Shared (across brands):
  reference tokens   →  blue.500, gray.200, spacing.4

Brand-specific (per brand):
  semantic tokens    →  color.action.primary
  component tokens   →  button.primary.bg

Runtime switching:
  <ThemeProvider brand="brand-a"> injects brand-a CSS custom properties
  <ThemeProvider brand="brand-b"> injects brand-b CSS custom properties
  Components read var(--color-action-primary) — brand-agnostic
```

---

### RFC Process Summary

```
1. File rfcs/NNN-component-name.md (PR against design-system repo)
2. Required sections: Problem, Prior Art, Proposed API, a11y Notes, Open Questions
3. Open for 1 sprint (2 weeks) — any engineer/designer can comment
4. Design review meeting — accept / request changes / reject
5. Accepted RFC → issues created in backlog with 2-sprint delivery target
6. No component ships without an approved RFC
```

---

### 5 Things That Kill Design Systems

```
1. No dedicated ownership — treated as shared "everyone's job" side project
2. Over-engineering upfront — building 200 components before proving value
3. No breaking change policy — API debt accumulates, teams stop trusting updates
4. Documentation as afterthought — Storybook added "later" = never
5. Treating adoption as automatic — if you build it, they won't necessarily come
```

---

### Quick Answers to Common Interview Questions

| Question | One-Sentence Answer |
|----------|-------------------|
| Shadcn vs. Radix vs. MUI? | Radix for unstyled a11y primitives as deps; Shadcn as copy-paste reference only; MUI is a full system with its own opinions — hard to style to your brand |
| CSS-in-JS vs. CSS Modules vs. Tailwind? | CSS Modules or vanilla-extract for zero-runtime in a design system; CSS-in-JS runtime cost shows up in high-frequency components |
| How many components before launch? | 8–12 most-used (Button, Input, Select, Modal, Typography, Badge, Card, Avatar) — prove value first |
| Who owns the design system? | A cross-functional team with dedicated frontend engineers, a designer, and a product manager — same as any product team |
| How do you handle one-off components? | Product teams own bespoke components. Design system owns cross-product components. Clear ownership charter prevents scope creep in both directions |

---

### Key Phrases for 15-YOE Candidate

- "The token naming convention is the design contract. Renaming later is a migration — treat it as a breaking change."
- "I've learned to ship a working Storybook before shipping the first component. It forces API clarity."
- "A design system without a governance model is a framework. Governance is what makes it a system."
- "The best design system is one developers forget about — it feels invisible because everything just works."
- "Breaking changes are a sign of learning. Refusing to break a bad API is the real problem."

---

*End of file — 15-YOE Design System Architecture Interview Prep*
