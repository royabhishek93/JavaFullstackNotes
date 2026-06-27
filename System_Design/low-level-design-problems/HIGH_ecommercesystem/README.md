# E-commerce System (LLD)

This folder follows the same structure and interview style as HIGH_movieticketbookingsystem.

## Files
- `e-commerce-system.md` - End-to-end low-level design
- `DATABASE_SCHEMA_VISUAL.md` - Schema and entity relationships
- `INTERVIEW_APPROACH.md` - How to present the system in interviews
- `interview_questions/` - Scenario-based Q and A

## Scope
- Product catalog and inventory
- Cart and checkout flow
- Orders, payments, and shipment lifecycle
- Discounts and idempotent order placement
- Concurrency controls for inventory reservation

## One-line pitch
Design for correctness first: inventory consistency + idempotent checkout + order/payment separation; then scale reads with denormalized catalog and async order processing.
