# Ride Booking System (LLD)

This folder follows the same structure and interview style as HIGH_movieticketbookingsystem.

## Files
- `ride-booking-system.md` - End-to-end low-level design
- `DATABASE_SCHEMA_VISUAL.md` - Schema and entity relationships
- `INTERVIEW_APPROACH.md` - How to present the system in interviews
- `interview_questions/` - Scenario-based Q and A

## Scope
- Rider and driver matching
- Driver availability and geo updates
- Ride lifecycle and pricing
- Payment integration and cancellation rules
- Concurrency controls for driver assignment

## One-line pitch
Design for correctness first: one driver cannot accept two rides, one ride cannot get two drivers, and trip/payment states must reconcile exactly once.
