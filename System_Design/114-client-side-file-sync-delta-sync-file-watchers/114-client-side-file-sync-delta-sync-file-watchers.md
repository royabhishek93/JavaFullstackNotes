# Client-Side File Sync: Watchers, Delta Sync, and Conflict Resolution
### How Dropbox notices a 4KB edit in a 2GB file and uploads only the part that changed

---

## PART 1 — THE STUDENT CONVERSATION

Imagine you edit a single paragraph in a 500-page PDF stored in your Dropbox folder. Naive sync would notice the file changed and re-upload the whole thing — potentially hundreds of megabytes — for a change of a few kilobytes. Do that a dozen times a day and you've saturated your upload bandwidth syncing edits that are, byte-for-byte, 99.9% identical to what's already in the cloud.

The first problem to solve is even more basic: how does the sync client know a file changed *at all*, the instant it happens, without constantly asking the OS "did anything change yet? did anything change yet?" thousands of times a second? That brute-force polling approach — rescanning every file's modification time in a folder tree — is exactly what it sounds like: expensive, slow to detect changes (only as fast as your poll interval), and wasteful on a laptop with 200,000 files in its sync folder. The fix is to let the operating system tell you, proactively, the moment something changes. Every major OS has a kernel-level facility for this — Linux has `inotify`, macOS has `FSEvents`, Windows has `ReadDirectoryChangesW`. The sync client registers "watch this folder" once, and the kernel pushes a notification event the instant a file is created, modified, or deleted — no polling loop at all.

Once you know *that* a file changed, you still face the "re-upload the whole 500-page PDF" problem. The fix here is **delta sync**: instead of treating the file as one big blob, split it into smaller chunks, and only re-upload the chunks that actually changed. If you split naively at fixed byte offsets (every 4MB, say), a single byte inserted at the start of the file shifts every subsequent chunk boundary by one byte — so EVERY chunk after the edit "looks different" even though nothing in them really changed. That defeats the purpose entirely. The real trick is **content-defined chunking**: use a rolling hash (like Rabin fingerprinting) to decide chunk boundaries based on the actual bytes seen, not a fixed offset counter. This means when you insert a byte near the start of the file, the algorithm finds the same "this pattern of bytes = boundary" markers later in the file, and only the chunk(s) actually touched by your edit look different. Everything after that point re-aligns and is recognized as identical to before, so only the truly-changed chunk needs to be uploaded (see 035-chunked-upload-multipart-upload.md for how those chunks then get uploaded in parallel, and 013-content-addressable-storage-deduplication.md for how the chunk's own hash becomes its storage address, deduplicating identical chunks across ALL your files, not just within one file).

Last piece: what happens if you edit the same file offline on your laptop AND your phone, and both come back online? There's no way to know which edit is "right" — they're just two different, equally valid versions of the file that diverged. Silently picking one and discarding the other is how people lose work and stop trusting the sync tool. So instead, sync clients detect the conflict (comparing version markers, not just wall-clock timestamps, since clocks lie) and keep BOTH copies — renaming one to something like `file (conflicted copy from Bob's laptop).txt` — and let the human decide what to do with the fork.

---

## PART 2 — THE FILE SYNC ARCHITECTURE DIAGRAMS

### Happy Path: Local Edit → Watcher → Chunk Diff → Upload

```
Local machine                         Sync Client                        Cloud Storage
──────────────                        ───────────                        ─────────────

User edits report.pdf
(2.1 GB, was already synced)
  |
  | write() syscalls hit disk
  v
Kernel-level watcher fires:
  Linux:   inotify IN_MODIFY event
  macOS:   FSEvents kFSEventStreamEventFlagItemModified
  Windows: ReadDirectoryChangesW FILE_ACTION_MODIFIED
  latency: <10ms from write() to event delivery
                                        |
                                        | event queued, debounced ~200-500ms
                                        | (batches rapid successive writes from
                                        |  the same save operation into ONE sync pass)
                                        v
                                  Read local manifest for report.pdf:
                                    chunk_001: hash=a1f9... (4.1 MB)
                                    chunk_002: hash=88bc... (3.9 MB)
                                    chunk_003: hash=2d7e... (4.3 MB)   <- edited region
                                    chunk_004: hash=f001... (4.0 MB)
                                    ... (total ~500 chunks for 2.1GB file)

                                  Re-chunk file with rolling hash (Rabin
                                  fingerprint), compute new chunk hashes:
                                    chunk_001: hash=a1f9... (UNCHANGED)
                                    chunk_002: hash=88bc... (UNCHANGED)
                                    chunk_003: hash=9c44... (CHANGED! was 2d7e...)
                                    chunk_004: hash=f001... (UNCHANGED)

                                  Diff against last-known manifest:
                                  → only chunk_003 differs
                                        |
                                        | PUT chunk_003 only (4.3 MB, not 2.1 GB)
                                        v
                                                                        Object store:
                                                                        chunks/9c44e2f1...
                                                                        (content-addressed,
                                                                         see 013)
                                        |
                                        | Update remote manifest:
                                        | report.pdf → [a1f9,88bc,9c44,f001,...]
                                        v
                                                                        Manifest DB row updated
                                                                        version: v47 → v48

Result: 4.3 MB uploaded instead of 2.1 GB.
        ~99.8% bandwidth savings for this edit.
        Upload time at 10 Mbps: ~3.5 sec (vs ~28 minutes for full file)
```

### Delta Sync Internals: Content-Defined Chunking with a Rolling Hash

```
Fixed-offset chunking (BROKEN for small edits):
  Original: [AAAA|BBBB|CCCC|DDDD]   4-byte fixed chunks
  Insert 1 byte at start:
            [XAAA|ABBB|BCCC|CDDD]   EVERY chunk boundary shifted!
  → all 4 chunks look "new" → re-upload everything → delta sync provides
    ZERO benefit for insertions/deletions (only helps for in-place edits
    that don't change file length, which is rare)

Content-defined chunking (Rabin fingerprint rolling hash):
  Slide a window (e.g. 48 bytes) across the file, computing a rolling
  hash of the window at every byte offset.
  Declare a chunk boundary whenever: hash(window) & bitmask == target
  (e.g. bitmask picks the low 13 bits, giving an average chunk size of
   ~8 KB — 2^13 = 8192)

  Original:  ...xyz|BOUNDARY|def...       (boundary determined by CONTENT,
                                            not byte position)
  Insert 1 byte anywhere before "def":
             ...Xxyz|BOUNDARY|def...      (rolling hash re-finds the SAME
                                            boundary pattern right after
                                            "xyz" — because boundary
                                            detection only looks at local
                                            byte content, not absolute offset)
  → only the chunk(s) between the edit and the next re-found boundary
    are new; everything after re-aligns to identical chunks
  → this is exactly how rsync's rolling-checksum algorithm and tools like
    restic/BorgBackup achieve efficient incremental sync/backup

Typical chunk size targets: 2-8 MB (Dropbox-style block sync) down to
2-64 KB (dedup-heavy backup tools) — the tradeoff is manifest overhead
(more, smaller chunks = more hash entries in the manifest = more requests)
vs. dedup granularity (smaller chunks = more precise change detection,
better cross-file dedup hit rate).
```

### Edge Case: Offline Conflict — Same File Edited on Two Devices

```
T0: report.pdf synced on both devices, version_vector = {laptop: 3, phone: 2}

T1: Laptop goes offline (airplane mode). User edits report.pdf locally.
    Local version_vector bumped: {laptop: 4, phone: 2}
    (increments ONLY the local device's counter — no coordination possible
     while offline, by definition)

T2: Phone (still online... wait, phone was already offline too, say on a flight)
    Phone ALSO edits report.pdf independently while offline.
    Local version_vector bumped: {laptop: 3, phone: 3}

T3: Both devices come back online, both try to push report.pdf

Server compares incoming version vectors against its stored one ({laptop:3, phone:2}):
  Laptop's vector {laptop:4, phone:2}: laptop counter ahead, phone counter
    equal → this is a clean, LINEAR update (nothing lost) → ACCEPT,
    server state becomes {laptop:4, phone:2}

  Phone's vector {laptop:3, phone:3}: phone counter ahead, but laptop
    counter is BEHIND what the server now has (3 < 4) → the two edits
    are CONCURRENT / DIVERGENT, neither vector dominates the other
    → this is a genuine conflict, not just a race to save first

Resolution (NOT "last write wins" — that silently destroys one edit):
  1. Server/client keeps the version that arrived/was already accepted:
       report.pdf  (laptop's edit, already applied)
  2. The conflicting version is preserved under a new name:
       report (conflicted copy from Phone, 2024-06-01).pdf
  3. Both files are fully synced to BOTH devices — nobody silently
     loses data, the human decides whether to merge, keep one, or
     keep both permanently.

Why not just compare last-modified timestamps instead of version vectors?
  Clocks drift and can be wrong (see 037-vector-clocks-write-conflict-detection.md) —
  a device with a clock 10 minutes fast would always "win" a timestamp
  comparison regardless of which edit actually happened first in reality.
  Version vectors track causality (who-saw-what), not wall-clock time,
  so they correctly detect "these are concurrent" vs "this one causally
  follows that one" without trusting any single clock.
```

---

## PART 3 — INTERNALS, IMPLEMENTATION, AND REAL NUMBERS

### File Watcher Setup (Linux inotify via Java)

```java
import java.nio.file.*;
import static java.nio.file.StandardWatchEventKinds.*;

public class SyncFolderWatcher {

    public void watch(Path syncRoot) throws IOException {
        WatchService watchService = FileSystems.getDefault().newWatchService();

        // Registers ONE inotify watch descriptor per directory (Linux limits
        // this — default max is 8192 watches system-wide via
        // /proc/sys/fs/inotify/max_user_watches; sync clients with 100K+
        // files often need to raise this via sysctl)
        Files.walk(syncRoot)
            .filter(Files::isDirectory)
            .forEach(dir -> {
                try {
                    dir.register(watchService, ENTRY_CREATE, ENTRY_MODIFY, ENTRY_DELETE);
                } catch (IOException e) {
                    log.warn("Failed to watch {}: falling back to periodic rescan", dir);
                }
            });

        while (true) {
            WatchKey key = watchService.take(); // blocks, NO polling/spinning
            for (WatchEvent<?> event : key.pollEvents()) {
                if (event.kind() == OVERFLOW) {
                    // Kernel event QUEUE overflowed (too many changes too fast,
                    // e.g. a git checkout touching 50,000 files at once).
                    // This is the #1 reason watchers miss events — MUST
                    // trigger a full reconciliation scan, not just log and move on.
                    scheduleFullRescan(syncRoot);
                    continue;
                }
                Path changed = ((Path) key.watchable()).resolve((Path) event.context());
                enqueueSyncTask(changed, event.kind());
            }
            key.reset();
        }
    }
}
```

### Content-Defined Chunking (Rabin-Karp Rolling Hash, Simplified)

```java
public class ContentDefinedChunker {

    private static final int WINDOW_SIZE = 48;       // bytes examined per hash
    private static final int AVG_CHUNK_BITS = 13;     // 2^13 = 8KB avg chunk size
    private static final long MASK = (1L << AVG_CHUNK_BITS) - 1;

    public List<Chunk> chunk(byte[] fileBytes) {
        List<Chunk> chunks = new ArrayList<>();
        int chunkStart = 0;
        RollingHash roller = new RollingHash(WINDOW_SIZE);

        for (int i = 0; i < fileBytes.length; i++) {
            long hash = roller.roll(fileBytes[i]); // O(1) update per byte,
                                                     // NOT re-hashing the whole window

            boolean isBoundary = (hash & MASK) == MASK && (i - chunkStart) > 2048;
            // min chunk size guard (2KB) prevents pathological tiny chunks
            // from noisy/random-looking data (e.g. already-compressed files)

            if (isBoundary || i == fileBytes.length - 1) {
                byte[] chunkData = Arrays.copyOfRange(fileBytes, chunkStart, i + 1);
                String sha256 = sha256Hex(chunkData); // content-address, see 013
                chunks.add(new Chunk(sha256, chunkData.length));
                chunkStart = i + 1;
            }
        }
        return chunks;
    }
}

// Manifest diff: compare old vs new chunk list by hash, upload ONLY misses
public List<Chunk> chunksNeedingUpload(List<Chunk> oldManifest, List<Chunk> newManifest) {
    Set<String> existingHashes = oldManifest.stream()
        .map(Chunk::hash).collect(Collectors.toSet());
    return newManifest.stream()
        .filter(c -> !existingHashes.contains(c.hash()))
        .toList();
}
```

### Reconciliation Fallback: Full Manifest Diff

```sql
-- When the watcher missed events (queue overflow, client was offline
-- for an extended period, or hit the OS watch-descriptor limit),
-- fall back to a full local-vs-remote manifest comparison.

-- Remote manifest (from last known sync state, stored server-side):
-- file_path            | chunk_hashes (JSON array)      | version | updated_at
-- /Docs/report.pdf      | ["a1f9...","88bc...",...]      | 47      | 2024-06-01T09:00:00Z
-- /Docs/budget.xlsx      | ["7c2e...","91aa...",...]      | 12      | 2024-05-28T14:20:00Z

-- Local rescan (walk every file, recompute a fast content digest):
-- 1. Compare mtime+size first (cheap short-circuit — if BOTH match the
--    last-known-synced values, skip re-chunking entirely, ~0 cost)
-- 2. If mtime/size differs (or is unknown after a long offline period),
--    re-run content-defined chunking and compare chunk-hash lists

-- Real numbers (illustrative, based on typical desktop sync client behavior):
--   Full rescan of 100,000 files, mostly unchanged: ~15-45 seconds
--     (dominated by stat() syscalls + reading manifest DB, not I/O of
--      file CONTENTS, since unchanged files are skipped via mtime+size)
--   Full rescan of 100,000 files, 5,000 genuinely changed: ~3-8 minutes
--     (re-chunking + hashing the changed subset)
--   Compare to real-time watcher-driven sync: near-instant (<1s) detection
--     per change, but ZERO coverage for changes made while the client
--     process wasn't running at all (laptop closed, app quit)

-- This is why a reconciliation scan ALSO always runs once at client
-- startup, regardless of watcher health — the watcher only covers the
-- window while the client process is alive and running.
```

---

## PART 4 — THE INTERVIEW CONVERSATION

**Interviewer:** "Design the sync engine for a Dropbox-like desktop client. A user has a 2GB folder of large files, and they make small edits throughout the day. How do you detect changes efficiently and avoid re-uploading entire files for every small edit?"

**You (architect answer):**

> "There are two separate problems here: detecting THAT something changed, and efficiently syncing WHAT changed, and I'd solve them differently.
>
> For detection, I use the OS's native file-watching API rather than polling — `inotify` on Linux, `FSEvents` on macOS, `ReadDirectoryChangesW` on Windows. The kernel pushes a notification the instant a watched file is created, modified, or deleted, typically within single-digit milliseconds. I debounce these events over a few hundred milliseconds, because a single 'save' in most applications triggers several rapid write syscalls, and I want to batch those into one sync pass rather than reacting to each one.
>
> For efficient sync of large files, I use content-defined chunking with a rolling hash — Rabin fingerprinting is the classic choice. I split each file into variable-length chunks based on local byte patterns rather than fixed byte offsets, specifically because fixed-offset chunking breaks catastrophically on insertions: shifting the file by even one byte shifts every subsequent chunk boundary, making every chunk after the edit look different even though the content is unchanged. With content-defined chunking, the rolling hash re-finds the same boundary pattern after the edit, so only the actually-modified chunk or two need to be re-uploaded — for a single-paragraph edit in a 500MB document, that's often a few megabytes instead of the whole file. Each chunk is content-addressed by its own hash, which also gives me deduplication for free across the user's entire file set, not just within one file.
>
> The operational concern I'd flag is watcher reliability. OS-level watchers have real limits — Linux's `inotify` has a system-wide max-watch-descriptor count, and the kernel's event queue can overflow if a huge number of files change in a very short window, like a `git checkout` touching tens of thousands of files at once. When that happens, the watcher silently drops events rather than erroring loudly, which means the sync client can miss changes. My mitigation is a two-part strategy: I always run a full reconciliation scan once at client startup regardless of watcher health, since the watcher only covers changes made while the process is alive, and I monitor for the specific 'overflow' event type from the watch API and trigger an immediate full-folder rescan when I see it, rather than trusting the watcher's event stream blindly."

---

## PART 5 — DECISION FRAMEWORK

### Change Detection & Sync Strategies

| Approach | How It Works | Tradeoff | Latency | Complexity | When It Fails |
|---|---|---|---|---|---|
| **OS file watcher (inotify/FSEvents/ReadDirectoryChangesW)** | Kernel pushes change notifications as they happen | Has per-OS limits (watch descriptor counts, event queue depth) | <10ms detection | Medium | Silently drops events on queue overflow or watch-limit exhaustion — needs a reconciliation fallback |
| **Periodic polling (rescan + compare mtime)** | Walk the tree on a timer, compare file metadata to last-known state | Simple, but change-detection latency = poll interval; wasteful CPU/IO on huge trees | Seconds to minutes (poll interval) | Low | Misses rapid changes between polls; doesn't scale past a few hundred thousand files |
| **Full-file re-upload (no chunking)** | Whenever a file changes, upload it whole | Simplest to implement; catastrophic bandwidth cost for large files with small edits | Proportional to file size | Low | Falls over completely once files exceed a few tens of MB with frequent small edits |
| **Fixed-offset chunking** | Split file into fixed-size blocks, hash each | Simple math, but ANY insertion/deletion shifts every later chunk boundary | Same as content-defined for pure overwrites; much worse for insert/delete | Low-Medium | Provides near-zero benefit for the most common real-world edit pattern (typing more text) |
| **Content-defined chunking (rolling hash)** | Chunk boundaries determined by local byte content, resilient to shifts | Requires implementing/tuning a rolling hash and boundary heuristics | Chunking: proportional to file size, but one-time per change; upload: proportional to CHANGED bytes only | Medium-High | Poorly tuned boundary parameters can produce pathologically tiny or huge chunks on certain data (e.g. already-compressed/encrypted files look "random") |

### When Full Delta Sync (Watcher + Content-Defined Chunking) Is Right

```
✓ Users regularly edit large files (documents, video projects, VM images,
  database dumps) where full re-upload would be wasteful
✓ Bandwidth is a real constraint (mobile connections, metered plans,
  large user base making frequent small edits)
✓ You control the client (desktop app) and can run a persistent watcher
  process — not just a stateless web upload form
✓ You want cross-file deduplication as a side benefit (shared chunks
  across near-duplicate files, e.g. versioned document exports)
```

### Skip Full Delta Sync When

```
✗ Files are small (a few hundred KB or less) — chunking overhead
  (manifest bookkeeping, multiple round trips) may exceed just
  re-uploading the whole file
✗ It's a web-based upload flow with no persistent client process —
  there's no watcher to hook into; simple whole-file or basic
  multipart upload (035) is more appropriate
✗ Files change completely on every edit (e.g. re-exported/re-encoded
  media where the whole binary differs byte-for-byte) — chunking buys
  nothing if nothing is actually shared with the previous version
✗ Engineering budget is tight and files are modest in size/frequency —
  a simpler timestamp-based "did this file change since last sync"
  check with whole-file upload may be an acceptable MVP
```

---

## QUICK REFERENCE CARD

```
CHANGE DETECTION (OS-native, no polling):
  Linux:   inotify            (IN_MODIFY, IN_CREATE, IN_DELETE, IN_Q_OVERFLOW)
  macOS:   FSEvents           (kFSEventStreamEventFlagItemModified)
  Windows: ReadDirectoryChangesW (FILE_ACTION_MODIFIED)
  → always pair with a full reconciliation scan at client startup

CONTENT-DEFINED CHUNKING:
  Rolling hash (Rabin fingerprint) over a sliding window (~48 bytes)
  Boundary when: hash(window) & bitmask == target
  Avg chunk size ~= 2^(mask bits)  (e.g. 13 bits → ~8KB average)
  Enforce a MIN chunk size to avoid pathological tiny chunks

SYNC FLOW:
  1. Watcher fires → debounce ~200-500ms
  2. Re-chunk changed file (content-defined)
  3. Diff chunk hash list vs last-known manifest
  4. Upload ONLY new/changed chunks (chunk hash = storage address, see 013)
  5. Update manifest + version vector

CONFLICT RESOLUTION:
  Use version vectors (per-device counters), NOT wall-clock timestamps
  Concurrent/divergent vectors → keep BOTH:
    file.txt
    file (conflicted copy from <Device>, <date>).txt
  Never silently discard an edit ("last write wins" = data loss)

RECONCILIATION FALLBACK TRIGGER:
  - Watcher OVERFLOW event received
  - Watch-descriptor limit hit (e.g. Linux max_user_watches exhausted)
  - Client was offline/closed for an extended period
  → full local-vs-remote manifest diff, short-circuited by mtime+size match
```

---
