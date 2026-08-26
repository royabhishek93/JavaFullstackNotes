# Parking Lot System (LLD)

This folder follows the same structure and interview style as HIGH_movieticketbookingsystem.

## Files
- parking-lot-system.md: end-to-end low-level design
- DATABASE_SCHEMA_VISUAL.md: schema and entity relationships
- INTERVIEW_APPROACH.md: how to present this in interviews
- interview_questions/: scenario-based Q and A

## Scope
- Vehicle entry and exit flow
- Slot allocation by vehicle type
- Ticket lifecycle and payment
- Dynamic pricing strategy
- Concurrency controls for slot assignment

## One-line pitch
Design for correctness first (no double allocation, accurate billing), then scale with partitioned floors, indexed slot lookup, and event-driven updates.
