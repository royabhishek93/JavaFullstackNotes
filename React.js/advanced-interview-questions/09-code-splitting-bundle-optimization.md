# How do you architect code splitting in a large app?

> **Interview priority:** SHOULD KNOW

## Question

How do you architect code splitting in a large app?

## Beginner Lens

Before memorizing the interview answer, follow the scenario and notice three things: the problem React is solving, the state or browser work that changes, and the rule that keeps the UI correct. Read the code blocks slowly and predict the next result before reading the explanation.

## Detailed Explanation

**HOW TO SAY IT:**

> "I worked on a fintech app where the initial bundle was 2.8MB. Users on
> mobile 4G were waiting 8-10 seconds before anything appeared. We got it
> down to 280KB using three levels of code splitting. Let me walk through
> the approach..."

```
REAL APP: Fintech Dashboard (before → after)

  BEFORE: Monolithic bundle
  ─────────────────────────
  index.js: 2.8MB
  ├─ react + react-dom: 140KB
  ├─ react-pdf (reports): 800KB      ← loaded even for login page
  ├─ chart.js (analytics): 600KB     ← loaded even on dashboard
  ├─ rich-text-editor: 400KB         ← loaded even when no notes open
  ├─ date-fns: 200KB                 ← only 3 functions used!
  └─ application code: 660KB

  AFTER: Route + component splitting
  ────────────────────────────────────
  initial.js: 280KB
  ├─ react + react-dom: 140KB
  ├─ application core: 140KB

  dashboard.js: 120KB     (loaded when /dashboard opens)
  analytics.js: 650KB     (loaded when /analytics opens)  ← chart.js here
  reports.js: 820KB       (loaded when /reports opens)    ← pdf here
  editor.js: 410KB        (loaded when editor modal opens)
  vendor-dates.js: 8KB    (only imported functions, tree-shaken)
```

```
CODE SPLITTING IMPLEMENTATION:

  LEVEL 1: ROUTE SPLITTING (always do this first)
  ─────────────────────────────────────────────────
  const Dashboard  = lazy(() => import('./pages/Dashboard'));
  const Analytics  = lazy(() => import('./pages/Analytics'));
  const Reports    = lazy(() => import('./pages/Reports'));

  function App() {
    return (
      <Suspense fallback={<PageSkeleton />}>
        <Routes>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/reports"   element={<Reports />} />
        </Routes>
      </Suspense>
    );
  }

  LEVEL 2: COMPONENT SPLITTING (heavy, conditional components)
  ─────────────────────────────────────────────────────────────
  // RichTextEditor is 400KB — only loaded when user opens "Add Note" modal
  const RichEditor = lazy(() => import('./components/RichEditor'));

  function NotesModal({ isOpen }) {
    if (!isOpen) return null;   // don't even lazy-load until needed
    return (
      <Suspense fallback={<div>Loading editor...</div>}>
        <RichEditor />
      </Suspense>
    );
  }

  LEVEL 3: FEATURE FLAG SPLITTING
  ──────────────────────────────────
  async function loadFeature(featureKey) {
    if (!featureFlags[featureKey]) return;
    const { Feature } = await import(`./features/${featureKey}`);
    // Feature loaded only for users with flag enabled
  }
```

```
  WHAT NOT TO LAZY LOAD:
  ──────────────────────────────────────────────────────────────
  WRONG: Lazy loading the navigation bar
  const Navbar = lazy(() => import('./Navbar')); // ← bad!
  // Navbar is ALWAYS visible on initial load
  // Lazy loading it = layout shift = worse LCP = bad Core Web Vital

  RULE: Only lazy-load components that are:
  ✓ Below the fold (user must scroll to see)
  ✓ Behind a tab or accordion
  ✓ Inside a modal (not open by default)
  ✓ Feature-flagged (not all users see it)
  ✓ Route-specific (separate pages)
```

---
