#!/usr/bin/env node
/* Exercise every generated trace step and fail on browser-side errors. */
const fs = require('fs');
const path = require('path');
const { pathToFileURL } = require('url');
const { chromium } = require('playwright');

const root = __dirname;
const custom = new Set([
  '01-lc-146-lru-cache-dry-run.html',
  '02-lc-207-course-schedule-dry-run.html',
  '05-lc-347-top-k-frequent-elements-dry-run.html',
]);
const pages = fs.readdirSync(root)
  .filter((name) => name.endsWith('-dry-run.html') && !custom.has(name))
  .sort();

(async () => {
  const browser = await chromium.launch({ headless: true });
  const failures = [];
  try {
    for (const name of pages) {
      const page = await browser.newPage();
      const errors = [];
      page.on('pageerror', (error) => errors.push(error.message));
      await page.goto(pathToFileURL(path.join(root, name)).href, { waitUntil: 'load' });
      const count = await page.evaluate(() => JSON.parse(document.querySelector('#trace-data').textContent).length);
      await page.evaluate((stepCount) => {
        for (let step = 1; step < stepCount; step += 1) document.querySelector('#next').click();
      }, count);
      const finalLabel = await page.locator('#label').textContent();
      if (!finalLabel.includes(`STEP ${count} / ${count}`)) errors.push(`final step label was '${finalLabel}'`);
      if (errors.length) failures.push(`${name}: ${errors.join('; ')}`);
      await page.close();
    }
  } finally {
    await browser.close();
  }
  if (failures.length) {
    console.error('Browser dry-run verification FAILED:');
    failures.forEach((failure) => console.error(`- ${failure}`));
    process.exit(1);
  }
  console.log(`Browser dry-run verification passed: exercised every trace step on ${pages.length} generated pages.`);
})().catch((error) => { console.error(error.stack || error); process.exit(1); });