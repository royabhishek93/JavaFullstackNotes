# Data Privacy in System Design: PII, GDPR & Encryption — YouTube Script
Duration: ~10 min | Target: Engineers 3–10 YOE

## HOOK (0:00–0:30)

"Your team encrypted every request with TLS. Every single hop. You did everything right... except one thing — you never encrypted the disk. Then someone walks off with a backup tape, or worse, a storage bucket gets misconfigured to public — and every credit card number, every government ID, every medical note you ever stored is sitting there in plain text, for anyone to read.

That's not a hypothetical. That's the single most common data-privacy failure in production systems — teams that believe 'we handle encryption' because TLS is everywhere, while the actual data at rest is completely naked.

In the next ten minutes, I'm going to show you how real systems architect around this — tokenization vaults, GDPR's 'right to be forgotten,' envelope encryption with KMS — the stuff that actually shows up in a senior system design interview."

[Screen cue: split screen — left side shows a padlock icon on a network cable labeled "TLS ✓", right side shows an open, unlocked disk icon labeled "At Rest ✗" with a red X. Title card: "Data Privacy in System Design."]

## THE PROBLEM (0:30–2:00)

"Let's start with something that has nothing to do with computers: a hospital's medical records department.

Not every staff member who can walk past a filing cabinet should be able to read every patient's full history. The billing clerk needs the insurance code and the total charge — they have zero legitimate reason to read the psychiatric consultation notes sitting in the same file. A well-run hospital doesn't rely on everyone's good judgment. It physically separates what each role can see.

That's the core idea behind data minimization and field-level protection: you architect the system so that services which don't need a piece of sensitive data structurally CANNOT see it — not 'we trust every downstream service to voluntarily ignore the fields it shouldn't read.' Trust is not a security control.

Now here's where it gets messy. Imagine that same patient, months later, formally requests: 'delete my records — all of them, everywhere, including whatever backup tapes you keep in storage.' Sounds simple, right? Except the records exist in at least four places: the active filing cabinet, the archive warehouse, a backup microfilm reel from last year's disaster-recovery drill, and a research database that copied an 'anonymized-looking' extract two years ago.

Deleting from just the first place doesn't satisfy the request. And this is EXACTLY the operational nightmare GDPR's 'right to be forgotten' creates for real software systems. A user's data was almost certainly copied into a cache, a search index, an analytics warehouse, a nightly backup, and some third-party email-marketing tool's contact list. A genuine deletion has to propagate — verifiably — to every single one of those copies. Not just the primary database row."

[Screen cue: draw a single user icon in the center, with dotted lines radiating out to five boxes labeled "Primary DB," "Search Index," "Cache," "Analytics Warehouse," "Third-Party Marketing Tool" — each box glowing red to represent "still has the data."]

## THE SOLUTION (2:00–5:00)

"So how do real systems solve this? Three big architectural moves.

Move one: tokenization. Instead of a sensitive value — a credit card number, a government ID — flowing through and being stored in every service that touches it, you put ONE tightly-controlled vault in front of it. The vault stores the real sensitive value exactly once, and hands every other service a meaningless, randomly generated token instead — something like 'tok_9f8a3b2c.' Your order records, your logs, your analytics events — they all reference that token, never the real card number.

Here's why that's powerful: if your analytics warehouse gets breached, the attacker walks away with tokens. Worthless tokens. They cannot be reversed into real card numbers without access to the one vault that holds the mapping. And it elegantly solves the 'delete everywhere' problem too — you delete ONE row in the vault, and instantly, every token across every downstream system becomes permanently meaningless. You don't need to hunt down and scrub the real card number from a dozen different databases, because it was never there in the first place.

Move two: the deletion orchestrator, or saga. When a user clicks 'delete my account,' that is not a single DELETE statement. It's a workflow. The orchestrator fires off deletion or anonymization events to every system that might hold that user's data: the primary DB gets a delete plus a tombstone for downstream CDC consumers, the search index gets a document delete, the cache gets key invalidation, object storage deletes uploaded files and avatars, CDN edge caches get purged. The analytics warehouse either anonymizes the rows or schedules a purge on the next batch cycle — some systems keep aggregate stats but strip the PII join-key. And backup snapshots — these CANNOT be edited in place. You can't reach into a backup tape and delete one row. So instead, that user gets tracked in a 'pending deletion' list and purged when that backup naturally expires and rotates out of retention. This is commonly the hardest, slowest part of a real erasure request.

And critically — the orchestrator writes a confirmation and audit log entry: 'user 12345 erasure completed across N systems on this date.' GDPR requires you to DEMONSTRATE compliance, not just make a good-faith attempt. That audit trail is a required system component, not an afterthought.

Move three: encryption, and this is where the TLS-versus-disk gap I mentioned in the hook actually gets fixed. Encryption in transit — TLS — protects data as it moves across a network, from a man-in-the-middle reading it on the wire. Encryption at rest protects data sitting on a disk, from being read if that disk — or a backup, or a decommissioned drive — is stolen or improperly accessed. You need BOTH, and the standard way to do 'at rest' properly at scale is envelope encryption through a KMS.

Here's how that actually works: the KMS holds a master key that never leaves the KMS or HSM — ever. Your app requests a 'data encryption key,' or DEK. The KMS generates one and hands it back TWICE — once in plaintext, once encrypted under the master key. Your app uses the plaintext DEK to encrypt the actual data, then immediately discards the plaintext version, storing only the ENCRYPTED DEK next to the encrypted data. To decrypt later, you send that encrypted DEK back to the KMS, the KMS decrypts it using the master key — which never left the KMS — and now your app has a plaintext DEK again to decrypt the real data.

The beautiful side effect: the master key is never exposed to application code, never transmitted in plaintext over a network. And when you eventually need to rotate the master key, you don't have to re-encrypt your entire dataset — you only re-wrap the DEKs. That's the difference between a five-minute key rotation and a multi-day re-encryption job across terabytes of data."

[Screen cue: live-draw the envelope encryption flow — a box labeled "KMS / HSM" with a master key icon locked inside that never moves, an arrow out labeled "DEK (plaintext) + DEK (encrypted)," then show the plaintext DEK encrypting a data blob and then being discarded, leaving only the encrypted DEK stored alongside the encrypted data.]

## DEEP DIVE — WHERE ENGINEERS GET IT WRONG (5:00–8:00)

"Now let's talk about where teams actually mess this up, because this is where interview follow-up questions live.

Trap one: trusting good behavior instead of structural enforcement. A lot of teams say 'our downstream services just don't read the sensitive fields.' That's not data minimization — that's hoping. If a service technically CAN see the psychiatric notes, eventually something will read them — a bug, a careless log statement, a new engineer who doesn't know the convention. Structural separation — literally not sending the field, or field-level encryption that only specific services hold keys for — is the only version of this that actually holds up.

Trap two — and this is the hook, so let's go deeper. Teams roll out TLS everywhere, feel great about it, and never actually check whether the disk itself is encrypted. Then a backup tape walks out the door, or someone leaves an S3 bucket public, and it turns out 'encryption' only ever covered the network hop, never the storage layer. You need to explicitly verify BOTH layers are covered — they protect against completely different threats, and having one does not imply the other.

Trap three: treating deletion as a single DELETE statement. If your 'right to be forgotten' flow is just `DELETE FROM users WHERE id = ?`, you have satisfied approximately none of the actual regulatory requirement, because the data is still sitting in your search index, your cache, your analytics warehouse, and your backups. You need the orchestrator pattern, full stop.

Trap four, and this one trips up even senior engineers: forgetting that backup snapshots cannot be edited in place. You cannot open a three-month-old backup and delete one row from it. The correct pattern is a 'pending deletion' tracking list, and the actual purge happens naturally when that backup rotates out of its retention window. If your design assumes you can synchronously scrub backups, that's a red flag in an interview.

Trap five: no audit trail. GDPR doesn't just want you to delete the data — it wants you to be able to PROVE, on demand, that you deleted it, when, and across which systems. If your architecture can't produce that proof, you've built half a solution.

Trap six: putting regulated data — card numbers, government IDs — into 'a column with an encryption flag' in your main application database, instead of isolating it into a separate vault or system boundary. This is a classic compliance-scope mistake. The moment your regular application database contains a raw card number, your ENTIRE application — every service that touches that table — falls inside PCI-DSS audit scope. Tokenization isn't just a security nicety, it's how you keep your compliance boundary small.

Trap seven: treating all data the same. Not everything needs field-level encryption and strict access logging. Public catalog data needs nothing. Internal dashboards need access control, nothing more. Standard PII — name, email, address — needs encryption at rest plus a GDPR-compliant deletion path. Sensitive PII — health records, precise geolocation — needs field-level encryption specifically, not just whole-disk encryption. And regulated data — card numbers, health records under HIPAA — needs full isolation via tokenization or vaulting. Encrypting everything uniformly either wastes engineering effort on data that didn't need it, or worse, gives you false confidence that your truly sensitive fields are protected the same way your blog post titles are.

Let's talk real numbers, because these come up in interviews too. A tokenization vault lookup typically costs less than 5 milliseconds — and critically, that hop only gets added at the actual point of card-charge processing, not on every single request that merely references the token elsewhere in your system. GDPR's erasure SLA — the regulation says 'without undue delay,' which in practice is commonly implemented as a 30-day maximum, and that's precisely why you need an asynchronous, saga-based deletion workflow rather than a synchronous one — some downstream systems, like cold backups, genuinely take time to purge on their own retention cycle. And envelope encryption overhead: AES-256 encrypting a few-hundred-byte field is sub-millisecond CPU cost. The dominant cost is actually the KMS round-trip to unwrap a DEK — commonly a few milliseconds — which is why production systems cache the unwrapped DEK per key rather than calling the KMS on every single read."

[Screen cue: comparison table on screen — rows: "Data Type" vs "Protection" vs "Pattern" — Public / Internal / PII / Sensitive PII / Regulated, each row highlighting escalating protection, with a small red "TRAP" flag next to "uniform encryption" crossed out.]

## REAL WORLD (8:00–9:30)

"Let's ground this in real-scale systems.

Think about a payments platform like PhonePe or Paytm processing tens of millions of card-linked transactions a month. Their tokenization vault is handling something on the order of 50 million tokenization lookups monthly, each resolving in under 5 milliseconds at p99 — and because the raw card number lives in exactly ONE isolated vault, their PCI-DSS audit scope shrinks from potentially 30-40 services that touch an order record down to just that one vault system. That's not a small win — that's the difference between a multi-month compliance audit and a contained, weeks-long one.

Now think about a large e-commerce platform like Flipkart handling a deletion request under India's DPDP Act or GDPR for EU customers. A single account deletion might need to propagate across 10 to 12 distinct systems — primary database, search index, recommendation cache, analytics warehouse, CDN edge caches, third-party marketing integrations — all orchestrated through a saga, with the entire workflow required to complete within that 30-day regulatory window, and every step logged for audit.

And think about a food delivery platform like Zomato or Swiggy storing customer addresses and phone numbers as PII. They'd typically run envelope encryption through something like AWS KMS — encrypting on the order of hundreds of millions of address and contact records — where the actual AES encrypt/decrypt cost is sub-millisecond, but they cache unwrapped DEKs aggressively, because at their read volume, even a few-millisecond KMS round-trip per request, multiplied across tens of thousands of requests per second, would become a real bottleneck."

[Screen cue: three company logo placeholders side by side — "PhonePe/Paytm: <5ms vault lookup, 50M+ tokenizations/month" / "Flipkart: 10-12 systems per deletion saga, 30-day SLA" / "Zomato/Swiggy: KMS envelope encryption, DEK caching at scale."]

## OUTRO + NEXT EPISODE (9:30–10:00)

"So — data minimization through structural separation, tokenization vaults to shrink your compliance blast radius, deletion sagas that actually honor 'right to be forgotten' across every copy of your data, and envelope encryption so a stolen master key never happens because the master key never left the KMS in the first place. That's the real architecture behind data privacy at scale.

If this helped you think about your own system differently, hit subscribe — I'm building out this entire system design series episode by episode. Next up: we're going to look at service mesh mTLS and how it automatically covers encryption-in-transit for every internal service-to-service hop, without every team having to remember to configure TLS themselves. See you in the next one."

[Screen cue: end card with subscribe button animation and a teaser thumbnail for "Service Mesh mTLS — Encrypting Every Internal Hop."]
