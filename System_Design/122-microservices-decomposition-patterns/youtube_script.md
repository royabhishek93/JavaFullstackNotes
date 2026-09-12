# Microservices Decomposition Patterns: Strangler Fig, BFF, and Anti-Corruption Layer — YouTube Script
Duration: ~10 min | Target: Engineers 3–10 YOE

## HOOK (0:00–0:30)
"Your company has a 10-year-old monolith. Leadership wants microservices. So someone proposes the obvious plan: freeze features for six months, rewrite everything from scratch, and cut over on a Friday night.

Here's the problem — that new system gets tested against real production traffic for the very first time on the exact same day it fully replaces the old one. There's no partial rollback. There's no 'flip one thing back.' It's all... or nothing.

That single decision — big-bang rewrite versus incremental migration — is one of the most common reasons real microservices migrations fail. Today I'm going to show you the pattern that avoids it entirely: the strangler fig. Plus two patterns that make it actually survivable — the Backend-For-Frontend, and the Anti-Corruption Layer."

[Screen cue: Split screen — left side shows a monolith blob with a red "BIG BANG CUTOVER — FRIDAY 11PM" label and a countdown clock; right side shows the same monolith slowly shrinking with green checkmarks appearing one at a time.]

## THE PROBLEM (0:30–2:00)
"Let's make this concrete. Imagine an old, fully-occupied office building. It's outdated, it's expensive to maintain, but there are tenants running businesses inside it right now. You can't just evacuate everyone and demolish it — the business inside can't stop operating for the two years a full rebuild would take.

That's exactly the situation with a 10-year-old monolith. It's ugly. It's hard to scale. Every deploy touches five unrelated features because they're all compiled into the same artifact. But it's also making the company money, right now, every second.

So the naive options are both bad. Option one: keep patching the monolith forever, and your deploy risk and coupling just keep getting worse. Option two: rewrite everything and cut over all at once — and now you've bet the entire business on one deployment event.

Real construction crews actually have a pattern for the 'occupied building' problem, and it's named after something that happens in nature. There's a real botanical phenomenon called the strangler fig — it's a plant that grows AROUND an existing host tree, sending down roots alongside it, gradually taking over more and more of the structural load, until eventually the original tree can be removed entirely and the fig stands on its own. And at no single moment did anything visibly collapse.

That's the metaphor the entire industry borrowed for exactly this migration problem."

[Screen cue: Side-by-side illustration — a strangler fig plant growing around a host tree over three time-lapse frames, next to a monolith diagram shrinking as service boxes appear around it over three equivalent frames.]

## THE SOLUTION (2:00–5:00)
"Let's walk through how this actually works, piece by piece.

**Step 1 — The Strangler Fig pattern itself.** You put a routing facade in FRONT of the old monolith — often this is literally your API Gateway. Then you migrate ONE capability at a time. Say, just the 'search' endpoint. You redirect only that ONE route through the facade to a new, independently-built search service. Every other route — orders, profile, reviews — still hits the old monolith, completely unchanged.

Users never notice the migration happening one room at a time. And here's the key benefit: if the new search service turns out to be broken, you flip that ONE route back to the monolith, instantly. The blast radius of a mistake is always just the one capability you're currently migrating — never the whole system.

You repeat this. Next month, migrate '/orders'. The month after, '/profile'. The monolith shrinks incrementally, and at every single stage, the system is fully working and fully deployable.

**Step 2 — The Backend-For-Frontend, or BFF.** Once you have several independent services, a single mobile app screen often needs data assembled from three or four of them at once — think a product page needing product details, current price, wishlist status, and inventory count. If the mobile app calls all four services directly, every one of those services now has to satisfy the mobile team's needs, AND a totally different web frontend team's needs, AND maybe a partner API's needs, all in one shared contract.

The fix: give each TYPE of consumer its own dedicated aggregation layer — a BFF — that calls the backend services and shapes the response exactly the way THAT client needs it. Mobile BFF stays lean for battery and bandwidth. Web BFF returns a richer payload. Neither one forces the underlying Product or Inventory service to compromise its clean data model to satisfy three competing consumers at once.

**Step 3 — The Anti-Corruption Layer, or ACL.** This shows up specifically DURING a strangler fig migration. Your shiny new Order service has a clean, modern domain model. But it still needs to read data from the ancient monolith's database — which represents 'an order' with 15 years of accumulated legacy quirks. Maybe a status field that's really three different concepts crammed into one column, because of a 'temporary' fix from 2014 that never got cleaned up.

If your new service's code directly understands those legacy quirks, you've just imported the monolith's mess straight into your brand-new codebase — defeating the entire point of the rewrite. The ACL is a thin, deliberate translation layer sitting between the new service and the legacy system. It converts the legacy model's quirks into your new service's clean domain model AT the boundary. The new code never sees the legacy mess. And if the legacy quirks ever change, only the translation layer needs updating — not your core domain logic.

**Step 4 — Database-per-service, and the API composition problem it creates.** Once services are split apart, each gets its OWN database — a deliberate choice, so services can't get silently re-coupled through a shared table the way they were coupled through shared code in the monolith. But now a business question that used to be one SQL JOIN — 'show me this customer's order history with current product names and prices' — needs data from two or three separate databases that can't be joined directly.

Two fixes here. First, API composition: a coordinating service calls each backend and joins the results in application code. Simple, but can be slow if calls are made one after another. Second, at higher scale: a precomputed, denormalized read model kept in sync via events — this is CQRS, applied specifically to the cross-service read problem."

[Screen cue: Live-drawn diagram — routing facade box with arrows splitting to "NEW search service" and "OLD monolith"; then a second diagram showing three BFF boxes (Mobile/Web/Partner) funneling into shared Product/Inventory services; then an ACL box sitting between "NEW Order Service" and "LEGACY DB" with a translation rule written out.]

## DEEP DIVE — WHERE ENGINEERS GET IT WRONG (5:00–8:00)
"Now, here's the thing — the pattern names are easy to memorize. The mistakes happen in the DETAILS. Let's go through every trap.

**Trap 1: Migrating the wrong capability first.** Teams get excited and want to prove the microservices rewrite by migrating checkout or payment on day one — the highest-risk, highest-visibility path in the entire system. Wrong order. The real prioritization is: migrate capabilities that are LOW-RISK if something goes wrong — not payment on day one. HIGH-VALUE to prove the pattern works — something the team was already planning to rewrite anyway. And LOOSELY COUPLED in the legacy code — a module that doesn't reach into six other modules' internal tables. The common real-world order is: read-heavy, low-risk features first — search, product catalog display — THEN write paths with lower blast radius, like profile updates — and checkout/payment absolutely LAST, once the pattern, the routing facade, and the team's confidence are all proven.

**Trap 2: Ignoring API composition latency.** Each additional service call in a composition adds its own network round-trip — commonly 5 to 50 milliseconds per hop, depending on same-datacenter versus cross-region. Here's the number that surprises people: a composition joining 4 services SEQUENTIALLY could add 100 to 200 milliseconds of latency, versus a single monolith SQL JOIN that used to run in single-digit milliseconds. That's not a rounding error — that's potentially 100x slower for the exact same business question. The fix engineers often miss: make those composition calls in PARALLEL — fan-out, not sequential — wherever the joined services don't depend on each other's results.

**Trap 3: Letting legacy-aware logic leak everywhere instead of using an ACL.** Without an anti-corruption layer, you get the SAME legacy-quirk-handling conditional logic copy-pasted across every single consumer of that data. That spread IS the actual 'corruption' the pattern is named to prevent. With an ACL, that same translation logic — 'legacy.status_code == 3 AND legacy.payment_flag == Y means PAID, but status_code == 3 AND payment_flag == N means PLACED' — lives in exactly ONE place. The maintenance cost is small and localized. Without it, that cost gets multiplied by every team that ever touches that data.

**Trap 4: Underestimating the migration timeline.** Strangler fig migrations for a large monolith commonly take many months to a few years for a FULL migration. That's not a bug in the pattern — it's the deliberate tradeoff for never having a single high-risk cutover event. If your migration plan says '8 weeks, done,' that's usually a big-bang rewrite wearing a strangler fig costume.

**Trap 5: Skipping the BFF and letting every client call every service directly.** Without a BFF per client type, your Product and Inventory services end up trying to satisfy the mobile team's lean-payload demands, the web team's rich-payload demands, and a partner's contract-stability demands, all inside ONE shared API contract. That's a recipe for an API that nobody is happy with and everybody wants to change."

[Screen cue: Comparison table on screen — rows: Strangler Fig / BFF / Anti-Corruption Layer / Database-per-service / API composition / Precomputed read model — columns: Problem It Solves | Cost/Tradeoff — pulled directly from the decision framework.]

## REAL WORLD (8:00–9:30)
"Let's ground this in scale numbers you'd actually quote in an interview.

Picture a large Indian e-commerce platform — similar scale to a Flipkart or Swiggy — running a decade-old monolith serving millions of requests a day. They start their strangler fig migration with product search, because it's read-heavy and low-risk — exactly the prioritization we just covered. Over the following 18 months, they migrate catalog display, then profile updates, and only in the final phase, checkout — each migration validated in production with instant single-route rollback available the entire time.

Now picture their mobile app team hitting the composition problem: a single product page needs product details, live price, wishlist status, and inventory count — four separate service calls. Calling them sequentially adds up to roughly 150 milliseconds of extra latency versus the old monolith's single JOIN. Switching those four calls to parallel fan-out brings that down to roughly the cost of the SLOWEST single call — maybe 40-50 milliseconds — instead of the sum of all four.

And picture their Order service team, mid-migration, needing to read from the legacy monolith's order table, which has that infamous overloaded status_code column from a 2014 hotfix. They build a dedicated Anti-Corruption Layer — maybe 200 lines of translation code — and that one file absorbs 15 years of schema quirks so the new Order service's clean domain model never has to know any of it exists."

[Screen cue: Stylized company logo placeholder + big numbers on screen: "18 MONTHS MIGRATION" / "150ms → 45ms with parallel fan-out" / "1 ACL FILE vs. N CONSUMERS OF LEGACY LOGIC".]

## OUTRO + NEXT EPISODE (9:30–10:00)
"So — strangler fig for safe incremental migration, BFF for competing client needs, anti-corruption layer for keeping legacy mess contained, and API composition or a precomputed read model for cross-service reads. Four patterns, one real interview answer.

This is actually episode 122 — the last one in this system design series. If any of this connected dots for you, the best next step isn't a new topic — it's going back through the full index. A LOT of these patterns build on each other: this episode literally referenced the API Gateway pattern and CQRS from earlier episodes. Go back, connect the pieces, and you'll walk into your next system design interview with the whole map in your head, not just one piece of it.

Subscribe if you want the full series in your feed, and drop a comment with which episode from the series helped you the most — I read every one. See you in the next one."

[Screen cue: Full series index scrolling on screen, episode 122 highlighted at the bottom, subscribe button animation.]
