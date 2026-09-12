# Trap 2: "We Enabled mTLS Everywhere — That Means We've Achieved Zero Trust, Correct?"

**Interviewer:** "We enabled mTLS everywhere. That means we've achieved Zero Trust, correct?"

**Correct Answer: No — mTLS is necessary but not sufficient.**

```
  mTLS gives you:                       Zero Trust ALSO requires:
  ------------------                     ---------------------------
  - Encryption in transit                 - Authorization
  - Mutual identity verification          - (who is ALLOWED to talk
    (both sides prove who they are)         to whom - least privilege)

                                          This is a SEPARATE, OPT-IN
                                          configuration:
                                          - Istio: AuthorizationPolicy
                                          - Consul: Service Intentions
```

Plenty of teams enable mTLS, feel secure, and leave every service able to call every other service — that's **encrypted chaos**, not zero trust.

## The Full Picture

```
  Zero Trust = Strong Identity (mTLS)  +  Explicit Authorization (default-deny + allow-list)
                     |                                |
              "who are you,                   "are you ALLOWED to
               cryptographically               talk to THIS specific
               proven?"                        service?"
```

## Why This Trap Exists

"We enabled mTLS" sounds complete and final — it's an easy box to check off in a security audit. The trap tests whether you understand that **encryption ≠ access control**, and that a mesh with mTLS-only, no authorization policies, still allows any compromised pod to reach any other service freely.

---
See also: [15-Scenario-Unauthorized-Service-Bypass.md](15-Scenario-Unauthorized-Service-Bypass.md), [01-Concepts-Reference.md — Part 3: Security](01-Concepts-Reference.md#3-security-mtls-and-zero-trust)
