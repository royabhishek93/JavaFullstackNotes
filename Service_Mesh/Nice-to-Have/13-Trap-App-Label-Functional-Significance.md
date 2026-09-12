# Trap 10: "The `app` Label Is Purely Cosmetic Metadata, It Doesn't Functionally Matter, Right?"

**Interviewer:** "The `app` label on my Kubernetes Deployment/Service is purely cosmetic metadata, it doesn't affect anything functionally, right?"

**Correct Answer: No — in Istio it has functional significance.**

```
  Deployment/Service WITH "app" label
                |
                v
  Kiali can correlate traffic data to build
  the service topology graph correctly
                |
                v
  Full visualization: which service talks to
  which, traffic %, error rates, all mapped

  -----------------------------------------------

  Deployment/Service WITHOUT "app" label
                |
                v
  Pods still communicate FINE - no errors,
  no traffic problems
                |
                v
  BUT Kiali graph shows NOTHING meaningful
  for that service - broken/empty visualization
```

Kiali (and some of Istio's own telemetry-to-topology correlation) depends on the `app` label to build the service graph. Missing it doesn't break traffic (pods still communicate fine), but it **breaks observability/visualization**.

## Why This Trap Exists

Interviewers use this to test whether you've actually **operated** a mesh hands-on versus just read about it — this is exactly the kind of "my dashboard is empty but everything technically works" gotcha that only shows up in real usage, not in architecture diagrams or docs skimmed at a high level.

---
See also: [01-Concepts-Reference.md — Part 5: Observability](../Must-Know/01-Concepts-Reference.md#5-observability-metrics-tracing-kialigrafana)
