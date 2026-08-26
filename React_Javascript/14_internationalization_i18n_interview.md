# Internationalization (i18n) — React Architect Interview Prep (15 YOE)

---

## 1. Big Picture Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        i18n ARCHITECTURE OVERVIEW                           │
└─────────────────────────────────────────────────────────────────────────────┘

  LOCALE DETECTION (ordered priority)
  ─────────────────────────────────────────────────────────────────────────
  1. URL path segment      /fr/dashboard          ← highest priority, shareable
  2. Subdomain             fr.myapp.com           ← SEO-friendly
  3. Query param           ?lang=fr               ← for testing / overrides
  4. Cookie                locale=fr              ← persisted user preference
  5. Accept-Language       HTTP header (server)   ← browser default
  6. User profile setting  DB column              ← authenticated users
  7. Fallback default      en                     ← always present

  TRANSLATION LOADING PIPELINE
  ─────────────────────────────────────────────────────────────────────────

  App Boot
      │
      ▼
  Detect Locale ──► "fr-CA"
      │
      ▼
  ┌───────────────────────────────────────────┐
  │  Lazy Load Strategy (dynamic import)      │
  │                                           │
  │  import(`./locales/${locale}/common.json`)│
  │  import(`./locales/${locale}/checkout.json│  ← namespace splitting
  │                                           │
  │  Suspense boundary shows skeleton/spinner │
  └───────────────────────────────────────────┘
      │
      ▼
  FALLBACK CHAIN
  ┌─────────────────────────────────────────────────────┐
  │  fr-CA  ──► fr  ──► en-US  ──► en  ──► KEY itself  │
  │                                                     │
  │  "button.submit" not in fr-CA?                      │
  │   → try fr (same language, different region)        │
  │   → try en-US (base language)                       │
  │   → try en (absolute fallback)                      │
  │   → show key "button.submit" (never blank)          │
  └─────────────────────────────────────────────────────┘
      │
      ▼
  RENDERING

  ┌─────────────────────────────────────────────────────┐
  │  RTL Support                                        │
  │                                                     │
  │  <html dir="rtl" lang="ar">                         │
  │                                                     │
  │  CSS Logical Properties:                            │
  │  margin-inline-start  (not margin-left)             │
  │  padding-inline-end   (not padding-right)           │
  │  border-start-color   (not border-left-color)       │
  │  text-align: start    (not text-align: left)        │
  │                                                     │
  │  Icons/arrows that indicate direction need flip:    │
  │  [chevron ›] ──RTL──► [‹ chevron]                   │
  │  transform: scaleX(-1) for directional icons        │
  └─────────────────────────────────────────────────────┘

  TRANSLATION MANAGEMENT WORKFLOW
  ─────────────────────────────────────────────────────────────────────────

  Developer writes code                 i18n("button.submit")
          │
          ▼
  i18next-scanner / i18next-parser      extracts keys from code
          │
          ▼
  Base locale file (en.json)            auto-populated with key stubs
          │
          ▼
  Crowdin / Lokalise                    translation management platform
          │
          ├── Human translators          professional per-language
          ├── TM (translation memory)    reuse previous translations
          └── Pseudo-locale testing      XXTESTXX wraps to find hardcoded strings
          │
          ▼
  CI/CD pull translations               crowdin download at build time
          │
          ▼
  Bundle split per locale               webpack/vite code splitting
          │
          ▼
  CDN-hosted locale files               served close to user
```

---

## 2. Core Concepts: i18n vs l10n

**Internationalization (i18n)** — The engineering infrastructure that makes a product *capable* of supporting multiple languages/regions. Done once, by developers. Examples: using `t()` instead of hardcoded strings, supporting dynamic layouts, using Intl APIs.

**Localization (l10n)** — The *content* and *cultural* adaptation for a specific locale. Done repeatedly, by translators/content teams. Examples: translating "Submit" to "Soumettre", formatting $1,234.56 as 1 234,56 € for fr-FR, changing date format from MM/DD/YYYY to DD/MM/YYYY.

**Distinction matters in interviews**: i18n is a one-time infrastructure investment. l10n is ongoing operational work. Conflating them signals shallow understanding.

---

## 3. Library Trade-offs: react-intl vs i18next/react-i18next

### react-intl (FormatJS)

**Strengths:**
- ICU message format — industry standard, handles plurals/gender/select natively
- Strong TypeScript support with code generation
- Tight integration with FormatJS ecosystem
- Backed by Yahoo/Slack/large enterprises

**Weaknesses:**
- More verbose API (component-based: `<FormattedMessage>`)
- No built-in lazy loading — you manage it yourself
- Smaller plugin ecosystem
- Migration from v2→v3→v5 has been painful historically

**Best for:** Enterprise apps where ICU compliance is mandatory, teams already on FormatJS ecosystem, apps needing strict message format validation.

### i18next / react-i18next

**Strengths:**
- Extremely flexible — plugins for everything (backend, language detection, caching)
- Namespace splitting built-in (load only what you need)
- Excellent lazy loading story with `i18next-http-backend`
- Massive ecosystem, 10M+ weekly downloads
- `useTranslation` hook is dead simple
- TypeScript key autocomplete with `react-i18next` type declarations

**Weaknesses:**
- Pluralization less strict than ICU by default (needs `i18next-icu` plugin for full CLDR)
- Configuration can get complex
- Default plural format is less expressive than ICU

**Best for:** Most production React apps. Especially good for SPAs with many lazy-loaded routes/modules, apps needing custom backends (translation stored in DB), and teams wanting TypeScript key safety.

**My default recommendation at 15 YOE:** i18next for new projects. react-intl only if the org has existing ICU message infrastructure or strict compliance needs.

---

## 4. Conversational Interview Script (15-YOE Architect Voice)

**Interviewer:** "Walk me through how you'd architect i18n for a large React application from scratch."

**You:** "I'd start by separating concerns clearly: detection, loading, rendering, and fallback handling are four distinct problems.

For detection, I establish a priority chain: URL path segment first because it's shareable and indexable, then cookie for returning users, then Accept-Language header as a sensible browser default. The URL-first approach also makes SSR straightforward — the server knows the locale from the first request without any client-side magic.

For loading, I never load all locales upfront. With 20 languages at 50KB each, that's a megabyte on initial load. Instead I use dynamic imports with Suspense boundaries — the detected locale loads on boot, additional locales only if the user switches. I also split by namespace — `common`, `checkout`, `dashboard` — so a user on the homepage doesn't download checkout translations.

For rendering, I'm opinionated about using i18next because the namespace splitting and plugin ecosystem are production-grade. Every user-visible string goes through `t()`. Dates, numbers, and currencies I format using `Intl.DateTimeFormat` and `Intl.NumberFormat` directly — no library needed, they're in every modern browser.

For RTL, I treat it as a first-class CSS concern from day one, not a bolt-on. That means CSS logical properties throughout — `margin-inline-start` instead of `margin-left`, `padding-inline-end` instead of `padding-right`. The `dir` attribute on `<html>` does most of the heavy lifting when logical properties are used consistently.

For fallbacks, I configure a chain: `fr-CA → fr → en`. That way regional variants benefit from the base language when a specific phrase hasn't been translated yet."

---

**Interviewer:** "What about TypeScript? How do you prevent typos in translation keys?"

**You:** "This is one of i18next's strongest features. You declare an `i18n` namespace in your TypeScript definitions pointing to your base locale JSON. The type system then enforces that every key you pass to `t()` actually exists in that JSON. You get full autocomplete in VS Code — it's a significant DX win.

The setup is about 10 lines of boilerplate in a `i18n.d.ts` file. The cost is that your base locale file becomes a source of truth that TypeScript validates against at compile time. Missing keys become compile errors, not silent runtime fallbacks. That's the tradeoff you want in a large codebase."

---

**Interviewer:** "How do you handle the case where a translator hasn't delivered translations for a new feature yet?"

**You:** "Two-layer strategy. First, fallback chain — if `fr` doesn't have a key, fall back to `en`. The user sees English rather than a missing key marker, which is acceptable for most product teams. Second, I add monitoring. I log missing translation keys to our observability platform in production. We get alerts when missing key rates spike — usually after a deploy that added new copy without corresponding translations. This creates accountability in the translation workflow without blocking releases."

---

## 5. Translation Key Strategies

### Flat Keys vs Nested Keys

**Flat:**
```json
{
  "button.submit": "Submit",
  "button.cancel": "Cancel",
  "checkout.total.label": "Total"
}
```

**Nested:**
```json
{
  "button": {
    "submit": "Submit",
    "cancel": "Cancel"
  },
  "checkout": {
    "total": {
      "label": "Total"
    }
  }
}
```

**Architect recommendation:** Nested with namespaces. Namespaces (`common`, `checkout`, `auth`) are the top-level split. Within a namespace, nested keys group related strings. This enables namespace-level lazy loading and makes Crowdin/Lokalise file organization cleaner.

### Context Keys

Use context keys when the same English word has different translations in context:

```json
{
  "button": {
    "submit": "Submit",
    "submit_checkout": "Place Order",
    "submit_feedback": "Send Feedback"
  }
}
```

i18next also has a built-in `context` feature: `t('button.submit', { context: 'checkout' })` maps to key `button.submit_checkout`. Useful when you want semantic separation without key proliferation.

---

## 6. Scenario Q&As

### Scenario 1: Pluralization for Russian (complex CLDR rules)

**Q:** "Your app launches in Russia. The word for 'item' has different forms depending on count. How do you handle this?"

**A:** Russian has four plural categories (one/few/many/other) based on CLDR rules:
- 1 item → "товар" (one)
- 2-4 items → "товара" (few)
- 5-20 items → "товаров" (many)
- 0 items → "товаров" (many/other)

i18next handles this with the `_one`, `_few`, `_many`, `_other` key suffixes when using the `i18next-icu` plugin or when configured with `pluralSeparator`. The translation file carries all forms:

```json
{
  "cart.items_one": "{{count}} товар",
  "cart.items_few": "{{count}} товара",
  "cart.items_many": "{{count}} товаров",
  "cart.items_other": "{{count}} товаров"
}
```

In code: `t('cart.items', { count: itemCount })` — i18next selects the right form automatically using the locale's CLDR plural rules.

The trap here is testing only with English and Arabic — those cover `one/other` and `zero/one/two/few/many/other` respectively. Russian exposes the `few` gap that purely binary plural systems miss.

---

### Scenario 2: SSR Hydration Mismatch with Locale

**Q:** "You're seeing React hydration errors on first load for international users. What's causing it and how do you fix it?"

**A:** Classic SSR/client locale mismatch. The server detects locale from the `Accept-Language` header and renders in French. The client boots, detects locale from a different source (say, a stale cookie with `en`), renders in English, and React finds a DOM mismatch.

Fix: Single source of truth. The server injects the detected locale into a `<script>` tag as `window.__INITIAL_LOCALE__ = 'fr'`. The client reads this before i18next initializes. Both server and client use the same value.

In Next.js, this is handled by the `i18n` config in `next.config.js` — Next manages locale routing and passes `locale` as a prop to every page via `getServerSideProps` / `getStaticProps`. The client never needs to re-detect.

---

### Scenario 3: Lazy Loading with Suspense

**Q:** "How do you implement lazy locale loading without showing blank content?"

**A:** i18next with `i18next-http-backend` handles the async load. I wrap the app with a Suspense boundary that shows a skeleton or spinner while translations load.

```tsx
// i18n.ts
import i18n from 'i18next';
import HttpBackend from 'i18next-http-backend';
import { initReactI18next } from 'react-i18next';

i18n
  .use(HttpBackend)
  .use(initReactI18next)
  .init({
    lng: window.__INITIAL_LOCALE__ ?? 'en',
    fallbackLng: 'en',
    ns: ['common'],
    defaultNS: 'common',
    backend: {
      loadPath: '/locales/{{lng}}/{{ns}}.json',
    },
    react: { useSuspense: true },
  });
```

```tsx
// App.tsx
import { Suspense } from 'react';
import { PageSkeleton } from './PageSkeleton';

export function App() {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <Router />
    </Suspense>
  );
}
```

The skeleton is critical — never show a blank screen or untranslated raw keys while loading.

---

### Scenario 4: RTL Layout for Arabic

**Q:** "You need to support Arabic. What breaks in your existing layout and how do you fix it?"

**A:** Everything that uses physical CSS properties breaks. `margin-left`, `padding-right`, `border-left`, `text-align: left`, absolute positioning with `left`/`right` — all of these are hardcoded to LTR.

The fix is CSS logical properties throughout:

| Physical (LTR-only) | Logical (both directions) |
|---------------------|---------------------------|
| `margin-left`       | `margin-inline-start`     |
| `margin-right`      | `margin-inline-end`       |
| `padding-left`      | `padding-inline-start`    |
| `padding-right`     | `padding-inline-end`      |
| `border-left`       | `border-inline-start`     |
| `text-align: left`  | `text-align: start`       |
| `left: 0`           | `inset-inline-start: 0`   |

With `<html dir="rtl">`, logical properties automatically flip. Zero JavaScript needed.

For Tailwind: use `ms-` (margin-start) instead of `ml-`, `pe-` instead of `pr-`. Tailwind 3.3+ has full logical property support.

Directional icons (arrows, chevrons, back buttons) need explicit handling — `transform: scaleX(-1)` or a separate icon variant.

BiDi text (mixed Arabic + English in one string) relies on the `unicode-bidi` CSS property and `dir="auto"` on text containers.

---

### Scenario 5: Translation Extraction Workflow

**Q:** "How do you ensure no hardcoded strings slip through to production?"

**A:** Three-layer defense:

1. **ESLint rule** — `eslint-plugin-i18n-checker` or a custom rule that flags string literals in JSX that aren't inside `t()` calls. Catches issues at save time.

2. **i18next-scanner in CI** — scans source files for `t('...')` calls, generates a diff against the current base locale file. CI fails if there are missing keys (developer forgot to add translation) or orphaned keys (key in JSON but no longer in code — translation debt).

3. **Pseudo-locale testing** — a special `xx` locale that wraps all strings in brackets: `"Submit"` becomes `"[Submit]"`. Run automated visual regression tests against the pseudo-locale. Any unbracketed text in the screenshots is a hardcoded string that escaped the ESLint rule.

---

### Scenario 6: Currency Formatting Without a Library

**Q:** "How would you format currency for multiple locales without adding a formatting library?"

**A:** `Intl.NumberFormat` — it's built into every modern browser and Node.js. Zero bundle cost.

```ts
function formatCurrency(
  amount: number,
  currency: string,
  locale: string
): string {
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
  }).format(amount);
}

// formatCurrency(1234.5, 'USD', 'en-US')  → "$1,234.50"
// formatCurrency(1234.5, 'EUR', 'fr-FR')  → "1 234,50 €"
// formatCurrency(1234.5, 'JPY', 'ja-JP')  → "¥1,235" (0 decimal places)
```

The JPY example catches people off-guard — `minimumFractionDigits: 2` is ignored for currencies that don't have fractional units. The `Intl` API handles this correctly out of the box.

---

### Scenario 7: Relative Time Formatting

**Q:** "How do you show '3 hours ago' in multiple languages?"

**A:** `Intl.RelativeTimeFormat`:

```ts
function formatRelativeTime(date: Date, locale: string): string {
  const rtf = new Intl.RelativeTimeFormat(locale, { numeric: 'auto' });
  const diffMs = date.getTime() - Date.now();
  const diffSec = Math.round(diffMs / 1000);
  const diffMin = Math.round(diffSec / 60);
  const diffHour = Math.round(diffMin / 60);
  const diffDay = Math.round(diffHour / 24);

  if (Math.abs(diffSec) < 60) return rtf.format(diffSec, 'second');
  if (Math.abs(diffMin) < 60) return rtf.format(diffMin, 'minute');
  if (Math.abs(diffHour) < 24) return rtf.format(diffHour, 'hour');
  return rtf.format(diffDay, 'day');
}
// locale 'en': "3 hours ago"
// locale 'fr': "il y a 3 heures"
// locale 'ar': "منذ ٣ ساعات"
```

Again: no library. Browser-native. Handles pluralization correctly per locale automatically.

---

### Scenario 8: Namespace Splitting for Performance

**Q:** "You have 200KB of translations total. How do you avoid sending all of it to every user?"

**A:** Namespace splitting + route-based lazy loading.

Split translations by feature domain:
- `common.json` — nav, buttons, errors (~10KB, loaded always)
- `auth.json` — login, signup, password reset (~5KB, loaded on auth routes)
- `checkout.json` — cart, payment, order (~20KB, loaded on checkout routes)
- `dashboard.json` — analytics, reports (~30KB, loaded on dashboard routes)

```ts
// On checkout route mount
i18n.loadNamespaces(['checkout']).then(() => {
  // Now t('checkout:cart.total') works
});

// Hook usage with namespace
const { t } = useTranslation(['common', 'checkout']);
```

A user visiting only the home page downloads `common.json` (~10KB). A checkout user downloads `common.json` + `checkout.json` (~30KB). No one downloads all 200KB unless they visit every feature.

---

## 7. Advanced Scenario Q&As

### Advanced 1: TypeScript Key Safety

**Q:** "How do you get TypeScript to autocomplete translation keys and catch typos at compile time?"

**A:** i18next has a first-class TypeScript story. You augment the `i18next` module's `CustomTypeOptions` interface:

```ts
// src/types/i18next.d.ts
import type common from '../locales/en/common.json';
import type checkout from '../locales/en/checkout.json';

declare module 'i18next' {
  interface CustomTypeOptions {
    defaultNS: 'common';
    resources: {
      common: typeof common;
      checkout: typeof checkout;
    };
  }
}
```

After this, `t('button.submit')` works — `t('button.submitX')` is a TypeScript error. The JSON file IS the type definition. You get autocomplete in VS Code for every valid key path.

The subtlety: this only covers the base locale (en). Other locale files don't need to be typed — they're validated at runtime via the fallback chain, not at compile time. Trying to type all locales creates a maintenance nightmare.

---

### Advanced 2: ICU Message Format for Complex Plurals and Gender

**Q:** "How do you handle grammatical gender in translations — e.g., 'He submitted' vs 'She submitted'?"

**A:** ICU `select` format. With `i18next-icu` plugin:

```json
{
  "user.submitted": "{gender, select, male {He submitted} female {She submitted} other {They submitted}} the form."
}
```

```tsx
// With react-i18next + i18next-icu
const { t } = useTranslation();
// t('user.submitted', { gender: user.gender })
// → "She submitted the form."
```

Without ICU, developers attempt string concatenation — `t('user.pronoun') + t('user.submitted_verb')` — which fails spectacularly in languages where verb conjugation depends on subject gender, number, AND tense simultaneously (Polish, Arabic, Hebrew). ICU `select` + `plural` combined in a single message handles these cases correctly.

---

### Advanced 3: CDN Strategy for Translation Files

**Q:** "Translation files are large. How do you serve them efficiently globally?"

**A:** CDN-hosted with aggressive caching, versioned by content hash.

Build output: `locales/fr/common.[hash].json`

The hash changes only when the file changes. CDN caches aggressively (cache-control: `max-age=31536000, immutable`). The HTML/JS bundle references the hashed filename, so cache busting is automatic.

For SSR: the server reads translation files from disk (or in-memory cache on boot) — no HTTP roundtrip. The client gets the locale JSON URL injected into the page and fetches it from CDN in parallel with JS parsing.

For edge rendering (Cloudflare Workers, Vercel Edge): preload locale files into the worker's local cache at deploy time. Translation lookups become synchronous, no I/O.

---

### Advanced 4: Multi-Tenant i18n — Different Translations per Brand

**Q:** "You're building a white-label SaaS where each tenant has custom translations. How do you architect this?"

**A:** Layered namespace resolution. Base translations are your product defaults. Tenant overrides are loaded as an additional namespace with higher priority.

```
Resolution order (highest to lowest):
1. tenant/{tenantId}/{locale}/common.json   ← tenant customizations
2. {locale}/common.json                    ← product defaults
3. fallback locale (en)                    ← absolute fallback
```

i18next supports this via multiple backends or a custom backend plugin that merges tenant-specific JSON on top of base translations at request time. The tenant backend fetches from your API or a tenant-specific CDN prefix.

Key insight: tenants only provide *override* files. They're sparse — only keys they want to change. The merge happens at load time. This way tenants can rebrand "Submit Order" to "Confirm Purchase" without maintaining a complete translation for every language.

---

## 8. Senior Trap Questions

### Trap 1: "Just Use Google Translate for Missing Locales"

**Trap:** "We don't have budget for translators for Portuguese. Can't we just run the English strings through the Google Translate API automatically?"

**Why it's a trap:** Machine translation of UI strings produces robotic, inconsistent, often wrong text. UI copy has context that MT systems miss — a button labeled "Book" could be translated as the noun (libro) or verb (reservar) in Spanish. Terms like "checkout", "bundle", "dashboard" have no direct translation and MT guesses badly. Legal/financial copy machine-translated is a liability risk.

**Correct answer:** Two legitimate alternatives: (1) Use a professional translator, even for a single batch review. (2) Launch the locale in English (fallback) with a banner "This page isn't available in Portuguese yet." Track user demand to justify translation budget. Never silently ship MT output as production UI.

---

### Trap 2: "Concatenate Translated Strings"

**Trap:** "Why not just do `t('hello') + ' ' + username + '!'`? It's simpler."

**Why it's a trap:** Word order varies dramatically by language. English: "Hello John!" German: "Guten Tag, John!" Japanese: "ジョンさん、こんにちは！" (name comes first). String concatenation hard-codes English word order into the code structure. When translators get "Hello" and "!" as separate keys, they have no way to reorder.

**Correct answer:** Always use placeholders in a single key:
```json
{ "greeting": "Hello, {{name}}!" }
```
```tsx
t('greeting', { name: username })
// German translator writes: "Guten Tag, {{name}}!"
// Japanese translator writes: "{{name}}さん、こんにちは！"
```
The translator controls placement of the interpolated value within their natural sentence structure.

---

### Trap 3: "RTL Just Means text-align: right"

**Trap:** "We support Arabic by adding `text-align: right` to all our text elements."

**Why it's a trap:** RTL is a complete layout mirror, not just text alignment. `text-align: right` without `dir="rtl"` creates visual chaos — punctuation ends up on the wrong side, inline elements stack in wrong order, list markers appear on wrong side. More critically: physical layout properties (margins, padding, borders, absolute positioning, flexbox `flex-start`) all remain LTR-oriented. A navigation sidebar that's on the left in LTR should be on the right in RTL. "Back" button chevron pointing left should point right. Form field labels on the right.

**Correct answer:** Set `dir="rtl"` on `<html>`, use CSS logical properties throughout, and do visual QA in an actual RTL browser with an Arabic locale. The `dir` attribute + logical properties handle 90% of cases automatically.

---

### Trap 4: "Load All Locales Upfront for Better Performance"

**Trap:** "Loading locales lazily adds latency when the user changes language. Why not preload everything?"

**Why it's a trap:** Math: 20 locales × 50KB each = 1MB of translation JSON on every page load, for every user, including users who will only ever read in English. This bloats the initial bundle and slows Time To Interactive. Most users never change their locale.

**Correct answer:** Load only the detected locale on boot. Pre-warm additional locales only if there's a locale switcher and the user hovers over it (speculative loading). Cache loaded locales in memory — switching back to a previously loaded locale is instant. The 1-2 second locale switch delay is acceptable UX; a 1MB initial payload is not.

---

### Trap 5: "Intl Requires a Library"

**Trap:** "We need to add `date-fns` or `moment` to handle date/number formatting for international locales."

**Why it's a trap:** `Intl.DateTimeFormat`, `Intl.NumberFormat`, `Intl.RelativeTimeFormat`, `Intl.ListFormat`, `Intl.PluralRules`, and `Intl.Collator` are all built into every modern browser (Chrome 24+, Firefox 29+, Safari 10+, Edge 12+) and Node.js. They have zero bundle cost and are maintained by browser vendors to stay in sync with CLDR updates. Adding moment.js or date-fns for locale formatting is unnecessary bundle bloat.

**Correct answer:** Use the Intl API directly. Only add a library if you need date *manipulation* (adding days, calculating diffs) — date-fns for that. For *formatting* dates and numbers for display, Intl is sufficient and superior.

---

### Trap 6: "Translation Keys Should Be the English Text"

**Trap:** "We use the English string itself as the key — `t('Submit')` instead of `t('button.submit')`. That way the key is self-documenting."

**Why it's a trap:** English strings change frequently during product iteration. "Submit" becomes "Place Order" — now the key is `t('Submit')` but the English copy is different. Every other locale file has a key `"Submit"` that no longer exists. Keys break on renames. Additionally: same English word in different contexts needs different translations. "Book" (noun) and "Book" (verb) are the same string in English but different words in most other languages. Using English text as keys makes context disambiguation impossible.

**Correct answer:** Use semantic/structural keys: `button.submit`, `checkout.confirm_order`, `navigation.book_appointment`. Keys are stable even when copy changes. Add a description/comment field for translator context. The base locale file maps keys to English copy — that's the human-readable layer.

---

## 9. Production Code Examples

### Example 1: i18n Setup (TypeScript)

```ts
// src/i18n/index.ts
import i18n from 'i18next';
import HttpBackend from 'i18next-http-backend';
import LanguageDetector from 'i18next-browser-languagedetector';
import { initReactI18next } from 'react-i18next';

const detectedLocale =
  (window as any).__INITIAL_LOCALE__ ??
  document.documentElement.lang ??
  'en';

i18n
  .use(HttpBackend)
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    lng: detectedLocale,
    fallbackLng: ['en'],
    ns: ['common'],
    defaultNS: 'common',
    backend: { loadPath: '/locales/{{lng}}/{{ns}}.json' },
    interpolation: { escapeValue: false },
    react: { useSuspense: true },
  });

export default i18n;
```

---

### Example 2: TypeScript Key Safety Declaration

```ts
// src/types/i18next.d.ts
import type common from '../locales/en/common.json';
import type checkout from '../locales/en/checkout.json';

declare module 'i18next' {
  interface CustomTypeOptions {
    defaultNS: 'common';
    resources: {
      common: typeof common;
      checkout: typeof checkout;
    };
  }
}
// Now t('button.nonexistent') is a TypeScript compile error
```

---

### Example 3: useTranslation with Namespace and Plural

```tsx
// src/components/CartSummary.tsx
import { useTranslation } from 'react-i18next';

interface Props { itemCount: number; total: number; locale: string }

export function CartSummary({ itemCount, total, locale }: Props) {
  const { t } = useTranslation(['common', 'checkout']);

  const formattedTotal = new Intl.NumberFormat(locale, {
    style: 'currency',
    currency: 'USD',
  }).format(total);

  return (
    <div>
      <p>{t('checkout:cart.items', { count: itemCount })}</p>
      <p>{t('checkout:cart.total', { total: formattedTotal })}</p>
    </div>
  );
}
// checkout.json: { "cart": { "items_one": "{{count}} item", "items_other": "{{count}} items" } }
```

---

### Example 4: RTL-Aware Layout Component

```tsx
// src/components/Sidebar.tsx
import { useTranslation } from 'react-i18next';
import { useEffect } from 'react';

const RTL_LOCALES = new Set(['ar', 'he', 'fa', 'ur']);

export function LocaleProvider({ locale, children }: {
  locale: string; children: React.ReactNode
}) {
  const lang = locale.split('-')[0];
  const dir = RTL_LOCALES.has(lang) ? 'rtl' : 'ltr';

  useEffect(() => {
    document.documentElement.setAttribute('lang', locale);
    document.documentElement.setAttribute('dir', dir);
  }, [locale, dir]);

  return <>{children}</>;
}
// CSS uses margin-inline-start/end — layout auto-flips with dir="rtl"
```

---

### Example 5: Lazy Namespace Loading on Route

```tsx
// src/pages/CheckoutPage.tsx
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import i18n from '../i18n';

export function CheckoutPage() {
  const [nsLoaded, setNsLoaded] = useState(false);
  const { t } = useTranslation('checkout');

  useEffect(() => {
    i18n.loadNamespaces(['checkout']).then(() => setNsLoaded(true));
  }, []);

  if (!nsLoaded) return <div aria-busy="true">{t('common:loading')}</div>;

  return <div>{t('checkout:title')}</div>;
}
```

---

### Example 6: Missing Translation Logger

```ts
// src/i18n/missingKeyHandler.ts
import { TOptions } from 'i18next';

export function onMissingKey(
  lngs: readonly string[],
  ns: string,
  key: string,
  fallbackValue: string
): void {
  if (process.env.NODE_ENV === 'production') {
    // Send to observability (DataDog, Sentry, custom)
    window.__analytics?.track('i18n_missing_key', { lngs, ns, key });
  } else {
    console.warn(`[i18n] Missing key: ${ns}:${key} for locales: ${lngs}`);
  }
}

// In i18n init:
// saveMissing: true,
// missingKeyHandler: onMissingKey,
```

---

### Example 7: Intl-Based Date Formatter Hook

```ts
// src/hooks/useFormatDate.ts
import { useTranslation } from 'react-i18next';
import { useCallback } from 'react';

export function useFormatDate() {
  const { i18n } = useTranslation();

  const formatDate = useCallback((date: Date, options?: Intl.DateTimeFormatOptions) => {
    return new Intl.DateTimeFormat(i18n.language, {
      year: 'numeric', month: 'long', day: 'numeric',
      ...options,
    }).format(date);
  }, [i18n.language]);

  return { formatDate };
}
// Usage: const { formatDate } = useFormatDate(); formatDate(new Date())
// en-US: "August 21, 2026"   fr-FR: "21 août 2026"   ja-JP: "2026年8月21日"
```

---

### Example 8: Locale Switcher with Lazy Loading

```tsx
// src/components/LocaleSwitcher.tsx
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

const LOCALES = [
  { code: 'en', label: 'English' },
  { code: 'fr', label: 'Français' },
  { code: 'ar', label: 'العربية' },
];

export function LocaleSwitcher() {
  const { i18n } = useTranslation();
  const [switching, setSwitching] = useState(false);

  async function changeLocale(locale: string) {
    setSwitching(true);
    await i18n.changeLanguage(locale);
    document.documentElement.lang = locale;
    setSwitching(false);
  }

  return (
    <select
      value={i18n.language}
      onChange={e => changeLocale(e.target.value)}
      disabled={switching}
      aria-label="Select language"
    >
      {LOCALES.map(l => <option key={l.code} value={l.code}>{l.label}</option>)}
    </select>
  );
}
```

---

## 10. Interview Cheat Sheet

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  i18n ARCHITECT CHEAT SHEET                                                 │
├──────────────────────────────────┬──────────────────────────────────────────┤
│  CONCEPT                         │  ANSWER                                  │
├──────────────────────────────────┼──────────────────────────────────────────┤
│  i18n vs l10n                    │  i18n = infrastructure (once)            │
│                                  │  l10n = content/culture (per locale)     │
├──────────────────────────────────┼──────────────────────────────────────────┤
│  Library choice                  │  i18next for most apps                   │
│                                  │  react-intl for ICU compliance           │
├──────────────────────────────────┼──────────────────────────────────────────┤
│  Key naming                      │  Semantic keys (button.submit)           │
│                                  │  NOT English text as key                 │
├──────────────────────────────────┼──────────────────────────────────────────┤
│  Locale detection order          │  URL > cookie > Accept-Language > default│
├──────────────────────────────────┼──────────────────────────────────────────┤
│  Fallback chain                  │  fr-CA → fr → en → key                  │
├──────────────────────────────────┼──────────────────────────────────────────┤
│  Lazy loading                    │  dynamic import + Suspense boundary      │
│                                  │  namespace split by feature              │
├──────────────────────────────────┼──────────────────────────────────────────┤
│  Pluralization                   │  _one/_few/_many/_other suffixes         │
│                                  │  CLDR rules per locale                   │
├──────────────────────────────────┼──────────────────────────────────────────┤
│  Date/Number/Currency            │  Intl.DateTimeFormat, Intl.NumberFormat  │
│                                  │  ZERO bundle cost, browser-native        │
├──────────────────────────────────┼──────────────────────────────────────────┤
│  Relative time                   │  Intl.RelativeTimeFormat — no library    │
├──────────────────────────────────┼──────────────────────────────────────────┤
│  RTL support                     │  dir="rtl" on <html>                     │
│                                  │  CSS logical properties throughout       │
│                                  │  margin-inline-start NOT margin-left     │
├──────────────────────────────────┼──────────────────────────────────────────┤
│  RTL ≠ text-align:right          │  TRAP — full layout mirror, icons, flow  │
├──────────────────────────────────┼──────────────────────────────────────────┤
│  String interpolation            │  t('greeting', {name}) NOT string concat │
├──────────────────────────────────┼──────────────────────────────────────────┤
│  TypeScript key safety           │  Augment i18next CustomTypeOptions       │
│                                  │  JSON file becomes TypeScript types      │
├──────────────────────────────────┼──────────────────────────────────────────┤
│  SSR hydration fix               │  window.__INITIAL_LOCALE__ from server   │
│                                  │  Single source of truth before hydration │
├──────────────────────────────────┼──────────────────────────────────────────┤
│  Missing keys in prod            │  Log to observability, alert on spike    │
├──────────────────────────────────┼──────────────────────────────────────────┤
│  Translation extraction          │  i18next-scanner in CI, fail on missing  │
├──────────────────────────────────┼──────────────────────────────────────────┤
│  Pseudo-locale testing           │  [Submit] brackets catch hardcoded text  │
├──────────────────────────────────┼──────────────────────────────────────────┤
│  Machine translation             │  NEVER for production UI — always human  │
├──────────────────────────────────┼──────────────────────────────────────────┤
│  Load all locales upfront        │  TRAP — 20 × 50KB = 1MB bloat            │
├──────────────────────────────────┼──────────────────────────────────────────┤
│  CDN strategy                    │  Content-hashed filenames, immutable TTL │
├──────────────────────────────────┼──────────────────────────────────────────┤
│  Multi-tenant i18n               │  Layered namespaces: tenant > product    │
├──────────────────────────────────┼──────────────────────────────────────────┤
│  Gender in translations          │  ICU select: {gender, select, m{} f{}}   │
└──────────────────────────────────┴──────────────────────────────────────────┘

TRAP QUICK REFERENCE
────────────────────────────────────────────────────────────────
Trap                          │ Correct Response
──────────────────────────────┼─────────────────────────────────
"Use Google Translate"        │ MT = poor UX, always human
"Concatenate strings"         │ Use {{placeholders}} in one key
"RTL = text-align:right"      │ Full layout flip, logical props
"Load all locales upfront"    │ Lazy load: 1MB bloat otherwise
"Intl needs a library"        │ Built-in, zero bundle cost
"Use English text as keys"    │ Keys break on copy changes, use
                              │ semantic keys: button.submit
────────────────────────────────────────────────────────────────

CLDR PLURAL CATEGORIES (by language)
────────────────────────────────────────────────────────────────
English/German:   one, other
French:           one (0 and 1), other
Russian/Polish:   one, few, many, other
Arabic:           zero, one, two, few, many, other  (6 forms!)
Chinese/Japanese: other (no pluralization)
────────────────────────────────────────────────────────────────

CSS LOGICAL PROPERTIES QUICK REF
────────────────────────────────────────────────────────────────
margin-left          → margin-inline-start
margin-right         → margin-inline-end
padding-left         → padding-inline-start
padding-right        → padding-inline-end
border-left          → border-inline-start
text-align: left     → text-align: start
left: 0              → inset-inline-start: 0
right: 0             → inset-inline-end: 0
────────────────────────────────────────────────────────────────

TAILWIND RTL EQUIVALENTS
────────────────────────────────────────────────────────────────
ml-4   → ms-4   (margin-start)
mr-4   → me-4   (margin-end)
pl-4   → ps-4   (padding-start)
pr-4   → pe-4   (padding-end)
────────────────────────────────────────────────────────────────
```

---

## 11. Quick Recall: Key Library APIs

### i18next / react-i18next

```ts
// Hook
const { t, i18n } = useTranslation('namespace');

// Basic
t('key')

// Interpolation
t('greeting', { name: 'Alice' })

// Plural
t('items', { count: 5 })

// Namespace
t('checkout:cart.total')

// Change language (lazy loads)
await i18n.changeLanguage('fr')

// Load namespace on demand
await i18n.loadNamespaces(['checkout'])

// Current language
i18n.language  // 'fr-CA'

// Resolved language (after fallback)
i18n.resolvedLanguage  // 'fr'
```

### Browser Intl APIs (zero bundle cost)

```ts
// Date formatting
new Intl.DateTimeFormat('fr-FR', { dateStyle: 'long' }).format(new Date())
// "21 août 2026"

// Number/currency
new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(1234.5)
// "1.234,50 €"

// Relative time
new Intl.RelativeTimeFormat('es', { numeric: 'auto' }).format(-3, 'hour')
// "hace 3 horas"

// List formatting
new Intl.ListFormat('en', { style: 'long', type: 'conjunction' }).format(['a', 'b', 'c'])
// "a, b, and c"

// Plural rules (for custom plural logic)
new Intl.PluralRules('ru').select(5)
// "many"

// Sorting (locale-aware)
new Intl.Collator('sv').compare('ä', 'z')
// Swedish: ä comes after z (unlike English sort)
```

---

## 12. Architecture Decision Record Template

When presenting your i18n architecture to stakeholders, frame it as decisions made:

**ADR-001: Library Selection**
- Decision: i18next over react-intl
- Rationale: Plugin ecosystem for backend loading, namespace splitting, TypeScript key safety
- Trade-off: No built-in ICU without plugin; acceptable given our content complexity

**ADR-002: Locale Detection Strategy**
- Decision: URL path segment as primary, cookie as persistence
- Rationale: URL-based locale enables SSR without client-side detection, shareable links preserve locale, cookie retains preference across sessions
- Trade-off: Requires i18n-aware routing; worth it for SSR correctness

**ADR-003: Translation Loading**
- Decision: Lazy load by namespace on route entry
- Rationale: 200KB total translations; loading all upfront wastes bandwidth for 90% of users who stay in one feature
- Trade-off: 100-200ms delay on first visit to a new feature; mitigated by preloading on hover/focus

**ADR-004: RTL Support**
- Decision: CSS logical properties from project start
- Rationale: Retrofitting logical properties into an LTR-only codebase is a multi-week effort; starting correct costs nothing
- Trade-off: Team must learn new property names; addressed via ESLint rule that flags physical properties

---

## 13. Common Interview Follow-Up Questions and Answers

**"How do you test i18n?"**

Three levels: (1) Unit tests with `i18n.changeLanguage('fr')` before rendering — verify correct text appears. (2) Integration tests run against the pseudo-locale to catch hardcoded strings. (3) Visual regression tests with Chromatic/Percy against RTL locales to catch layout breaks. Never rely solely on manual QA for RTL.

**"How do you handle translations for dynamic content from an API?"**

API responses should return locale-appropriate content, not keys. The server is responsible for localizing dynamic data (product names, descriptions, error messages from backend). The frontend only localizes static UI chrome. If the backend returns keys, wrap API responses in a mapper that runs them through i18next at the API client layer — but push back on this architecture; it creates tight coupling.

**"What's your strategy for A/B testing translations?"**

Feature flags + namespace overrides. The A/B test defines a variant namespace (`checkout_v2`) that overrides specific keys in `checkout`. Users in the experiment load the variant namespace on top of the base. When the experiment concludes, winning variant keys are merged into the base namespace. Translation management platform (Crowdin/Lokalise) tracks both namespaces.

**"How do you handle translation for user-generated content?"**

You don't — i18n is for UI strings, not UGC. For UGC that needs to be readable across languages (e.g., product reviews on a global marketplace), that's a separate machine translation pipeline (MT) with clear labeling to users that it's automated. Never route UGC through your UI translation workflow.

**"What's the performance impact of i18next on your bundle?"**

Core i18next is ~28KB minified+gzipped. react-i18next adds ~8KB. With HTTP backend for lazy loading and language detector: total ~50KB. This is the one-time infrastructure cost. Compare to moment.js (~67KB) or date-fns with locales (~75KB per locale). The Intl API eliminates any need for date/number formatting libraries, keeping the total impact minimal.
