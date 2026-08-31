#!/usr/bin/env python3
"""Generate contract-oriented visualizers from the Java priority guide."""
from html import escape
from pathlib import Path
import importlib.util
import json
import re

ROOT = Path(__file__).parent
OUTPUT = ROOT / "leetcode-dry-run-animations"
CUSTOM_IDS = {"146", "207", "347"}

spec = importlib.util.spec_from_file_location("deck_generator", ROOT / "generate_leetcode_video_decks.py")
deck_generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deck_generator)


def model_for(pattern):
    text = pattern.lower()
    if any(word in text for word in ("tree", "graph", "dfs", "bfs", "flood")):
        return "Traversal frontier", "visited / frontier / current node"
    if any(word in text for word in ("linked", "pointer", "list")):
        return "Linked nodes", "head / current / previous / next links"
    if any(word in text for word in ("stack", "parentheses", "histogram")):
        return "Stack state", "index / stack / result"
    if any(word in text for word in ("sliding", "substring", "window")):
        return "Sliding window", "left / right / counts / best"
    if any(word in text for word in ("dynamic", "coin", "house", "paths", "subset")):
        return "Dynamic-programming table", "position / dp values / best"
    if any(word in text for word in ("heap", "priority", "median", "closest")):
        return "Heap state", "heap / candidate / result"
    if "binary" in text or "rotated" in text:
        return "Search range", "left / mid / right"
    if any(word in text for word in ("hash", "anagram", "sum")):
        return "Hash state", "index / lookup map / answer"
    return "Working state", "input position / working values / result"


def kind_for(line):
    text = line.strip()
    if text.startswith(("for ", "for(", "while ", "while(")):
        return "loop condition"
    if text.startswith(("if ", "if(")) or text.startswith("else if"):
        return "branch check"
    if text.startswith("return "):
        return "return"
    if "=" in text and not any(operator in text for operator in ("==", "!=", ">=", "<=")):
        return "state update"
    if "(" in text and ")" in text:
        return "method call"
    return "statement"


def explain(kind, line):
    if kind == "loop condition":
        return f"Check whether this loop has another item to process: `{line}`."
    if kind == "branch check":
        return f"Evaluate this decision before changing the visible state: `{line}`."
    if kind == "state update":
        return f"Apply this exact Java state update: `{line}`."
    if kind == "method call":
        return f"Execute this method or helper call: `{line}`."
    if kind == "return":
        return f"Return the value maintained by the algorithm: `{line}`."
    return f"Execute the active Java statement: `{line}`."


def trace_for(code, pattern, expected):
    source = [line.rstrip() for line in code.strip().splitlines()]
    model, variables = model_for(pattern)
    steps = []
    for number, raw in enumerate(source, 1):
        line = raw.strip()
        if not line or line in {"{", "}"} or line.startswith("//"):
            continue
        kind = kind_for(line)
        steps.append({
            "line": number, "kind": kind, "active": line,
            "before": f"{model}: before Java line {number}; {variables} are unchanged.",
            "after": f"{model}: apply line {number} and refresh {variables}.",
            "variables": variables, "explanation": explain(kind, line),
            "invariant": f"The {model.lower()} must represent every processed part of the canonical input."
        })
    steps.append({
        "line": len(source), "kind": "expected result", "active": "return result",
        "before": f"{model}: all canonical input is processed.", "after": f"Expected output: {expected}",
        "variables": variables, "explanation": "Compare the final visual state with the expected output.",
        "invariant": "The final result must agree with the canonical example."
    })
    return source, steps


STYLE = """<style>@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');*{box-sizing:border-box}:root{--bg:#08131f;--surface:#0f2233;--surface2:#132d42;--line:#2b4e66;--ink:#edf6fb;--muted:#a9c0d0;--cyan:#61d9d2;--blue:#75baff;--amber:#ffd166;--green:#a7e47a}body{margin:0;background:linear-gradient(135deg,#08131f,#10283a);color:var(--ink);font-family:'DM Sans',sans-serif}main{max-width:1440px;margin:auto;padding:24px}.eyebrow{color:var(--cyan);font:700 11px 'IBM Plex Mono',monospace;letter-spacing:.08em}h1{margin:6px 0;font-size:2.35rem}p{color:var(--muted)}.chips,.controls{display:flex;gap:8px;flex-wrap:wrap}.chip{border:1px solid var(--line);border-radius:999px;padding:4px 9px;color:var(--muted);font-size:12px}.layout{display:grid;grid-template-columns:minmax(0,1.05fr) minmax(360px,.95fr);gap:14px;margin-top:18px}.panel{background:rgba(15,34,51,.96);border:1px solid var(--line);border-radius:8px;padding:16px;min-width:0}.panel h2{font-size:.88rem;margin:0 0 10px;color:var(--cyan)}.input,.state,.code{font:13px/1.6 'IBM Plex Mono',monospace;white-space:pre-wrap}.state{min-height:92px;color:#d4e7f2}.code{height:525px;overflow:auto;background:#07121d;border:1px solid #203e53;padding:8px;border-radius:5px}.code-line{display:block;padding:1px 7px;border-left:3px solid transparent}.code-line.active{background:#1a4055;border-left-color:var(--amber);color:#fff}.line-no{display:inline-block;width:34px;color:#7896aa}.label{font:700 12px 'IBM Plex Mono',monospace;color:var(--blue);margin-bottom:10px}.active-source{color:var(--amber);font:13px/1.55 'IBM Plex Mono',monospace;overflow-wrap:anywhere}.caption{min-height:68px;line-height:1.55}.invariant{border-left:3px solid var(--green);padding:10px 12px;background:#10291c;color:#dff7cd;line-height:1.5}.controls{align-items:center;margin-top:16px}.btn{background:var(--surface2);border:1px solid var(--line);color:var(--ink);border-radius:5px;padding:8px 12px;cursor:pointer;font:600 13px 'DM Sans',sans-serif}.btn.primary{background:#164560;border-color:var(--blue)}.meter{margin-left:auto;color:var(--muted);font:12px 'IBM Plex Mono',monospace}@media(max-width:820px){main{padding:16px}h1{font-size:1.8rem}.layout{grid-template-columns:1fr}.code{height:370px}.meter{margin-left:0}}</style>"""


def build(problem):
    rank, lc_id, title, pattern, time, space, statement, example, java = problem
    expected = example.split("→")[-1].strip() if "→" in example else "See canonical example"
    code, trace = trace_for(java, pattern, expected)
    data = json.dumps(code).replace("</", "<\\/")
    trace_data = json.dumps(trace).replace("</", "<\\/")
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>LC {lc_id} {escape(title)} | Code Dry Run</title>{STYLE}</head><body><main><div class="eyebrow">LC {lc_id} | CODE-LEVEL DRY RUN</div><h1>{escape(title)}</h1><div class="chips"><span class="chip">{escape(pattern)}</span><span class="chip">{escape(time)}</span><span class="chip">{escape(space)}</span></div><div class="layout"><section class="panel"><h2>Canonical Input</h2><div class="input">{escape(example)}</div><h2 style="margin-top:18px">State Before / After</h2><div class="state" id="before"></div><div class="state" id="after"></div><h2 style="margin-top:18px">Variables</h2><div class="state" id="variables"></div></section><section class="panel"><h2>Complete Java Solution</h2><div class="code" id="code"></div></section></div><div class="layout"><section class="panel"><div class="label" id="label"></div><div class="active-source" id="active"></div><p class="caption" id="caption"></p><div class="invariant" id="invariant"></div></section><section class="panel"><h2>Expected Output</h2><div class="state">{escape(expected)}</div><p>{escape(statement)}</p></section></div><div class="controls"><button class="btn primary" id="play">Play</button><button class="btn" id="previous">Previous</button><button class="btn" id="next">Next</button><button class="btn" id="reset">Reset</button><span class="meter" id="meter"></span></div></main><script id="code-data" type="application/json">{data}</script><script id="trace-data" type="application/json">{trace_data}</script><script>const codeLines=JSON.parse(document.querySelector('#code-data').textContent),trace=JSON.parse(document.querySelector('#trace-data').textContent);let index=0,running=false,timer;const code=document.querySelector('#code');const html=value=>value.replace(/[&<>]/g,char=>({{"&":"&amp;","<":"&lt;",">":"&gt;"}}[char]));codeLines.forEach((line,i)=>{{const row=document.createElement('span');row.className='code-line';row.dataset.line=i+1;row.innerHTML=`<span class="line-no">${{String(i+1).padStart(2,' ')}}</span>${{html(line)||' '}}`;code.append(row)}});function render(){{const step=trace[index];label.textContent=`STEP ${{index+1}} / ${{trace.length}} | ${{step.kind.toUpperCase()}} | JAVA LINE ${{step.line}}`;active.textContent=step.active;before.textContent=step.before;after.textContent=step.after;variables.textContent=step.variables;caption.textContent=step.explanation;invariant.textContent=step.invariant;meter.textContent=`${{index+1}} / ${{trace.length}}`;document.querySelectorAll('.code-line').forEach(row=>row.classList.toggle('active',Number(row.dataset.line)===step.line));const selected=code.querySelector('.active');if(selected)selected.scrollIntoView({{block:'center',behavior:'smooth'}})}}function stop(){{running=false;clearInterval(timer);play.textContent='Play'}}function next(){{index=Math.min(index+1,trace.length-1);render();if(index===trace.length-1)stop()}}previous.onclick=()=>{{stop();index=Math.max(0,index-1);render()}};next.onclick=()=>{{stop();next()}};reset.onclick=()=>{{stop();index=0;render()}};play.onclick=()=>{{running=!running;play.textContent=running?'Pause':'Play';clearInterval(timer);if(running)timer=setInterval(next,2400)}};document.addEventListener('keydown',event=>{{if(event.key==='ArrowRight')next.click();if(event.key==='ArrowLeft')previous.click();if(event.key===' '){{event.preventDefault();play.click()}}}});render();</script></body></html>'''


def main():
    problems = deck_generator.parse_problems(deck_generator.SOURCE.read_text(encoding="utf-8"))
    if len(problems) != 70:
        raise ValueError(f"Expected 70 source problems, found {len(problems)}")
    for problem in problems:
        rank, lc_id, title, *_ = problem
        if lc_id not in CUSTOM_IDS:
            slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
            page = build(problem).replace(
                "</body></html>",
                "<script>document.querySelector('#next').onclick=()=>{stop();next()};</script></body></html>",
            )
            (OUTPUT / f"{int(rank):02d}-lc-{lc_id}-{slug}-dry-run.html").write_text(page, encoding="utf-8")
    print("Generated 67 code-level dry-run pages; preserved 01, 02, and 05.")


if __name__ == "__main__":
    main()