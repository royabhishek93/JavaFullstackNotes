# Mermaid Diagrams — Extracted

Diagrams extracted from `interviewguide.md` and replaced in-place with ASCII-art equivalents. Kept here verbatim for anyone who wants the interactive/renderable Mermaid version.

## From `interviewguide.md` — "Control Plane vs. Data Plane (Component Diagram)"

```mermaid
flowchart TB
    subgraph DataPlane["Data Plane (per Pod, handles real traffic)"]
        SidecarA["Sidecar Proxy A (Envoy)"] <-->|"direct proxy-to-proxy traffic"| SidecarB["Sidecar Proxy B (Envoy)"]
    end
    subgraph ControlPlane["Control Plane (configures & secures, NOT in request path)"]
        ConfigMgr["Configuration Manager (Galley)"]
        TrafficCtl["Traffic Controller (Pilot)"]
        SecMgr["Security Manager (Citadel)"]
    end
    ConfigMgr -->|"validated config"| TrafficCtl
    TrafficCtl -->|"pushes config on CHANGE only"| SidecarA
    TrafficCtl -->|"pushes config on CHANGE only"| SidecarB
    SecMgr -->|"issues TLS certs"| SidecarA
    SecMgr -->|"issues TLS certs"| SidecarB
```
