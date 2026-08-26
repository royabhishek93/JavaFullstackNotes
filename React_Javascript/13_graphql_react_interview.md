# GraphQL + React: 15-YOE Architect Interview Prep

> Target: Senior / Staff / Architect-level interviews. Apollo Client v3+, TypeScript, React 18+.

---

## 1. Big Picture: ASCII Diagrams

### 1.1 GraphQL Request Lifecycle

```
  React Component
       │
       │  useQuery(GET_USER)
       ▼
  ┌─────────────────────────────────────────────┐
  │           Apollo Client                     │
  │                                             │
  │  1. Check Cache Policy                      │
  │     cache-first → hit? → return             │
  │     network-only → skip cache               │
  │     cache-and-network → return stale +      │
  │                          fetch in bg        │
  │                                             │
  │  2. Query Deduplication                     │
  │     Same query in-flight? → reuse promise  │
  │                                             │
  │  3. InMemoryCache lookup                    │
  │     __typename + id → normalize & lookup   │
  └──────────────┬──────────────────────────────┘
                 │ cache miss / network-only
                 ▼
  ┌─────────────────────────────────────────────┐
  │         Apollo Link Chain                   │
  │                                             │
  │  AuthLink → RetryLink → HttpLink            │
  │  (headers)   (retries)  (fetch POST)        │
  └──────────────┬──────────────────────────────┘
                 │
                 ▼
  ┌─────────────────────────────────────────────┐
  │        GraphQL Server (e.g. NestJS)         │
  │                                             │
  │  Schema validation → Resolver tree          │
  │  DataLoader batching (solves N+1)           │
  │  Partial responses (data + errors[])        │
  └──────────────┬──────────────────────────────┘
                 │  JSON response
                 ▼
  Apollo Client writes to InMemoryCache
  → React component re-renders with new data
```

### 1.2 Apollo InMemoryCache — Normalized Cache Structure

```
  Raw response:
  {
    user: {
      __typename: "User",
      id: "u1",
      name: "Alice",
      posts: [
        { __typename: "Post", id: "p1", title: "Hello" }
      ]
    }
  }

  After normalization in InMemoryCache:
  ┌──────────────────────────────────────┐
  │  ROOT_QUERY                          │
  │  ├── user({"id":"u1"}) → ref "User:u1" │
  │                                      │
  │  User:u1                             │
  │  ├── __typename: "User"              │
  │  ├── id: "u1"                        │
  │  ├── name: "Alice"                   │
  │  └── posts → [ref "Post:p1"]         │
  │                                      │
  │  Post:p1                             │
  │  ├── __typename: "Post"              │
  │  ├── id: "p1"                        │
  │  └── title: "Hello"                  │
  └──────────────────────────────────────┘

  Key insight: any query that returns User:u1 shares
  the SAME cache entry. Update once → all components
  using that entity re-render automatically.
```

### 1.3 Cache Update Strategies — Decision Tree

```
  After mutation completes...
         │
         ▼
  Does the mutation return the updated entity?
         │
    YES ─┤─── Apollo auto-updates via normalization ✓
         │    (if same __typename + id in response)
         │
    NO ──┤
         │
         ▼
  Is the change simple (field update on known entity)?
         │
    YES ─┤─── cache.modify() ← preferred
         │
    NO ──┤
         │
         ▼
  Is it a list (add/remove item)?
         │
    YES ─┤─── cache.modify() with evict or
         │    writeFragment + readQuery + writeQuery
         │
    NO ──┤
         │
         ▼
  Is data hard to derive locally?
         │
    YES ─┤─── refetchQueries (last resort, network hit)
         │
    NO ──┘
```

---

## 2. Conversational Interview Script — 15-YOE Architect Voice

### "Walk me through your decision: REST vs GraphQL."

> "At scale I treat this as a cost-benefit analysis, not a dogma fight.
>
> REST wins when you have: a simple CRUD resource model, aggressive HTTP caching (CDN, ETags), a public API where clients are unknown, or a team that lacks GraphQL tooling maturity. HTTP caching alone is a massive operational advantage — you get CDN edge caching for free with GET requests, which GraphQL's POST-everything approach gives up.
>
> GraphQL wins when you have: a heterogeneous client landscape (mobile app vs web vs TV app each needing different shapes), significant over-fetching causing mobile performance issues, rapid frontend iteration where backend changes are a bottleneck, or you need schema-first contracts and type-safe code generation across teams.
>
> The hidden cost of GraphQL is operational: you need DataLoaders to prevent N+1 on the backend, query complexity limits to prevent denial-of-service via deeply nested queries, persisted queries for production security, and your team needs to understand cache normalization deeply or you'll have subtle stale-data bugs in production.
>
> In my last architecture, we ran both: REST for public read-heavy endpoints behind a CDN, GraphQL for the authenticated dashboard where 12 different product teams each needed different data shapes. The GraphQL layer sat on top of our existing REST microservices as a BFF (Backend For Frontend)."

### "How does Apollo Client cache normalization work in production?"

> "Apollo's InMemoryCache stores entities by a cache key, defaulting to `__typename:id`. So `User:u1` is a single entry shared across every query that touches that user. This means if a mutation returns an updated User object, every component subscribed to any query containing that user re-renders automatically — you get UI consistency for free.
>
> The production gotcha is entities without an `id` field, or where the unique identifier has a different name. If you have a `Product` type with a `sku` field instead of `id`, you must configure `keyFields: ['sku']` in your InMemoryCache typePolicies, otherwise Apollo generates a non-normalized key and you lose the shared-reference benefit.
>
> The second gotcha is paginated lists. Apollo by default merges all pages of the same query into one cache entry. If you're doing cursor pagination, you need `keyArgs` to create separate cache entries per set of arguments. I've seen production bugs where page 2 results overwrote page 1 because keyArgs wasn't configured."

### "What's your take on graphql-codegen?"

> "Non-negotiable at scale. The schema is the contract; codegen enforces that contract at compile time. You define your `.graphql` files, run codegen, and get typed hooks — `useGetUserQuery`, `useCreateOrderMutation` — where TypeScript knows exactly what fields are available and what variables are required.
>
> The operational win is that when a backend team changes a schema field, every frontend query that referenced that field fails the TypeScript build. You catch breaking changes in CI, not in production. Without codegen, you're doing string-based query writing with `any`-typed responses — that's a 15-year-old JavaScript antipattern.
>
> In CI I run `graphql-codegen --check` to verify generated types are up-to-date with the committed `.graphql` files. Any drift fails the build."

---

## 3. Scenario Q&As (8 Production Scenarios)

### Scenario 1: Dashboard loads too slowly — 8 separate REST calls

**Interviewer**: "Our React dashboard fires 8 REST API calls on mount. Users report it feels slow. How do you approach this?"

**Answer**: "First, I profile — are these calls sequential or parallel? Parallel is often fine. The real pain is sequential waterfalls: Component A loads, then triggers Component B's fetch, then Component C's. That's a 'request waterfall' and REST makes it easy to create accidentally.

GraphQL with a single query solves the waterfall because you declare the full data shape upfront. One network round-trip, server resolves in parallel where possible. But before migrating, I'd check: are these 8 endpoints cacheable at the CDN? If so, REST + aggressive caching might actually outperform GraphQL.

If we go GraphQL, I'd co-locate data requirements with components using fragments, then compose them into a single root query at the page level. This is the 'fragment colocation' pattern — each component owns its data requirements, but they're batched into one network request."

---

### Scenario 2: Stale data after mutation

**Interviewer**: "After a user updates their profile, the header still shows the old name for a few seconds. How do you fix this?"

**Answer**: "This is a cache consistency issue. Apollo normalized the user in cache as `User:u1`. If the mutation's response included the updated `User` object with the same `id`, Apollo would auto-update the cache and the header would re-render immediately.

The root cause is usually one of two things: (1) The mutation response doesn't return the updated fields. Fix: change the mutation to return `{ id, name, avatar }`. (2) The cache key isn't normalized correctly. Fix: verify `keyFields` config.

If the mutation can't return the updated entity, I'd use `cache.modify` to surgically update the cached User:u1 entry. I'd avoid `refetchQueries` here — it's a full network round-trip for a field we already know the new value of."

---

### Scenario 3: Optimistic UI for a 'Like' button

**Interviewer**: "We have a Like button. Users click it and wait 300ms for the server. Product wants instant feedback. How?"

**Answer**: "Apollo's `optimisticResponse` was built exactly for this. You provide the expected response shape alongside the mutation. Apollo writes it to cache immediately, component re-renders, user sees the like. When the real response comes back, Apollo reconciles. If the server returns an error, Apollo automatically rolls back to the pre-mutation cache state.

The key is matching the optimistic response shape exactly to what the real response would be — same `__typename`, same fields. If they don't match, you get a brief flash as the real response overwrites the optimistic one."

---

### Scenario 4: Infinite scroll with cursor pagination

**Interviewer**: "We need infinite scroll. How do you implement pagination with Apollo?"

**Answer**: "Cursor-based pagination with `fetchMore` and a custom `merge` function in typePolicies.

The critical config is `keyArgs`. Without it, each page's arguments (cursor, limit) would create separate cache entries or worse, overwrite each other. I set `keyArgs: false` to tell Apollo 'all pages of this query belong to the same list' and then provide a `merge` function that concatenates the incoming edges onto the existing ones.

For the UI, `fetchMore` returns a new observable. I attach it to an IntersectionObserver on the last list item. When it enters the viewport, call `fetchMore({ variables: { cursor: pageInfo.endCursor } })`. Apollo merges the result and the component re-renders with the extended list.

For offset pagination, same pattern but `keyArgs: ['search', 'filter']` — include only the stable filter args, not the offset itself."

---

### Scenario 5: Real-time notifications

**Interviewer**: "We need real-time notifications when a new order comes in. GraphQL subscriptions vs polling?"

**Answer**: "For order notifications specifically — high-value, user-visible — subscriptions are the right call. The latency matters: a 5-second polling interval means users wait up to 5 seconds, which feels broken for 'you have a new order'.

Implementation: `useSubscription` hook with the Apollo WebSocket link (`graphql-ws` transport). The subscription pushes a notification object; I write it into cache using the subscription's `onData` callback and cache.modify, or use a local state update to trigger a notification toast.

For lower-stakes real-time needs — dashboard metrics, activity feeds — I'd actually keep polling with `pollInterval: 30000`. WebSockets add operational complexity: you need sticky sessions or a pub/sub broker behind your GraphQL server (Redis, etc.), connection management, reconnection logic. For data that's fine being 30 seconds stale, polling is simpler and cheaper."

---

### Scenario 6: Multiple teams, schema ownership

**Interviewer**: "We have 5 backend teams each owning different services. How do you structure the GraphQL layer?"

**Answer**: "Apollo Federation. Each team owns a subgraph — their own schema, their own GraphQL service. The Apollo Router (or Gateway) composes them into a supergraph at runtime. Teams deploy independently; the router handles query planning across subgraphs.

The Federation key is entity references. The Orders subgraph can reference `User` (owned by the Users subgraph) via `@key` directives. When a query spans both, the router federates: fetches from Users subgraph, passes the key to Orders subgraph.

Without Federation, you'd have a monolithic schema with a single team as a bottleneck. Federation is the microservices pattern applied to GraphQL."

---

### Scenario 7: Security — preventing abusive queries

**Interviewer**: "GraphQL lets clients request any depth of nesting. How do you prevent abuse?"

**Answer**: "Three layers of defense: (1) Query depth limiting — reject queries deeper than N levels. `graphql-depth-limit` library. Set depth limit based on your actual deepest legitimate query. (2) Query complexity analysis — assign a cost to each field, reject queries exceeding a total cost budget. `graphql-validation-complexity` or custom plugins. (3) Persisted queries in production — clients only send a query hash, server maps it to an allowlisted query. Unknown queries are rejected. This is the strongest protection and also improves performance (small hash instead of full query over the wire).

I'd also add rate limiting at the HTTP layer and introspection disabled in production (otherwise you're advertising your full schema to attackers)."

---

### Scenario 8: Migrating from REST to GraphQL incrementally

**Interviewer**: "We have a large REST API. How do you migrate without a big bang?"

**Answer**: "Strangler Fig pattern. Stand up a GraphQL BFF layer that initially proxies to your existing REST endpoints. Frontend teams start writing GraphQL queries; the resolvers call REST under the hood. No REST service needs to change.

Over time, you migrate resolvers one by one to call data sources directly (database, gRPC, etc.), bypassing REST. The frontend never knows the difference.

The key benefit: you get all the GraphQL tooling wins (type safety, codegen, fragment colocation) immediately, without requiring any backend changes. You can migrate resolvers to native GraphQL at your own pace, driven by performance needs or team capacity.

I've done this migration at two companies. The BFF approach also lets you implement DataLoader batching in the GraphQL layer to fix N+1 issues caused by the REST services, without touching those services."

---

## 4. Advanced Scenario Q&As (4 Scenarios)

### Advanced 1: Fragment Colocation — The Relay Model

**Interviewer**: "What is fragment colocation and why does it matter at scale?"

**Answer**: "Fragment colocation means each component declares exactly the data it needs, co-located with the component file. The parent composes fragments into a query but doesn't need to know what data the children need.

Without it: the parent query over-fetches to cover all possible children's needs, or children make separate queries causing waterfalls. With it: data requirements are encapsulated. When a child component's data needs change, you update its fragment — the parent query updates automatically via composition, with no parent file changes needed.

At scale this matters enormously. In a large app, you might have 50 components on a page. Without colocation, someone has to maintain a giant page-level query and know what every component needs. With colocation, it's self-documenting and safe to refactor.

The Relay framework enforces this pattern. Apollo supports it through manual discipline and conventions. I enforce it via code review guidelines and sometimes lint rules checking that `useFragment` / component fragments are co-located."

---

### Advanced 2: Apollo Error Policies — Partial Data

**Interviewer**: "GraphQL can return both `data` and `errors` in the same response. How do you handle this?"

**Answer**: "This is GraphQL's partial error model — a resolver can fail for one field without failing the entire query. By default Apollo treats any `errors` array as a failure and puts data in the `error` field, discarding partial data.

Apollo's `errorPolicy` option changes this behavior. With `errorPolicy: 'all'`, Apollo returns both `data` and `errors` to the component. This lets you render the successfully-fetched parts while showing error states for the failed parts.

In production, I use this for non-critical fields. For a user profile page, if the main user data succeeds but the `recentActivity` resolver fails, I'd rather show the profile with a 'Could not load activity' message than show nothing. `errorPolicy: 'all'` enables this.

The component then checks both: render `data.user.name` normally, render `data.user.recentActivity` with a fallback, check `errors` array to log or show inline warnings. This is more complex UI logic but produces a much better user experience than a full page error."

---

### Advanced 3: Apollo Client vs urql vs React Query for GraphQL

**Interviewer**: "Why Apollo Client and not React Query or urql?"

**Answer**: "It depends on what you're optimizing for. Let me give you the honest trade-offs.

React Query is excellent for REST but its GraphQL support is bolt-on — you write fetch functions, React Query handles caching but as opaque blobs (no normalization). You don't get the auto-consistency across components that Apollo's normalized cache provides. For most CRUD apps with simple data shapes, React Query's simplicity wins. When you have complex relational data where the same entity appears in multiple queries, lack of normalization becomes painful.

urql is the 'lightweight Apollo' — normalized cache (with Graphcache plugin), smaller bundle, more modular. I'd choose urql for a performance-sensitive application where bundle size matters, or a smaller team that finds Apollo's API surface overwhelming. Graphcache has better defaults in some ways — optimistic updates are simpler.

Apollo Client wins for: large teams needing ecosystem maturity, Federation support, DevTools quality, and Apollo Studio integration. The normalized cache is the most battle-tested implementation. The downsides: bundle size (~32kb min+gzip), a lot of API surface area, occasional confusing cache behavior.

My default recommendation at architect level: Apollo for complex applications with multiple teams, urql for performance-critical single-team projects, React Query if you're mostly REST and adding GraphQL endpoints incrementally."

---

### Advanced 4: DataLoader and the N+1 Problem

**Interviewer**: "Explain the GraphQL N+1 problem and how DataLoader solves it."

**Answer**: "The N+1 problem happens because GraphQL resolvers are called independently for each item in a list. If you fetch 10 posts and each post's resolver fetches its author via `db.findUser(post.authorId)`, you execute 1 query for posts + 10 queries for authors = 11 queries (1 + N).

DataLoader solves this with batching and caching. You define a batch function: given an array of user IDs, return users in the same order. DataLoader collects all calls to `load(userId)` within a single event loop tick, then calls your batch function once with all IDs. Result: 1 query for posts + 1 batch query for all 10 authors = 2 queries.

DataLoader also caches within a request: if two posts have the same author, the author is only fetched once. This cache is per-request (created anew each time in the GraphQL context), not global — important for data isolation between users.

Implementation: create a DataLoader in the GraphQL context factory (runs once per request), use it in resolvers via `context.userLoader.load(authorId)`. Every resolver gets the same loader instance for that request, so batching works across the resolver tree.

This is a backend concern but I always ask backend teams about DataLoader usage before recommending GraphQL adoption. Without it, you're often worse than REST on database load."

---

## 5. Senior Trap Questions (6 Traps)

### Trap 1: "GraphQL solves all over-fetching problems"

**The trap**: Saying yes, GraphQL eliminates over-fetching.

**Why it's a trap**: GraphQL shifts over-fetching responsibility to the client. If you write a page-level query that fetches all fields "just in case" — which developers do without discipline — you're over-fetching just as badly as REST, just in a different place. The solution is fragment colocation: each component requests only what it needs. Without that discipline, GraphQL queries balloon.

**Correct answer**: "GraphQL gives you the *capability* to eliminate over-fetching, but it requires fragment colocation discipline. Without it, developers write kitchen-sink queries at the page level and you've just moved the over-fetching from the server to the client. I enforce colocation via code review and encourage Relay-style fragments. Apollo DevTools 'Operations' tab is useful for auditing — if a query returns 50 fields and only 10 appear in the component, you have colocation debt."

---

### Trap 2: "We should call refetchQueries after every mutation for consistency"

**The trap**: Nodding along that refetchQueries is the right default.

**Why it's a trap**: `refetchQueries` makes extra network requests. If you have 10 active queries and a mutation touches one entity, you don't need to refetch 10 queries — you need to update one cache entry. Using refetchQueries as a default is wasteful and makes your app feel slower (UI doesn't update until the refetch completes).

**Correct answer**: "refetchQueries is a sledgehammer. I use it as a last resort when I genuinely can't derive the new state locally. For most mutations, the right approach is: (1) If the mutation returns the updated entity, Apollo auto-updates via normalization. (2) If not, use `cache.modify` to surgically update the specific cache entry. (3) For optimistic UX, use `optimisticResponse`. refetchQueries makes sense when you're adding an item to a paginated list that uses server-side sorting — you can't know which page the new item belongs on without asking the server."

---

### Trap 3: "Apollo InMemoryCache is just a key-value store"

**The trap**: Agreeing that it's a simple map of query string → result.

**Why it's a trap**: It's a normalized entity store. Entities are stored by `__typename:id`, not by query. This is the fundamental design that enables automatic UI consistency — update one entity, all queries containing it re-render. A simple key-value cache would require manual cache invalidation after every mutation.

**Correct answer**: "InMemoryCache is a normalized entity graph. The canonical key is `__typename + id` — configurable via `keyFields`. This normalization is what makes Apollo's cache powerful: any two queries that return the same `User:u1` share one cache entry. A mutation that updates `User:u1` automatically updates every component using any query containing that user. Without normalization, you'd need explicit query invalidation, which is fragile and easy to miss. The `ROOT_QUERY` object maps query+args to entity references; the actual data lives in the entity slots."

---

### Trap 4: "Calling useQuery in every child component causes N+1 fetches"

**The trap**: Agreeing this is a problem and recommending prop-drilling or lifting state.

**Why it's a trap**: Apollo deduplicates identical in-flight queries within the same render cycle. If 10 child components each call `useQuery(GET_USER, { variables: { id: '1' } })` simultaneously, Apollo makes one network request and shares the result. Additionally, once the cache is warm, all 10 components read from cache with zero network requests.

**Correct answer**: "Apollo handles this via query deduplication. Identical queries (same operation name + variables) that are in-flight simultaneously are merged into one network request. And after the first render, they all read from the normalized cache. So using useQuery in child components is actually fine — it's a feature, not a bug. This is what makes component-level data fetching viable. The pattern to avoid is sequential waterfalls, where Component B's useQuery only runs after Component A's data arrives — that's when you should lift the query up or use parallel queries."

---

### Trap 5: "GraphQL subscriptions should replace all polling"

**The trap**: Agreeing that subscriptions are always superior and recommending migrating all polls to subscriptions.

**Why it's a trap**: WebSocket subscriptions add significant operational complexity. You need: a WebSocket-capable server, connection management and reconnection logic, potentially sticky sessions or a pub/sub broker (Redis Pub/Sub, etc.) for horizontal scaling, and client-side handling of connection state. For data that updates every 30+ seconds, a simple `pollInterval` is dramatically simpler and often more reliable.

**Correct answer**: "Subscriptions are the right tool when low latency genuinely matters — chat, live collaborative editing, trading feeds. For dashboard metrics refreshed every 30 seconds, or activity feeds, polling is operationally simpler and the user experience difference is imperceptible. My rule of thumb: if the acceptable staleness is more than 5-10 seconds, poll. If users expect sub-second updates, subscribe. I've seen engineers introduce WebSocket infrastructure for a dashboard that refreshes every minute — that's over-engineering that adds a production failure mode for no user benefit."

---

### Trap 6: "You should use cache-and-network everywhere for freshness"

**The trap**: Agreeing that `cache-and-network` is the safe default.

**Why it's a trap**: `cache-and-network` causes two renders per query fetch (one for cached data, one for network data). At scale this means double renders across your component tree on every navigation. It also defeats the purpose of caching for read-heavy views where data doesn't change often. Overusing it is a performance antipattern that developers reach for when they're not confident about cache updates.

**Correct answer**: "cache-and-network is a UX optimization for specific cases: screens where showing slightly stale data briefly is acceptable, but you want freshness ASAP. The right default is `cache-first` — return cached data immediately, only fetch if there's a cache miss. This gives instant navigations back to previously visited screens. Use `network-only` for critical data like payment confirmation screens where stale data is dangerous. The real goal is to make cache updates correct after mutations, so you never need `cache-and-network` as a crutch for stale data."

---

## 6. Production TypeScript/React Code Examples

### 6.1 Apollo Client Setup with TypeScript

```typescript
// src/apollo/client.ts
import { ApolloClient, InMemoryCache, createHttpLink, from } from '@apollo/client';
import { setContext } from '@apollo/client/link/context';
import { onError } from '@apollo/client/link/error';

const httpLink = createHttpLink({ uri: '/graphql' });

const authLink = setContext((_, { headers }) => ({
  headers: { ...headers, authorization: `Bearer ${getToken()}` },
}));

const errorLink = onError(({ graphQLErrors, networkError }) => {
  graphQLErrors?.forEach(({ message, path }) =>
    console.error(`[GraphQL error] ${message} at ${path}`)
  );
  if (networkError) console.error(`[Network error] ${networkError}`);
});

export const client = new ApolloClient({
  link: from([errorLink, authLink, httpLink]),
  cache: new InMemoryCache({
    typePolicies: {
      Product: { keyFields: ['sku'] },       // non-id key
      Query: {
        fields: {
          products: { keyArgs: ['filter'], merge: false },
        },
      },
    },
  }),
});
```

---

### 6.2 codegen.yml — Type-safe Hook Generation

```yaml
# codegen.yml
schema: http://localhost:4000/graphql
documents: 'src/**/*.graphql'
generates:
  src/generated/graphql.ts:
    plugins:
      - typescript
      - typescript-operations
      - typescript-react-apollo
    config:
      withHooks: true
      withComponent: false
      withResultType: true
      scalars:
        DateTime: string
        UUID: string
```

```bash
# package.json script
"codegen": "graphql-codegen --config codegen.yml",
"codegen:watch": "graphql-codegen --config codegen.yml --watch",
"codegen:check": "graphql-codegen --config codegen.yml --check"
```

---

### 6.3 Fragment Colocation Pattern

```typescript
// src/components/UserCard/UserCard.graphql
fragment UserCard_user on User {
  id
  name
  avatarUrl
  email
}
```

```typescript
// src/components/UserCard/UserCard.tsx
import { UserCard_UserFragment } from '@/generated/graphql';

interface Props { user: UserCard_UserFragment; }

export const UserCard = ({ user }: Props) => (
  <div>
    <img src={user.avatarUrl} alt={user.name} />
    <h3>{user.name}</h3>
    <p>{user.email}</p>
  </div>
);
```

```typescript
// src/pages/TeamPage.graphql
query GetTeam($id: ID!) {
  team(id: $id) {
    id
    name
    members { ...UserCard_user }
  }
}
```

---

### 6.4 useQuery with Loading/Error States (typed)

```typescript
import { useGetTeamQuery } from '@/generated/graphql';

const TeamPage = ({ teamId }: { teamId: string }) => {
  const { data, loading, error } = useGetTeamQuery({
    variables: { id: teamId },
    fetchPolicy: 'cache-first',
    errorPolicy: 'all',   // allow partial data
  });

  if (loading) return <TeamSkeleton />;
  if (error && !data) return <ErrorState message={error.message} />;

  return (
    <>
      {error && <InlineWarning errors={error.graphQLErrors} />}
      <TeamView team={data!.team} />
    </>
  );
};
```

---

### 6.5 useMutation with Optimistic Response

```typescript
import { useLikePostMutation } from '@/generated/graphql';

const LikeButton = ({ post }: { post: { id: string; likeCount: number; liked: boolean } }) => {
  const [likePost] = useLikePostMutation();

  const handleLike = () => likePost({
    variables: { postId: post.id },
    optimisticResponse: {
      likePost: {
        __typename: 'Post',
        id: post.id,
        likeCount: post.likeCount + 1,
        liked: true,
      },
    },
  });

  return <button onClick={handleLike}>{post.likeCount} ♥</button>;
};
```

---

### 6.6 cache.modify — Surgical Cache Update

```typescript
const [createComment] = useCreateCommentMutation({
  update(cache, { data }) {
    if (!data?.createComment) return;
    cache.modify({
      id: cache.identify({ __typename: 'Post', id: postId }),
      fields: {
        comments(existing = []) {
          const newRef = cache.writeFragment({
            data: data.createComment,
            fragment: CommentFragment,
          });
          return [...existing, newRef];
        },
        commentCount: (count: number) => count + 1,
      },
    });
  },
});
```

---

### 6.7 Cursor Pagination with fetchMore

```typescript
const { data, fetchMore, loading } = useGetPostsQuery({
  variables: { first: 20 },
});

const loadMore = () =>
  fetchMore({ variables: { after: data?.posts.pageInfo.endCursor } });

// typePolicies config for correct merging:
// Query: { fields: { posts: { keyArgs: ['filter'],
//   merge(existing, incoming) {
//     return { ...incoming, edges: [...(existing?.edges ?? []), ...incoming.edges] };
//   }}}}
```

---

### 6.8 useSubscription — Real-time Notifications

```typescript
import { useNewOrderSubscription } from '@/generated/graphql';

const OrderNotificationBell = () => {
  const [unread, setUnread] = useState(0);

  useNewOrderSubscription({
    onData({ data: { data } }) {
      if (data?.newOrder) {
        setUnread(n => n + 1);
        toast.success(`New order: ${data.newOrder.id}`);
      }
    },
  });

  return <Bell badge={unread} />;
};
```

---

### 6.9 Apollo Client Subscription Link Setup (graphql-ws)

```typescript
import { GraphQLWsLink } from '@apollo/client/link/subscriptions';
import { createClient } from 'graphql-ws';
import { split, getMainDefinition } from '@apollo/client';

const wsLink = new GraphQLWsLink(createClient({
  url: 'wss://api.example.com/graphql',
  connectionParams: () => ({ authorization: `Bearer ${getToken()}` }),
}));

const splitLink = split(
  ({ query }) => {
    const def = getMainDefinition(query);
    return def.kind === 'OperationDefinition' && def.operation === 'subscription';
  },
  wsLink,
  from([errorLink, authLink, httpLink])
);
```

---

### 6.10 DataLoader on the Backend (NestJS context)

```typescript
// src/graphql/context.ts
import DataLoader from 'dataloader';
import { UserService } from '../user/user.service';

export const createContext = (userService: UserService) => ({
  userLoader: new DataLoader<string, User>(async (ids) => {
    const users = await userService.findByIds([...ids]);
    return ids.map(id => users.find(u => u.id === id) ?? new Error(`User ${id} not found`));
  }),
});

// In resolver:
@ResolveField('author', () => User)
async getAuthor(@Parent() post: Post, @Context() ctx: AppContext) {
  return ctx.userLoader.load(post.authorId);  // batched!
}
```

---

## 7. Interview Cheat Sheet

### REST vs GraphQL — One-line Decision

| Signal | Choose |
|--------|--------|
| Public API, CDN caching needed | REST |
| Mobile clients, bandwidth constrained | GraphQL |
| Multiple clients needing different shapes | GraphQL |
| Simple CRUD, small team | REST |
| Cross-team schema ownership at scale | GraphQL + Federation |

---

### Apollo Cache Quick Reference

| Operation | Use When |
|-----------|----------|
| Mutation returns entity | Auto-update (normalization) |
| Update known field(s) | `cache.modify()` |
| Add item to list | `cache.modify()` + `writeFragment` |
| Can't derive new state locally | `refetchQueries` (last resort) |
| Instant UI feedback | `optimisticResponse` |

---

### Fetch Policy Quick Reference

| Policy | Behavior | Use Case |
|--------|----------|----------|
| `cache-first` | Cache → network on miss | Default, navigating back |
| `network-only` | Always network | Payment confirm, auth |
| `cache-only` | Cache or error | Offline-first |
| `no-cache` | Network, don't store | Sensitive data |
| `cache-and-network` | Cache immediately + bg network | Stale-while-revalidate UX |

---

### Error Policies

| Policy | Behavior |
|--------|----------|
| `none` (default) | Any error → `error` field, no `data` |
| `all` | Returns both `data` and `errors` |
| `ignore` | Returns `data`, ignores errors |

Use `all` for partial-failure tolerance on non-critical fields.

---

### Key Apollo TypePolicies Patterns

```typescript
// Non-id primary key
Product: { keyFields: ['sku'] }

// Composite key
OrderItem: { keyFields: ['orderId', 'productId'] }

// Pagination — separate cache per filter, merge pages
Query: {
  fields: {
    products: {
      keyArgs: ['filter'],              // separate cache per filter
      merge(existing, incoming, { args }) {  // accumulate pages
        return { ...incoming, edges: [...(existing?.edges ?? []), ...incoming.edges] };
      }
    }
  }
}
```

---

### The 5 Trap Answer Starters

1. **"GraphQL solves all over-fetching"** → "GraphQL gives the capability, but fragment colocation discipline is required..."
2. **"refetchQueries after every mutation"** → "refetchQueries is a last resort; cache.modify is the right tool for..."
3. **"Apollo cache is key-value"** → "It's a normalized entity graph, keyed by __typename + id..."
4. **"useQuery in children causes N+1 fetches"** → "Apollo deduplicates in-flight queries; the real risk is sequential waterfalls..."
5. **"Subscriptions replace polling"** → "Subscriptions are for sub-5s latency requirements; polling is operationally simpler for..."

---

### graphql-codegen Workflow

```
1. Write .graphql files alongside components
2. Run: npx graphql-codegen --config codegen.yml
3. Import typed hooks: useGetUserQuery, useCreatePostMutation
4. CI check: graphql-codegen --check (fails if out of sync)
5. Never write manual TypeScript types for GraphQL responses
```

---

### Apollo DevTools Checklist (use in interviews to show depth)

- **Operations tab**: Inspect active queries, variables, cache keys
- **Cache tab**: Browse normalized entity store, verify keyFields
- **Mutations**: Watch optimistic writes and real response reconciliation
- **Network**: Identify query deduplication, check for waterfalls

---

### Federation Architecture (for "how do you scale GraphQL?")

```
Client
  │  single GraphQL endpoint
  ▼
Apollo Router (Supergraph)
  │  query planning, entity resolution
  ├── Users Subgraph (owns User type)
  ├── Orders Subgraph (references User via @key)
  ├── Inventory Subgraph
  └── Notifications Subgraph
```

Each team: independent schema, independent deploy, `@key` for cross-subgraph entity references.

---

### urql vs Apollo vs React Query — 3-Line Summary

- **Apollo Client**: Normalized cache, best ecosystem, largest bundle, best for complex relational data across large teams
- **urql + Graphcache**: Normalized cache, smaller bundle, simpler API, good for performance-sensitive apps
- **React Query**: Best DX for REST, GraphQL is first-class but not normalized, choose when REST > GraphQL in your stack

---

### Questions to Ask the Interviewer (signal architect maturity)

1. "How are you handling the N+1 problem today — DataLoaders, or batching at a different layer?"
2. "Do you have query complexity limits in place? What's your worst offending query depth?"
3. "How do you handle schema versioning — do you deprecate fields or version the endpoint?"
4. "What's your cache hit rate in production? Do you have Apollo Studio or similar observability?"
5. "Are you using persisted queries in production, or sending full query strings?"

---

*Last updated: 2026-08 | Apollo Client v3 | graphql-ws | graphql-codegen v5*
