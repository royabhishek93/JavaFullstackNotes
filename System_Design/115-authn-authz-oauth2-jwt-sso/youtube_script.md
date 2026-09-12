# Authentication & Authorization: OAuth2, JWT, SSO, RBAC — YouTube Script
Duration: ~10 min | Target: Engineers 3–10 YOE

## HOOK (0:00–0:30)

Picture this: your company just went from 3 microservices to 20. Every single one of them needs to check "who is this user, and are they allowed to do this?" So what do you do? The naive answer — every service calls a central auth server, on every single request, to ask "is this token valid?"

Now do the math. Twenty services, each getting hit with a few thousand requests a second. That central auth server just became the busiest, most fragile machine in your entire company. One blip in that service, and literally everything — checkout, login, admin panel, mobile app — goes down at once. That's not a hypothetical. That's how single points of failure are born.

By the end of this video, you'll know exactly how systems like Google, Okta, and every serious backend at scale solve this — using a token that verifies itself, in under a millisecond, with zero network calls back to home base.

[Screen cue: Show a diagram of 20 microservice boxes all drawing arrows into one central "Auth Server" box that's glowing red/overloaded, with a "single point of failure" label flashing.]

## THE PROBLEM (0:30–2:00)

Let's use an analogy, because this concept clicks instantly once you picture it physically. Imagine a huge office campus — a dozen separate buildings, each one a microservice. Every employee needs to badge into every building they visit.

The dumb way to build this: every single door, every single time someone walks up, calls the front-desk security office on the phone. "Hey, is employee 12345 allowed in?" The front desk looks them up, reads back their clearance level, hangs up. Fine for one door with light traffic. Completely collapses when you've got a thousand employees walking through fifty doors a minute. The front desk becomes the bottleneck — and if the phone line goes down, EVERY door goes down with it.

That's exactly the problem with naive authentication in a microservices world: if "who is this user" requires a network call to a central service on every single request, you've built a system that's only as reliable, and only as fast, as that one central service — no matter how many services you've built around it.

So the question becomes: how do we let each door verify a badge on its own, without picking up the phone every time?

[Screen cue: Draw the office-campus analogy — one "Front Desk" box, a phone icon with a red X through it, and a dozen door icons each independently trying to call it.]

## THE SOLUTION (2:00–5:00)

Here's the fix, and it's the same fix real security systems use in physical buildings and in software: the front desk — think Okta, Auth0, or your own auth service, this is your **Identity Provider** — verifies you ONE time, at the main gate. Then it hands you a badge. Not just any badge — a badge that is cryptographically tamper-proof, and lists your clearance directly on its face: "Engineering, Level 3, expires 6PM today."

Every door on campus has a badge reader that can verify that badge is real, on its own, using a public verification key that was distributed to every door in advance. No phone call to the front desk needed. That badge is exactly what a **JWT — a JSON Web Token** — is in software. It's a self-contained, digitally signed claim: "this user is 12345, these are their roles, this token expires at time T." Structurally, it's three base64-encoded parts — a header, a payload, and a signature — separated by dots. Any downstream service fetches the identity provider's public key once, from something called a JWKS endpoint, caches it, and from then on can verify every token completely locally. Recompute the signature, compare it, check the expiry and issuer claims — all CPU-bound, zero I/O, zero network call to the identity provider on the hot path.

But here's the question every engineer asks the second they hear this: "If the badge is good until 6PM, and I need to fire someone at 2PM, how do I get their badge back?" This is THE central tradeoff of token-based auth — a self-contained token that nobody needs to look up is ALSO a token that nobody can instantly invalidate.

The real-world answer: make the badge short-lived. A JWT access token that expires in just 5 to 15 minutes. Pair it with a separate, longer-lived **refresh token** — this one DOES get checked against a database on every use. So you get fast, stateless verification for the common case — every regular API call — and a bounded blast radius, at most 15 minutes, if you ever actually need to revoke someone.

Now zoom out from a single company to multiple companies and apps — that's **SSO, Single Sign-On**. Log into your identity provider once, and Slack, Gmail, your internal tools — every trusted app — accepts that same badge instead of making you log in again.

And **OAuth2** is the protocol underneath "Login with Google." Here's the key insight people get wrong: when you click that button, the app you're logging into never sees your Google password. You get redirected to Google's own login page, you approve some scopes, Google redirects back with a short-lived authorization code, and THEN — server to server, never touching your browser — that code gets exchanged for an access token. Your password never leaves Google's servers.

Finally, once a service knows WHO you are — authentication — it still needs to decide WHAT you're allowed to do — authorization. That's **RBAC, Role-Based Access Control**: does this user's ROLE — admin, editor, viewer — permit this action? Simple table lookup, easy to reason about. And there's a more powerful cousin, **ABAC, Attribute-Based Access Control**, which checks a whole policy: is the user's department equal to the document's department, AND is it business hours, AND is the request coming from a corporate IP? More flexible — but harder to audit, because "who can do what" isn't a simple lookup table anymore.

[Screen cue: Live-draw the OAuth2 Authorization Code flow step by step — User, App, Google Auth Server, Google Resource Server — with the auth code and access token exchange arrows, highlighting that client_secret and password never touch the browser.]

## DEEP DIVE — WHERE ENGINEERS GET IT WRONG (5:00–8:00)

Let's go through the traps, because this is where interviews — and production incidents — actually happen.

**Trap one: treating revocation as an afterthought.** If your JWT access tokens live for, say, 24 hours "for convenience," you've just created a 24-hour window where a stolen token is fully usable and there's nothing you can do about it except wait. That's why production systems keep access tokens to 5-15 minutes. It's not arbitrary — it's a deliberate blast-radius decision.

**Trap two: refresh token theft, and reuse detection.** Here's the mechanism: at login, you get an access token expiring in 10 minutes, and a refresh token expiring in 30 days, stored hashed in the database. At the 9-minute mark, the client silently calls the refresh endpoint. The auth server issues a BRAND NEW access token AND a brand new refresh token — and marks the OLD refresh token as used. Now here's the trap engineers miss: what if that old, already-rotated refresh token gets presented again? That's not a random glitch — that's a signal the token was STOLEN, and someone else is racing you to use it. The correct response isn't to just reject that one request — it's to revoke the ENTIRE token family immediately. If you don't implement reuse detection, a stolen refresh token is a 30-day free pass for an attacker.

**Trap three: key rotation without a grace period.** Your auth server signs tokens with a private key, identified by a "kid" — key ID — in the JWKS document. If you rotate that signing key and immediately delete the OLD public key from the JWKS endpoint, here's what happens: any token that was signed two minutes before the rotation — and is still within its valid TTL — suddenly fails verification EVERYWHERE, instantly, for every user holding one. This is a real, common production incident. The fix is simple but frequently forgotten: keep old keys published in the JWKS document for as long as the longest-lived token signed with them could still be valid.

**Trap four: forgetting that "stateless" isn't free.** If you add a denylist check to your JWT verification to handle emergency revocation, congratulations — you've just reintroduced the network round trip you were trying to avoid, and you no longer have a truly stateless system. That's fine if it's a deliberate tradeoff, but plenty of teams do this by accident and then wonder why their "fast JWT verification" isn't actually fast.

**Trap five: session stores as a hidden single point of failure.** If you go the OTHER route — server-side sessions with Redis — your session lookup costs half a millisecond to two milliseconds. Fast, but it's network I/O every request, and now a Redis outage IS an authentication outage for your entire platform, even though nothing about your actual application logic broke.

**Trap six: overloading RBAC or overloading the token.** If you try to cram ABAC-style rules — business hours, IP ranges, department matching — into the JWT payload itself, you'll end up forcing users to re-login every time a business policy changes, because the rule is now baked into a token that's already been issued. The fix architects give in interviews: push complex, frequently changing policy into a dedicated policy engine, like Open Policy Agent, and keep the token itself limited to coarse role claims that rarely change.

Let's put it side by side. Compare the actual numbers: JWT signature verification is 0.1 to 0.3 milliseconds, pure CPU, no I/O. A Redis session lookup is 0.5 to 2 milliseconds — small, but it's real network I/O and a real dependency. JWKS cache TTL on verifying services is typically 10 to 60 minutes, meaning a key rotation takes up to an hour to fully propagate — plan your grace period accordingly.

[Screen cue: Comparison table — Session Cookie vs Stateless JWT vs Opaque Token+Introspection — columns for verification cost and revocation speed, with the six traps as red callout bubbles pointing at the relevant row.]

## REAL WORLD (8:00–9:30)

Let's ground this in real scale. Think about a food delivery platform like Swiggy or Zomato during a Friday dinner rush — easily 50,000+ requests per second hitting order placement, restaurant search, and delivery tracking services combined. If every one of those requests had to round-trip to a central auth server just to confirm "yes, this rider's token is valid," that auth service alone would need to handle tens of thousands of QPS just for token checks — on top of everything else it does. Stateless JWT verification means each of those 50,000+ requests gets authenticated in under half a millisecond, entirely inside the service that received it.

Now think about a fintech platform like PhonePe or Paytm. They can't afford ANY laxity on revocation — if a device is reported stolen or a session looks suspicious, that access needs to die fast. This is exactly why fintech backends lean toward SHORTER access token TTLs — sometimes as low as 5 minutes instead of 15 — accepting slightly more refresh traffic in exchange for a tighter blast radius. It's the same tradeoff from the decision framework, just tuned more aggressively because the cost of a compromised token is a financial transaction, not a delayed cart update.

And for SSO specifically — picture a large e-commerce company like Flipkart with dozens of internal tools: seller dashboard, logistics ops console, customer support panel. Without SSO, that's a dozen separate logins and a dozen separate places for credentials to leak. With SSO through a central identity provider, one login badge — issued once — grants access across every internal tool an employee is authorized for, and when that employee leaves the company, revoking ONE identity instantly locks every door, instead of someone having to remember to deactivate a dozen separate accounts.

[Screen cue: Company logos — Swiggy/Zomato, PhonePe, Flipkart — each next to their relevant number: "50,000+ req/sec," "5-min access token TTL," "1 login → 12 internal tools."]

## OUTRO + NEXT EPISODE (9:30–10:00)

So — stateless JWTs solve the fan-out problem, refresh token rotation with reuse detection solves the revocation problem, and pushing complex rules into a policy engine solves the authorization problem, all without ever forcing every request back through one fragile front desk.

If this made token-based auth finally click, hit subscribe — this is a system design series, and every episode builds on the last. Next episode, we're going one level deeper: what happens when ONE of those twenty microservices needs to call ANOTHER microservice on your behalf, with no user anywhere in the loop — service-to-service auth, mutual TLS, and workload identity. See you there.

[Screen cue: End card — "Next: Service-to-Service Auth & mTLS" with subscribe button animation.]
