# React Testing — 15-YOE Interview Prep

> Target role: Staff / Principal / Senior II Engineer
> Stack: React + TypeScript, Jest/Vitest, React Testing Library, MSW, Playwright

---

## 1. THE BIG PICTURE — Testing Pyramid

```
                         ▲
                        /E\         E2E Tests
                       / 2 \       (Playwright / Cypress)
                      / E   \      • Fewest tests
                     /  ────  \    • Highest confidence
                    /  Integ.  \   • Slowest & most flaky
                   /  Tests     \  • Cost: $$$
                  / ──────────── \
                 / Unit  Tests    \  Integration Tests
                / RTL components  \  (RTL + MSW, Hooks)
               /  Custom hooks     \ • Medium confidence
              /   Pure functions    \• Medium cost
             / ───────────────────── \
            /   Unit Tests            \
           /  (utils, reducers, pure    \
          /   functions, transformers)   \
         /─────────────────────────────── \
        /                                  \
       ────────────────────────────────────

  Speed:  ████████████  ████████   ██
          Unit          Integ.     E2E
  Cost:   Low           Medium     High
  Conf:   Low           Medium     High (when not flaky)

  RTL PHILOSOPHY:
  "The more your tests resemble the way your software is used,
   the more confidence they can give you." — Kent C. Dodds

  ┌─────────────────────────────────────────────────────────┐
  │  Test Type     │  Tools            │  Isolation Level   │
  ├─────────────────────────────────────────────────────────┤
  │  Unit          │  Jest/Vitest      │  Full isolation     │
  │  Integration   │  RTL + MSW        │  Module boundaries  │
  │  E2E           │  Playwright       │  Real browser/app   │
  │  Visual        │  Chromatic        │  Pixel diffing      │
  │  Accessibility │  axe-core + RTL   │  DOM + ARIA         │
  └─────────────────────────────────────────────────────────┘

  WHERE TO INVEST (Staff-level answer):
  - 70% Integration (RTL + MSW) — highest ROI
  - 20% Unit (pure functions, reducers, utils)
  - 10% E2E (critical user journeys only: checkout, auth, onboarding)
```

---

## 2. CONVERSATIONAL INTERVIEW SCRIPT

### How a 15-YOE Engineer Opens the Testing Conversation

**Interviewer:** "Walk me through your testing philosophy for React applications."

**You (staff-level response):**

"My philosophy is anchored in the testing pyramid, but I think about it in terms of ROI rather than just quantity. At this point in my career, I've seen teams write hundreds of unit tests that gave zero confidence in production — and I've seen a handful of well-written integration tests catch critical regressions for years.

For React specifically, I align with RTL's design philosophy: tests should interact with components the way users do — by finding elements by role, label, or text, not by class names or implementation details. The moment your test knows about internal state or which child component rendered, it's testing implementation, not behavior. Those tests break on every refactor and slow you down.

My go-to stack is React Testing Library for everything from unit hooks to component integration, MSW for API-layer mocking so the HTTP layer is real, and Playwright for 5-10 critical E2E flows. I use Jest or Vitest depending on the build tool — Vitest for Vite-based apps because the config overhead is nearly zero.

In terms of where I've made mistakes: early in my career I over-mocked. I'd mock child components, mock every hook, and end up testing an empty box. The test passed because the mock passed. Now I mock at the network boundary — MSW intercepts the actual fetch calls — and let real components render. That gives you honest signal."

---

### How to Answer "What's Your Coverage Target?"

"Coverage percentage is a vanity metric in isolation. A codebase can have 100% line coverage and still have zero tests for the critical paths — because line coverage tells you which lines were *executed*, not whether behavior was *asserted*.

What I actually care about: branch coverage on business logic, mutation testing scores on domain code, and whether the test suite reliably catches regressions in the staging-to-prod pipeline. A team I joined had 85% coverage but the payment flow had no tests — every deploy was a prayer.

That said, if I need a number for a mandate: 80% line coverage as a floor to block CI, with strict branch coverage requirements on anything touching money, auth, or data mutations."

---

## 3. SCENARIO-BASED Q&As (Production Context)

### Q1: "How do you test a form with async validation?"

**Scenario:** A registration form that checks username availability via API on blur.

**Answer:**

"I use MSW to intercept the API call and RTL's `userEvent` for real interaction. The key is `userEvent.type` returns a promise in v14+, so you await it, then wait for the async feedback to appear."

```typescript
// src/__tests__/RegistrationForm.test.tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { server } from '../mocks/server';
import { RegistrationForm } from '../RegistrationForm';

test('shows error when username is taken', async () => {
  server.use(
    http.get('/api/check-username', () =>
      HttpResponse.json({ available: false })
    )
  );

  const user = userEvent.setup();
  render(<RegistrationForm />);

  await user.type(screen.getByLabelText(/username/i), 'takenUser');
  await user.tab(); // triggers blur → API call

  expect(
    await screen.findByText(/username is already taken/i)
  ).toBeInTheDocument();
});
```

"Notice I use `findByText` not `getByText` — `findBy` returns a promise and retries until the element appears or times out. That's the async assertion pattern."

---

### Q2: "How do you test a component that uses React Query?"

**Answer:**

"I wrap the component in a `QueryClientProvider` with a fresh `QueryClient` per test — no cache sharing between tests. I mock the network with MSW, not `useQuery` itself. Mocking `useQuery` is over-mocking — you lose confidence that the query config, error handling, and loading states work."

```typescript
// test-utils/wrappers.tsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { PropsWithChildren } from 'react';

export function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
}

export function QueryWrapper({ children }: PropsWithChildren) {
  const client = createTestQueryClient();
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

// UserProfile.test.tsx
test('displays user data from API', async () => {
  server.use(
    http.get('/api/users/42', () =>
      HttpResponse.json({ id: 42, name: 'Ada Lovelace' })
    )
  );

  render(<UserProfile userId={42} />, { wrapper: QueryWrapper });

  expect(await screen.findByText('Ada Lovelace')).toBeInTheDocument();
});
```

---

### Q3: "How do you test a custom hook?"

**Answer:**

"With `renderHook` from RTL. The trap most people fall into is forgetting `act()` when the hook triggers state updates that happen outside of React's normal event flow — like in a `setInterval` or after an awaited promise."

```typescript
// useCounter.test.ts
import { renderHook, act } from '@testing-library/react';
import { useCounter } from '../useCounter';

test('increments counter', () => {
  const { result } = renderHook(() => useCounter(0));

  act(() => {
    result.current.increment();
  });

  expect(result.current.count).toBe(1);
});

test('async reset after delay', async () => {
  const { result } = renderHook(() => useCounter(5));

  await act(async () => {
    await result.current.resetAfterDelay(100);
  });

  expect(result.current.count).toBe(0);
});
```

---

### Q4: "How do you test Zustand stores?"

**Answer:**

"Two approaches depending on what you're testing. For the store logic in isolation, import the store and call actions directly — Zustand stores are just functions. For component-store integration, render the component and assert via the DOM."

```typescript
// cartStore.test.ts — testing store logic directly
import { useCartStore } from '../stores/cartStore';

beforeEach(() => {
  useCartStore.getState().reset(); // reset between tests
});

test('adds item to cart', () => {
  const { addItem, items } = useCartStore.getState();
  addItem({ id: '1', name: 'Widget', price: 9.99 });
  expect(useCartStore.getState().items).toHaveLength(1);
});

test('calculates total correctly', () => {
  const store = useCartStore.getState();
  store.addItem({ id: '1', name: 'A', price: 10 });
  store.addItem({ id: '2', name: 'B', price: 5 });
  expect(store.total()).toBe(15);
});
```

---

### Q5: "How do you handle flaky tests?"

**Answer:**

"Flakiness is almost always caused by one of five things: timing assumptions, shared state between tests, non-deterministic data (like `Date.now()`), network calls leaking through, or test order dependencies.

My debugging checklist:
1. Run the failing test in isolation — if it passes, it's a shared state problem.
2. Check if timers or `Date` are used without mocking — use `jest.useFakeTimers()` or `vi.useFakeTimers()`.
3. Verify MSW is resetting handlers between tests via `afterEach(() => server.resetHandlers())`.
4. For E2E flakiness: add explicit waits on element visibility (`await page.waitForSelector()`), never sleep arbitrary milliseconds.
5. Use `--runInBand` to identify race conditions in parallel test runners."

---

### Q6: "How do you test error boundaries?"

**Answer:**

"You have to suppress the `console.error` output React prints — otherwise the test output is noisy and CI shows red even when the test passes. Then spy on the component that throws."

```typescript
// ErrorBoundary.test.tsx
const ThrowingComponent = ({ shouldThrow }: { shouldThrow: boolean }) => {
  if (shouldThrow) throw new Error('Boom');
  return <div>OK</div>;
};

test('renders fallback on error', () => {
  const consoleSpy = jest
    .spyOn(console, 'error')
    .mockImplementation(() => {});

  render(
    <ErrorBoundary fallback={<p>Something went wrong</p>}>
      <ThrowingComponent shouldThrow />
    </ErrorBoundary>
  );

  expect(screen.getByText('Something went wrong')).toBeInTheDocument();
  consoleSpy.mockRestore();
});
```

---

### Q7: "What's your approach to accessibility testing?"

**Answer:**

"Automated testing with axe-core catches roughly 30-40% of WCAG issues — the deterministic ones like missing alt attributes, improper heading hierarchy, missing form labels. The other 60% require manual testing with real screen readers.

I integrate `@axe-core/react` in dev mode to get real-time feedback, and use `jest-axe` in tests for assertions. But more importantly, I use RTL's `getByRole` — which forces me to think about ARIA semantics at authoring time."

```typescript
// Dashboard.test.tsx — axe integration
import { axe, toHaveNoViolations } from 'jest-axe';
expect.extend(toHaveNoViolations);

test('Dashboard has no accessibility violations', async () => {
  const { container } = render(<Dashboard />);
  const results = await axe(container);
  expect(results).toHaveNoViolations();
});

// Correct query — role-based, accessibility-correct
test('submit button is keyboard accessible', () => {
  render(<LoginForm />);
  const button = screen.getByRole('button', { name: /sign in/i });
  expect(button).toBeEnabled();
});
```

---

### Q8: "How do you test file uploads?"

**Answer:**

"RTL's `userEvent.upload()` handles this. You create a `File` object and pass it to the input. The tricky part is when the component reads the file content — you may need to mock `FileReader`."

```typescript
test('uploads image and shows preview', async () => {
  const user = userEvent.setup();
  render(<ImageUploader />);

  const file = new File(['(image data)'], 'photo.png', { type: 'image/png' });
  const input = screen.getByLabelText(/upload image/i);

  await user.upload(input, file);

  expect(await screen.findByAltText(/preview/i)).toBeInTheDocument();
  expect(screen.getByText('photo.png')).toBeInTheDocument();
});
```

---

## 4. ADVANCED SCENARIO Q&As

### AQ1: "How do you test a component that uses IntersectionObserver for infinite scroll?"

**Answer:**

"IntersectionObserver is a browser API not available in jsdom. You mock it in your test setup, then trigger intersection callbacks manually."

```typescript
// jest.setup.ts — mock IntersectionObserver
const mockIntersectionObserver = jest.fn().mockImplementation((callback) => ({
  observe: jest.fn((element) => {
    // Store callback to trigger manually in tests
    (element as any).__intersectionCallback = callback;
  }),
  unobserve: jest.fn(),
  disconnect: jest.fn(),
}));
global.IntersectionObserver = mockIntersectionObserver;

// InfiniteList.test.tsx
test('loads more items when sentinel is visible', async () => {
  server.use(
    http.get('/api/items', ({ request }) => {
      const url = new URL(request.url);
      const page = url.searchParams.get('page') ?? '1';
      return HttpResponse.json({ items: [`item-page-${page}`], hasMore: true });
    })
  );

  render(<InfiniteList />);
  expect(await screen.findByText('item-page-1')).toBeInTheDocument();

  // Simulate the sentinel becoming visible
  const sentinel = document.querySelector('[data-testid="sentinel"]')!;
  act(() => {
    (sentinel as any).__intersectionCallback([{ isIntersecting: true }]);
  });

  expect(await screen.findByText('item-page-2')).toBeInTheDocument();
});
```

---

### AQ2: "How do you test React concurrent features and Suspense?"

**Answer:**

"Testing Suspense-wrapped components requires wrapping renders in `act()` to flush all state transitions. In RTL v13+ running React 18, this is largely handled automatically, but you need to ensure the deferred data actually resolves.

The key insight: `findBy*` queries wait for async transitions, including Suspense fallback → content transitions. Mock the resource with MSW and use `findBy`."

```typescript
// ProductPage.test.tsx — uses Suspense + React Query
test('shows product after suspense resolves', async () => {
  server.use(
    http.get('/api/products/1', () =>
      HttpResponse.json({ id: 1, name: 'Keyboard', price: 149 })
    )
  );

  render(
    <Suspense fallback={<div>Loading...</div>}>
      <ProductPage productId={1} />
    </Suspense>,
    { wrapper: QueryWrapper }
  );

  // Loading state is visible initially
  expect(screen.getByText('Loading...')).toBeInTheDocument();

  // Wait for Suspense to resolve
  expect(await screen.findByText('Keyboard')).toBeInTheDocument();
  expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
});
```

---

### AQ3: "How do you structure MSW in a large codebase?"

**Answer:**

"I treat MSW handlers like fixtures — organized by domain, with a base set for the happy path and per-test overrides for edge cases. The `server.use()` call adds a one-time override that MSW prioritizes over base handlers, and `server.resetHandlers()` in `afterEach` brings you back to baseline."

```typescript
// mocks/handlers/users.ts
import { http, HttpResponse } from 'msw';

export const userHandlers = [
  http.get('/api/users/:id', ({ params }) =>
    HttpResponse.json({ id: params.id, name: 'Default User', role: 'user' })
  ),
  http.post('/api/users', async ({ request }) => {
    const body = await request.json() as Record<string, unknown>;
    return HttpResponse.json({ id: 'new-id', ...body }, { status: 201 });
  }),
];

// mocks/server.ts
import { setupServer } from 'msw/node';
import { userHandlers } from './handlers/users';
import { productHandlers } from './handlers/products';

export const server = setupServer(...userHandlers, ...productHandlers);

// In test: override for error scenario
test('shows error message on network failure', async () => {
  server.use(
    http.get('/api/users/:id', () =>
      HttpResponse.error()
    )
  );
  // ... rest of test
});
```

---

### AQ4: "How do you approach mutation testing and when is it worth it?"

**Answer:**

"Mutation testing (Stryker for JS/TS) works by automatically introducing bugs — flipping `>` to `>=`, removing conditionals — and checking if your tests fail. If a mutant survives, your tests didn't catch that code change.

It's the highest-signal coverage metric because it answers 'do my tests actually assert anything meaningful?' Line coverage can't tell you that.

When it's worth it: high-stakes business logic — pricing calculators, authorization rules, data validation. Not worth running on UI-heavy components or generated code — the mutation score will be low and misleading.

Setup: Stryker with Jest or Vitest, configured to only run on specific directories like `src/domain/` or `src/utils/`. Run in CI on PRs that touch business logic, not on every push (mutation testing is slow — 10-20x the test runtime)."

---

## 5. SENIOR TRAP QUESTIONS

### Trap 1: "100% test coverage means the code has no bugs."

**THE TRAP:** The interviewer is testing whether you understand what coverage actually measures.

**Wrong answer:** "Yes, 100% coverage gives us full confidence."

**Correct answer:**

"This is a dangerous misconception I've seen cause real production incidents. Line coverage only tells you that a line was executed during a test run — it says nothing about whether the behavior was asserted. You can have 100% coverage with `expect(true).toBe(true)` as every assertion.

Real example: I inherited a codebase with 94% coverage where the discount calculation had a test, but the test never asserted the discount amount — it only asserted the function didn't throw. A pricing bug shipped to production.

The meaningful metric is branch coverage + mutation score. And beyond numbers: does the test fail when I break the behavior? That's the real question."

---

### Trap 2: "getByText is the best query selector in RTL."

**THE TRAP:** Preferring text queries over role queries misses accessibility and is more brittle.

**Wrong answer:** "Yes, `getByText` is easy to use and precise."

**Correct answer:**

"I actually consider `getByRole` the default choice, with `getByText` as a fallback for non-interactive content. Here's why: `getByRole` queries the accessibility tree, which is what screen readers and assistive technology see. If `getByRole('button', { name: 'Submit' })` fails, it means the button isn't properly labeled for accessibility — that's a bug you just caught for free.

`getByText` can find elements a screen reader would skip entirely, giving you false confidence. It's also more fragile — copy changes break it even when the button still works.

RTL's recommended query priority:
1. `getByRole` (most users experience the app this way)
2. `getByLabelText` (forms)
3. `getByPlaceholderText` (when no label)
4. `getByText` (non-interactive: paragraphs, headings)
5. `getByTestId` (last resort — escape hatch)"

---

### Trap 3: "You should mock everything in unit tests for isolation."

**THE TRAP:** Over-mocking creates tests that only verify the mock's behavior, not real code.

**Wrong answer:** "Yes, unit tests should mock all dependencies to be truly isolated."

**Correct answer:**

"Over-mocking is one of the most common testing mistakes I see in codebases. When you mock your child components, your custom hooks, your utilities — you're testing a hollow shell. The test passes because the mock passes, but the real integration might be completely broken.

The question I ask is: where is the real uncertainty? For network calls, mock at the HTTP boundary with MSW — let the real `fetch`, the real query function, the real serialization code all run. The mock lives outside your application code.

I only mock: the network (MSW), time (fake timers), external SDKs (Stripe, analytics, third-party auth), and browser APIs not in jsdom (IntersectionObserver, ResizeObserver, canvas).

I don't mock: my own utility functions, my own hooks, my own sub-components. Those should integrate and break visibly when something changes."

---

### Trap 4: "Snapshot tests prevent regressions."

**THE TRAP:** Snapshot tests are often treated as a safety net when they're actually a false confidence trap.

**Wrong answer:** "Yes, snapshots are great for catching unintended UI changes."

**Correct answer:**

"Snapshot tests have a specific failure mode that makes them counterproductive: the 'update all' reflex. When developers run `jest --updateSnapshot` without carefully reviewing what changed — which is extremely common — snapshots become documentation of current state, not assertions of intended behavior.

I've reviewed PRs where 500 snapshot lines changed because someone updated a spacing constant, the developer ran `--updateSnapshot`, and a real DOM structure regression was buried in the diff.

When I do use snapshots: small, focused inline snapshots of specific values — not entire component trees. Inline snapshots (`.toMatchInlineSnapshot()`) are better because reviewers see the actual expected value in the PR diff.

When I avoid them: any large component, any component that frequently changes markup, any component where the important behavior is interaction, not structure."

---

### Trap 5: "E2E tests should cover all scenarios for maximum confidence."

**THE TRAP:** Inverting the pyramid destroys build speed and creates a flaky test suite.

**Wrong answer:** "E2E tests give the most confidence, so more is better."

**Correct answer:**

"Inverting the testing pyramid is a common anti-pattern I've had to reverse on multiple teams. E2E tests are expensive in every dimension: slow to run (minutes vs milliseconds), expensive to maintain, flaky due to network timing, and they serialize — you can't easily parallelize 200 Playwright tests without significant infrastructure.

A team I worked with had 400 Cypress tests and a 45-minute CI pipeline. No one ran tests locally. PRs sat for 2 hours. We cut that to 40 E2E tests covering the core user journeys — checkout, auth, onboarding — and moved everything else to RTL integration tests. Pipeline dropped to 8 minutes.

The right E2E test question: 'Is this something that can only be verified in a real browser with a real server?' If the answer is no, move it down the pyramid."

---

### Trap 6: "fireEvent is the same as userEvent in RTL."

**THE TRAP:** `fireEvent` is a low-level synthetic event dispatcher; `userEvent` simulates real browser interactions.

**Wrong answer:** "They're basically the same — both fire DOM events."

**Correct answer:**

"`fireEvent` dispatches a single synthetic DOM event. `userEvent` simulates the full sequence of events a real user produces. When a user types in an input, the browser fires: `pointerover`, `pointerenter`, `mouseover`, `mouseenter`, `pointermove`, `mousemove`, `pointerdown`, `mousedown`, `focus`, `keydown`, `keypress`, `input`, `keyup` — and more. `fireEvent.change()` fires exactly one event.

This gap matters when: components use `onKeyDown` to block characters, when there's logic on `onPointerDown`, when focus management is involved, or when you're testing character-by-character validation.

`userEvent.type()` is also promise-based in v14, meaning each character is awaited and you can test intermediate states.

Practical rule: use `userEvent` for all user interactions in tests. Reserve `fireEvent` for testing how your component responds to events it wouldn't normally receive — like simulating browser-level drag events or testing edge-case event handling."

---

## 6. PRODUCTION CODE EXAMPLES

### Example 1: Full Form Integration Test

```typescript
// LoginForm.test.tsx
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { server } from '../mocks/server';
import { LoginForm } from '../LoginForm';

const setup = () => {
  const user = userEvent.setup();
  render(<LoginForm />);
  return {
    user,
    emailInput: screen.getByRole('textbox', { name: /email/i }),
    passwordInput: screen.getByLabelText(/password/i),
    submitButton: screen.getByRole('button', { name: /sign in/i }),
  };
};

test('successful login redirects to dashboard', async () => {
  server.use(
    http.post('/api/auth/login', () =>
      HttpResponse.json({ token: 'abc123', redirectTo: '/dashboard' })
    )
  );

  const { user, emailInput, passwordInput, submitButton } = setup();

  await user.type(emailInput, 'ada@example.com');
  await user.type(passwordInput, 'secure-pass-123');
  await user.click(submitButton);

  expect(await screen.findByText(/welcome back/i)).toBeInTheDocument();
});

test('shows field errors on server validation failure', async () => {
  server.use(
    http.post('/api/auth/login', () =>
      HttpResponse.json(
        { errors: { email: 'No account with this email' } },
        { status: 422 }
      )
    )
  );

  const { user, emailInput, passwordInput, submitButton } = setup();

  await user.type(emailInput, 'unknown@example.com');
  await user.type(passwordInput, 'wrong');
  await user.click(submitButton);

  expect(
    await screen.findByText('No account with this email')
  ).toBeInTheDocument();
});
```

---

### Example 2: Testing a Custom Hook with Async State

```typescript
// useProductSearch.test.ts
import { renderHook, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { server } from '../mocks/server';
import { useProductSearch } from '../hooks/useProductSearch';
import { QueryWrapper } from '../test-utils/wrappers';

test('fetches products based on search query', async () => {
  server.use(
    http.get('/api/products', ({ request }) => {
      const q = new URL(request.url).searchParams.get('q');
      return HttpResponse.json({
        results: [{ id: 1, name: `Result for ${q}` }],
      });
    })
  );

  const { result } = renderHook(
    () => useProductSearch('keyboard'),
    { wrapper: QueryWrapper }
  );

  expect(result.current.isLoading).toBe(true);

  await waitFor(() => {
    expect(result.current.isLoading).toBe(false);
  });

  expect(result.current.data?.results[0].name).toBe('Result for keyboard');
});
```

---

### Example 3: Vitest vs Jest — Config Comparison

```typescript
// vitest.config.ts — minimal setup for Vite projects
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test-setup.ts'],
    globals: true, // enables describe/test/expect without imports
  },
});

// jest.config.ts — equivalent setup
export default {
  testEnvironment: 'jsdom',
  setupFilesAfterFramework: ['./src/test-setup.ts'],
  transform: {
    '^.+\\.(ts|tsx)$': ['babel-jest', { presets: ['@babel/preset-typescript'] }],
  },
};

// Key differences:
// - Vitest: native ESM, no transform config needed for Vite codebases
// - Vitest: uses Vite's resolver — same aliases, same env variables
// - Vitest: watch mode is faster (HMR-based, not jest's file-hash)
// - Jest: larger ecosystem, better snapshot diffing UX, jest-circus default runner
// - Migration: @jest-environment-vitest-jsdom, vitest's jest compat API covers 95%
```

---

### Example 4: Playwright E2E — Checkout Flow

```typescript
// e2e/checkout.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Checkout flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/products');
  });

  test('completes purchase end-to-end', async ({ page }) => {
    await page.getByRole('button', { name: /add to cart/i }).first().click();
    await page.getByRole('link', { name: /cart/i }).click();
    await page.getByRole('button', { name: /proceed to checkout/i }).click();

    await page.getByLabel('Card number').fill('4242424242424242');
    await page.getByLabel('Expiry').fill('12/28');
    await page.getByLabel('CVC').fill('123');

    await page.getByRole('button', { name: /place order/i }).click();

    await expect(
      page.getByRole('heading', { name: /order confirmed/i })
    ).toBeVisible({ timeout: 10_000 });
  });
});
```

---

### Example 5: Testing with Fake Timers

```typescript
// AutoSave.test.tsx
import { render, screen, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AutoSaveForm } from '../AutoSaveForm';

test('auto-saves after 2 seconds of inactivity', async () => {
  const onSave = jest.fn();
  jest.useFakeTimers();

  const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
  render(<AutoSaveForm onSave={onSave} />);

  await user.type(screen.getByRole('textbox'), 'Hello world');

  expect(onSave).not.toHaveBeenCalled();

  act(() => {
    jest.advanceTimersByTime(2000);
  });

  expect(onSave).toHaveBeenCalledWith({ content: 'Hello world' });

  jest.useRealTimers();
});
```

---

### Example 6: Accessible Component Query Patterns

```typescript
// Navigation.test.tsx — demonstrates correct query usage
test('navigation renders landmark regions correctly', () => {
  render(<SiteNavigation />);

  // Landmarks — use getByRole
  expect(screen.getByRole('navigation')).toBeInTheDocument();
  expect(screen.getByRole('banner')).toBeInTheDocument(); // <header>
  expect(screen.getByRole('main')).toBeInTheDocument();

  // Interactive elements — use getByRole with name
  const navLinks = screen.getAllByRole('link');
  expect(navLinks.length).toBeGreaterThan(0);

  // Current page — accessible state
  const currentLink = screen.getByRole('link', { name: /home/i });
  expect(currentLink).toHaveAttribute('aria-current', 'page');
});
```

---

### Example 7: CI Test Configuration (GitHub Actions)

```yaml
# .github/workflows/test.yml
name: Test
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        shard: [1, 2, 3, 4] # parallel shards

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: npm

      - run: npm ci

      - name: Run tests (shard ${{ matrix.shard }}/4)
        run: |
          npx vitest run \
            --reporter=junit \
            --outputFile=test-results/junit-${{ matrix.shard }}.xml \
            --shard=${{ matrix.shard }}/4

      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: test-results-${{ matrix.shard }}
          path: test-results/
```

---

## 7. VITEST vs JEST — DECISION FRAMEWORK

```
Project uses Vite?
├── YES → Use Vitest
│   • Zero config for TypeScript/JSX
│   • Shares Vite's resolver (path aliases just work)
│   • Native ESM, no babel transform needed
│   • `vi` is a drop-in for `jest` namespace
│
└── NO (webpack/CRA/Next.js)
    ├── Next.js → Jest with @next/jest preset (official support)
    ├── CRA → Jest (built in, don't fight it)
    └── Custom webpack → Jest with babel-jest

MIGRATION CHECKLIST (Jest → Vitest):
□ Replace jest.* calls with vi.* (or enable globals: true for compat)
□ Replace @types/jest with @vitest/globals
□ Verify msw setup works (node vs browser environment)
□ Check jest.mock paths — Vitest uses same API
□ Update coverage: c8 (faster) or istanbul (more compatible)
□ Run tests with --reporter=verbose to catch any silent failures
```

---

## 8. INTERVIEW CHEAT SHEET

```
┌─────────────────────────────────────────────────────────────────────┐
│                   REACT TESTING QUICK REFERENCE                      │
├────────────────────┬────────────────────────────────────────────────┤
│  QUERY PREFIX      │  USE WHEN                                       │
├────────────────────┼────────────────────────────────────────────────┤
│  getBy*            │  Element must exist NOW (throws if not found)   │
│  queryBy*          │  Element might not exist (returns null)         │
│  findBy*           │  Element will exist EVENTUALLY (returns Promise)│
│  getAllBy*         │  Multiple elements, throws if none              │
│  queryAllBy*       │  Multiple elements, returns [] if none          │
│  findAllBy*        │  Multiple elements, async, returns Promise      │
├────────────────────┼────────────────────────────────────────────────┤
│  QUERY TYPE        │  PRIORITY                                       │
├────────────────────┼────────────────────────────────────────────────┤
│  getByRole         │  1st — accessibility-correct, use always        │
│  getByLabelText    │  2nd — forms                                    │
│  getByPlaceholder  │  3rd — when no label exists                     │
│  getByText         │  4th — non-interactive content                  │
│  getByTestId       │  Last resort — add data-testid as escape hatch  │
├────────────────────┼────────────────────────────────────────────────┤
│  ASYNC PATTERN     │  CODE                                           │
├────────────────────┼────────────────────────────────────────────────┤
│  Wait for element  │  await screen.findByText('Hello')               │
│  Wait for removal  │  await waitForElementToBeRemoved(spinner)       │
│  Wait for condition│  await waitFor(() => expect(...))               │
│  User events       │  await userEvent.click(button)                  │
├────────────────────┼────────────────────────────────────────────────┤
│  MOCKING           │  WHEN TO USE                                    │
├────────────────────┼────────────────────────────────────────────────┤
│  MSW               │  All HTTP calls (preferred, real fetch runs)    │
│  jest.mock()       │  3rd party modules, browser APIs, timers        │
│  jest.spyOn()      │  Observe calls without replacing implementation │
│  jest.fn()         │  Callback props, event handlers                 │
│  vi.useFakeTimers  │  setTimeout, setInterval, Date.now()            │
├────────────────────┼────────────────────────────────────────────────┤
│  TRAP              │  CORRECT POSITION                               │
├────────────────────┼────────────────────────────────────────────────┤
│  100% cov = safe   │  Coverage ≠ correctness. Use mutation testing   │
│  Mock everything   │  Mock at network boundary, not components       │
│  E2E for all cases │  Keep pyramid shape — E2E is slow + flaky       │
│  Snapshot safety   │  Inline, focused, not full trees                │
│  getByText first   │  getByRole first for accessibility              │
│  fireEvent = user  │  userEvent fires full event sequences           │
└────────────────────┴────────────────────────────────────────────────┘

KEY PACKAGES (with versions as of 2025):
  @testing-library/react     ^16.0
  @testing-library/user-event ^14.5
  @testing-library/jest-dom  ^6.0
  msw                        ^2.0  (note: breaking changes from v1)
  vitest                     ^2.0
  jest                       ^29.0
  @playwright/test           ^1.45
  jest-axe / axe-core        ^4.x
  stryker-cli (mutation)     ^8.x

MSW v2 BREAKING CHANGES (common interview gotcha):
  v1: rest.get('/api/x', (req, res, ctx) => res(ctx.json({...})))
  v2: http.get('/api/x', () => HttpResponse.json({...}))   ← new API

TESTING HOOKS THAT NEED CONTEXT:
  renderHook(() => useMyHook(), {
    wrapper: ({ children }) => (
      <MyContext.Provider value={mockValue}>{children}</MyContext.Provider>
    ),
  });

ACT() RULES:
  - Wrap state updates that happen OUTSIDE React's event system
  - RTL wraps most interactions automatically (userEvent, fireEvent)
  - Manual act() needed for: setTimeout callbacks, Promise resolution
    inside setInterval, manually calling store actions in hook tests

COVERAGE COMMANDS:
  vitest run --coverage                    # c8 provider (default)
  vitest run --coverage --coverage.provider=istanbul
  jest --coverage --collectCoverageFrom='src/**/*.{ts,tsx}'

DEBUGGING TESTS:
  screen.debug()                           # print current DOM
  screen.logTestingPlaygroundURL()         # open visual query helper
  await screen.findByText('x', {}, { timeout: 5000 }) # extend timeout
```

---

## 9. BONUS: WHAT MAKES A 15-YOE ANSWER STAND OUT

**Junior answer:** "I write unit tests with Jest and use describe/it blocks."

**Mid-level answer:** "I use RTL with `userEvent` and mock my API calls."

**Senior answer:** "I prioritize integration tests with RTL + MSW. I avoid over-mocking — the network boundary is where mocking lives, not inside my component tree. I use accessibility queries first, which catches a11y bugs for free. My coverage target is a floor, not a goal — I care more about whether the test suite catches production-like failures."

**Staff answer:** "My test strategy starts from the failure modes of the system. I map the critical user journeys, ensure each has an integration test (happy path + primary failure modes), and add E2E tests only for things that can't be verified without a real browser. I use mutation testing on domain logic to verify test quality, not just coverage. I treat flakiness as a bug — it degrades team trust in the suite, which leads to 'update all' habits. I measure how often the test suite catches a regression before it ships. That's the only metric that matters."

---

*Last updated: 2025 — React 18/19, RTL v16, MSW v2, Vitest v2, Playwright v1.45*
