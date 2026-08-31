#!/usr/bin/env python3
"""Generate one beginner-friendly interview deck for each LeetCode entry."""
from html import escape
from pathlib import Path
import re

ROOT = Path(__file__).parent
SOURCE = ROOT / "LeetCode_PRIORITY_SORTED_2026.md"
OUTPUT = ROOT / "leetcode-video-decks"

CSS = '''<style>@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');*{box-sizing:border-box}:root{--bg:#07111d;--s:#0c1a2a;--s2:#10253a;--line:#25435b;--ink:#e8f1f7;--muted:#9cb5c9;--blue:#5eb5ff;--cyan:#5eead4;--lime:#a3e635;--red:#fb7185}body{margin:0;background:var(--bg);color:var(--ink);font-family:'DM Sans',sans-serif;height:100vh;overflow:hidden}#p{height:100vh;display:flex;flex-direction:column}header,footer{background:var(--s);display:flex;align-items:center;padding:9px 24px;border-color:var(--line);border-style:solid}header{justify-content:space-between;border-width:0 0 1px}footer{justify-content:space-between;border-width:1px 0 0}.name{font-size:12px;color:var(--blue);font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:75vw}.counter{font:11px 'IBM Plex Mono',monospace;color:var(--muted)}#progress{height:3px;background:#102238}#progress i{display:block;height:100%;background:linear-gradient(90deg,var(--blue),var(--cyan));transition:width .25s}.stage{flex:1;min-height:0}.slide{display:none;height:100%;overflow:auto;padding:18px max(24px,calc((100vw - 1280px)/2));animation:in .25s ease}.slide.active{display:block}@keyframes in{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}h1{font-size:clamp(2rem,4vw,3.7rem);line-height:1.08;margin:0}h2{font-size:1.34rem;margin:0 0 12px;color:var(--blue)}.eye{font:700 10px 'IBM Plex Mono',monospace;color:var(--cyan);letter-spacing:.08em;text-transform:uppercase;margin-bottom:8px}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.card{background:var(--s);border:1px solid var(--line);border-radius:7px;padding:13px 15px}.card h3{font-size:.9rem;color:var(--cyan);margin:0 0 7px}p,li{font-size:.88rem;line-height:1.55;color:var(--muted);margin:0}ul{padding-left:18px;margin:0}li{margin:4px 0}strong{color:var(--ink)}.quote{border-left:3px solid var(--cyan);padding:13px 16px;background:#092033;color:#d9e9f5;font-size:.95rem;line-height:1.62;border-radius:0 7px 7px 0}.diagram,.code{background:#04101c;border:1px solid var(--line);border-radius:7px;padding:12px;font:12px/1.58 'IBM Plex Mono',monospace;white-space:pre;overflow:auto;color:#bad3e7}.code{white-space:pre-wrap}.why{border-left:3px solid var(--lime);background:#102311;color:#d9f99d;padding:11px 14px;border-radius:0 7px 7px 0;font-size:.87rem;line-height:1.55;margin-top:10px}.trap{border-left:3px solid var(--red);background:#280f1b;color:#fecdd3;padding:11px 14px;border-radius:0 7px 7px 0;font-size:.87rem;line-height:1.55;margin-top:10px}.tag{display:inline-block;border:1px solid var(--line);border-radius:99px;padding:3px 8px;color:var(--muted);font-size:10px;margin:2px}.title{height:100%;display:flex;align-items:center;justify-content:center;text-align:center;flex-direction:column;padding:24px}.title p{max-width:760px;margin-top:14px}.btn{background:var(--s2);border:1px solid var(--line);color:var(--ink);font:600 12px 'DM Sans',sans-serif;padding:6px 15px;border-radius:5px;cursor:pointer}.dots{display:flex;gap:4px;max-width:55vw;flex-wrap:wrap;justify-content:center}.dot{width:6px;height:6px;border-radius:50%;border:0;background:var(--line);padding:0;cursor:pointer}.dot.active{background:var(--blue);transform:scale(1.35)}@media(max-width:720px){.grid{grid-template-columns:1fr}.slide{padding:15px 16px}.diagram{font-size:10px}.dots{display:none}.name{max-width:60vw}}</style>'''

def slide(index, label, heading, body):
    return f'<section class="slide" id="s{index}" data-title="{escape(label)}"><div class="eye">{escape(label)}</div><h2>{escape(heading)}</h2>{body}</section>'

def explain(pattern, title=""):
    value = pattern.lower()
    name = title.lower()
    if 'maximum path sum' in name:
        return ('a tree path that may use both children once but can return only one branch upward', 'At each node, ignore negative gains; update the global answer with left gain + node + right gain, then return node + the better one-child gain.', 'Postorder gives child gains first, so every node can evaluate the best path passing through it.')
    if 'lowest common ancestor' in name:
        return ('the first tree node whose subtrees contain the two targets', 'Return the target when found; if left and right both return non-null, the current node is the LCA.', 'Postorder lets each subtree report whether it found either target.')
    if 'reverse nodes in k-group' in name:
        return ('linked-list segments that must be reversed only when a full group exists', 'Find the kth node first; reverse exactly that group, reconnect it, then continue from the next group.', 'Checking group size before rewiring prevents a partial final group from being reversed.')
    if 'reverse linked list' in name:
        return ('a list whose arrows need to point backward', 'Save `next`, point `current.next` to `previous`, then advance both pointers.', 'The saved next pointer keeps the remaining list reachable while each link is reversed once.')
    if 'jump game ii' in name:
        return ('the farthest range reachable with the current number of jumps', 'Scan the current range, track its farthest reach, and increment jumps only when you finish that range.', 'This is BFS by ranges without building an explicit queue.')
    if 'jump game' in name:
        return ('the farthest index reachable so far', 'For every index within reach, update farthest; fail only when the index itself is beyond farthest.', 'Keeping one farthest value proves whether any future position remains reachable.')
    if 'maximum product' in name:
        return ('a product where a negative number can swap the best and worst outcome', 'Track both current maximum and minimum; update both using the old values before replacing them.', 'A negative multiplied by the most negative product can become the new maximum.')
    if 'buy and sell stock' in name:
        return ('the cheapest earlier buying price while scanning future selling prices', 'Update the minimum price first, then compare today’s profit against the best profit.', 'Every sale only needs the cheapest purchase before it, not every earlier purchase.')
    if 'rotate array' in name:
        return ('a rotation that can be expressed as three reversals', 'Reverse all, reverse the first k items, then reverse the remaining items.', 'Three in-place reversals move the suffix to the front without extra array storage.')
    if 'count subarrays with k odd' in name:
        return ('an exactly-k constraint that is easier to count as two at-most constraints', 'Compute `atMost(k) - atMost(k - 1)` using a window that shrinks when odd count exceeds the limit.', 'Every subarray with exactly k odds is included in the first count but excluded from the second.')
    if 'validate binary search tree' in name:
        return ('a node constrained by every ancestor, not only its direct parent', 'Pass a lower and upper bound down the tree and require each value to be strictly inside both bounds.', 'Bounds carry the full BST rule to every descendant.')
    if 'construct tree from preorder' in name:
        return ('preorder choosing the root while inorder divides left and right subtrees', 'Read the next preorder value as root; use its inorder index to recurse on the exact left and right ranges.', 'The two traversals together uniquely locate each subtree when values are unique.')
    if 'lru cache' in value or 'doubly linked' in value:
        return ('constant-time key lookup plus constant-time recency updates', 'Use a HashMap to find a node and a doubly linked list to move it to most-recent or remove least-recent.', 'The HashMap avoids a list scan; the doubly linked list avoids shifting elements.')
    if 'topological' in value:
        return ('a dependency graph where work starts only after prerequisites', 'Enqueue every zero-indegree node; when it completes, decrement its outgoing neighbors.', 'If processed nodes are fewer than all nodes, a cycle blocked the remaining work.')
    if 'flood fill' in value:
        return ('a connected component in a grid', 'When an unvisited land cell is found, mark it visited and explore its four neighbors.', 'One DFS/BFS consumes exactly one island, so each cell is visited at most once.')
    if 'floyd' in value:
        return ('an array or linked list that can be treated as a cycle', 'Move one pointer one step and another two steps; a meeting proves a cycle.', 'The two speeds expose a cycle without a HashSet.')
    if 'monotonic deque' in value:
        return ('the best element in every fixed window', 'Remove expired indices from the front and smaller values from the back before adding the current index.', 'The deque keeps candidates in decreasing order, so its front is the window maximum.')
    if 'monotonic stack' in value:
        return ('unresolved elements waiting for a greater or smaller boundary', 'Maintain a monotonic stack; pop an index only when the current value resolves its answer.', 'Every index enters and leaves once, avoiding repeated scans.')
    if 'prefix/suffix' in value:
        return ('a result that depends on everything before and after each position', 'Store prefix information left-to-right, then multiply by a rolling suffix right-to-left.', 'Two passes reuse partial products without division or nested loops.')
    if 'prefix sum' in value:
        return ('a range sum expressed as a difference of two prefixes', 'Track the current prefix and look up how often the needed earlier prefix occurred.', 'A HashMap turns every possible start index into one constant-time lookup.')
    if 'merge overlapping' in value or 'three-phase insertion' in value:
        return ('intervals whose overlap becomes local after sorting', 'Sort by start time and compare the next interval only with the current merged interval.', 'All intervals before the current one are already finalized, so one scan is enough.')
    if 'sliding window' in value:
        return ('a moving left/right boundary', 'Expand `right`; shrink `left` only while the window violates its rule.', 'Each element enters and leaves the window at most once.')
    if 'two pointer' in value:
        return ('two indexes moving toward each other or forward together', 'Use what is already known about the ends to decide which pointer can safely move.', 'You eliminate impossible answers without checking every pair.')
    if 'binary search' in value:
        return ('a sorted half or a monotonic answer space', 'At `mid`, identify the half that still can contain the answer and discard the other half.', 'Half the candidates disappear on every iteration.')
    if 'backtracking' in value:
        return ('a graph, tree, grid, or choice tree', 'Choose one path, mark its state, recurse, then undo the state when returning.', 'The recursive call represents one smaller version of the same problem.')
    if 'bfs' in value or 'topological' in value:
        return ('layers, prerequisites, or shortest unweighted steps', 'Put starting nodes in a queue; process one layer or zero-indegree node at a time.', 'The queue captures the next valid work in the correct order.')
    if 'heap' in value or 'priority' in value or 'bucket' in value:
        return ('repeated access to the best current candidate', 'Keep only the candidates that matter; remove the least useful candidate when over capacity.', 'A heap avoids repeatedly sorting all input.')
    if 'stack' in value:
        return ('a next greater/smaller or nested-structure relationship', 'Store unresolved items. Pop only when the current value resolves their question.', 'Every item is pushed and popped once.')
    if 'linked list' in value or 'cycle' in value:
        return ('pointer rewiring or pointer movement', 'Keep references before changing links; move pointers in a defined order.', 'The nodes are reused without needing another data structure.')
    if 'dp' in value or 'knapsack' in value or 'kadane' in value or 'fibonacci' in value:
        return ('overlapping smaller answers', 'Define what one DP state means, initialize the smallest state, then build forward.', 'Each state is solved once instead of recomputing recursive branches.')
    if 'hash' in value or 'anagram' in value:
        return ('fast lookup of a previously seen value or normalized key', 'Store the information needed to answer the next element in constant average time.', 'A HashMap/HashSet replaces an inner scan.')
    if 'sort' in value or 'interval' in value:
        return ('an order that makes neighbors meaningful', 'Sort first, then make one linear pass using the relationship between adjacent items.', 'Sorting turns a global comparison problem into a local decision.')
    return ('the invariant that must remain true after each step', 'Write down what your variables mean and update only enough state to preserve it.', 'A clear invariant turns a brute-force search into one controlled pass.')

def parse_problems(source):
    matcher = re.compile(r'^### (\d+)\. LC (\d+) - (.+?) \|.*?\n\*\*Pattern:\*\* (.+?) \| \*\*Time:\*\* (.+?) \| \*\*Space:\*\* (.+?)\n\n\*\*Problem:\*\* (.+?)\n\n\*\*Example:\*\* (.+?)\n\n```java\n(.*?)```', re.M | re.S)
    return [match.groups() for match in matcher.finditer(source)]

def parse_followups(source):
    matcher = re.compile(r'\*\*LC (\d+) - .*?\*\*\n- Q: (.*?)\n- A: (.*?)(?=\n\n|\n###|\Z)', re.S)
    return {lc_id: (question.strip(), answer.strip()) for lc_id, question, answer in matcher.findall(source)}

def trace(example, pattern, move):
    return f'''<div class="diagram">Given example
-------------
{escape(example)}

1. Start with the smallest valid state for {escape(pattern)}.
2. Read the next input item and update only that state.
3. Apply the invariant: {escape(move)}
4. Record the answer only when the invariant permits it.</div>'''

def build(rank, lc_id, title, pattern, time, space, problem, example, code, followup=None):
    title = title.strip()
    idea, move, reason = explain(pattern, title)
    safe = escape(title)
    code = escape(code.strip())
    slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
    slides = [f'<section class="slide active" id="s1" data-title="Introduction"><div class="title"><div class="eye">LeetCode {lc_id} | Beginner interview walkthrough</div><h1>{safe}</h1><p>Learn how to recognize the pattern, state the invariant, derive the best approach, and explain the code confidently.</p><div><span class="tag">{escape(pattern)}</span><span class="tag">Time {escape(time)}</span><span class="tag">Space {escape(space)}</span></div></div></section>']
    slides += [
        slide(2, 'Problem', 'Read the question like an interviewer', f'<div class="quote">“The task is: <strong>{escape(problem)}</strong> Before coding, I will confirm input constraints, whether I may change input, and what to return on an empty or impossible case.”</div><div class="card" style="margin-top:12px"><h3>Given example</h3><p>{escape(example)}</p></div><div class="why"><strong>Why begin here:</strong> the data shape and required output decide the pattern. Do not start coding from a memorized solution name.</div>'),
        slide(3, 'Pattern Recognition', f'Recognize: {pattern}', f'''<div class="diagram">Question clue
     |
     v
{escape(idea)}
     |
     v
Best tool: {escape(pattern)}
     |
     v
Invariant: {escape(move)}</div><div class="why"><strong>Why this approach:</strong> {escape(reason)} This is the interview signal: explain why the pattern removes unnecessary work.</div>'''),
        slide(4, 'Brute Force', 'Start with the simplest correct idea', f'<div class="grid"><div class="card"><h3>Baseline</h3><p>Without <strong>{escape(pattern)}</strong>, we would repeatedly search, compare, or recompute candidates as new input arrives.</p></div><div class="card"><h3>What we reuse</h3><p>The optimized solution retains the information described by this insight: <strong>{escape(idea)}</strong>.</p></div></div><div class="quote" style="margin-top:12px">“I mention the baseline to show the improvement. The important step is identifying exactly what repeated work I can preserve as state.”</div>'),
        slide(5, 'Dry Run', 'Dry run using the given example', f'{trace(example, pattern, move)}<div class="why"><strong>How to approach it:</strong> do not jump from example to code. Say what changes after each input item. The invariant tells you which state to keep and when an answer is valid.</div>'),
        slide(6, 'Algorithm', 'Best interview approach: step by step', f'<ol><li>State the pattern: <strong>{escape(pattern)}</strong>.</li><li>Choose the smallest state needed to remember previous work.</li><li>Process the input once, preserving this rule: <strong>{escape(move)}</strong>.</li><li>Update the answer when the rule says a candidate is valid.</li><li>Return the required value and cover empty/boundary input.</li></ol><div class="why"><strong>Complexity:</strong> time is <strong>{escape(time)}</strong> and space is <strong>{escape(space)}</strong>. Explain where each cost comes from rather than only quoting it.</div>'),
        slide(7, 'Code', 'Java implementation to explain line by line', f'<div class="code">{code}</div><div class="why"><strong>What to say while coding:</strong> “I am keeping the state minimal. Each update has one purpose: maintain the invariant or record a better answer.”</div>'),
        slide(8, 'Pitfalls', 'Beginner mistakes and boundary cases', f'<div class="grid"><div class="card"><h3>Check before coding</h3><ul><li>Empty input or one element.</li><li>Duplicate values or equal boundaries.</li><li>Overflow for sums/products; use `long` when constraints require it.</li><li>Whether input mutation is allowed.</li></ul></div><div class="card"><h3>Pattern-specific trap</h3><p>{escape(move)} Skipping this rule usually creates an off-by-one error, duplicate result, or missed candidate.</p></div></div><div class="trap"><strong>Interview trap:</strong> do not claim $O(1)$ space if recursion, a returned result, or a HashMap grows with input. State the auxiliary space assumption clearly.</div>'),
        slide(9, 'Follow-ups', 'Cross question: extend the same idea', f'<div class="quote"><strong>Interviewer:</strong> “{escape(followup[0] if followup else "Can you return the actual path or indices, not only the value?")}”<br><br><strong>You say:</strong> “{escape(followup[1] if followup else "I would store the extra metadata needed to reconstruct the answer while preserving the same core invariant.")}”</div><div class="why"><strong>Why this is a useful follow-up:</strong> it tests whether you understand the state behind <strong>{escape(pattern)}</strong>, rather than memorizing one method.</div>'),
        slide(10, 'Interview Answer', 'How to explain this solution live', f'<div class="quote">“For <strong>LC {lc_id}: {safe}</strong>, I recognize <strong>{escape(idea)}</strong>. A brute-force solution repeats comparisons. I use <strong>{escape(pattern)}</strong> and maintain this invariant: <strong>{escape(move)}</strong>. That lets me process the input in <strong>{escape(time)}</strong> time with <strong>{escape(space)}</strong> space. I would test the provided example, empty input, duplicates, and the boundary where the invariant changes.”</div><div class="why"><strong>Practice goal:</strong> first explain the invariant without code. Once that is clear, the implementation becomes a translation of your reasoning.</div>'),
    ]
    js = '''<script>const s=[...document.querySelectorAll('.slide')],d=document.querySelector('.dots'),c=document.querySelector('.counter'),b=document.querySelector('#progress i');let n=Math.max(0,+new URLSearchParams(location.search).get('slide')-1||0);s.forEach((_,i)=>{const x=document.createElement('button');x.className='dot';x.onclick=()=>show(i);d.append(x)});function show(i){n=Math.max(0,Math.min(i,s.length-1));s.forEach((x,j)=>x.classList.toggle('active',j===n));[...d.children].forEach((x,j)=>x.classList.toggle('active',j===n));c.textContent=`${n+1} / ${s.length}`;b.style.width=`${(n+1)*100/s.length}%`;history.replaceState(null,'','?slide='+(n+1))}document.querySelector('#prev').onclick=()=>show(n-1);document.querySelector('#next').onclick=()=>show(n+1);document.addEventListener('keydown',e=>{if(e.key==='ArrowRight'||e.key===' ')show(n+1);if(e.key==='ArrowLeft')show(n-1)});show(n)</script>'''
    html = f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>LC {lc_id} {safe} | Beginner Guide</title>{CSS}</head><body><main id="p"><header><span class="name">LC {lc_id} | {safe}</span><span class="counter"></span></header><div id="progress"><i></i></div><div class="stage">{"".join(slides)}</div><footer><button class="btn" id="prev">Previous</button><div class="dots"></div><button class="btn" id="next">Next</button></footer></main>{js}</body></html>'
    return f'{int(rank):02d}-lc-{lc_id}-{slug}-video.html', html

def main():
    source = SOURCE.read_text(encoding='utf-8')
    problems = parse_problems(source)
    followups = parse_followups(source)
    if len(problems) != 70:
        raise ValueError(f'Expected 70 problems, found {len(problems)}')
    OUTPUT.mkdir(exist_ok=True)
    for problem in problems:
        filename, html = build(*problem, followup=followups.get(problem[1]))
        (OUTPUT / filename).write_text(html, encoding='utf-8')
    print(f'Generated {len(problems)} LeetCode video decks in {OUTPUT.name}.')

if __name__ == '__main__':
    main()