# Partial Application in a Data Validation Pipeline
> **Topic:** Currying | **Level:** Intermediate | **Frequency:** Medium

## The Setup
You are designing a form validation library at Paytm that will be used across the checkout, KYC, and onboarding flows. Validators need to be composable — you should be able to build a phone number validator that is reused across forms, parameterize it with country-specific rules, and compose multiple validators into a pipeline without writing new functions for every combination.

## The Question
Show how currying and partial application enable a composable validator library. Include the difference between currying and partial application in your design.

## Diagram
```
  CURRIED VALIDATOR SHAPE:
  validate(rule)(errorMessage)(value) → { valid, error }

  PARTIAL APPLICATION to create reusable validators:
  ┌────────────────────────────────────────────────────┐
  │  const isRequired = validate(                      │
  │    v => v !== null && v !== ''                     │
  │  )('This field is required');                      │
  │  ← rule + message locked in → isRequired(value)   │
  └────────────────────────────────────────────────────┘

  COMPOSITION (not strict currying, more partial application):
  ┌────────────────────────────────────────────────────┐
  │  const validatePhone = compose(                    │
  │    isRequired,                                     │
  │    isNumeric,                                      │
  │    hasLength(10),     ← partial: length locked in  │
  │    matchesPattern(/^[6-9]/)  ← partial             │
  │  );                                                │
  │                                                    │
  │  validatePhone('9876543210'); // valid              │
  │  validatePhone('');           // "This field..."   │
  └────────────────────────────────────────────────────┘
```

## Model Answer (15 YOE)
Here I distinguish between currying and partial application precisely, because they are related but different tools.

Currying strictly means `f(a, b, c)` becomes `f(a)(b)(c)` — one argument per step. Partial application is broader — it means pre-filling some arguments and getting back a function that expects the rest, but those "rest" arguments can be multiple. `hasLength(10)` is partial application: the original function takes a length and a value, I pre-fill the length, and I get back a unary function that takes only the value. That is partial application. If I had written it as `hasLength(10)(value)` it would also be the curried form. In practice, for a validation library, I use whichever shape produces the cleanest composition syntax.

```js
// Curried validator factory
const validate = (rule) => (errorMessage) => (value) => ({
  valid: rule(value),
  error: rule(value) ? null : errorMessage,
});

// Partially applied validators (rule + message pre-filled)
const isRequired = validate(v => v != null && v !== '')('This field is required');
const isNumeric  = validate(v => /^\d+$/.test(v))('Must be numeric');
const hasLength  = (n) => validate(v => String(v).length === n)(`Must be ${n} digits`);
const matchesPattern = (re) => validate(v => re.test(v))('Invalid format');

// Compose runs validators left to right, returns first failure
const compose = (...validators) => (value) =>
  validators.reduce((result, fn) => result.valid ? fn(value) : result,
                    { valid: true, error: null });

const validateIndianPhone = compose(
  isRequired,
  isNumeric,
  hasLength(10),
  matchesPattern(/^[6-9]/),
);

validateIndianPhone('9876543210'); // { valid: true, error: null }
validateIndianPhone('');           // { valid: false, error: 'This field is required' }
validateIndianPhone('1234567890'); // { valid: false, error: 'Invalid format' }
```

The key architectural property: every validator in the library is a function that takes a value and returns a result object. They are interchangeable. Adding a new rule does not require modifying existing validators. Different forms compose different subsets — KYC form uses the full phone validator, a quick search bar uses only `isRequired`. The partial application that pre-fills the rule and message is what makes each named validator reusable without repetition.

## Follow-up
**Q:** When is partial application preferable to currying in a library API?

**A:** When the natural grouping of arguments does not align with single-at-a-time application. `hasLength(10)` is cleaner API design than `hasLength(10)(undefined)(value)` — the length and the error message are conceptually bound together in one configuration step. Partial application lets you group related arguments. Currying forces one-at-a-time. In a public API I design the grouping based on what callers naturally have at the same time, not based on theoretical purity of currying.
