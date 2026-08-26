# React Architecture Patterns — 15-YOE Interview Prep

> Target: Senior / Staff / Principal Engineer rounds at FAANG, fintech, SaaS companies.
> Tone: production-experienced, opinionated, trade-off-aware.

---

## 1. Big Picture ASCII Diagrams

### Component Composition Patterns

```
UNIDIRECTIONAL DATA FLOW (top-down)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

        ┌──────────────────────┐
        │      App (state)     │
        │   data, dispatch     │
        └──────────┬───────────┘
                   │ props
         ┌─────────┴─────────┐
         ▼                   ▼
   ┌───────────┐       ┌───────────┐
   │FeatureA   │       │FeatureB   │
   │(container)│       │(container)│
   └─────┬─────┘       └─────┬─────┘
         │ props              │ props
    ┌────┴────┐          ┌────┴────┐
    ▼         ▼          ▼         ▼
 ┌──────┐ ┌──────┐   ┌──────┐ ┌──────┐
 │  UI  │ │  UI  │   │  UI  │ │  UI  │
 └──────┘ └──────┘   └──────┘ └──────┘


COMPOUND COMPONENT PATTERN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    <Select value={v} onChange={fn}>     ← Parent owns state
        <Select.Trigger />               ← Reads context
        <Select.Content>                 ← Reads context
            <Select.Option value="a" />  ← Fires context callback
            <Select.Option value="b" />
        </Select.Content>
    </Select>

    Context (implicit shared state)
    ┌────────────────────────────────┐
    │ { value, onChange, open,       │
    │   setOpen, selectedLabel }     │
    └────────────────────────────────┘
           ▲              ▲
     Select.Trigger   Select.Option
       reads open       calls onChange


RENDER PROPS — INVERSION OF CONTROL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    <DataFetcher url="/api/users">
      {({ data, loading, error }) =>   ← Consumer decides rendering
        loading ? <Spinner /> :
        error   ? <ErrorBanner /> :
                  <UserTable data={data} />
      }
    </DataFetcher>

    vs Hook version (simpler but loses JSX flexibility):
    const { data, loading, error } = useDataFetcher("/api/users");


HOC WRAPPING / COMPOSITION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    withAnalytics(
      withAuth(
        withErrorBoundary(
          UserDashboard
        )
      )
    )

    → renders as:
    <AnalyticsProvider>
      <AuthGuard>
        <ErrorBoundary>
          <UserDashboard {...ownProps} />
        </ErrorBoundary>
      </AuthGuard>
    </AnalyticsProvider>


CONTAINER / PRESENTATIONAL SPLIT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    UserListContainer          UserList (pure)
    ─────────────────          ────────────────
    useUsers()                 props: { users, onSelect }
    useFilters()               No data fetching
    handleSelect()             No business logic
    → passes props down →      Fully testable in Storybook


MICRO-FRONTEND MODULE FEDERATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    ┌──────────────────────────────────────────┐
    │              Shell App (Host)            │
    │   ┌──────────────────────────────────┐   │
    │   │  React Router / Layout           │   │
    │   │  Shared: react, react-dom, MUI   │   │
    │   └────────┬──────────────┬──────────┘   │
    │            │              │               │
    │   ┌────────▼──────┐ ┌────▼────────────┐  │
    │   │  MFE: Billing │ │ MFE: Analytics  │  │
    │   │  (Remote 1)   │ │ (Remote 2)      │  │
    │   │  own deploy   │ │ own deploy      │  │
    │   └───────────────┘ └─────────────────┘  │
    └──────────────────────────────────────────┘
```

---

## 2. Conversational Interview Script

### How a 15-YOE Engineer Speaks

**Bad (junior answer):**
> "Compound components use context to share state between parent and child."

**Good (senior answer):**
> "Compound components solve the problem of leaky abstraction — when you have something like a Select or a Tabs component, the sub-components need shared state, but you don't want to expose that state in the public API. The pattern is: the parent component holds state and drops it into context, and all the sub-components read from that context without the consumer needing to wire anything up manually. The benefit over passing props everywhere is that you get an expressive, HTML-native-feeling API. The trade-off is discoverability — new engineers on the team need to learn which components are valid children. I've shipped this pattern in our design system at [company] for our `<Tabs>`, `<Select>`, and `<Accordion>` components and it scaled well across 40+ consumer teams."

**Key verbal patterns:**
- Lead with the problem the pattern solves, not its definition
- Name a specific trade-off unprompted
- Reference a production context
- Use phrases like "The tension here is...", "Where this breaks down is...", "In practice what I've seen is..."

---

## 3. Scenario-Based Q&As (8 Questions)

---

### Q1: Your dashboard has 12 widgets. State is scattered across components. Performance is degrading. How do you approach the architecture?

**Answer:**

First I'd profile before redesigning. React DevTools Profiler tells me which components are re-rendering and why. Nine times out of ten it's one of three problems: too much state too high in the tree, context that triggers mass re-renders, or missing memoization.

My refactor sequence:

1. Separate read-heavy and write-heavy state. Widget display state (collapsed/expanded) stays local. Shared business state (date range, filters that affect all widgets) goes into a Zustand store or split Contexts.

2. Each widget becomes a self-contained feature module — its own data hook, its own loading/error states. They don't share a parent loading state.

3. For the dashboard layout I'd use a compound component pattern: `<Dashboard>` owns layout state, `<Dashboard.Widget id="revenue">` registers itself. This keeps the consumer API clean.

4. Add `React.memo` on leaf widgets, `useCallback` on handlers passed down, and `useMemo` on expensive selectors.

The architectural principle is: co-locate state with the nearest component that needs it, not with the nearest common ancestor above that.

---

### Q2: Your team is building a design system. When do you choose Compound Components vs Render Props vs just exporting a custom hook?

**Answer:**

These are not competing patterns — they solve different problems.

**Compound Components** when: you have a parent-child relationship with implicit shared state, and the consumer needs to control the DOM structure. Classic examples: `<Select>`, `<Tabs>`, `<Accordion>`, `<Menu>`. The consumer can reorder children, add wrappers, swap trigger components.

**Render Props** when: you need to share stateful logic but the rendering is completely consumer-defined, AND you specifically need the consumer to be able to conditionally compose JSX. The key case where render props still beat hooks: when you need to pass the render function as a prop to a non-React context (like a virtualized list's row renderer) or when the parent component needs to coordinate multiple children that each receive different slices of the same state.

**Custom Hook** when: the logic is pure behavior with no structural opinion about the DOM. `useForm`, `usePagination`, `useInfiniteScroll`. The consumer renders whatever they want.

In practice in a design system: I default to compound components for interactive UI components, custom hooks for behavior primitives, and render props only when I need explicit render delegation (like a `DataGrid`'s cell renderer).

---

### Q3: A new engineer on your team says "just pass everything through context." What problems do you foresee?

**Answer:**

Three concrete problems in production:

**Performance**: Every consumer of a context re-renders when any value in that context changes. If you put `{ user, theme, cart, notifications }` into one context, a cart update re-renders every component reading theme. I've seen this take a 60fps dashboard to 15fps.

**Fix**: Split context by update frequency. `ThemeContext` changes once. `UserContext` changes on login. `CartContext` changes constantly. Keep them separate so only relevant subtrees re-render.

**Debugging**: Context has no devtools story. Redux has time-travel debugging. Zustand has a devtools middleware. Context is a black box. In a large codebase tracing why a value changed is painful.

**Testability**: Components that read from context require a provider in every test. This is manageable but adds boilerplate. With a custom hook you can mock the hook directly.

**The right model**: Context is excellent for low-frequency, broadly-needed state — theme, locale, auth. For high-frequency business state use a proper store. For localized UI state keep it local.

---

### Q4: Your team is arguing about folder structure — feature-based vs type-based. How do you settle it?

**Answer:**

Type-based (components/, hooks/, utils/) works fine at small scale — under 5 engineers, under 30 features. It breaks at scale because a feature change requires touching 5 different folders, which multiplies merge conflicts and makes it hard to reason about "what does this feature consist of."

Feature-based (features/billing/, features/analytics/) co-locates everything a feature needs: its components, hooks, types, tests, API calls. A new engineer can understand and own a feature without knowing the whole codebase.

The structure I've shipped at scale:

```
src/
  features/
    billing/
      components/     ← feature-private components
      hooks/
      api/
      types/
      index.ts        ← explicit public API
  shared/
    components/       ← cross-feature UI primitives
    hooks/
    utils/
  app/
    routes/
    providers/
```

The `index.ts` boundary is key — it enforces that features don't reach into each other's internals. If `analytics` needs something from `billing` it imports from `features/billing/index.ts`, not from `features/billing/components/InternalHelper.tsx`. This prevents the spaghetti that kills large codebases.

The argument I use to settle team debates: ask "if we delete this feature tomorrow, can I delete one folder?" If yes, the structure is right.

---

### Q5: Walk me through how you'd implement a micro-frontend architecture for a large enterprise platform.

**Answer:**

I'd use Webpack Module Federation, which is the production-proven approach. The setup:

**Shell app (host)** handles routing, authentication, shared layout, and declares shared dependencies — React, React-DOM, your design system. It lazy-loads remote modules at runtime.

**Remote apps** each deploy independently, expose their entry points via Module Federation config, and consume shared singletons from the host.

The critical decisions:

**Shared dependencies**: React must be a singleton — two React instances running simultaneously cause hook order errors. You declare it as a shared singleton in every webpack config. Same for your design system.

**Communication**: Don't use window globals. Define a thin event bus or use a shared Zustand store that's part of the host's shared bundle. Remotes can publish events, host and other remotes subscribe.

**Routing**: Shell owns the top-level routes. Each remote owns sub-routes within its prefix. `/billing/*` maps to the Billing MFE.

**Error isolation**: Each remote is wrapped in an Error Boundary in the shell. If Billing MFE crashes, Analytics keeps working.

**The trade-offs I'm honest about**: Module Federation adds meaningful build complexity. CI/CD pipelines need to handle versioning of remote entry URLs. Type safety across MFE boundaries requires a shared types package or schema registry. I've seen teams reach for MFE too early — for under 5 teams a monorepo with Nx or Turborepo achieves 90% of the benefits with 10% of the complexity.

---

### Q6: A modal is rendering inside a deeply nested component and has z-index issues with the parent's overflow:hidden. How do you fix this architecturally?

**Answer:**

This is the classic Portal use case. React Portals let you render a component's output into a different DOM node than its parent — typically directly under `document.body` — while keeping it in the React component tree for event bubbling and context propagation.

```tsx
// ModalPortal.tsx
import { createPortal } from 'react-dom';

const ModalPortal: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    return () => setMounted(false);
  }, []);

  if (!mounted) return null;
  return createPortal(children, document.body);
};
```

The key insight: the component stays in the React tree (so context, event bubbling work normally), but the DOM node is outside the overflow:hidden ancestor. z-index stacking contexts are resolved at the DOM level, so placing the modal under body gives you a clean stacking context.

For a design system I'd go further — a centralized `<ModalStack>` portal target at the app root, with a context-based `useModal` hook that manages open/close state and focus trapping. This prevents the z-index arms race where multiple portals fight each other.

---

### Q7: How do you handle errors in a React application at an architectural level?

**Answer:**

Error handling in React has three distinct layers, and you need all three.

**Layer 1: Error Boundaries** for synchronous render errors and lifecycle errors. Wrap feature modules, not individual components. A crash in Billing shouldn't take down Analytics.

```tsx
// Wrap at feature boundary, not at leaf component level
<ErrorBoundary fallback={<BillingError />} onError={logToSentry}>
  <BillingFeature />
</ErrorBoundary>
```

**Layer 2: Async error handling** — Error Boundaries do NOT catch errors in event handlers or async operations. Those need try/catch or promise rejection handlers. I use a custom `useAsync` hook that puts errors into state, which then flow through normal rendering.

**Layer 3: Global handler** — `window.addEventListener('unhandledrejection')` and `window.onerror` as a safety net. These feed into your observability platform (Sentry, Datadog).

**Error boundary reset**: Provide a reset mechanism so users can recover without a full page reload. Pass a `resetKeys` prop — when those values change (like route change) the boundary resets automatically.

The architectural principle: fail fast and fail small. Isolate failures to the smallest meaningful boundary.

---

### Q8: Your component is receiving 15 props, several of which are callbacks. How do you redesign the API?

**Answer:**

15 props is a code smell but the diagnosis matters. I look for three things:

**Grouping related props** into an object. If you have `firstName`, `lastName`, `email`, `avatarUrl` those should be `user: User`. If you have `onSave`, `onCancel`, `onDelete` those might be `actions: FormActions`.

**Separating concerns** — is this one component doing two jobs? A `UserForm` that also handles submission AND displays a preview is two components. Split them.

**Controlled vs uncontrolled API design**: For form components especially, offering a controlled API (caller owns state via `value`/`onChange`) and an uncontrolled default (component owns state, caller gets `defaultValue`/`onSubmit`) reduces props for simple cases.

**Component composition**: Instead of `<DataTable sortable filterable paginated exportable />` with 15 boolean flags, use composition:

```tsx
<DataTable data={rows}>
  <DataTable.Toolbar>
    <DataTable.Filter />
    <DataTable.Export />
  </DataTable.Toolbar>
  <DataTable.Body />
  <DataTable.Pagination />
</DataTable>
```

Each capability is opt-in by inclusion, not by prop. This is the Compound Component pattern applied to API design.

---

## 4. Advanced Scenario Q&As (4 Deep-Dive Questions)

---

### A1: Explain how you'd architect a React application's state management for a complex multi-step form with real-time validation, auto-save, and optimistic updates.

**Answer:**

This needs three separate state layers working together, not one monolithic form state.

**Layer 1: Form UI state** — React Hook Form handles this. Field values, touched state, validation errors, submission state. It uses uncontrolled components and ref-based updates so it doesn't trigger re-renders on every keystroke.

**Layer 2: Server sync state** — React Query (TanStack Query) handles optimistic updates, caching, background refetching. When the user submits, I call `mutate` with an `onMutate` optimistic update, roll back on error.

**Layer 3: Application state** — the saved form state that persists across navigation lives in Zustand or a server-side draft system.

The auto-save implementation uses a debounced `watch` subscription from RHF that fires a React Query mutation. The key architectural decision: auto-save runs against a `/drafts/:id` endpoint, not the main resource. This separates draft state from committed state and prevents partial saves from corrupting live data.

For multi-step: each step is a separate form with its own validation schema (Zod). A parent `useFormWizard` hook tracks current step, aggregates step data, and handles final submission. This means step validation runs independently, and navigating back to a step shows its errors without re-validating the whole form.

The subtle piece: optimistic updates need a rollback mechanism. Every optimistic mutation needs a snapshot of previous state from `queryClient.getQueryData()` stored in the `onMutate` context so `onError` can call `queryClient.setQueryData(snapshot)`.

---

### A2: How do you architect component reusability in a design system used by 30+ product teams?

**Answer:**

The hardest problem in design systems isn't building components — it's designing APIs that are flexible enough for 30 teams' use cases without becoming unmaintainable. My framework:

**Layered API design**: Primitive → Composite → Pattern.

- **Primitive**: `<Button variant="primary" size="md" />` — no opinions about layout or context
- **Composite**: `<FormField label error helperText><Input /></FormField>` — assembles primitives
- **Pattern**: `<LoginForm onSubmit />` — opinionated, escape hatch via `renderField` prop

Teams at different maturity levels use different layers. New teams use patterns. Experienced teams drop to composites. Teams with unique requirements use primitives.

**The asChild pattern** (popularized by Radix UI): instead of a `as` prop that changes the rendered element, accept `asChild` which merges your component's behavior onto whatever the consumer renders:

```tsx
<Button asChild>
  <Link to="/dashboard">Go to Dashboard</Link>
</Button>
// renders <a> with Button styles + Link behavior
```

This solves the polymorphic component typing problem cleanly.

**Versioning**: Semver for the package, but also a deprecation pipeline. When we change a component API we go: `// @deprecated, use NewProp instead` in JSDoc, add a console.warn in dev, keep old prop working for 2 major versions. Breaking changes in design systems kill adoption.

**Documentation as architecture**: Storybook isn't optional. Every component needs a "Kitchen Sink" story, an accessibility story, and stories for every prop combination that represents a real product use case. The stories ARE the API contract.

---

### A3: Walk me through how React's reconciliation algorithm affects your architectural decisions.

**Answer:**

Understanding reconciliation is what separates engineers who write code that works from engineers who write code that's fast.

React's diffing has two heuristics: different element types produce different trees (so React unmounts and remounts), and keys signal stable identity across renders.

**Architectural implications:**

**1. Component identity**: If I conditionally render `<AdminView />` vs `<UserView />` based on a role, those are different component types — React unmounts one and mounts the other, resetting all state. Sometimes that's what you want. If I want to preserve state across that switch, I need to render both and use CSS display:none on the inactive one, or lift the state out.

**2. List keys**: Using array index as key is the most common performance bug I see in production. It causes React to patch in-place (mutating DOM nodes rather than moving them) when list order changes, which breaks component state and animations. Always use a stable, unique ID from the data.

**3. Context and re-renders**: When a Context value changes reference (even if deeply equal), all consumers re-render. This is a reconciliation trigger that bypasses shouldComponentUpdate and memo. Solution: memoize context values, or use selector libraries like `use-context-selector`.

**4. The memo trap**: `React.memo` compares props shallowly. If a parent passes an inline object or function on every render, memo does nothing. You need `useMemo` and `useCallback` on the parent side. I've audited codebases where memo was applied to 40 components and provided zero benefit because no one memoized the props.

**5. Suspense and concurrent features**: With React 18 and `useTransition`, you can mark state updates as non-urgent. React will interrupt render of low-priority updates to handle high-priority ones (like user input). This changes architectural thinking: you can have expensive background renders without blocking the UI, but you need to be careful about tearing — ensure your data sources are compatible with concurrent rendering.

---

### A4: How do you architect a feature flag system in React, and what are the architectural trade-offs?

**Answer:**

Feature flags in a React app have three layers: data fetching, state management, and component API.

**Data layer**: Flags come from a service (LaunchDarkly, GrowthBook, your own). They're fetched at app init, before the main render. I use a context provider at the root that holds the flag map and exposes a `useFlag` hook.

**State management**: Flags are read-only during a session (don't change them on the fly in production without careful thought — it causes UI inconsistency). They should be cached and not cause re-renders unless explicitly refreshed.

**Component API** — the design choices:

```tsx
// Option A: Hook (most common)
const showNewDashboard = useFlag('new-dashboard-v2');

// Option B: Component wrapper (better for A/B test boundaries)
<FeatureFlag flag="new-dashboard-v2" fallback={<OldDashboard />}>
  <NewDashboard />
</FeatureFlag>

// Option C: HOC (good for route-level flags)
const ProtectedRoute = withFeatureFlag('admin-panel', FallbackComponent)(AdminPanel);
```

**Architectural trade-offs:**

Option A is simplest but scatters flag reads throughout components, making it hard to audit what's flagged. Option B is more explicit and easier to clean up (search for the component name, delete it when the flag is 100%). Option C is good for coarse-grained gating but verbose for small UI tweaks.

**The cleanup problem**: Flags accumulate. A mature system needs a way to track which flags are still active. I enforce a lint rule: every `useFlag` call must have a corresponding entry in a `flags.ts` manifest with an owner and planned removal date. This is purely architectural hygiene but it prevents the flag debt that kills codebases after 3 years.

**SSR / hydration**: Flags served from a CDN edge can differ between server render and client hydration, causing hydration mismatches. Solution: include flag values in the server response HTML as a script tag, hydrate from that on the client, then sync with the flag service asynchronously.

---

## 5. Senior Trap Questions (6 Questions)

---

### TRAP 1: "You should always lift state to the nearest common ancestor."

**The Trap:** This is standard React teaching and the interviewer says it like it's always correct. If you agree without qualification, you've walked into the trap.

**What goes wrong:** Mechanical lifting creates prop drilling — passing props through 3-5 intermediate components that don't use them. This couples unrelated components, makes refactoring painful, and pollutes intermediate component APIs.

**Correct Answer:**

> "Lifting state is the right move when components truly need to be in sync and they're close in the tree. But 'nearest common ancestor' can mean the root of your app if two distant leaf components share state. I don't lift state just because two components need it — I ask whether they need it in sync or whether they each need the same *type* of state independently. If they genuinely share state, I consider the distance: if it's 2 levels I lift; if it's 5+ levels I reach for a custom hook that encapsulates the state and can be consumed anywhere, or I use a store. The 'lift to common ancestor' rule was written before hooks. The modern equivalent is: extract to a custom hook or a store, and only lift when the parent itself needs to orchestrate the child states."

---

### TRAP 2: "HOCs are deprecated and you should always use hooks instead."

**The Trap:** Many engineers believe this because hooks replaced most HOC use cases. Agreeing makes you look like you're reciting blog posts, not thinking.

**What goes wrong:** HOCs are not deprecated. They serve specific purposes that hooks cannot.

**Correct Answer:**

> "Hooks replaced HOCs for most use cases — sharing stateful logic without wrapper components is cleaner. But HOCs are still the right tool for certain cross-cutting concerns. The cases where I still reach for HOCs: wrapping a component at the point of definition (not call site) for things like analytics tracking, auth protection on route components, or adding an error boundary declaratively. With hooks, you can't conditionally add a behavior to a component from outside its definition. A HOC lets you do `export default withAnalytics(MyComponent)` which is a clean separation — the component doesn't know about analytics. With hooks you'd have to add `useAnalytics()` inside every component. For a design system's internal implementation, HOCs also give you a clear wrapping semantic that's easier to visualize in React DevTools."

---

### TRAP 3: "Error Boundaries catch all React errors."

**The Trap:** The interviewer states this casually. Many engineers just nod.

**What goes wrong:** Error Boundaries catch a specific and limited set of errors. Agreeing shows you haven't used them deeply.

**Correct Answer:**

> "Error Boundaries catch errors that happen during rendering, in lifecycle methods, and in constructors of class components in their subtree. They do NOT catch: errors in event handlers (use try/catch there), errors in async code like setTimeout or fetch callbacks, errors in the Error Boundary component itself, and — this trips people up — errors in Server Components or SSR rendering on the server side. They also don't catch errors thrown in useEffect cleanup functions in all React versions. In production I always pair Error Boundaries with a global window.onerror and window.addEventListener('unhandledrejection') handler so nothing slips through. And since Error Boundaries are class components, I always wrap them in a functional component facade to keep the call site clean."

---

### TRAP 4: "Just use Context instead of Redux — it's the same thing with less boilerplate."

**The Trap:** This is a popular take that sounds modern and pragmatic. It's also wrong for non-trivial apps.

**What goes wrong:** Context and Redux/Zustand are different tools. Replacing one with the other blindly causes real production problems.

**Correct Answer:**

> "Context is a dependency injection mechanism, not a state management solution. The differences matter at scale. First, performance: when a Context value changes, every component consuming that context re-renders. Redux/Zustand use selector subscriptions — a component only re-renders when the specific slice it cares about changes. Second, devtools: Redux has time-travel debugging, action replay, state inspection. Context is a black box. Third, middleware: Redux's middleware pipeline gives you a centralized place for side effects, logging, and analytics. Context has none of that. Where I do use Context: low-frequency global values like theme, locale, current user. Where I use a store: high-frequency business state, anything where I need fine-grained subscriptions or debugging. The pragmatic rule: if your app has complex async flows, optimistic updates, or you have more than a handful of engineers, a store pays for itself quickly."

---

### TRAP 5: "Smaller components are always better."

**The Trap:** This sounds like good engineering advice. The interviewer often says it while reviewing a PR. Agreeing without nuance is the trap.

**What goes wrong:** Over-componentization is a real problem that causes prop drilling, cognitive overload, and naming exhaustion.

**Correct Answer:**

> "Decomposition should follow cohesion, not line count. I split a component when: it has multiple independent concerns that will change at different rates, it can be meaningfully reused elsewhere, or it's large enough that a reader can't hold it in working memory. I don't split it just because it's over 100 lines. The costs of over-componentization are real: every split requires a name (naming is hard), creates a new file boundary, and often requires lifting or threading props that didn't need to be shared. I've worked on codebases where a simple form was split into 8 components, and following the data flow meant jumping between 8 files. That's worse than one 200-line component. The question I ask: 'Does this extraction add meaning or just add indirection?' If I'm naming something `UserFormEmailSection` it's a sign I'm extracting for extraction's sake."

---

### TRAP 6: "Always make your components controlled — uncontrolled components are the old way."

**The Trap:** Controlled is the "React way" so this sounds authoritative. It's wrong as a universal rule.

**What goes wrong:** Forcing controlled APIs on every component creates unnecessary boilerplate for consumers and can hurt performance.

**Correct Answer:**

> "The right choice depends on who owns the state and why. Controlled components are correct when the parent needs to react to every state change, derive other state from the input, or implement validation that must affect other UI. But for the majority of form interactions, the parent doesn't need to know about the value until submission. Uncontrolled with a ref (or the default behavior of HTML form elements) is simpler and more performant — no re-render on every keystroke. React Hook Form's entire value proposition is using uncontrolled inputs, and it dominates because it's right. The API design pattern I follow: default to uncontrolled with `defaultValue` and `onSubmit`, and offer a controlled API via `value` and `onChange` for consumers who need it. This is exactly how HTML inputs work, and it makes your components feel natural to use."

---

## 6. Production Code Examples

### 6.1 Compound Component — Tabs

```tsx
// features/shared/components/Tabs/Tabs.tsx
import React, { createContext, useContext, useState } from 'react';

interface TabsContextValue {
  activeTab: string;
  setActiveTab: (id: string) => void;
}

const TabsContext = createContext<TabsContextValue | null>(null);

const useTabs = () => {
  const ctx = useContext(TabsContext);
  if (!ctx) throw new Error('Tabs subcomponents must be used inside <Tabs>');
  return ctx;
};

interface TabsProps {
  defaultTab: string;
  children: React.ReactNode;
}

export const Tabs = ({ defaultTab, children }: TabsProps) => {
  const [activeTab, setActiveTab] = useState(defaultTab);
  return (
    <TabsContext.Provider value={{ activeTab, setActiveTab }}>
      <div className="tabs">{children}</div>
    </TabsContext.Provider>
  );
};

Tabs.List = ({ children }: { children: React.ReactNode }) => (
  <div role="tablist" className="tabs__list">{children}</div>
);

Tabs.Tab = ({ id, children }: { id: string; children: React.ReactNode }) => {
  const { activeTab, setActiveTab } = useTabs();
  return (
    <button
      role="tab"
      aria-selected={activeTab === id}
      onClick={() => setActiveTab(id)}
    >
      {children}
    </button>
  );
};

Tabs.Panel = ({ id, children }: { id: string; children: React.ReactNode }) => {
  const { activeTab } = useTabs();
  if (activeTab !== id) return null;
  return <div role="tabpanel">{children}</div>;
};
```

---

### 6.2 Render Props — Data Fetcher

```tsx
// shared/components/DataFetcher.tsx
import { useState, useEffect } from 'react';

interface FetchState<T> {
  data: T | null;
  loading: boolean;
  error: Error | null;
}

interface DataFetcherProps<T> {
  url: string;
  children: (state: FetchState<T>) => React.ReactNode;
}

export function DataFetcher<T>({ url, children }: DataFetcherProps<T>) {
  const [state, setState] = useState<FetchState<T>>({
    data: null, loading: true, error: null,
  });

  useEffect(() => {
    let cancelled = false;
    setState({ data: null, loading: true, error: null });

    fetch(url)
      .then(res => res.json())
      .then(data => { if (!cancelled) setState({ data, loading: false, error: null }); })
      .catch(error => { if (!cancelled) setState({ data: null, loading: false, error }); });

    return () => { cancelled = true; };
  }, [url]);

  return <>{children(state)}</>;
}

// Usage — consumer fully controls rendering:
// <DataFetcher<User[]> url="/api/users">
//   {({ data, loading }) => loading ? <Spinner /> : <UserTable users={data!} />}
// </DataFetcher>
```

---

### 6.3 HOC — withAnalytics

```tsx
// shared/hocs/withAnalytics.tsx
import { useEffect, ComponentType } from 'react';
import { analytics } from '@/lib/analytics';

interface AnalyticsProps {
  pageName: string;
}

export function withAnalytics<P extends object>(
  WrappedComponent: ComponentType<P>,
  pageName: string
) {
  const displayName = WrappedComponent.displayName || WrappedComponent.name;

  const WithAnalytics = (props: Omit<P, keyof AnalyticsProps>) => {
    useEffect(() => {
      analytics.track('page_view', { pageName });
      return () => analytics.track('page_exit', { pageName });
    }, []);

    return <WrappedComponent {...(props as P)} />;
  };

  WithAnalytics.displayName = `withAnalytics(${displayName})`;
  return WithAnalytics;
}

// Usage:
// export default withAnalytics(BillingPage, 'billing');
```

---

### 6.4 Custom Hook as Architecture — usePagination

```tsx
// features/shared/hooks/usePagination.ts
import { useState, useMemo } from 'react';

interface PaginationOptions {
  totalItems: number;
  itemsPerPage?: number;
  initialPage?: number;
}

export function usePagination({
  totalItems,
  itemsPerPage = 20,
  initialPage = 1,
}: PaginationOptions) {
  const [currentPage, setCurrentPage] = useState(initialPage);
  const totalPages = Math.ceil(totalItems / itemsPerPage);

  const pagination = useMemo(() => ({
    currentPage,
    totalPages,
    itemsPerPage,
    offset: (currentPage - 1) * itemsPerPage,
    hasPrev: currentPage > 1,
    hasNext: currentPage < totalPages,
  }), [currentPage, totalPages, itemsPerPage]);

  const goTo = (page: number) =>
    setCurrentPage(Math.max(1, Math.min(page, totalPages)));

  return { ...pagination, goTo, goNext: () => goTo(currentPage + 1),
    goPrev: () => goTo(currentPage - 1) };
}
```

---

### 6.5 Error Boundary with Reset

```tsx
// shared/components/ErrorBoundary.tsx
import React, { Component, ErrorInfo } from 'react';

interface Props {
  children: React.ReactNode;
  fallback: React.ReactNode | ((error: Error, reset: () => void) => React.ReactNode);
  onError?: (error: Error, info: ErrorInfo) => void;
  resetKeys?: unknown[];
}

interface State { error: Error | null; }

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromProps(props: Props, state: State) {
    // Reset if resetKeys changed
    if (state.error && props.resetKeys) return { error: null };
    return null;
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    this.props.onError?.(error, info);
  }

  reset = () => this.setState({ error: null });

  render() {
    const { error } = this.state;
    if (error) {
      const { fallback } = this.props;
      return typeof fallback === 'function' ? fallback(error, this.reset) : fallback;
    }
    return this.props.children;
  }
}
```

---

### 6.6 Portal — Modal Base

```tsx
// shared/components/Modal/Modal.tsx
import { createPortal } from 'react-dom';
import { useEffect, useRef } from 'react';

interface ModalProps {
  open: boolean;
  onClose: () => void;
  children: React.ReactNode;
}

export const Modal = ({ open, onClose, children }: ModalProps) => {
  const previousFocus = useRef<Element | null>(null);

  useEffect(() => {
    if (open) {
      previousFocus.current = document.activeElement;
      return () => { (previousFocus.current as HTMLElement)?.focus(); };
    }
  }, [open]);

  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    if (open) document.addEventListener('keydown', handleEsc);
    return () => document.removeEventListener('keydown', handleEsc);
  }, [open, onClose]);

  if (!open) return null;

  return createPortal(
    <div className="modal-overlay" onClick={onClose} role="dialog" aria-modal>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        {children}
      </div>
    </div>,
    document.body
  );
};
```

---

### 6.7 Module Federation Config

```js
// webpack.config.js (Shell/Host)
const { ModuleFederationPlugin } = require('webpack').container;

module.exports = {
  plugins: [
    new ModuleFederationPlugin({
      name: 'shell',
      remotes: {
        billing: 'billing@https://billing.internal.com/remoteEntry.js',
        analytics: 'analytics@https://analytics.internal.com/remoteEntry.js',
      },
      shared: {
        react: { singleton: true, requiredVersion: '^18.0.0' },
        'react-dom': { singleton: true, requiredVersion: '^18.0.0' },
        '@company/design-system': { singleton: true },
      },
    }),
  ],
};
```

---

### 6.8 Controlled + Uncontrolled Component API

```tsx
// shared/components/Toggle/Toggle.tsx
import { useState } from 'react';

interface ToggleProps {
  // Controlled API
  checked?: boolean;
  onChange?: (checked: boolean) => void;
  // Uncontrolled API
  defaultChecked?: boolean;
  // Common
  label: string;
  disabled?: boolean;
}

export const Toggle = ({ checked, onChange, defaultChecked = false, label, disabled }: ToggleProps) => {
  const isControlled = checked !== undefined;
  const [internalChecked, setInternalChecked] = useState(defaultChecked);
  const value = isControlled ? checked : internalChecked;

  const handleChange = () => {
    const next = !value;
    if (!isControlled) setInternalChecked(next);
    onChange?.(next);
  };

  return (
    <label>
      <input type="checkbox" checked={value} onChange={handleChange} disabled={disabled} />
      {label}
    </label>
  );
};
```

---

## 7. Interview Cheat Sheet

```
╔══════════════════════════════════════════════════════════════════════╗
║           REACT ARCHITECTURE — SENIOR ENGINEER CHEAT SHEET          ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  PATTERNS — when to use which                                        ║
║  ─────────────────────────────────────────────────────────────────   ║
║  Compound Components   → implicit shared state, flexible DOM         ║
║                          structure (Select, Tabs, Accordion)         ║
║                                                                      ║
║  Render Props          → caller controls rendering, delegate         ║
║                          to row renderers, cell renderers           ║
║                                                                      ║
║  HOCs                  → cross-cutting concerns at definition        ║
║                          site (analytics, auth guard, logging)       ║
║                                                                      ║
║  Custom Hooks          → reusable stateful behavior, no DOM         ║
║                          opinion (useForm, usePagination)           ║
║                                                                      ║
║  Container/Presentational → testability, Storybook isolation        ║
║                                                                      ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  STATE DECISIONS                                                     ║
║  ─────────────────────────────────────────────────────────────────   ║
║  Local useState        → UI-only state, no sharing needed           ║
║  Lift state up         → 1-2 levels, truly shared                   ║
║  Custom hook           → logic reuse, or deep sharing needed        ║
║  Context               → low-freq global: theme, locale, auth       ║
║  Store (Zustand/Redux) → high-freq business state, devtools,        ║
║                          subscriptions, async flows                  ║
║                                                                      ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  ERROR BOUNDARIES — what they catch vs don't                        ║
║  ─────────────────────────────────────────────────────────────────   ║
║  CATCH:   render errors, lifecycle errors, constructor errors       ║
║  MISS:    event handlers, async code, SSR, the boundary itself      ║
║  ALWAYS:  pair with window.onerror + unhandledrejection             ║
║  PATTERN: wrap feature boundaries, not leaf components              ║
║                                                                      ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  PORTALS — when to use                                              ║
║  ─────────────────────────────────────────────────────────────────   ║
║  Use when: overflow:hidden, z-index stacking, DOM order matters     ║
║  React tree intact → context, events work normally                  ║
║  DOM node moves → z-index resolved from body, no stacking issues    ║
║                                                                      ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  MICRO-FRONTENDS — decision criteria                                ║
║  ─────────────────────────────────────────────────────────────────   ║
║  Use MFE when: 3+ independent teams, independent deploy needed      ║
║  Don't use: < 3 teams (monorepo + Nx is 90% benefit, 10% cost)     ║
║  Key: React singleton in shared, event bus for communication        ║
║  Key: Error Boundary per remote in shell                            ║
║                                                                      ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  TRAP ANSWERS — one-liners                                          ║
║  ─────────────────────────────────────────────────────────────────   ║
║  "Always lift state"      → No: extract to hook/store if deep      ║
║  "HOCs are deprecated"    → No: still valid for cross-cutting       ║
║  "EB catches all errors"  → No: misses async + event handlers       ║
║  "Context = Redux"        → No: no selectors, no devtools           ║
║  "Smaller = always better"→ No: over-split = prop drilling          ║
║  "Always controlled"      → No: RHF proves uncontrolled scales      ║
║                                                                      ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  FOLDER STRUCTURE RULE                                              ║
║  ─────────────────────────────────────────────────────────────────   ║
║  Feature-based at scale: can I delete one folder to delete          ║
║  one feature? If no, restructure.                                   ║
║  Public API: features/X/index.ts — never reach into internals       ║
║                                                                      ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  COMPONENT API DESIGN CHECKLIST                                     ║
║  ─────────────────────────────────────────────────────────────────   ║
║  □ Controlled + uncontrolled variants for form components           ║
║  □ forwardRef if consumer needs DOM node access                     ║
║  □ Polymorphic: asChild pattern over "as" prop                      ║
║  □ Composition over configuration (Compound > boolean flags)        ║
║  □ DisplayName set for DevTools                                     ║
║  □ Props grouped by concern, not listed individually                ║
║                                                                      ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  RECONCILIATION — key facts for interviews                          ║
║  ─────────────────────────────────────────────────────────────────   ║
║  Different element type → full unmount/remount (state reset)        ║
║  Index as key → bugs when list order changes                        ║
║  Inline object prop → memo() provides zero benefit                  ║
║  Context value change → ALL consumers re-render (ref equality)      ║
║  useTransition → marks update as non-urgent (concurrent mode)       ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

## Quick Reference: Pattern Decision Tree

```
Need to share logic between components?
│
├─ Logic is pure behavior, no DOM? ────────────────→ Custom Hook
│
├─ Logic needs to wrap a component at definition?  → HOC
│
└─ Logic affects what gets rendered?
   │
   ├─ Consumer controls rendering + JSX? ─────────→ Render Props
   │
   └─ Parent-child relationship, shared state?
      │
      ├─ Consumer controls child composition? ────→ Compound Component
      │
      └─ Fixed structure, simple API? ────────────→ Props + forwardRef


Need to manage state?
│
├─ Only one component needs it? ─────────────────→ useState / useReducer
│
├─ A few nearby components? ─────────────────────→ Lift state up
│
├─ Deep tree, infrequent updates? ───────────────→ Context
│
└─ Frequent updates, need devtools, many consumers? → Zustand / Redux
```

---

*File created: 2026-08-22 | Level: 15-YOE Senior / Staff Engineer | Topics: 12 | Questions: 18*
