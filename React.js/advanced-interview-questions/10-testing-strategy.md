# Describe your testing approach for a large React app.

> **Interview priority:** SHOULD KNOW

## Question

Describe your testing approach for a large React app.

## Beginner Lens

Before memorizing the interview answer, follow the scenario and notice three things: the problem React is solving, the state or browser work that changes, and the rule that keeps the UI correct. Read the code blocks slowly and predict the next result before reading the explanation.

## Detailed Explanation

**HOW TO SAY IT:**

> "I think about testing in terms of confidence per dollar. An E2E test
> gives you high confidence but is expensive to write and slow to run.
> A unit test is cheap and fast but gives you narrow confidence.
> For a checkout flow in an e-commerce app, here's how I'd distribute..."

```
REAL APP: Swiggy-style Food Ordering — Testing Pyramid

          ╱━━━━━━━━━╲
         ╱   E2E     ╲        5 tests
        ╱  Playwright  ╲      Critical flows ONLY:
       ╱────────────────╲     - User places an order end-to-end
      ╱  Integration      ╲   - Payment succeeds
     ╱   RTL + MSW         ╲  - Delivery tracking updates
    ╱    (50-100 tests)      ╲
   ╱─────────────────────────╲
  ╱   Unit Tests               ╲  200+ tests
 ╱   Jest (reducers, utils,     ╲  - Price calculation fn
╱    custom hooks)               ╲  - Coupon validation
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ - useCartTotal hook

  INTEGRATION TEST EXAMPLE (what I test at this level):
  ─────────────────────────────────────────────────────
  // Full checkout flow: add item → apply coupon → pay → success
  test('user can complete checkout with valid coupon', async () => {
    // MSW intercepts real fetch calls — no axios-mock, no jest.mock
    server.use(
      http.get('/api/cart', () => HttpResponse.json(mockCart)),
      http.post('/api/coupon/SAVE20', () => HttpResponse.json({ discount: 20 })),
      http.post('/api/order', () => HttpResponse.json({ orderId: 'ORD-123' }))
    );

    render(<CheckoutPage />);

    // Act like a user
    await userEvent.type(screen.getByPlaceholderText('Coupon code'), 'SAVE20');
    await userEvent.click(screen.getByRole('button', { name: 'Apply' }));

    expect(await screen.findByText('₹20 discount applied')).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'Place Order' }));

    expect(await screen.findByText('Order ORD-123 confirmed!')).toBeInTheDocument();
  });
  // This test covers: input handling, API call, state update, success UI
  // All with real fetch() (intercepted by MSW), not mocked functions
```

```
WHY MSW OVER jest.mock:

  WITH jest.mock:                    WITH MSW:
  ───────────────────────            ─────────────────────────────────
  jest.mock('../api/cart');          server.use(
  // Mocks the import                 http.get('/api/cart', () =>
  // Brittle — if you rename            HttpResponse.json(mockCart))
  // the file, test breaks           );
  // If you switch from axios         // Intercepts at network level
  // to fetch, test still passes     // Works with ANY http client
  // (hiding a real bug)             // If you change axios → fetch,
                                     // test correctly re-validates
```

---
