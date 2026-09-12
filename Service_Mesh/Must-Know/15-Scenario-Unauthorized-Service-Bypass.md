# Scenario 4: Frontend Can Directly Call Payment Service, Bypassing Checkout

**Interviewer:** "Our security team found that `frontend` could directly call `payment-service`, bypassing `checkout-service`. How does that happen and how do we prevent it?"

**You (15-yr Architect):**

By default, in a freshly installed mesh, **every service can talk to every other service** — mTLS just encrypts, it doesn't restrict by default (until you set a default-deny policy). This is a real trap: people assume "we installed the mesh, so we're secure," but authorization rules are opt-in.

## Before the Fix (ASCII)

```
   checkout-service ------------> payment-service   (intended path)
   frontend --------------------> payment-service   (NOT intended, but ALLOWED by default!)
   recommendation ---------------> payment-service   (NOT intended, but ALLOWED by default!)
```

## After Applying Default-Deny + Explicit Allow (ASCII)

```
   checkout-service ---ALLOW (explicit intention)---> payment-service
   frontend --------x--DENY (default)----------------> payment-service
   recommendation ---x--DENY (default)----------------> payment-service
```

## How to Configure It

- **Consul:** create a `deny-all` intention on `payment-service`, then a specific `allow` intention for `checkout-service -> payment-service`.
- **Istio:** an `AuthorizationPolicy` with `action: ALLOW` scoped to a specific `source.principal` (the SPIFFE identity of `checkout-service`'s service account), plus cluster-wide default-deny via a `PeerAuthentication` + root-namespace `AuthorizationPolicy`.

## Why This Matters for the Interview

> "mTLS is necessary but not sufficient for zero trust — it gives you encryption and identity, but authorization (who is *allowed* to talk to whom) is a separate, opt-in configuration. Teams that enable mTLS and stop there have encrypted chaos, not zero trust."

This is also the exact concept demonstrated in the Consul tutorial demo — reducing `payment-service`'s allowed callers down to only `checkout-service` shrinks the attack surface (micro-segmentation), so even a critical vulnerability in `payment-service` can't be reached from arbitrary compromised pods.

---
See also: [01-Concepts-Reference.md — Part 3: Security](01-Concepts-Reference.md#3-security-mtls-and-zero-trust), [02-Trap-mTLS-Equals-Zero-Trust.md](02-Trap-mTLS-Equals-Zero-Trust.md), [`Diagram-04-Zero-Trust-Microsegmentation.drawio`](../Diagram-04-Zero-Trust-Microsegmentation.drawio)
