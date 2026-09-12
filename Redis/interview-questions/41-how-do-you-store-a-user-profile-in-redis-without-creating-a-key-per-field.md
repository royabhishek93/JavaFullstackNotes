# How do you store a user profile in Redis without creating a key per field?

**Type:** Scenario-Based
**Topic:** Redis Core Data Types — Hashes
**Level:** Mid Interview (3–8+ YOE)

## Direct Answer
Use a **Hash**. A single Redis key (e.g., `user:1000`) can hold many field/value pairs (`name`, `email`, `phone`, etc.), so the whole profile lives under one key instead of scattering `user:1000:name`, `user:1000:email`, `user:1000:phone` as separate top-level keys.

## Easy Explanation
A Hash is like a labeled folder — one folder (`user:1000`), with several labeled sheets of paper inside it (`name`, `email`, `phone`). You can pull out just one sheet (`HGET`) or the whole folder at once (`HGETALL`), and updating one sheet doesn't require reprinting the others. Using separate top-level keys for every field is like scattering those sheets across the whole filing cabinet instead of keeping them together.

## Diagram
```
Instead of:
  user:1000:name  -> "Piyush"
  user:1000:email -> "piyush@example.com"
  user:1000:phone -> "9999999999"
  (3 separate top-level keys for one entity)

Use a Hash — ONE key, many fields:
  HSET user:1000 name "Piyush" email "piyush@example.com" phone "9999999999"

  user:1000  (Hash)
    ├── name  -> "Piyush"
    ├── email -> "piyush@example.com"
    └── phone -> "9999999999"

  HGET user:1000 email     -> "piyush@example.com"   (just one field)
  HGETALL user:1000        -> all fields at once
```

## Production Example
```bash
HSET user:1000 name "Piyush" plan "pro" loginCount 42
HGET user:1000 plan            # "pro"
HINCRBY user:1000 loginCount 1 # atomically bump just that one field
HDEL user:1000 plan            # remove just one field, rest stay intact
```

This pattern is used constantly for caching database rows: one Hash per row, with each column mapped to a field — far tidier than one Redis key per column, and it lets you update a single field (like `loginCount`) without touching the rest of the cached object.

## Why Interviewers Ask This
It's a foundational question that reveals whether a candidate understands *why* Hashes exist — as the natural fit for "object with several fields" — instead of defaulting to plain Strings with manually concatenated key names for every field.
