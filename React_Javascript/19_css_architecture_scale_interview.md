# CSS Architecture at Scale — React Architect Interview Prep (15 YOE)

> Target role: Staff/Principal Frontend Engineer, Frontend Architect, Senior React Engineer
> Depth: Production-grade — not tutorial-level, not trivia-level

---

## 1. BIG PICTURE: CSS Architecture Decision Tree

```
START: New project or migration decision
           │
           ▼
    ┌──────────────────────────────────────────────────────────────────┐
    │  What are your primary constraints?                              │
    └──────────────────────────────────────────────────────────────────┘
           │
     ┌─────┴──────┐
     │            │
     ▼            ▼
  Runtime     Performance /
  flexibility  Bundle size critical?
  needed?         │
     │            ▼
     │         ┌──────────────────────────────────────────┐
     │         │  Zero-runtime CSS-in-JS or Tailwind JIT   │
     │         │  • Vanilla Extract (TS-first, typed tokens)│
     │         │  • Linaria (tagged template literals)      │
     │         │  • Tailwind CSS (utility-first JIT)        │
     │         └──────────────────────────────────────────┘
     │
     ▼
  Dynamic styles via props at runtime?
     │
  ┌──┴──┐
  YES   NO
  │     │
  ▼     ▼
styled- CSS Modules
comps/  + custom
Emotion  properties
  │
  └── Warning: SSR FOUC risk,
      runtime serialization cost,
      large JS bundle


SPECIFICITY / CASCADE MODEL:
─────────────────────────────────────────────────────────────────────
Lowest                                                       Highest
  │                                                              │
  ▼                                                              ▼
@layer base  →  @layer components  →  @layer utilities  →  inline style
(resets)       (design system)       (tailwind utils)      (avoid!)
                                                          ↑
                                              !important lives here
                                              (trap: avoids layers)


BUILD PIPELINE BY APPROACH:
─────────────────────────────────────────────────────────────────────

CSS MODULES:
  .tsx → webpack/vite → css-loader → :local() → [hash].css
  Output: deterministic class names, zero runtime

STYLED-COMPONENTS / EMOTION (Runtime CSS-in-JS):
  .tsx → babel plugin → JS bundle → StyleSheet.inject() at runtime
  Output: dynamic <style> tags, SSR needs ServerStyleSheet / cache flush

LINARIA (Zero-runtime):
  .tsx → linaria/babel → extracted .css → bundler
  Output: static CSS file + className references in JS, zero runtime

VANILLA EXTRACT:
  .ts (style definitions) → @vanilla-extract/vite-plugin → .css files
  Output: fully typed CSS, hashed class names, zero runtime overhead

TAILWIND CSS:
  .tsx → Tailwind JIT scanner → PostCSS → purged .css
  Output: only classes used are emitted; no runtime

STYLE DICTIONARY (Design Tokens Pipeline):
  tokens.json → Style Dictionary transforms → CSS custom props
              → Tailwind theme extension
              → TypeScript type definitions
              → iOS/Android/etc.
```

---

## 2. CONVERSATIONAL INTERVIEW SCRIPT — 15-YOE ARCHITECT VOICE

### "Walk me through how you choose a CSS architecture for a team."

> "The first thing I do is a **constraint map**, not a features list. I ask: What is the team's CSS literacy? What is the rendering model — SPA, SSR, streaming SSR? What are the performance budgets? Are we inheriting a legacy codebase or greenfield?
>
> For a team with mixed CSS skill levels going greenfield, I lean Tailwind plus CVA for component variants, because Tailwind's JIT compiler means you only ship what you use, and CVA gives you TypeScript-safe variant APIs without any CSS-in-JS runtime cost. The team writes fewer files, the design system is enforced via tailwind.config.ts, and ESLint + stylelint rules catch hardcoded colors.
>
> For a design system that needs runtime theming — white-labeling, runtime color scheme switching beyond dark/light — I'd consider styled-components or Emotion, but I'd be very explicit about the performance contract: you're paying with JS bundle size, runtime serialization, and SSR complexity. In 2024-onward I would almost always choose Vanilla Extract over styled-components for a new design system. Vanilla Extract gives you full TypeScript types on your design tokens, zero runtime, and the theming story via CSS custom properties is excellent.
>
> For teams already on CSS Modules, I'd often stay there unless there's a specific pain point — CSS Modules are boring in the best possible way: deterministic, zero runtime, understood by every CSS engineer."

---

### "What's the biggest mistake you see teams make with CSS-in-JS?"

> "Treating it as a complete CSS replacement without understanding the runtime model. Every styled-component call at render time serializes a CSS string, hashes it, and injects it into the document. In a component tree with hundreds of unique prop combinations, that's hundreds of style insertions. On a high-traffic SSR page, the critical path includes collecting all server-side styles and flushing them into the HTML — if you get that wrong, you get Flash of Unstyled Content on hydration.
>
> The other failure mode is using CSS-in-JS for values that CSS custom properties can handle perfectly — dark mode, spacing scale, color themes. Those don't need JavaScript at all. A CSS custom property changes cascade instantly; a prop change in styled-components triggers re-serialization.
>
> I tell teams: use CSS-in-JS for logic that genuinely requires JavaScript — conditional style blocks based on complex application state. For theming and tokens, use CSS custom properties."

---

### "How do you enforce CSS conventions at the team level?"

> "Three layers. First, ESLint rules — I use `eslint-plugin-no-restricted-syntax` to ban inline style objects where CSS variables could be used, and I ban hardcoded hex/rgb values in style props. Second, stylelint — I configure it to enforce naming conventions, disallow magic numbers in property values (use tokens), and flag `!important` outside of `@layer`. Third, design token governance — I run Style Dictionary in CI, and any token addition or change to the JSON source requires a PR review from the design team. The generated CSS custom properties file is committed, never hand-edited."

---

## 3. SCENARIO Q&As — PRODUCTION CONTEXT

### Scenario 1: SSR performance degradation with styled-components

**Interviewer:** "Your SSR React app is showing 400ms+ TTFB. Profiling shows `ServerStyleSheet.collectStyles` is taking 180ms. What do you do?"

**Answer:**
> "That's the cost of runtime CSS-in-JS at scale. The styled-components server-side collect pass traverses the entire render tree to gather emitted styles, and at large component counts it becomes the bottleneck.
>
> Short-term: I'd audit which components actually need dynamic prop-driven styles. Often 80% of styled-components are purely static — those should be migrated to CSS Modules or Vanilla Extract immediately, which removes them from the collect traversal.
>
> Medium-term: Migrate the entire design system to Vanilla Extract. The cost is upfront migration work, but you permanently eliminate the collect step from the server hot path. Vanilla Extract styles are pre-extracted at build time — they're just static CSS files served by the CDN.
>
> During migration: I'd also look at CSS containment (`contain: layout style`) on leaf components to limit style recalculation scope, and critical CSS extraction to inline above-the-fold styles and defer the rest."

---

### Scenario 2: Specificity wars in a large legacy codebase

**Interviewer:** "A team of 20 engineers has accumulated three years of global CSS, component-level CSS Modules, a UI library with its own styles, and some Tailwind classes added recently. Specificity conflicts are constant. How do you fix it?"

**Answer:**
> "This is a CSS Layers migration. `@layer` gives you an explicit specificity order that overrides the cascade's natural specificity rules.
>
> I'd define a layer order at the top of the app's main stylesheet:
> ```css
> @layer reset, base, components, library, utilities, overrides;
> ```
>
> The UI library styles go into `@layer library`. Your app component styles go into `@layer components`. Tailwind's output goes into `@layer utilities`. Now a utility class in `utilities` always beats a component style in `components` regardless of selector specificity — you've made the hierarchy explicit and testable.
>
> Legacy CSS that isn't yet layered sits in the unlayered cascade, which has higher specificity than any layer, so you migrate it gradually. I'd add a lint rule that flags any new CSS written outside of an @layer block."

---

### Scenario 3: Design system token migration

**Interviewer:** "Your design team delivers new brand tokens — 200 color tokens, 30 spacing tokens. They want them live in the web app, iOS, and Android simultaneously. How do you architect this?"

**Answer:**
> "Style Dictionary is the tool for this. The design team maintains a `tokens/` directory — JSON or YAML files organized by category. Style Dictionary transforms apply per platform:
>
> - Web: CSS custom properties (`--color-brand-primary: #...`)
> - iOS: Swift color literals or a Swift enum
> - Android: XML color resources
>
> I'd integrate Style Dictionary into the monorepo as a build step. The generated CSS custom properties file is published as part of the design system package. Web app imports it once at the root; individual components reference tokens by variable name only — never raw hex values. CI enforces this via stylelint's `declaration-property-value-disallowed-list` rule banning raw hex in component files.
>
> For theming (dark mode, brand variants), I'd use data-attribute selectors:
> ```css
> [data-theme="dark"] { --color-surface: #1a1a1a; }
> [data-theme="light"] { --color-surface: #ffffff; }
> ```
> Theme switching is a single DOM attribute change — zero JavaScript style recalculation."

---

### Scenario 4: Tailwind at scale — when it starts hurting

**Interviewer:** "Team is 6 months in on Tailwind. Engineers are complaining that complex interactive states make class strings unmanageable. What's your solution?"

**Answer:**
> "This is exactly the problem CVA (Class Variance Authority) solves. You define component variants in a typed schema:
>
> ```typescript
> import { cva } from 'class-variance-authority';
>
> const button = cva('px-4 py-2 rounded font-medium', {
>   variants: {
>     intent: {
>       primary: 'bg-blue-600 text-white hover:bg-blue-700',
>       danger:  'bg-red-600 text-white hover:bg-red-700',
>     },
>     size: { sm: 'text-sm', lg: 'text-lg px-6 py-3' },
>   },
>   defaultVariants: { intent: 'primary', size: 'sm' },
> });
> ```
>
> Now instead of 15 Tailwind classes inlined in JSX, you have a `button({ intent: 'danger', size: 'lg' })` call. The TypeScript types prevent invalid combinations. The class strings live in one place, colocated with the component.
>
> For dynamic values that Tailwind JIT can't handle (user-specified colors, runtime pixel values), I'd use CSS custom properties set inline and reference them in Tailwind's arbitrary value syntax or plain CSS. Inline style for the variable value, Tailwind class for the property that reads the variable."

---

### Scenario 5: Container queries replacing media queries

**Interviewer:** "You have a card component that needs to reflow based on available width, not viewport width. It's used in a sidebar (narrow) and a main grid (wide). How do you handle this today?"

**Answer:**
> "This is the canonical use case for Container Queries. Before container queries, you'd pass a prop to the card component indicating context — sidebar vs. grid — and apply different classes. That's logic leak: the layout context shouldn't be the component's concern.
>
> With container queries:
> ```css
> .card-wrapper { container-type: inline-size; }
>
> @container (min-width: 400px) {
>   .card { display: flex; flex-direction: row; }
> }
> ```
>
> The card responds to its container's width, not the viewport. It just works in both sidebar and grid without any prop threading. Browser support is now excellent — all major browsers since late 2023. For a new project I'd use this by default. For legacy, I'd polyfill with `container-query-polyfill` on a per-component basis during migration."

---

### Scenario 6: CSS Custom Properties vs. CSS-in-JS for theming

**Interviewer:** "Argue for using CSS custom properties instead of a styled-components theme for a SaaS product that supports tenant white-labeling."

**Answer:**
> "Custom properties win on multiple dimensions here. First, the runtime model: changing a CSS custom property is a single DOM operation — the browser re-cascades affected elements natively. No JavaScript parsing, no re-render, no style sheet injection. With styled-components, a theme change re-renders every styled component that consumes the theme.
>
> Second, SSR: custom properties are static CSS — they're in the stylesheet the server sends. No collection step, no hydration mismatch. The tenant's brand colors are set on `:root` or a `[data-tenant]` selector — the CSS handles it.
>
> Third, debuggability: in DevTools you see `--color-brand: #ff6b35` right on the element. With CSS-in-JS you see hashed class names pointing to injected style tags.
>
> Fourth, interoperability: custom properties work with any CSS tool — CSS Modules, Tailwind arbitrary values, plain CSS, SVG fill values. A styled-components theme object is JS-only.
>
> The one case where CSS-in-JS theme wins: when your dynamic style logic exceeds what custom properties can express — e.g., computing a color mix or animation keyframe value that requires JavaScript math. That's rare."

---

### Scenario 7: Critical CSS extraction in Next.js

**Interviewer:** "A Next.js app has a 3-second First Contentful Paint. The CSS is loading as a render-blocking stylesheet. Walk me through the fix."

**Answer:**
> "Render-blocking CSS means the browser won't paint until the stylesheet is downloaded and parsed. The fix is critical CSS extraction: inline only the CSS needed for above-the-fold content in the `<head>`, and defer the rest asynchronously.
>
> Next.js with the App Router handles some of this automatically — it route-splits CSS and loads only what's needed per route. But for further optimization, I'd use `critters` (integrated as `next/font` handles fonts) or configure the `experimental.optimizeCss` flag which runs critters under the hood.
>
> For manual control: identify above-the-fold components, extract their CSS into a `critical.css` file, inline it with `<style>` in the document head, and load the full stylesheet with `<link rel="preload" as="style" onload="this.rel='stylesheet'">`.
>
> CSS containment also helps rendering performance: adding `contain: layout style paint` to complex, isolated components tells the browser those elements can't affect layout outside their boundary — enabling parallel layout calculation."

---

### Scenario 8: Atomic CSS vs. semantic CSS — team decision

**Interviewer:** "Your team is split: half want Tailwind (atomic/utility-first), half want BEM CSS Modules (semantic). How do you decide?"

**Answer:**
> "I'd frame it as a trade-off analysis, not a preference vote.
>
> **Tailwind/Atomic** gives you: zero dead CSS (JIT), no naming decisions, consistent spacing/color via design tokens baked into config, faster prototyping. It costs you: JSX readability at complex states, loss of semantic meaning in class names, Tailwind knowledge required for all contributors.
>
> **BEM CSS Modules** gives you: readable, self-documenting class names, clear component boundaries, familiar to any CSS engineer. It costs you: CSS file proliferation, potential specificity issues at scale, dead CSS risk without purging.
>
> My decision criteria: team CSS literacy, codebase longevity, and whether the design system has strong token discipline. For a consumer product team iterating fast with a design system: Tailwind + CVA. For an enterprise internal tool or a codebase that will have contributors with varying frontend depth: CSS Modules with stylelint enforcement. For a reusable component library intended for external consumption: Vanilla Extract — the consumer's styling system doesn't matter, and you get zero runtime overhead."

---

## 4. ADVANCED SCENARIO Q&As

### Advanced 1: Vanilla Extract — typed design tokens

**Interviewer:** "How would you implement a fully typed design token system in Vanilla Extract for a multi-brand SaaS product?"

**Answer:**
> "Vanilla Extract's `createTheme` and `createThemeContract` are the primitives here. First define the contract — the shape of all tokens with no values:
>
> ```typescript
> // tokens.css.ts
> import { createThemeContract } from '@vanilla-extract/css';
>
> export const vars = createThemeContract({
>   color: { brand: null, surface: null, text: null },
>   space: { sm: null, md: null, lg: null },
> });
> ```
>
> Then each tenant provides a theme implementation:
> ```typescript
> // tenantA.css.ts
> import { createTheme } from '@vanilla-extract/css';
> import { vars } from './tokens.css';
>
> export const tenantATheme = createTheme(vars, {
>   color: { brand: '#ff6b35', surface: '#fff', text: '#111' },
>   space:  { sm: '4px', md: '8px', lg: '16px' },
> });
> ```
>
> At runtime, you apply the tenant's theme class to the root element. The CSS custom properties cascade through the entire tree. TypeScript prevents you from missing a token — the contract enforces completeness. The generated output is static CSS files, zero runtime serialization."

---

### Advanced 2: CSS containment strategy

**Interviewer:** "Explain the `contain` property and when you'd use it in a high-performance React application."

**Answer:**
> "CSS `contain` restricts what a browser needs to recalculate when an element changes. There are four values that matter:
>
> - `layout`: changes inside can't affect layout outside
> - `style`: counter/quotes changes inside don't escape
> - `paint`: overflow is clipped, painter can skip off-screen elements
> - `size`: element's size is independent of its children
>
> `contain: layout style paint` (also written as `contain: content`) is the right choice for isolated component islands — a data grid, a chat message list, a card that re-renders frequently. The browser can skip recalculating the page layout when only that component changes.
>
> In React: I'd apply it to components that are frequently updated via streaming data or user interaction but are visually isolated. Combined with `will-change: transform` on animated elements, you push those elements to their own GPU layer, avoiding layout thrash entirely.
>
> The anti-pattern: applying `contain: size` without explicit dimensions causes the element to collapse — it no longer takes size from children. Always verify in DevTools."

---

### Advanced 3: Migrating a large codebase from styled-components to Vanilla Extract

**Interviewer:** "You're leading a migration of 300 styled-components to Vanilla Extract across 6 teams. How do you execute this without breaking production?"

**Answer:**
> "Coexistence first — both systems can run in the same app simultaneously. Vanilla Extract styles are static CSS, styled-components are JS-injected. No conflict.
>
> Migration strategy:
>
> 1. **Token parity first** — port the styled-components `ThemeProvider` tokens to a `createThemeContract` + CSS custom properties. Both systems can now read from the same CSS custom properties, even though they access them differently.
>
> 2. **Leaf components first** — start with components that have no children dependencies: buttons, inputs, badges. These are the easiest to port and the most reused — highest impact.
>
> 3. **Codemod** — write a jscodeshift transform that converts static styled-components (no props, no theme reference) to Vanilla Extract `.css.ts` files automatically. That handles maybe 60% of cases.
>
> 4. **Gradual dynamic migration** — for components with prop-driven styles, replace `styled(Button)<{isActive: boolean}>` with `cva`-style recipe in Vanilla Extract using `styleVariants` and `recipe` from `@vanilla-extract/recipes`.
>
> 5. **CI gate** — add a lint rule that bans new `styled.*` imports. Existing ones are warnings; new ones are errors. Migration completes when zero warnings remain."

---

### Advanced 4: CSS @layer and third-party library integration

**Interviewer:** "You're using a component library (like MUI or Radix) that ships its own CSS. Your app styles conflict with library styles. Walk me through a durable solution."

**Answer:**
> "Wrap the library's styles in a `@layer`:
> ```css
> @layer library {
>   @import 'radix-ui/themes.css';
> }
>
> @layer components { /* your app styles */ }
> @layer utilities  { /* tailwind or atomic utilities */ }
> ```
>
> Now your `components` layer always wins over the `library` layer regardless of selector specificity. No more `!important` arms races to override a library's `.MuiButton-root` selector.
>
> For libraries that inject styles at runtime (like MUI's emotion-based system), you can configure MUI's `StyledEngineProvider` with `injectFirst` to push its styles earlier in the cascade, then use a layer order that puts your styles above it.
>
> For Radix UI's unstyled primitives: wrap the import in a layer and add your design system's styles in a higher layer — clean separation.
>
> The key insight: `@layer` makes the cascade explicit and intentional. The previous approach was implicit — whoever had the more specific selector won, which led to the specificity arms race. Layers replace specificity battles with a clear hierarchy."

---

## 5. SENIOR TRAP QUESTIONS

### Trap 1: "CSS-in-JS is always the right choice for React"

**The trap:** The assumption conflates "works with React" with "optimal for React." Interviewers set this up as a leading statement to see if you'll agree.

**Why it's wrong:**
> "This was a reasonable assumption in 2018 when CSS Modules had tooling gaps and Tailwind didn't exist in its current form. Today it's demonstrably false for several reasons.
>
> Runtime CSS-in-JS (styled-components, Emotion) has real costs: every unique style at render time is serialized to a CSS string, hashed, and injected into the document. Under React 18 concurrent rendering, this can cause ordering issues with style injection since concurrent renders can be interrupted. Sebastian Markbåge's critique (the styled-components team's own analysis post-React 18) acknowledged these limitations.
>
> SSR adds FOUC risk if the style collection and flush isn't implemented correctly. The JS bundle includes all style logic — a design system built on styled-components adds 40-80KB gzipped of runtime.
>
> For performance-critical applications, Tailwind JIT or Vanilla Extract are strictly better: zero runtime overhead, static CSS output, and Vanilla Extract gives you full TypeScript typing on tokens which styled-components cannot match without significant boilerplate.
>
> The right answer is: CSS-in-JS is *a* valid choice when dynamic, prop-driven styles justify the overhead. It's not the default correct choice."

---

### Trap 2: "Tailwind means you don't need to know CSS"

**The trap:** Presented as a selling point of Tailwind — marketing language that some engineers genuinely believe.

**Why it's wrong:**
> "Tailwind abstracts CSS *syntax*, not CSS *concepts*. When `flex-col` doesn't behave as expected, you need to understand that `flex-direction: column` doesn't work unless `display: flex` is also applied on the parent. `gap-4` only works if the element is a flex or grid container. `overflow-hidden` on a parent clips absolute-positioned children only if the parent has a non-static position — that's a core CSS positioning concept, not Tailwind-specific.
>
> Engineers who don't understand the box model, stacking context, containing blocks, or the difference between `width: 100%` and `width: 100vw` will produce broken layouts in Tailwind — they'll just be broken in utility classes instead of CSS files.
>
> If anything, Tailwind requires *more* CSS familiarity than CSS Modules because you're applying individual property-value pairs directly — you need to know which properties to combine, not just which class names the framework provides.
>
> I always require CSS fundamentals knowledge regardless of which styling system a team uses."

---

### Trap 3: "CSS Modules prevent all style conflicts"

**The trap:** CSS Modules do scope styles locally — but there are multiple escape hatches that can re-introduce conflicts.

**Why it's wrong:**
> "CSS Modules provide local scope by default — the `.button` class becomes `.button_a3f7b2` at build time. But there are several ways conflicts can leak:
>
> First, `:global()` selectors. Any CSS written inside `:global(.button) { }` is not scoped — it emits a global `.button` selector. Developers use this to target library components and forget that it escapes the module.
>
> Second, CSS composition: `composes: button from './base.module.css'` pulls in styles from another module. If that base module has `:global()` rules, you've imported globals.
>
> Third, CSS custom properties: custom properties cascade through the DOM including across shadow DOM boundaries (they penetrate shadow DOM, unlike regular inherited properties). If you define `--color-primary` in a CSS Module selector, it cascades to all child elements including those styled by other modules.
>
> Fourth, animation names: keyframe names in CSS Modules are locally scoped by default in most configurations, but some older tooling versions don't scope them, leading to `@keyframes slide-in` collisions globally.
>
> The right mental model: CSS Modules provide *class name* isolation, not *style effect* isolation. Side effects through the cascade still apply."

---

### Trap 4: "Inline styles are fine for dynamic values"

**The trap:** Positioned as a pragmatic solution to dynamic styling — "why import a whole library when you can just use style={{}}?"

**Why it's wrong:**
> "Inline styles are a dead end for real UI work. The fundamental limitations:
>
> 1. **No pseudo-selectors**: You cannot write `:hover`, `:focus`, `:focus-visible`, `::before`, `::after` with inline styles. If your dynamic value needs to affect hover state, inline styles can't do it.
>
> 2. **No media queries**: Responsive design via inline styles requires JavaScript `window.matchMedia` listeners, which are slower and don't benefit from media query cache invalidation that the browser optimizes natively.
>
> 3. **No CSS animations**: `@keyframes` and `animation` properties on inline styles are extremely limited.
>
> 4. **Performance**: Every inline style object in JSX creates a new object reference on each render. Combined with many dynamic components, this increases GC pressure. React does shallow-compare style objects but new object references force style updates.
>
> 5. **No cascade advantage**: Inline styles have the highest specificity (short of `!important`), making them impossible to override from design system utilities.
>
> **The correct pattern for dynamic values**: CSS custom properties set inline, referenced in CSS classes.
> ```tsx
> // Correct: set the variable inline, use it in CSS
> <div style={{ '--progress': `${value}%` } as React.CSSProperties}
>      className={styles.progress} />
> // .progress::after { width: var(--progress); }
> ```
> This gives you dynamic values with full CSS capability — pseudo-selectors, transitions, media queries all work."

---

### Trap 5: "More specific selector = more reliable styling"

**The trap:** Engineers from a jQuery/global CSS background often think specificity is a tool for reliability — "I'll just make my selector more specific to win."

**Why it's wrong:**
> "High specificity is a debt instrument in CSS — you borrow authority now and pay compound interest forever. Once a selector chain reaches `.page .section .component .button.is-active`, the only way to override it is an even longer chain or `!important`. This is how `!important` hell starts: someone writes `!important` to override a specific selector, then someone else writes `!important` to override that, and now you have `!important` in 47 places.
>
> The professional approach is low and flat specificity everywhere. A single class selector (specificity 0-1-0) is the target. Component isolation via CSS Modules or Tailwind's utility classes achieves this — every class has the same specificity, and you manage priority with layer order, not specificity points.
>
> CSS `@layer` is the correct modern tool for priority management. Layered styles always lose to unlayered styles regardless of specificity, and layers beat each other in declared order regardless of specificity. This means you can have:
> ```css
> @layer utilities { .text-red { color: red; } }    /* wins */
> @layer components { .card .title { color: blue; } }  /* loses */
> ```
> The utility (specificity 0-1-0) beats the component (specificity 0-2-0) because of layer order, not specificity. This is the correct model."

---

### Trap 6: "Tailwind's JIT compiler generates CSS at runtime"

**The trap:** The term "Just-in-Time" sounds like runtime. Interviewers or candidates confuse Tailwind's JIT with CSS-in-JS runtime generation.

**Why it's wrong:**
> "Tailwind's JIT compiler runs at **build time**, not runtime. The terminology is borrowed from JIT compilation (like JVM JIT) but in Tailwind's context it means 'generate only the classes that appear in your source files at build time' rather than shipping the entire Tailwind stylesheet (which was 3MB+ before purging).
>
> The JIT scanner reads your source files during the build process, identifies every Tailwind class string, and generates only those CSS rules. The output is a static `.css` file — no JavaScript, no runtime style injection, no DOM manipulation.
>
> This is the opposite of CSS-in-JS runtime generation. Tailwind's output is indistinguishable from hand-written CSS — it's a static asset served by a CDN with perfect caching behavior.
>
> The distinction matters for performance conversations: Tailwind has zero runtime styling overhead. The only JavaScript in play is your component logic, not style generation."

---

## 6. PRODUCTION TYPESCRIPT/REACT CODE EXAMPLES

### Example 1: CSS Modules with TypeScript — typed class names

```typescript
// Button.module.css.d.ts (auto-generated by typed-css-modules)
declare const styles: {
  readonly button: string;
  readonly primary: string;
  readonly danger: string;
  readonly sm: string;
  readonly lg: string;
};
export default styles;

// Button.tsx
import styles from './Button.module.css';
import cx from 'clsx';

type ButtonProps = {
  intent?: 'primary' | 'danger';
  size?: 'sm' | 'lg';
  children: React.ReactNode;
} & React.ButtonHTMLAttributes<HTMLButtonElement>;

export const Button = ({ intent = 'primary', size = 'sm', children, className, ...props }: ButtonProps) => (
  <button className={cx(styles.button, styles[intent], styles[size], className)} {...props}>
    {children}
  </button>
);
```

---

### Example 2: Vanilla Extract — typed theme contract

```typescript
// theme.css.ts
import { createThemeContract, createTheme } from '@vanilla-extract/css';

export const vars = createThemeContract({
  color: { primary: null, surface: null, text: null },
  radius: { sm: null, md: null },
});

export const lightTheme = createTheme(vars, {
  color: { primary: '#2563eb', surface: '#ffffff', text: '#111827' },
  radius: { sm: '4px', md: '8px' },
});

export const darkTheme = createTheme(vars, {
  color: { primary: '#60a5fa', surface: '#111827', text: '#f9fafb' },
  radius: { sm: '4px', md: '8px' },
});
```

---

### Example 3: CVA with Tailwind — type-safe variant API

```typescript
// components/Badge/Badge.tsx
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const badge = cva('inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium', {
  variants: {
    variant: {
      default:     'bg-gray-100 text-gray-800',
      success:     'bg-green-100 text-green-800',
      destructive: 'bg-red-100 text-red-800',
      warning:     'bg-yellow-100 text-yellow-800',
    },
  },
  defaultVariants: { variant: 'default' },
});

type BadgeProps = React.HTMLAttributes<HTMLDivElement> & VariantProps<typeof badge>;

export const Badge = ({ className, variant, ...props }: BadgeProps) => (
  <div className={cn(badge({ variant }), className)} {...props} />
);
```

---

### Example 4: CSS Custom Properties — runtime theming without JS re-render

```typescript
// ThemeProvider.tsx
type Theme = 'light' | 'dark' | 'high-contrast';

export const ThemeProvider = ({ children }: { children: React.ReactNode }) => {
  const [theme, setTheme] = React.useState<Theme>('light');

  React.useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    // CSS handles the rest — no component re-renders for theme change
  }, [theme]);

  return (
    <ThemeContext.Provider value={{ theme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
};
```

```css
/* globals.css */
:root { --color-surface: #ffffff; --color-text: #111827; }
[data-theme="dark"] { --color-surface: #111827; --color-text: #f9fafb; }
[data-theme="high-contrast"] { --color-surface: #000000; --color-text: #ffffff; }
```

---

### Example 5: CSS @layer — specificity management

```css
/* app/globals.css */
@layer reset, tokens, base, components, utilities, overrides;

@layer reset {
  *, *::before, *::after { box-sizing: border-box; margin: 0; }
}

@layer tokens {
  :root { --space-4: 1rem; --color-brand: #2563eb; }
}

@layer components {
  .card { background: var(--color-surface); padding: var(--space-4); }
}

@layer utilities {
  .mt-4  { margin-top: var(--space-4); }
  .text-brand { color: var(--color-brand); }
}
/* utilities always beat components; components always beat reset — explicit, no surprises */
```

---

### Example 6: Container Query — component-level responsiveness

```css
/* Card.module.css */
.wrapper {
  container-type: inline-size;
  container-name: card;
}

.card {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

@container card (min-width: 400px) {
  .card { flex-direction: row; align-items: center; }
  .image { width: 120px; flex-shrink: 0; }
}
```

```tsx
// Card.tsx — works in sidebar AND main grid without prop threading
export const Card = ({ title, image }: CardProps) => (
  <div className={styles.wrapper}>
    <div className={styles.card}>
      <img src={image} className={styles.image} alt="" />
      <h3>{title}</h3>
    </div>
  </div>
);
```

---

### Example 7: Style Dictionary config — token pipeline

```javascript
// style-dictionary.config.js
module.exports = {
  source: ['tokens/**/*.json'],
  platforms: {
    css: {
      transformGroup: 'css',
      prefix: 'ds',
      buildPath: 'src/tokens/',
      files: [{ destination: 'tokens.css', format: 'css/variables' }],
    },
    ts: {
      transformGroup: 'js',
      buildPath: 'src/tokens/',
      files: [{ destination: 'tokens.ts', format: 'javascript/es6' }],
    },
  },
};
// Output: --ds-color-brand-primary, --ds-space-md, etc.
```

---

### Example 8: ESLint rule — enforce token usage, ban hardcoded colors

```javascript
// .eslintrc.js
module.exports = {
  rules: {
    'no-restricted-syntax': [
      'error',
      {
        // Ban style={{ color: '#...' }} — use CSS custom property
        selector: "JSXAttribute[name.name='style'] ObjectExpression Property[key.name=/color|background/] Literal[value=/^#|^rgb/]",
        message: 'Use a CSS custom property token instead of a hardcoded color.',
      },
      {
        // Ban import of styled from styled-components in new files
        selector: "ImportDeclaration[source.value='styled-components'] ImportDefaultSpecifier",
        message: 'New components must use Vanilla Extract or CSS Modules. See migration guide.',
      },
    ],
  },
};
```

---

### Example 9: Tailwind config — design token integration

```typescript
// tailwind.config.ts
import type { Config } from 'tailwindcss';
import tokens from './src/tokens/tokens.json';

const config: Config = {
  content: ['./src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          primary:   tokens.color.brand.primary.value,
          secondary: tokens.color.brand.secondary.value,
        },
      },
      spacing: Object.fromEntries(
        Object.entries(tokens.space).map(([k, v]) => [k, (v as any).value])
      ),
    },
  },
};

export default config;
```

---

### Example 10: Dynamic CSS custom property — progress bar without inline style limitations

```tsx
// ProgressBar.tsx
interface ProgressBarProps { value: number; max?: number; }

export const ProgressBar = ({ value, max = 100 }: ProgressBarProps) => {
  const pct = Math.min(100, Math.max(0, (value / max) * 100));
  return (
    <div
      className={styles.track}
      style={{ '--progress': `${pct}%` } as React.CSSProperties}
      role="progressbar"
      aria-valuenow={value}
    >
      <div className={styles.fill} />
    </div>
  );
};
```

```css
/* ProgressBar.module.css */
.track { width: 100%; background: var(--color-surface-2); border-radius: 9999px; overflow: hidden; }
.fill  {
  height: 8px;
  width: var(--progress, 0%);
  background: var(--color-brand);
  transition: width 300ms ease;
}
/* Pseudo-selectors, transitions — impossible with pure inline styles */
```

---

## 7. INTERVIEW CHEAT SHEET

### Core Trade-off Matrix

| Approach          | Runtime Cost | SSR Complexity | Type Safety | Dynamic Props | Token Integration |
|-------------------|-------------|----------------|-------------|---------------|-------------------|
| CSS Modules       | Zero         | None           | Via d.ts    | Limited (CPs) | CSS custom props  |
| styled-components | High         | High (collect) | Good        | Excellent     | ThemeProvider     |
| Emotion           | Medium-High  | Medium         | Good        | Excellent     | ThemeProvider     |
| Vanilla Extract   | Zero         | None           | Excellent   | Via recipe    | createThemeContract|
| Linaria           | Zero         | None           | Moderate    | Limited       | CSS custom props  |
| Tailwind CSS      | Zero         | None           | Via CVA     | Via CP hacks  | tailwind.config.ts |

---

### When to Choose Each

| Scenario                                          | Best Choice                    |
|---------------------------------------------------|--------------------------------|
| Greenfield product, speed matters                 | Tailwind + CVA                 |
| Reusable component library (external consumers)   | Vanilla Extract                |
| Team unfamiliar with utility-first CSS            | CSS Modules + stylelint        |
| Complex runtime theming, many prop-driven styles  | Emotion (with SSR cache setup) |
| Large migration from styled-components            | Vanilla Extract                |
| Design tokens across web + mobile                 | Style Dictionary + CSS vars    |
| Inherited mixed codebase, stop specificity wars   | CSS @layer migration           |

---

### Key Concepts to Know Cold

**CSS Custom Properties:**
- Cascade through the DOM (including from parent to child)
- Penetrate Shadow DOM (unlike regular inherited properties)
- Change at runtime without JS re-render via attribute/class toggle
- Can be set inline for dynamic values, referenced in CSS for pseudo-selector support

**CSS @layer:**
- Unlayered styles always beat layered styles (regardless of specificity)
- Layers beat each other in declaration order (first declared = lowest priority)
- Use to tame third-party library specificity without `!important`

**Tailwind JIT:**
- Runs at BUILD TIME — scans source files, emits only used classes
- Zero runtime — output is a static CSS file
- Dynamic class names at runtime? Use CSS custom properties + arbitrary values

**Container Queries:**
- `container-type: inline-size` on the wrapper element
- `@container name (min-width: Xpx)` in CSS
- Responds to container width, not viewport width
- Full browser support since late 2023

**Vanilla Extract:**
- All style definitions in `.css.ts` files — TypeScript, but treated as CSS
- Extracted to static CSS at build time by Vite/webpack plugin
- `createThemeContract` — define token shape with no values (TypeScript enforces completeness)
- `recipe` from `@vanilla-extract/recipes` for Tailwind-style variant APIs

---

### Specificity Quick Reference

```
Inline style:        1-0-0-0  (always wins, avoid for theming)
ID selector:         0-1-0-0  (avoid in component CSS)
Class/attr/pseudo:   0-0-1-0  (target — use only class selectors in components)
Element/pseudo-elem: 0-0-0-1  (OK for resets only)

@layer rule: layer order beats specificity
!important: beats everything (except !important in higher-specificity selector)
```

---

### SSR CSS-in-JS Checklist (styled-components / Emotion)

- [ ] `ServerStyleSheet.collectStyles()` wraps the render tree
- [ ] `sheet.getStyleTags()` injected into `<head>` before HTML flush
- [ ] `sheet.seal()` called after injection to prevent memory leaks
- [ ] Emotion: `createCache` per request, `extractCritical` from `@emotion/server`
- [ ] Test FOUC by disabling JS: page should look styled before hydration
- [ ] Monitor TTFB — if `collectStyles` > 50ms, begin migration to Vanilla Extract

---

### Design Token Governance Rules

1. No raw hex values in component files — ESLint enforces
2. No `px` magic numbers — spacing must reference scale tokens
3. Token additions require design team PR review
4. Style Dictionary runs in CI — generated files are committed, not hand-edited
5. Token names follow semantic pattern: `--color-{role}-{prominence}` not `--color-blue-500`
6. Breaking token changes (rename/delete) require major version bump in design system package

---

### Performance Quick Hits

| Optimization                          | Impact          | Tool                            |
|---------------------------------------|-----------------|---------------------------------|
| Critical CSS extraction               | TTFB / FCP      | critters, `next/font`           |
| CSS containment (`contain: content`)  | Layout/paint    | Manual CSS on isolated islands  |
| Unused CSS purging                    | Transfer size   | Tailwind JIT, PurgeCSS          |
| Defer non-critical stylesheets        | FCP / render-blocking | `rel="preload"` + `onload` |
| CSS custom property for theme switch  | No JS re-render | data-attribute selector          |
| Avoid inline style objects in loops   | GC pressure     | CSS class + custom property      |

---

### Top 5 Things That Signal Seniority in This Interview

1. **You distinguish runtime CSS-in-JS from zero-runtime** without prompting, and articulate the SSR cost specifically.
2. **You reach for CSS custom properties** before JavaScript for dynamic theming, and explain why.
3. **You name CSS @layer** when the question involves specificity conflicts or third-party library overrides.
4. **You mention Style Dictionary** for design token governance — not just "we have a theme object."
5. **You give a migration path** rather than a greenfield recommendation when asked about a legacy codebase — knowing which battles to pick is architecture.

---

*Last updated: 2026-08 | Covers CSS Modules, styled-components, Emotion, Vanilla Extract, Linaria, Tailwind CSS, CSS Custom Properties, @layer, Container Queries, Style Dictionary, BEM, CUBE CSS, CVA, CSS Containment*
