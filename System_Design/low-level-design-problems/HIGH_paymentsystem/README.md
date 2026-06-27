# Payment System (LLD)

This folder follows the same structure as `HIGH_movieticketbookingsystem` and focuses on payment-domain low-level design for interviews.

## Files
- `payment-system.md` - End-to-end LLD (requirements, APIs, classes, flows)
- `DATABASE_SCHEMA_VISUAL.md` - Visual ER schema with PK/FK and status transitions
- `INTERVIEW_APPROACH.md` - How to explain this design in interviews
- `interview_questions/` - Topic-wise scenario-based Q&A

## Scope
This design covers:
- Payment intent/order creation
- Idempotent charge execution
- Retry and failure handling
- Webhook reconciliation
- Ledger-based accounting safety
- Refund (full/partial)

## Quick Start Talking Point
"Design for correctness first: idempotency + ledger immutability + webhook reconciliation; then design for scale using queue-based processing and gateway abstraction."
