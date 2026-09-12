# Data Privacy in System Design: PII, GDPR & Encryption — LinkedIn Post

## Post Text (copy-paste ready)

Your TLS was perfect. Your unencrypted backup tape is why the breach still happened.

- Data minimization isn't "services promise not to read fields they don't need" — it's structural: if a service can't see it, a bug can't leak it.
- A tokenization vault stores the real card number ONCE. Everyone else — order records, analytics, fraud checks — only ever sees a meaningless token. Breach the analytics warehouse, attacker gets tokens, not card numbers.
- "Delete my account" is not one DELETE statement. It's an orchestrated saga hitting your primary DB, search index, cache, CDN, analytics warehouse, and object storage — with cold backups tracked for purge on their natural retention expiry, because you literally cannot edit a backup tape in place.
- Encryption in transit (TLS) and encryption at rest are two different threats. Teams that nail TLS everywhere still get breached because the disk itself was never encrypted.
- Envelope encryption via KMS: the master key never leaves the KMS. You only ever handle short-lived data encryption keys — so rotating the master key later never means re-encrypting your entire dataset.

Swipe → to see the tokenization vault flow, the GDPR deletion saga, envelope encryption, and the full data-classification decision tree.

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
TLS everywhere ≠ data protected. Here's how tokenization vaults + GDPR deletion sagas + envelope encryption actually work. 🎥👇

### Variant B — Long (400-600 chars)
A team encrypts every network hop with TLS, feels done, and still gets breached — because the disk was never encrypted, and a backup tape walks out the door in plaintext. This is the #1 gap in real data-privacy architectures.

In this post: why "delete my account" is an orchestrated saga (not one DELETE), how a tokenization vault shrinks your PCI-DSS scope from 30+ services down to one, and how envelope encryption via KMS means your master key never leaves the vault — so rotating it never requires re-encrypting your entire dataset.

If you're prepping for system design interviews, this is a recurring theme. Save it.

---

## Best Time to Post
Tuesday or Wednesday, 8:00–9:30 AM IST (before the workday starts, when Indian tech engineers are scrolling LinkedIn over chai/coffee).

## Engagement Hook
"Has your team ever assumed 'we're encrypted' because of TLS, only to realize the data at rest was never covered? Drop your story below."
