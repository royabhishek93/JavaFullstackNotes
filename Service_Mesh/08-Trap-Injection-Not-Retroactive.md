# Trap 3: "I Labeled the Namespace for Injection — My Existing Running Pods Now Have Sidecars, Right?"

**Interviewer:** "I labeled my namespace `istio-injection=enabled`. My existing running pods should now have sidecars, right?"

**Correct Answer: No.**

```
   Label namespace istio-injection=enabled
                |
                v
   Mutating webhook is now ACTIVE for this namespace
                |
                v
   Does it retroactively inject sidecars into
   pods that are ALREADY RUNNING?
                |
               NO -- webhook only fires on
                     NEW pod-creation events
```

The mutating webhook only fires on **new pod creation** events. Existing pods must be **deleted/recreated** (or a rolling restart triggered, e.g. `kubectl rollout restart deployment/...`) to get sidecars injected.

## Fix

```
  kubectl label namespace default istio-injection=enabled
  kubectl rollout restart deployment --all -n default
  # or: kubectl delete pod <pod> -n default   (if managed by a Deployment/ReplicaSet, it recreates)
```

## Why This Trap Exists

This exact gotcha shows up constantly in real Istio setups — people label the namespace, don't see a change, and assume the mesh installation is broken, when actually it's working exactly as designed. It tests whether you understand **when** admission webhooks fire (pod creation time only), not just what they do.

---
See also: [01-Concepts-Reference.md — Part 2: Sidecar Injection](01-Concepts-Reference.md#2-sidecar-pattern-control-plane-vs-data-plane)
