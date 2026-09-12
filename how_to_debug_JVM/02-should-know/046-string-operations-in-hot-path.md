# #46 — String Operations in the Hot Path

> **Category:** CPU Profiling & Flame Graphs | **Type:** Scenario Q&A | **Priority:** ⭐ Should-Know

## 🗣️ The Interview Question
"E-commerce service is CPU-bound on the order formatting path. What are the usual string suspects?"

## 😊 Explain It Simply (for anyone)
Think about writing a thousand postcards by hand. If, for each postcard, you first tear up your last draft and start the sentence completely from scratch (rather than just editing what you already wrote), you'll waste enormous time re-copying words that never changed. In programming, joining strings together with `+` in a loop does something similar behind the scenes — each concatenation can create a brand-new, slightly bigger copy of the whole string, throwing away the old one, which becomes painfully slow as the list grows. Similarly, using a "fill-in-the-blanks" formatting tool (like `String.format`) is convenient but has to re-read and re-parse the blank-filling template every single time it's called, like re-reading the postcard template's instructions from scratch for every card instead of remembering the layout. The fix for both is to use a single reusable "scratchpad" (a `StringBuilder`) that you keep appending to, and to avoid template-parsing tools in loops that run thousands of times per second.

## 📊 Visualize It
```
WRONG:  result = "" ; result += a ; result += b ; ...
        [copy][copy+a][copy+a+b][copy+a+b+c]...  <- O(n) new copies!

WRONG:  String.format("Order %s: $%.2f", id, total)
        [parse format string EVERY call] -> [allocate buffer] -> [result]

RIGHT:  StringBuilder sb = new StringBuilder(sizeHint);
        sb.append(a).append(b).append(c);   <- one growing buffer, no re-parse
```

## 🏭 The Real Production Answer (15-YOE Level)
```java
// WRONG — StringBuilder created implicitly per concat, O(n) copies
String result = "";
for (Order o : orders) {
    result += o.getId() + "," + o.getTotal() + "\n";
}

// WRONG — String.format parses format string on every call
String line = String.format("Order %s: $%.2f", o.getId(), o.getTotal());

// RIGHT — pre-sized StringBuilder, avoid format parsing
StringBuilder sb = new StringBuilder(orders.size() * 40);
for (Order o : orders) {
    sb.append(o.getId()).append(',').append(o.getTotal()).append('\n');
}
```

In the flame graph, `String.format` shows up because `Formatter` parses the format string, allocates a buffer, and the format string itself isn't cached by the JVM. At 10k calls/sec this is measurable.

## 🔑 Key Takeaway
In hot loops, avoid `+=` concatenation and `String.format` — use a pre-sized `StringBuilder` since both alternatives re-copy or re-parse on every single call.
