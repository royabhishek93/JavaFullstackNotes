# Factory Function Pattern — Configurable Behavior Without Duplication
> **Topic:** Higher-Order Functions | **Level:** Intermediate | **Frequency:** Medium

## The Setup
A PhonePe backend has four fee calculators: NEFT (flat fee), IMPS (percentage), UPI (free), RTGS (tiered). A junior wrote four separate functions with identical branching logic, differing only in fee structure.

## The Question
Refactor using a factory function HOF. Show how the factory encapsulates config via closure.

## Diagram

```
Factory HOF — createFeeCalculator(config) returns a specialized function:

  createFeeCalculator({ type: 'flat',  amount: 2.5  })   --> neftFee(txn)
  createFeeCalculator({ type: 'pct',   rate: 0.002 })    --> impsFee(txn)
  createFeeCalculator({ type: 'free'               })    --> upiFee(txn)
  createFeeCalculator({ type: 'tiered', tiers: [...] })  --> rtgsFee(txn)

  Closure captures config:
  +------------------------+
  | createFeeCalculator    |
  |  config = { flat: 2.5} | <-- captured in closure
  |  return (txn) => {     |
  |    ... use config ...  |
  |  }                     |
  +------------------------+
         |
         v returns
  neftFee = (txn) => 2.5  (config baked in, not re-passed on each call)
```

## Model Answer (15 YOE)

```js
function createFeeCalculator(config) {
  switch (config.type) {
    case 'flat':
      return txn => config.amount;

    case 'percentage':
      return txn => +(txn.amount * config.rate).toFixed(2);

    case 'free':
      return txn => 0;

    case 'tiered':
      return txn => {
        const tier = config.tiers.find(t => txn.amount <= t.upTo) || config.tiers.at(-1);
        return tier.fee;
      };

    default:
      throw new Error(`Unknown fee type: ${config.type}`);
  }
}

// Config-driven — each instrument gets one factory call
const neftFee = createFeeCalculator({ type: 'flat',       amount: 2.5 });
const impsFee = createFeeCalculator({ type: 'percentage', rate: 0.002 });
const upiFee  = createFeeCalculator({ type: 'free' });
const rtgsFee = createFeeCalculator({ type: 'tiered', tiers: [
  { upTo: 200000,  fee: 25 },
  { upTo: 500000,  fee: 50 },
  { upTo: Infinity, fee: 100 },
]});

// Usage — all have identical call signature
const txn = { amount: 150000, instrument: 'RTGS' };
rtgsFee(txn); // 25

// Lookup table pattern — even cleaner at the call site
const feeCalc = { neft: neftFee, imps: impsFee, upi: upiFee, rtgs: rtgsFee };
const fee = feeCalc[txn.instrument.toLowerCase()](txn);
```

The factory captures `config` via closure — the returned function never re-receives it. Each specialized function has an identical call signature `(txn) => fee`, which means they are interchangeable in a pipeline or lookup table. Adding a new instrument is one factory call and one lookup-table entry — zero changes to existing functions. Compare this to the junior's approach: four functions with near-identical switch statements that all need updating when the base logic changes.

## Follow-up

**Q:** How do you test factory-generated functions in isolation?

**A:** Each generated function is a plain unary function — test it directly with representative inputs: `expect(impsFee({ amount: 10000 })).toBe(20)`. Test the factory itself by asserting it throws on unknown types and returns a function for known types. The closure config is an implementation detail — you test observable behavior (fee output), not the captured config directly.
