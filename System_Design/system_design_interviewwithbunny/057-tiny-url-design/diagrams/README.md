# 🎨 Tiny URL System Design Diagrams

> **⚠️ ATTENTION BEGINNERS**: Current diagrams need improvement! See [DIAGRAM_IMPROVEMENT_GUIDE.md](DIAGRAM_IMPROVEMENT_GUIDE.md) for detailed instructions on how to enhance them for better learning.

---

## 📚 **Learning Path (Start Here!)**

```
┌─────────────────────────────────────────────────────────────┐
│  RECOMMENDED LEARNING SEQUENCE                              │
├─────────────────────────────────────────────────────────────┤
│  1. Read ../INTERVIEW_GUIDE.md (Pages 1-2 first)           │
│     ↓                                                       │
│  2. Read BEGINNERS_GUIDE.md (understand concepts)           │
│     ↓                                                       │
│  3. Read DIAGRAM_IMPROVEMENT_GUIDE.md (see what's missing)  │
│     ↓                                                       │
│  4. Apply improvements to diagrams (hands-on learning!)     │
│     ↓                                                       │
│  5. Practice drawing Diagram 2 (HLD) on whiteboard          │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚨 **Why These Diagrams Need Improvement**

The current diagrams are **too abstract** for beginners. They're missing:

- ❌ Clear separation of **WRITE PATH** vs **READ PATH** (critical insight!)
- ❌ Traffic volume indicators (1,157/sec writes vs 115,740/sec reads)
- ❌ **Zookeeper** for ID generation (key component)
- ❌ **Redis cache** positioning as first-line defense
- ❌ Timing annotations (0.1ms cache hit vs 5ms DB miss)
- ❌ Explanation boxes ("Why this component exists?")
- ❌ Failure scenarios and mitigations

**The improvement guide shows exactly what to fix!**

---

## 📂 **Current Diagram Files**

| File | Current State | Priority | Improvement Guide Section |
|------|---------------|----------|---------------------------|
| `01-context.drawio` | ⚠️ Missing read/write ratio | Medium | Section: Diagram 1 |
| `02-hld-components.drawio` | ⚠️ Needs write/read split | **HIGH** | Section: Diagram 2 (MOST IMPORTANT) |
| `03-primary-sequence.drawio` | ⚠️ No cache hit/miss paths | High | Section: Diagram 3 |
| `04-data-model.drawio` | ⚠️ Missing Redis/ClickHouse | Medium | Section: Diagram 4 |
| `05-scale-failures.drawio` | ⚠️ No failure scenarios | Medium | Section: Diagram 5 |

---

## 🛠️ **How to Open & Edit**

### **Option 1: Online (Easiest)**
1. Go to [diagrams.net](https://app.diagrams.net)
2. Click **File → Open** → select a `.drawio` file from this folder
3. Edit using the improvement guide instructions
4. **File → Save** back to the same file

### **Option 2: VS Code (Recommended for Developers)**
1. Install extension: `Draw.io Integration` by Henning Dieterichs
2. Click any `.drawio` file in VS Code
3. Edit in the built-in viewer
4. Ctrl+S / Cmd+S to save

### **Option 3: Desktop App**
1. Download [draw.io desktop app](https://github.com/jgraph/drawio-desktop/releases)
2. Open `.drawio` files directly
3. Edit and save

---

## 📖 **Key Documents**

| File | Purpose | When to Read |
|------|---------|--------------|
| [INTERVIEW_GUIDE.md](../INTERVIEW_GUIDE.md) | Complete interview script with analogies | **START HERE** - Read pages 1-2 tonight |
| [DIAGRAM_IMPROVEMENT_GUIDE.md](DIAGRAM_IMPROVEMENT_GUIDE.md) | Step-by-step instructions to fix diagrams | After understanding concepts |
| [BEGINNERS_GUIDE.md](BEGINNERS_GUIDE.md) | Walkthrough of current diagrams | Read alongside diagrams |

---

## 🎯 **Interview Usage Strategy**

### **What to Draw in an Interview (Whiteboard)**

**ONLY draw Diagram 2 (HLD Components) - the rest you discuss verbally!**

```
Time Budget (45-min interview):
├─ 5 min: Requirements gathering
├─ 3 min: Capacity estimation
├─ 10 min: Draw Diagram 2 (HLD) - WRITE & READ paths
├─ 15 min: Deep dive on ID generation, caching, sharding
├─ 7 min: Discuss failures (Diagram 5 concepts verbally)
└─ 5 min: Q&A / trade-offs
```

**Pro Tip**: Practice drawing Diagram 2 in under 5 minutes! That's your core visual aid.

---

## 🎨 **Visual Design Standards**

### **Color Coding (Apply to Improved Diagrams)**

| Component Type | Color | Hex Code |
|----------------|-------|----------|
| Write Path | Light Blue | `#ADD8E6` |
| Read Path | Light Green | `#90EE90` |
| Analytics | Light Orange | `#FFB84D` |
| Cache Layers | Light Yellow | `#FFFFE0` |
| Failures | Light Red | `#FFB6C1` |

### **Icons to Use**

- 🔥 Hot path (high traffic)
- ⏱️ Timing measurements
- 🧠 Key insights / "Why?" boxes
- ⚠️ Edge cases
- ❌ Failure points
- ✅ Success paths
- 🛡️ Reliability patterns

---

## ✅ **Quality Checklist**

Before considering diagrams "interview-ready":

- [ ] **Diagram 2** clearly separates WRITE (left) and READ (right) paths
- [ ] Traffic volumes shown: 1,157/sec vs 115,740/sec
- [ ] All 7 components present: API Gateway, Shortener, Redirect, Zookeeper, Redis, MySQL, Kafka+ClickHouse
- [ ] Each component has a "Why it exists" explanation box
- [ ] **Diagram 3** shows cache hit (0.1ms) vs miss (5ms) timing
- [ ] **Diagram 4** includes MySQL, Redis, AND ClickHouse schemas
- [ ] **Diagram 5** shows at least 3 failure scenarios with mitigations
- [ ] All diagrams use consistent color coding

---

## 🚀 **Quick Start (15 Minutes)**

**Want to make these diagrams interview-ready fast?**

1. **Read**: DIAGRAM_IMPROVEMENT_GUIDE.md → Section: Diagram 2 (10 min)
2. **Edit**: Open `02-hld-components.drawio` in diagrams.net
3. **Apply**: Follow the "LEFT SIDE: WRITE PATH" and "RIGHT SIDE: READ PATH" templates
4. **Test**: Can you explain this diagram to a friend in under 3 minutes?

**That one diagram is 80% of the interview!**

---

## 💡 **Why Separate WRITE and READ Paths?**

> This is the #1 insight interviewers look for!

```
WRITE PATH:  1,157 requests/sec  → Simple, any DB handles it
READ PATH:   115,740 requests/sec → HARD! Needs caching, CDN, sharding

Interview red flag: Treating them the same
Interview green flag: "This is a 100:1 read-heavy system, 
                       so I'll optimize the read path with..."
```

---

## 📁 **Export for Presentations**

Once diagrams are improved:

1. **File → Export as → PNG** (for slides/documents)
2. **File → Export as → SVG** (for scaling/printing)
3. Save in a separate `exports/` folder

---

## 🤝 **Contributing**

If you improve these diagrams:
1. Follow the improvement guide structure
2. Add beginner explanation boxes
3. Test with someone new to system design
4. Export a PNG preview

---

## 📞 **Help & Resources**

- **Stuck on a diagram?** Check the corresponding section in INTERVIEW_GUIDE.md
- **Don't understand a component?** Read BEGINNERS_GUIDE.md
- **Want to verify your changes?** Use the checklist in DIAGRAM_IMPROVEMENT_GUIDE.md

**Remember**: These diagrams are **learning tools**, not art projects. Clarity > Beauty!
