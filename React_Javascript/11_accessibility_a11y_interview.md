# React Accessibility (a11y) — 15-YOE Architect Interview Prep

> Target role: Staff / Principal Engineer, Frontend Architect  
> Scope: WCAG 2.2, React 18+, TypeScript, real production patterns  
> Last updated: 2026-08

---

## 1. BIG PICTURE — ASCII Diagrams

### 1a. WCAG 2.2 Conformance Levels

```
╔══════════════════════════════════════════════════════════════════╗
║              WCAG 2.2 — POUR PRINCIPLES                          ║
╠══════════════╦═══════════════════════════════════════════════════╣
║  PRINCIPLE   ║  KEY CRITERIA (most relevant for web apps)        ║
╠══════════════╬═══════════════════════════════════════════════════╣
║ Perceivable  ║ 1.1.1 Non-text alt text (A)                       ║
║              ║ 1.3.1 Info & relationships via semantics (A)       ║
║              ║ 1.4.1 Use of color — not sole means (A)           ║
║              ║ 1.4.3 Color contrast 4.5:1 text, 3:1 large (AA)  ║
║              ║ 1.4.4 Resize text 200% no loss (AA)               ║
║              ║ 1.4.11 Non-text contrast 3:1 UI elements (AA)     ║
╠══════════════╬═══════════════════════════════════════════════════╣
║ Operable     ║ 2.1.1 All functionality via keyboard (A)          ║
║              ║ 2.1.2 No keyboard trap (A)                        ║
║              ║ 2.4.3 Focus order meaningful (A)                  ║
║              ║ 2.4.7 Focus visible (AA)                          ║
║              ║ 2.4.11 Focus Not Obscured - partially (AA) 2.2    ║
║              ║ 2.5.3 Label in name (A) — visible label in name   ║
╠══════════════╬═══════════════════════════════════════════════════╣
║ Understandable║ 3.1.1 Language of page (A)                       ║
║              ║ 3.2.1 On focus — no context change (A)            ║
║              ║ 3.3.1 Error identification (A)                    ║
║              ║ 3.3.2 Labels or instructions (A)                  ║
║              ║ 3.3.7 Redundant entry (A) — new in 2.2            ║
╠══════════════╬═══════════════════════════════════════════════════╣
║ Robust       ║ 4.1.2 Name, Role, Value for all UI (A)            ║
║              ║ 4.1.3 Status messages via role/property (AA) 2.1  ║
╚══════════════╩═══════════════════════════════════════════════════╝

Conformance Levels:
  [A]   — Must have. Legal baseline in most jurisdictions.
  [AA]  — Industry standard. Required by ADA, EN 301 549, AODA.
  [AAA] — Enhanced. Aim where possible (e.g. sign language video).
```

### 1b. Accessibility Tree & AT Interaction Model

```
  Browser DOM (HTML)
  ┌─────────────────────────────────────────┐
  │  <div class="modal" role="dialog"        │
  │    aria-labelledby="modal-title"         │
  │    aria-modal="true">                    │
  │    <h2 id="modal-title">Confirm</h2>     │
  │    <button>OK</button>                   │
  │  </div>                                  │
  └──────────────┬──────────────────────────┘
                 │  Browser computes
                 ▼
  Accessibility Tree (AOM)
  ┌─────────────────────────────────────────┐
  │  dialog "Confirm"  [modal=true]          │
  │    ├── heading level=2 "Confirm"         │
  │    └── button "OK"  [focusable]          │
  └──────────────┬──────────────────────────┘
                 │  OS Accessibility API
                 │  macOS: NSAccessibility
                 │  Windows: IAccessible2 / UIA
                 ▼
  Assistive Technology (AT)
  ┌─────────────────────────────────────────┐
  │  Screen Reader (NVDA / VoiceOver / JAWS) │
  │  ► Announces: "Confirm, dialog"          │
  │  ► Reads heading, then focuses button    │
  │  ► User presses Space/Enter → activates  │
  └─────────────────────────────────────────┘

  Key: What is NOT in the DOM (e.g. CSS pseudo-elements,
       aria-hidden="true" subtrees) is NOT in the a11y tree.
       React portals ARE in the a11y tree at their DOM position.
```

### 1c. Keyboard Navigation Model

```
  Tab / Shift+Tab  ──►  Moves between focusable elements
  Arrow Keys       ──►  Moves within composite widgets
                        (menu, listbox, radio group, tabs)
  Enter / Space    ──►  Activates buttons, toggles checkboxes
  Escape           ──►  Closes dialogs, menus, tooltips
  Home / End       ──►  Jump to first/last item in widget

  Roving tabIndex pattern (composite widget):
  ┌──────────────────────────────────────────────┐
  │  tablist (role="tablist")                     │
  │    tab[0] tabIndex={0}   ← only this in tab  │
  │    tab[1] tabIndex={-1}  ← arrow key reaches │
  │    tab[2] tabIndex={-1}  ← arrow key reaches │
  └──────────────────────────────────────────────┘
  Rule: Exactly ONE item with tabIndex=0 at a time.
        Rest are tabIndex=-1, reachable only by arrows.
```

---

## 2. CONVERSATIONAL INTERVIEW SCRIPT — 15-YOE Architect Voice

### How to Open an Accessibility Discussion

> Use this when the interviewer asks "Tell me about your approach to accessibility."

---

"Accessibility for me is less a checklist and more a design constraint I bake in from day one — similar to how I'd treat performance or security. In my experience, retrofitting a11y onto a mature codebase costs roughly ten times more than designing with it in mind. I've led three large-scale a11y remediation projects, and in all three cases the root cause was the same: teams treated it as a QA concern rather than an architecture concern.

My framework is WCAG 2.2 AA as the hard floor — that's the legal baseline for most of our markets. But I go beyond the checklist. I think about the interaction model: how does a keyboard-only user navigate this product? How does a screen reader user build a mental map of the page? How does a user on 200% zoom experience our layout?

On the React side, I focus on three things: semantic HTML first, ARIA only when native won't do, and programmatic focus management at route and modal boundaries. Automated tooling like axe-core catches maybe 30% of real issues — the rest requires actual screen reader testing with NVDA on Windows and VoiceOver on Mac.

I also push for accessibility in the design system layer — if your Button, Modal, and Combobox components are accessible by default, every team that consumes them gets accessibility for free. That's the leverage point at scale."

---

### How to Answer "How do you prioritize a11y work?"

"I triage by impact and legal risk. Critical path interactions — auth, checkout, core navigation — get WCAG AA treatment before launch. Secondary features get scheduled. I also involve legal early: in the US, ADA Title III applies to public-facing web apps, and there were over 4,000 web accessibility lawsuits in 2023 alone. That conversation usually unlocks budget.

I also set up axe-core in CI so regressions don't sneak in — it's not comprehensive but it's a great regression net. And I schedule quarterly manual testing sessions with real AT users, not just developers running VoiceOver for five minutes."

---

## 3. SCENARIO Q&As (Standard, 8+)

---

### Q1: A designer hands you a custom dropdown. Native `<select>` won't work because it needs to render rich content (icons, descriptions). How do you implement it accessibly?

**Answer (15-YOE):**

This is a combobox or listbox pattern from ARIA Authoring Practices Guide (APG). The key decisions:

1. Use `role="combobox"` on the input, `role="listbox"` on the dropdown container, `role="option"` on each item.
2. Implement roving tabIndex inside the listbox — exactly one `tabIndex=0`, rest `tabIndex=-1`.
3. Wire keyboard: Arrow Down/Up moves between options, Enter/Space selects, Escape closes and returns focus to the trigger.
4. Connect with ARIA: `aria-expanded`, `aria-controls` (pointing to listbox id), `aria-activedescendant` (pointing to focused option id).
5. Announce selection: option text is the accessible name of each `role="option"`.

The most common mistake is getting focus management wrong on close: focus must return to the trigger button, not drop to the document body.

I prefer using Radix UI's Select or Headless UI's Combobox rather than hand-rolling, because they've already solved these edge cases. The architectural question is whether to wrap them in your design system to enforce consistent accessible naming.

---

### Q2: After a client-side route change in a React SPA, screen reader users lose context — they don't know the page changed. How do you fix this?

**Answer (15-YOE):**

This is one of the most common SPA accessibility failures. The browser doesn't reload so VoiceOver/NVDA don't announce a page change.

Three approaches, in order of preference:

**Option A — Focus the `<h1>` or main content area on route change.** After navigation, programmatically move focus to the new page's heading. Users hear the page title announced.

**Option B — Live region route announcer.** A visually-hidden `aria-live="assertive"` region that emits the new page title on route change. Libraries like `@reach/router` (now deprecated) used this.

**Option C — Focus the skip-to-content link or `<main>` element.** Set `tabIndex={-1}` on `<main>` so it's programmatically focusable without appearing in the tab order.

I use Option A in React Router v6 — fire a `useEffect` on `location.pathname` change and call `.focus()` on a ref attached to the `<h1>`. The `<h1>` needs `tabIndex={-1}` to be programmatically focusable.

Also critical: update `document.title` on route change. Screen reader users use the title to orient.

---

### Q3: Your toast notification library fires a success/error message after async operations. Screen reader users never hear these. What's wrong and how do you fix it?

**Answer (15-YOE):**

The toasts are being rendered to the DOM but there's no mechanism telling the AT that new content appeared. The fix is `aria-live` regions.

Rules:
- `aria-live="polite"` — waits for the user to finish current reading. Use for success messages, non-urgent info.
- `aria-live="assertive"` — interrupts immediately. Use for errors that require action, critical warnings. Use sparingly — it's jarring.
- `role="status"` is equivalent to `aria-live="polite"` with `aria-atomic="true"`.
- `role="alert"` is equivalent to `aria-live="assertive"` with `aria-atomic="true"`.

The gotcha: the live region container must exist in the DOM *before* you inject content into it. Injecting a brand new `aria-live` element with content already inside is unreliable across screen readers. Solution: render the live region empty on mount, then populate it dynamically.

For toast libraries, I create a singleton `<div role="status" aria-live="polite" aria-atomic="true">` in the app root and update its text content via a context/store.

---

### Q4: A modal dialog opens but focus stays on the triggering button behind it. What are all the problems with this and how do you fully fix it?

**Answer (15-YOE):**

Problems:
1. Focus is behind the modal — keyboard user can tab through background content.
2. Screen reader user has no indication a dialog opened.
3. When modal closes, focus may not return to trigger — user is lost.

Full fix:

1. **Focus first focusable element in modal on open** — or focus the dialog itself if there's no obvious first element.
2. **Trap focus inside the modal** — Tab and Shift+Tab must cycle only within the modal. This requires intercepting Tab keydown and wrapping around.
3. **Add `aria-modal="true"`** — tells compatible screen readers the rest of the page is inert. Also use the `inert` attribute on background content for full coverage (now baseline in all modern browsers).
4. **Set `role="dialog"` and `aria-labelledby`** pointing to the modal title.
5. **On close: return focus to the trigger element** — store a ref to the trigger before opening, call `.focus()` on close.

I use Radix UI's `<Dialog>` component in production — it handles all of the above including the `inert` cascade. Writing focus traps manually is error-prone and breaks on dynamic content changes inside the modal.

---

### Q5: A form has inline validation errors that appear after blur. How do you make these errors accessible?

**Answer (15-YOE):**

Two problems to solve: association and announcement.

**Association:** Link the error message to the input using `aria-describedby`. The input's `aria-describedby` should point to the error element's `id`. Even when there's no error, the element can exist (empty or hidden) so the reference is stable.

**Announcement:** Screen readers will announce `aria-describedby` content when the field is focused or described. For real-time inline validation, also add `role="alert"` or `aria-live="polite"` on the error container so it's announced immediately when it appears.

**`aria-invalid="true"`** on the input signals an error state — screen readers announce "invalid" alongside the input label.

**Required fields:** Use `aria-required="true"` (or native `required`) — don't rely solely on a visual asterisk.

At the form level, on submit failure, move focus to the first error field or a summary `role="alert"` region listing all errors. This is critical — users who submitted and got no feedback assume nothing happened.

---

### Q6: You're building a data table with complex headers (merged cells, multi-level headers). How do you make it accessible?

**Answer (15-YOE):**

Simple tables: use `<th scope="col">` and `<th scope="row">`. Screen readers use `scope` to associate header cells with data cells.

Complex tables (merged headers, nested categories): `scope` isn't sufficient. Use `id` on each `<th>` and `headers` attribute on each `<td>` listing the ids of all applicable header cells. This creates explicit associations.

Also:
- `<caption>` to give the table a visible title. Alternatively `aria-label` or `aria-labelledby` on `<table>`.
- `<thead>`, `<tbody>`, `<tfoot>` for semantic structure.
- For very large tables, consider `role="grid"` with arrow-key navigation (grid pattern) to avoid hundreds of tab stops.
- Never use `<table>` for layout — `role="presentation"` overrides table semantics if you must.

Common mistake: building tables with `<div>` for layout flexibility, then adding ARIA grid roles. The result is usually broken because cell/row count computations are wrong or column headers don't associate correctly. Prefer native table elements.

---

### Q7: How do you implement a skip link, and why do keyboard-only users care?

**Answer (15-YOE):**

Skip links let keyboard users bypass repetitive navigation (headers, nav bars) and jump directly to main content. Without them, a user on a page with 50 nav links has to Tab through all 50 on every page load.

Implementation:
- First element in `<body>`: `<a href="#main-content" class="skip-link">Skip to main content</a>`
- Target: `<main id="main-content" tabIndex={-1}>` — `tabIndex={-1}` makes it programmatically focusable so focus moves AND the viewport scrolls.
- CSS: visually hidden by default (off-screen), visible only on `:focus`.

The `tabIndex={-1}` on `<main>` is the detail most developers miss. Without it, the browser moves scroll position but focus stays on the skip link — defeating the purpose.

Multiple skip links are fine: "Skip to main content", "Skip to search", "Skip to footer". But keep it minimal — one is usually enough.

---

### Q8: A senior designer insists on using icon-only buttons throughout the UI. How do you handle this?

**Answer (15-YOE):**

Icon-only buttons have no visible text label — screen readers will announce the button's accessible name, which defaults to nothing (or the raw SVG title if there is one). Users hear "button" with no context.

Solutions:

1. **Preferred: `aria-label` on the button.** `<button aria-label="Close dialog"><CloseIcon /></button>`. The icon is decorative — add `aria-hidden="true"` to the SVG so it's not also read.

2. **Visually hidden text.** Wrap text in a `<span className="sr-only">Close dialog</span>` inside the button. The text is in the DOM (good for search, good for AT) but hidden visually. This is often preferable to `aria-label` because it's translatable by i18n systems.

3. **`title` attribute.** Provides a tooltip on hover AND an accessible name fallback, but browser support for it as the accessible name is inconsistent. Don't rely on it alone.

WCAG 2.5.3 (Label in Name): for buttons that have *both* a visible label and an `aria-label`, the `aria-label` must contain the visible text — or AT users who use speech control ("Click Submit") can't match the label.

---

## 4. ADVANCED SCENARIO Q&As (Architect Depth, 4+)

---

### AQ1: You're leading a design system migration for a company with 20 product teams. How do you enforce accessibility across all teams without becoming a bottleneck?

**Answer (15-YOE):**

This is a governance and architecture problem as much as a technical one. My approach:

**Layer 1 — Design system as the floor.** Every primitive component (Button, Input, Modal, Select, Tabs, etc.) is accessible by default. Teams can't easily use inaccessible variants because none exist in the exported API. The accessible behavior is the only behavior. Accessibility is a feature, not an option.

**Layer 2 — CI enforcement.** Integrate `axe-core` via `@axe-core/react` in Storybook and via `jest-axe` in unit tests. This catches regressions without human review. Block PRs that introduce axe violations. This is not the full picture (30% coverage) but it's a zero-effort regression net.

**Layer 3 — Linting.** `eslint-plugin-jsx-a11y` catches static patterns: missing alt text, empty buttons, invalid ARIA usage. This runs in editors and CI. It teaches developers as they type.

**Layer 4 — Contribution model.** Document accessibility requirements in component ADRs. When a team builds a new pattern not in the design system, they go through an accessibility review before publishing. One accessibility architect per guild, not one per company.

**Layer 5 — Metrics.** Track axe violation counts per team in dashboards. Make it visible. Run quarterly AT testing sessions, rotate teams through them.

The goal is to make the accessible path the easiest path. When the design system Button already handles focus styles, ARIA, and keyboard events, teams don't have to think about it.

---

### AQ2: Your product has a drag-and-drop interface for reordering items. How do you make it accessible?

**Answer (15-YOE):**

Drag-and-drop is one of the hardest patterns to make accessible because the interaction model is inherently spatial and mouse-centric.

**The core principle:** Provide an equivalent keyboard mechanism. The drag-and-drop experience can remain as-is for mouse users. The accessible alternative doesn't have to be drag-and-drop at all.

**Approaches:**

1. **Keyboard sort mode.** When a user focuses a draggable item, a "Grab" button activates it. Then arrow keys move it up/down. Spacebar or Enter drops it. This is the ARIA APG "listbox reorder" pattern.

2. **`aria-grabbed` / `aria-dropeffect`** — these ARIA attributes are deprecated in ARIA 1.1 and removed in 1.2. Do not use them. Use the keyboard mechanism above instead.

3. **Live region announcements.** Announce state changes: "Item grabbed. Use arrow keys to move. Press Space to drop or Escape to cancel." When dropped: "Item moved to position 3 of 8."

4. **`role="listitem"` with `aria-roledescription`** — `aria-roledescription="sortable item"` gives AT users context that this item is movable.

Libraries like `@dnd-kit/core` have accessibility hooks built in — `useSortable` fires announcements via a live region. Always audit the announcements with a real screen reader before shipping.

---

### AQ3: You need to build a complex combobox with async search (like a location autocomplete). Walk through the full accessible implementation.

**Answer (15-YOE):**

This is ARIA Authoring Practices pattern: "Combobox with List Autocomplete."

**Markup structure:**
- `<input role="combobox" aria-expanded aria-controls="listbox-id" aria-activedescendant="focused-option-id" aria-autocomplete="list">`
- `<ul role="listbox" id="listbox-id">` — appears below input
- `<li role="option" id="option-{n}" aria-selected>` — each result

**Keyboard behavior:**
- Type in input → triggers async fetch → renders options in listbox
- Arrow Down from input → moves "virtual focus" to first option (sets `aria-activedescendant`, does NOT move DOM focus)
- Arrow Down/Up in list → cycles through options, updating `aria-activedescendant`
- Enter → selects focused option, closes list, updates input value
- Escape → closes list, optionally clears input
- Tab → selects focused option (or closes list if none focused)

**Loading state:** While fetching, announce "Loading..." via `aria-live="polite"` region or `role="status"`. Don't leave users in silence.

**No results:** Announce "No results found" — either via live region or render it as a non-selectable item in the listbox with `aria-disabled="true"`.

**The hard part:** `aria-activedescendant` virtual focus vs DOM focus. Real focus stays on the input at all times (critical for mobile keyboards). The "active" item is indicated only via ARIA. This means you must style the active item via CSS `[aria-selected="true"]` or a data attribute — `:focus-within` alone won't work.

---

### AQ4: How do you approach accessibility testing methodology for a production React app? What does a real testing process look like?

**Answer (15-YOE):**

Testing layers in order of coverage vs effort:

**Layer 1 — Static analysis (free, zero effort after setup)**
- `eslint-plugin-jsx-a11y` catches ~20% of issues at author time
- `jest-axe` in unit/integration tests catches ~30% of rendered output issues
- Run in CI, block on failures

**Layer 2 — Storybook + axe (component-level)**
- `@storybook/addon-a11y` runs axe on every story
- Catches component-level violations before they reach the page
- Authors see violations in the Storybook panel during development

**Layer 3 — E2E testing with axe (page-level)**
- `axe-playwright` or `cypress-axe` runs full-page axe scans in E2E tests
- Catches violations in composed page context that component tests miss

**Layer 4 — Manual keyboard testing (critical)**
- Unplug the mouse. Tab through every user flow.
- Verify: all interactive elements reachable, focus visible, modals trap/return focus, forms validate correctly
- Test with Windows high-contrast mode

**Layer 5 — Screen reader testing (critical, catches 40%+ not found by automation)**
- NVDA + Firefox on Windows (free, most common SR on Windows)
- VoiceOver + Safari on macOS (built-in, used by iOS testers)
- Test: page title, heading structure, landmark regions, form labels, error messages, dynamic content announcements
- Test on iOS with VoiceOver for mobile coverage

**Layer 6 — User testing with AT users (gold standard)**
- Quarterly sessions with disabled users who use AT daily
- Catches real workflow issues, not just technical violations

**Tooling stack I use in production:**
- Dev: eslint-plugin-jsx-a11y + axe DevTools browser extension
- CI: jest-axe, axe-playwright
- Manual: NVDA/VoiceOver, color contrast analyzer, keyboard-only walkthrough checklist
- Design review: Figma accessibility annotations plugin

---

## 5. SENIOR TRAP QUESTIONS (6+)

---

### Trap 1: "We just add aria-label to everything. That makes it accessible, right?"

**The trap:** The candidate agrees or gives a generic "yes aria-label is good" answer.

**Why it's wrong:**
`aria-label` *overwrites* the accessible name computation. If you `aria-label` a button that already has visible text, the visible text and the `aria-label` can diverge — violating WCAG 2.5.3 (Label in Name). Users who rely on speech input ("Click Submit") say the visible label, not the aria-label. The disconnect breaks speech control.

ARIA First Rule: "If you can use a native HTML element or attribute with the semantics and behavior you require, use it rather than re-purposing an element and adding ARIA." Native `<button>Submit</button>` needs no ARIA. `<label>` with `for` needs no ARIA.

Over-use of `aria-label` masks structural problems. If your headings are `<div>` elements with `aria-level`, you're fighting the platform. Use `<h1>-<h6>`.

**The correct answer:** Use native HTML semantics first. Use `aria-label` only when there's no visible text (icon-only buttons) or when the visible text alone isn't descriptive enough in context. Auditing `aria-label` usage is part of my code review checklist.

---

### Trap 2: "We'll add accessibility at the end of the sprint / project."

**The trap:** Candidate nods, or offers "we can do a11y QA at the end."

**Why it's wrong:**
Retrofitting accessibility onto a mature codebase costs 10x more than designing with it in mind. Specific examples:
- A design system built with `<div>` buttons requires every component to be rebuilt or wrapped.
- Complex state management patterns not designed for keyboard interaction require invasive refactors.
- Inaccessible design decisions (color choices, animation-heavy flows, no keyboard path for gestures) are expensive to undo after user research and engineering.

Automated tools catch roughly 30% of WCAG failures. The other 70% (focus management, meaningful labels, cognitive load, temporal sequences) require human judgment early in the design phase.

The "end of sprint" approach also creates a false safety — teams ship inaccessible features thinking a future audit will catch everything.

**The correct answer:** Shift-left. Accessibility in design (annotations), in development (linting, jest-axe), in code review (a11y checklist), in QA (keyboard test, AT test). The cost at each stage is proportional — design changes are cheap, shipped code changes are not.

---

### Trap 3: "We scored 100% on Lighthouse accessibility. We're done."

**The trap:** Candidate accepts this as sufficient coverage.

**Why it's wrong:**
Lighthouse (which uses axe-core under the hood) catches approximately 30% of real WCAG issues. The 100% score means you have no automatically-detectable violations — it does not mean the product is accessible.

What Lighthouse cannot test:
- Whether `aria-label` values are meaningful (it checks presence, not quality)
- Whether focus management in modals is correct
- Whether color contrast passes with dynamic themes
- Whether form error messages are logically connected
- Whether the keyboard interaction model makes sense
- Whether screen reader announcements convey the right information
- Whether the tab order matches reading order
- Whether live region announcements are timed correctly

A product can score 100% Lighthouse and completely fail AT testing.

**The correct answer:** Lighthouse is a useful regression net, not a compliance certificate. We layer manual keyboard testing, screen reader testing, and user testing with AT users on top of automated scanning.

---

### Trap 4: "I put tabIndex={0} on the div, so it's keyboard accessible now."

**The trap:** Candidate agrees that tabIndex={0} is sufficient.

**Why it's wrong:**
`tabIndex={0}` makes an element *focusable* via Tab. It does not make it *operable*. Native interactive elements (`<button>`, `<a>`, `<input>`) have built-in keyboard event handling: Enter/Space activate buttons, Enter follows links. A `<div tabIndex={0}>` receives focus but does nothing when the user presses Enter or Space — unless you wire those event handlers manually.

Three requirements for a custom interactive element:
1. `tabIndex={0}` — focusable
2. `role="button"` (or appropriate role) — announces correctly to AT
3. `onKeyDown` handler for Enter and Space — operable

Missing any one of these creates a broken experience. The common pattern:
```tsx
// Wrong — focusable but not operable
<div tabIndex={0} onClick={handleClick}>Click me</div>

// Right — but still: use a real button instead
<div
  tabIndex={0}
  role="button"
  onClick={handleClick}
  onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') handleClick(); }}
>
  Click me
</div>
```

**The correct answer:** Use `<button>` instead. It gives you focus, keyboard operation, and correct role for free. `tabIndex={0}` on a `<div>` is a code smell — almost always it means a `<button>` or `<a>` should be used instead.

---

### Trap 5: "Our users don't use screen readers, so we don't need to worry about accessibility."

**The trap:** Candidate accepts this framing or doesn't push back.

**Why it's wrong:**

**Data:** 15-26% of the global population has some form of disability. Screen reader users are ~7.6M in the US. But accessibility also benefits users with temporary disabilities (broken arm, eye surgery), situational disabilities (bright sunlight, one hand occupied), and older adults (age-related vision/motor decline). Accessibility features also benefit everyone: captions help in noisy environments, keyboard navigation helps power users.

**Legal risk:** ADA Title III lawsuits against web properties exceeded 4,000/year in the US by 2023. The EU Web Accessibility Directive, AODA (Canada), and EN 301 549 (EU procurement) all require WCAG AA for commercial web apps. A single lawsuit can cost $50K-$500K in settlement and remediation.

**SEO:** Accessible HTML (semantic structure, alt text, clear headings) correlates with better search ranking. Screen readers and search crawlers have similar needs.

**Maintenance:** Semantic, accessible code is better code — clearer structure, fewer edge cases, more testable.

**The correct answer:** This assumption is both empirically wrong and legally risky. We build accessibly for business reasons (legal compliance, market size, SEO), ethical reasons (inclusive design), and quality reasons (better code). I always reframe accessibility as a risk management discussion, not a charity exercise.

---

### Trap 6: "We use `display: none` to hide things visually, but they're still in the DOM for screen readers."

**The trap:** Candidate thinks `display: none` or `visibility: hidden` are ways to provide "screen reader only" content.

**Why it's wrong:**
`display: none` removes the element from the accessibility tree entirely. Screen readers do not announce `display: none` content. The same is true for `visibility: hidden`. These hide content from everyone — sighted users and AT users alike.

To create **visually hidden but AT-accessible** content (the `.sr-only` pattern):
```css
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
```

To hide content from AT but keep it visually visible: `aria-hidden="true"`.

Summary table:
```
  CSS display:none      → hidden from everyone (visual + AT)
  CSS visibility:hidden → hidden from everyone (visual + AT)
  aria-hidden="true"    → hidden from AT only (visible on screen)
  .sr-only class        → hidden visually only (present in AT)
```

**The correct answer:** These are four distinct visibility axes. Conflating them causes either content being announced twice, or not at all. I ensure our design system's `VisuallyHidden` component uses the `.sr-only` pattern, not `display: none`.

---

## 6. PRODUCTION TYPESCRIPT/REACT CODE EXAMPLES

---

### Example 1 — Accessible Modal with Focus Trap

```tsx
// AccessibleModal.tsx
import { useEffect, useRef } from 'react';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  triggerRef: React.RefObject<HTMLElement>;
}

export function AccessibleModal({ isOpen, onClose, title, children, triggerRef }: ModalProps) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const titleId = useId();

  useEffect(() => {
    if (!isOpen) return;
    const firstFocusable = dialogRef.current?.querySelector<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    firstFocusable?.focus();
    return () => { triggerRef.current?.focus(); };
  }, [isOpen]);

  if (!isOpen) return null;
  return (
    <div role="dialog" aria-modal="true" aria-labelledby={titleId}
      ref={dialogRef} onKeyDown={(e) => e.key === 'Escape' && onClose()}>
      <h2 id={titleId}>{title}</h2>
      {children}
      <button onClick={onClose}>Close</button>
    </div>
  );
}
```

---

### Example 2 — Live Region Toast Announcer

```tsx
// ToastAnnouncer.tsx
import { useEffect, useState } from 'react';

export function ToastAnnouncer({ message, type }: { message: string; type: 'polite' | 'assertive' }) {
  const [announced, setAnnounced] = useState('');

  useEffect(() => {
    // Clear then set to force re-announcement of identical messages
    setAnnounced('');
    const timer = setTimeout(() => setAnnounced(message), 50);
    return () => clearTimeout(timer);
  }, [message]);

  return (
    <div
      aria-live={type}
      aria-atomic="true"
      role={type === 'assertive' ? 'alert' : 'status'}
      className="sr-only"
    >
      {announced}
    </div>
  );
}
```

---

### Example 3 — Skip Link

```tsx
// SkipLink.tsx
export function SkipLink() {
  return (
    <a
      href="#main-content"
      className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50
                 focus:px-4 focus:py-2 focus:bg-white focus:text-black focus:border-2 focus:border-black"
    >
      Skip to main content
    </a>
  );
}

// Usage in layout:
// <SkipLink />
// <main id="main-content" tabIndex={-1}>...</main>
```

---

### Example 4 — Accessible Form Field with Error

```tsx
// FormField.tsx
import { useId } from 'react';

interface FormFieldProps {
  label: string;
  error?: string;
  required?: boolean;
  value: string;
  onChange: (v: string) => void;
}

export function FormField({ label, error, required, value, onChange }: FormFieldProps) {
  const inputId = useId();
  const errorId = useId();

  return (
    <div>
      <label htmlFor={inputId}>
        {label}
        {required && <span aria-hidden="true"> *</span>}
        {required && <span className="sr-only"> (required)</span>}
      </label>
      <input
        id={inputId}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        aria-required={required}
        aria-invalid={!!error}
        aria-describedby={error ? errorId : undefined}
      />
      {error && (
        <div id={errorId} role="alert" aria-live="polite">
          {error}
        </div>
      )}
    </div>
  );
}
```

---

### Example 5 — Route Change Focus Management

```tsx
// useFocusOnRouteChange.ts
import { useEffect, useRef } from 'react';
import { useLocation } from 'react-router-dom';

export function useFocusOnRouteChange() {
  const location = useLocation();
  const headingRef = useRef<HTMLHeadingElement>(null);

  useEffect(() => {
    // Small delay to allow React to render new route content
    const timer = setTimeout(() => {
      headingRef.current?.focus();
    }, 100);
    return () => clearTimeout(timer);
  }, [location.pathname]);

  return headingRef;
}

// Usage:
// function PageLayout({ title }: { title: string }) {
//   const headingRef = useFocusOnRouteChange();
//   return <h1 ref={headingRef} tabIndex={-1}>{title}</h1>;
// }
```

---

### Example 6 — Roving TabIndex for Tabs Widget

```tsx
// Tabs.tsx
import { useState, useRef, KeyboardEvent } from 'react';

interface Tab { id: string; label: string; content: React.ReactNode; }

export function Tabs({ tabs }: { tabs: Tab[] }) {
  const [activeIndex, setActiveIndex] = useState(0);
  const tabRefs = useRef<(HTMLButtonElement | null)[]>([]);

  function handleKeyDown(e: KeyboardEvent, index: number) {
    let next = index;
    if (e.key === 'ArrowRight') next = (index + 1) % tabs.length;
    else if (e.key === 'ArrowLeft') next = (index - 1 + tabs.length) % tabs.length;
    else if (e.key === 'Home') next = 0;
    else if (e.key === 'End') next = tabs.length - 1;
    else return;
    e.preventDefault();
    setActiveIndex(next);
    tabRefs.current[next]?.focus();
  }

  return (
    <div>
      <div role="tablist">
        {tabs.map((tab, i) => (
          <button
            key={tab.id}
            role="tab"
            aria-selected={i === activeIndex}
            aria-controls={`panel-${tab.id}`}
            id={`tab-${tab.id}`}
            tabIndex={i === activeIndex ? 0 : -1}
            ref={(el) => { tabRefs.current[i] = el; }}
            onClick={() => setActiveIndex(i)}
            onKeyDown={(e) => handleKeyDown(e, i)}
          >
            {tab.label}
          </button>
        ))}
      </div>
      {tabs.map((tab, i) => (
        <div
          key={tab.id}
          role="tabpanel"
          id={`panel-${tab.id}`}
          aria-labelledby={`tab-${tab.id}`}
          hidden={i !== activeIndex}
        >
          {tab.content}
        </div>
      ))}
    </div>
  );
}
```

---

### Example 7 — Visually Hidden Component

```tsx
// VisuallyHidden.tsx
import { CSSProperties } from 'react';

const styles: CSSProperties = {
  position: 'absolute',
  width: '1px',
  height: '1px',
  padding: 0,
  margin: '-1px',
  overflow: 'hidden',
  clip: 'rect(0, 0, 0, 0)',
  whiteSpace: 'nowrap',
  border: 0,
};

export function VisuallyHidden({ children }: { children: React.ReactNode }) {
  return <span style={styles}>{children}</span>;
}

// Usage: <button><CloseIcon aria-hidden="true" /><VisuallyHidden>Close dialog</VisuallyHidden></button>
```

---

### Example 8 — Accessible Icon Button

```tsx
// IconButton.tsx
import { ButtonHTMLAttributes, forwardRef } from 'react';

interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  icon: React.ReactNode;
  label: string; // Required accessible label
}

export const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(
  ({ icon, label, ...rest }, ref) => (
    <button ref={ref} aria-label={label} type="button" {...rest}>
      <span aria-hidden="true">{icon}</span>
    </button>
  )
);
IconButton.displayName = 'IconButton';
```

---

## 7. INTERVIEW CHEAT SHEET

### WCAG 2.2 Key Numbers

| Criterion | Requirement |
|-----------|------------|
| 1.4.3 (AA) | Text contrast ≥ 4.5:1 (≥ 3:1 for large text ≥ 18pt/14pt bold) |
| 1.4.11 (AA) | UI component / graphical contrast ≥ 3:1 |
| 2.4.7 (AA) | Focus indicator must be visible |
| 2.4.11 (AA, 2.2) | Focus not fully obscured by sticky headers/footers |
| Automated tools | Catch ~30% of WCAG issues |

---

### ARIA Quick Reference

| Scenario | Use |
|----------|-----|
| Button with icon only | `aria-label="Close"` on button, `aria-hidden="true"` on icon |
| Input error message | `aria-describedby` on input pointing to error div |
| Invalid input | `aria-invalid="true"` |
| Required field | `aria-required="true"` or native `required` |
| Live content (non-urgent) | `aria-live="polite"` or `role="status"` |
| Live content (urgent) | `aria-live="assertive"` or `role="alert"` |
| Modal dialog | `role="dialog"` + `aria-modal="true"` + `aria-labelledby` |
| Open/closed widget | `aria-expanded="true/false"` |
| Loading state | `aria-busy="true"` |
| Visually hidden info | `.sr-only` CSS class (NOT `display:none`) |
| Decorative image | `alt=""` (empty string, NOT missing `alt`) |
| Decorative icon | `aria-hidden="true"` |

---

### Native HTML vs ARIA Decision Tree

```
Need an interactive element?
  ├── Button action        → <button>
  ├── Navigation link      → <a href="...">
  ├── Text input           → <input type="text">
  ├── Checkbox             → <input type="checkbox">
  ├── Radio group          → <fieldset><legend> + <input type="radio">
  ├── Select dropdown      → <select> (if options are plain text)
  ├── Heading              → <h1>-<h6>
  ├── Navigation region    → <nav>
  ├── Main content         → <main>
  └── Custom widget        → Use ARIA roles + keyboard handlers
                             (combobox, listbox, tabs, grid, etc.)

Rule: If a native element exists, use it.
      ARIA is for when native HTML doesn't cover the pattern.
```

---

### Focus Management Checklist

```
[ ] Modal opens → focus moves to first focusable element in modal
[ ] Modal closes → focus returns to trigger element
[ ] Focus is trapped within modal (Tab/Shift+Tab cycle inside only)
[ ] Route change → focus moves to new page h1 or main landmark
[ ] document.title updates on route change
[ ] Skip link present, jumps to <main tabIndex={-1}>
[ ] Dialogs have role="dialog" aria-modal="true" aria-labelledby
[ ] Composite widgets use roving tabIndex (tabs, menus, grids)
[ ] No positive tabIndex values (tabIndex > 0) in the codebase
[ ] Focus is always visible (no outline: none without replacement)
```

---

### Screen Reader Testing Matrix

| Screen Reader | Browser | Platform | Use Case |
|---------------|---------|----------|----------|
| NVDA | Firefox | Windows | Most common free SR — primary test target |
| JAWS | Chrome/Edge | Windows | Enterprise, most used globally |
| VoiceOver | Safari | macOS | Mac/iOS development testing |
| VoiceOver | Safari | iOS | Mobile screen reader testing |
| TalkBack | Chrome | Android | Android mobile testing |

Minimum viable testing: NVDA + Firefox (Windows), VoiceOver + Safari (Mac).

---

### Common Mistakes Quick-Reference

| Mistake | Fix |
|---------|-----|
| `<div onClick>` without role | Use `<button>` or add `role="button"` + `onKeyDown` |
| `placeholder` as label | Add `<label>` — placeholder disappears on type |
| `display: none` for screen-reader-only content | Use `.sr-only` CSS pattern |
| Missing `alt` on `<img>` | `alt=""` for decorative, `alt="description"` for informative |
| `aria-label` duplicates visible text | Remove aria-label, let the visible text be the name |
| Positive `tabIndex` (e.g., tabIndex={3}) | Remove — breaks natural tab order |
| Focus rings removed with `outline: none` | Replace with custom focus-visible styles |
| `<table>` for layout | Use CSS Grid/Flex; if must use, add `role="presentation"` |
| Modals without focus trap | Use Radix Dialog or implement focus trap |
| Async content added silently | Wrap in `aria-live` region |

---

### Talking Points by Interviewer Type

**If interviewer is engineering manager:**
"Accessibility reduces legal risk, expands market reach, and improves code quality. I've seen teams save six figures in remediation costs by shifting a11y left."

**If interviewer is tech lead:**
"I enforce a11y at the design system layer so every component is accessible by default. CI catches regressions with jest-axe. Manual AT testing covers the 70% automated tools miss."

**If interviewer is principal/staff engineer:**
"The interesting problems are focus management in complex SPAs, composable ARIA attribute patterns in design systems, and building accessible drag-and-drop with equivalent keyboard mechanisms."

**If asked about WCAG 2.2 new criteria:**
"2.4.11 Focus Not Obscured — sticky headers can't fully cover focused elements. 3.3.7 Redundant Entry — don't ask users to re-enter info they already provided. 2.5.7 Dragging Movements — pointer drag must have single-pointer alternative. 2.5.8 Target Size Minimum — interactive targets ≥ 24x24 CSS pixels."

---

### The 30-Second Accessibility Elevator Pitch

"Accessibility is building for the full range of human capability. Technically, it means WCAG 2.2 AA compliance: semantic HTML, keyboard operability, screen reader support, sufficient color contrast. Architecturally, it means baking it into the design system so teams get it for free. Practically, it means keyboard-first development, aria-live regions for dynamic content, and programmatic focus management at SPA route boundaries. Automated tools catch 30% — the rest needs real AT testing."

---

*End of file — /React_Javascript/11_accessibility_a11y_interview.md*
