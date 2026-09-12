# Advanced Scenario 2: Rotating Mesh-Wide Certificates at Scale (Thousands of Pods) Without Downtime

**Interviewer:** "How do you handle mesh-wide certificate rotation without downtime, at scale (thousands of pods)?"

**You (15-yr Architect):**

This is automatic in both Istio and Consul **by design** — that's the whole point of having a CA baked into the control plane. Certs are typically **short-lived** (Istio default ~24h, configurable).

## Rotation Flow (ASCII sequence)

```
  Control Plane CA               Envoy Sidecar
       |                              |
       | (well before cert expiry,    |
       |  e.g. at 2/3 of TTL)         |
       |<---- request new cert -------|
       |     (SDS - Secret Discovery  |
       |      Service)                |
       |----- new cert issued ------->|
       |                              |
       |                              |-- hot-swap cert in memory
       |                              |   NO restart, NO connection drop
```

The key term is **SDS (Secret Discovery Service)** — Envoy fetches certs dynamically via an API rather than reading a mounted file that requires a pod restart. This means rotation is invisible operationally, and it scales to thousands of pods because each sidecar independently pulls its own renewed cert on its own schedule — there's no single coordinated "rotate everything at once" event that could cause a thundering herd on the CA.

## The Harder Case: Root CA Rotation

Root CA rotation is much rarer, and requires more care — a **dual-root trust period**:

```
  Phase 1: Both OLD root and NEW root trusted simultaneously
           (leaf certs signed by either root are accepted)
  Phase 2: All sidecars have picked up leaf certs signed by NEW root
  Phase 3: Drop trust for OLD root entirely
```

Skipping the dual-trust period means any sidecar still holding an old-root-signed cert would suddenly fail mTLS handshakes the moment you cut over — a self-inflicted mesh-wide outage.

## Dual-Root-Trust Rotation (Sequence Diagram)

```
Old Root CA        New Root CA        Sidecar A (S1)       Sidecar B (S2)
     |                  |                    |                    |
     |=============== Phase 1 - dual trust ================================|
     |-- leaf cert (old-root signed) still trusted ------->|                |
     |                  |-- leaf cert (new-root signed) accepted too ----->|
     |                  |                    |-- mTLS handshake succeeds   |
     |                  |                    |   (either root trusted) -->|
     |                  |                    |                    |
     |=============== Phase 2 - rollover ===================================|
     |                  |-- S1 picks up new leaf cert (new-root signed) -->|
     |                  |                    |                    |
     |=============== Phase 3 - drop old trust =============================|
     |-- old root trust removed ---------------------------->|                |
     |-- old root trust removed --------------------------------------------->|
     |                  |                    |                    |
[any sidecar still on old-root cert would now fail handshake]
```
*(Full Mermaid source: see [mermaid-diagrams.md](mermaid-diagrams.md))*

## Why This Matters for the Interview

> "Leaf cert rotation is a solved, invisible problem at scale because of SDS and short TTLs. Root CA rotation is the one that requires an actual runbook and a transition window with dual trust — that's the detail that separates 'I've read about this' from 'I've actually rotated a root CA in production.'"

---
See also: [01-Concepts-Reference.md — Part 3: Security](01-Concepts-Reference.md#3-security-mtls-and-zero-trust), [`Diagram-03-mTLS-Handshake.drawio`](Diagram-03-mTLS-Handshake.drawio)
