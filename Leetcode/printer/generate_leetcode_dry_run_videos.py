#!/usr/bin/env python3
"""Create autoplay, pauseable algorithm dry-run pages for every priority problem."""
from html import escape
from pathlib import Path
import importlib.util
import json
import re

if __name__ == "__main__":
    from generate_code_level_dry_runs import main as generate_code_level_pages
    generate_code_level_pages()
    raise SystemExit

ROOT = Path(__file__).parent
OUTPUT = ROOT / "leetcode-dry-run-animations"
spec = importlib.util.spec_from_file_location("deck_generator", ROOT / "generate_leetcode_video_decks.py")
deck_generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deck_generator)

CSS = """<style>@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');*{box-sizing:border-box}:root{--bg:#07111d;--s:#0c1a2a;--s2:#10253a;--line:#25435b;--ink:#e8f1f7;--muted:#9cb5c9;--blue:#5eb5ff;--cyan:#5eead4;--lime:#a3e635;--amber:#fbbf24}body{margin:0;min-height:100vh;background:var(--bg);color:var(--ink);font-family:'DM Sans',sans-serif}main{max-width:1100px;margin:0 auto;padding:24px}.eyebrow{font:700 10px 'IBM Plex Mono',monospace;letter-spacing:.08em;color:var(--cyan)}h1{font-size:clamp(1.9rem,4vw,3.3rem);margin:7px 0}p{color:var(--muted);line-height:1.6}.layout{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:18px}.panel{background:var(--s);border:1px solid var(--line);border-radius:8px;padding:16px}.panel h2{font-size:.9rem;margin:0 0 10px;color:var(--cyan)}.input{font:13px/1.65 'IBM Plex Mono',monospace;color:#c7dced;white-space:pre-wrap;min-height:110px}.tokens{display:flex;flex-wrap:wrap;gap:5px;margin-top:10px;min-height:44px}.token{font:12px 'IBM Plex Mono',monospace;color:#9fb9ce;background:#081525;border:1px solid var(--line);border-radius:4px;padding:4px 6px;transition:all .28s}.token.active{color:#07111d;background:var(--amber);border-color:var(--amber);transform:translateY(-2px)}.state{font:14px/1.6 'IBM Plex Mono',monospace;min-height:190px;white-space:pre-wrap}.step{font:700 12px 'IBM Plex Mono',monospace;color:var(--blue);margin-bottom:8px}.caption{font-size:1.1rem;line-height:1.55;min-height:96px}.why{border-left:3px solid var(--lime);background:#102311;color:#d9f99d;padding:12px 14px;border-radius:0 7px 7px 0;line-height:1.55;margin-top:14px}.controls{display:flex;align-items:center;gap:9px;margin-top:15px}.btn{background:var(--s2);border:1px solid var(--line);color:var(--ink);font:600 13px 'DM Sans',sans-serif;padding:8px 13px;border-radius:5px;cursor:pointer}.btn.primary{background:#123b5c;border-color:var(--blue)}.progress{height:6px;background:#102238;border-radius:4px;overflow:hidden;flex:1}.progress i{display:block;height:100%;background:linear-gradient(90deg,var(--blue),var(--cyan));transition:width .35s}.chips{display:flex;flex-wrap:wrap;gap:6px}.chip{border:1px solid var(--line);border-radius:99px;padding:3px 8px;color:var(--muted);font-size:11px}.steps{margin-top:14px;display:grid;grid-template-columns:repeat(6,1fr);gap:5px}.dot{height:5px;background:var(--line);border-radius:4px}.dot.active{background:var(--amber)}a{color:var(--cyan)}@media(max-width:700px){main{padding:16px}.layout{grid-template-columns:1fr}.steps{grid-template-columns:repeat(3,1fr)}.controls{flex-wrap:wrap}}</style>"""

SCRIPT = """<script>
const trace = JSON.parse(document.querySelector('#trace-data').textContent);
const tokens = JSON.parse(document.querySelector('#token-data').textContent);
let step = 0, running = true, timer;
const label = document.querySelector('#label'), caption = document.querySelector('#caption');
const state = document.querySelector('#state'), bar = document.querySelector('#bar');
const play = document.querySelector('#play'), dots = document.querySelector('#steps');
const tokenLane = document.querySelector('#tokens');
trace.forEach(() => { const dot = document.createElement('i'); dot.className = 'dot'; dots.append(dot); });
tokens.forEach(token => { const item = document.createElement('span'); item.className = 'token'; item.textContent = token; tokenLane.append(item); });
function render() {
  const current = trace[step];
  label.textContent = `STEP ${step + 1} / ${trace.length} - ${current[0]}`;
  caption.textContent = current[1];
  state.textContent = `Pattern: ${document.body.dataset.pattern}\n\nInvariant:\n${trace[Math.min(step, 4)][1]}\n\nCurrent teaching focus:\n${current[0]}`;
  bar.style.width = `${(step + 1) * 100 / trace.length}%`;
  [...dots.children].forEach((dot, index) => dot.classList.toggle('active', index <= step));
    const activeToken = Math.min(tokens.length - 1, Math.floor(step * tokens.length / trace.length));
    [...tokenLane.children].forEach((token, index) => token.classList.toggle('active', index <= activeToken));
}
function advance() { step = (step + 1) % trace.length; render(); }
function schedule() { clearInterval(timer); if (running) timer = setInterval(advance, 4200); play.textContent = running ? 'Pause' : 'Play'; }
play.onclick = () => { running = !running; schedule(); };
document.querySelector('#next').onclick = () => { running = false; schedule(); advance(); };
document.querySelector('#previous').onclick = () => { running = false; schedule(); step = (step + trace.length - 1) % trace.length; render(); };
document.querySelector('#reset').onclick = () => { running = false; schedule(); step = 0; render(); };
document.addEventListener('keydown', event => { if (event.key === ' ') { event.preventDefault(); play.click(); } if (event.key === 'ArrowRight') document.querySelector('#next').click(); if (event.key === 'ArrowLeft') document.querySelector('#previous').click(); });
render(); schedule();
</script>"""

def steps_for(title, pattern, example, time, space):
    idea, invariant, reason = deck_generator.explain(pattern, title)
    return [
        ("Load the example", f"We start with the exact input: {example}"),
        ("Recognize the clue", f"This is not a random scan. The clue is {idea}."),
        ("Create the state", f"The state begins empty and will keep only what we need for {pattern}."),
        ("Process one step", invariant),
        ("Preserve the invariant", reason),
        ("Finish", f"The best approach is {time} time and {space} space. Replay the trace and explain each state change aloud."),
    ]

def tokens_for(example):
    tokens = re.findall(r"[A-Za-z0-9]+|->|→|\[|\]|\{|\}|\(|\)|,|=", example)
    return tokens[:24] or ["input"]

def build(problem):
    rank, lc_id, title, pattern, time, space, statement, example, _code = problem
    title = title.strip()
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    trace_json = json.dumps(steps_for(title, pattern, example, time, space)).replace("</", "<\\/")
    token_json = json.dumps(tokens_for(example)).replace("</", "<\\/")
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>LC {lc_id} {escape(title)} | Dry Run</title>{CSS}</head><body data-pattern="{escape(pattern)}"><main><div class="eyebrow">LC {lc_id} | AUTOPLAY DRY-RUN VISUALIZATION</div><h1>{escape(title)}</h1><div class="chips"><span class="chip">{escape(pattern)}</span><span class="chip">{escape(time)}</span><span class="chip">{escape(space)}</span></div><div class="layout"><section class="panel"><h2>Problem</h2><p>{escape(statement)}</p><h2 style="margin-top:18px">Given Input</h2><div class="input">{escape(example)}</div><div class="tokens" id="tokens"></div></section><section class="panel"><div class="step" id="label"></div><div class="caption" id="caption"></div><h2>State To Explain</h2><div class="state" id="state"></div></section></div><div class="why"><strong>Teaching rule:</strong> pause after each step and ask: “What state changed? Why is the invariant still true? What would make us move differently?”</div><div class="controls"><button class="btn primary" id="play">Pause</button><button class="btn" id="previous">Previous</button><button class="btn" id="next">Next</button><button class="btn" id="reset">Reset</button><div class="progress"><i id="bar"></i></div></div><div class="steps" id="steps"></div></main><script id="trace-data" type="application/json">{trace_json}</script><script id="token-data" type="application/json">{token_json}</script>{SCRIPT}</body></html>'''

def main():
    problems = deck_generator.parse_problems(deck_generator.SOURCE.read_text(encoding="utf-8"))
    if len(problems) != 70:
        raise ValueError(f"Expected 70 problems, found {len(problems)}")
    OUTPUT.mkdir(exist_ok=True)
    for problem in problems:
        rank, lc_id, title, *_ = problem
        if lc_id == "146":
            continue
        slug = re.sub(r"[^a-z0-9]+", "-", title.strip().lower()).strip("-")
        output = OUTPUT / f"{int(rank):02d}-lc-{lc_id}-{slug}-dry-run.html"
        output.write_text(build(problem), encoding="utf-8")
    print(f"Generated {len(problems)} autoplay dry-run pages in {OUTPUT.name}.")

if __name__ == "__main__":
    main()