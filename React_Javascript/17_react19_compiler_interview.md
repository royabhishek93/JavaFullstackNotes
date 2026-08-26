# React 19 & React Compiler — 15-YOE Architect Interview Prep

---

## 1. BIG PICTURE ASCII DIAGRAMS

### React 19 Feature Map

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          REACT 19 FEATURE MAP                               │
├─────────────────────────┬───────────────────────────────────────────────────┤
│   COMPILER / PERF       │   NEW HOOKS & APIS                                │
│  ─────────────────────  │  ──────────────────────────────────────────────   │
│  React Compiler         │  use()            — read Promise/Context in render │
│  (auto-memoization)     │  useFormStatus()  — parent form pending state      │
│  Rules of React         │  useOptimistic()  — optimistic UI w/ auto-rollback │
│  "use no memo"          │  useActionState() — action state + pending         │
│  opt-out directive      │                                                    │
├─────────────────────────┼───────────────────────────────────────────────────┤
│   ACTIONS               │   SERVER INTEGRATION                               │
│  ─────────────────────  │  ──────────────────────────────────────────────   │
│  Async transitions      │  Server Actions  — fn called directly from client  │
│  Auto pending state     │  Server Components (stable)                        │
│  startTransition(async) │  Progressive enhancement via <form action={fn}>    │
│  Error boundary link    │                                                    │
├─────────────────────────┼───────────────────────────────────────────────────┤
│   DX IMPROVEMENTS       │   BREAKING / DEPRECATIONS                          │
│  ─────────────────────  │  ──────────────────────────────────────────────   │
│  ref as regular prop    │  forwardRef → deprecated                           │
│  <Context> shorthand    │  ReactDOM.render → removed                         │
│  Hydration diff errors  │  Legacy Context API → removed                      │
│  Document metadata      │  string refs → removed                             │
│  Asset preload APIs     │  defaultProps on fn comps → removed                │
└─────────────────────────┴───────────────────────────────────────────────────┘
```

### React Compiler Transformation Flow

```
  YOUR SOURCE CODE
       │
       ▼
┌──────────────────┐
│  Babel Plugin /  │  ← babel-plugin-react-compiler
│  Vite Plugin     │    or @next/react-compiler (Next.js 15+)
└──────────┬───────┘
           │  Parses component/hook AST
           ▼
┌──────────────────────────────────────────────────────────┐
│              RULES OF REACT ANALYSIS                     │
│                                                          │
│  ✓ Pure functions (no side effects in render)            │
│  ✓ No mutation of props/state/context                    │
│  ✓ Stable hook call order                                │
│  ✗ Violation? → SKIP this component (safe fallback)      │
└──────────────────────────┬───────────────────────────────┘
                           │  Passes rules check
                           ▼
┌──────────────────────────────────────────────────────────┐
│           DEPENDENCY TRACKING (per expression)           │
│                                                          │
│  Compiler identifies every value and its dependencies    │
│  Generates fine-grained memo slots                       │
│  Replaces useMemo / useCallback calls automatically      │
└──────────────────────────┬───────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────┐
│              EMITTED OUTPUT                              │
│                                                          │
│  Component wrapped with internal $memo$ runtime calls    │
│  Only changed subtrees re-compute                        │
│  Developer sees normal JSX — no visible wrappers         │
└──────────────────────────────────────────────────────────┘

OPT-OUT PATH:
  "use no memo"  →  Compiler skips entire component/hook
  React.memo()   →  Still works; compiler won't double-wrap
```

### use() Hook — Suspense Integration

```
  Parent Component
       │
       ├── <Suspense fallback={<Spinner/>}>
       │         │
       │         └── <ChildComponent promise={dataPromise} />
       │                    │
       │                    │  const data = use(promise)
       │                    │
       │                    │  Promise pending?  → throws Promise  → Suspense catches
       │                    │  Promise rejected? → throws Error   → ErrorBoundary catches
       │                    │  Promise resolved? → returns value  → renders normally
       │
       └── <ErrorBoundary fallback={<Error/>}>
                  (wraps Suspense for error handling)
```

---

## 2. CONVERSATIONAL INTERVIEW SCRIPT (15-YOE ARCHITECT VOICE)

**Interviewer**: Walk me through the biggest architectural changes in React 19 and how you'd approach adopting them in a large existing codebase.

**You**: React 19 ships three categories of change that matter at the architecture level. First, the React Compiler — it's the biggest performance story. It statically analyzes your components and automatically inserts memoization where the dependency graph warrants it. In a large codebase, this can be a net win because most engineers don't write perfect useMemo/useCallback discipline. The catch is it enforces "Rules of React" strictly — any component violating them gets skipped by the compiler, so you need to audit and fix violations before you capture the gains.

Second is the Server/Client model maturing — Server Actions are now stable. You can mark a function with `"use server"` and call it directly from a Client Component. It looks like a function call but goes over the network. This collapses the traditional "write an API route, write a fetch call, write error handling" pattern into one function definition. The security surface area is different — you have to think about what data the server function exposes, almost like a public API endpoint but with implicit auth context from the request.

Third is ergonomic improvements — ref as a regular prop removes the forwardRef ceremony that tripped up half my teams at some point, the `use()` hook unifies reading promises and context, and document metadata can be colocated with the component that owns the intent. In a micro-frontend or large SPA, scattering `<title>` management into Helmet configs is a maintenance headache. React 19 deduplicates these natively.

For rollout in a brownfield codebase, I'd do it in phases: first upgrade to React 18.3 (bridge release that warns on deprecated patterns), fix all warnings, then cut to React 19. The Compiler comes separately — enable it per-directory with the `includesPaths` config until you've audited the codebase.

---

**Interviewer**: How does the `use()` hook differ from what we had before?

**You**: The name is deceptively simple but it's semantically distinct from every hook we had. Before React 19, if you wanted async data in a component you had three options: useEffect + local state (side-effect pattern), a custom hook that wraps those, or a data-fetching library like React Query that already integrated with Suspense under the hood.

`use()` is a first-class primitive that reads a Promise synchronously in the render phase. It integrates with Suspense the same way a lazy-loaded component does — the component suspends while the promise is pending. When the promise resolves, React retries the render.

What's unique is that `use()` can be called conditionally and inside loops — it's not a hook in the traditional sense; it doesn't follow hook rules about call order. That's intentional — it's a read operator, not a state manager.

It also reads Context. So `const user = use(UserContext)` works anywhere in the component tree, even inside an if-block. That's a meaningful DX improvement for context that's consumed conditionally.

The error case is also clean — if the promise rejects, it throws and the nearest ErrorBoundary catches it. So the Suspense + ErrorBoundary pair is the standard scaffold for `use()`.

---

## 3. SCENARIO Q&As — PRODUCTION CONTEXT

### Scenario 1: Migrating a Legacy Codebase to React Compiler

**Q**: Your team has a 300-component React 18 app. You want to adopt the React Compiler. What's your rollout plan?

**A**: I'd never enable it globally day one. My phased plan:

1. **Audit phase** — Run `eslint-plugin-react-compiler` across the codebase. It reports every Rules of React violation without the compiler being enabled. Get that to zero violations in CI before touching the compiler config.

2. **Canary phase** — Enable the compiler only for `src/components/ui/` (leaf-level presentational components). These are most likely to be pure and gain the most from memoization. Monitor render counts in Profiler sessions.

3. **Expand incrementally** — Move up the tree, directory by directory. Use `includesPaths` in the compiler config to gate it.

4. **Handle opt-outs** — Any component that legitimately needs non-pure behavior (imperatively mutating a ref, DOM measurements) gets `"use no memo"` at the top. Document why.

5. **Delete dead useMemo/useCallback** — After the compiler is widely enabled, run a codemod to remove manually written memoization the compiler now handles. This reduces code noise but requires care — the compiler's memoization is not identical to manual memoization; double-check with profiler.

Risk: the compiler is still evolving. Pin the exact compiler version in CI and test with Playwright on every bump.

---

### Scenario 2: useOptimistic in a Chat Application

**Q**: You're building a real-time chat UI. Messages are sent via a Server Action. How do you use `useOptimistic` to make it feel instant?

**A**: Classic optimistic update pattern. The key steps:

```typescript
// ChatInput.tsx
"use client";
import { useOptimistic, useTransition } from "react";
import { sendMessageAction } from "./actions";

type Message = { id: string; text: string; status: "sent" | "pending" };

interface Props {
  messages: Message[];
  conversationId: string;
}

export function ChatInput({ messages, conversationId }: Props) {
  const [optimisticMessages, addOptimistic] = useOptimistic(
    messages,
    (current: Message[], newText: string) => [
      ...current,
      { id: crypto.randomUUID(), text: newText, status: "pending" as const },
    ]
  );

  const [, startTransition] = useTransition();

  function handleSubmit(formData: FormData) {
    const text = formData.get("text") as string;
    startTransition(async () => {
      addOptimistic(text);
      await sendMessageAction(conversationId, text);
    });
  }

  return (
    <>
      <MessageList messages={optimisticMessages} />
      <form action={handleSubmit}>
        <input name="text" autoComplete="off" />
        <button type="submit">Send</button>
      </form>
    </>
  );
}
```

The optimistic message shows immediately with `status: "pending"`. If `sendMessageAction` throws, React automatically reverts `optimisticMessages` back to the committed `messages` prop. The real message coming back from the server (via revalidation or websocket) replaces the optimistic entry.

Critical point: `useOptimistic` is scoped to the transition. Outside a `startTransition`, the optimistic state is not active. Always wrap server action calls in `startTransition` to get the optimistic behavior.

---

### Scenario 3: Server Actions Security Model

**Q**: Your senior engineer says "Server Actions are just API routes with better DX." How do you respond?

**A**: Partially true but the differences matter operationally. A Next.js API route (`app/api/messages/route.ts`) is an explicit HTTP endpoint with a URL. You control authentication middleware, you see it in network logs, it's easily consumable by mobile clients or third parties.

A Server Action is a function exposed as a POST endpoint under the hood, but the URL is opaque (a hash). React serializes arguments, sends them over `multipart/form-data` or JSON, and deserializes on the server. Callers don't write fetch — they call the function. This has real implications:

- **Auth**: You still have to explicitly check auth inside the Server Action. The "implicit auth context" just means headers/cookies are available via `cookies()` or `headers()` — they don't automatically gate access. Many engineers assume the compiler handles this, which is dangerous.
- **Input validation**: Server Actions receive serialized data from the client. Use Zod or equivalent inside every action, same discipline as an API route.
- **Rate limiting**: Harder to add middleware since the URL is opaque. Next.js middleware runs before any route, so you can still do it, but it's less obvious.
- **Logging/observability**: Requires explicit instrumentation since there's no named route to correlate.

I treat Server Actions as internal RPC calls, not public APIs. If a mobile app or third party needs the data, I still write a proper API route.

---

### Scenario 4: useFormStatus for Complex Form UX

**Q**: You have a checkout form with multiple submit buttons (Save Draft, Submit Order). Each button should show a loading state during its respective action. How do you structure this with `useFormStatus`?

**A**: `useFormStatus` reads the pending state of the nearest parent `<form>`. The key insight is that it must live in a child component, not in the component that renders the form itself.

```typescript
// SubmitButton.tsx
"use client";
import { useFormStatus } from "react-dom";

interface Props {
  label: string;
  pendingLabel: string;
}

function SubmitButton({ label, pendingLabel }: Props) {
  const { pending } = useFormStatus();
  return (
    <button type="submit" disabled={pending}>
      {pending ? pendingLabel : label}
    </button>
  );
}

// CheckoutForm.tsx
export function CheckoutForm() {
  return (
    <form action={submitOrderAction}>
      {/* form fields */}
      <SubmitButton label="Submit Order" pendingLabel="Placing order..." />
    </form>
  );
}
```

For the multi-button case with different actions, each button triggers the same form's pending state (since a form can only have one active submission), so you'd split into two separate `<form>` elements — one for Save Draft, one for Submit Order. Each gets its own `SubmitButton` child that reads its own form's pending state. No prop drilling for loading state anywhere.

This pattern eliminates the `isSubmitting` boolean that used to bubble through 3-4 component layers.

---

### Scenario 5: Document Metadata — Replacing React Helmet

**Q**: Your team uses `react-helmet-async` for meta tags. React 19 adds native support. How do you migrate and what are the gotchas?

**A**: React 19 hoists `<title>`, `<meta>`, `<link>`, and `<script>` rendered anywhere in the tree to `<head>`. It deduplicates by tag type and attribute keys — for example, duplicate `<title>` tags are resolved with the last render winning.

Migration is straightforward for most cases: delete `react-helmet-async`, replace `<Helmet>` wrappers with inline JSX. For a product detail page:

```typescript
// ProductPage.tsx
export function ProductPage({ product }: { product: Product }) {
  return (
    <>
      <title>{product.name} — Acme Store</title>
      <meta name="description" content={product.description} />
      <link rel="canonical" href={`https://acme.com/products/${product.slug}`}`} />
      <ProductDetail product={product} />
    </>
  );
}
```

Gotchas to watch:

- **Precedence on `<link>`**: Use the `precedence` prop to control stylesheet load order. Without it, React doesn't guarantee order between dynamically rendered stylesheets.
- **SSR**: On the server, React collects and emits these into the HTML `<head>`. Verify your streaming SSR setup doesn't need special wiring — Next.js App Router handles it automatically, but custom Express+RSC setups may not.
- **Animation of `<title>`**: The deduplication "last render wins" means if two routes render simultaneously during a transition, the title might flicker. Wrap transitions carefully.
- **Open Graph tags**: Still verify these with a crawler because crawlers read the raw HTML, not the React-managed DOM.

---

### Scenario 6: Hydration Error Improvements

**Q**: React 19 claims better hydration errors. Describe what changed and how it affects your debugging workflow.

**A**: In React 18 and earlier, a hydration mismatch produced a generic error like "Text content did not match. Server: 'X' Client: 'Y'" with a stack trace pointing to the internal reconciler, not your code. Diagnosing required disabling SSR locally or sprinkling console.logs around suspicion points.

React 19 provides a diff format in the error output — it shows the server-rendered HTML alongside what the client expected to render, line by line, with the differing node highlighted. It also points to the component in your source that caused the mismatch.

In practice this cuts hydration debugging from 30-minute hunts to 5-minute fixes. Common causes I now see surfaced clearly:

- `new Date()` called during SSR versus CSR (timezone difference)
- `typeof window !== "undefined"` checks that render different UI on server vs client
- User-agent-conditional code
- Browser extensions that inject DOM nodes (this one shows in the diff clearly as an extra node the client didn't expect)

My workflow change: I removed our custom "disable SSR in dev" escape hatch because the errors are now informative enough to fix properly rather than skip.

---

### Scenario 7: Actions Pattern — Async Transitions

**Q**: What are "Actions" in React 19 and how do they relate to transitions?

**A**: React 19 formalizes the pattern of passing async functions to `startTransition`. Before React 19, `startTransition` only accepted synchronous updaters — async was a common mistake that silently didn't work as expected.

Now `startTransition(async () => { ... })` is supported. During the async work, the transition is in "pending" state. `isPending` from `useTransition` reflects this. React batches state updates that happen inside the transition when the async work completes.

`useActionState` wraps this into a higher-level hook that gives you the action result, pending state, and a dispatch function:

```typescript
import { useActionState } from "react";

async function loginAction(
  prevState: { error: string | null },
  formData: FormData
): Promise<{ error: string | null }> {
  const result = await authenticate(formData);
  if (!result.ok) return { error: result.message };
  return { error: null };
}

function LoginForm() {
  const [state, dispatch, isPending] = useActionState(loginAction, { error: null });
  return (
    <form action={dispatch}>
      <input name="email" type="email" />
      <input name="password" type="password" />
      {state.error && <p role="alert">{state.error}</p>}
      <button disabled={isPending}>{isPending ? "Logging in..." : "Log in"}</button>
    </form>
  );
}
```

The form's `action` prop accepts `dispatch` directly — this enables progressive enhancement. Without JavaScript, the form submits as a standard POST. With JavaScript, React intercepts and runs the action client-side (or routes to a Server Action). This is a huge win for accessibility and resilience.

---

### Scenario 8: ref as Prop — Eliminating forwardRef

**Q**: Walk me through the ref prop change in React 19 and where it matters architecturally.

**A**: `forwardRef` was a wrapper function that existed because `ref` was special — React intercepted it before props reached the component. In React 19, `ref` is treated as a regular prop. You access it the same way as `className` or `onClick`.

```typescript
// React 18 — required forwardRef
const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ label, ...props }, ref) => (
    <label>
      {label}
      <input ref={ref} {...props} />
    </label>
  )
);

// React 19 — ref is just a prop
function Input({ label, ref, ...props }: InputProps & { ref?: React.Ref<HTMLInputElement> }) {
  return (
    <label>
      {label}
      <input ref={ref} {...props} />
    </label>
  );
}
```

Architecturally, this matters for component libraries. We maintained a set of ~60 forwardRef wrappers for our design system's primitive components. That's 60 files with boilerplate wrapping that obscures the component's intent when you read it. React 19 lets us unwrap all of them, reducing the abstraction layer between the component's API and its implementation.

Migration: `forwardRef` still works in React 19 (deprecated, not removed). You can codemods the wrapper away incrementally. The one gotcha is TypeScript — you need to add `ref` to your Props interface explicitly, including the right `React.Ref<T>` type, or TypeScript won't accept it. The React 19 types package updates this, but third-party component libraries lag.

---

## 4. ADVANCED SCENARIO Q&As

### Advanced Scenario 1: React Compiler Blind Spots

**Q**: In what cases does the React Compiler fail to auto-memoize and you still need manual useMemo/useCallback?

**A**: The compiler's static analysis has limits. Cases where manual memoization remains necessary:

**Dynamic object keys**: When you compute an object whose shape is determined at runtime, the compiler can't prove the reference is stable:

```typescript
// Compiler cannot safely memoize this — key set is dynamic
function buildConfig(features: string[]) {
  return features.reduce((acc, f) => ({ ...acc, [f]: true }), {});
}
```

**Cross-component memoization boundaries**: The compiler operates per-component. If a value created in ParentComponent is passed through multiple children and needs reference equality at a deeply nested consumer, the compiler memoizes within each component independently. The prop-drilling path can still cause re-renders if the parent's memoized value updates for other reasons. React.memo() on the consumer is still the right tool here.

**Third-party library interop**: Libraries that check reference equality externally (react-spring, framer-motion, some Zustand selectors) may not respond correctly to compiler-generated memoization because the compiler's internal runtime is not identical to `useMemo`. You may need to annotate with `"use no memo"` and manage memoization manually for those components.

**Async generators and complex closures**: The compiler's dependency tracking can struggle with closures over mutable refs inside complex async code patterns.

Rule of thumb at architect level: enable the compiler, delete obvious manual memoization, then run profiler sessions and add back targeted `useMemo` only where the profiler shows measured regression.

---

### Advanced Scenario 2: Concurrent Features + Server Actions Error Handling

**Q**: How do you design error handling for Server Actions in a production app with Server Components, Server Actions, and Suspense all in play?

**A**: This requires three distinct error handling layers that are easy to conflate:

**Layer 1 — Server Action validation errors** (expected): Return an error object from the action, don't throw. Use `useActionState` to surface the error in the component. These are user-correctable errors (validation, business logic).

**Layer 2 — Server Action unexpected errors** (thrown): Wrap the action body in try/catch, log to your observability pipeline (Datadog/Sentry), and return a generic user-facing message. Never expose stack traces or internal messages to the client.

**Layer 3 — RSC rendering errors**: These propagate as ErrorBoundary catches. Granular ErrorBoundaries at route segment level (Next.js `error.tsx`) prevent full-page failures.

The architecture I use:

```typescript
// actions/orders.ts
"use server";

import { z } from "zod";
import { logger } from "@/lib/logger";

const CreateOrderSchema = z.object({ /* ... */ });

type ActionResult =
  | { ok: true; orderId: string }
  | { ok: false; error: string; fieldErrors?: Record<string, string[]> };

export async function createOrderAction(
  _prev: ActionResult | null,
  formData: FormData
): Promise<ActionResult> {
  const parsed = CreateOrderSchema.safeParse(Object.fromEntries(formData));
  if (!parsed.success) {
    return {
      ok: false,
      error: "Validation failed",
      fieldErrors: parsed.error.flatten().fieldErrors,
    };
  }
  try {
    const order = await db.orders.create(parsed.data);
    return { ok: true, orderId: order.id };
  } catch (err) {
    logger.error("createOrder failed", { err });
    return { ok: false, error: "Unable to create order. Please try again." };
  }
}
```

The calling component uses `useActionState`, reads `state.fieldErrors` for inline validation messages and `state.error` for a top-level banner. Never re-throws to an ErrorBoundary from a Server Action — use the return-value pattern for user-facing errors.

---

### Advanced Scenario 3: useOptimistic with Concurrent Renders

**Q**: What happens to optimistic state when multiple optimistic updates are in flight simultaneously?

**A**: Each call to `addOptimistic` inside a `startTransition` queues an additional optimistic update. React merges them using the reducer function in sequence. So if two messages are sent quickly, `optimisticMessages` will show both pending messages on top of the committed state.

The tricky case is interleaved resolution — message 2 resolves before message 1. Since `useOptimistic` reverts on error and re-applies on new committed state, partial resolution can produce UI flicker if you're not careful.

My production pattern for chat is to use a deduplication key and track pending IDs separately:

```typescript
const [pendingIds, setPendingIds] = useState<Set<string>>(new Set());
const [optimisticMessages, addOptimistic] = useOptimistic(
  messages,
  (current, { id, text }: { id: string; text: string }) => [
    ...current,
    { id, text, status: "pending" as const },
  ]
);
```

When the server action returns the confirmed message (with the same client-generated ID), your revalidation path replaces the optimistic entry naturally. The `pendingIds` set lets you visually differentiate "still pending" from "confirmed by server."

For collaborative editing, `useOptimistic` is the wrong primitive — it's purely local optimistic state with auto-revert, not conflict resolution. For collaborative scenarios you need OT or CRDT (e.g., Yjs) operating at the data layer, with React only rendering what the CRDT materializes.

---

### Advanced Scenario 4: React Compiler + Design System Migration

**Q**: Your team maintains a shared design system used by 8 product teams. How do you roll out the React Compiler for it without breaking consumers?

**A**: A shared library has a different risk profile than an app — breaking the library breaks 8 teams. My approach:

**Phase 1 — Compiler as dev dependency only**: The design system package runs the compiler as part of its build (emitting optimized output). Consumers get already-compiled components without needing to run the compiler themselves. This lets you validate compiler correctness in the library before asking teams to enable it in their apps.

**Phase 2 — Test harness expansion**: Add a "compiler exhaustive" test suite — render every component with every variant and compare snapshots pre/post compiler. React Testing Library tests pass through because the API surface doesn't change. But visual regression tests with Chromatic/Percy catch layout changes from timing differences.

**Phase 3 — Explicit opt-outs in package metadata**: Export a list of components that have `"use no memo"` and why. This communicates to consumers where manual memoization is still needed.

**Phase 4 — Consumer opt-in**: Once the library's compiler output is stable for 2+ release cycles, recommend that product teams enable the compiler in their apps. Provide migration docs specific to your design system (which components accept refs, which have imperative handles that interact differently with compiler memoization).

The key principle is that the compiler must be invisible to consumers — same prop API, same behavior, just fewer re-renders.

---

## 5. SENIOR TRAP QUESTIONS

### Trap 1: "React Compiler Eliminates useMemo/useCallback Entirely"

**Trap phrasing**: "Now that we have the React Compiler, we can delete all useMemo and useCallback from our codebase and never write them again."

**Why it's a trap**: The compiler handles the common case — stable values derived from props/state in pure components. But it has documented blind spots: dynamic object keys, cross-component memoization, library interop expecting specific reference stability, and components that legitimately opt out with `"use no memo"`. Blindly deleting all manual memoization before profiling will introduce performance regressions in those areas.

**Correct answer**: Enable the compiler, let it handle what it can, then measure with the React Profiler. Remove useMemo/useCallback only where the profiler confirms the compiler has taken over that job. Keep manual memoization where the profiler shows the compiler is not covering it (or where the component is opted out). This is a "trust but verify" rollout, not a mass deletion.

---

### Trap 2: "use() Is Like useEffect for Promises"

**Trap phrasing**: "use() is basically useEffect but cleaner — I can use it to trigger async operations, fetch data, subscribe to streams..."

**Why it's a trap**: `useEffect` runs after render as a side effect. `use()` runs during render and suspends the component tree while waiting. They are categorically different. `use()` is a read primitive — it reads the resolved value of a Promise that someone else started. It does not initiate fetches. If you call `use(fetch('/api/data'))` inside a component, you create a new fetch on every render because `fetch()` is called in the render phase. You need to lift the Promise creation outside the component (at the route level, in a context, via a data library).

`use()` also has no cleanup mechanism — you cannot cancel a subscription with it. For subscriptions, useEffect is still the correct tool.

**Correct answer**: `use(promise)` is a synchronous read of an already-in-flight promise. Create promises outside the render cycle; pass them in as props or read them from a cache. Think of it as "deref a promise in JSX," not "replace useEffect."

---

### Trap 3: "Server Actions Are Just Better API Routes"

**Trap phrasing**: "We can replace all our Express API routes with Server Actions — same result, less code."

**Why it's a trap**: Server Actions are tightly coupled to the React rendering model. They're called as functions from components, not as fetch() calls from arbitrary clients. Their URLs are opaque hashes, not stable named endpoints. This means mobile apps, CLI tools, third-party integrations, and webhooks cannot call them directly. Rate limiting, versioning, and API documentation tooling (OpenAPI, etc.) don't apply to Server Actions without extra work.

Additionally, Server Actions run in the context of the Next.js/server runtime — they're not portable to standalone express services, they don't participate in API gateways the same way, and their serialization format is Next.js-specific.

**Correct answer**: Server Actions are the right tool for form submissions and mutations initiated from React components in the same Next.js app. For anything that needs to be called by external clients, maintain proper API routes with explicit contracts. Use Server Actions to simplify client-server interaction within the app, not as a universal API replacement.

---

### Trap 4: "forwardRef Is Still Required in React 19"

**Trap phrasing**: "We need forwardRef to pass refs to custom components — it's a fundamental React requirement."

**Why it's a trap**: As of React 19, `ref` is a regular prop. `forwardRef` is deprecated (not removed — it still works for backward compatibility). New components should accept `ref` in their props interface directly without any wrapper. The old behavior where React stripped `ref` from props and handled it specially no longer applies.

**Correct answer**: In React 19, write `function MyInput({ ref, ...props }: Props) { ... }` and it works. `forwardRef` is a compatibility shim for libraries that haven't updated. New code should not use it. When migrating existing components, unwrap the `forwardRef` call and add `ref` to the props type explicitly.

---

### Trap 5: "useOptimistic Handles All Conflict Resolution"

**Trap phrasing**: "We're building a collaborative doc editor. I'll use useOptimistic — it handles the case where two users edit the same field at the same time."

**Why it's a trap**: `useOptimistic` is a single-user, single-client optimistic update pattern. It shows an assumed-successful state immediately and reverts if the server action fails. It has no mechanism for merging concurrent edits from multiple users. If User A and User B both edit the same paragraph, `useOptimistic` won't detect the conflict — it'll just revert if the server rejects one, which is a jarring UX for collaborative editing.

Collaborative conflict resolution requires operational transformation (OT) or conflict-free replicated data types (CRDTs) like Yjs or Automerge at the data layer. React's job in that scenario is just to render what the CRDT materializes — no optimistic hooks needed, because the CRDT itself handles merge and convergence.

**Correct answer**: `useOptimistic` is for single-user interaction patterns where you're confident the server will succeed (or you're okay with a full revert on failure). For collaborative editing, use a purpose-built CRDT library. Don't conflate "optimistic UI" with "conflict resolution."

---

### Trap 6: "Context as Provider Shorthand is Just Syntax Sugar"

**Trap phrasing**: "The `<MyContext>` shorthand for `<MyContext.Provider>` is purely cosmetic, right? No behavioral difference?"

**Why it's a trap**: Mostly true but with one behavioral nuance: React 19 also changes how context consumers work with the `use()` hook. With the old `useContext`, you called it unconditionally at the top of the component. With `use(MyContext)`, you can call it conditionally — inside an if-block, inside a loop. This is a genuine behavioral change enabled by the new context read model, not just a naming shorthand. The shorthand and the `use()` context API together represent a cohesive redesign of the context developer experience.

Additionally, if you're using TypeScript, the generic type inference is slightly different — `<MyContext value={...}>` requires the value to match the context type directly, and some edge cases around `null` default values surface differently in type checking.

**Correct answer**: The `<Context>` shorthand is mostly ergonomic but it's part of a broader context redesign. The more significant change is `use(Context)` enabling conditional context consumption. Don't dismiss it as purely cosmetic — update your mental model of how context works in React 19.

---

## 6. PRODUCTION TYPESCRIPT/REACT CODE EXAMPLES

### Example 1: use() with Suspense and ErrorBoundary

```typescript
// ProductDetail.tsx
import { use, Suspense } from "react";
import { ErrorBoundary } from "react-error-boundary";

async function fetchProduct(id: string): Promise<Product> {
  const res = await fetch(`/api/products/${id}`);
  if (!res.ok) throw new Error("Product not found");
  return res.json();
}

function ProductCard({ productPromise }: { productPromise: Promise<Product> }) {
  const product = use(productPromise); // suspends if pending, throws if rejected
  return <div>{product.name} — ${product.price}</div>;
}

export function ProductDetail({ id }: { id: string }) {
  const productPromise = fetchProduct(id); // create once, outside render
  return (
    <ErrorBoundary fallback={<p>Failed to load product.</p>}>
      <Suspense fallback={<p>Loading...</p>}>
        <ProductCard productPromise={productPromise} />
      </Suspense>
    </ErrorBoundary>
  );
}
```

> Note: In production, `fetchProduct` would be called at route level or cached — never recreated on each render.

---

### Example 2: Context as Provider + use() for Conditional Read

```typescript
// ThemeContext.tsx
import { createContext, use } from "react";

type Theme = "light" | "dark";
const ThemeContext = createContext<Theme>("light");

export function ThemeProvider({ children, value }: { children: React.ReactNode; value: Theme }) {
  return <ThemeContext value={value}>{children}</ThemeContext>; // no .Provider
}

export function ThemedButton({ admin }: { admin?: boolean }) {
  // use() can be called conditionally — unlike useContext
  const theme = admin ? use(ThemeContext) : "light";
  return <button data-theme={theme}>Click</button>;
}
```

---

### Example 3: Server Action with Zod Validation

```typescript
// actions/newsletter.ts
"use server";
import { z } from "zod";
import { db } from "@/lib/db";

const Schema = z.object({ email: z.string().email() });
type Result = { ok: true } | { ok: false; error: string };

export async function subscribeAction(_: Result | null, fd: FormData): Promise<Result> {
  const parsed = Schema.safeParse({ email: fd.get("email") });
  if (!parsed.success) return { ok: false, error: "Invalid email address" };
  await db.subscribers.upsert({ email: parsed.data.email });
  return { ok: true };
}
```

```typescript
// NewsletterForm.tsx
"use client";
import { useActionState } from "react";
import { useFormStatus } from "react-dom";
import { subscribeAction } from "./actions/newsletter";

function SubmitBtn() {
  const { pending } = useFormStatus();
  return <button disabled={pending}>{pending ? "Subscribing..." : "Subscribe"}</button>;
}

export function NewsletterForm() {
  const [state, dispatch] = useActionState(subscribeAction, null);
  if (state?.ok) return <p>You are subscribed!</p>;
  return (
    <form action={dispatch}>
      <input name="email" type="email" placeholder="you@example.com" />
      {state?.error && <span role="alert">{state.error}</span>}
      <SubmitBtn />
    </form>
  );
}
```

---

### Example 4: useOptimistic — Like/Unlike Toggle

```typescript
"use client";
import { useOptimistic, useTransition } from "react";
import { toggleLikeAction } from "./actions";

interface Props { postId: string; initialLiked: boolean; initialCount: number; }

export function LikeButton({ postId, initialLiked, initialCount }: Props) {
  const [optimistic, setOptimistic] = useOptimistic(
    { liked: initialLiked, count: initialCount },
    (cur, newLiked: boolean) => ({
      liked: newLiked,
      count: newLiked ? cur.count + 1 : cur.count - 1,
    })
  );
  const [, startTransition] = useTransition();

  function handleClick() {
    startTransition(async () => {
      setOptimistic(!optimistic.liked);
      await toggleLikeAction(postId, !optimistic.liked);
    });
  }

  return (
    <button onClick={handleClick} aria-pressed={optimistic.liked}>
      {optimistic.liked ? "Unlike" : "Like"} ({optimistic.count})
    </button>
  );
}
```

---

### Example 5: ref as Prop — Design System Input Component

```typescript
// Input.tsx — React 19, no forwardRef
import { ComponentPropsWithRef } from "react";

interface InputProps extends ComponentPropsWithRef<"input"> {
  label: string;
  error?: string;
}

export function Input({ label, error, ref, id, ...props }: InputProps) {
  const inputId = id ?? `input-${label.toLowerCase().replace(/\s/g, "-")}`;
  return (
    <div>
      <label htmlFor={inputId}>{label}</label>
      <input id={inputId} ref={ref} aria-invalid={!!error} {...props} />
      {error && <span role="alert">{error}</span>}
    </div>
  );
}
```

---

### Example 6: Asset Preloading APIs

```typescript
// VideoPlayerPage.tsx — preload heavy assets before component mounts
import { preinit, preload } from "react-dom";

export function VideoPlayerPage({ videoUrl }: { videoUrl: string }) {
  // Eagerly preload the player script and video chunk
  preinit("https://cdn.acme.com/player.js", { as: "script" });
  preload(videoUrl, { as: "video" });

  return (
    <>
      <title>Watch Video</title>
      <link rel="preload" href={videoUrl} as="video" />
      <VideoPlayer src={videoUrl} />
    </>
  );
}
```

---

### Example 7: Document Metadata Colocated with Route Component

```typescript
// app/products/[slug]/page.tsx (Next.js App Router)
import { notFound } from "next/navigation";

async function getProduct(slug: string) {
  const res = await fetch(`${process.env.API_URL}/products/${slug}`, { next: { revalidate: 60 } });
  if (!res.ok) return null;
  return res.json() as Promise<Product>;
}

export default async function ProductPage({ params }: { params: { slug: string } }) {
  const product = await getProduct(params.slug);
  if (!product) notFound();
  return (
    <>
      <title>{product.name} | Acme</title>
      <meta name="description" content={product.shortDescription} />
      <meta property="og:image" content={product.imageUrl} />
      <ProductDetail product={product} />
    </>
  );
}
```

---

### Example 8: React Compiler Opt-Out with use no memo

```typescript
// AudioVisualizer.tsx — uses mutable canvas ref, opt out of compiler
"use no memo";

import { useRef, useEffect } from "react";

interface Props { analyserNode: AnalyserNode }

export function AudioVisualizer({ analyserNode }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current!;
    const ctx = canvas.getContext("2d")!;
    const data = new Uint8Array(analyserNode.frequencyBinCount);
    let raf: number;

    function draw() {
      analyserNode.getByteFrequencyData(data);
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      data.forEach((val, i) => {
        ctx.fillRect(i * 3, canvas.height - val, 2, val);
      });
      raf = requestAnimationFrame(draw);
    }
    raf = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(raf);
  }, [analyserNode]);

  return <canvas ref={canvasRef} width={600} height={200} />;
}
```

---

## 7. INTERVIEW CHEAT SHEET

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                   REACT 19 — ARCHITECT CHEAT SHEET                         ║
╠══════════════════════╦═════════════════════════════════════════════════════╣
║ FEATURE              ║ ONE-LINE MENTAL MODEL                               ║
╠══════════════════════╬═════════════════════════════════════════════════════╣
║ React Compiler       ║ Auto-memoization via static analysis; opt out with  ║
║                      ║ "use no memo"; enforces Rules of React              ║
╠══════════════════════╬═════════════════════════════════════════════════════╣
║ use(promise)         ║ Synchronous read in render; suspends if pending;    ║
║                      ║ NOT a replacement for useEffect                     ║
╠══════════════════════╬═════════════════════════════════════════════════════╣
║ use(Context)         ║ Read context conditionally/in loops; unlike         ║
║                      ║ useContext which must be unconditional              ║
╠══════════════════════╬═════════════════════════════════════════════════════╣
║ useFormStatus        ║ Must live in CHILD of <form>; reads parent form's   ║
║                      ║ pending state; no prop drilling for loading state   ║
╠══════════════════════╬═════════════════════════════════════════════════════╣
║ useOptimistic        ║ Local optimistic state; auto-reverts on error;      ║
║                      ║ NOT conflict resolution; wrap in startTransition    ║
╠══════════════════════╬═════════════════════════════════════════════════════╣
║ useActionState       ║ Action result + pending state in one hook;          ║
║                      ║ form action={dispatch} for progressive enhancement  ║
╠══════════════════════╬═════════════════════════════════════════════════════╣
║ Server Actions       ║ "use server" fn called from client as RPC;          ║
║                      ║ NOT public API; always validate input; check auth   ║
╠══════════════════════╬═════════════════════════════════════════════════════╣
║ ref as prop          ║ forwardRef deprecated; ref is just a prop now;      ║
║                      ║ add to Props interface with React.Ref<T>            ║
╠══════════════════════╬═════════════════════════════════════════════════════╣
║ <Context> shorthand  ║ No more .Provider; part of context redesign;        ║
║                      ║ pair with use(Context) for conditional reads        ║
╠══════════════════════╬═════════════════════════════════════════════════════╣
║ Document metadata    ║ <title>/<meta>/<link> anywhere; React deduplicates; ║
║                      ║ use precedence prop for stylesheet order            ║
╠══════════════════════╬═════════════════════════════════════════════════════╣
║ Asset loading        ║ preinit() / preload() / preloadModule() in render;  ║
║                      ║ emits <link rel="preload"> in <head>                ║
╠══════════════════════╬═════════════════════════════════════════════════════╣
║ Hydration errors     ║ React 19 shows server/client diff + source pointer; ║
║                      ║ no more cryptic "text content mismatch"             ║
╠══════════════════════╩═════════════════════════════════════════════════════╣
║                         TRAP QUICK-REFERENCE                               ║
╠══════════════════════╦═════════════════════════════════════════════════════╣
║ TRAP                 ║ CORRECT RESPONSE                                    ║
╠══════════════════════╬═════════════════════════════════════════════════════╣
║ Compiler → delete    ║ No — measure first; compiler has blind spots        ║
║ all useMemo          ║ (dynamic keys, cross-component, library interop)    ║
╠══════════════════════╬═════════════════════════════════════════════════════╣
║ use() = useEffect    ║ No — use() is a sync read in render; no cleanup;   ║
║ for promises         ║ useEffect is still for side effects                 ║
╠══════════════════════╬═════════════════════════════════════════════════════╣
║ Server Actions =     ║ No — opaque URL, React-coupled, no external callers ║
║ API routes           ║ without extra work; different security model        ║
╠══════════════════════╬═════════════════════════════════════════════════════╣
║ forwardRef needed    ║ No — deprecated in React 19; ref is a regular prop  ║
╠══════════════════════╬═════════════════════════════════════════════════════╣
║ useOptimistic =      ║ No — it's local/single-user; collaborative editing  ║
║ conflict resolution  ║ needs CRDT (Yjs/Automerge) at the data layer        ║
╠══════════════════════╬═════════════════════════════════════════════════════╣
║ <Context> = only     ║ No — part of context redesign; use(Context) enables ║
║ cosmetic sugar       ║ conditional reads, which is a behavioral change     ║
╚══════════════════════╩═════════════════════════════════════════════════════╝
```

### Migration Checklist: React 18 → React 19

```
□ Upgrade to React 18.3 first — it adds deprecation warnings for React 19 removals
□ Fix all console warnings from 18.3 before upgrading
□ Replace ReactDOM.render with createRoot (removed in React 19)
□ Remove string refs (removed)
□ Remove legacy Context API (contextTypes / childContextTypes removed)
□ Remove defaultProps on function components (deprecated, use default params)
□ Update react + react-dom + @types/react to 19.x together
□ Update Next.js to 15+ if using App Router (React 19 support)
□ Install eslint-plugin-react-compiler, fix violations before enabling compiler
□ Enable compiler per-directory (includesPaths) not globally on day one
□ Replace react-helmet / react-helmet-async with native metadata tags
□ Migrate forwardRef components to plain props + ref in interface (optional but clean)
□ Test hydration in staging — React 19 is stricter about mismatches
□ Verify TypeScript types: @types/react 19 changes Ref handling
□ Run visual regression suite (Chromatic/Percy) before shipping
```

### Key Differences: React 18 vs React 19 at a Glance

```
                    REACT 18              REACT 19
                   ──────────            ──────────
Async transitions  startTransition       startTransition(async fn)
                   (sync only)           supported natively

Form handling      useEffect + fetch     Server Actions + useActionState
                   manual state          + useFormStatus built in

Memoization        Manual everywhere     React Compiler handles most cases
                                         "use no memo" to opt out

ref forwarding     forwardRef wrapper    ref is a regular prop
                   required

Context syntax     <Ctx.Provider>        <Ctx> shorthand (+ use(Ctx))

Metadata           react-helmet          Native <title>/<meta>/<link>

Hydration errors   Cryptic messages      Diff view with source pointer

Suspense data      Third-party libs      use(promise) as first-class API
```

---

*Prepared for 15-YOE React Architect interviews. Covers React 19 stable + React Compiler (Forget) as of 2024-2025 release cycle. Always verify against official React blog and changelog for latest status.*
