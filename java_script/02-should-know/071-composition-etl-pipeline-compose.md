# ETL Data Pipeline with compose — Flipkart Catalog Ingestion
> **Topic:** Composition | **Level:** Intermediate | **Frequency:** High

## The Setup
Flipkart receives 50,000 raw product records daily from sellers via CSV. Each record needs to be parsed, validated, GST-enriched, and normalized before hitting the catalog DB. A junior engineer wrote one 200-line `processProduct` function. You are doing the architecture review.

## The Question
How would you redesign this using function composition, and what concrete benefits does that give the team?

## Diagram

```
ETL Pipeline — pipe(parse, validate, enrichGst, normalize, formatForDb)

  rawCSVRow
     |
     v
+----------+       +-----------+       +----------+       +-----------+       +----------+
|  parse   | ----> | validate  | ----> | enrichGst| ----> | normalize | ----> | formatDb |
| str->obj |       | throw if  |       | add tax  |       | trim/case |       | shape    |
+----------+       | bad data  |       | fields   |       | fields    |       | for PG   |
                   +-----------+       +----------+       +-----------+       +----------+
                                                                                    |
                                                                                    v
                                                                              { name, price,
                                                                                priceWithGst,
                                                                                category }
Each box: pure, unary, independently unit-testable.
To add "applyDiscount" — insert one box. Zero changes to other boxes.
```

## Model Answer (15 YOE)

I would decompose the 200-line function into five focused pure functions and wire them with `pipe`. Here is the actual implementation:

```js
const pipe = (...fns) => x => fns.reduce((acc, fn) => fn(acc), x);

const parse        = raw  => ({ ...raw, price: Number(raw.price), stock: Number(raw.stock) });
const validate     = prod => { if (!prod.name || prod.price <= 0) throw new Error(`Invalid: ${prod.name}`); return prod; };
const enrichGst    = prod => ({ ...prod, priceWithGst: +(prod.price * 1.18).toFixed(2) });
const normalize    = prod => ({ ...prod, name: prod.name.trim().toLowerCase(), category: prod.category?.trim() });
const formatForDb  = prod => ({ name: prod.name, price: prod.price, priceWithGst: prod.priceWithGst, category: prod.category });

const processProduct = pipe(parse, validate, enrichGst, normalize, formatForDb);
```

The concrete team benefits: each stage has a unit test with zero setup — no mocks, no DB, just input/output. When the GST rate changes from 18% to 28%, I touch `enrichGst` only. When a new requirement arrives — "add brand normalization" — I insert `normalizeBrand` between `normalize` and `formatForDb`. The composition itself is self-documenting: one glance tells you the full processing sequence. The 200-line function required reading every line before trusting any change.

## Follow-up

**Q:** What happens if one stage needs to fetch exchange rates from an external API?

**A:** That stage is impure (I/O dependency), so it breaks the synchronous pipeline contract. I lift the whole pipeline into an async context: make the impure stage return a Promise, then use an async pipe variant that awaits each stage. Alternatively, I pre-fetch the rate outside the pipeline and pass it in via closure or partial application so the stage itself stays pure. The principle is: push I/O to the edges; keep the core transforms pure.
