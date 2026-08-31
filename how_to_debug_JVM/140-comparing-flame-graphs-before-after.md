# #140 — Comparing Two Flame Graphs (Before/After)

> **Category:** CPU Profiling & Flame Graphs | **Type:** Advanced Scenario Q&A | **Priority:** ⚙️ Expert/Niche

## 🗣️ The Interview Question
"You deployed a fix for a CPU regression. How do you quantitatively compare pre- and post-deployment flame graphs?"

## 😊 Explain It Simply (for anyone)
Imagine you take a "before" photo and an "after" photo of a messy room you cleaned up, and you want to know precisely what changed — not just eyeball two pictures and guess. Simply staring at two flame graphs side by side is like eyeballing those two room photos: your brain is bad at spotting small, precise differences in complex, colorful images, and you might miss a new mess that appeared in a corner while celebrating that the middle of the room got cleaner. The better approach is a differencing tool that overlays the "before" and "after" data automatically and highlights, in color, exactly where things got worse (shown in red) versus where things got better (shown in blue) — like a photo-editing tool that highlights only the pixels that changed. This "differential flame graph" turns a fuzzy visual comparison into a precise, colored map of exactly which functions got faster, which got slower, and whether any brand-new hot spots appeared as a side effect of your fix.

## 📊 Visualize It
```
before.txt (collapsed stacks)     after.txt (collapsed stacks)
        \                                /
         \                              /
          -----> difffolded.pl ---------
                       |
                       v
                 flamegraph.pl
                       |
                       v
              diff.svg
    [RED = more CPU after (regression)]
    [BLUE = less CPU after (improvement)]
    width = magnitude of the sample-count delta
```

## 🏭 The Real Production Answer (15-YOE Level)
Visual comparison of two flame graphs is error-prone. Use differential flame graphs.

async-profiler can produce collapsed stacks:
```bash
# Before deployment
./profiler.sh -e cpu -d 60 -o collapsed -f /tmp/before.txt <pid>

# After deployment
./profiler.sh -e cpu -d 60 -o collapsed -f /tmp/after.txt <pid>

# Generate differential flame graph using Brendan Gregg's tools
./difffolded.pl /tmp/before.txt /tmp/after.txt | ./flamegraph.pl > /tmp/diff.svg
```

In the diff flame graph, red = regression (more CPU after), blue = improvement (less CPU after). The width still represents sample count delta. This makes it immediately obvious if your fix helped and where any new hotspots appeared.

Quantitatively: compare total sample counts for the hot method:
```bash
grep "Pattern.compile" /tmp/before.txt | awk -F' ' '{sum+=$2} END {print sum}'
grep "Pattern.compile" /tmp/after.txt  | awk -F' ' '{sum+=$2} END {print sum}'
```

## 🔑 Key Takeaway
Don't eyeball two flame graphs — generate collapsed stacks for before/after and run `difffolded.pl` to produce a colored diff that quantifies exactly what got better or worse.
