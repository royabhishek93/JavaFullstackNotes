# Rate Limiter System (LLD)

This folder follows the same structure and interview style as HIGH_movieticketbookingsystem.

## Files
- `rate-limiter-system.md` - End-to-end low-level design
- `DATABASE_SCHEMA_VISUAL.md` - Schema and entity relationships
- `INTERVIEW_APPROACH.md` - How to present the system in interviews
- `interview_questions/` - Scenario-based Q and A

## Scope
- Per-user, per-IP, per-API-key, and per-tenant limits
- Fixed window, sliding window, token bucket, and leaky bucket strategies
- Distributed enforcement with Redis/cache + fallback rules
- Idempotent allow/deny decision logging and metrics
- Handling burst traffic and hot keys

## One-line pitch
A good rate limiter is not just about blocking traffic; it protects correctness, fairness, and downstream capacity under contention.
