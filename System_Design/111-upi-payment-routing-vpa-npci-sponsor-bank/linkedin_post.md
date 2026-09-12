# UPI Payment Routing: VPA Resolution, Sponsor Banks, and the NPCI Switch — LinkedIn Post

## Post Text (copy-paste ready)

GPay never sees your bank account number. Not once. Here's the system that moves 12-14 BILLION transactions a month without ever exposing it.

- Your VPA (`alice@okhdfcbank`) is resolved ONLY by NPCI's central mapper — neither the payer's app nor the payer's bank ever sees the real account number, only the payee's own sponsor bank does.
- GPay, PhonePe, and Paytm are NOT banks — they have no direct NPCI connection. They're the "travel booking site"; ICICI/HDFC/Axis are the "airline" actually plugged into the switch.
- Money moves in strict two phases: DEBIT confirmed first (~800ms), THEN credit is attempted (~1400ms). Never the reverse — crediting first risks creating money that never existed.
- If the credit leg times out after the debit already succeeded, NPCI auto-triggers a reversal — regulatory ceiling is T+1 working day, but in practice it's usually minutes to hours, fully automatic.
- The real idempotency guarantee against retry storms isn't the app-level "does this RRN exist?" check — it's a UNIQUE(rrn) constraint at the database level, because two racing retries can both pass that check before either commits.

Swipe → to see the full debit-credit sequence, the auto-reversal edge case, and how UPI compares to card auth/capture, batch ACH, RTGS, and blockchain settlement.

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
GPay never sees your bank account number — here's the NPCI switch, sponsor banks & the idempotency trap engineers miss. 🎥👇

### Variant B — Long (400-600 chars)
Every month, UPI processes 12-14 billion transactions — and somehow GPay never touches your actual bank account number. The trick: a central NPCI mapper that ONLY it can resolve, a "sponsor bank" doing the real regulated work behind every PSP app, and a two-phase debit-then-credit flow with auto-reversal built in if the credit leg fails. The part that trips up engineers in interviews: idempotency has to be enforced with a UNIQUE database constraint, not just an app-level check — because retries race each other. Full breakdown in the carousel + video.

---

## Best Time to Post
Tuesday or Wednesday, 8:30–9:30 AM IST (commute-scroll window for Indian tech professionals, before the workday starts)

## Engagement Hook
If you were designing this: would you enforce idempotency with just an app-level check, or a DB-level UNIQUE constraint — and why does it actually matter? Drop your answer below.
