# 🎨 TinyURL System — Beginner-Friendly Diagrams

## What's Different About These Diagrams?

These diagrams are designed to **match the interview guide's clarity**. They include:

✅ **Real-world analogies** (Redis = fridge, MySQL = basement filing cabinet)  
✅ **Step-by-step numbered flows** with timing information  
✅ **"WHY" explanations** for every component  
✅ **Large, readable text** (no tiny boxes!)  
✅ **Color-coded paths** (write = blue, read = green, errors = red)  
✅ **Latency calculations** showing the math  

## How to Open

### Option 1: Online (Easiest)
1. Go to [diagrams.net](https://app.diagrams.net)
2. File → Open → select any `.drawio` file from this folder
3. Edit, zoom, export as needed

### Option 2: VS Code
1. Install **Draw.io Integration** extension
2. Click any `.drawio` file in this folder
3. Edit directly in VS Code

### Option 3: Desktop App
1. Download [draw.io desktop](https://github.com/jgraph/drawio-desktop/releases)
2. Open any `.drawio` file

## Diagrams in This Folder

### 01-context-BEGINNER.drawio
**The Big Picture — Start Here!**

Shows:
- Left side: **Write path** (creating short URLs) — happens 1,157 times/sec
- Right side: **Read path** (redirecting) — happens 115,740 times/sec  
- Key components with analogies (Zookeeper = lottery ticket dispenser)
- Cache hit vs cache miss paths

**Use this for:** Initial 5-minute interview answer, explaining overall architecture

---

### 02-hld-components-BEGINNER.drawio
**Component Deep Dive — WHY Each Piece Exists**

Each component has:
- What it does
- **WHY it exists** (problem it solves)
- Real-world analogy
- Common trap to avoid

Components explained:
- Zookeeper (ID range coordinator)
- Base62 encoding
- MySQL (storage)
- Redis (cache layer)
- Kafka + ClickHouse (analytics)
- 302 vs 301 redirect
- Rate limiter
- CDN edge cache

**Use this for:** When interviewer asks "Why not just use X?" or "Why do you need Y?"

---

### 03-sequence-flow-BEGINNER.drawio
**Step-by-Step Flow — The Timeline View**

Shows two complete flows:

**FLOW 1: CREATE SHORT URL**
- 6 steps with exact timing
- Total: ~5ms

**FLOW 2: REDIRECT (THE CRITICAL PATH)**
- Cache hit path (90% of requests): 0.5ms ⚡
- Cache miss path (10% of requests): 5ms
- Math showing average latency: 0.95ms

**Use this for:** When interviewer asks "Walk me through what happens when..." or for deep-dive questions

---

### 04-data-model-BEGINNER.drawio
**Database Schema — Table Structure Explained**

Shows:
- **url_mappings table**: Every column explained with WHY it exists
- **url_clicks table** (ClickHouse): Why separate from main table
- **Indexes**: Which indexes to create and WHY
- **Sharding strategy**: How to split across 10 MySQL servers

Key concepts:
- PRIMARY KEY on short_code (O(log n) lookup)
- Why TEXT not VARCHAR for long_url
- OLTP vs OLAP pattern
- Index warnings (what NOT to create)

**Use this for:** When interviewer asks "Show me your schema" or "How do you store this?"

---

## Interview Tips

### Opening (First 60 seconds)
1. Draw **01-context-BEGINNER** on whiteboard
2. Explain the asymmetry: "Write path is easy (1K/sec), read path is the challenge (100K/sec)"
3. Point out: "Cache + DB combo solves this perfectly"

### Deep Dive (Next 10 minutes)
1. Reference **02-hld-components-BEGINNER** to explain WHY choices
2. Use **03-sequence-flow-BEGINNER** to walk through both flows
3. Always show the latency math!

### Common Questions
- **"Why not just hash the URL?"** → Point to Zookeeper box in diagram 02 (collision problem)
- **"Why Redis AND MySQL?"** → Point to cache analogy (fridge vs basement)
- **"Show me the numbers"** → Use diagram 03's latency breakdown

## Customization Tips

Want to personalize these diagrams for your interview?

1. **Change scale numbers**: Update "1,157/sec" to match your requirements
2. **Add your details**: Click any text box and edit
3. **Export for presentation**: File → Export as PNG/SVG
4. **Print for whiteboard practice**: Export as PDF, print, practice drawing

## Compared to Original Diagrams

| Original | Beginner-Friendly |
|----------|-------------------|
| Technical jargon | Plain English + analogies |
| Small text, hard to read | Large, clear labels |
| Just shows components | Shows components + WHY they exist |
| No timing info | Step-by-step with ms latency |
| Static | Explains the "why" at every step |

## Learning Path

1. **Day 1**: Study diagram 01 (big picture) for 30 minutes
2. **Day 2**: Study diagram 02 (components) — memorize the "WHY" for each
3. **Day 3**: Study diagram 03 (flow) — practice explaining both flows
4. **Day 4**: Print and practice drawing simplified versions on whiteboard
5. **Day 5**: Mock interview — explain from memory

## Questions?

These diagrams are based on the [INTERVIEW_GUIDE.md](../INTERVIEW_GUIDE.md) in the parent folder. If anything is unclear, check the guide for more detailed explanations.

---

**Remember:** Interviewers care more about your **reasoning** than perfect recall. The "WHY" boxes in these diagrams are your secret weapon! 🎯
