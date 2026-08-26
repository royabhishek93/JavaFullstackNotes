# Frontend Observability — 15-YOE React Architect Interview Prep

> Target role: Staff / Principal Frontend Engineer, React Architect
> Focus: Sentry, RUM, Feature Flags, Analytics, Alerting, Privacy, Session Replay
> Voice: 15 years of production scars, not textbook answers

---

## 1. Big Picture ASCII Diagram — Full Observability Stack

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     FRONTEND OBSERVABILITY STACK                            │
└─────────────────────────────────────────────────────────────────────────────┘

  Browser / React App
  ┌───────────────────────────────────────────────────────────────────────┐
  │  User Interaction  →  React Components  →  API Calls  →  Rendering   │
  └──────────┬──────────────────┬──────────────────┬─────────────────────┘
             │                  │                  │
     ┌───────▼──────┐   ┌───────▼──────┐   ┌──────▼────────┐
     │ ERROR LAYER  │   │  PERF LAYER  │   │ FEATURE LAYER │
     │              │   │              │   │               │
     │ Sentry SDK   │   │ web-vitals   │   │ LaunchDarkly  │
     │ ErrorBoundary│   │ LCP/INP/CLS  │   │ GrowthBook    │
     │ Breadcrumbs  │   │ TTFB/FCP     │   │ PostHog FF    │
     │ Source Maps  │   │ Long Tasks   │   │ A/B Variants  │
     └──────┬───────┘   └──────┬───────┘   └──────┬────────┘
            │                  │                   │
            │          ┌───────▼──────┐            │
            │          │  RUM ENGINE  │            │
            │          │  Datadog RUM │            │
            │          │  Sentry Perf │            │
            │          │  SpeedCurve  │            │
            │          └──────┬───────┘            │
            │                 │                    │
     ┌──────▼─────────────────▼────────────────────▼────────┐
     │                  ANALYTICS LAYER                      │
     │  GA4 / PostHog / Amplitude / Mixpanel                 │
     │  Custom events, page_view, conversions, funnels       │
     │  Session Replay (LogRocket / Sentry Replay)           │
     └──────────────────────────┬────────────────────────────┘
                                │
     ┌──────────────────────────▼────────────────────────────┐
     │              BACKEND LOG AGGREGATOR                   │
     │  Structured JSON logs (correlation IDs)               │
     │  Datadog / ELK / Loki                                 │
     └──────────────────────────┬────────────────────────────┘
                                │
     ┌──────────────────────────▼────────────────────────────┐
     │                 ALERTING LAYER                        │
     │  Error rate spike  →  PagerDuty (sev1)                │
     │  LCP regression    →  Slack #perf-alerts              │
     │  Flag rollout fail →  Automatic kill switch           │
     │  JS exception surge→  On-call rotation                │
     └───────────────────────────────────────────────────────┘

  PRIVACY COMPLIANCE (cross-cutting)
  ┌───────────────────────────────────────────────────────────┐
  │  GDPR consent gate  →  Anonymize before send              │
  │  Cookie banner      →  Respect opt-out                    │
  │  PII masking in     →  Session replay scrubbing           │
  │  Source maps        →  Private upload only (never public) │
  └───────────────────────────────────────────────────────────┘
```

---

## 2. Conversational Interview Script — 15-YOE Architect Voice

**Interviewer:** Walk me through how you'd set up observability for a new React app from day one.

**You:** I break it into three concentric rings. The innermost ring is error capture — nothing else matters if you're blind to crashes. I'd wire up Sentry on day one with an `ErrorBoundary` at the router level and a nested one inside each major feature. The SDK captures unhandled promise rejections and console errors automatically, but the boundary is what keeps the rest of the UI alive when one feature explodes.

The middle ring is performance. I instrument web-vitals right after — LCP, INP, CLS — and pipe those into our RUM backend. The critical point here is that Lighthouse gives you lab numbers in a controlled environment. What users actually experience is field data, and there's always a gap. I've seen apps score 95 on Lighthouse and have LCP complaints from real users in Southeast Asia on 4G. Field data via CrUX or your own RUM is truth.

The outer ring is behavioral — analytics and feature flags. I set up GA4 or PostHog for event tracking, and I get feature flags in front of the team early because they're your deployment safety net. Once the team sees they can kill a bad feature in 30 seconds without a deploy, the culture shifts toward more aggressive shipping.

Cutting across all three is privacy compliance. Every tool I just named has a data pipeline that could ship PII to a third party. Before any of this goes to production, I need a consent gate that respects GDPR and blocks initialization of analytics/session replay until the user consents.

---

**Interviewer:** How do source maps work in production, and what's the wrong way to handle them?

**You:** Source maps are a double-edged sword. They're essential for debugging minified production code — without them, Sentry shows you `main.abc123.js:1:89423` which is useless. With them, you get the original TypeScript file, line, and column.

The wrong way — and I've seen this in codebases I've inherited — is to serve source maps publicly alongside the bundle. You set `devtool: 'source-map'` in webpack and forget about it. Now anyone can open DevTools, follow the link, and read your entire source. You've effectively shipped your IP and potentially exposed business logic, API keys in comments, internal architecture decisions.

The right way is to generate source maps but never expose them publicly. You upload them directly to Sentry using `sentry-webpack-plugin` or `sentry-cli`, tied to a release identifier. Sentry uses them server-side for symbolication. The `.map` files never hit your CDN.

The release identifier is the linchpin. It ties the deployed bundle to the uploaded source maps. I typically use the git commit SHA — set `SENTRY_RELEASE=$(git rev-parse HEAD)` in CI, pass it to both the webpack plugin and `Sentry.init()`. When a crash happens on bundle `abc123`, Sentry fetches the matching source map and shows you the original code.

---

**Interviewer:** Feature flags — aren't they just environment variables with extra steps?

**You:** That's the trap junior devs fall into. Env vars are build-time constants. A feature flag is a runtime, user-targeting decision. The distinction changes everything.

Env vars require a redeploy to change. Feature flags change in milliseconds from a dashboard — no deploy, no PR, no risk window. When an incident hits at 2 AM, your on-call doesn't want to do a hotfix deploy. They want to flip a flag.

The harder part of flags that people miss is assignment consistency. If I'm running an A/B test and a user is in variant B, they need to stay in variant B on every page load, every session, across devices if possible. You achieve this by hashing the user ID (not a random number) to determine the variant. Every LaunchDarkly, GrowthBook, or PostHog evaluation for the same user ID produces the same bucket. Random assignment breaks the experiment.

Then there are targeting rules — you want to roll out to 5% of users, but specifically only users in Germany with a premium account. That's not an env var.

---

## 3. Scenario Q&As — Production Context (8+)

---

### Scenario 1: ErrorBoundary Not Catching Async Errors

**Q:** Your ErrorBoundary isn't catching errors from async event handlers. A button click that triggers a failing async function causes a white screen instead of a fallback UI. Why?

**A:** ErrorBoundaries only catch errors thrown during rendering, in lifecycle methods, and in constructors of child components. They do not catch errors in event handlers or async callbacks — those happen outside React's call stack.

For event handlers, you need a `try/catch` inside the handler itself, then either set error state to trigger the boundary manually, or call `window.onerror` / `reportError()`. Sentry still captures these via its global `unhandledrejection` listener, but the boundary UI never shows.

```typescript
// Correct pattern for async handler + Sentry
const handleSubmit = async () => {
  try {
    await submitOrder(cartItems);
  } catch (err) {
    Sentry.captureException(err, {
      tags: { feature: "checkout", step: "submit" },
    });
    setErrorState(err as Error); // triggers ErrorBoundary via state
  }
};
```

---

### Scenario 2: Sentry Showing Wrong File in Stack Trace

**Q:** Sentry reports a crash but the stack trace points to vendor bundle code, not your code. Source maps are uploaded. What went wrong?

**A:** Two common causes:

1. **Release mismatch.** The `release` string in `Sentry.init()` doesn't match the release used when uploading source maps. Sentry can't find the right map file, falls back to the raw bundle, and points into vendor code. Fix: ensure `SENTRY_RELEASE` is consistent between upload and runtime.

2. **Wrong artifact path.** The webpack output `publicPath` doesn't match what Sentry expects as the URL prefix. The `urlPrefix` in `sentry-webpack-plugin` must match your CDN URL, e.g., `https://cdn.myapp.com/static/js/`. Mismatch = no symbolication.

Verify with `sentry-cli releases files <release> list` — check that files are present and paths match what the browser actually requests.

---

### Scenario 3: LCP Regression After Deploy

**Q:** Datadog RUM shows LCP degraded from 1.8s to 3.4s 20 minutes after a deploy. How do you triage?

**A:** First, confirm the signal is real: is this p75 or p50, across all geo/device segments, or just mobile in one region? A single heavy user session can spike p75 temporarily.

If confirmed real, check the build diff. Most LCP regressions fall into:
- A new hero image added without `width`/`height` attributes, causing layout shifts and delayed render
- A new render-blocking script or stylesheet added to `<head>`
- A lazy-loaded component that previously didn't intersect LCP now does
- A backend response time regression for the API that fetches LCP content

Use the Sentry/Datadog span waterfall for a session that shows high LCP. This shows you exactly where time is spent. If it's a resource, trace it back to the deploy.

If it's bad enough, roll back the deploy or use a feature flag to disable the new code path.

---

### Scenario 4: Feature Flag Race Condition in SSR

**Q:** You're using LaunchDarkly client-side SDK in a Next.js app. Users report seeing the wrong variant on first load. What's happening?

**A:** The client-side SDK initializes asynchronously. During SSR, the server renders with no flag context — it uses defaults. The page hydrates, the SDK initializes, evaluates the real flag, and the component flips to the correct variant. Users see a flash of incorrect content (FOIC), sometimes called a "flash of uncontrolled feature."

Correct approach: use the LaunchDarkly Node.js SDK on the server, evaluate flags at request time, pass the evaluated values as props or into a React context during SSR, and initialize the client SDK with `bootstrap` values so it matches the server render on hydration.

```typescript
// Next.js getServerSideProps
export async function getServerSideProps(ctx) {
  const ldClient = await getLDServerClient();
  const user = { key: ctx.req.session.userId };
  const flags = await ldClient.allFlagsState(user);
  return { props: { flags: flags.toJSON() } };
}
```

---

### Scenario 5: Analytics Page Views Not Firing in SPA

**Q:** After migrating to React Router, GA4 only logs one page_view per session — the landing page. Why?

**A:** GA4's default `page_view` event fires on full page loads. In a SPA, navigation is handled client-side via the History API — there is no real page load after the first one. GA4's script never knows a navigation happened.

Fix: listen to React Router's `location` changes and manually fire `page_view`:

```typescript
import { useEffect } from "react";
import { useLocation } from "react-router-dom";

export function useGAPageTracking() {
  const location = useLocation();
  useEffect(() => {
    window.gtag?.("event", "page_view", {
      page_path: location.pathname + location.search,
    });
  }, [location]);
}
```

If you're using GA4's "Enhanced Measurement," it has a history change detection feature, but it's unreliable in complex SPAs. Explicit firing is safer.

---

### Scenario 6: Session Replay Capturing Passwords

**Q:** A security audit finds that your LogRocket session replay is recording password fields and credit card numbers. How do you fix it and prevent recurrence?

**A:** Immediate fix: LogRocket and Sentry Session Replay both have DOM masking options. Enable privacy mode globally, then selectively unmask safe elements.

```typescript
LogRocket.init("app/id", {
  dom: {
    inputSanitizer: true, // masks all <input> by default
  },
});
```

For Sentry Session Replay, use the `maskAllInputs` option:

```typescript
Sentry.init({
  integrations: [
    Sentry.replayIntegration({
      maskAllInputs: true,
      maskAllText: false, // too aggressive for most apps
      blockAllMedia: false,
    }),
  ],
});
```

For prevention: add a `data-sentry-mask` attribute to any sensitive element as a defense-in-depth layer, and add a pre-deploy checklist item that asks "does this form contain PII/financial data? If yes, verify masking."

---

### Scenario 7: Breadcrumbs Not Showing User Path Before Error

**Q:** Sentry captures an exception but the breadcrumb trail only shows network requests, not the UI interactions that led to the crash. How do you enrich it?

**A:** Sentry auto-captures XHR/fetch and console calls as breadcrumbs, but it doesn't know about your business-level UI interactions unless you tell it.

Add manual breadcrumbs at key interaction points:

```typescript
const handleTabChange = (tab: string) => {
  Sentry.addBreadcrumb({
    category: "ui.click",
    message: `User switched to tab: ${tab}`,
    level: "info",
    data: { tab, userId: currentUser.id },
  });
  setActiveTab(tab);
};
```

For forms, add a breadcrumb at each step of a multi-step wizard. This creates a trail that makes the crash reproducible.

---

### Scenario 8: Correlation Between Frontend Errors and Backend Logs

**Q:** A user reports a checkout failure. You have a Sentry event but you can't find the matching backend log. How do you set up correlation?

**A:** You need a trace/correlation ID that flows from frontend to backend. Generate one per user session (or per transaction) and attach it everywhere.

Frontend: generate or receive a trace ID, add it to all outbound API requests as a header (`X-Trace-Id` or use the W3C `traceparent` header format). Report it to Sentry as a tag.

```typescript
const traceId = crypto.randomUUID();
Sentry.setTag("trace_id", traceId);

// Attach to all fetch calls via interceptor
const originalFetch = window.fetch;
window.fetch = (input, init = {}) => {
  const headers = new Headers(init.headers);
  headers.set("X-Trace-Id", traceId);
  return originalFetch(input, { ...init, headers });
};
```

Backend: read `X-Trace-Id`, log it on every log line for the request. Now when a Sentry event has `trace_id: abc123`, you grep for that ID in Datadog/ELK and see the entire server-side execution.

---

## 4. Advanced Scenario Q&As (4+)

---

### Advanced 1: INP Regression — Diagnosing Long Tasks

**Q:** PostHog RUM shows INP (Interaction to Next Paint) degrading after a new data grid component shipped. How do you isolate the cause?

**A:** INP measures the worst interaction responsiveness across the entire page visit. A value above 200ms fails the Core Web Vitals threshold.

Start in Chrome DevTools Performance tab. Record a session that replicates the interaction. Look for "Long Tasks" (shown in red in the Main thread) that occur during the interaction. A task over 50ms blocks the main thread.

Likely culprits with a data grid:
- Synchronous sort/filter logic running during a click handler on thousands of rows
- Heavy re-render triggered by prop change without memoization (`useMemo`/`React.memo`)
- DOM mutation batching issue — React 18 concurrent mode helps but isn't magic

```typescript
// Before: blocking sort in click handler
const handleSort = (col: string) => {
  setData([...data].sort(compareFn)); // synchronous, blocks thread
};

// After: defer heavy work with startTransition
import { useTransition } from "react";
const [isPending, startTransition] = useTransition();
const handleSort = (col: string) => {
  startTransition(() => {
    setData([...data].sort(compareFn)); // yields to browser
  });
};
```

Instrument with the PerformanceObserver API to capture real INP events and associate them with the component responsible.

---

### Advanced 2: Gradual Rollout with Statistical Significance Gate

**Q:** You're running an A/B test on a new checkout flow. How do you ensure you don't call a winner too early?

**A:** "Peeking" is the most common mistake in A/B testing — you look at results while the test is running, see a positive trend, and declare a winner. The problem is that early in an experiment, random variance makes results look significant. If you call it early you'll be wrong ~40% of the time even with "p < 0.05" because you're doing multiple comparisons over time.

The correct process:

1. **Pre-calculate sample size** before starting. Use a power calculator (e.g., Evan's A/B testing calculator) with your baseline conversion rate, minimum detectable effect (MDE), 80% power, and 95% confidence. Only start the test when you can commit to running it until that sample size is reached.

2. **Set the test duration upfront** — typically 1-2 full business weeks to capture weekly seasonality.

3. **Don't peek until you hit the target sample size.** Automate this: have GrowthBook or your stats layer hold results behind a gate and only reveal them when the sample threshold is met.

4. **Primary metric only.** Pick one north-star metric per test. If you test 5 metrics and look for any improvement, your false positive rate explodes.

```typescript
// GrowthBook experiment config — define before launch
const experiment = {
  key: "checkout-redesign-v2",
  variations: [0, 1], // control, variant
  coverage: 1.0, // 100% of traffic
  weights: [0.5, 0.5],
  minSampleSize: 2500, // pre-calculated
  metrics: ["checkout_conversion_rate"], // one primary metric
};
```

---

### Advanced 3: Privacy-First Analytics Architecture

**Q:** Legal says you cannot send any user data to US-based third parties without explicit consent. How do you architect analytics?

**A:** Three options, in order of privacy strictness:

**Option 1: Consent gate with conditional initialization.** Initialize GA4/Mixpanel only after explicit consent. This is the most common pattern but means you lose data from non-consenting users (~30-40% in EU).

```typescript
const initAnalytics = (consent: boolean) => {
  if (!consent) return;
  // Only now initialize third-party scripts
  loadGA4("G-XXXXXXXX");
};
```

**Option 2: First-party proxy.** Route analytics events through your own domain endpoint, strip PII server-side, then forward to the analytics vendor. This satisfies "no data sent to third parties" because the browser talks to your servers only. Cloudflare Workers or a simple Lambda can do this.

**Option 3: Self-hosted analytics.** PostHog is open-source and can run entirely within your infrastructure. No data leaves your AWS/GCP environment. This is the cleanest answer for regulated industries (healthcare, finance, EU-focused products). You give up some features but gain complete data sovereignty.

My default recommendation: PostHog self-hosted for Europe-facing products, with a consent banner that gates everything else. Segment can act as the router that only fires downstream destinations after consent status is confirmed.

---

### Advanced 4: Alerting Strategy — What to Alert On and What Not To

**Q:** Your on-call is getting paged 20 times per night for frontend alerts. How do you redesign the alerting strategy?

**A:** Alert fatigue is as dangerous as no alerting — both result in the real incident being missed. The principle is: every alert must be actionable and should represent something that requires human attention right now.

**Alert on (sev1 — page on-call):**
- Error rate spike >3x baseline for any 5-minute window (new crash class, not existing noise)
- LCP p75 > 4s for 10+ minutes (user experience is broken)
- Complete checkout funnel dropping >50% conversion (revenue impact)
- JS exception affecting >1% of active sessions

**Alert on (sev2 — Slack only):**
- LCP p75 creeping above 2.5s for 30 minutes
- New Sentry issue with >100 occurrences/hour
- Feature flag evaluation errors (SDK can't reach LaunchDarkly)
- Source map upload failure in CI (means next deploy will have bad stack traces)

**Do NOT alert on:**
- Individual Sentry errors from known-bad clients (bots, extension conflicts)
- Single-user LCP spike
- Third-party script timeouts (unless you can do anything about them)

In Sentry, use "Alert Rules" with `is:unresolved !has:assignee` filters to reduce noise from already-triaged issues. Integrate with PagerDuty for sev1, Slack for sev2, and make sure each alert links directly to the relevant dashboard.

---

## 5. Senior Trap Questions (6+)

---

### Trap 1: "console.error is enough for error tracking in production"

**Trap name:** The Silent Production Fallacy

**Why it's a trap:** `console.error` writes to the browser console. In production, with DevTools closed, that error disappears completely. You have no aggregation, no alerting, no stack traces with context, no source map symbolication, no user context, and no ability to correlate the error with a specific release. You're flying completely blind.

**Correct answer:** `console.error` is a development-time debugging tool. In production you need:
- Sentry (or equivalent) for aggregation across all users
- Automatic deduplication (so a bug affecting 10,000 users shows as one issue, not 10,000 noise events)
- Source map symbolication (so the stack trace is readable)
- User context (which users are affected, what plan/segment)
- Release tracking (when did this first appear? did a deploy introduce it?)
- Alerting (paging someone before users start emailing support)

If I inherited a codebase using only `console.error` for errors, fixing that is literally the first PR I'd open.

---

### Trap 2: "Lighthouse score = real user experience"

**Trap name:** The Lab Data Illusion

**Why it's a trap:** Lighthouse runs in a controlled lab environment: simulated Moto G4 on slow 4G, no user behavioral variance, no third-party script timing variance, no CDN geographic variance, no cached state from previous visits. It's useful for catching obvious problems and tracking trends over time, but it cannot represent what real users experience.

**Correct answer:** Lighthouse is lab data. Real user experience is field data. The gap between them is often enormous:
- A user in Brazil on an actual 3G connection has a different experience than Lighthouse's simulation
- A returning user with a warm cache has much better performance than the cold-load Lighthouse tests
- Real-world JS execution varies wildly by device CPU

Field data comes from the Chrome User Experience Report (CrUX — aggregate, no user tracking) or your own RUM implementation using the `web-vitals` library reporting to your analytics backend. Core Web Vitals assessments in Search Console use CrUX data — that's what Google ranks you on, not your Lighthouse score.

I've seen teams spend a sprint chasing a 100 Lighthouse score while their p75 LCP in the field was 4.5 seconds because their hero image was served from a server with no CDN edge node near their primary user base.

---

### Trap 3: "Feature flags are just if/else statements"

**Trap name:** The Stateless Flag Fallacy

**Why it's a trap:** `if (FEATURE_FLAG_ENV_VAR)` is a build-time constant. A feature flag system is a runtime targeting engine. Treating them as equivalent means you miss every property that makes feature flags valuable.

**Correct answer:** Real feature flags require:
- **Consistent assignment:** The same user must get the same variant every time. This is done by hashing the user ID (not using `Math.random()`). Hash functions like MurmurHash3 or consistent hashing ensure deterministic bucketing.
- **Targeting rules:** Roll out to internal users first, then 1% → 5% → 20% → 100%, or target by country, plan, company, or any attribute.
- **Kill switch with no redeploy:** If the flag evaluation happens at runtime from a remote config service, you can turn off a bad feature in 30 seconds without touching code.
- **A/B experiment framework:** Assignment consistency is the prerequisite for valid A/B tests.
- **Flag evaluation in SSR:** Must be done with the server-side SDK so the first render matches what the client will show (no hydration mismatch).

If you build your own `if/else` with env vars, you get none of these. You also get feature flag debt that accumulates until nobody knows which flags are permanent and which are temporary, but that's a different problem.

---

### Trap 4: "Upload source maps to the public server alongside the bundle"

**Trap name:** The Source Code Exposure Trap

**Why it's a trap:** Publishing `.map` files on your CDN/public server alongside your JavaScript bundles is the default behavior of `devtool: 'source-map'` in webpack. Most developers enable this and move on without realizing they've just published their entire readable source code to the internet.

**What it exposes:**
- Your complete application business logic
- Internal API endpoint structures and naming conventions
- Comments that might include architectural decisions, TODO items, or security notes
- Environment variable names (not values, but names hint at structure)
- Component structure that reveals product roadmap

**Correct answer:** Generate source maps but never serve them publicly. Use `sentry-webpack-plugin` to upload them directly to Sentry after each build, then delete the `.map` files before deploying to your CDN. Tie them to a release identifier.

```javascript
// webpack.config.js
const { sentryWebpackPlugin } = require("@sentry/webpack-plugin");

module.exports = {
  devtool: "hidden-source-map", // generates maps but doesn't reference them in bundle
  plugins: [
    sentryWebpackPlugin({
      org: "my-org",
      project: "my-project",
      authToken: process.env.SENTRY_AUTH_TOKEN,
      release: { name: process.env.SENTRY_RELEASE },
      sourcemaps: {
        assets: "./dist/**",
        deleteFilesAfterUpload: "./dist/**/*.map", // delete after upload
      },
    }),
  ],
};
```

---

### Trap 5: "A/B test everything at once"

**Trap name:** The Interaction Effect Trap

**Why it's a trap:** Running multiple concurrent A/B experiments on overlapping user populations creates interaction effects. Experiment A changes the button color. Experiment B changes the page layout. Users in variant A1+B2 have a completely different experience than A0+B0, and your analytics can't attribute the conversion difference correctly because you can't isolate which experiment (or their combination) caused the effect.

Additionally, running multiple experiments on the same page dilutes statistical power. If you need 1,000 users to detect a 5% lift in one experiment, you need proportionally more traffic when users are split across multiple experiments.

**Correct answer:**
- One primary experiment per page/feature area at a time
- If you must run concurrent experiments, use **mutual exclusion** (partition users so a user is in at most one experiment) — both GrowthBook and LaunchDarkly support this
- Use **holdout groups** (a portion of users excluded from all experiments) to measure the aggregate impact of your experimentation program
- Accept that experimentation velocity has a natural ceiling set by your traffic volume and desired statistical confidence

---

### Trap 6: "Session replay is just a nice-to-have debugging tool"

**Trap name:** The Privacy Afterthought Trap

**Why it's a trap:** Teams add session replay thinking it's just a debugging shortcut and skip the privacy analysis. The trap is that session replay records everything the user does in the DOM by default — including potentially filling in forms with email addresses, phone numbers, credit card numbers, or SSNs. Depending on your jurisdiction, that's a GDPR/CCPA/PCI violation.

There's also the performance trap: session replay adds meaningful payload to every page (typically 50-200KB for the SDK) and ongoing CPU/memory overhead for DOM mutation observation. Blindly enabling it in production for all users can regress your INP and TTI.

**Correct answer:**
- Enable session replay only after confirming privacy masking covers all sensitive inputs and text content (`maskAllInputs: true` is the safe default)
- Gate replay behind consent (same as analytics)
- Use sampling to limit replay collection to a percentage of sessions — you don't need replays of every session, just enough to reproduce reported bugs
- Audit the replay with a security engineer before enabling in production
- Review your vendor's data residency — does replay data leave the region where your users are?

```typescript
Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  integrations: [
    Sentry.replayIntegration({
      maskAllInputs: true,
      maskAllText: false,
      blockAllMedia: false,
      // Only capture 10% of sessions, 100% of sessions with errors
      sessionSampleRate: 0.1,
      errorSampleRate: 1.0,
    }),
  ],
});
```

---

## 6. Production TypeScript/React Code Examples

---

### Example 1: Sentry ErrorBoundary with Fallback UI and Reset

```typescript
// components/FeatureErrorBoundary.tsx
import * as Sentry from "@sentry/react";
import { type ReactNode } from "react";

interface Props {
  feature: string;
  children: ReactNode;
}

export function FeatureErrorBoundary({ feature, children }: Props) {
  return (
    <Sentry.ErrorBoundary
      beforeCapture={(scope) => {
        scope.setTag("feature", feature);
        scope.setLevel("error");
      }}
      fallback={({ resetError }) => (
        <div role="alert" className="error-fallback">
          <p>Something went wrong in {feature}.</p>
          <button onClick={resetError}>Try again</button>
        </div>
      )}
    >
      {children}
    </Sentry.ErrorBoundary>
  );
}
```

---

### Example 2: Sentry Init with User Context and Replay

```typescript
// lib/sentry.ts
import * as Sentry from "@sentry/react";

export function initSentry() {
  Sentry.init({
    dsn: process.env.NEXT_PUBLIC_SENTRY_DSN!,
    release: process.env.NEXT_PUBLIC_SENTRY_RELEASE,
    environment: process.env.NODE_ENV,
    tracesSampleRate: 0.2,
    integrations: [
      Sentry.browserTracingIntegration(),
      Sentry.replayIntegration({
        maskAllInputs: true,
        sessionSampleRate: 0.05,
        errorSampleRate: 1.0,
      }),
    ],
  });
}

export function identifyUser(user: { id: string; email: string; plan: string }) {
  Sentry.setUser({ id: user.id, email: user.email });
  Sentry.setTag("plan", user.plan);
}
```

---

### Example 3: web-vitals Reporting to Analytics

```typescript
// lib/vitals.ts
import { onCLS, onFCP, onINP, onLCP, onTTFB, type Metric } from "web-vitals";

function reportToAnalytics(metric: Metric) {
  const { name, value, rating, id } = metric;
  window.gtag?.("event", name, {
    event_category: "Web Vitals",
    event_label: id,
    value: Math.round(name === "CLS" ? value * 1000 : value),
    non_interaction: true,
    metric_rating: rating, // "good" | "needs-improvement" | "poor"
  });
}

export function initWebVitals() {
  onCLS(reportToAnalytics);
  onFCP(reportToAnalytics);
  onINP(reportToAnalytics);
  onLCP(reportToAnalytics);
  onTTFB(reportToAnalytics);
}
```

---

### Example 4: Feature Flag Hook with LaunchDarkly

```typescript
// hooks/useFeatureFlag.ts
import { useFlags, useLDClient } from "launchdarkly-react-client-sdk";
import { useEffect } from "react";

export function useFeatureFlag<T>(
  flagKey: string,
  defaultValue: T
): { value: T; isLoading: boolean } {
  const flags = useFlags();
  const ldClient = useLDClient();
  const isLoading = !ldClient?.initialized();

  const value = (flags[flagKey] ?? defaultValue) as T;
  return { value, isLoading };
}

// Usage
function CheckoutButton() {
  const { value: showNewFlow, isLoading } = useFeatureFlag("checkout-v2", false);
  if (isLoading) return <ButtonSkeleton />;
  return showNewFlow ? <NewCheckoutButton /> : <LegacyCheckoutButton />;
}
```

---

### Example 5: GrowthBook A/B Test Hook

```typescript
// hooks/useExperiment.ts
import { useExperiment } from "@growthbook/growthbook-react";

type Variant = "control" | "variant_a" | "variant_b";

export function useCheckoutExperiment() {
  const { value, inExperiment } = useExperiment<Variant>({
    key: "checkout-redesign-2025",
    variations: ["control", "variant_a", "variant_b"],
  });
  return { variant: value, inExperiment };
}
```

---

### Example 6: SPA Page View Tracking Hook (GA4)

```typescript
// hooks/usePageTracking.ts
import { useEffect, useRef } from "react";
import { useLocation } from "react-router-dom";

export function usePageTracking() {
  const location = useLocation();
  const prevPath = useRef<string | null>(null);

  useEffect(() => {
    const path = location.pathname + location.search;
    if (path === prevPath.current) return; // prevent duplicate fires
    prevPath.current = path;
    window.gtag?.("event", "page_view", { page_path: path });
  }, [location]);
}
```

---

### Example 7: Structured Frontend Log Sender

```typescript
// lib/logger.ts
interface LogPayload {
  level: "info" | "warn" | "error";
  message: string;
  context?: Record<string, unknown>;
}

const traceId = crypto.randomUUID();

export async function sendLog(payload: LogPayload) {
  await fetch("/api/logs", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Trace-Id": traceId,
    },
    body: JSON.stringify({
      ...payload,
      timestamp: new Date().toISOString(),
      traceId,
      userAgent: navigator.userAgent,
    }),
  });
}
```

---

### Example 8: Sentry Custom Breadcrumb on Route Change

```typescript
// components/SentryRouteInstrumentation.tsx
import * as Sentry from "@sentry/react";
import { useEffect } from "react";
import { useLocation } from "react-router-dom";

export function SentryRouteInstrumentation() {
  const location = useLocation();
  useEffect(() => {
    Sentry.addBreadcrumb({
      category: "navigation",
      message: `Navigated to ${location.pathname}`,
      level: "info",
      data: { search: location.search, hash: location.hash },
    });
  }, [location]);
  return null;
}
```

---

### Example 9: Consent-Gated Analytics Init

```typescript
// lib/analytics.ts
type ConsentStatus = "granted" | "denied" | "pending";

let analyticsInitialized = false;

export function onConsentChange(status: ConsentStatus) {
  if (status !== "granted" || analyticsInitialized) return;
  analyticsInitialized = true;

  // GA4 consent update
  window.gtag?.("consent", "update", {
    analytics_storage: "granted",
    ad_storage: "denied", // never grant ad storage without explicit consent
  });

  // PostHog opt-in
  window.posthog?.opt_in_capturing();
}
```

---

## 7. Interview Cheat Sheet

```
┌──────────────────────────────────────────────────────────────────────┐
│              FRONTEND OBSERVABILITY CHEAT SHEET                      │
│              15-YOE Architect Quick Reference                        │
└──────────────────────────────────────────────────────────────────────┘

ERROR TRACKING
─────────────
  Sentry v8+: ErrorBoundary + global unhandledrejection + performance
  Source maps: hidden-source-map → sentry-webpack-plugin → deleteAfterUpload
  Release: SENTRY_RELEASE = git rev-parse HEAD (set in CI)
  User context: Sentry.setUser({ id, email }) — do NOT set before consent
  Breadcrumbs: addBreadcrumb() at key UI interactions, not just errors
  Scope: Sentry.withScope(scope => scope.setExtra(...)) for per-event context

SOURCE MAPS
───────────
  WRONG: devtool: 'source-map' + deploy .map files to CDN
  RIGHT: devtool: 'hidden-source-map' + sentry-webpack-plugin + deleteFilesAfterUpload
  Key: release identifier must match between build and runtime init
  Verify: sentry-cli releases files <release> list

RUM / WEB VITALS
───────────────
  Library: web-vitals (Google-maintained, same metrics as CrUX)
  Metrics: LCP <2.5s | INP <200ms | CLS <0.1 | FCP | TTFB
  Field vs Lab: CrUX/RUM = truth; Lighthouse = useful signal, not ground truth
  Report: send onCLS/onINP/onLCP to GA4 as non_interaction events
  INP fix: startTransition for heavy renders, yield with scheduler.yield()

FEATURE FLAGS
─────────────
  Providers: LaunchDarkly (enterprise) | GrowthBook (OSS) | PostHog FF
  SSR: evaluate with server SDK → bootstrap client SDK → no hydration flash
  Assignment: deterministic hash of user ID = consistent bucketing
  Kill switch: change flag in dashboard → live within seconds, no deploy
  Debt: schedule flag removal in the PR that adds the flag

A/B TESTING
──────────
  Pre-calculate sample size before starting (use power calculator)
  Don't peek: lock results until target sample size reached
  One primary metric per experiment
  Concurrent tests: use mutual exclusion layers (GB/LD support this)
  Holdout group: 5-10% excluded from all experiments for baseline

ANALYTICS
─────────
  GA4 SPA: fire page_view manually on location change (useLocation hook)
  GA4 custom dims: set before event, user-scoped vs event-scoped
  PostHog self-hosted: GDPR-safe, no data leaves your infra
  Privacy proxy: route events through your own domain → strip PII → forward

SESSION REPLAY
─────────────
  Sentry Replay: maskAllInputs: true (default safe)
  LogRocket: inputSanitizer: true
  Sampling: sessionSampleRate: 0.05-0.1, errorSampleRate: 1.0
  Gate behind consent — replay = personal data under GDPR
  Performance cost: ~50-200KB SDK + DOM mutation observer CPU

ALERTING
────────
  Sev1 (page): error rate 3x baseline | LCP p75 > 4s | checkout drop >50%
  Sev2 (Slack): new issue >100/hr | LCP >2.5s sustained | flag eval errors
  Do NOT alert on: known bot errors | individual session spikes | 3rd party timeouts
  Sentry: alert rules with !has:assignee is:unresolved to reduce noise
  Integrate: PagerDuty sev1 | Slack webhook sev2

PRIVACY
───────
  Consent gate: init analytics/replay ONLY after consent
  GA4 consent mode: update storage grants, never grant ad_storage without explicit consent
  PII: never send email/name/ssn/CC to third-party analytics
  PostHog self-hosted: cleanest GDPR answer for EU-facing products
  Source maps: private upload only — never public (IP exposure)

CORRELATION / LOGGING
────────────────────
  Generate traceId = crypto.randomUUID() per session
  Attach to: Sentry tag | all fetch headers (X-Trace-Id) | log payloads
  Backend: log X-Trace-Id on every request log line
  Result: Sentry event → grep traceId in ELK/Datadog → full server trace

COMMON TRAP ANSWERS
───────────────────
  "console.error is enough"       → NO. No aggregation, alerting, context, maps.
  "Lighthouse = real experience"  → NO. Lab data. Field data (RUM/CrUX) is truth.
  "Flags are just if/else"        → NO. Consistent assignment, targeting, no-redeploy kills.
  "Public source maps are fine"   → NO. Exposes source. Upload to Sentry only.
  "A/B test everything at once"   → NO. Interaction effects. One primary per page.
  "Replay is low-risk debug tool" → NO. PII risk, GDPR, performance overhead.

TOOLS MAP
─────────
  Error tracking   : Sentry (primary), Datadog APM (enterprise)
  RUM              : Sentry Performance, Datadog RUM, SpeedCurve
  Feature flags    : LaunchDarkly, GrowthBook (OSS), PostHog FF
  Analytics        : GA4, PostHog (self-hosted for GDPR), Amplitude
  Session replay   : Sentry Replay, LogRocket, FullStory
  Alerting         : PagerDuty, Opsgenie, Slack webhooks
  Log aggregation  : Datadog, ELK Stack, Grafana Loki
  A/B testing      : GrowthBook, Statsig, LaunchDarkly Experiments
```

---

## 8. Quick Reference: Key Configuration Patterns

### Sentry Webpack Plugin (Production Setup)

```typescript
// webpack.config.ts
import { sentryWebpackPlugin } from "@sentry/webpack-plugin";

export default {
  devtool: "hidden-source-map",
  plugins: [
    sentryWebpackPlugin({
      org: process.env.SENTRY_ORG!,
      project: process.env.SENTRY_PROJECT!,
      authToken: process.env.SENTRY_AUTH_TOKEN!,
      release: { name: process.env.SENTRY_RELEASE! },
      sourcemaps: {
        assets: "./dist/**",
        deleteFilesAfterUpload: ["./dist/**/*.map"],
      },
      telemetry: false,
    }),
  ],
};
```

### LaunchDarkly Provider (Next.js App Router)

```typescript
// app/providers.tsx
"use client";
import { LDProvider } from "launchdarkly-react-client-sdk";

export function FlagProvider({ user, bootstrapData, children }) {
  return (
    <LDProvider
      clientSideID={process.env.NEXT_PUBLIC_LD_CLIENT_ID!}
      context={{ kind: "user", key: user.id, plan: user.plan }}
      options={{ bootstrap: bootstrapData }} // from server SDK
    >
      {children}
    </LDProvider>
  );
}
```

### Performance Budget CI Check

```typescript
// scripts/check-budgets.ts
const BUDGETS = {
  LCP_P75_MS: 2500,
  INP_P75_MS: 200,
  CLS_P75: 0.1,
};

async function checkBudgets() {
  const metrics = await fetchRUMMetrics(); // from your RUM API
  const violations = Object.entries(BUDGETS).filter(
    ([key, budget]) => metrics[key] > budget
  );
  if (violations.length > 0) {
    console.error("Performance budget violations:", violations);
    process.exit(1); // fail CI
  }
}
checkBudgets();
```

---

## 9. Closing Context: What Separates 15-YOE Answers

A senior will describe what tools do. An architect explains the failure modes, the incentive structures, and the organizational patterns that make observability actually work.

**What interviewers probe for at architect level:**

- Do you know why Lighthouse and field data diverge? (Geographic variance, behavioral variance, caching state)
- Have you debugged a broken source map upload pipeline? (Release mismatch, publicPath misconfiguration)
- Can you explain why A/B test peeking is statistically invalid? (Multiple comparisons problem, early stopping inflation)
- Have you designed a privacy-compliant analytics architecture? (Consent gates, self-hosted, PII scrubbing)
- Can you explain feature flag consistent assignment at a technical level? (Hash function on user ID, not Math.random)
- Do you know the organizational failure mode of alert fatigue? (Too many alerts → on-call ignores them → real incident missed)

The difference between "I've used Sentry" and "I've owned observability for a 50-engineer frontend org" shows up in questions like "what's the first thing that breaks when you scale from 3 to 30 frontend engineers?" The answer is: alerting becomes noisy and unowned, source map uploads start failing silently in CI, and nobody knows which feature flags are safe to remove. You've seen these problems. Talk about them.
