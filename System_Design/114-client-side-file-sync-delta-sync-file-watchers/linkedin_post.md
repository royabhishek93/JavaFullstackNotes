# Client-Side File Sync: Watchers, Delta Sync & Conflict Resolution — LinkedIn Post

## Post Text (copy-paste ready)

You edit 4KB in a 2GB file. A naive sync client re-uploads all 2GB. Here's how Dropbox avoids that 99.8% waste.

- **Stop polling, start listening**: `inotify` (Linux), `FSEvents` (macOS), `ReadDirectoryChangesW` (Windows) push change events to the client in <10ms — no timer loop re-scanning 200,000 files every 30 seconds.
- **Fixed-size chunking is a trap**: split a file into fixed 4-byte (or 4MB) blocks and insert ONE byte at the start — every chunk boundary shifts, every chunk "looks new," and you get ZERO delta-sync benefit for the most common edit pattern there is: typing more text.
- **Content-defined chunking fixes it**: a rolling hash (Rabin fingerprint) finds chunk boundaries based on local byte content, not absolute offset — so a real 4.3MB chunk uploads instead of the full 2.1GB file. That's a 3.5-second upload instead of 28 minutes on a 10 Mbps line.
- **Watchers silently fail**: Linux's default `inotify` watch limit is 8,192 directories, and the kernel's event queue can OVERFLOW during a `git checkout` touching 50,000 files — dropping events with no error. Every serious client runs a full reconciliation scan at startup regardless, because the watcher only covers changes made while the process is alive.
- **Never use "last write wins" for conflicts**: two devices editing offline produce version vectors like `{laptop:4, phone:2}` vs `{laptop:3, phone:3}` — neither dominates the other, so it's a genuine conflict. The fix is keeping BOTH files (`report (conflicted copy from Bob's laptop).txt`), never silently discarding one. Clocks lie; causality (version vectors) doesn't.

Swipe → to see: the watcher pipeline, the rolling-hash chunk diff, the version-vector conflict diagram, and the full decision table.

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
How Dropbox syncs a 4KB edit in a 2GB file without re-uploading 2GB. Watchers, rolling-hash chunking, version vectors — full breakdown 👇

### Variant B — Long (400-600 chars)
Naive file sync re-uploads an entire file on any edit. Dropbox doesn't — it uses OS-level watchers (inotify/FSEvents/ReadDirectoryChangesW) to detect changes in under 10ms, then content-defined chunking with a rolling hash to upload only the bytes that actually changed — turning a 2.1GB re-upload into a 4.3MB one. The catch: fixed-offset chunking breaks completely on inserts, watch queues silently overflow at scale, and conflict resolution needs version vectors, not timestamps, or you'll silently destroy user edits. Full breakdown of the architecture, the failure modes, and the exact interview answer in the carousel.

---

## Best Time to Post
Tuesday or Wednesday, 8:00–9:30 AM IST (before the Indian tech workday starts — highest engineer scroll time on LinkedIn) or 7:30–9:00 PM IST (post-work wind-down scroll).

## Engagement Hook
"Have you ever had a sync tool silently overwrite one of your edits? What did you do after that — did you trust it again?"
