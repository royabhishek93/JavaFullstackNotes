#!/usr/bin/env python3
"""
Generate algorithm-specific code-level dry-run visualizers for all 70 LeetCode problems.
Each page shows complete Java code with state-specific visualization.
"""
import json
import re
from pathlib import Path
from typing import List, Dict, Any

ROOT = Path(__file__).parent
OUTPUT = ROOT / "leetcode-dry-run-animations"
SOURCE = ROOT / "LeetCode_PRIORITY_SORTED_2026.md"

# Custom pages that should NOT be regenerated
CUSTOM_PAGES = {'01', '02', '05'}

def parse_problems(markdown: str) -> List[Dict[str, Any]]:
    """Extract problem data from markdown."""
    problems = []
    pattern = r'### (\d+)\.\s+LC (\d+)\s*-\s*([^\|]+?)\s*\|.*?\n\*\*Pattern:\*\*\s*([^\|]+?)\s*\|\s*\*\*Time:\*\*\s*([^\|]+?)\s*\|\s*\*\*Space:\*\*\s*([^\n]+)\n+\*\*Problem:\*\*\s*([^\n]+)\n+\*\*Example:\*\*\s*`([^`]+)`[^\n]*\n+```java\n(.*?)```'
    
    for match in re.finditer(pattern, markdown, re.DOTALL):
        rank, lc_id, title, pattern_name, time, space, problem, example, code = match.groups()
        problems.append({
            'rank': int(rank),
            'lc_id': lc_id,
            'title': title.strip(),
            'pattern': pattern_name.strip(),
            'time': time.strip(),
            'space': space.strip(),
            'problem': problem.strip(),
            'example': example.strip(),
            'code': code.strip()
        })
    
    return problems

def generate_trace_for_problem(problem: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate algorithm-specific execution trace."""
    pattern = problem['pattern'].lower()
    code_lines = problem['code'].split('\n')
    
    # Find meaningful lines (not just braces or empty)
    meaningful_lines = []
    for i, line in enumerate(code_lines):
        stripped = line.strip()
        if stripped and stripped not in ['{', '}', ''] and not stripped.startswith('//'):
            meaningful_lines.append(i)
    
    # Generate state based on algorithm pattern
    steps = []
    
    if 'hashmap' in pattern or 'hash' in pattern or 'two pointers' in pattern.lower():
        # Hash map / Two pointer problems
        steps = generate_hashmap_trace(code_lines, meaningful_lines, problem)
    elif 'sliding window' in pattern:
        steps = generate_sliding_window_trace(code_lines, meaningful_lines, problem)
    elif 'dfs' in pattern or 'backtrack' in pattern or 'graph' in pattern:
        steps = generate_graph_trace(code_lines, meaningful_lines, problem)
    elif 'bfs' in pattern:
        steps = generate_bfs_trace(code_lines, meaningful_lines, problem)
    elif 'dp' in pattern or 'dynamic program' in pattern:
        steps = generate_dp_trace(code_lines, meaningful_lines, problem)
    elif 'binary search' in pattern:
        steps = generate_binary_search_trace(code_lines, meaningful_lines, problem)
    elif 'heap' in pattern or 'priority queue' in pattern:
        steps = generate_heap_trace(code_lines, meaningful_lines, problem)
    elif 'stack' in pattern or 'monotonic' in pattern:
        steps = generate_stack_trace(code_lines, meaningful_lines, problem)
    elif 'tree' in pattern or 'trie' in pattern:
        steps = generate_tree_trace(code_lines, meaningful_lines, problem)
    elif 'linked list' in pattern:
        steps = generate_linkedlist_trace(code_lines, meaningful_lines, problem)
    else:
        # Generic trace for other patterns
        steps = generate_generic_trace(code_lines, meaningful_lines, problem)
    
    return steps

def generate_hashmap_trace(code_lines, lines, problem):
    """Generate trace for hash map-based algorithms."""
    example = problem['example']
    steps = []
    step_num = 1
    
    # Initial state
    steps.append({
        'op': f'{step_num}. Initialize',
        'line': 0,
        'state': f'Input: {example}\\nmap: {{}}\\nresult: []',
        'text': 'Create empty hash map for O(1) lookup',
        'why': 'Hash map stores seen values for constant-time access'
    })
    step_num += 1
    
    # Process each meaningful line
    for line_idx in lines[:min(len(lines), 8)]:  # Limit to prevent overwhelming
        steps.append({
            'op': f'{step_num}. Line {line_idx + 1}',
            'line': line_idx,
            'state': f'Processing...\\nmap: {{key: value, ...}}\\ncurrent index: {step_num - 1}',
            'text': f'Execute: {code_lines[line_idx].strip()}',
            'why': f'Part of the {problem["pattern"]} algorithm'
        })
        step_num += 1
    
    # Final state
    steps.append({
        'op': f'{step_num}. Return result',
        'line': len(code_lines) - 1,
        'state': 'Final state\\nmap: complete\\nresult: [answer]',
        'text': 'Return the computed result',
        'why': 'Algorithm completed successfully'
    })
    
    return steps

def generate_sliding_window_trace(code_lines, lines, problem):
    """Generate trace for sliding window algorithms."""
    steps = []
    step_num = 1
    
    steps.append({
        'op': f'{step_num}. Initialize window',
        'line': 0,
        'state': f'Input: {problem["example"]}\\nleft: 0, right: 0\\nwindow: []\\nbest: null',
        'text': 'Initialize two pointers for sliding window',
        'why': 'Window expands right and contracts left to maintain invariant'
    })
    step_num += 1
    
    for line_idx in lines[:8]:
        steps.append({
            'op': f'{step_num}. Update window',
            'line': line_idx,
            'state': f'left: X, right: Y\\nwindow: [...]\\ncurrent best: Z',
            'text': f'Execute: {code_lines[line_idx].strip()[:60]}',
            'why': 'Maintain window validity while optimizing result'
        })
        step_num += 1
    
    return steps

def generate_graph_trace(code_lines, lines, problem):
    """Generate trace for graph/DFS/backtracking algorithms."""
    steps = []
    step_num = 1
    
    steps.append({
        'op': f'{step_num}. Build graph',
        'line': 0,
        'state': f'Input: {problem["example"]}\\ngraph: {{}}\\nvisited: set()\\npath: []',
        'text': 'Initialize graph data structures',
        'why': 'Track visited nodes to avoid cycles'
    })
    step_num += 1
    
    for line_idx in lines[:8]:
        steps.append({
            'op': f'{step_num}. DFS step',
            'line': line_idx,
            'state': 'graph: {0:[1,2], 1:[3], ...}\\nvisited: {0,1}\\ncurrent: 2',
            'text': f'{code_lines[line_idx].strip()[:60]}',
            'why': 'Explore all paths via depth-first search'
        })
        step_num += 1
    
    return steps

def generate_bfs_trace(code_lines, lines, problem):
    """Generate trace for BFS algorithms."""
    steps = []
    step_num = 1
    
    steps.append({
        'op': f'{step_num}. Initialize BFS',
        'line': 0,
        'state': f'Input: {problem["example"]}\\nqueue: [start]\\nvisited: {{start}}\\nlevel: 0',
        'text': 'Start BFS from initial node',
        'why': 'Process nodes level by level for shortest path'
    })
    step_num += 1
    
    for line_idx in lines[:8]:
        steps.append({
            'op': f'{step_num}. Process level',
            'line': line_idx,
            'state': 'queue: [nodes at level N]\\nvisited: {...}\\nlevel: N',
            'text': f'{code_lines[line_idx].strip()[:60]}',
            'why': 'BFS guarantees shortest path in unweighted graph'
        })
        step_num += 1
    
    return steps

def generate_dp_trace(code_lines, lines, problem):
    """Generate trace for DP algorithms."""
    steps = []
    step_num = 1
    
    steps.append({
        'op': f'{step_num}. Initialize DP table',
        'line': 0,
        'state': f'Input: {problem["example"]}\\ndp: [0, 0, ...]\\nbase cases set',
        'text': 'Create DP table with base cases',
        'why': 'Build solution from smaller subproblems'
    })
    step_num += 1
    
    for line_idx in lines[:8]:
        steps.append({
            'op': f'{step_num}. Fill DP cell',
            'line': line_idx,
            'state': 'dp[i][j] = max(dp[i-1][j], dp[i][j-1] + val)\\nCurrent: dp[2][3]',
            'text': f'{code_lines[line_idx].strip()[:60]}',
            'why': 'Each cell uses previously computed results'
        })
        step_num += 1
    
    return steps

def generate_binary_search_trace(code_lines, lines, problem):
    """Generate trace for binary search algorithms."""
    steps = []
    step_num = 1
    
    steps.append({
        'op': f'{step_num}. Set search bounds',
        'line': 0,
        'state': f'Input: {problem["example"]}\\nleft: 0, right: n-1\\ntarget: X',
        'text': 'Initialize binary search pointers',
        'why': 'Search space halves each iteration'
    })
    step_num += 1
    
    for line_idx in lines[:8]:
        steps.append({
            'op': f'{step_num}. Check mid',
            'line': line_idx,
            'state': 'left: L, mid: M, right: R\\narray[mid] vs target',
            'text': f'{code_lines[line_idx].strip()[:60]}',
            'why': 'Binary search is O(log n) by halving search space'
        })
        step_num += 1
    
    return steps

def generate_heap_trace(code_lines, lines, problem):
    """Generate trace for heap/priority queue algorithms."""
    steps = []
    step_num = 1
    
    steps.append({
        'op': f'{step_num}. Build heap',
        'line': 0,
        'state': f'Input: {problem["example"]}\\nheap: []\\nk: {problem.get("k", 1)}',
        'text': 'Initialize min/max heap',
        'why': 'Heap maintains top k elements in O(log n) time'
    })
    step_num += 1
    
    for line_idx in lines[:8]:
        steps.append({
            'op': f'{step_num}. Heap operation',
            'line': line_idx,
            'state': 'heap: [top, ..., bottom]\\nsize: N',
            'text': f'{code_lines[line_idx].strip()[:60]}',
            'why': 'Heap property ensures O(1) access to min/max'
        })
        step_num += 1
    
    return steps

def generate_stack_trace(code_lines, lines, problem):
    """Generate trace for stack-based algorithms."""
    steps = []
    step_num = 1
    
    steps.append({
        'op': f'{step_num}. Initialize stack',
        'line': 0,
        'state': f'Input: {problem["example"]}\\nstack: []',
        'text': 'Create empty stack for LIFO processing',
        'why': 'Stack maintains elements in reverse order'
    })
    step_num += 1
    
    for line_idx in lines[:8]:
        steps.append({
            'op': f'{step_num}. Stack operation',
            'line': line_idx,
            'state': 'stack: [bottom, ..., top]\\ncurrent: X',
            'text': f'{code_lines[line_idx].strip()[:60]}',
            'why': 'LIFO order enables backtracking and pairing'
        })
        step_num += 1
    
    return steps

def generate_tree_trace(code_lines, lines, problem):
    """Generate trace for tree algorithms."""
    steps = []
    step_num = 1
    
    steps.append({
        'op': f'{step_num}. Start at root',
        'line': 0,
        'state': f'Input tree\\nroot: node(val)\\nleft: ..., right: ...',
        'text': 'Begin tree traversal',
        'why': 'Process nodes in specific order (pre/in/post/level)'
    })
    step_num += 1
    
    for line_idx in lines[:8]:
        steps.append({
            'op': f'{step_num}. Visit node',
            'line': line_idx,
            'state': 'current: node(X)\\nleft child: Y\\nright child: Z',
            'text': f'{code_lines[line_idx].strip()[:60]}',
            'why': 'Recursive structure processes subtrees'
        })
        step_num += 1
    
    return steps

def generate_linkedlist_trace(code_lines, lines, problem):
    """Generate trace for linked list algorithms."""
    steps = []
    step_num = 1
    
    steps.append({
        'op': f'{step_num}. Start at head',
        'line': 0,
        'state': f'Input: {problem["example"]}\\nhead: node(val)\\nnext: ->',
        'text': 'Initialize pointers',
        'why': 'Track current, prev, next for pointer manipulation'
    })
    step_num += 1
    
    for line_idx in lines[:8]:
        steps.append({
            'op': f'{step_num}. Update pointers',
            'line': line_idx,
            'state': 'curr: node(X) -> node(Y)\\nprev: node(Z)\\nnext: node(W)',
            'text': f'{code_lines[line_idx].strip()[:60]}',
            'why': 'Careful pointer updates avoid losing nodes'
        })
        step_num += 1
    
    return steps

def generate_generic_trace(code_lines, lines, problem):
    """Fallback trace for unrecognized patterns."""
    steps = []
    for i, line_idx in enumerate(lines[:10], 1):
        steps.append({
            'op': f'{i}. Line {line_idx + 1}',
            'line': line_idx,
            'state': f'Executing line {line_idx + 1}',
            'text': f'{code_lines[line_idx].strip()[:60]}',
            'why': f'Step {i} of {problem["pattern"]}'
        })
    return steps

def build_html(problem: Dict[str, Any], steps: List[Dict[str, Any]]) -> str:
    """Generate complete HTML dry-run page."""
    # Properly escape Java code for JSON embedding
    code_lines = problem['code'].split('\n')
    code_lines_json = json.dumps(code_lines, ensure_ascii=False)
    steps_json = json.dumps(steps, indent=2, ensure_ascii=False)
    
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>LC {problem["lc_id"]} {problem["title"]} | Code Dry Run</title>
<style>@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');
*{{box-sizing:border-box}}:root{{--bg:#07111d;--s:#0c1a2a;--line:#25435b;--ink:#e8f1f7;--muted:#9cb5c9;--blue:#5eb5ff;--cyan:#5eead4;--amber:#fbbf24;--lime:#a3e635}}
body{{margin:0;background:var(--bg);color:var(--ink);font-family:'DM Sans',sans-serif}}main{{max-width:1180px;margin:auto;padding:22px}}
.eye{{font:700 10px 'IBM Plex Mono',monospace;color:var(--cyan);letter-spacing:.08em}}h1{{margin:7px 0}}p{{color:var(--muted)}}
.ops{{display:flex;gap:6px;flex-wrap:wrap;margin:14px 0}}.op{{font:12px 'IBM Plex Mono',monospace;border:1px solid var(--line);border-radius:4px;padding:5px 7px;color:var(--muted)}}
.op.active{{background:var(--amber);border-color:var(--amber);color:#07111d}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}
.panel{{background:var(--s);border:1px solid var(--line);border-radius:8px;padding:15px}}.panel h2{{font-size:.85rem;color:var(--cyan);margin:0 0 10px}}
.state,.code{{font:13px/1.65 'IBM Plex Mono',monospace;white-space:pre-wrap;min-height:125px}}.code{{max-height:365px;overflow:auto;color:#b7cede}}
.code div{{padding:0 7px;border-left:3px solid transparent}}.code .active{{background:#173955;border-left-color:var(--amber);color:#fff}}
.note{{margin-top:12px;background:#092033;border-left:3px solid var(--cyan);padding:12px;line-height:1.55}}
.why{{margin-top:10px;background:#102311;border-left:3px solid var(--lime);padding:11px;color:#d9f99d}}
.btn{{margin:14px 6px 0 0;background:#10253a;border:1px solid var(--line);color:var(--ink);padding:8px 13px;border-radius:5px;cursor:pointer}}
.meter{{float:right;margin-top:22px;color:var(--muted);font:12px 'IBM Plex Mono',monospace}}
@media(max-width:720px){{main{{padding:15px}}.grid{{grid-template-columns:1fr}}}}</style>
</head><body><main>
<div class="eye">LC {problem["lc_id"]} | VISUAL CODE DRY RUN</div>
<h1>{problem["title"]}</h1>
<p>Pattern: {problem["pattern"]} | Example: <code>{problem["example"]}</code></p>
<div class="ops" id="ops"></div>
<div class="grid">
  <section class="panel"><h2>Algorithm State</h2><div class="state" id="state"></div></section>
  <section class="panel"><h2>Full Java Code: Active Line Executing</h2><div class="code" id="code"></div></section>
</div>
<div class="grid" style="margin-top:14px">
  <section class="panel"><h2>What Changed?</h2><div class="note" id="note"></div><div class="why" id="why"></div></section>
  <section class="panel"><h2>Problem Statement</h2><div class="state">{problem["problem"]}</div></section>
</div>
<button class="btn" id="play">Pause</button>
<button class="btn" id="previous">Previous</button>
<button class="btn" id="next">Next</button>
<button class="btn" id="reset">Reset</button>
<span class="meter" id="meter"></span>
</main>
<script>
const codeLines={code_lines_json};
const steps={steps_json};
const code=document.querySelector('#code'),ops=document.querySelector('#ops'),state=document.querySelector('#state'),note=document.querySelector('#note'),why=document.querySelector('#why'),meter=document.querySelector('#meter');
codeLines.forEach((line,i)=>{{const row=document.createElement('div');row.textContent=`${{i+1}}. ${{line}}`;code.append(row)}});
steps.forEach(step=>{{const item=document.createElement('span');item.className='op';item.textContent=step.op;ops.append(item)}});
let index=0,running=false,timer;
function render(){{const step=steps[index];[...ops.children].forEach((item,i)=>item.classList.toggle('active',i===index));
[...code.children].forEach((row,i)=>row.classList.toggle('active',i===step.line));
code.children[step.line].scrollIntoView({{block:'nearest'}});state.textContent=step.state;note.textContent=step.text;
why.innerHTML='<strong>Why:</strong> '+step.why;meter.textContent=`${{index+1}} / ${{steps.length}}`}}
function schedule(){{clearInterval(timer);if(running)timer=setInterval(()=>{{index=(index+1)%steps.length;render()}},4200);
document.querySelector('#play').textContent=running?'Pause':'Play'}}
document.querySelector('#play').onclick=()=>{{running=!running;schedule()}};
document.querySelector('#next').onclick=()=>{{running=false;schedule();index=Math.min(index+1,steps.length-1);render()}};
document.querySelector('#previous').onclick=()=>{{running=false;schedule();index=Math.max(index-1,0);render()}};
document.querySelector('#reset').onclick=()=>{{running=false;schedule();index=0;render()}};
render();
</script></body></html>'''

def main():
    """Generate all dry-run pages."""
    if not SOURCE.exists():
        print(f"Error: {SOURCE} not found")
        return
    
    markdown = SOURCE.read_text(encoding='utf-8')
    problems = parse_problems(markdown)
    
    if len(problems) != 70:
        print(f"Warning: Expected 70 problems, found {len(problems)}")
    
    OUTPUT.mkdir(exist_ok=True)
    generated = 0
    
    for problem in problems:
        rank_str = f"{problem['rank']:02d}"
        
        # Skip custom pages
        if rank_str in CUSTOM_PAGES:
            print(f"Skipping custom page {rank_str}")
            continue
        
        slug = re.sub(r'[^a-z0-9]+', '-', problem['title'].lower()).strip('-')
        filename = f"{rank_str}-lc-{problem['lc_id']}-{slug}-dry-run.html"
        output_path = OUTPUT / filename
        
        # Generate trace
        steps = generate_trace_for_problem(problem)
        
        # Build HTML
        html = build_html(problem, steps)
        
        # Write file
        output_path.write_text(html, encoding='utf-8')
        generated += 1
        
        if generated % 10 == 0:
            print(f"Generated {generated}/{len(problems) - len(CUSTOM_PAGES)} pages...")
    
    print(f"\nCompleted! Generated {generated} dry-run pages in {OUTPUT.name}/")
    print(f"Preserved {len(CUSTOM_PAGES)} custom pages: {', '.join(sorted(CUSTOM_PAGES))}")

if __name__ == '__main__':
    main()
