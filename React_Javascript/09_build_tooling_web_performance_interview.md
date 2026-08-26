# Build Tooling & Web Performance — 15-YOE Interview Prep

---

## 1. Big Picture: The Modern Build Pipeline

```
SOURCE CODE
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│  TRANSFORM STAGE                                                │
│                                                                 │
│  TypeScript/JSX ──► esbuild / SWC / Babel ──► ES5/ESNext JS    │
│  SCSS/PostCSS   ──► CSS Processor          ──► Optimized CSS    │
│  Assets         ──► Asset Pipeline         ──► Hashed files     │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│  BUNDLE STAGE                                                   │
│                                                                 │
│  Entry Points ──┐                                              │
│  node_modules ──┼──► Dependency Graph ──► Module Federation    │
│  Dynamic Imports┘          │                                   │
│                             ▼                                   │
│               ┌─────────────────────────┐                      │
│               │  Tree Shaking (ESM only) │                      │
│               │  Dead code elimination   │                      │
│               └─────────────────────────┘                      │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│  OPTIMIZE STAGE                                                 │
│                                                                 │
│  JS Minification   ──► Terser / esbuild minify                 │
│  CSS Minification  ──► cssnano / lightningcss                  │
│  Code Splitting    ──► Route chunks + vendor chunks            │
│  Image Optimization──► WebP/AVIF conversion, responsive        │
│  Source Maps       ──► Separate .map files (prod)              │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│  OUTPUT STAGE                                                   │
│                                                                 │
│  dist/                                                          │
│  ├── main.[contenthash].js      (app code)                     │
│  ├── vendor.[contenthash].js    (node_modules chunk)           │
│  ├── route-dashboard.[hash].js  (lazy route)                   │
│  ├── styles.[contenthash].css                                  │
│  └── assets/logo.[hash].webp                                   │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│  DEPLOY STAGE                                                   │
│                                                                 │
│  CI/CD Pipeline                                                 │
│  ├── Performance Budget check (size-limit, Lighthouse CI)      │
│  ├── Upload to CDN (S3 + CloudFront / Fastly / Cloudflare)     │
│  ├── Set cache headers (immutable for hashed assets)           │
│  └── Update service worker manifest                            │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
   END USERS
   Real User Monitoring (RUM) → Core Web Vitals → Alerting
```

---

## 2. Conversational Interview Script

**Interviewer**: Walk me through how you think about build tooling choices for a large enterprise React app.

**You**: Sure. The first question I ask is: what's the team's pain? If it's slow local dev — people waiting 30 seconds for HMR — that points to Vite or a Turbopack migration. If it's build correctness at scale — custom loaders, module federation, migrating from an older stack — that's still Webpack territory.

At my last company we had a 400k-LOC dashboard app. Webpack 5 build was 4 minutes cold, 8-second HMR. We migrated to Vite for development, kept Webpack for production builds because we had a Module Federation setup sharing components across three micro-frontends. Vite's rollup-based production build didn't support Module Federation at the time, so the split was: Vite for DX, Webpack for production. Dev build time dropped from 4 minutes to under 15 seconds.

**Interviewer**: Why is Vite so much faster in development specifically?

**You**: Two reasons that compound each other. First, native ES Modules in the browser. Vite doesn't bundle in dev at all — it serves files individually over native ESM. The browser does the module resolution. Second, esbuild for pre-bundling node_modules. esbuild is written in Go and is 10-100x faster than JavaScript-based transpilers. So your third-party dependencies get pre-bundled once, cached, and served as a single chunk. Your source files are served unbundled with instant HMR at the module level rather than reprocessing the whole entry.

The trade-off is that in very large apps with thousands of modules, the initial page load in dev can actually be slower because the browser makes hundreds of requests. We had a case where our e-commerce app had 800+ direct imports and the dev server first load took 6 seconds. We solved it by splitting into sub-packages.

**Interviewer**: Tell me about tree shaking. How confident are you that it's working?

**You**: Not very, without measurement. Tree shaking is one of those things engineers assume is working but often isn't. The core requirement is ESM — static import/export statements. CJS with require() cannot be statically analyzed. The bundler runs dead code elimination by marking exports as "used" or "unused" and dropping the unused ones.

The practical gotchas are: side effects. If a module runs code just by being imported — think global polyfills, CSS imports, event listener registration — the bundler can't safely remove it. That's what the `sideEffects` field in package.json controls. You set it to `false` if the package has no side effects, or list specific files that do. When that field is missing, Webpack and Rollup default to assuming everything has side effects and won't tree shake.

We actually had a 40kb regression once when a library we used published an update that accidentally removed their `sideEffects: false` annotation. Bundle analyzer caught it in the next PR review.

**Interviewer**: How do you enforce performance budgets?

**You**: Multiple layers. size-limit in the CI pipeline is the gate — it fails the build if any bundle exceeds defined thresholds. Lighthouse CI in a separate workflow gives the actual performance scores against a baseline. And we have RUM dashboards in Datadog tracking Core Web Vitals per page, per release, segmented by geography and device class.

The size-limit check is the fast feedback loop. Lighthouse CI runs against a staging deployment so it catches real render issues. And the RUM layer catches things neither of those find — like a slow third-party script that's only slow on mobile 4G in Southeast Asia.

---

## 3. Scenario-Based Q&As (Production Context)

### Q1: Your LCP is 4.2 seconds on the homepage. How do you debug it?

**Answer**: LCP measures when the largest content element is painted — typically a hero image or above-the-fold text block. I'd start in Chrome DevTools Performance tab to identify what the LCP element actually is, then check the waterfall:

1. Is the image being discovered late? If the `<img>` is injected by JavaScript after render, the browser can't preload it. Fix: add `<link rel="preload" as="image">` in the `<head>`, or better, put the image tag directly in HTML.
2. Is the image too large? Check if it's served as a PNG when it could be WebP/AVIF. A 500kb PNG becoming an 80kb AVIF is an immediate win.
3. Is the server TTFB high? SSR/SSG vs CSR makes a huge difference. If TTFB is over 600ms the server is the bottleneck, not the frontend.
4. Is there render-blocking CSS or fonts? `font-display: swap` prevents invisible text during font load. Remove blocking stylesheets from `<head>`.
5. Is there a redirect chain? An http→https→www redirect adds 200-400ms on each hop.

In production I'd also segment the RUM data — LCP often varies dramatically between desktop/mobile and between regions due to CDN PoP placement.

### Q2: A new engineer added lodash to the checkout page and now the bundle is 72kb larger. What do you do?

**Answer**: This is a classic lodash trap. CJS lodash (`import _ from 'lodash'`) pulls in the entire library even if you use one function. The fix options in order of preference:

1. Replace with lodash-es: `import { debounce } from 'lodash-es'` — ESM, tree-shakeable
2. Replace with native JS — most lodash utilities have native equivalents in ES2020+
3. Deep import: `import debounce from 'lodash/debounce'` — CJS but per-function

I'd also set up a lint rule (`eslint-plugin-lodash`) to enforce lodash-es imports, and add a bundle budget in size-limit specifically for the checkout chunk so this regression can't happen again silently.

### Q3: Your Webpack build is generating a 2.3MB main bundle. What's your systematic approach?

**Answer**: Four-step process. First, run webpack-bundle-analyzer — this gives a visual treemap. Most of the time you see immediately: a few huge libraries, some duplicate packages at different versions, or unexpectedly large polyfills.

Second, look for duplicates. `npm ls react` or `yarn why react` to see if multiple versions are bundled. Duplicate react alone can add 50-100kb. Fix with Webpack's `resolve.alias` or package manager resolutions field.

Third, check polyfill scope. If you're targeting modern browsers but have `@babel/polyfill` or a blanket `core-js` import, you're shipping unnecessary code. Switch to targeted polyfills via browserslist + `useBuiltIns: 'usage'`.

Fourth, code splitting. Move large vendor libraries to their own chunks and lazy-load routes. But — and this is important — don't over-split. I'll come back to that.

```js
// webpack.config.js — bundle analyzer setup
const BundleAnalyzerPlugin = require('webpack-bundle-analyzer').BundleAnalyzerPlugin;

module.exports = {
  plugins: [
    new BundleAnalyzerPlugin({
      analyzerMode: process.env.ANALYZE ? 'server' : 'disabled',
      openAnalyzer: true,
    }),
  ],
  optimization: {
    splitChunks: {
      chunks: 'all',
      cacheGroups: {
        vendor: {
          test: /[\\/]node_modules[\\/]/,
          name: 'vendors',
          priority: 10,
        },
        charts: {
          test: /[\\/]node_modules[\\/](recharts|d3|victory)/,
          name: 'charts-vendor',
          priority: 20,
        },
      },
    },
  },
};
```

### Q4: You need to add a new feature that uses a 400kb library only on one admin page. How do you handle it?

**Answer**: Dynamic import with React.lazy and Suspense. The library only loads when the admin page is rendered, not on initial app load.

```jsx
// AdminDashboard.tsx
import React, { Suspense, lazy } from 'react';

const HeavyChartLib = lazy(() =>
  import('./HeavyChartContainer').then(mod => ({
    default: mod.HeavyChartContainer,
  }))
);

export function AdminDashboard() {
  return (
    <Suspense fallback={<ChartSkeleton />}>
      <HeavyChartLib data={data} />
    </Suspense>
  );
}
```

In production I'd also add a prefetch hint on the admin nav link so the chunk loads in idle time while the user is still reading the current page, not when they click:

```jsx
<Link
  to="/admin"
  onMouseEnter={() => import('./HeavyChartContainer')}
>
  Admin
</Link>
```

### Q5: How do you set up source maps for production error tracking without exposing source to end users?

**Answer**: The key insight is that source maps don't have to be publicly accessible to be useful for error tracking. The pattern I use:

1. Generate `source-map` type (full fidelity) during build
2. Upload `.map` files to error tracking service (Sentry, Datadog) via their CLI/plugin during CI
3. Delete `.map` files from the deploy artifact before pushing to CDN
4. Set `X-SourceMap` or `//# sourceMappingURL` to point to an authenticated internal endpoint if needed

```js
// webpack.config.js — production source maps
module.exports = {
  devtool: process.env.NODE_ENV === 'production'
    ? 'hidden-source-map'  // generates maps but doesn't reference them in JS
    : 'eval-cheap-module-source-map',
};
```

`hidden-source-map` generates the `.map` files but doesn't add the `//# sourceMappingURL` comment, so browsers won't attempt to load them. Your CI uploads to Sentry, you never deploy the maps to your CDN.

### Q6: The marketing team wants to add a third-party analytics script. You're worried about INP regression. How do you approach it?

**Answer**: INP (Interaction to Next Paint) measures responsiveness — the delay from user interaction to the next frame. Third-party scripts are a major culprit because they compete for the main thread.

My requirements for any new third-party script:
1. Load with `async` or `defer` — never blocking
2. Prefer loading after `DOMContentLoaded` or on user idle using `requestIdleCallback`
3. Sandbox in a web worker if the script supports it (Partytown is a tool for this)
4. Measure INP before and after in a staging environment with WebPageTest
5. Set a budget: if it costs more than 20ms to INP p75, it doesn't go in without business justification and a mitigation plan

```html
<!-- Deferred third-party load -->
<script>
  window.addEventListener('load', () => {
    requestIdleCallback(() => {
      const script = document.createElement('script');
      script.src = 'https://analytics.example.com/script.js';
      script.async = true;
      document.head.appendChild(script);
    });
  });
</script>
```

### Q7: Your service worker is causing users to get stale content after a deploy. How do you fix it?

**Answer**: Classic stale service worker problem. The root cause is usually cache-first strategy without a proper update flow. My approach:

The service worker lifecycle: `install` → `waiting` → `activate`. When you deploy a new SW, it installs but waits until all tabs running the old SW are closed. Users on old tabs never get the update.

Fixes:
1. Use `skipWaiting()` in the new SW install event — but this can break in-flight requests
2. Prompt the user: "New version available — refresh" using the `waiting` state detection
3. Use Workbox's `updatefound` event to show a toast
4. For pure static assets: Workbox `staleWhileRevalidate` serves cache immediately but fetches fresh in background and updates cache for next load

```js
// service-worker.js with Workbox
import { registerRoute } from 'workbox-routing';
import { StaleWhileRevalidate, CacheFirst } from 'workbox-strategies';

// Static assets: cache-first with content hash
registerRoute(
  ({ request }) => request.destination === 'script' || request.destination === 'style',
  new CacheFirst({ cacheName: 'static-assets' })
);

// API responses: stale-while-revalidate
registerRoute(
  ({ url }) => url.pathname.startsWith('/api/'),
  new StaleWhileRevalidate({ cacheName: 'api-cache' })
);
```

### Q8: How do you handle font loading to avoid invisible text and layout shift?

**Answer**: Two separate problems: FOIT (Flash of Invisible Text) and CLS (layout shift from font metrics changing).

For FOIT: `font-display: swap` in the @font-face declaration. Text renders immediately in fallback font, swaps when custom font loads. For body text this is usually fine.

For CLS: the font swap changes the letter spacing, line height, word wrap — causing layout shift. The modern solution is `size-adjust`, `ascent-override`, `descent-override` CSS properties to make the fallback font metrics match the custom font. The Font Loading API and tools like `fontaine` or Next.js's built-in font optimization do this automatically.

```css
/* Manual fallback font adjustment */
@font-face {
  font-family: 'Inter';
  src: url('/fonts/inter.woff2') format('woff2');
  font-display: swap;
}

@font-face {
  font-family: 'Inter-fallback';
  src: local('Arial');
  size-adjust: 107%;
  ascent-override: 90%;
  descent-override: 22%;
}

body {
  font-family: 'Inter', 'Inter-fallback', Arial, sans-serif;
}
```

Also: preload critical fonts in the `<head>`:

```html
<link rel="preload" href="/fonts/inter.woff2" as="font" type="font/woff2" crossorigin>
```

---

## 4. Advanced Scenario Q&As

### Advanced Q1: You need to implement Module Federation for a micro-frontend architecture. Walk through the design decisions.

**Answer**: Module Federation is Webpack 5's mechanism for sharing code between separately deployed applications at runtime. The mental model: each app is both a "host" (consumer) and "remote" (provider).

Key design decisions I've faced:

**Shared dependencies**: If both host and remote load React, you want only one copy at runtime. The `shared` config handles this. The trap is version mismatches — if host requires React 18.2 and remote provides 18.0, Federation has to decide whether to use the host's version or load both. Setting `singleton: true` forces one instance.

**Contract management**: The remote exposes components as if they're npm packages, but they're loaded at runtime from a URL. You get no TypeScript types automatically. We solved this by publishing type declaration packages from each remote that the host installs — not the actual code, just the types.

**Error boundaries**: A remote component failing shouldn't crash the host. Mandatory React error boundaries around every federated import.

**Versioning strategy**: We use content-hash-based remote URLs for stability but expose a manifest endpoint that maps logical names to hashed URLs. The host reads the manifest on startup.

```js
// webpack.config.js — remote app (product-catalog)
new ModuleFederationPlugin({
  name: 'productCatalog',
  filename: 'remoteEntry.js',
  exposes: {
    './ProductCard': './src/components/ProductCard',
    './useProductSearch': './src/hooks/useProductSearch',
  },
  shared: {
    react: { singleton: true, requiredVersion: '^18.0.0' },
    'react-dom': { singleton: true, requiredVersion: '^18.0.0' },
  },
}),
```

### Advanced Q2: Core Web Vitals are failing in field data (CrUX) but passing in Lighthouse. Why and how do you close the gap?

**Answer**: This is a real and common situation. Lighthouse is lab data — it runs in a controlled synthetic environment with a simulated mid-tier mobile device and throttled network. CrUX is real user data collected by Chrome from actual users, aggregated over 28 days.

Reasons field data is worse:
1. **Real device diversity**: Your users on 3-year-old Android phones have much slower CPUs than Lighthouse's simulation
2. **Third-party scripts**: Lighthouse sometimes doesn't load all third parties. Your users do
3. **Data freshness**: CrUX is 28-day rolling. A recent regression might not yet show in CrUX but will be live in 28 days
4. **Geographic variance**: Users in high-latency regions hurt your p75. Lighthouse tests from a single location
5. **User interaction patterns**: INP requires real user interaction; Lighthouse simulates standard interactions

How I close the gap:
- Set up real user monitoring with web-vitals.js reporting to your analytics
- Use WebPageTest with real device profiles (actual Android phones on 4G)
- Deploy Lighthouse CI against staging but don't treat it as the source of truth for production
- Segment CrUX data by device category and country to find where you're failing

```js
// web-vitals RUM reporting
import { onCLS, onINP, onLCP } from 'web-vitals';

function sendToAnalytics({ name, value, id, rating }) {
  fetch('/api/vitals', {
    method: 'POST',
    body: JSON.stringify({
      metric: name,
      value: Math.round(value),
      rating,         // 'good', 'needs-improvement', 'poor'
      url: location.href,
      userAgent: navigator.userAgent,
    }),
  });
}

onCLS(sendToAnalytics);
onINP(sendToAnalytics);
onLCP(sendToAnalytics);
```

### Advanced Q3: You're building an e-commerce site that needs to work offline. Design the service worker caching strategy.

**Answer**: The key is matching caching strategy to content characteristics. No single strategy fits everything.

I categorize content into four buckets:

**App shell** (HTML, CSS, JS bundles): CacheFirst with versioning. These have content hashes in filenames, so a new deploy = new URL = cache miss = fresh content. The old URLs stay cached and still work for users mid-session.

**Product catalog API** (/api/products): StaleWhileRevalidate. Show cached data instantly, fetch fresh in background. Acceptable staleness for browsing, not for checkout.

**Product images**: CacheFirst with size limit. Cache images aggressively but cap the cache at 50MB to avoid filling mobile storage. Use Cache API's `CacheStorage` with expiry metadata.

**Checkout/payment API**: NetworkFirst with fallback to "you're offline, try again." Never cache payment data.

```js
// workbox.config.js
import { precacheAndRoute } from 'workbox-precaching';
import { registerRoute } from 'workbox-routing';
import { CacheFirst, NetworkFirst, StaleWhileRevalidate } from 'workbox-strategies';
import { ExpirationPlugin } from 'workbox-expiration';

precacheAndRoute(self.__WB_MANIFEST); // app shell

registerRoute(
  ({ url }) => url.pathname.startsWith('/api/products'),
  new StaleWhileRevalidate({ cacheName: 'product-api' })
);

registerRoute(
  ({ request }) => request.destination === 'image',
  new CacheFirst({
    cacheName: 'images',
    plugins: [new ExpirationPlugin({ maxEntries: 200, maxAgeSeconds: 7 * 24 * 60 * 60 })],
  })
);

registerRoute(
  ({ url }) => url.pathname.startsWith('/api/checkout'),
  new NetworkFirst({ networkTimeoutSeconds: 10 })
);
```

### Advanced Q4: Walk through a complete polyfill strategy for a large app targeting 95% of browsers while minimizing bundle size.

**Answer**: The naive approach — include all polyfills — adds 80-120kb to every user's download including users on modern browsers who don't need any of it. The smart approach has three layers:

**Layer 1: browserslist config**. Define your actual target in `.browserslistrc`. This drives both Babel transforms and core-js polyfill inclusion. I query based on actual analytics data, not a default config.

**Layer 2: Babel + core-js `useBuiltIns: 'usage'`**. Babel analyzes which features you actually use and only includes polyfills for those features, targeted to your browserslist. If you never use `WeakRef`, it's never included.

**Layer 3: Differential serving (module/nomodule)**. Build two bundles: one for modern browsers (ES modules, no transforms) and one legacy bundle. Modern browsers load the slim ESM bundle; IE11 and old Androids load the legacy one. The `type="module"` / `nomodule` attributes in HTML handle the routing.

```js
// babel.config.js
module.exports = {
  presets: [
    ['@babel/preset-env', {
      useBuiltIns: 'usage',
      corejs: 3,
      targets: 'extends @acme/browserslist-config',
    }],
  ],
};
```

```
# .browserslistrc
[production]
> 0.5%
last 2 Chrome versions
last 2 Firefox versions
last 2 Safari versions
last 2 Edge versions
not dead
not IE 11  # explicit opt-out if business requirements allow
```

The discipline is revisiting this config every 6-12 months. As browsers auto-update, your "last 2 versions" coverage shifts and you can drop older polyfills. We removed IE11 support last year and saved 48kb per user.

---

## 5. Senior Trap Questions

### Trap 1: "Vite is better than Webpack in all scenarios."

**The Trap**: Assuming Vite is a drop-in replacement that is universally superior.

**The Reality**: Vite uses Rollup under the hood for production builds, not esbuild. Rollup is excellent but has its own limitations. Webpack still has advantages in:
- Module Federation (Webpack 5's native feature — Vite's equivalent `vite-plugin-federation` has limitations)
- Deep customization via loaders and the full plugin ecosystem
- Very large codebases where Rollup's build memory usage can be an issue
- Teams with existing Webpack expertise and complex custom configurations
- SSR scenarios where the bundling model differs significantly

**Correct Answer**: "Vite wins on developer experience, especially HMR speed in dev. For production, it's project-specific. I wouldn't migrate a working Webpack 5 setup with Module Federation just because Vite is trendy. I'd migrate if the DX pain is costing team velocity."

---

### Trap 2: "Tree shaking removes all dead code from your bundle."

**The Trap**: Assuming tree shaking is automatic and complete.

**The Reality**: Three things break tree shaking silently:
1. CommonJS modules (require/module.exports) — not statically analyzable, the entire module gets included
2. Missing `sideEffects: false` in package.json — bundler conservatively includes everything
3. Dynamic imports with variables — `import(someVariable)` cannot be statically analyzed

**The Test**: Check if your tree shaking is actually working by adding a named export you never import and verifying it's absent in the bundle. Many engineers assume it works but have never verified.

**Correct Answer**: "Tree shaking works on ESM only, requires proper sideEffects annotation, and has caveats around dynamic imports. I verify it works by checking the bundle analyzer output, not by assumption."

---

### Trap 3: "Our bundle is too big — let's add more code splitting."

**The Trap**: Over-splitting into too many small chunks, creating waterfall request chains.

**The Reality**: HTTP/2 multiplexing helps, but there's still overhead per request — connection establishment, cache lookup, service worker interception. A page that needs to load 40 separate 5kb chunks is often slower than loading 2 chunks of 100kb each, especially on mobile with high round-trip time.

Additionally, over-splitting breaks optimal gzip/brotli compression. Compression works better on larger files because patterns repeat across more data.

**The Balance**: Webpack's `minSize` and `maxSize` split chunk options exist for this reason. A typical sweet spot is chunks between 30kb-150kb. Route-based splitting is almost always worth it. Function-level splitting rarely is.

**Correct Answer**: "Splitting is a balance. I split by route boundary and by vendor libraries that can be shared across routes. I measure the actual request waterfall in the network panel rather than just looking at chunk count."

---

### Trap 4: "Source maps in production are a security risk — don't use them."

**The Trap**: Blanket rejection of production source maps due to security concern.

**The Reality**: Source maps are only a risk if they're publicly accessible. The two options are:
1. Publicly accessible source maps — yes, anyone can read your source. Real risk.
2. Hidden source maps uploaded only to your error tracking service (Sentry, etc.) — no public exposure, full error tracking fidelity

Without production source maps, error tracking stacks look like `minified.js:1:48291` and are nearly impossible to act on. The operational cost of poor error visibility is real and significant.

**Correct Answer**: "I use `hidden-source-map` in production — Webpack generates the map files but doesn't reference them in the JS output. CI uploads them to Sentry and then deletes them before CDN deploy. You get full stack traces in error tracking without any public exposure."

---

### Trap 5: "We got a Lighthouse score of 100 — our site is fast."

**The Trap**: Conflating a perfect Lighthouse score with real-world user performance.

**The Reality**: Lighthouse is a synthetic lab test. A 100 score means you did well under controlled, simulated conditions. Real user performance can differ because:
- Lab uses a specific device profile. Your users span from iPhone 15 to 4-year-old Android
- Lab uses a simulated network (typical 4G). Your users are on congested WiFi, slow 3G, or high-latency mobile
- Lab tests a single load. Users experience varying server response times, CDN cache states, and interference from other tabs
- Lab doesn't include the full range of third-party scripts that load in real sessions
- INP requires real user interactions — Lighthouse's interaction simulation is limited

**Correct Answer**: "Lighthouse 100 is a good signal that there's no obvious low-hanging fruit. But I don't celebrate it — I check CrUX field data, set up RUM with web-vitals.js, and look at p75 LCP/INP/CLS from real users before declaring the site fast."

---

### Trap 6: "Just enable gzip and you'll be fine for compression."

**The Trap**: Treating gzip as the end state of compression optimization.

**The Reality**: Brotli (br) compression achieves 15-25% better compression ratios than gzip, especially for text assets (JS, CSS, HTML). It's supported by all modern browsers and all major CDNs. Not using Brotli is leaving file size on the table.

Also, compression is most effective when combined with:
- Content-type-specific settings (higher compression for text, skip for already-compressed images)
- Static pre-compression during build (compress once, serve many times) vs dynamic compression (compress on every request)
- Correct `Vary: Accept-Encoding` headers so CDNs cache both compressed and uncompressed versions

**Correct Answer**: "We use Brotli as the primary compression algorithm with gzip fallback. Our Webpack build uses `compression-webpack-plugin` to generate both `.br` and `.gz` files at build time. Nginx/CloudFront serves the pre-compressed file based on the Accept-Encoding header."

---

## 6. Production Code Examples

### Vite Config (Enterprise React App)

```ts
// vite.config.ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
          'ui-vendor': ['@mui/material', '@emotion/react'],
          'charts': ['recharts'],
        },
      },
    },
    sourcemap: 'hidden',
    chunkSizeWarningLimit: 600,
  },
});
```

### size-limit Config (Performance Budget)

```json
// package.json
{
  "size-limit": [
    { "path": "dist/main.js", "limit": "150 kB" },
    { "path": "dist/vendor.js", "limit": "200 kB" },
    { "path": "dist/*.css", "limit": "30 kB" }
  ],
  "scripts": {
    "size": "size-limit",
    "ci:size": "size-limit --json"
  }
}
```

### Lighthouse CI Config

```js
// lighthouserc.js
module.exports = {
  ci: {
    collect: { url: ['https://staging.example.com/'] },
    assert: {
      assertions: {
        'categories:performance': ['error', { minScore: 0.85 }],
        'first-contentful-paint': ['warn', { maxNumericValue: 2000 }],
        'largest-contentful-paint': ['error', { maxNumericValue: 2500 }],
        'cumulative-layout-shift': ['error', { maxNumericValue: 0.1 }],
        'total-blocking-time': ['warn', { maxNumericValue: 300 }],
      },
    },
    upload: { target: 'lhci', serverBaseUrl: process.env.LHCI_SERVER_URL },
  },
};
```

### CSS Modules vs Tailwind Decision Point

```tsx
// CSS Modules — good for: complex component-specific styles, no PurgeCSS needed
import styles from './ProductCard.module.css';

export function ProductCard({ product }) {
  return (
    <div className={styles.card}>
      <img className={styles.image} src={product.imageUrl} alt={product.name} />
      <h2 className={styles.title}>{product.name}</h2>
    </div>
  );
}
```

```tsx
// Tailwind — good for: design system consistency, small final CSS with PurgeCSS
export function ProductCard({ product }) {
  return (
    <div className="rounded-lg shadow-md overflow-hidden hover:shadow-lg transition-shadow">
      <img className="w-full h-48 object-cover" src={product.imageUrl} alt={product.name} />
      <h2 className="text-lg font-semibold p-4 text-gray-900">{product.name}</h2>
    </div>
  );
}
```

**When NOT to use CSS-in-JS (runtime)**: Styled-components and emotion with runtime CSS generation add ~15kb overhead and defer style computation to JavaScript execution time. This hurts INP on mobile. For high-performance apps, prefer zero-runtime alternatives (Linaria, vanilla-extract) or CSS Modules.

### Content Hashing and Cache Headers Strategy

```nginx
# nginx.conf — CDN cache strategy
# Hashed assets (JS/CSS with content hash in filename): immutable
location ~* \.(js|css)$ {
  if ($uri ~* "\.[0-9a-f]{8,}\.(js|css)$") {
    add_header Cache-Control "public, max-age=31536000, immutable";
  }
}

# HTML: must revalidate on every request
location ~* \.html$ {
  add_header Cache-Control "no-cache, must-revalidate";
}

# Images with hash: long cache
location ~* \.(webp|avif|png|jpg)$ {
  add_header Cache-Control "public, max-age=2592000";
}
```

### Image Optimization Pipeline

```js
// Image component with format negotiation
export function OptimizedImage({ src, alt, width, height, priority = false }) {
  return (
    <picture>
      <source
        srcSet={`${src}.avif`}
        type="image/avif"
      />
      <source
        srcSet={`${src}.webp`}
        type="image/webp"
      />
      <img
        src={`${src}.jpg`}
        alt={alt}
        width={width}
        height={height}
        loading={priority ? 'eager' : 'lazy'}
        decoding={priority ? 'sync' : 'async'}
        fetchpriority={priority ? 'high' : 'auto'}
      />
    </picture>
  );
}
```

### Dynamic Import with Prefetch

```tsx
// Route-based splitting with prefetch on hover
import { lazy, Suspense } from 'react';

const AdminPanel = lazy(() => import(
  /* webpackChunkName: "admin" */
  /* webpackPrefetch: true */
  './pages/AdminPanel'
));

const routes = [
  {
    path: '/admin',
    element: (
      <Suspense fallback={<PageSkeleton />}>
        <AdminPanel />
      </Suspense>
    ),
  },
];
```

---

## 7. Core Web Vitals Reference Card

| Metric | Full Name | Good | Needs Improvement | Poor | Measured By |
|--------|-----------|------|-------------------|------|-------------|
| LCP | Largest Contentful Paint | ≤2.5s | 2.5–4s | >4s | Load performance |
| INP | Interaction to Next Paint | ≤200ms | 200–500ms | >500ms | Responsiveness |
| CLS | Cumulative Layout Shift | ≤0.1 | 0.1–0.25 | >0.25 | Visual stability |

**LCP causes**: Slow server (TTFB), render-blocking resources, slow image load, client-side rendering.

**INP causes**: Long JavaScript tasks on main thread, heavy event handlers, layout thrashing, third-party scripts.

**CLS causes**: Images/embeds without explicit dimensions, dynamic content insertion above fold, web font swap (without size-adjust).

---

## 8. Interview Cheat Sheet

### Build Tools at a Glance

| Concern | Dev | Prod | Notes |
|---------|-----|------|-------|
| **Vite** | native ESM, instant HMR | Rollup | Best DX for new projects |
| **Webpack 5** | slow HMR (improving) | Webpack | Module Federation, legacy |
| **Turbopack** | Rust-based, Vercel | in progress | Next.js 13+ default (beta) |
| **esbuild** | direct use | fast but limited | No tree shaking for CJS |

### Tree Shaking Requirements Checklist
- [ ] ESM (import/export) — not CJS
- [ ] `sideEffects: false` in package.json (or file list)
- [ ] No dynamic import with variable (`import(variable)`)
- [ ] `@babel/preset-env` not converting ESM to CJS (`modules: false`)
- [ ] Verified with bundle analyzer — not assumed

### Code Splitting Decision Matrix

| Split Type | When To Use | Risk |
|------------|-------------|------|
| Route-based | Always | Low |
| Component-based (lazy) | Heavy components >50kb | Low |
| Vendor chunks | Stable libraries | Low |
| Per-feature | Rarely loaded features | Medium |
| Micro-splits (<5kb each) | Never | Waterfall requests |

### Service Worker Caching Strategy by Content Type

| Content | Strategy | Reason |
|---------|----------|--------|
| App shell (hashed) | Cache First | Content hash = safe cache |
| API data | Stale While Revalidate | Fast + fresh |
| User data | Network First | Accuracy required |
| Payment/auth | Network Only | Never stale |
| Images | Cache First + expiry | Large, rarely changes |

### CDN Cache Header Rules
- Hashed assets (JS/CSS/images with hash): `Cache-Control: public, max-age=31536000, immutable`
- HTML: `Cache-Control: no-cache` (validates with etag, fast 304)
- API JSON: `Cache-Control: public, max-age=60, stale-while-revalidate=300`

### Key Interview Phrases

**On Vite vs Webpack**: "Vite wins on developer experience, but Webpack is still the right call for Module Federation and deeply customized build pipelines."

**On tree shaking**: "I verify tree shaking actually works with the bundle analyzer. The sideEffects annotation is the most commonly missed piece."

**On performance budgets**: "Size-limit in CI is the gate. Lighthouse CI is the signal. RUM is the ground truth."

**On source maps**: "I use `hidden-source-map` — generates maps for Sentry upload, never served publicly. The alternative is flying blind on production errors."

**On Core Web Vitals**: "Lighthouse is a starting point. CrUX field data is what Google uses for ranking. I always check p75 on real user data."

**On code splitting**: "Over-splitting is a real problem. Too many small chunks creates waterfall request chains. Route-level splitting is almost always right. Sub-component splitting needs measurement to justify."

**On polyfills**: "`useBuiltIns: 'usage'` with browserslist targeting — only polyfill what you actually use, only for browsers that need it. Revisit every 6 months as browser coverage shifts."

---

## Quick Reference: What Each Tool Is For

```
webpack-bundle-analyzer  → visualize bundle composition, find bloat
size-limit               → CI enforcement of size budgets
Lighthouse CI            → CI enforcement of performance scores
web-vitals.js            → RUM collection of Core Web Vitals
Workbox                  → Service worker caching strategy library
lightningcss / cssnano   → CSS minification
esbuild                  → Fast transpile/minify (Go-based)
SWC                      → Fast transpile (Rust-based, Babel replacement)
Partytown                → Move third-party scripts to web workers
fontaine / @next/font    → Font optimization, CLS prevention
sharp / squoosh          → Image format conversion (WebP/AVIF)
```
