# #121 — DOM Parsing Large XML → OOM

> **Category:** Memory Leaks End-to-End | **Type:** Scenario Q&A | **Priority:** 📘 Advanced

## 🗣️ The Interview Question
"Why does parsing a 500MB XML file with DocumentBuilder cause an OOM?"

## 😊 Explain It Simply (for anyone)
DOM parsing (loading an entire document into a big in-memory tree structure, all at once, so you can navigate it freely) is like photocopying an ENTIRE 500-page book, page by page, and stapling every single page together into one giant binder before you're allowed to read even the first sentence. Each "page" in Java's version costs extra overhead (metadata bookkeeping per object), so a 500MB file can balloon to 1.5–3 GB in memory. A smarter approach — streaming (reading the book one page at a time, remembering only what you need, then discarding the page) — lets you process the same document using a tiny fraction of the memory.

## 📊 Visualize It
```
 DOM (Document Object Model) — loads EVERYTHING at once:

  500 MB XML file
       |
       v
  [Full in-memory tree: Element, Attribute, Text nodes]
       |
       v
  1.5 GB - 3 GB heap usage  <-- OOM risk!

 StAX/SAX streaming — one element in memory at a time:

  500 MB XML file --(stream)--> [current element only] --> discard --> next
       small, constant memory footprint
```

## 🏭 The Real Production Answer (15-YOE Level)

Buggy code:
```java
public Document parse(InputStream xml) throws Exception {
    // LEAK: loads the ENTIRE document tree into memory at once
    DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
    DocumentBuilder builder = factory.newDocumentBuilder();
    return builder.parse(xml); // 500MB file → easily 3-5x in memory as DOM
}
```

Why it leaks: DOM parsing builds a complete in-memory tree. A 500MB XML can require 1.5–3 GB of heap for the DOM (due to Java object overhead per node — element, attribute, text node each carry ~100-200 bytes of JVM overhead).

Fix — use SAX or StAX for streaming:
```java
// StAX streaming: only current element in memory at once
public void processLargeXml(InputStream xml) throws Exception {
    XMLInputFactory factory = XMLInputFactory.newInstance();
    XMLStreamReader reader = factory.createXMLStreamReader(xml);
    while (reader.hasNext()) {
        int event = reader.next();
        if (event == XMLStreamConstants.START_ELEMENT) {
            handleElement(reader.getLocalName(), reader);
        }
    }
    reader.close();
}
```

For very large files that must be processed as DOM, split into chunks with a SAX-based splitter, or use VTD-XML which provides random access without full in-memory tree.

## 🔑 Key Takeaway
Never DOM-parse a file whose size is unbounded or large — use SAX/StAX streaming so memory usage stays constant regardless of file size.
