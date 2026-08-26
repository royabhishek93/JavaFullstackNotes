# AWS Interview Questions — Print-Ready Scripts

This folder contains print-ready interview scripts for AWS + Spring Boot topics.
No code to memorize — just what to say, with ASCII diagrams to draw.

## How to Use
Read each file out loud before your interview.
Every section has: what the interviewer asks → what you say → diagram to draw.

## Files

| File | Topic |
|---|---|
| 8.spring-security-jwt-postgres-auth-eks-interview.md | Spring Security + JWT + PostgreSQL on EKS (with code) |
| 8.spring-security-jwt-postgres-auth-eks-interview-print.md | Same — print version (no code, just what to say) |
| 9.rds-aurora-connection-pooling-eks-interview-print.md | RDS Aurora + RDS Proxy + connection pooling traps |
| 10.eks-hpa-keda-production-traps-interview-print.md | EKS: HPA, KEDA, IRSA, CPU throttling, IP exhaustion |

## Topics Covered

- JWT auth lifecycle: BCrypt password storage, stateless sessions, token blacklisting
- Spring Security filter chain on EKS (multi-pod stateless auth)
- RDS Aurora: cluster vs instance endpoint, replication lag, Multi-AZ failover
- RDS Proxy: connection multiplexing, pinning, HikariCP maxLifetime trap
- EKS HPA vs KEDA (CPU metrics vs SQS queue depth)
- CPU limits throttling trap (limits = requests → silent performance regression)
- IRSA vs node IAM roles (blast radius and least privilege)
- PodDisruptionBudget (rolling deploys without downtime)
- EKS VPC CNI IP exhaustion (prefix delegation solution)

## Notes
- Files 9–10 added 2026-08-21: scenario + advanced + trap format for 15-yr architect rounds.
- For code examples, see the companion files in ../AWS/.
