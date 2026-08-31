#!/usr/bin/env node
/* Collection gate: prevents generic trace pages from being mistaken for code-level dry runs. */
const childProcess = require('child_process');
const fs = require('fs');
const path = require('path');

const root = __dirname;
const pages = fs.readdirSync(root)
  .filter((name) => name.endsWith('-dry-run.html'))
  .sort();
const failures = [];
const genericPages = [];
const placeholderStatePages = [];
const customPages = new Set([
  '01-lc-146-lru-cache-dry-run.html',
  '02-lc-207-course-schedule-dry-run.html',
  '05-lc-347-top-k-frequent-elements-dry-run.html',
]);

if (pages.length !== 70) {
  failures.push(`Expected 70 dry-run pages, found ${pages.length}.`);
}

for (const name of pages) {
  const html = fs.readFileSync(path.join(root, name), 'utf8');
  const required = ['id="play"', 'id="previous"', 'id="next"', 'id="reset"'];
  const missing = required.filter((value) => !html.includes(value));
  if (missing.length) failures.push(`${name}: missing controls ${missing.join(', ')}.`);
  if (!html.includes('trace-data') && !html.includes('const steps=')) {
    failures.push(`${name}: missing execution trace data.`);
  }
  if (html.includes('leetcode-video-decks')) {
    failures.push(`${name}: contains a link to the removed full-deck folder.`);
  }
  if (!customPages.has(name)) {
    if (!html.includes('id="code-data"') || !html.includes('scrollIntoView')) {
      genericPages.push(name);
      continue;
    }
    const codeMatch = html.match(/<script id="code-data" type="application\/json">([\s\S]*?)<\/script>/);
    const traceMatch = html.match(/<script id="trace-data" type="application\/json">([\s\S]*?)<\/script>/);
    try {
      const codeLines = JSON.parse(codeMatch[1]);
      const trace = JSON.parse(traceMatch[1]);
      const meaningfulLines = codeLines
        .map((line, index) => ({ line: line.trim(), number: index + 1 }))
        .filter(({ line }) => line && line !== '{' && line !== '}' && !line.startsWith('//'));
      const tracedLines = new Set(trace.map((step) => step.line));
      const missingLines = meaningfulLines.filter(({ number }) => !tracedLines.has(number));
      if (missingLines.length) throw new Error(`missing Java lines ${missingLines.map(({ number }) => number).join(', ')}`);
      for (const step of trace) {
        for (const field of ['line', 'kind', 'active', 'before', 'after', 'variables', 'explanation', 'invariant']) {
          if (!step[field]) throw new Error(`missing '${field}' field`);
        }
        if (!Number.isInteger(step.line) || step.line < 1 || step.line > codeLines.length) {
          throw new Error(`invalid code line ${step.line}`);
        }
        if (/before Java line|apply line|unchanged\.$/.test(step.before) || /before Java line|apply line|unchanged\.$/.test(step.after)) {
          placeholderStatePages.push(name);
          break;
        }
      }
    } catch (error) {
      failures.push(`${name}: invalid code-level trace (${error.message}).`);
    }
  }
}

try {
  childProcess.execFileSync('node', [path.join(root, '..', 'verify_lru_dry_run.js')], { stdio: 'pipe' });
} catch (error) {
  failures.push(`LRU behavioral gate failed: ${error.stderr?.toString().trim() || error.message}`);
}

try {
  childProcess.execFileSync('node', [path.join(root, 'verify_browser_dry_runs.js')], { stdio: 'pipe' });
} catch (error) {
  failures.push(`Browser trace gate failed: ${error.stderr?.toString().trim() || error.message}`);
}

if (genericPages.length) {
  failures.push(`${genericPages.length} pages are not code-level dry runs. They lack displayed Java code and statement-by-statement execution: ${genericPages.join(', ')}`);
}
if (placeholderStatePages.length) {
  failures.push(`${placeholderStatePages.length} pages use generic before/after text instead of algorithm-specific state and do not meet DRY_RUN_VISUALIZER_CONTRACT.md: ${placeholderStatePages.join(', ')}`);
}

if (failures.length) {
  console.error('Dry-run collection verification FAILED:');
  failures.forEach((failure) => console.error(`- ${failure}`));
  process.exit(1);
}

console.log(`Dry-run collection verification passed: ${pages.length} pages, 67 generated source-line traces, the LRU behavior gate, and the browser trace gate passed.`);