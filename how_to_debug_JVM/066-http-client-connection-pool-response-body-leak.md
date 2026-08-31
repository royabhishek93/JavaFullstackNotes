# #66 — HTTP Client Connection Pool + Unconsumed Response Body Leak

> **Category:** Heap Dump Analysis | **Type:** Scenario Q&A | **Priority:** 👍 Good-to-Know

## 🗣️ The Interview Question
"OOM on a service that calls 5 downstream APIs. Heap dump shows millions of byte[] objects. No obvious static collection. What do you look for?"

## 😊 Explain It Simply (for anyone)
When you make a phone call to another company (calling a downstream API), the phone line (an HTTP connection) is a shared, limited resource — there's a small pool of phone lines everyone shares. Proper etiquette is: you listen to the ENTIRE message the other person leaves you (read the full response body) and then hang up cleanly, so the line goes back into the shared pool for the next caller.

If your code hangs up early — maybe because you decided you didn't like the answer and returned immediately — the line is left in limbo, still holding onto the recorded message's buffer (bytes) in memory, and can't be reused. Do this enough times across 5 different services and you run out of phone lines while also piling up millions of half-finished voicemail recordings (byte arrays) in memory.

## 📊 Visualize It
```
RestTemplate call to downstream API:
  response = restTemplate.getForEntity(url, String.class)
  if (status != 200) return null;   ← BUG: body never read/closed!

Connection pool:  [C1][C2][C3]...[C20]
  each early-return leaves a connection "checked out"
  with its response buffer (byte[]) still referenced

Heap dump histogram:
  byte[]                            →  3,000,000 instances
  sun.net.www.http.KeepAliveStream  →  high count, all unclosed

Fix: WebClient .bodyToMono(String.class).onErrorResume(...)
  → stream is always fully drained/terminated, connection returns to pool
```

## 🏭 The Real Production Answer (15-YOE Level)

When using `RestTemplate`, `HttpClient`, or `WebClient`, if the response body is not fully consumed and closed, the connection cannot be returned to the pool. The `InputStream` backing the response body holds a reference to the buffer.

```java
// Leaking — response not closed
public String fetchData(String url) {
    ResponseEntity<String> response = restTemplate.getForEntity(url, String.class);
    if (response.getStatusCode() != HttpStatus.OK) {
        // BUG: early return without consuming body
        return null;
    }
    return response.getBody();
}

// Fix with WebClient — reactive, handles backpressure
public Mono<String> fetchData(String url) {
    return webClient.get()
        .uri(url)
        .retrieve()
        .bodyToMono(String.class)
        .onErrorResume(e -> Mono.empty()); // Always terminates the stream
}
```

Diagnosis in heap dump:
- MAT histogram → look for high count of `byte[]` → check the dominator
- Filter by `sun.net.www.http.KeepAliveStream` or `org.apache.http.impl.io.SessionInputBufferImpl`
- These are the buffers held by unconsumed response bodies

## 🔑 Key Takeaway
If you don't fully read AND close an HTTP response body, the connection — and its buffer — never returns to the pool, even on error paths.
