# Async Generator for Paginated API — Flipkart Product Catalog Export
> **Topic:** Generator Functions | **Level:** Intermediate | **Frequency:** High

## The Setup

Flipkart needs to export all 2 million products from the catalog API to a CSV. The API returns 100 products per page. Loading everything into memory before writing a single CSV row is not viable. This tests understanding of async generators and the memory profile of `for await...of` versus `Promise.all`.

## The Question

"You need to export all 2 million products from the catalog API to a CSV. The API returns 100 products per page. How do you consume all pages without loading everything into memory?"

## Diagram

```
  yield products (page=5)
       │
       │  Consumer writes page 5 to CSV
       │  Consumer calls for await's internal .next()
       │
  <generator resumes>
  page++ → page=6
  await fetch(page=6)    ← real network call happens HERE, not before
       │
  yield products (page=6)
```

Memory profile: O(pageSize) at all times — never O(totalProducts).

## Model Answer (15 YOE)

The wrong answer: recursively fetch all pages, push to an array, return it. That is 2 million objects in heap before a single CSV row is written.

```js
async function* fetchProductPages(categoryId, pageSize = 100) {
  let page = 0;

  while (true) {
    const res = await fetch(
      `/api/catalog/products?category=${categoryId}&page=${page}&size=${pageSize}`
    );
    const products = await res.json();

    if (products.length === 0) return; // signals { done: true } to consumer

    yield products;  // hand back this page, freeze here

    page++;
  }
}

// Consumer — processes 100 products at a time, never more in memory
async function exportCatalogToCSV(categoryId) {
  const writer = createCsvWriteStream(`/exports/catalog-${categoryId}.csv`);

  for await (const productPage of fetchProductPages(categoryId, 100)) {
    for (const product of productPage) {
      writer.write(toCsvRow(product));
    }
  }

  writer.end();
  console.log('Export complete');
}
```

What makes this production-correct:
- `page` counter is encapsulated inside the generator — no external state to leak or reset accidentally
- If the export job crashes after page 40, you can resume by seeding `startPage=40`
- Memory profile stays at O(pageSize), not O(totalProducts)
- `for await...of` handles the `{ done: true }` check automatically — no manual `while (!done)` loop
- The network call on page 6 does not start until the consumer has finished writing page 5 — true backpressure

## Follow-up

**Q:** "Why `for await...of` and not `for...of`?"

**A:** `for...of` uses the sync `Symbol.iterator` protocol. It would iterate over the Promise objects themselves, not their resolved values. `for await...of` uses `Symbol.asyncIterator` and awaits each `.next()` call, so the consumer pauses until each page's network request resolves.

**Q:** "How do you add resumability if the export crashes mid-way?"

**A:** Pass a `startPage` parameter to the generator and persist the last successfully written page number to a checkpoint file. On restart, read the checkpoint and pass it as `startPage`.
