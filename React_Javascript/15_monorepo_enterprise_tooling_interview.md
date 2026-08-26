# Monorepo & Enterprise Tooling — 15-YOE React Architect Interview Prep

> Target role: Staff/Principal Frontend Engineer or React Architect
> Focus: Monorepo tooling, CI optimization, shared component libraries, dependency governance

---

## 1. Big Picture — ASCII Diagrams

### 1.1 Monorepo Directory Structure

```
my-company/
├── apps/                          # Deployable applications
│   ├── web/                       # Next.js customer-facing app
│   │   ├── package.json
│   │   └── src/
│   ├── admin/                     # Vite-based internal dashboard
│   │   ├── package.json
│   │   └── src/
│   └── mobile/                    # React Native app
│       ├── package.json
│       └── src/
│
├── packages/                      # Shared libraries (internal, no npm publish)
│   ├── ui/                        # Design system components
│   │   ├── package.json           # name: "@company/ui"
│   │   └── src/
│   ├── hooks/                     # Shared React hooks
│   │   ├── package.json           # name: "@company/hooks"
│   │   └── src/
│   ├── utils/                     # Pure utility functions
│   │   ├── package.json           # name: "@company/utils"
│   │   └── src/
│   ├── api-client/                # Generated API client
│   │   ├── package.json           # name: "@company/api-client"
│   │   └── src/
│   └── tsconfig/                  # Shared TypeScript configs
│       ├── package.json           # name: "@company/tsconfig"
│       ├── base.json
│       ├── nextjs.json
│       └── react-library.json
│
├── tools/                         # Internal developer tooling
│   ├── eslint-config/             # Shared ESLint rules
│   ├── jest-preset/               # Shared Jest configuration
│   └── scripts/                  # Release, code-generation scripts
│
├── pnpm-workspace.yaml            # Workspace definition
├── package.json                   # Root package.json
├── turbo.json                     # Turborepo task pipeline
└── .changeset/                    # Changesets config
    └── config.json
```

### 1.2 Task Dependency Graph (Turborepo Pipeline)

```
                    ┌─────────────────────────────────────┐
                    │         turbo run build              │
                    └────────────────┬────────────────────┘
                                     │
                    ┌────────────────▼────────────────────┐
                    │   Resolve task graph (topological)  │
                    └────────────────┬────────────────────┘
                                     │
         ┌───────────────────────────┼──────────────────────────┐
         ▼                           ▼                           ▼
   @company/tsconfig          @company/utils              @company/hooks
   [build: N/A - config]      [build ──────────────────▶ cache HIT ✓]
         │                           │                           │
         │                           ▼                           │
         │                    @company/ui                        │
         │                    [depends on: utils, tsconfig]      │
         │                    [build ──────────────────▶ RUN]    │
         │                           │                           │
         └───────────────────────────▼───────────────────────────┘
                                     │
                         ┌───────────▼───────────┐
                         │   apps/web  apps/admin │
                         │   [depends on: ui,     │
                         │    hooks, api-client]  │
                         │   [build ──▶ RUN]      │
                         └───────────────────────┘

Legend:
  cache HIT ✓  = Turborepo found matching hash → skip execution
  RUN          = Inputs changed → execute task
  ──▶          = "this task must complete before me" (dependsOn)
```

### 1.3 CI Pipeline (GitHub Actions)

```
┌─────────────────────────────────────────────────────────────────┐
│  PR opened / push to branch                                      │
└────────────────────┬────────────────────────────────────────────┘
                     │
         ┌───────────▼───────────┐
         │  Affected detection   │   turbo run build test lint
         │  nx affected --base=  │   --filter=[...since main]
         │  origin/main          │
         └───────────┬───────────┘
                     │
         ┌───────────▼───────────────────────────────────────────┐
         │               Parallel Job Matrix                      │
         │  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐ │
         │  │  lint     │  │ type-   │  │  unit tests           │ │
         │  │  (cached) │  │ check   │  │  (affected only,      │ │
         │  │           │  │(cached) │  │   cached)             │ │
         │  └──────────┘  └──────────┘  └──────────────────────┘ │
         └───────────────────────┬───────────────────────────────┘
                                 │
                     ┌───────────▼───────────┐
                     │   Build (cached)      │
                     │   Remote cache read   │
                     │   from Turborepo/     │
                     │   Nx Cloud            │
                     └───────────┬───────────┘
                                 │
                     ┌───────────▼───────────┐
                     │   E2E tests           │
                     │   (per-app, Cypress/  │
                     │    Playwright)        │
                     └───────────┬───────────┘
                                 │
                     ┌───────────▼───────────┐
                     │  Deploy preview env   │
                     │  (affected apps only) │
                     └───────────────────────┘
```

---

## 2. Conversational Interview Script — 15-YOE Architect Voice

### 2.1 Monorepo vs Polyrepo Decision

**Interviewer:** "Walk me through how you'd decide whether to use a monorepo or stick with separate repos for a new product suite."

**Architect Answer:**
"The decision isn't ideological — it's about your team's actual coupling patterns and deployment model.

I start by asking three questions: How often do changes span multiple packages simultaneously? How mature is the CI infrastructure? And how independent are the teams?

If I have a design system, an API client layer, and three apps that all need to change together when we update an API contract — that's a strong signal for monorepo. With polyrepo, an API breaking change creates a waterfall of PRs across repos, each needing coordination. With monorepo, it's one atomic commit and the CI catches all breakages in a single run.

On the other hand, if I have a mobile team in a completely different timezone with a separate release cadence and their own platform-specific CI requirements — forcing them into a shared repo may slow everyone down. Independent teams with genuinely independent lifecycles benefit from polyrepo.

The trap people fall into is thinking monorepo is just 'put everything in one git repo.' Without proper tooling — specifically a task orchestrator like Turborepo or Nx — you'll run the full CI suite on every commit and it'll grind to a halt within months. Tooling isn't optional; it's what makes monorepo scalable.

My default for a greenfield product suite with shared design language and shared auth patterns: monorepo with pnpm workspaces and Turborepo. For genuinely independent microservice backends with separate frontend SPAs owned by separate business units: polyrepo, probably with shared npm packages for the common bits."

---

**Interviewer:** "You mentioned polyrepo sometimes. What's the cost of going back from monorepo to polyrepo?"

**Architect Answer:**
"It's not catastrophic but it's genuinely painful. You lose git history continuity — you can migrate with tools like `git filter-repo` but nobody ever has time to do it cleanly. You then have to re-establish CI conventions in multiple repos. Shared packages that were internal now need to be versioned and published to npm or a private registry, which adds a whole release workflow overhead. The cognitive load of 'which version of @company/ui does this app use' comes back.

I've done this migration once — we split a monorepo for a team that was acquired and needed total independence. It took about three weeks of infra work, and we lost about six months of git blame context on the shared packages.

Going the other direction — consolidating polyrepos into a monorepo — is actually easier with modern tooling. We can migrate with `git subtree` and preserve history."

---

### 2.2 When the Interviewer Pushes on Scale

**Interviewer:** "Doesn't monorepo fall apart at Google/Meta scale?"

**Architect Answer:**
"At Google/Meta scale you need custom VCS tooling — Piper, or Meta's equivalent. At the scale most companies actually operate — say, 50–200 engineers, hundreds of packages — standard Turborepo or Nx handles it well.

The key insight is that caching makes scale manageable. Once your CI can restore a cached build artifact in two seconds instead of recompiling in three minutes, the size of your repo becomes irrelevant for most tasks. The bottleneck shifts from 'how many packages exist' to 'how many packages were actually touched by this PR.'

I've run a monorepo with 80 packages and 12 apps. With remote caching via Turborepo Cloud, a typical PR that touches two packages ran in under four minutes on CI. Without caching it was 25 minutes. That's the whole argument for tooling right there."

---

## 3. Scenario Q&As — Production Context

### Scenario 1: A junior dev introduces a circular dependency between @company/ui and @company/hooks

**Q:** "We're getting a TypeScript build error about a circular dependency. How do you handle this and prevent recurrence?"

**A:**
"Circular dependencies in a monorepo are a structural warning sign, not just a build problem. If `@company/ui` depends on `@company/hooks` and `@company/hooks` depends on `@company/ui`, your build system has no valid topological sort order.

Immediate fix: identify which specific import creates the cycle. Usually it's a utility function that crept into the wrong package. Move it to `@company/utils` or create a new `@company/shared` package that neither circular party depends on.

Prevention: TypeScript project references will actually enforce this at compile time — if you configure them correctly and try to create a cycle, `tsc --build` will error. Additionally, Nx has an `enforceModuleBoundaries` rule in ESLint that lets you define explicit dependency directions. I configure it so that `apps` can depend on `packages`, `packages` can depend on other `packages`, but never vice versa, and `packages` can never depend on `apps`.

Long term: I run `madge --circular` in CI as a lightweight check before TypeScript even runs."

---

### Scenario 2: Build times are climbing — 35 minutes per CI run

**Q:** "Your monorepo CI is taking 35 minutes. Engineers are complaining. Walk me through your optimization approach."

**A:**
"I approach this as a funnel optimization problem.

First, instrument — turn on Turborepo's `--summarize` flag and look at the task timeline. Find the P95 bottlenecks. In my experience it's usually one of three things: cache misses because the cache key is too broad, no remote caching configured so every CI agent starts cold, or no affected detection so we're running all tasks even for trivial changes.

Second, establish remote caching immediately. With Turborepo this means setting `TURBO_TEAM` and `TURBO_TOKEN` env vars pointing at Turborepo Cloud or a self-hosted remote cache (there are open-source options like `turborepo-remote-cache` on npm). This alone typically drops CI time by 60–80% for PRs that don't touch many packages.

Third, enable affected-only execution. `turbo run build --filter=[origin/main]...` only runs tasks for packages whose source files changed relative to the base branch. This means a PR that only touches `apps/admin` doesn't rebuild `apps/web` or any unrelated packages.

Fourth, parallelize jobs. Turborepo schedules tasks in parallel automatically where there are no dependencies. For E2E tests which can't be cached, split them across multiple CI agents by app.

That 35-minute run can typically be brought to under 6 minutes with remote caching plus affected detection, and under 3 minutes for PRs that touch one or two packages."

---

### Scenario 3: You need to make a breaking change to @company/ui Button props

**Q:** "The design system team wants to rename the `variant` prop to `intent` on Button. Half the company's apps use this prop. How do you manage this change?"

**A:**
"This is the classic breaking change governance problem in a shared internal library.

My approach is a deprecation window strategy. Since this is an internal unversioned package, I don't need to publish a new major version — but I do need to communicate and track adoption.

Step one: add a deprecated `variant` prop that accepts the old values and internally maps to `intent`. Use a PropTypes/TypeScript overload that marks `variant` as `@deprecated` in JSDoc. Add a runtime `console.warn` in development only.

Step two: run a codemod across the entire monorepo. Something like `jscodeshift` with a custom transform that renames `variant=` to `intent=` across all JSX in `apps/`. This can be a single PR that touches 50 files — and this is exactly why monorepo is powerful for this. In polyrepo you'd be coordinating across 5 separate repos.

Step three: once the codemod PR is merged and CI is green, remove the deprecated prop in a follow-up PR.

Step four: if this is an externally published package, use Changesets to bump the major version, generate a CHANGELOG entry documenting the migration, and publish. Internal consumers get a clear migration guide.

The key safety net is TypeScript. Once I remove the deprecated prop, TypeScript immediately surfaces every unconverted consumer in the monorepo — there's no hiding from it."

---

### Scenario 4: Phantom dependency issue in production

**Q:** "An app works locally but crashes in a fresh CI environment with 'Cannot find module @company/lodash-internal'. What's happening?"

**A:**
"This is a phantom dependency problem — a textbook pnpm workspaces vs npm/yarn hoisting difference.

With npm and yarn classic, all packages in a monorepo get hoisted into the root `node_modules`. If `apps/web` happens to import `lodash-internal` (which is a dependency of `@company/hooks`, not of `apps/web` directly), it works locally because lodash-internal is physically present in the hoisted node_modules. But it's not declared as a dependency of `apps/web`. In a CI environment using `--frozen-lockfile` or strict install, the hoist might be different or absent.

pnpm solves this with strict isolation. Each package's `node_modules` only contains packages it explicitly declares as dependencies. pnpm uses symlinks to a content-addressable store, and if you didn't list it in your `package.json`, you can't import it. This error would fail locally too with pnpm, which is exactly the point — it forces you to declare your dependencies correctly.

The fix is: add `lodash-internal` explicitly to `apps/web/package.json` if it genuinely needs it, or (better) expose a stable API from `@company/hooks` that doesn't require consumers to import its internal deps directly.

This is one of the primary reasons I default to pnpm workspaces over npm workspaces in new monorepos."

---

### Scenario 5: Shared test utilities across apps

**Q:** "Multiple apps have copy-pasted test setup code — custom render functions, mock providers, test factories. How do you centralize this?"

**A:**
"Create a dedicated `packages/test-utils` package. This is a workspace package that's never published externally but is available to every app via the workspace protocol.

The package exports a custom render function that wraps `@testing-library/react`'s render with the app's context providers — theme provider, query client, router, etc. It exports factory functions for common test data shapes. It re-exports test utilities from testing-library so consumers get a single import point.

The tricky part: `packages/test-utils` needs to be a `devDependency` (not a regular dependency) of consuming apps, because it should never appear in production bundles. And you need to configure your TypeScript `paths` in the test environment to resolve `@company/test-utils` to the workspace package.

In the tsconfig for tests:
```json
{
  "compilerOptions": {
    "paths": {
      "@company/test-utils": ["../../packages/test-utils/src/index.ts"]
    }
  }
}
```

This is also a good use of the `typeVersions` field in the test-utils `package.json` if you want the TypeScript resolution to work without explicit path configuration."

---

### Scenario 6: Renovatebot PR storm after a React major version update

**Q:** "Renovatebot opened 47 PRs simultaneously updating React from 17 to 18 across the monorepo. How do you handle this, and how do you prevent it in future?"

**A:**
"This is a Renovatebot configuration problem. The default behavior creates one PR per package, which is overwhelming and creates merge conflict hell.

For a monorepo, configure Renovatebot to group related updates. In `renovate.json`:

```json
{
  "packageRules": [
    {
      "matchPackageNames": ["react", "react-dom", "@types/react"],
      "groupName": "react"
    }
  ]
}
```

This creates a single PR that updates React across every affected `package.json` in one shot. You can also set `rangeStrategy: bump` for workspace packages so it updates the version ranges properly.

For the React 17→18 migration specifically, this is also where a monorepo shines: you can update all consumers atomically and verify they all work together before merging, rather than coordinating separate PRs across repos.

Going forward: configure `automerge: true` for patch and minor updates on leaf packages (apps), but require manual review for major updates. Also configure `prConcurrentLimit` to cap simultaneous Renovatebot PRs so your CI isn't overwhelmed."

---

### Scenario 7: Remote cache security concern

**Q:** "Your security team is concerned about using Turborepo Cloud for remote caching. What are their valid concerns and alternatives?"

**A:**
"The legitimate concern is artifact integrity and data sovereignty. Build artifacts stored in a remote cache are effectively compiled code that will be deployed. If the cache is compromised, an attacker could swap a build artifact.

Turborepo Cloud addresses this with artifact signing, but if your security team's requirement is 'no build artifacts leave our perimeter,' then the right answer is self-hosted remote caching.

Options: the `turborepo-remote-cache` npm package is a minimal self-hosted server that implements the Turborepo Remote Cache API. You run it on your own infrastructure, back it by S3 or GCS, and point your `turbo.json` at it. Zero data leaves your network.

Nx Cloud offers similar self-hosted options (Nx Enterprise).

For the signing concern specifically: Turborepo supports cache artifact signing with a token. Configure `TURBO_REMOTE_CACHE_SIGNATURE_KEY` in your environment and every artifact is HMAC-signed before upload and verified before use. This prevents cache poisoning.

I'd bring this to the security team as: 'Here are the controls. Self-hosted solves data sovereignty, signing solves integrity.' That's usually sufficient for an enterprise security review."

---

### Scenario 8: TypeScript path aliases breaking in production builds

**Q:** "We use `@company/ui` imports everywhere. In development they work fine. But the Next.js production build fails with module not found errors on the `@company/ui` package. What's the likely cause?"

**A:**
"Several things can cause this but the most common is the `exports` field misconfiguration in the package's `package.json`, combined with Next.js's `transpilePackages` config.

By default, Next.js treats workspace packages as external node modules and does not transpile them. If `@company/ui` ships TypeScript source (no pre-compiled dist), you need to tell Next.js to transpile it:

```js
// next.config.js
module.exports = {
  transpilePackages: ['@company/ui', '@company/hooks']
}
```

The second common cause: the `main` and `exports` fields in `@company/ui/package.json` point to a `dist/` directory that doesn't exist because the package isn't pre-built. In a monorepo with Turborepo, you need either:
1. Pre-build shared packages before apps (configure `dependsOn: ["^build"]` in turbo.json), OR
2. Point the `main` field at the TypeScript source directly and use `transpilePackages` in Next.js.

The third cause: the tsconfig `paths` mapping is correct for tsc, but the webpack/esbuild bundler doesn't read tsconfig `paths` by default. Next.js handles this, but if you're using a different bundler, you may need an alias plugin.

I've seen this exact issue trip up teams who test in dev mode (where Next.js imports source directly) but fail in production builds (where bundler optimization behaves differently)."

---

## 4. Advanced Scenario Q&As

### Advanced 1: Micro-frontend architecture within a monorepo

**Q:** "Our platform team wants to adopt module federation so different teams can deploy independently. How does this interact with the monorepo structure?"

**A:**
"Module federation and monorepo aren't at odds — they solve different problems. The monorepo is about developer experience during development. Module federation is about runtime composition of independently deployed code.

In practice, I model it like this: the monorepo contains all the apps and shared packages during development. Each app is a webpack/rspack Module Federation host or remote. The shared packages in `packages/` are configured as Module Federation `shared` modules, which means they're deduplicated at runtime rather than bundled multiple times.

The key architectural decision is version alignment. If `apps/checkout` (team A) and `apps/homepage` (team B) both expose/consume `@company/ui` via Module Federation but on different versions, you get duplicate React instances at runtime — which breaks hooks. The monorepo actually helps here because everyone's on the same version of internal packages by default.

For CI: each app has its own deployment pipeline, but they share the monorepo CI for development-time type-checking and unit tests. The Turborepo `--filter` flag targets only the affected apps for deployment.

Where it gets complex: if you want complete deployment independence (team B can deploy `apps/homepage` without re-deploying `apps/checkout`), you need a contract testing layer — something like Component Testing in Storybook or integration tests that verify the Module Federation API contract doesn't break."

---

### Advanced 2: Changesets with a mix of internal and published packages

**Q:** "Our monorepo has 30 internal packages and 5 published npm packages. How do you configure Changesets to handle both?"

**A:**
"Changesets has first-class support for this via the `ignore` config and the `privatePackages` option.

In `.changeset/config.json`:
```json
{
  "changelog": "@changesets/cli/changelog",
  "commit": false,
  "linked": [],
  "access": "restricted",
  "baseBranch": "main",
  "updateInternalDependencies": "patch",
  "ignore": ["@company/web", "@company/admin"]
}
```

The `ignore` field lists packages that should never be published. For internal packages that are workspace-only, I set `"private": true` in their `package.json` — Changesets respects this and won't try to publish them.

For the 5 published packages, the full Changesets workflow applies: engineers run `pnpm changeset` to describe their change, it generates a markdown file in `.changeset/`, CI validates that every PR touching a published package has a changeset, and the release PR is generated automatically.

For internal packages, I still use Changesets' `updateInternalDependencies` setting, which keeps the `package.json` version fields in sync even for private packages. This matters for Renovatebot and for semver-based `dependsOn` tracking.

One nuance: the `linked` field lets you declare packages that should version together. If `@company/ui-core` and `@company/ui-react` should always be on the same version, link them. Any changeset that bumps one will bump both."

---

### Advanced 3: TypeScript incremental compilation in a monorepo

**Q:** "Our TypeScript type-checking is slow even with project references. What's your deep-dive diagnosis and fix?"

**A:**
"TypeScript project references with `composite: true` and `incremental: true` should give you near-instant type-checking for unchanged packages. When it's still slow, the diagnostic path is:

First, run `tsc --build --verbose` and watch which packages are being rebuilt. If TypeScript is rebuilding packages it shouldn't need to, the `.tsbuildinfo` files may be missing or stale. These live in each package's output directory and are what TypeScript uses to determine what changed.

Second, check that each package's `tsconfig.json` has:
```json
{
  "compilerOptions": {
    "composite": true,
    "incremental": true,
    "declarationDir": "./dist",
    "outDir": "./dist",
    "tsBuildInfoFile": "./dist/.tsbuildinfo"
  }
}
```
Without `composite: true`, TypeScript cannot use project references properly.

Third, check that CI is caching the `.tsbuildinfo` files. If CI always starts fresh and throws away the incremental state, you lose the benefit. With Turborepo, the cache inputs/outputs for the `type-check` task should include `dist/.tsbuildinfo` as an output so it's cached between runs.

Fourth, look at the `skipLibCheck` setting. Setting it to `true` for type-checking tasks (not for the final build) skips type-checking of `.d.ts` files in `node_modules`, which can cut check time significantly.

Fifth, consider using `tsc --build --dry` to see what would be rebuilt without actually running it. This often reveals a subtle dependency misconfiguration where a leaf package has a stale reference."

---

### Advanced 4: Turborepo cache invalidation — when caching goes wrong

**Q:** "A critical security patch was shipped but some CI runs are restoring a cached pre-patch build artifact and deploying the unpatched version. How do you investigate and fix this?"

**A:**
"This is a cache poisoning scenario — incorrect artifacts being served from cache. The root cause is almost always that the cache key (based on input file hashes) doesn't capture some input that affects the output.

Turborepo's cache key is a hash of: the input files matching the `inputs` pattern in `turbo.json`, the task's dependencies' cache hashes, environment variable values listed in `env`, and the turbo pipeline config itself.

If the security patch involved changing an environment variable (say, a CSP header value injected at build time), but that env var isn't listed in turbo.json's `env` array, Turborepo won't invalidate the cache. The fix is to add it:

```json
{
  "tasks": {
    "build": {
      "env": ["NODE_ENV", "NEXT_PUBLIC_API_URL", "CSP_POLICY_VERSION"],
      "outputs": [".next/**", "dist/**"]
    }
  }
}
```

For investigation: run `turbo run build --verbosity=2` to see the exact hash computation. Compare the hash between a run that used cache and a fresh run.

Immediate mitigation: run `turbo run build --force` to bypass the cache for this deployment cycle. For CI, you can set `TURBO_FORCE=true` as an env var to force a full rebuild.

Long-term: audit all inputs that affect your builds and ensure they're enumerated in the `env` and `inputs` fields. I also recommend storing the turbo run summary artifacts so you can forensically compare cache hashes across runs."

---

## 5. Senior Trap Questions

### Trap 1: "A monorepo just means putting everything in one git repo, right?"

**Named Trap:** "Monorepo = git repo only" trap

**Why it's wrong:**
A monorepo without tooling is a monolith in disguise. If you just `git clone` everything into one repo with no task orchestration, every CI run builds and tests everything, every time. At 20 packages that might be tolerable. At 50 packages it's 40-minute CI runs. At 100 packages nobody pushes code.

**Correct Answer:**
"Monorepo is a development strategy, not a git feature. The git repo is just the container. What makes it viable at scale is the tooling layer on top: a task orchestrator (Turborepo or Nx) that understands the dependency graph, can determine which packages were affected by a change, can cache task outputs, and can run tasks in parallel. Without that layer, a monorepo quickly becomes slower than polyrepo."

---

### Trap 2: "npm workspaces (or yarn workspaces) handles everything we need"

**Named Trap:** "Workspaces = task orchestration" conflation trap

**Why it's wrong:**
npm workspaces and pnpm workspaces handle *dependency resolution and installation* across packages. They ensure that `apps/web`'s `node_modules/@company/ui` resolves to the local workspace package rather than an npm registry version. That's it. They do not provide: task caching, affected detection, parallel task scheduling with dependency awareness, or remote artifact caching.

**Correct Answer:**
"Workspaces solve the installation problem. Turborepo or Nx solve the execution problem. You need both. I use pnpm workspaces for package management (plus the phantom dependency prevention benefits) and Turborepo for task orchestration. The two tools are complementary, not competing."

---

### Trap 3: "All our shared packages should be published to npm so apps can pin to specific versions"

**Named Trap:** "Publish everything to npm" trap

**Why it's wrong:**
Publishing internal packages to npm (even a private registry) introduces release ceremony for every change: bump version, generate changelog, publish, wait for consumers to update. For internal packages that only have internal consumers, this overhead is pure waste. You also now have to manage version mismatches between packages — `apps/web` on `@company/ui@2.1.0` and `apps/admin` on `@company/ui@2.0.1` with a bug that was fixed in 2.1.0 is a support problem.

**Correct Answer:**
"For packages with only internal consumers, I keep them as unversioned workspace packages. They're always at 'latest' because all consumers are in the same repo and updated atomically. This is one of the primary value propositions of monorepo. I only publish to npm (or a private registry) when there are external consumers — other repos or teams — who need to pin to specific versions."

---

### Trap 4: "Turborepo cache is for builds only, so we don't need to cache test runs"

**Named Trap:** "Cache is just for build artifacts" trap

**Why it's wrong:**
Turborepo can cache any task that has deterministic inputs and outputs. Test runs are deterministic if the source files and test files haven't changed. If `@company/utils` passes all tests on commit X, and nobody touches `@company/utils` between commit X and commit Y, there is no reason to re-run those tests on commit Y. Turborepo's cache key will match and it returns the cached pass result in milliseconds.

**Correct Answer:**
"In my turbo.json I cache lint, type-check, and test tasks alongside build tasks. For test tasks, the output to cache is usually `coverage/` or a JUnit XML report. The cache key automatically includes the source files. A PR that touches only `apps/web` will restore cached test results for all the untouched packages. This is often the single biggest CI time saving — test suites take much longer than builds."

---

### Trap 5: "Circular dependencies are just a code smell, they won't break anything in practice"

**Named Trap:** "Circular deps are just warnings" trap

**Why it's wrong:**
In a monorepo, circular package dependencies break the topological sort that task orchestrators use to schedule work. If `@company/ui` → `@company/hooks` → `@company/ui`, Turborepo cannot determine which package to build first. At runtime in Node.js, circular CommonJS requires can result in partially initialized modules (the well-known `undefined is not a function` for something that definitely exists). TypeScript project references actively prevent circular references and will error at compile time.

**Correct Answer:**
"Circular dependencies between packages in a monorepo have concrete consequences: broken build ordering, potential runtime initialization order bugs in SSR, and they indicate a design problem — usually a package trying to do too many things. The fix is always extracting the shared concept into a third package that neither circular party depends on. I enforce this with TypeScript project references and Nx's `enforceModuleBoundaries` ESLint rule."

---

### Trap 6: "We should use path aliases in tsconfig to share code instead of creating separate packages"

**Named Trap:** "tsconfig paths as a substitute for packages" trap

**Why it's wrong:**
tsconfig `paths` is a TypeScript-only compilation hint. It doesn't affect module resolution in bundlers (webpack, Vite, esbuild) unless you separately configure aliases there too. More critically, code referenced via paths doesn't have its own `package.json`, so it can't declare its own dependencies — consumers inherit transitive dependencies invisibly. There's no clear ownership boundary. It doesn't participate in the Turborepo task graph. You can't incrementally build it separately. It's also harder to extract into a standalone publishable package later.

**Correct Answer:**
"tsconfig paths are useful for within-package aliases (like `@/components` → `./src/components`). For code shared across packages or apps, always create a proper workspace package with its own `package.json`. This gives you clear ownership, explicit dependency declaration, participation in the build graph, and the ability to go from internal to published later with minimal friction."

---

## 6. Configuration Examples

### 6.1 pnpm-workspace.yaml

```yaml
packages:
  - 'apps/*'
  - 'packages/*'
  - 'tools/*'
```

### 6.2 Root package.json

```json
{
  "name": "my-company-monorepo",
  "private": true,
  "scripts": {
    "build": "turbo run build",
    "dev": "turbo run dev --parallel",
    "lint": "turbo run lint",
    "test": "turbo run test",
    "type-check": "turbo run type-check",
    "clean": "turbo run clean && rm -rf node_modules"
  },
  "devDependencies": {
    "turbo": "^2.0.0",
    "@changesets/cli": "^2.27.0"
  },
  "engines": {
    "node": ">=20",
    "pnpm": ">=9"
  },
  "packageManager": "pnpm@9.0.0"
}
```

### 6.3 turbo.json — Full Pipeline Config

```json
{
  "$schema": "https://turbo.build/schema.json",
  "tasks": {
    "build": {
      "dependsOn": ["^build"],
      "inputs": ["src/**", "package.json", "tsconfig.json"],
      "outputs": ["dist/**", ".next/**", "!.next/cache/**"]
    },
    "test": {
      "dependsOn": ["^build"],
      "inputs": ["src/**", "tests/**", "jest.config.*"],
      "outputs": ["coverage/**"]
    },
    "lint": {
      "inputs": ["src/**", ".eslintrc*", "eslint.config.*"]
    },
    "type-check": {
      "dependsOn": ["^build"],
      "inputs": ["src/**", "tsconfig.json"],
      "outputs": ["dist/.tsbuildinfo"]
    },
    "dev": {
      "cache": false,
      "persistent": true
    }
  },
  "ui": "tui"
}
```

### 6.4 Shared package package.json (@company/ui)

```json
{
  "name": "@company/ui",
  "version": "0.0.0",
  "private": true,
  "main": "./src/index.ts",
  "types": "./src/index.ts",
  "exports": {
    ".": {
      "import": "./dist/index.mjs",
      "require": "./dist/index.js",
      "types": "./dist/index.d.ts",
      "development": "./src/index.ts"
    }
  },
  "scripts": {
    "build": "tsup src/index.ts --format esm,cjs --dts",
    "type-check": "tsc --noEmit",
    "lint": "eslint src/"
  },
  "peerDependencies": {
    "react": ">=18",
    "react-dom": ">=18"
  },
  "devDependencies": {
    "@company/tsconfig": "workspace:*",
    "tsup": "^8.0.0"
  }
}
```

### 6.5 App package.json (apps/web) with workspace protocol

```json
{
  "name": "@company/web",
  "version": "0.0.0",
  "private": true,
  "scripts": {
    "build": "next build",
    "dev": "next dev",
    "type-check": "tsc --noEmit",
    "lint": "next lint"
  },
  "dependencies": {
    "@company/ui": "workspace:*",
    "@company/hooks": "workspace:*",
    "@company/api-client": "workspace:*",
    "next": "^14.0.0",
    "react": "^18.0.0",
    "react-dom": "^18.0.0"
  },
  "devDependencies": {
    "@company/tsconfig": "workspace:*",
    "@company/test-utils": "workspace:*",
    "@company/eslint-config": "workspace:*"
  }
}
```

### 6.6 TypeScript base config (@company/tsconfig/base.json)

```json
{
  "$schema": "https://json.schemastore.org/tsconfig",
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "lib": ["ES2022"],
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": true,
    "declaration": true,
    "declarationMap": true,
    "composite": true,
    "incremental": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "resolveJsonModule": true
  }
}
```

### 6.7 TypeScript config for a library package

```json
{
  "extends": "@company/tsconfig/base.json",
  "compilerOptions": {
    "outDir": "./dist",
    "tsBuildInfoFile": "./dist/.tsbuildinfo",
    "rootDir": "./src"
  },
  "include": ["src"],
  "references": [
    { "path": "../../packages/utils" }
  ]
}
```

### 6.8 .changeset/config.json

```json
{
  "$schema": "https://unpkg.com/@changesets/config@3.0.0/schema.json",
  "changelog": ["@changesets/changelog-github", { "repo": "my-company/monorepo" }],
  "commit": false,
  "fixed": [],
  "linked": [["@company/ui-core", "@company/ui-react"]],
  "access": "restricted",
  "baseBranch": "main",
  "updateInternalDependencies": "patch",
  "ignore": ["@company/web", "@company/admin", "@company/mobile"]
}
```

### 6.9 Renovate configuration for monorepo

```json
{
  "$schema": "https://docs.renovatebot.com/renovate-schema.json",
  "extends": ["config:base", ":dependencyDashboard"],
  "prConcurrentLimit": 5,
  "packageRules": [
    {
      "matchPackageNames": ["react", "react-dom", "@types/react", "@types/react-dom"],
      "groupName": "react core",
      "schedule": ["on the first day of the month"]
    },
    {
      "matchDepTypes": ["devDependencies"],
      "matchUpdateTypes": ["minor", "patch"],
      "automerge": true
    }
  ],
  "ignorePaths": ["**/node_modules/**"]
}
```

### 6.10 GitHub Actions CI workflow — affected only

```yaml
name: CI

on:
  pull_request:
    branches: [main]

jobs:
  ci:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - uses: pnpm/action-setup@v4
        with:
          version: 9

      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: 'pnpm'

      - run: pnpm install --frozen-lockfile

      - name: Build, lint, type-check, test (affected only)
        run: pnpm turbo run build lint type-check test --filter=[origin/main]...
        env:
          TURBO_TOKEN: ${{ secrets.TURBO_TOKEN }}
          TURBO_TEAM: ${{ vars.TURBO_TEAM }}
```

---

## 7. Key Concepts Reference

### pnpm Workspace Protocol

The `workspace:*` protocol in `package.json` dependencies tells pnpm to resolve this package from the local workspace rather than npm. At publish time, Changesets replaces `workspace:*` with the actual version number automatically. This is preferable over `"*"` (which is an npm version range) because it explicitly declares local resolution intent.

Variants:
- `workspace:*` — resolves to workspace package, publishes as exact current version
- `workspace:^` — resolves to workspace package, publishes as `^version`
- `workspace:~` — resolves to workspace package, publishes as `~version`

### Turborepo Hash Inputs

Turborepo computes a cache key from:
1. Content hash of all files matching `inputs` pattern (default: all files not in .gitignore)
2. Hash of all `dependsOn` tasks' cache keys (cascading hash)
3. Values of environment variables listed in `env` array
4. The task's pipeline configuration in turbo.json
5. The turbo version itself

If any input changes, the hash changes, the cache misses, and the task runs.

### Nx vs Turborepo Decision Matrix

| Capability | Turborepo | Nx |
|---|---|---|
| Task caching | Yes (remote via Turborepo Cloud) | Yes (remote via Nx Cloud) |
| Affected detection | Via `--filter=[base]...` | Via `nx affected` |
| Code generators | No | Yes (schematics/generators) |
| Module boundaries lint | No (use ESLint separately) | Built-in |
| Migration support | Manual | Nx provides automated migrations |
| Setup complexity | Low | Medium-High |
| Best for | Simple monorepos, fast setup | Large orgs, full governance |

My heuristic: for a new project or small/medium org, Turborepo. For an org with dedicated infra team, many package types, and need for enforced boundaries: Nx.

### Changesets Workflow

```
1. Engineer makes change to @company/ui
2. Engineer runs: pnpm changeset
   → CLI prompts: which packages changed?
   → Which bump type: patch/minor/major?
   → Write a summary (becomes CHANGELOG entry)
   → Creates: .changeset/happy-cats-dance.md

3. PR is opened with .changeset file
4. CI bot validates: if published package touched,
   a changeset must exist (enforced by:
   pnpm changeset status --since=origin/main --verbose)

5. Release PR is auto-generated by changeset action
   → Bumps versions in package.json files
   → Aggregates CHANGELOG entries
   → When merged: `pnpm changeset publish` runs
```

---

## 8. Interview Cheat Sheet

### One-Line Answers

| Question | Power Answer |
|---|---|
| Why monorepo? | Atomic cross-package changes, shared tooling, single source of truth for internal packages |
| Why pnpm over npm/yarn workspaces? | Strict isolation prevents phantom dependencies; disk-efficient content-addressable store |
| What does Turborepo actually do? | Task orchestration with content-addressable caching and dependency-aware parallelism |
| What does `dependsOn: ["^build"]` mean? | Before running this package's build, run build in all its dependencies first |
| What is affected detection? | Only run tasks for packages whose source files changed relative to the base branch |
| Why not publish all packages? | Internal packages with internal consumers have no reason for versioning overhead; unversioned workspace packages are always consistent |
| How to prevent breaking changes? | Deprecation window + codemod PR + TypeScript enforcement + ESLint module boundary rules |
| What is the `workspace:*` protocol? | Tells pnpm to resolve from local monorepo; replaced with real version on publish by Changesets |

### Architecture Principles to State Unprompted

1. "Tooling is what makes monorepo viable at scale — the git repo is just the container."
2. "Cache everything that's deterministic: builds, tests, lint, type-check."
3. "pnpm workspaces for package management, Turborepo for task orchestration — they're complementary."
4. "Internal packages stay unversioned and private. External consumers get published packages with Changesets."
5. "Affected detection is the other half of caching — don't run what you don't need to run."
6. "TypeScript project references are both a performance tool and a dependency enforcement tool."
7. "Circular dependencies between packages are always a design problem, not just a warning."

### Numbers to Drop

- Remote caching typically reduces CI time by **60–80%** for unaffected packages
- A well-configured monorepo with 80 packages: typical PR runs in **under 4 minutes** with remote caching
- Without caching the same repo: **25+ minutes** per run
- `workspace:*` saves: zero coordination overhead vs. publishing to npm for internal packages
- TypeScript incremental builds: **3–5x faster** than full builds after initial compilation

### Red Flag Phrases (Don't Say These)

- "We just put everything in one folder" — misses the tooling requirement
- "npm workspaces handles orchestration" — no, it handles installation only
- "We version all packages even internal ones" — unnecessary overhead
- "Circular deps are fine, webpack handles it" — breaks build order and TypeScript project refs
- "We cache the build, not the tests" — missed 50% of the caching opportunity
- "Turborepo cache just stores build outputs" — it stores outputs for any deterministic task

### Questions to Ask the Interviewer

1. "What's the current CI run time for a typical PR, and what's the team's pain threshold?"
2. "Do you have external consumers of your component library, or is everything internal?"
3. "How many engineers share the monorepo, and how independent are their release cadences?"
4. "Is there an existing convention around TypeScript project references, or would that be greenfield?"
5. "What's the governance model for breaking changes to shared packages today?"

---

## 9. Closing — Architect-Level Synthesis

The distinguishing quality of a 15-YOE architect answer on monorepo tooling is understanding that every tool solves a specific problem and the problems are distinct:

- **pnpm workspaces**: package installation and dependency isolation
- **Turborepo/Nx**: task scheduling, caching, and affected detection
- **TypeScript project references**: compile-time dependency enforcement and incremental typing
- **Changesets**: release workflow and changelog automation for published packages
- **Renovatebot**: automated dependency update governance
- **ESLint module boundaries**: runtime/compile-time import policy enforcement

The engineer who has only used one tool tries to make it solve all problems. The architect knows which layer each tool belongs to and configures them to work together. The failure mode they've seen is the team that adds Turborepo to an npm workspace without configuring remote caching (getting only half the benefit) or the team that starts publishing every internal package to npm because "that's how packages work" (adding ceremony that slows them down).

The goal is a developer experience where an engineer can clone the repo, run `pnpm install && pnpm dev`, and have the correct apps running against the correct local packages in under two minutes — and a CI experience where a focused PR completes in under five minutes regardless of how large the overall monorepo is.

---

*File: 15_monorepo_enterprise_tooling_interview.md*
*Last updated: 2026-08-21*
*Category: React / Enterprise Frontend Architecture*
