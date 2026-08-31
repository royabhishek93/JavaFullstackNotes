# Code-Level Dry-Run Visualizer Contract

Every LeetCode dry-run page in this folder must meet this contract before it is called complete.

## Content Requirements

1. Display the complete executable Java solution. Do not abbreviate methods or replace code with pseudocode.
2. Use one canonical example that reaches every meaningful branch: normal path, boundary path, and failure/miss/eviction path where relevant.
3. Create one visual step per meaningful executed statement: entry, condition, variable update, loop iteration, helper call, helper mutation, and return.
4. Every step must show the active input/index/node, exact active source line, algorithm-specific state (not generic placeholders), variable values, plain-English explanation, and invariant.
5. Never combine state mutations into one visual step.
6. Expand helper methods. Pointer assignments must each have their own state.
7. Provide Previous, Next, Reset, Pause controls, and auto-scroll the source code to the active line.

## Format Requirements

Each HTML file must use this exact JavaScript schema:

```javascript
const codeLines = [
  'line 1 of Java code',
  'line 2 of Java code',
  // ... complete method
];

const steps = [
  {
    op: 'Step label',
    line: N,  // 0-indexed line number in codeLines
    state: 'algorithm-specific state visualization',  // NOT "before Java line" or generic text
    // Additional fields vary by algorithm:
    // For arrays/lists: show actual values [1,2,3]
    // For graphs: show adjacency list {0:[1,2], 1:[3]}
    // For trees: show level order or structure
    // For stacks/queues: show contents [top,...,bottom]
    text: 'plain English: what just changed',
    why: 'why this preserves the algorithm invariant'
  },
  // ... one step per meaningful statement
];
```

## Test Requirements

Each problem must have a `verify_<problem-name>_dry_run.js` test script that:

1. Parses `codeLines` and `steps` from the HTML via regex
2. Builds executable Java source from `codeLines`
3. Compiles via `javac` and runs via `java` using Node.js `child_process`
4. Executes the canonical input and captures actual output
5. Validates each `step.state` matches the actual Java execution state at that line
6. Checks final output matches expected result
7. Exits with code 1 and clear error message on any mismatch

Example structure:
```javascript
const html = fs.readFileSync('XX-problem.html', 'utf8');
const codeLines = JSON.parse(html.match(/const codeLines=\[(.*?)\];/s)[1]);
const steps = JSON.parse(html.match(/const steps=\[(.*?)\];/s)[1]);

// Compile and run the actual Java code
const javaSource = buildTestHarness(codeLines, canonicalInput);
const output = compileAndRun(javaSource);

// Validate each step's state against actual execution
for (const step of steps) {
  const actualState = captureStateAtLine(step.line);
  if (step.state !== actualState) {
    console.error(`Step ${step.op}: expected ${step.state}, got ${actualState}`);
    process.exit(1);
  }
}
```

## Integration Requirements

Each new problem must be registered in `verify_all_dry_runs.js` collection gate.

## Completion Evidence

- Structural validator passes (controls, code display, step schema)
- Behavioral validator passes (Java execution matches visual steps)
- Browser interaction test passes (no JS errors, all steps navigable)
- Screenshot is presentation evidence only, not correctness proof