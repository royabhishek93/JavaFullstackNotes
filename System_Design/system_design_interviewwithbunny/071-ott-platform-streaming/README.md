# OTT Platform System Design — Netflix / Amazon Prime / Hotstar

## Overview
Design a large-scale OTT (Over-The-Top) video streaming platform that serves 200M+ subscribers, streams 4K HDR content globally with <2s startup latency, supports live sports, offline downloads, and a personalized recommendation engine.

**Key difference from YouTube**: OTT is **subscription-gated, licensed content** (SVOD/TVOD) with strict DRM, multi-bitrate adaptive streaming, and a curated catalogue rather than UGC (user-generated content).

---

## Interview Clarification Questions (ask these first!)

| Question | Why It Matters |
|----------|---------------|
| Scale: MAU, concurrent streams? | Sizing CDN, DB, infra |
| VOD only or Live streaming too? | Fundamentally different pipeline |
| Offline downloads? | Changes storage + DRM design |
| Multi-device sync (continue watching)? | State sync complexity |
| Global or single-region? | CDN, geo-restriction design |
| Own CDN or 3rd party? | Cost vs control tradeoff |

**Assumed scale** (Netflix-like):
- 200M subscribers, 100M DAU
- 15M concurrent streams peak
- 10,000 titles, 5 quality variants each
- 500 PB+ storage
- 99.99% availability SLA

---

## Learning Path

### Level 1: Beginner (Week 1-2)
1. [Architecture Overview](HLD/01_Architecture_Overview.md) — Big picture
2. [System Components](HLD/02_System_Components.md) — Microservices breakdown
3. [Video Streaming Flow](Flows/Video_Streaming_Flow.md) — How a play button works
4. [Database Design](HLD/04_Database_Design.md) — Schema & data model

**Key Concepts**: CDN, ABR streaming, HLS/DASH, subscription model

### Level 2: Intermediate (Week 3-4)
1. [Content Delivery](HLD/03_Content_Delivery.md) — CDN, ABR, encoding
2. [Content Ingestion Flow](Flows/Content_Ingestion_Flow.md) — Upload → Transcode → Publish
3. [Subscription Flow](Flows/Subscription_Flow.md) — Payment, entitlements
4. [Design Patterns](LLD/05_Design_Patterns.md) — Strategy, Observer, Factory

**Key Concepts**: Adaptive bitrate, DRM, transcoding pipeline, event-driven

### Level 3: Advanced (Week 5-6)
1. [Security & DRM](HLD/06_Security_DRM.md) — Widevine, FairPlay, PlayReady
2. [Recommendation Algorithm](LLD/04_Core_Algorithms.md) — Collaborative filtering, ML
3. [Class Diagrams](LLD/01_Class_Diagrams.md) — OOP design
4. [Code Implementation](LLD/06_Code_Implementation.md) — Java Spring Boot
5. [AWS Deployment](AWS_Deployment/AWS_Architecture.md) — CloudFront, ECS, S3

**Key Concepts**: DRM key management, ML recommendations, global CDN

---

## Documentation Structure

### High-Level Design (HLD)
- [01. Architecture Overview](HLD/01_Architecture_Overview.md) — System blueprint, ASCII diagrams
- [02. System Components](HLD/02_System_Components.md) — All microservices explained
- [03. Content Delivery](HLD/03_Content_Delivery.md) — CDN, ABR, HLS/DASH, encoding
- [04. Database Design](HLD/04_Database_Design.md) — Schema, indexing, NoSQL vs SQL choices
- [05. Scalability](HLD/05_Scalability.md) — Handling 15M concurrent streams
- [06. Security & DRM](HLD/06_Security_DRM.md) — DRM, auth, geo-restriction

### Low-Level Design (LLD)
- [01. Class Diagrams](LLD/01_Class_Diagrams.md) — Java OOP model
- [02. Sequence Diagrams](LLD/02_Sequence_Diagrams.md) — Method-level interactions
- [03. State Machines](LLD/03_State_Machines.md) — Content lifecycle, subscription states
- [04. Core Algorithms](LLD/04_Core_Algorithms.md) — Recommendation, search ranking
- [05. Design Patterns](LLD/05_Design_Patterns.md) — Strategy, Observer, Factory, Builder
- [06. Code Implementation](LLD/06_Code_Implementation.md) — Spring Boot Java examples

### Transaction Flows
- [Content Ingestion Flow](Flows/Content_Ingestion_Flow.md) — Upload → Transcode → CDN
- [Video Streaming Flow](Flows/Video_Streaming_Flow.md) — Play button → first frame
- [Subscription Flow](Flows/Subscription_Flow.md) — Signup → payment → entitlement
- [Recommendation Flow](Flows/Recommendation_Flow.md) — ML pipeline → homepage
- [Offline Download Flow](Flows/Offline_Download_Flow.md) — DRM-protected downloads

### AWS Deployment
- [AWS Architecture](AWS_Deployment/AWS_Architecture.md) — Complete cloud setup
- [Cost Optimization](AWS_Deployment/Cost_Optimization.md) — S3, CloudFront, Spot instances

---

## OTT vs YouTube: Key Differences

| Dimension | OTT (Netflix) | YouTube (UGC) |
|-----------|--------------|---------------|
| Content source | Licensed / original | User-uploaded |
| Access control | Subscription-gated | Free + ads |
| DRM | Mandatory (Widevine, FairPlay) | Optional |
| Content volume | ~10K titles | 800M videos |
| Upload pipeline | Professional ingest | Self-serve upload |
| Live streaming | Scheduled events (sports) | Always-on |
| Offline playback | DRM-protected download | Premium feature |
| CDN strategy | Own CDN (Netflix OCA) | Google CDN |

---

## Interview Frequency

- **85%** — HLS/DASH adaptive streaming, CDN design
- **80%** — Content ingestion & transcoding pipeline
- **75%** — DRM and content protection
- **72%** — Recommendation system design
- **70%** — Database design (catalogue, users, watch history)
- **65%** — Subscription & entitlement management
- **60%** — Live streaming architecture
- **55%** — Offline download with DRM
