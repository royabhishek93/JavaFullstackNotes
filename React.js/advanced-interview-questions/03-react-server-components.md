# Explain RSC. How is it different from SSR?

> **Interview priority:** MUST KNOW

## Question

Explain RSC. How is it different from SSR?

## Beginner Lens

Before memorizing the interview answer, follow the scenario and notice three things: the problem React is solving, the state or browser work that changes, and the rule that keeps the UI correct. Read the code blocks slowly and predict the next result before reading the explanation.

## Detailed Explanation

**HOW TO SAY IT:**

> "This is one I see confused a lot. Let me use an Amazon product detail page
> as an example. That page has maybe 30 components — title, price, images,
> reviews, related products, add-to-cart button, wishlist button.
> Out of those 30, maybe 3 actually need to be interactive: add-to-cart,
> wishlist, and image zoom. SSR renders all 30 to HTML but still ships all 30
> as JavaScript for hydration. RSC says: those 27 display-only components
> should never touch the browser's JS engine at all."

```
REAL APP: Amazon Product Detail Page

  WITHOUT RSC — everything is JS:
  ┌─────────────────────────────────────────────────────────┐
  │  Browser downloads: react.js + all 30 components as JS   │
  │  Browser parses ALL 30 component definitions             │
  │  Browser hydrates ALL 30 components                      │
  │  Bundle size: ~450KB just for this page                  │
  └─────────────────────────────────────────────────────────┘

  WITH RSC — only interactive parts are JS:
  ┌─────────────────────────────────────────────────────────┐
  │  ProductPage         (Server — reads DB, zero JS)        │
  │  ├── ProductTitle    (Server — zero JS)                  │
  │  ├── PriceDisplay    (Server — zero JS)                  │
  │  ├── ImageGallery    (Server — zero JS, but...)          │
  │  │     └─ ZoomButton ('use client' — needs onClick) ←JS  │
  │  ├── ProductDetails  (Server — zero JS)                  │
  │  ├── ReviewSection   (Server — await db.reviews.findAll) │
  │  │     └─ LikeButton ('use client' — needs click) ←JS   │
  │  └── AddToCartBtn    ('use client' — needs state) ←JS   │
  │                                                          │
  │  JS shipped: 3 components only (ZoomBtn, LikeBtn, Cart)  │
  │  Bundle size: ~80KB  (vs 450KB)                          │
  │  DB query runs directly in ProductPage — no API needed   │
  └─────────────────────────────────────────────────────────┘
```

```
SSR vs RSC vs CSR — SIDE BY SIDE:

                  CSR               SSR              RSC
  ─────────────  ──────────────     ──────────────   ────────────────────
  Runs on        Browser            Server+Browser   Server only (for SC)
  JS to client   Full bundle        Full bundle      Zero (for SC)
  Can await DB   No (needs API)     No (needs API)   YES — direct query
  Has useState   Yes                Yes              NO
  Has onClick    Yes                No (server)      NO
  Initial HTML   Empty <div>        Full HTML        Full HTML
  Hydration      Full               Full             Only Client parts
  SEO            Poor               Good             Good
  Bundle size    Largest            Large            Smallest

  // Server Component — runs on server, never in browser
  async function ProductPage({ id }) {           // async by default!
    const product = await db.products.findById(id); // direct DB
    const reviews = await db.reviews.find({ productId: id });
    // No useEffect, no loading state, no API call needed
    return (
      <div>
        <h1>{product.title}</h1>
        <p>{product.price}</p>
        <ReviewList reviews={reviews} />        {/* Server Component */}
        <AddToCartButton productId={id} />      {/* Client Component */}
      </div>
    );
  }
```

```
THE ONE RULE THAT TRIPS PEOPLE:

  Server CAN hold Client ✅         Client CANNOT import Server ❌
  ────────────────────────          ──────────────────────────────
  // page.tsx (Server)              // CartButton.tsx ('use client')
  import CartButton from            import ProductData from
    './CartButton' // ← client        './ProductData'  // ← server
  // Fine — Cart runs in browser    // ERROR — server component
                                    // can't be bundled for browser

  WORKAROUND — pass Server output as children:
  // page.tsx (Server)
  <ClientShell>
    <ServerDataDisplay />   {/* resolved before client receives it */}
  </ClientShell>
  // ClientShell.tsx ('use client')
  export function ClientShell({ children }) {
    const [open, setOpen] = useState(false);
    return <div onClick={() => setOpen(true)}>{children}</div>;
    // children = already-rendered Server output, treated as opaque
  }
```

> "My rule in a Next.js 13+ project: everything starts as a Server Component
> by default. I only add 'use client' when I need useState, useEffect,
> event handlers, or browser APIs. That way I'm shipping the minimum JS
> necessary and my database queries live right next to the UI that uses them."

---
