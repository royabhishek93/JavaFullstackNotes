# React State Management — 15-YOE Interview Prep

> Target: Senior / Staff / Principal engineer interviews. Every answer below is written the
> way a 15-year veteran actually speaks — no hand-waving, no toy examples.

---

## 1. State Management Landscape (Big Picture)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     STATE MANAGEMENT OPTIONS LANDSCAPE                      │
├──────────────────────┬──────────────────────────────────────────────────────┤
│  STATE TYPE          │  BEST TOOL(S)                                        │
├──────────────────────┼──────────────────────────────────────────────────────┤
│  Local UI state      │  useState, useReducer                                │
│  (toggle, form field)│                                                      │
├──────────────────────┼──────────────────────────────────────────────────────┤
│  Shared client state │  Zustand (simple), Redux Toolkit (large / auditable) │
│  (cart, user prefs)  │  Context + useReducer (low-churn, small apps)        │
├──────────────────────┼──────────────────────────────────────────────────────┤
│  Server / async state│  TanStack Query (React Query), RTK Query             │
│  (API data, cache)   │  SWR (lightweight alternative)                       │
├──────────────────────┼──────────────────────────────────────────────────────┤
│  URL / navigation    │  useSearchParams (React Router v6), nuqs             │
│  state               │  (filters, sort, page number — shareable links)      │
├──────────────────────┼──────────────────────────────────────────────────────┤
│  Form state          │  React Hook Form (perf-critical / large forms)       │
│                      │  Controlled components (simple, <5 fields)           │
├──────────────────────┼──────────────────────────────────────────────────────┤
│  Atomic / fine-grain │  Jotai, Recoil                                       │
│  derived state       │  (derived atoms, no Provider boilerplate)            │
└──────────────────────┴──────────────────────────────────────────────────────┘

        DECISION MATRIX — "Which tool do I reach for?"

        Is the state server data (fetched from an API)?
            YES ──► React Query / RTK Query  (caching, dedup, retry for free)
            NO  ──► Is it tied to the URL? (filter, pagination)
                        YES ──► useSearchParams / nuqs
                        NO  ──► Is it local to ONE component?
                                    YES ──► useState / useReducer
                                    NO  ──► Shared across many components?
                                                Small app / low churn?
                                                    YES ──► Zustand
                                                Large, auditable, time-travel?
                                                    YES ──► Redux Toolkit
```

---

## 2. State Taxonomy Deep-Dive

### 2a. Local State
`useState` and `useReducer` live inside a single component tree. Lift them only when two
siblings need to share — never pre-emptively lift to a global store.

### 2b. Shared Client State
State owned by the frontend that multiple components read/write: shopping cart, theme,
authenticated user object (after login). Candidates: Zustand, Redux Toolkit, Context.

### 2c. Server State
Data that lives on the server, cached locally. Has loading / error / stale / refetch
lifecycle. React Query was built precisely for this. Trying to manage it with
`useState + useEffect` is reinventing the wheel badly.

### 2d. URL State
Filters, sort column, page number, selected tab — anything where the user expects to
paste the URL and land in the same view. `useSearchParams` (React Router) or `nuqs`
(type-safe query params). This is massively underused in production codebases.

---

## 3. Conversational Interview Script

> Interviewer: "Walk me through how you think about state management on a large React app."

**15-YOE answer:**

"My first instinct is to categorize the state before picking a tool. There are really four
buckets: local UI state, shared client state, server state, and URL state. Each has a
different lifecycle and a different optimal tool.

For server data — anything that comes from an API — I reach for React Query almost
reflexively. It gives you caching, background refetching, deduplication of in-flight
requests, loading and error states, and optimistic updates, all configured with a few
options. Before React Query existed, every team I joined had a bespoke `useApi` hook that
was basically a bad re-implementation of those same concerns.

For shared client state that has nothing to do with the server — a shopping cart that
hasn't been saved yet, user preferences stored in localStorage, modal open/close state
shared between a nav button and a sidebar — I use Zustand. It has almost no boilerplate.
One `create` call, selectors that prevent unnecessary re-renders, and devtools support
with one line. For teams that need time-travel debugging, strict serialisability
enforcement, or very large teams where auditability matters, I'd go Redux Toolkit instead.
RTK with `createSlice` and `createAsyncThunk` has removed most of the classic Redux
boilerplate.

Context API I use sparingly. It's great for low-churn configuration — theme, locale,
feature flags. The problem is every consumer re-renders on every context value change, and
that's a real performance footgun if you put frequently-updated state in it.

URL state is probably the most underused. If a user should be able to bookmark or share a
URL and land in the same state — filter by category, page 3, sorted by date — that belongs
in the URL, not in component state. `useSearchParams` from React Router v6 or the `nuqs`
library handles this cleanly with TypeScript types."

---

> Interviewer: "How does Context API work under the hood, and when does it cause problems?"

**15-YOE answer:**

"React Context uses a provider-consumer model. When the provider's value prop changes —
reference equality check — React schedules a re-render of every component that called
`useContext` for that context. There's no selector mechanism. If I have a context that
holds `{ theme, user, cartCount }` and `cartCount` changes on every add-to-cart click,
every component subscribed to that context re-renders, even the ones that only care about
`theme`.

The fix is either to split the context into multiple smaller contexts — one for theme, one
for user, one for cart — or to move the high-churn state to Zustand which has selector
support. Memoisation with `React.memo` on consumers can also help, but it's defence-in-
depth, not a root fix.

I've seen production apps with a monolithic `AppContext` that held 30 fields. On every
keystroke in a search box, the entire app re-rendered. The fix was a 3-hour refactor to
Zustand with selectors."

---

## 4. Scenario-Based Q&As (Production Context)

---

### Q1. You're building a shopping cart. Where does cart state live?

**Answer:**

Cart state is shared client state — multiple components need it (header badge, cart
sidebar, checkout page). Before checkout, it's purely client-side; after checkout it gets
persisted to the server.

I'd model it in Zustand: a slice with `items[]`, `addItem`, `removeItem`, `clearCart`. The
header reads `useCartStore(s => s.items.length)` — a selector that only re-renders when
item count changes, not on every cart mutation. If the user is logged in, I sync cart
state to the server with a `useMutation` from React Query on every add/remove, and I load
the server cart on mount with `useQuery`.

I would NOT put this in Redux unless the team already uses Redux and I need time-travel
debugging for QA purposes.

---

### Q2. The product listing page has filters (category, price range, sort) and pagination. Where does that state live?

**Answer:**

URL state, without hesitation. `?category=electronics&minPrice=100&page=2&sort=price_asc`.

Why? Because users expect browser back/forward to work, expect to bookmark the filtered
view, and expect to share the link with a colleague who sees the same results. If I use
`useState` for this, all of that breaks.

I'd use `nuqs` for type-safe query params, or `useSearchParams` from React Router v6 and
parse manually. The component reads from the URL, dispatches `setSearchParams` on filter
change, and React Query fetches based on those params.

```tsx
// URL-driven filters with nuqs
import { useQueryState, parseAsInteger, parseAsString } from "nuqs";

function ProductFilters() {
  const [category, setCategory] = useQueryState("category", parseAsString.withDefault("all"));
  const [page, setPage] = useQueryState("page", parseAsInteger.withDefault(1));

  const { data } = useQuery({
    queryKey: ["products", category, page],
    queryFn: () => fetchProducts({ category, page }),
  });

  return <FilterUI category={category} page={page} onCategoryChange={setCategory} />;
}
```

---

### Q3. A data table shows 10,000 user records. Server state. How do you manage loading, pagination, and stale data?

**Answer:**

React Query with `keepPreviousData: true` (or `placeholderData: keepPreviousData` in v5)
so the table doesn't flash empty on every page change. I'd also prefetch the next page on
hover or on mount.

```tsx
import { useQuery, keepPreviousData } from "@tanstack/react-query";

function UsersTable({ page }: { page: number }) {
  const { data, isFetching } = useQuery({
    queryKey: ["users", page],
    queryFn: () => fetchUsers(page),
    placeholderData: keepPreviousData,
    staleTime: 30_000, // treat data as fresh for 30s — avoid refetch on tab focus
  });

  // Prefetch next page
  const queryClient = useQueryClient();
  useEffect(() => {
    queryClient.prefetchQuery({
      queryKey: ["users", page + 1],
      queryFn: () => fetchUsers(page + 1),
    });
  }, [page, queryClient]);

  return <Table rows={data?.users} loading={isFetching} />;
}
```

---

### Q4. An authentication flow: user logs in, JWT stored, user object shared across the app. How do you model this?

**Answer:**

Two separate concerns:

1. **The JWT** — stored in an httpOnly cookie (never localStorage for security). The auth
   flow is a server round-trip, so I use a React Query mutation for the login call.

2. **The user object** — once logged in, I fetch `/me` with React Query and treat it as
   server state with a long `staleTime` (e.g., 5 minutes). Components that need the user
   call `useCurrentUser()` which is just a thin wrapper around `useQuery({ queryKey: ['me'] })`.

I do NOT put the user object in a Context or Zustand store. React Query is already caching
it. A second store is redundant state that can get out of sync.

```tsx
// hooks/useCurrentUser.ts
export function useCurrentUser() {
  return useQuery<User>({
    queryKey: ["me"],
    queryFn: fetchCurrentUser,
    staleTime: 5 * 60 * 1000,
    retry: false, // don't retry 401s
  });
}

// Any component
function Avatar() {
  const { data: user } = useCurrentUser();
  return <img src={user?.avatarUrl} alt={user?.name} />;
}
```

---

### Q5. A form with 50 fields — address, billing, shipping, preferences. Controlled components or React Hook Form?

**Answer:**

React Hook Form, no question. Controlled components re-render the entire form on every
keystroke because state lives in React. React Hook Form is uncontrolled by default —
values live in the DOM, and it only triggers a re-render on `formState` changes (errors,
dirty, submit). For a 50-field form, the performance difference is dramatic.

The other benefit is validation integration. Zod + RHF's `zodResolver` gives you
schema-level validation with TypeScript types inferred automatically.

```tsx
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

const CheckoutSchema = z.object({
  street: z.string().min(1, "Required"),
  city: z.string().min(1, "Required"),
  zip: z.string().regex(/^\d{5}$/, "Must be 5 digits"),
  cardNumber: z.string().length(16),
});

type CheckoutForm = z.infer<typeof CheckoutSchema>;

function CheckoutPage() {
  const { register, handleSubmit, formState: { errors } } = useForm<CheckoutForm>({
    resolver: zodResolver(CheckoutSchema),
  });

  const onSubmit = (data: CheckoutForm) => submitOrder(data);

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <input {...register("street")} />
      {errors.street && <span>{errors.street.message}</span>}
      {/* ... */}
    </form>
  );
}
```

---

### Q6. How do you implement optimistic updates for a "like" button?

**Answer:**

React Query's `onMutate` / `onError` / `onSettled` callbacks are built for this.

```tsx
const likeMutation = useMutation({
  mutationFn: (postId: string) => likePost(postId),
  onMutate: async (postId) => {
    await queryClient.cancelQueries({ queryKey: ["posts"] });
    const previous = queryClient.getQueryData<Post[]>(["posts"]);
    queryClient.setQueryData<Post[]>(["posts"], (old) =>
      old?.map((p) => p.id === postId ? { ...p, likes: p.likes + 1 } : p) ?? []
    );
    return { previous }; // context passed to onError
  },
  onError: (_err, _vars, context) => {
    // Roll back on failure
    queryClient.setQueryData(["posts"], context?.previous);
  },
  onSettled: () => {
    queryClient.invalidateQueries({ queryKey: ["posts"] });
  },
});
```

The pattern: cancel in-flight queries, snapshot current data, apply optimistic change,
return snapshot as context. On error, restore snapshot. On settled, invalidate to sync
with server truth.

---

### Q7. A real-time dashboard — WebSocket pushes updates every second. Where does this data live?

**Answer:**

React Query can receive manual cache updates from a WebSocket. I'd use `queryClient.setQueryData`
inside the WebSocket message handler. This keeps the data in the React Query cache so
components use `useQuery` as normal — they don't know or care whether the data arrived
via HTTP or WebSocket.

```tsx
function useLiveDashboard() {
  const queryClient = useQueryClient();

  // Initial load via HTTP
  const query = useQuery({ queryKey: ["dashboard"], queryFn: fetchDashboard });

  useEffect(() => {
    const ws = new WebSocket("wss://api.example.com/dashboard");
    ws.onmessage = (event) => {
      const update: DashboardData = JSON.parse(event.data);
      queryClient.setQueryData(["dashboard"], update);
    };
    return () => ws.close();
  }, [queryClient]);

  return query;
}
```

---

### Q8. You have a normalized entity store — users, posts, comments. An update to a user's name needs to reflect everywhere. How do you structure this?

**Answer:**

Normalisation. Store entities as flat maps keyed by ID, not nested arrays. Redux Toolkit's
`createEntityAdapter` gives this out of the box. React Query can also be set up this way
by using individual `["user", id]` query keys and updating them on mutations.

The core principle: single source of truth per entity. If `user_42` appears in the posts
list and the sidebar and the comment threads, they all point to `users["42"]`. Update once,
reads everywhere see the change.

```ts
// RTK entity adapter example
import { createEntityAdapter, createSlice } from "@reduxjs/toolkit";

interface User { id: string; name: string; avatarUrl: string; }

const usersAdapter = createEntityAdapter<User>();

const usersSlice = createSlice({
  name: "users",
  initialState: usersAdapter.getInitialState(),
  reducers: {
    upsertUser: usersAdapter.upsertOne,
    removeUser: usersAdapter.removeOne,
  },
});

// Selectors
export const { selectAll: selectAllUsers, selectById: selectUserById } =
  usersAdapter.getSelectors((state: RootState) => state.users);
```

---

## 5. Advanced Scenario Q&As

---

### A1. RTK Query vs React Query — when do you choose each?

**Answer:**

RTK Query lives inside the Redux ecosystem. If my app already uses Redux Toolkit and I
want the server state to live in the Redux store — so I can inspect it in Redux DevTools,
combine it with reducers, or use it in middleware — RTK Query is the natural fit. It
generates hooks from an `api` slice definition, and cache invalidation uses tags.

React Query (TanStack Query) is framework-agnostic and lighter to set up. If I'm starting
fresh and don't need Redux, React Query has a better DX for complex scenarios like
infinite scroll, dependent queries, and the optimistic update pattern above.

The practical tie-breaker: if the team is already on Redux, RTK Query. Otherwise, React
Query. Never both in the same app for the same data — that's double caching.

```ts
// RTK Query — define once, use everywhere
const api = createApi({
  reducerPath: "api",
  baseQuery: fetchBaseQuery({ baseUrl: "/api" }),
  tagTypes: ["User"],
  endpoints: (builder) => ({
    getUser: builder.query<User, string>({
      query: (id) => `users/${id}`,
      providesTags: (_, __, id) => [{ type: "User", id }],
    }),
    updateUser: builder.mutation<User, Partial<User> & { id: string }>({
      query: ({ id, ...patch }) => ({ url: `users/${id}`, method: "PATCH", body: patch }),
      invalidatesTags: (_, __, { id }) => [{ type: "User", id }],
    }),
  }),
});

export const { useGetUserQuery, useUpdateUserMutation } = api;
```

---

### A2. Immer under the hood in Redux Toolkit — explain what it does and why it matters.

**Answer:**

Immer lets you write reducers that look like they mutate state directly, but Immer
intercepts those mutations and produces a new immutable state object. Under the hood it
uses JavaScript Proxies to record every mutation on a draft copy, then applies them to
produce a new object without touching the original.

Why it matters: before Immer, Redux reducers were full of spread operators that were
verbose and error-prone. With RTK + Immer:

```ts
// Without Immer — error-prone spread
case "UPDATE_ITEM":
  return {
    ...state,
    items: state.items.map(item =>
      item.id === action.payload.id
        ? { ...item, ...action.payload }
        : item
    ),
  };

// With RTK + Immer — reads like imperative code, stays immutable
updateItem(state, action: PayloadAction<Item>) {
  const item = state.items.find(i => i.id === action.payload.id);
  if (item) Object.assign(item, action.payload); // Immer handles the rest
},
```

The gotcha: you can EITHER mutate the draft OR return a new value. Never both. If you
return a value from a Immer producer AND mutate the draft, Immer throws. This trips up
engineers unfamiliar with Immer.

---

### A3. Jotai atoms vs Zustand store — when do atoms win?

**Answer:**

Atoms win when you have a large graph of fine-grained, derived state where different parts
of the UI subscribe to different slices and you want React to only re-render what changed.

Classic example: a spreadsheet or a canvas editor. Each cell is an atom. A formula cell
derives its atom from other atoms. Only the cells that depend on changed atoms re-render.
In a single Zustand store, you'd need very precise selectors to achieve the same, and the
selector setup becomes complex.

Atoms also avoid the Provider boilerplate of Context and the single-store mental model of
Redux/Zustand. But for most apps — a shopping cart, a user dashboard — a Zustand store
with good selectors is simpler and more predictable than a graph of atoms.

```ts
// Jotai derived atom example
import { atom, useAtom } from "jotai";

const priceAtom = atom(100);
const taxRateAtom = atom(0.08);
const totalAtom = atom((get) => get(priceAtom) * (1 + get(taxRateAtom)));

function PriceSummary() {
  const [total] = useAtom(totalAtom); // only re-renders when price or taxRate changes
  return <div>Total: ${total.toFixed(2)}</div>;
}
```

---

### A4. Zustand selectors — how do they prevent re-renders, and when do they fail?

**Answer:**

Zustand's `useStore` hook re-renders a component when the selected slice changes by
reference equality (`Object.is`). If you select a primitive (`s => s.count`), it only
re-renders when `count` changes. If you select an object (`s => s.user`), it re-renders
whenever the `user` reference changes — even if no fields changed.

The failure mode: inline object creation inside the selector.

```ts
// BUG — new object every render, always re-renders
const { name, email } = useStore(s => ({ name: s.user.name, email: s.user.email }));

// FIX 1 — select primitives individually
const name = useStore(s => s.user.name);
const email = useStore(s => s.user.email);

// FIX 2 — use shallow equality
import { shallow } from "zustand/shallow";
const { name, email } = useStore(s => ({ name: s.user.name, email: s.user.email }), shallow);
```

In production I enforce a team rule: never select an object literal inline. Either select
primitives or use `shallow`. This is documented in our ADR.

Zustand devtools are enabled by wrapping the store with the `devtools` middleware:

```ts
import { devtools } from "zustand/middleware";
const useStore = create<CartStore>()(devtools((set) => ({ ... }), { name: "CartStore" }));
```

---

## 6. Senior Trap Questions

---

### TRAP 1: "Context API is perfect for global state, right?"

**The Trap:** Saying yes without qualification.

**What the interviewer is testing:** Whether you know about the re-render problem.

**Correct Answer:**

"Context is good for low-churn global state — theme, locale, feature flags. The problem
is that there's no selector mechanism. When the context value changes, every component
that calls `useContext` for that context re-renders, period. If you put a frequently-
updated value — like cart item count, or any state that changes on user interaction — into
a monolithic context object, you trigger cascading re-renders across the entire tree.

For high-churn shared state, Zustand with selectors is the right tool. For low-churn
config-like state, Context is fine. I've seen production apps grind to a halt because
someone put form state in an AppContext."

---

### TRAP 2: "Redux is too complex. I'd never use it in a modern app."

**The Trap:** Dismissing Redux without nuance, OR defending vanilla Redux without mentioning RTK.

**What the interviewer is testing:** Whether you know the modern Redux story.

**Correct Answer:**

"Vanilla Redux circa 2017 — action constants, switch-case reducers, separate action
creators, connect HOC — yes, that was boilerplate-heavy. But Redux Toolkit, which is now
the official recommended approach, has eliminated most of that. `createSlice` combines
actions and reducers. `createAsyncThunk` handles async with loading/error states.
`createEntityAdapter` handles normalised collections. RTK Query handles server state.

That said, I don't reach for Redux by default. For a small-to-medium app, Zustand is
simpler and has less ceremony. I'd use Redux Toolkit when: the team is large and needs
strict conventions, we need time-travel debugging for complex flows (e.g., a multi-step
checkout wizard), or the app has complex cross-cutting state that benefits from middleware
like analytics or logging."

---

### TRAP 3: "I use useEffect to sync server data into component state."

**The Trap:** Using `useEffect` + `useState` for server data fetching.

**What the interviewer is testing:** Whether you know why this is an antipattern.

**Correct Answer:**

"That pattern solves the fetch, but you're re-implementing a subset of what React Query
does — badly. With `useEffect + useState` you get: no deduplication (two components
mounting simultaneously fire two identical requests), no caching (navigating away and back
refetches from scratch), no background refetch on focus or interval, no built-in loading /
error states unless you add more useState calls, no retry on failure, and no way to
invalidate the cache when a mutation happens.

React Query gives all of that with one `useQuery` call and a handful of options. The
`useEffect + fetch + setState` pattern is the 2019 way. In 2024 it's a code smell in any
app of meaningful size."

---

### TRAP 4: "I store API response data in useState."

**The Trap:** Using `useState` as a cache for server data.

**What the interviewer is testing:** Same as Trap 3, specifically about the caching dimension.

**Correct Answer:**

"useState has no concept of staleness, no shared cache across components, and no automatic
background refresh. If two components both need the same `/api/products` data and both use
useState, you fire two requests and get two independent caches that can diverge. If you
update a product and want the list to reflect it, you have to manually thread callbacks or
use a shared ref.

React Query uses a query key as a cache key. Any component anywhere in the tree that calls
`useQuery({ queryKey: ['products'] })` shares the same cached result. Invalidating that
key on mutation refetches once and both components update. That's the right model for
server state."

---

### TRAP 5: "Zustand and Redux are basically the same thing."

**The Trap:** Treating them as interchangeable.

**What the interviewer is testing:** Whether you understand their architectural differences.

**Correct Answer:**

"They solve the same problem — shared client state — but with different philosophies and
trade-offs.

Zustand is a minimal, unopinionated store. No actions, no reducers, no dispatch — you just
call functions that `set` state. Setup is 10 lines. No Provider required. Devtools and
time-travel are opt-in via middleware and not as mature as Redux's.

Redux Toolkit enforces a strict unidirectional data flow: components dispatch actions,
reducers handle them, selectors read. This structure is overhead for small apps but a
feature for large teams — it makes every state change auditable and traceable through
Redux DevTools, even months later in production. Redux also has a rich middleware
ecosystem (analytics, logging, offline sync).

The practical guidance I give teams: start with Zustand. If you hit the point where you
need strict conventions, advanced devtools, or complex middleware, migrate to RTK. The two
are not equivalent — Zustand optimises for simplicity, Redux optimises for structure."

---

### TRAP 6: "I memoize everything with useMemo and useCallback to prevent re-renders."

**The Trap:** Over-memoizing, or memoizing without measuring.

**What the interviewer is testing:** Whether you understand when memoization actually helps
vs. adds cost.

**Correct Answer:**

"Memoization has a cost — computing and storing the previous result, doing the comparison.
If the computation is cheap (string concatenation, simple filter), memoizing it is net
negative. `useMemo` and `useCallback` are optimizations, not defaults.

I reach for `useMemo` when: the computation is genuinely expensive (sorting/filtering
10,000 items), or the value is a reference type passed to a `React.memo` child where
reference instability would cause unnecessary re-renders.

`useCallback` is useful when passing callbacks to `React.memo` children or as dependencies
of `useEffect`/`useMemo` that should only re-run when the callback logic actually changes.

The correct process: profile first with React DevTools Profiler, find the actual hot
spots, then apply memoization surgically. Blanket memoization everywhere is cargo-culting.
I've reviewed codebases where every function and variable was wrapped in hooks — it added
memory overhead and made the code harder to read with zero measurable perf improvement."

---

### TRAP 7 (Bonus): "staleTime and cacheTime in React Query are the same thing."

**The Trap:** Confusing the two, or not knowing what either does.

**What the interviewer is testing:** Whether you've actually shipped React Query in production.

**Correct Answer:**

"They control different things. `staleTime` is how long React Query considers data fresh
after it's fetched. During that window, it won't refetch on component mount or window
focus — it just returns the cached value. Default is 0, meaning data is immediately stale
and will background-refetch on next mount.

`cacheTime` (renamed `gcTime` in v5) is how long unused data stays in the cache after all
subscribers unmount. When a component unmounts, React Query starts a garbage collection
timer. If no component re-subscribes before the timer expires, the cache entry is cleared.
Default is 5 minutes.

In practice: I set `staleTime` based on how often the data changes. For static reference
data (country list, product categories), I'll set `staleTime: Infinity`. For user-
generated content, I'll set 30–60 seconds. `gcTime` I rarely change — 5 minutes is
usually right."

---

## 7. Production Code Examples

### 7a. Zustand Store with TypeScript and Selectors

```ts
// store/cartStore.ts
import { create } from "zustand";
import { devtools, persist } from "zustand/middleware";

interface CartItem { id: string; name: string; price: number; qty: number; }
interface CartState {
  items: CartItem[];
  addItem: (item: Omit<CartItem, "qty">) => void;
  removeItem: (id: string) => void;
  clearCart: () => void;
}

export const useCartStore = create<CartState>()(
  devtools(
    persist(
      (set) => ({
        items: [],
        addItem: (item) =>
          set((s) => {
            const existing = s.items.find((i) => i.id === item.id);
            if (existing) {
              return { items: s.items.map((i) => i.id === item.id ? { ...i, qty: i.qty + 1 } : i) };
            }
            return { items: [...s.items, { ...item, qty: 1 }] };
          }),
        removeItem: (id) => set((s) => ({ items: s.items.filter((i) => i.id !== id) })),
        clearCart: () => set({ items: [] }),
      }),
      { name: "cart-storage" }
    ),
    { name: "CartStore" }
  )
);

// Selector — only re-renders when item count changes
export const useCartCount = () => useCartStore((s) => s.items.reduce((n, i) => n + i.qty, 0));
```

---

### 7b. React Query — Infinite Scroll

```tsx
import { useInfiniteQuery } from "@tanstack/react-query";

function ProductList() {
  const { data, fetchNextPage, hasNextPage, isFetchingNextPage } = useInfiniteQuery({
    queryKey: ["products"],
    queryFn: ({ pageParam = 1 }) => fetchProducts(pageParam),
    getNextPageParam: (lastPage) => lastPage.nextPage ?? undefined,
    staleTime: 60_000,
  });

  const products = data?.pages.flatMap((p) => p.items) ?? [];

  return (
    <>
      {products.map((p) => <ProductCard key={p.id} product={p} />)}
      <button onClick={() => fetchNextPage()} disabled={!hasNextPage || isFetchingNextPage}>
        {isFetchingNextPage ? "Loading..." : hasNextPage ? "Load More" : "No More"}
      </button>
    </>
  );
}
```

---

### 7c. Redux Toolkit — createSlice with Immer

```ts
// features/notifications/notificationsSlice.ts
import { createSlice, createAsyncThunk, PayloadAction } from "@reduxjs/toolkit";

interface Notification { id: string; message: string; read: boolean; }
interface State { items: Notification[]; status: "idle" | "loading" | "failed"; }

export const fetchNotifications = createAsyncThunk(
  "notifications/fetch",
  async (userId: string) => {
    const res = await fetch(`/api/users/${userId}/notifications`);
    return res.json() as Promise<Notification[]>;
  }
);

const notificationsSlice = createSlice({
  name: "notifications",
  initialState: { items: [], status: "idle" } as State,
  reducers: {
    markRead(state, action: PayloadAction<string>) {
      const n = state.items.find((i) => i.id === action.payload);
      if (n) n.read = true; // Immer handles immutability
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchNotifications.pending, (state) => { state.status = "loading"; })
      .addCase(fetchNotifications.fulfilled, (state, action) => {
        state.status = "idle";
        state.items = action.payload;
      })
      .addCase(fetchNotifications.rejected, (state) => { state.status = "failed"; });
  },
});

export const { markRead } = notificationsSlice.actions;
export default notificationsSlice.reducer;
```

---

### 7d. React Hook Form + Zod (production form)

```tsx
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation } from "@tanstack/react-query";

const schema = z.object({
  email: z.string().email(),
  password: z.string().min(8, "Min 8 characters"),
  role: z.enum(["admin", "viewer", "editor"]),
});
type FormData = z.infer<typeof schema>;

export function CreateUserForm() {
  const { register, handleSubmit, control, formState: { errors, isSubmitting } } =
    useForm<FormData>({ resolver: zodResolver(schema) });

  const { mutateAsync } = useMutation({ mutationFn: createUser });

  return (
    <form onSubmit={handleSubmit((data) => mutateAsync(data))}>
      <input {...register("email")} placeholder="Email" />
      {errors.email && <p>{errors.email.message}</p>}
      <input {...register("password")} type="password" />
      {errors.password && <p>{errors.password.message}</p>}
      <Controller name="role" control={control}
        render={({ field }) => (
          <select {...field}>
            <option value="viewer">Viewer</option>
            <option value="editor">Editor</option>
            <option value="admin">Admin</option>
          </select>
        )} />
      <button type="submit" disabled={isSubmitting}>Create User</button>
    </form>
  );
}
```

---

## 8. Interview Cheat Sheet

```
┌─────────────────────────────────────────────────────────────────────┐
│                    REACT STATE MANAGEMENT CHEAT SHEET               │
├──────────────────┬──────────────────────────────────────────────────┤
│  Problem         │  Solution                                        │
├──────────────────┼──────────────────────────────────────────────────┤
│  API data        │  React Query (useQuery, useMutation)             │
│  Shared UI state │  Zustand (small/medium) or RTK (large/complex)   │
│  URL filters     │  useSearchParams / nuqs                          │
│  Forms (large)   │  React Hook Form + Zod                           │
│  Config/theme    │  Context API (low churn only)                    │
│  Fine-grained    │  Jotai atoms                                     │
│  derived state   │                                                  │
├──────────────────┼──────────────────────────────────────────────────┤
│  Context trap    │  All consumers re-render on any value change     │
│  Fix             │  Split contexts OR move to Zustand with selector │
├──────────────────┼──────────────────────────────────────────────────┤
│  useEffect trap  │  No cache, no dedup, no retry, no invalidation   │
│  Fix             │  useQuery from React Query                       │
├──────────────────┼──────────────────────────────────────────────────┤
│  Optimistic upd  │  onMutate (snapshot+apply), onError (rollback),  │
│                  │  onSettled (invalidate)                           │
├──────────────────┼──────────────────────────────────────────────────┤
│  Immer rule      │  Mutate draft OR return new value — never both   │
├──────────────────┼──────────────────────────────────────────────────┤
│  staleTime       │  How long data is "fresh" (no refetch)           │
│  gcTime          │  How long unused cache entry survives            │
├──────────────────┼──────────────────────────────────────────────────┤
│  Zustand select  │  Select primitives OR use shallow equality       │
│  Never           │  s => ({ a: s.a, b: s.b }) without shallow       │
├──────────────────┼──────────────────────────────────────────────────┤
│  Normalisation   │  entities (id map) + ids (array) — flat > nested │
├──────────────────┼──────────────────────────────────────────────────┤
│  RTK vs RQ       │  Already on Redux → RTK Query                    │
│                  │  Greenfield → React Query                        │
│                  │  Never both for same data                        │
├──────────────────┼──────────────────────────────────────────────────┤
│  Memoize rule    │  Measure first. Memoize when: expensive compute  │
│                  │  OR reference passed to React.memo child         │
└──────────────────┴──────────────────────────────────────────────────┘
```

### Quick talking points for the interview room

- "I categorise state before picking a tool — local, shared, server, URL."
- "Server state is a different problem from client state. React Query is not Redux."
- "Context is configuration, not a state manager. Every consumer re-renders."
- "URL state is the most underused tool. If users bookmark it, it belongs in the URL."
- "Optimistic updates: snapshot, apply, rollback on error, invalidate on settle."
- "RTK + Immer: write mutations, get immutability — but never mutate AND return."
- "Zustand selectors: select primitives or use shallow. Inline objects are a re-render bug."
- "React Hook Form is uncontrolled — values live in the DOM, not React state. 50-field forms need this."
- "staleTime controls freshness window. gcTime controls garbage collection. They are different."
- "Atoms (Jotai) win for fine-grained derived state graphs. Stores win for most apps."
