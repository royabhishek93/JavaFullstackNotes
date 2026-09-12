# Trap 5: "Envoy Encrypts Traffic Between My App and Its Own Sidecar Too, Right?"

**Interviewer:** "Envoy encrypts the traffic between my app container and its own sidecar too, right? Since they're in the 'secure' pod boundary?"

**Correct Answer: No.**

```
  Pod boundary
  +---------------------------------------------------+
  |  App Container  <--localhost, PLAINTEXT-->  Envoy  |  <-- NOT encrypted
  |                                              Sidecar |      (loopback traffic
  +---------------------------------------------------+       never leaves the pod)
                          |
                          | mTLS ENCRYPTED
                          | (the ONLY hop that's encrypted)
                          v
                     Envoy Sidecar (remote pod)
```

Traffic between the app container and its own sidecar goes over `localhost` **in plaintext**. mTLS is only applied on the **pod-to-pod** hop — sidecar-to-sidecar, across the actual network.

## Why This Is Considered Acceptable

This is intentional: loopback traffic never leaves the pod's network namespace, so it's considered a low-risk boundary (an attacker would need to already be inside that specific pod/container to intercept it — at which point they likely have direct access to the app anyway).

## Why This Trap Exists

If an interviewer asks "is ALL traffic encrypted end-to-end including inside the pod," the precise, correct answer is **no** — only the inter-pod hop. Saying "yes, everything is encrypted" reveals a surface-level understanding of the sidecar pattern rather than the actual data path.

---
See also: [01-Concepts-Reference.md — Part 2: Sidecar Pattern diagram](01-Concepts-Reference.md#2-sidecar-pattern-control-plane-vs-data-plane), [`Diagram-01-Sidecar-Pattern.drawio`](Diagram-01-Sidecar-Pattern.drawio)
