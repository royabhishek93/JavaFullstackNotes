# Data Privacy in System Design: PII, GDPR, and Encryption At Rest/In Transit
### How you design a system that can prove, on demand, exactly who touched a user's data and forget them on request

---

## PART 1 — THE STUDENT CONVERSATION

Imagine a hospital's medical records department. Not every staff member who can walk past a filing cabinet should be able to read every patient's full history — the billing clerk needs to see the insurance code and the total charge, but has no legitimate reason to read the psychiatric consultation notes in the same file. A well-run hospital doesn't rely on everyone's good judgment; it physically separates what each role can see, redacting or omitting fields that role doesn't need. This is the core idea behind **data minimization and field-level protection**: a system should be architected so that services which don't need a piece of sensitive data structurally CANNOT see it, rather than trusting every downstream service to voluntarily ignore fields it shouldn't read.

Now imagine a patient, months later, formally requests: "delete my records — all of them, everywhere, including whatever backup tapes you keep in storage." This sounds simple until you realize the hospital's records exist in at least four places: the active filing cabinet, the archive warehouse, a backup microfilm reel from last year's disaster-recovery drill, and a research database that copied an anonymized-looking extract two years ago. Deleting "the record" from just the first place doesn't satisfy the request — and this is exactly the operational nightmare that **GDPR's "right to be forgotten"** creates for real software systems: a user's data was likely copied into a cache, a search index, an analytics warehouse, a nightly backup, and a third-party email-marketing tool's contact list, and a genuine deletion has to propagate — verifiably — to every single one of those copies, not just the primary database row.

The practical engineering answer many production systems converge on is **tokenization**: instead of a piece of sensitive data (a credit card number, a government ID) flowing through and being stored in every service that touches it, a single, tightly-controlled **vault** stores the real sensitive value ONCE, and hands every other service a meaningless, randomly-generated **token** that stands in for it everywhere else in the system — order records, logs, analytics events all reference "token: tok_9f8a3b2c" instead of the real card number. If a downstream analytics database gets breached, the attacker gets tokens, not credit card numbers — the tokens are worthless without access to the one vault that can reverse them. This also elegantly solves the "delete everywhere" problem for the sensitive value itself: deleting the ONE row in the vault instantly makes every token across every other system permanently meaningless, without needing to hunt down and scrub every copy of the actual card number.

Finally, **encryption** operates at two different layers with two different threat models: **encryption in transit** (TLS) protects data as it MOVES across a network from being read by someone intercepting the wire; **encryption at rest** protects data sitting on a disk from being read if that disk (or a backup, or a decommissioned drive) is physically stolen or improperly accessed. A common, subtle real-world gap: a system fully encrypts data in transit between every service (TLS everywhere) but stores it unencrypted on disk — meaning a stolen backup tape or a misconfigured, publicly-readable storage bucket exposes everything in plaintext despite the team believing they had "encryption" fully handled.

---

## PART 2 — THE DATA PRIVACY ARCHITECTURE DIAGRAMS

### Tokenization Vault: Sensitive Data Touches Exactly One System

```
Checkout Service                    Tokenization Vault              Downstream Systems
─────────────────                    ───────────────────              ───────────────────
User submits card:
4111-1111-1111-1111
        │
        │ POST /tokenize
        v
                              ┌──────────────────────────┐
                              │  VAULT (isolated, tightly  │
                              │  access-controlled, often  │
                              │  a separate compliance      │
                              │  boundary — PCI-DSS scope   │
                              │  is contained HERE, not      │
                              │  spread across your stack)   │
                              │                              │
                              │  real card number ←→ token   │
                              │  4111...1111 ←→ tok_9f8a3b2c │
                              └──────────────┬───────────────┘
                                             │ returns token only
        │<────────────────────────────────────
        │  tok_9f8a3b2c
        v
Order record stores:                                        Analytics warehouse,
  { orderId: 789,                                            fraud-check service,
    cardToken: "tok_9f8a3b2c" }  ─────────────────────────>  order-history service
  (the REAL card number never                                ALL reference the SAME
   leaves the vault again except                              token — none of them
   for the actual payment processor                           ever sees or stores
   charge call, which needs it)                                the real card number

Right-to-be-forgotten for the card number itself:
  DELETE FROM vault WHERE token = 'tok_9f8a3b2c'
  → every downstream reference to tok_9f8a3b2c is now permanently
    meaningless, with ZERO need to hunt down and scrub that value from
    the order table, the analytics warehouse, or any log file.
```

### GDPR Deletion Propagation Across a Real Distributed System

```
User clicks "Delete my account" (right to erasure request)
        │
        v
┌──────────────────────────────────────────────────────────────┐
│           DELETION ORCHESTRATOR (often a Saga —                │
│           see 048-saga-pattern-choreography-vs-orchestration)   │
└──────────────────────────────────┬───────────────────────────┘
        │                          │                          │
        v                          v                          v
Primary DB:                Search Index (ES):          Cache (Redis):
DELETE user row +          DELETE document by            invalidate/expire all
tombstone for CDC          userId (see 014)              keys for this userId
consumers (008)                  │                              │
        │                        v                              v
        v                 Analytics Warehouse:            CDN edge caches:
Object Storage (S3):      mark rows anonymized OR         purge any cached
delete user's uploaded    schedule for purge on           user-specific
files/avatars              next batch cycle (some          responses
        │                  systems keep AGGREGATE
        v                  stats but strip the PII
Backup Snapshots:          join-key)
CANNOT be edited in
place — instead, tracked
in a "pending deletion"
list and purged when that
backup naturally expires/
rotates out of retention
(commonly the hardest,
slowest-to-satisfy part
of a real erasure request)
        │
        v
Confirmation + audit log entry: "user 12345 erasure request completed
across N systems on [date]" — GDPR requires demonstrable compliance,
not just a good-faith attempt, so this audit trail is itself a
required system component, not an afterthought.
```

### Encryption at Rest vs In Transit — Two Different Threats

```
        Client                    TLS 1.3                    App Server
  ─────────────────────────────────────────────────────────────────────
         │  (in transit: protects against a network eavesdropper /
         │   man-in-the-middle reading the data as it crosses the wire)
         │
                                                        App Server
                                                             │
                                                             │  writes to disk
                                                             v
                                                   ┌──────────────────┐
                                                   │  Encrypted Disk /  │
                                                   │  Encrypted Column   │  ← at rest:
                                                   │  (AES-256, via a     │    protects against a
                                                   │  KMS-managed key)    │    stolen disk, an
                                                   └──────────────────┘    improperly-public
                                                                            storage bucket, or a
                                                                            decommissioned drive
                                                                            being read directly

Envelope encryption (how the KMS key relationship actually works):
  1. KMS holds a master key, NEVER leaves the KMS/HSM
  2. App requests a "data encryption key" (DEK) — KMS generates one,
     returns it PLUS that same DEK encrypted under the master key
  3. App uses the plaintext DEK to encrypt the actual data, then
     DISCARDS the plaintext DEK, storing only the ENCRYPTED DEK
     alongside the encrypted data
  4. To decrypt later: send the encrypted DEK back to KMS, KMS decrypts
     it using the master key (which never left KMS), app uses the
     now-plaintext DEK to decrypt the actual data
  → the master key is never exposed to application code or transmitted
    over the network in plaintext, and rotating the master key doesn't
    require re-encrypting all your data, only re-wrapping the DEKs.
```

---

## PART 3 — INTERNALS AND REAL NUMBERS

### Data Classification — Not All Data Needs the Same Protection

```
PUBLIC          — product catalog, public blog posts
                   → no special handling required

INTERNAL         — internal metrics dashboards, non-sensitive configs
                   → access control, no encryption mandate beyond baseline

PII (Personally  — name, email, address, phone number
Identifiable      → encryption at rest, access logging, subject to
Information)         GDPR/CCPA deletion & export rights

SENSITIVE PII /  — government ID, health records, precise geolocation
SPECIAL CATEGORY  → field-level encryption, strictest access controls,
                     often a LEGAL requirement for extra consent

REGULATED         — credit card numbers (PCI-DSS), health data (HIPAA)
                   → tokenization/vaulting to shrink compliance scope,
                     dedicated audit trails, often a SEPARATE, isolated
                     system boundary rather than "a column with an
                     encryption flag" in the main application database
```

### Real Numbers

```
Tokenization vault lookup: typically <5ms, an extra network hop added
  only at the point of actual card-charge processing — NOT on every
  request that merely references the token.
GDPR erasure request SLA: the regulation requires a response "without
  undue delay," commonly interpreted/implemented as a 30-day maximum —
  which is precisely why a DELETION ORCHESTRATOR / saga-based workflow
  (rather than a single synchronous DELETE) is the realistic
  architecture: some downstream systems (cold backups) genuinely take
  time to purge on their own retention cycle.
Envelope encryption overhead: AES-256 encrypt/decrypt of typical field-
  sized data (a few hundred bytes) is sub-millisecond CPU cost; the
  KMS round-trip to unwrap a DEK is the dominant cost, commonly a few
  milliseconds, and is cached per-DEK to avoid a KMS call on every read.
```

---

## PART 4 — THE INTERVIEW CONVERSATION

**Interviewer:** "You're designing a payments system that stores credit card numbers and is subject to GDPR. How do you architect data handling so a security breach in your analytics warehouse doesn't leak card numbers, and so you can fully honor a user's deletion request?"

**You (architect answer):**

> "The first architectural decision is to never let the raw card number propagate beyond the minimum system that legally needs it. I'd introduce a tokenization vault: the card number is submitted once, stored in a tightly access-controlled, isolated vault, and every other service in the system — order records, the analytics warehouse, fraud checks — only ever sees an opaque token that references it. That means if the analytics warehouse is breached, the attacker gets meaningless tokens, not card numbers, and it also shrinks my PCI-DSS compliance scope down to just the vault, rather than every service that happens to touch an order record.
>
> For GDPR erasure, I'd treat 'delete this user' as an orchestrated, multi-step workflow — similar to a saga — rather than a single DELETE statement, because the user's data genuinely exists in multiple places: the primary database, the search index, caches, the analytics warehouse, object storage for any uploaded files, and cold backups that can't be edited in place. Deleting the vault's card-token mapping alone instantly invalidates every downstream token reference with no further cleanup needed there, which is a nice side benefit of the tokenization design. For the rest, I'd have the orchestrator fire deletion/anonymization events to each downstream system, track completion, and explicitly account for cold backups being purged on their own retention cycle rather than pretending we can edit an already-written backup tape — and I'd keep an audit log proving the request was actually completed across every system, since GDPR compliance requires demonstrating this, not just attempting it in good faith.
>
> For everything at rest, I'd use envelope encryption via a KMS: the master key never leaves the KMS/HSM, application services only ever handle short-lived, per-record data encryption keys, which also means rotating the master key later doesn't require re-encrypting the entire dataset."

---

## PART 5 — DECISION FRAMEWORK

| Data Type | Protection Required | Architecture Pattern |
|---|---|---|
| **Regulated (card numbers, gov IDs)** | Maximum: isolate, don't let it propagate | Tokenization vault; keep the real value in exactly one system |
| **Sensitive PII (health, precise location)** | Field-level encryption + strict access logging | Encrypt specific columns/fields, not just the whole disk |
| **Standard PII (name, email, address)** | Encryption at rest + GDPR-compliant deletion path | Standard at-rest encryption + deletion propagation via orchestrator/saga |
| **Internal/non-sensitive** | Access control only | No special encryption mandate |
| **Any sensitive data in transit** | TLS everywhere, including service-to-service (not just edge) | Service mesh mTLS (116) covers internal hops automatically |
| **Deleting a user across a distributed system** | Orchestrated, verifiable, audited propagation | Deletion saga/orchestrator hitting DB, search index, cache, CDN, warehouse, and a tracked queue for backups pending natural expiry |
