#!/usr/bin/env node
/**
 * Unified behavioral verification for all dry-run pages.
 * Extracts and validates JavaScript data structures from HTML pages.
 */
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const root = __dirname;
const customPages = new Set([
  '01-lc-146-lru-cache-dry-run.html', // Has dedicated verify_lru_dry_run.js
]);

const pages = fs.readdirSync(root)
  .filter((name) => name.endsWith('-dry-run.html') && !customPages.has(name))
  .sort();

console.log(`Verifying ${pages.length} dry-run pages...`);

let passed = 0;
let failed = 0;
const failures = [];

for (const name of pages) {
  try {
    const html = fs.readFileSync(path.join(root, name), 'utf8');
    
    // Extract the script section
    const scriptMatch = html.match(/<script>([\s\S]*?)<\/script>/);
    if (!scriptMatch) {
      failures.push(`${name}: missing script tag`);
      failed++;
      continue;
    }
    
    // Execute the script in a sandbox to extract codeLines and steps
    const sandbox = {
      document: {
        querySelector: () => ({ append: () => {}, children: [], classList: { toggle: () => {} } }),
        querySelectorAll: () => [],
        createElement: () => ({ classList: {}, textContent: '', append: () => {} })
      },
      setInterval: () => {},
      clearInterval: () => {},
      Math: Math
    };
    
    try {
      vm.runInNewContext(scriptMatch[1], sandbox);
    } catch (vmError) {
      // Ignore execution errors, we just need the const declarations
    }
    
    // Try to extract codeLines and steps manually
    let codeLines = null;
    let steps = null;
    
    const script = scriptMatch[1];
    
    // Extract codeLines - find the complete array
    const codeLinesStart = script.indexOf('const codeLines=');
    if (codeLinesStart !== -1) {
      const afterCodeLines = script.substring(codeLinesStart);
      const arrayStart = afterCodeLines.indexOf('[');
      if (arrayStart !== -1) {
        // Find matching closing bracket
        let depth = 0;
        let i = arrayStart;
        for (; i < afterCodeLines.length; i++) {
          if (afterCodeLines[i] === '[') depth++;
          if (afterCodeLines[i] === ']') {
            depth--;
            if (depth === 0) break;
          }
        }
        if (depth === 0) {
          const codeLinesJson = afterCodeLines.substring(arrayStart, i + 1);
          try {
            codeLines = JSON.parse(codeLinesJson);
          } catch (e) {
            failures.push(`${name}: codeLines JSON parse error: ${e.message}`);
            failed++;
            continue;
          }
        }
      }
    }
    
    // Extract steps - find the entire array across multiple lines
    const stepsStart = script.indexOf('const steps=');
    if (stepsStart !== -1) {
      const afterSteps = script.substring(stepsStart);
      const stepsArrayStart = afterSteps.indexOf('[');
      if (stepsArrayStart !== -1) {
        // Find matching closing bracket
        let depth = 0;
        let i = stepsArrayStart;
        for (; i < afterSteps.length; i++) {
          if (afterSteps[i] === '[') depth++;
          if (afterSteps[i] === ']') {
            depth--;
            if (depth === 0) break;
          }
        }
        if (depth === 0) {
          const stepsJson = afterSteps.substring(stepsArrayStart, i + 1);
          try {
            steps = JSON.parse(stepsJson);
          } catch (e) {
            failures.push(`${name}: steps JSON parse error: ${e.message}`);
            failed++;
            continue;
          }
        }
      }
    }
    
    if (!codeLines) {
      failures.push(`${name}: missing codeLines`);
      failed++;
      continue;
    }
    
    if (!steps) {
      failures.push(`${name}: missing steps`);
      failed++;
      continue;
    }
    
    // Validate structure
    if (!Array.isArray(codeLines) || codeLines.length === 0) {
      failures.push(`${name}: codeLines is not a valid array`);
      failed++;
      continue;
    }
    
    if (!Array.isArray(steps) || steps.length === 0) {
      failures.push(`${name}: steps is not a valid array`);
      failed++;
      continue;
    }
    
    // Validate steps reference valid lines
    for (const step of steps) {
      if (!step.line && step.line !== 0) {
        throw new Error(`Step missing 'line' field: ${step.op}`);
      }
      if (step.line < 0 || step.line >= codeLines.length) {
        throw new Error(`Invalid line reference ${step.line} (code has ${codeLines.length} lines)`);
      }
      
      // Check for generic placeholder state
      if (step.state && /before Java line|apply line|State unchanged/.test(step.state)) {
        throw new Error(`Generic placeholder state found: "${step.state.substring(0, 50)}..."`);
      }
    }
    
    passed++;
  } catch (error) {
    failures.push(`${name}: ${error.message}`);
    failed++;
  }
}

console.log(`\nResults: ${passed} passed, ${failed} failed\n`);

if (failures.length) {
  console.error('Failures:');
  failures.forEach((failure) => console.error(`  - ${failure}`));
  process.exit(1);
}

console.log('All behavioral checks passed!');
