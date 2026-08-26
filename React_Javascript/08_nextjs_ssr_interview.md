# Next.js / SSR — 15-YOE Senior Engineer Interview Prep

---

## 1. Big Picture: Rendering Strategy Decision Tree

```
START: What kind of page is this?
│
├─► Is the content the SAME for every user and changes infrequently?
│       │
│       ├─► YES — Can I tolerate stale data for hours/days?
│       │         │
│       │         ├─► YES → SSG (Static Site Generation)
│       │         │         export const revalidate = false | getStaticProps
│       │         │         Best for: marketing, blog, docs
│       │         │
│       │         └─► NO, but OK with seconds/minutes of staleness
│       │                   │
│       │                   └─► ISR (Incremental Static Regeneration)
│       │                         revalidate = 60 | on-demand ISR
│       │                         Best for: product pages, news, pricing
│       │
├─► Is content PER-USER or depends on request (cookies, auth, live data)?
│       │
│       ├─► YES — Does SEO matter for this page?
│       │         │
│       │         ├─► YES → SSR (Server-Side Rendering)
│       │                   getServerSideProps | async Server Component (no cache)
│       │                   Best for: user dashboards with SEO, search results
│       │         │
│       │         └─► NO → CSR (Client-Side Rendering)
│       │                   useEffect + fetch | React Query | SWR
│       │                   Best for: authenticated dashboards, admin UIs
│       │
├─► Is the page highly interactive with real-time updates?
│       │
│       └─► YES → Hybrid: SSR/SSG shell + CSR for dynamic parts
│                   Streaming with Suspense for progressive loading
│
└─► Do I have a mix of static structure + dynamic data?
        │
        └─► YES → React Server Components (RSC) + Client Components
                  Static layout in Server Component, interactive parts
                  wrapped in "use client" Client Components

RENDERING STRATEGY SUMMARY:
┌─────────────┬──────────────┬──────────────┬──────────────┬──────────────┐
│   Strategy  │   When HTML  │  Data Fresh  │  JS to Client│  Best For    │
├─────────────┼──────────────┼──────────────┼──────────────┼──────────────┤
│ CSR         │ Browser      │ On demand    │ Full bundle  │ Dashboards   │
│ SSR         │ Per request  │ Per request  │ Hydration JS │ User pages   │
│ SSG         │ Build time   │ Stale        │ Hydration JS │ Marketing    │
│ ISR         │ Background   │ Revalidated  │ Hydration JS │ Content site │
│ RSC         │ Server+stream│ Per request  │ Near-zero JS │ Data-heavy   │
└─────────────┴──────────────┴──────────────┴──────────────┴──────────────┘
```

---

## 2. Conversational Interview Script

### "Walk me through how you think about rendering strategies in Next.js"

> "When I join a project or start a new feature, I first ask: who sees this page and how often does the data change? That answer drives everything.
>
> For a marketing homepage or blog — content is the same for everyone, updates weekly — SSG is the obvious choice. Build once, serve from CDN edge nodes globally. Sub-millisecond TTFB. For product pages that update pricing or inventory daily, ISR with a 60-second revalidate gives us the CDN speed with freshness guarantees we can control.
>
> The moment content becomes per-user — think a logged-in dashboard or a search results page that depends on query params — I move to SSR or RSC with no-cache. But I'm careful here. SSR adds server latency on every request, so I ask: does this page need SEO? If it's behind auth, probably not, and I'll lean CSR with React Query for better perceived performance through client-side caching and optimistic updates.
>
> With App Router, my default is now Server Components for the data-fetching layer and Client Components only at the leaves where interactivity lives. This gives me zero-bundle JS for the static structure and server-side data access without an extra API hop."

### "How do you explain React Server Components to a senior who hasn't used App Router?"

> "RSC is a new execution model, not just an optimization. A Server Component runs exclusively on the server — it can await database calls, read files, access secrets — and sends its rendered output to the client as a serialized payload called the RSC payload. No JavaScript for that component ships to the browser. Zero bundle contribution.
>
> The mental model shift is: we used to have one JS bundle that ran everywhere. Now the component tree is split. Server Components form the skeleton — they fetch data, they render HTML structure. Client Components, marked with 'use client', are islands of interactivity. They hydrate and handle events.
>
> The constraint that trips people up: Server Components cannot use hooks, cannot attach event handlers, cannot access browser APIs. They're async functions that return JSX. That's it. If you need useState or onClick, that component or its boundary must be a Client Component."

---

## 3. Scenario-Based Q&As (Production Context)

### Q1: You're building an e-commerce product listing page. Thousands of products, prices update daily, SEO is critical. What rendering strategy?

**Answer:**
ISR with on-demand revalidation is the right call. At build time, pre-render the top N (say, 1000) most-visited product pages statically. Set `revalidate = 3600` (1 hour) as a baseline. When prices update in the CMS or ERP system, trigger on-demand ISR via a webhook to `revalidateTag('products')` or `revalidatePath('/products/[id]')`. This gives CDN-speed TTFB for SEO crawlers while keeping prices reasonably fresh. For inventory ("only 2 left") that needs real-time accuracy, overlay that specific piece as a Client Component that fetches from an edge API route.

```typescript
// app/products/[id]/page.tsx
import { notFound } from 'next/navigation'

export const revalidate = 3600 // hourly baseline

export async function generateStaticParams() {
  const products = await fetchTopProducts(1000)
  return products.map(p => ({ id: p.id }))
}

export default async function ProductPage({ params }: { params: { id: string } }) {
  const product = await fetch(`${process.env.API_URL}/products/${params.id}`, {
    next: { tags: [`product-${params.id}`] }
  }).then(r => r.json())

  if (!product) notFound()
  return <ProductDetail product={product} />
}
```

### Q2: A dashboard page loads slowly. Users are seeing 3-4 second blank screens. How do you fix it?

**Answer:**
The blank screen suggests either SSR blocking on slow data, or CSR waiting for JS bundle + data waterfall. I'd audit the data dependencies. With App Router, I'd convert to Streaming with Suspense:

```typescript
// app/dashboard/page.tsx
import { Suspense } from 'react'
import { DashboardSkeleton, MetricsSkeleton } from '@/components/skeletons'

export default function DashboardPage() {
  return (
    <main>
      <h1>Dashboard</h1>
      <Suspense fallback={<MetricsSkeleton />}>
        <KPIMetrics />   {/* slow — hits analytics DB */}
      </Suspense>
      <Suspense fallback={<DashboardSkeleton />}>
        <RecentOrders /> {/* fast — hits orders DB */}
      </Suspense>
    </main>
  )
}
```

`RecentOrders` unblocks immediately. `KPIMetrics` streams in when ready. The page is interactive in under 500ms. The slow query doesn't block anything else.

### Q3: You need to protect 50 routes behind auth. Where do you put the auth check?

**Answer:**
Middleware is the right layer. It runs at the edge before any rendering, applies to all matched routes, and handles redirects with zero overhead:

```typescript
// middleware.ts
import { NextRequest, NextResponse } from 'next/server'
import { verifyJWT } from '@/lib/auth'

export async function middleware(request: NextRequest) {
  const token = request.cookies.get('auth-token')?.value

  if (!token) {
    return NextResponse.redirect(new URL('/login', request.url))
  }

  const payload = await verifyJWT(token)
  if (!payload) {
    const response = NextResponse.redirect(new URL('/login', request.url))
    response.cookies.delete('auth-token')
    return response
  }

  // Inject user ID into headers for downstream Server Components
  const requestHeaders = new Headers(request.headers)
  requestHeaders.set('x-user-id', payload.userId)
  return NextResponse.next({ request: { headers: requestHeaders } })
}

export const config = {
  matcher: ['/dashboard/:path*', '/account/:path*', '/orders/:path*']
}
```

I avoid putting auth checks in individual Server Components — that's duplicated logic and creates gaps. Middleware is the single enforcement point.

### Q4: Product team wants A/B testing on the homepage hero. No client-side flicker allowed. How?

**Answer:**
Middleware + cookie-based bucketing at the edge. First request assigns the user to a variant, sets a cookie, and rewrites the URL internally. Zero flicker because the HTML is generated server-side for the assigned variant:

```typescript
// middleware.ts (A/B portion)
export async function middleware(request: NextRequest) {
  const bucket = request.cookies.get('ab-hero')?.value ?? assignBucket()
  const url = request.nextUrl.clone()

  if (request.nextUrl.pathname === '/') {
    url.pathname = bucket === 'B' ? '/home-variant-b' : '/home-variant-a'
    const response = NextResponse.rewrite(url)
    response.cookies.set('ab-hero', bucket, { maxAge: 60 * 60 * 24 * 7 })
    return response
  }
}

function assignBucket(): 'A' | 'B' {
  return Math.random() < 0.5 ? 'A' : 'B'
}
```

### Q5: How do you handle a Server Action for a checkout form?

**Answer:**
Server Actions let forms POST directly to server-side logic without an explicit API route. Here's a production pattern including validation and error handling:

```typescript
// app/checkout/actions.ts
'use server'
import { z } from 'zod'
import { revalidatePath } from 'next/cache'
import { redirect } from 'next/navigation'

const CheckoutSchema = z.object({
  addressLine1: z.string().min(1),
  city: z.string().min(1),
  paymentToken: z.string().min(1),
})

export async function submitCheckout(prevState: unknown, formData: FormData) {
  const result = CheckoutSchema.safeParse(Object.fromEntries(formData))
  if (!result.success) {
    return { errors: result.error.flatten().fieldErrors }
  }

  const order = await createOrder(result.data) // DB write
  revalidatePath('/orders')
  redirect(`/orders/${order.id}/confirmation`)
}
```

```typescript
// app/checkout/page.tsx
'use client'
import { useActionState } from 'react'
import { submitCheckout } from './actions'

export default function CheckoutForm() {
  const [state, action, isPending] = useActionState(submitCheckout, null)
  return (
    <form action={action}>
      {/* fields */}
      <button disabled={isPending}>
        {isPending ? 'Processing...' : 'Place Order'}
      </button>
      {state?.errors && <ErrorSummary errors={state.errors} />}
    </form>
  )
}
```

### Q6: When would you use a Route Handler (API route) vs a Server Action vs a Server Component direct fetch?

**Answer:**
The decision matrix I use:

- **Server Component direct fetch**: Default for read operations. Component directly awaits data. No network round-trip. No boilerplate route.
- **Server Action**: Mutations from UI (form submits, button clicks that write data). Progressive enhancement — works without JS. Type-safe — shared between client and server. Use this instead of an API route for most write operations.
- **Route Handler**: When you need an HTTP endpoint consumed by third parties (webhooks, mobile apps, external services), or when you need streaming responses, or SSE. Also for OAuth callbacks and cron job endpoints.

The mistake I see often is reaching for a Route Handler out of habits from Pages Router. In App Router, 90% of what used to be API routes can become Server Actions or Server Component data fetches.

### Q7: Explain the four caches in Next.js App Router and when each is invalidated.

**Answer:**
Next.js has four distinct caching layers, and conflating them causes bugs:

1. **Request Memoization**: Within a single render pass, identical `fetch()` calls are deduplicated. Scope: single request. Automatic, no configuration needed. This means you can fetch user data in multiple Server Components without multiple DB hits.

2. **Data Cache**: The result of `fetch()` is persisted across requests on the server. Opt-out with `cache: 'no-store'`. Invalidate with `revalidateTag()` or `revalidatePath()`. This is where ISR lives — `next: { revalidate: 60 }`.

3. **Full Route Cache**: The rendered HTML + RSC payload of static routes is stored on the server. Populated at build time for static routes. Invalidated by revalidation or deployment. Dynamic routes (using cookies, headers, searchParams) are excluded.

4. **Router Cache**: Client-side in-memory cache of visited route segments. Persists for the browser session. Automatic prefetching populates it. `router.refresh()` clears the current route's entry. This is why you sometimes see stale data after a mutation — you need to call `revalidatePath` server-side AND the Router Cache needs to be busted.

### Q8: A page works in development but shows hydration mismatch errors in production. How do you debug?

**Answer:**
Hydration mismatches happen when the server-rendered HTML doesn't match what React renders on the client. Common causes:

1. **Date/time rendering** — `new Date()` differs between server and client.
2. **Browser-only APIs in Server Components** — `localStorage`, `window`, `navigator`.
3. **Non-deterministic rendering** — `Math.random()`, `crypto.randomUUID()` called during render.
4. **Third-party scripts modifying the DOM** before React hydrates.
5. **Conditional rendering based on `typeof window`**.

Debug approach: add `suppressHydrationWarning` progressively to isolate the component. Next.js 14+ shows the exact diff in the error overlay. For timestamps, I use `suppressHydrationWarning` on the specific element + `useEffect` to update client-side. For random IDs, generate server-side and pass as props.

```typescript
// Pattern for client-only rendering to avoid mismatch
'use client'
import { useState, useEffect } from 'react'

export function ClientOnlyWrapper({ children }: { children: React.ReactNode }) {
  const [mounted, setMounted] = useState(false)
  useEffect(() => setMounted(true), [])
  if (!mounted) return null
  return <>{children}</>
}
```

---

## 4. Advanced Scenario Q&As

### A1: How does React Server Component streaming work under the hood? What is the RSC payload?

**Answer:**
When Next.js renders an RSC page with Suspense boundaries, it doesn't wait for all data to be ready. It uses the RSC wire format — a line-delimited JSON-like stream — to progressively send component output.

The stream starts with the static shell: everything above and outside Suspense boundaries. This is flushed immediately. The browser starts parsing and can render above-the-fold content. For each Suspense boundary, a placeholder (the fallback) is included in the initial HTML.

As each suspended component resolves on the server, its RSC payload chunk is appended to the stream. The browser receives it and React's runtime patches the corresponding Suspense boundary — replacing the fallback with real content. This happens without a page navigation or state loss.

The RSC payload is NOT HTML. It's a compact serialized representation of the virtual DOM tree — component types, props, and children. It includes references to Client Component bundles that need hydration but not the Server Component code itself. This is what "zero JS for Server Components" actually means — their code doesn't ship, but their output does travel over the wire.

The performance implication: Time To First Byte is fast because the shell flushes immediately. Largest Contentful Paint happens progressively. You can prioritize above-the-fold Suspense boundaries by putting them first in the component tree.

### A2: Explain the difference between `revalidatePath` and `revalidateTag`. When does each fail to do what you expect?

**Answer:**
`revalidatePath('/products/123')` invalidates the Full Route Cache and Data Cache for that specific URL. It's URL-based. The problem: if the same data is consumed by multiple pages (e.g., a product appears in `/products/123`, `/categories/electronics`, and `/search?q=widget`), you'd need to invalidate all of them. That doesn't scale.

`revalidateTag('product-123')` invalidates all `fetch()` calls that were tagged with that string, regardless of which page they appear on. This is the correct primitive for content-based invalidation. You tag fetches at the data level, not the URL level.

Where `revalidateTag` fails to work as expected:
- You forgot to tag the `fetch()` calls — `next: { tags: ['product-123'] }` must be present at the fetch site.
- You're revalidating from a Client Component or a non-server context. `revalidatePath` and `revalidateTag` only work in Server Actions and Route Handlers.
- The Router Cache (client-side) is NOT cleared by these functions. The client might still show stale data from its in-memory segment cache. You need to call `router.refresh()` on the client or navigate away and back.

```typescript
// Route handler for CMS webhook
// app/api/revalidate/route.ts
import { revalidateTag } from 'next/cache'
import { NextRequest } from 'next/server'

export async function POST(request: NextRequest) {
  const { secret, tag } = await request.json()
  if (secret !== process.env.REVALIDATION_SECRET) {
    return Response.json({ error: 'Unauthorized' }, { status: 401 })
  }
  revalidateTag(tag)
  return Response.json({ revalidated: true, tag })
}
```

### A3: How do you architect data fetching in a complex App Router page with nested layouts?

**Answer:**
App Router layouts are Server Components by default and can fetch data. This creates an interesting architecture decision: where in the layout tree does data fetching live?

My approach is the "fetch as close to usage" principle. Each Server Component fetches only what it needs. Request Memoization handles deduplication automatically — the same `fetch()` URL called in `RootLayout`, `DashboardLayout`, and `DashboardPage` will only hit the network once per request cycle.

For shared data like "current user", I create a cached wrapper:

```typescript
// lib/data/user.ts
import { cache } from 'react'
import { cookies } from 'next/headers'

export const getCurrentUser = cache(async () => {
  const token = cookies().get('auth-token')?.value
  if (!token) return null
  return fetchUserFromDB(token)
})
```

`React.cache()` memoizes per-request, like request memoization but for non-fetch async functions (DB calls, etc.). Any Server Component in the tree can call `getCurrentUser()` — it resolves once and returns the memoized result.

For parallel data fetching (avoid waterfalls), use `Promise.all()`:

```typescript
// app/dashboard/page.tsx
export default async function DashboardPage() {
  const [user, orders, metrics] = await Promise.all([
    getCurrentUser(),
    getRecentOrders(),
    getDashboardMetrics(),
  ])
  return <Dashboard user={user} orders={orders} metrics={metrics} />
}
```

If some data is slow and shouldn't block the page, move it into a child Server Component wrapped in Suspense — it fetches in parallel but doesn't block the parent render.

### A4: How would you implement optimistic UI with Server Actions?

**Answer:**
`useOptimistic` pairs with Server Actions for instant-feedback UI. The pattern is: immediately apply the change to local state while the Server Action runs in the background, then sync with server truth.

```typescript
'use client'
import { useOptimistic, useTransition } from 'react'
import { toggleLike } from './actions'

type Post = { id: string; liked: boolean; likeCount: number }

export function LikeButton({ post }: { post: Post }) {
  const [optimisticPost, setOptimistic] = useOptimistic(
    post,
    (state, liked: boolean) => ({
      ...state,
      liked,
      likeCount: liked ? state.likeCount + 1 : state.likeCount - 1,
    })
  )
  const [, startTransition] = useTransition()

  const handleLike = () => {
    startTransition(async () => {
      setOptimistic(!optimisticPost.liked)
      await toggleLike(post.id)
    })
  }

  return (
    <button onClick={handleLike}>
      {optimisticPost.liked ? 'Unlike' : 'Like'} ({optimisticPost.likeCount})
    </button>
  )
}
```

The key subtlety: `useOptimistic` automatically reverts to server state when the action settles. If the Server Action throws, the optimistic update rolls back. If it succeeds, Next.js revalidates the path and the server truth replaces the optimistic state.

---

## 5. Senior Trap Questions

### TRAP 1: "SSR is always better than CSR for user experience"

**The Trap:** Candidates agree because "SSR = faster initial content = better UX". This is wrong in multiple scenarios.

**The Real Answer:**
SSR sends pre-rendered HTML but still ships the same JavaScript bundle for hydration. Time-to-First-Byte is faster, but Time-to-Interactive (TTI) can be *worse* than CSR when:

- The server is geographically far from the user (SSR adds server latency, whereas CSR serves static files from a CDN edge node)
- The page is behind auth (crawlers don't see it, so SEO benefit is zero) — you're paying SSR latency cost for nothing
- Hydration is expensive — the browser downloads HTML, then downloads JS, then executes hydration, then the page becomes interactive. A user clicking during hydration gets a dead button. CSR pages are interactive as soon as JS executes, no hydration phase.
- Data changes frequently — SSR fetches on every request, which under load stresses the server

When CSR wins: authenticated dashboards, admin panels, heavily interactive UIs, pages where data changes per interaction. The first "load" feels slower but subsequent navigation is instant because the SPA handles routing client-side.

**The mature answer:** "SSR vs CSR is always a trade-off. I choose based on SEO requirements, data freshness needs, geographic distribution, and interactivity requirements. I default to SSG/ISR with CSR shells where possible."

---

### TRAP 2: "Use getServerSideProps for all pages to keep data fresh"

**The Trap:** Sounds defensive and safe. Actually destroys performance and scalability.

**The Real Answer:**
`getServerSideProps` (Pages Router) or equivalent dynamic Server Components (App Router) run on every request. This means:

- No CDN caching — every request hits your server
- Cold starts on serverless deployments affect every user
- Server under load from traffic spikes — you can't absorb bursts with CDN
- Latency is additive: user → server → DB → server → user, on every page load

For a blog post that changes once a week, using SSR means 1 million pageviews = 1 million DB queries. With SSG + ISR, it's 1 DB query per revalidation window.

Ask yourself: "What is the actual staleness tolerance for this content?" Most product content (blog, docs, marketing pages) is fine with 60 seconds of ISR staleness. Only use SSR when the content is truly per-request (personalized, auth-gated with SEO, depends on request cookies/headers).

---

### TRAP 3: "React Server Components replace all Client Components"

**The Trap:** RSC hype leads candidates to say they'd put everything in Server Components.

**The Real Answer:**
Server Components cannot:
- Use `useState`, `useReducer`, `useEffect`, or any other hook
- Attach event handlers (`onClick`, `onChange`, etc.)
- Use browser APIs (`window`, `localStorage`, `navigator`)
- Use Context API (consuming context)
- Use third-party client-only libraries (charting libraries, animation libraries, rich text editors)

Any interactive UI — forms, dropdowns, modals, accordions, drag-and-drop, real-time updates — requires Client Components. The goal is not to eliminate Client Components but to push them to the leaves of the component tree, keeping data fetching and non-interactive structure in Server Components.

The architecture pattern is: Server Component → fetches data, renders layout structure → passes data as props to Client Components → Client Components handle interactivity. You minimize JS bundle by keeping the Client Component surface area small, not by eliminating them.

---

### TRAP 4: "RSC means zero JavaScript sent to the browser"

**The Trap:** "Server Components have zero bundle size" — partially true, misleadingly stated.

**The Real Answer:**
Server Component *code* does not ship to the browser. That's accurate. But:

1. The RSC **payload** is transmitted — a serialized representation of the rendered component tree. It's compact but it's not zero bytes.
2. Any **Client Components** in the tree still ship their JavaScript.
3. The **Next.js runtime** and **React runtime** still ship.
4. Props passed from Server Components to Client Components must be serializable — they travel in the RSC payload.

The real benefit is: complex data transformation logic, heavy libraries used only for rendering (markdown parsers, date formatters), ORM queries — none of this ships as JS. A `marked` library used to parse markdown in a Server Component adds zero bytes to the client bundle. That's the meaningful win, not "zero JS".

Also: large server-side only libraries are a security consideration. If you import a DB client in a Server Component, you must ensure it's not accidentally imported in a Client Component. Next.js will error if you try, but be aware of the boundary.

---

### TRAP 5: "Hydration errors are minor warnings, you can suppress them"

**The Trap:** Candidates dismiss hydration mismatches as cosmetic.

**The Real Answer:**
Hydration mismatches are a serious correctness problem. React's hydration algorithm tries to reuse server-rendered DOM nodes. When the client-rendered virtual DOM doesn't match, React must:

1. In React 17 and earlier: throw and re-render the entire tree client-side (full hydration failure)
2. In React 18: attempt to recover by discarding the server HTML and re-rendering — causing a flash of incorrect content

The visible effects:
- **Content flicker**: User sees server content, then it's replaced by client content
- **CLS (Cumulative Layout Shift)**: Layout jumps hurt Core Web Vitals
- **State loss**: Any server-rendered form values or interactive state is discarded
- **Inconsistent UX**: Different content briefly visible on slow connections

The correct fix is to eliminate the mismatch, not suppress it. `suppressHydrationWarning` is only appropriate for timestamps and similar values that legitimately differ (like `<time datetime={serverTime}>`). Using it broadly masks bugs.

---

### TRAP 6: "Just use dynamic imports for everything to reduce bundle size"

**The Trap:** Sounds like an optimization. Over-applied, it creates waterfall loading.

**The Real Answer:**
Dynamic imports (`next/dynamic`, `React.lazy`) defer JavaScript loading until the component is needed. But:

- They introduce a **loading waterfall**: render → discover dynamic import → fetch JS → render component. This delays content.
- **Suspense boundaries** needed for each lazy component add complexity.
- **Preloading** with `<link rel="preload">` or Next.js `<Script strategy="beforeInteractive">` can mitigate this but adds complexity.
- For above-the-fold critical components, dynamic import makes initial render *slower*.

When dynamic import is correct:
- Components only visible after user interaction (modals, drawers, tooltips)
- Heavy third-party widgets (maps, video players, rich text editors)
- Components conditionally rendered based on feature flags
- Components below the fold on long pages

The senior answer: "I use dynamic imports strategically for large, conditionally-rendered components. For the critical rendering path, I keep static imports. With RSC, the calculus changes — moving a heavy library to a Server Component entirely eliminates the bundle concern for that code."

---

## 6. Production Code Examples

### ISR with On-Demand Revalidation

```typescript
// app/blog/[slug]/page.tsx
export const dynamicParams = true // allow paths not in generateStaticParams

export async function generateStaticParams() {
  const posts = await getPublishedPosts({ limit: 100 }) // top 100 at build
  return posts.map(post => ({ slug: post.slug }))
}

export default async function BlogPost({ params }: { params: { slug: string } }) {
  const post = await fetch(`${process.env.CMS_URL}/posts/${params.slug}`, {
    next: { tags: [`post-${params.slug}`, 'posts'] }
  }).then(r => r.json())
  return <ArticleLayout post={post} />
}
```

### Next.js Image Optimization

```typescript
// components/ProductImage.tsx
import Image from 'next/image'

export function ProductImage({ src, alt }: { src: string; alt: string }) {
  return (
    <div style={{ position: 'relative', aspectRatio: '1 / 1' }}>
      <Image
        src={src}
        alt={alt}
        fill
        sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
        priority={false}  // true only for above-the-fold hero images
        style={{ objectFit: 'cover' }}
      />
    </div>
  )
}
// next.config.ts
// remotePatterns: [{ protocol: 'https', hostname: 'cdn.mystore.com' }]
```

### Parallel Route for Modal Pattern

```
// App Router file structure for intercepting routes:
// app/
//   products/
//     [id]/
//       page.tsx         (full product page)
//   @modal/
//     (.)products/
//       [id]/
//         page.tsx       (modal view — same URL, different layout)
//   layout.tsx           (renders both {children} and {modal})
```

```typescript
// app/layout.tsx
export default function RootLayout({
  children,
  modal,
}: {
  children: React.ReactNode
  modal: React.ReactNode
}) {
  return (
    <html>
      <body>
        {children}
        {modal}
      </body>
    </html>
  )
}
```

### Middleware for Geolocation Redirect

```typescript
// middleware.ts
import { NextRequest, NextResponse } from 'next/server'

const REGION_MAP: Record<string, string> = {
  GB: '/en-gb', DE: '/de', FR: '/fr', JP: '/ja'
}

export async function middleware(request: NextRequest) {
  const country = request.geo?.country ?? 'US'
  const locale = request.cookies.get('preferred-locale')?.value

  if (!locale && request.nextUrl.pathname === '/') {
    const target = REGION_MAP[country] ?? '/en-us'
    return NextResponse.redirect(new URL(target, request.url))
  }
  return NextResponse.next()
}

export const config = { matcher: '/' }
```

### Edge Runtime Route Handler

```typescript
// app/api/health/route.ts
export const runtime = 'edge'

export async function GET() {
  return Response.json({
    status: 'ok',
    region: process.env.VERCEL_REGION ?? 'local',
    timestamp: new Date().toISOString()
  })
}
// Use edge runtime for: lightweight endpoints, geolocation, low-latency health checks
// Use Node.js runtime for: crypto, file system, native node modules, heavy computation
```

### Streaming with Error Boundary

```typescript
// app/dashboard/page.tsx
import { Suspense } from 'react'
import { ErrorBoundary } from 'react-error-boundary'

export default function DashboardPage() {
  return (
    <div className="dashboard-grid">
      <ErrorBoundary fallback={<div>Failed to load metrics</div>}>
        <Suspense fallback={<MetricsSkeleton />}>
          <AnalyticsMetrics /> {/* slow DB query — streams when ready */}
        </Suspense>
      </ErrorBoundary>
      <Suspense fallback={<TableSkeleton />}>
        <RecentActivity />   {/* fast query — renders immediately */}
      </Suspense>
    </div>
  )
}
```

---

## 7. Interview Cheat Sheet

### Rendering Strategy Quick Reference

| Scenario | Strategy | Next.js Primitive |
|---|---|---|
| Marketing page, blog | SSG | `export const revalidate = false` |
| Product catalog, news | ISR | `export const revalidate = 60` |
| Per-user page with SEO | SSR | `export const dynamic = 'force-dynamic'` |
| Auth dashboard | CSR | `'use client'` + `useEffect`/React Query |
| Data-heavy, no interactivity | RSC | Default Server Component |
| Interactive UI leaf | Client Component | `'use client'` directive |
| Mutations from forms | Server Action | `'use server'` in actions file |
| Third-party webhook | Route Handler | `app/api/*/route.ts` |

### App Router vs Pages Router Mapping

| Pages Router | App Router Equivalent |
|---|---|
| `getServerSideProps` | `async` Server Component with `force-dynamic` |
| `getStaticProps` | `async` Server Component with `revalidate` |
| `getStaticPaths` | `generateStaticParams()` |
| `pages/api/*` | `app/api/*/route.ts` (Route Handlers) |
| `_app.tsx` | `app/layout.tsx` |
| `_document.tsx` | `app/layout.tsx` (root) |

### Caching Cheat Sheet

| Cache | Scope | Invalidate |
|---|---|---|
| Request Memoization | Single request | Automatic (per request boundary) |
| Data Cache | Cross-request, server | `revalidateTag()`, `revalidatePath()`, deploy |
| Full Route Cache | Cross-request, server | Same as Data Cache; dynamic routes opt out |
| Router Cache | Client browser session | `router.refresh()`, navigation, tab close |

### RSC Boundary Rules

```
Server Component CAN:          Client Component CAN:
- await async calls             - useState, useReducer
- access process.env secrets    - useEffect, custom hooks
- import server-only libraries  - event handlers (onClick, etc.)
- reduce client bundle          - browser APIs (window, localStorage)
- pass props to Client Comps   - Context API consumers
                                - third-party client libs
CANNOT:                         CANNOT:
- useState / hooks              - await on server (async Server Component)
- onClick / event handlers      - access server-only APIs
- window / localStorage         - import 'server-only' modules
- use 3rd party client libs
```

### Common Gotchas Checklist

- [ ] Are dates formatted consistently server/client? (hydration mismatch risk)
- [ ] Is `Math.random()` or `Date.now()` called during render? (hydration mismatch)
- [ ] Is sensitive data (API keys, tokens) imported in a Client Component? (security leak)
- [ ] Are `revalidateTag` strings consistently named between fetch tags and revalidation calls?
- [ ] Is `router.refresh()` called after mutations to bust Router Cache?
- [ ] Are Suspense boundaries present for slow-loading Server Components? (streaming)
- [ ] Is `generateStaticParams` exporting enough paths? (ISR fills the rest on-demand)
- [ ] Are `next/image` `sizes` props configured for responsive layouts? (performance)
- [ ] Is middleware matcher scoped correctly? (avoid running on `/_next/static` paths)
- [ ] Are Server Actions protected with authentication checks server-side? (security)

### Time Complexity for SSR Decisions

```
Decision: "Should I SSR this page?"

YES if:
  - Content varies per user/session AND SEO matters
  - Content must be fresh on every load (live prices, real-time stock)
  - Page uses cookies/headers to personalize content with SEO requirement

NO — use SSG/ISR if:
  - Content is the same for all users
  - Staleness of minutes/hours is acceptable
  - Page is behind auth (no SEO benefit from SSR)

NO — use CSR if:
  - Page is behind auth AND heavily interactive
  - Content is fetched client-side anyway (no SSR benefit)
  - Real-time updates required (WebSocket, polling)
```

### The 30-Second Pitch for any Interview Question

1. **State the trade-offs** — never frame it as "X is always better"
2. **Name the production context** — e-commerce, dashboard, blog, etc.
3. **Mention the metric** — TTFB, TTI, CLS, bundle size, server load
4. **Describe the failure mode** — what goes wrong if you choose wrong
5. **Give the pragmatic answer** — what you'd actually do and why

---

*Last updated: 2026-08 | Next.js 14+ (App Router) | React 18+*
