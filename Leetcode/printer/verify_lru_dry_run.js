#!/usr/bin/env node
/* Validates dry-run trace metadata before browser interaction tests. */
const fs = require('fs');
const childProcess = require('child_process');
const os = require('os');
const path = require('path');
const vm = require('vm');

const page = path.join(__dirname, 'leetcode-dry-run-animations', '01-lc-146-lru-cache-dry-run.html');
const html = fs.readFileSync(page, 'utf8');
const trace = html.match(/const steps=\[(.*?)\n\];\nsteps\.forEach/s)?.[1];
const code = html.match(/const codeLines=\[(.*?)\];\nconst steps=/s)?.[1];

if (!trace || !code) {
  throw new Error('Cannot locate codeLines or steps in the LRU dry-run page.');
}

const labels = [...trace.matchAll(/op:'([^']+)'/g)].map((match) => match[1]);
const lineReferences = [...trace.matchAll(/(?:line|lines):(?:\[([^\]]+)\]|(\d+))/g)]
  .flatMap((match) => (match[1] || match[2]).match(/\d+/g).map(Number));
const codeLineCount = (code.match(/^/gm) || []).length - 1;
const combinedMutations = labels.filter((label) => /\+|evict \+|map \+/.test(label));
const multiLineSteps = [...trace.matchAll(/lines:\[/g)].length;
const normalizesLabels = html.includes('step.op = `${index + 1}. ${step.op.replace(/^\\d+\\.\\s*/, \'\')}`;');

const failures = [];
if (labels.length === 0) failures.push('Trace has no steps.');
if (!normalizesLabels) failures.push('Visible step labels are not normalized from the trace position.');
lineReferences.forEach((line) => {
  if (line < 0 || line >= codeLineCount) failures.push(`Code reference ${line} is outside 0..${codeLineCount - 1}.`);
});
if (combinedMutations.length) failures.push(`Combined mutations are not allowed: ${combinedMutations.join('; ')}`);
if (multiLineSteps) failures.push(`${multiLineSteps} steps highlight multiple code lines; one visual step must execute one statement.`);

if (failures.length) {
  console.error('LRU dry-run contract FAILED:');
  failures.forEach((failure) => console.error(`- ${failure}`));
  process.exit(1);
}

console.log(`LRU dry-run contract passed: ${labels.length} one-statement steps, ${codeLineCount} code lines.`);

const codeBody = html.match(/const codeLines=\[(.*?)\];\nconst steps=/s)?.[1];
const stepsBody = html.match(/const steps=\[(.*?)\n\];\nsteps\.forEach/s)?.[1];
const sandbox = {};
vm.runInNewContext(`const codeLines = [${codeBody}]; const steps = [${stepsBody}]; this.codeLines = codeLines; this.steps = steps;`, sandbox);

const cacheClass = sandbox.codeLines.join('\n');
const lastBrace = cacheClass.lastIndexOf('\n}');
const instrumentedCache = `${cacheClass.slice(0, lastBrace)}
  String snapshot() {
    StringBuilder keys = new StringBuilder();
    for (Node node = head.next; node != tail; node = node.next) {
      if (keys.length() > 0) keys.append(',');
      keys.append(node.key);
    }
    List<Integer> mapKeys = new ArrayList<>(cache.keySet());
    Collections.sort(mapKeys);
    return "list=" + keys + ";map=" + mapKeys;
  }
${cacheClass.slice(lastBrace)}`;
const java = `import java.util.*;
${instrumentedCache}
class LruDryRunVerifier {
  static void snapshot(String label, LRUCache cache) { System.out.println(label + "|" + cache.snapshot()); }
  static String expectedList(LinkedHashMap<Integer, Integer> expected) {
    List<Integer> keys = new ArrayList<>(expected.keySet());
    Collections.reverse(keys); // LinkedHashMap is least -> most; LRU list is most -> least.
    return keys.toString().replace(" ", "").replace("[", "").replace("]", "");
  }
  static void assertMatches(LRUCache cache, LinkedHashMap<Integer, Integer> expected, String context) {
    List<Integer> mapKeys = new ArrayList<>(expected.keySet());
    Collections.sort(mapKeys);
    String wanted = "list=" + expectedList(expected) + ";map=" + mapKeys;
    if (!cache.snapshot().equals(wanted)) throw new AssertionError(context + " expected " + wanted + " but got " + cache.snapshot());
  }
  static void randomizedVerification() {
    for (int capacity = 1; capacity <= 5; capacity++) {
      for (int seed = 0; seed < 25; seed++) {
        final int maxEntries = capacity;
        LRUCache cache = new LRUCache(capacity);
        LinkedHashMap<Integer, Integer> expected = new LinkedHashMap<>(16, 0.75f, true) {
          protected boolean removeEldestEntry(Map.Entry<Integer, Integer> entry) { return size() > maxEntries; }
        };
        Random random = new Random(seed);
        for (int operation = 0; operation < 200; operation++) {
          int key = random.nextInt(8);
          if (random.nextBoolean()) {
            int value = random.nextInt(1000);
            cache.put(key, value);
            expected.put(key, value);
          } else {
            int actual = cache.get(key);
            int wanted = expected.getOrDefault(key, -1);
            if (actual != wanted) throw new AssertionError("capacity=" + capacity + ", seed=" + seed + ", op=" + operation + ": expected get(" + key + ")=" + wanted + " but got " + actual);
          }
          assertMatches(cache, expected, "capacity=" + capacity + ", seed=" + seed + ", op=" + operation);
        }
      }
    }
  }
  public static void main(String[] args) {
    LRUCache cache = new LRUCache(2);
    cache.put(1, 1); snapshot("put1", cache);
    cache.put(2, 2); snapshot("put2", cache);
    System.out.println("get1=" + cache.get(1)); snapshot("afterGet1", cache);
    cache.put(3, 3); snapshot("put3", cache);
    System.out.println("get2=" + cache.get(2)); snapshot("afterGet2", cache);
    cache.put(4, 4); snapshot("put4", cache);
    System.out.println("get1b=" + cache.get(1)); snapshot("afterGet1b", cache);
    System.out.println("get3=" + cache.get(3)); snapshot("afterGet3", cache);
    System.out.println("get4=" + cache.get(4)); snapshot("afterGet4", cache);
    randomizedVerification();
    System.out.println("randomized=pass");
  }
}`;
const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'lru-dry-run-'));
const javaFile = path.join(temp, 'LruDryRunVerifier.java');
fs.writeFileSync(javaFile, java);
try {
  childProcess.execFileSync('javac', [javaFile], { stdio: 'pipe' });
  const output = childProcess.execFileSync('java', ['-cp', temp, 'LruDryRunVerifier'], { encoding: 'utf8' });
  const expected = {
    put1: 'list=1;map=[1]', put2: 'list=2,1;map=[1, 2]', get1: '1', afterGet1: 'list=1,2;map=[1, 2]',
    put3: 'list=3,1;map=[1, 3]', get2: '-1', afterGet2: 'list=3,1;map=[1, 3]', put4: 'list=4,3;map=[3, 4]',
    get1b: '-1', afterGet1b: 'list=4,3;map=[3, 4]', get3: '3', afterGet3: 'list=3,4;map=[3, 4]', get4: '4', afterGet4: 'list=4,3;map=[3, 4]', randomized: 'pass',
  };
  const actual = Object.fromEntries(output.trim().split('\n').map((line) => line.split(/=(.*)|\|(.*)/).filter(Boolean)));
  Object.entries(expected).forEach(([key, value]) => {
    if (actual[key] !== value) failures.push(`Java ${key}: expected ${value}, got ${actual[key]}`);
  });
  const checkpoints = [
    ['put(1, 1): call addToHead', '1', ['1']], ['put(2, 2): call addToHead', '2,1', ['1', '2']],
    ['addToHead(1): head.next = node', '1,2', ['1', '2']], ['put(3, 3): call addToHead', '3,1', ['1', '3']],
    ['get(2): miss', '3,1', ['1', '3']], ['put(4, 4): call put path', '4,3', ['3', '4']],
    ['get(1): miss', '4,3', ['3', '4']], ['get(3): call get path', '3,4', ['3', '4']], ['get(4): call get path', '4,3', ['3', '4']],
  ];
  for (const [label, list, keys] of checkpoints) {
    const step = sandbox.steps.find((item) => item.op.includes(label));
    if (!step) { failures.push(`Visual checkpoint missing: ${label}`); continue; }
    const visibleKeys = step.map.map((entry) => entry.match(/^(\d+) ->/)?.[1]).sort();
    if (step.list.join(',') !== list) failures.push(`${label}: expected visual list ${list}, got ${step.list.join(',')}`);
    if (visibleKeys.join(',') !== keys.join(',')) failures.push(`${label}: expected visual map ${keys}, got ${visibleKeys}`);
  }
  if (failures.length) {
    console.error('LRU dry-run verification FAILED:');
    failures.forEach((failure) => console.error(`- ${failure}`));
    process.exit(1);
  }
  console.log('LRU behavioral verification passed: canonical outputs, 9 visual checkpoints, and 25,000 randomized operations match.');
} finally {
  fs.rmSync(temp, { recursive: true, force: true });
}