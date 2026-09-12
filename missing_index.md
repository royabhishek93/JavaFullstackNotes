# Missing Topics Index — Gaps for a 2026 Software Architect

> Generated from a full repository inventory (Java, Spring, Kafka, AWS, System Design, LLD, Reactive, JVM debugging, React, AI/LLM). This repo is **exceptionally strong** in those areas — this file tracks what's still missing or shallow for someone being evaluated as an **architect** (not just senior engineer) in 2026.

---

## ❌ Completely Missing

| Topic | Why it matters for 2026 architects |
|---|---|
| **Infrastructure as Code** (Terraform, CDK, Pulumi) | Architects are expected to own provisioning, not just design — no IaC content exists anywhere, despite 30+ AWS files assuming console/manual setup |
| **Domain-Driven Design** (bounded contexts, aggregates, ubiquitous language, event storming) | Foundational for decomposing microservices correctly — currently microservices patterns are covered but not the *decomposition methodology* |
| **FinOps / Cost Optimization** | Cost-aware architecture (reserved capacity, spot instances, right-sizing) is now a core architect responsibility, not just an ops concern |
| **Platform Engineering / Internal Developer Platforms** | Backstage, self-service infra, golden paths — the dominant 2024-2026 org pattern for scaling engineering teams |
| **Multi-cloud / cloud-agnostic design** | Repo is 100% AWS; no Azure/GCP comparison or portability strategy |
| **Team Topologies / Conway's Law** | How team structure should drive (or follow) system boundaries — increasingly asked at architect level |
| **Feature flags / progressive delivery** (LaunchDarkly-style, canary, blue-green) | Standard for de-risking deploys; only "deployment" mentioned is basic CI/CD |
| **Data mesh / data platform architecture** | Relevant if the architect role touches analytics/data platforms |
| **Edge computing** (Lambda@Edge, Cloudflare Workers) | Growing pattern for latency-sensitive global apps |
| **Rust/Go as polyglot options** | Common in infra tooling, sidecars, high-perf services — repo is Java/JS only |

---

## 🟡 Present but Shallow (needs depth for architect-level, not just mention)

| Topic | Current state | Gap |
|---|---|---|
| **Kubernetes** | EKS-specific (HPA, KEDA, OOMKilled) | No general K8s architecture, CRDs/operators, Helm, admission controllers |
| **Docker** | Assumed in CI/CD | No Dockerfile optimization, multi-stage builds, image security scanning |
| **Service Mesh** | Istio mentioned once | No VirtualServices/DestinationRules, mTLS, traffic shifting details |
| **Observability** | Good on tracing/logging/actuator | No Prometheus/Grafana setup, alerting design, **SLO/SLI/error budget** methodology |
| **Security** | OAuth2/JWT/Cognito is strong | No **Zero Trust**, mTLS, OWASP-based security testing |
| **Testing** | Unit/integration/contract solid | No **chaos engineering**, load/perf testing strategy |
| **Data engineering** | Kafka is exceptional | No Flink/Spark, data warehousing (Snowflake/Redshift), batch pipelines |
| **Cloud-native databases** | DynamoDB deep | No CockroachDB/Spanner/TiDB (distributed SQL/NewSQL) trade-offs |
| **GraphQL / gRPC** | One file each (gRPC now also touched in [System_Design/Communication_Patterns_Webhook_WebSocket__Webclient_gRPC_REST.md](System_Design/Communication_Patterns_Webhook_WebSocket__Webclient_gRPC_REST.md)) | Not architect-depth (federation, schema design, streaming/interceptors) |
| **Serverless** | Lambda basics | No cold-start mitigation, state management, cost modeling |

---

## ✅ Already Exceptional (no action needed)

Kafka, Java concurrency/virtual threads, Spring Boot internals, AWS architecture, System Design HLD/LLD, JVM debugging (**now including Modern Observability #145–#149**: continuous eBPF profiling, APM-first triage, AI-assisted RCA), Microservices resilience patterns, AI/LLM engineering, Reactive Programming, Communication patterns (REST/WebClient/FeignClient/WebSocket/Webhook/gRPC/SSE).

---

## ✅ Closed Gaps (previously flagged, now filled)

| Topic | Where it now lives |
|---|---|
| **Continuous profiling** (Grafana Pyroscope/Parca, eBPF) | [how_to_debug_JVM/145-continuous-ebpf-profiling-pyroscope-parca.md](how_to_debug_JVM/145-continuous-ebpf-profiling-pyroscope-parca.md) |
| **Vendor APM tooling** (Datadog/New Relic/Dynatrace triage workflow) | [how_to_debug_JVM/146-apm-first-triage-datadog-newrelic-dynatrace.md](how_to_debug_JVM/146-apm-first-triage-datadog-newrelic-dynatrace.md), [147-apm-dashboard-green-trap.md](how_to_debug_JVM/147-apm-dashboard-green-trap.md) |
| **AI-assisted production debugging** (LLM-based heap/thread dump RCA) | [how_to_debug_JVM/148-ai-assisted-heap-thread-dump-analysis.md](how_to_debug_JVM/148-ai-assisted-heap-thread-dump-analysis.md) |
| **eBPF profiling overhead/security trade-offs** | [how_to_debug_JVM/149-ebpf-profiling-zero-overhead-trap.md](how_to_debug_JVM/149-ebpf-profiling-zero-overhead-trap.md) |

---

## 🤖 agentic_ai/ Folder — Deep Dive Audit (2026-08-31)

The `agentic_ai/` folder was audited separately — it is the **most current folder in the entire repo** (content updated through August 2026: Claude 5 model family, Anthropic Managed Agents API, Computer Use safety, Deep Agents/SubAgents). RAG (incl. GraphRAG, hybrid search, reranking, RAGAS eval), vector DBs, LangGraph/multi-agent orchestration, MCP (incl. security + marketplace design), fine-tuning/QLoRA, prompt engineering, LLM security/governance, observability (LangSmith/Langfuse/W&B, semantic caching), voice agents, and AWS deployment are all covered at architect depth — far beyond what was initially assumed.

Only **two genuine gaps** found after a targeted search:

| Topic | Why it matters |
|---|---|
| **A2A (Agent2Agent) protocol** (Google) | Zero mentions anywhere. Emerging complement/rival to MCP — MCP = agent↔tool, A2A = agent↔agent across vendors/orgs. Increasingly asked as "MCP vs A2A — when do you need both?" |
| **Formal agent evaluation benchmarks** (SWE-bench, GAIA, AgentBench) | RAG-specific eval (RAGAS) is thorough, but no coverage of standardized *agent* capability benchmarks used to compare agent frameworks/models |

---

## 🎯 Top Priority Order (highest ROI first)

1. **Terraform / IaC**
2. **Domain-Driven Design**
3. **SRE fundamentals** (SLO/SLI/error budgets, incident response, postmortems)
4. **Kubernetes deep-dive** (beyond EKS specifics)
5. **FinOps / cost optimization**
6. **A2A (Agent2Agent) protocol vs MCP** (agentic_ai gap)
7. **Agent evaluation benchmarks** (SWE-bench/GAIA/AgentBench) (agentic_ai gap)

---

*Last updated: 2026-08-31*
