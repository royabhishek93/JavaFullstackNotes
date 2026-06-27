# MED Q01 - Fixed Window Boundary Burst Problem

## Scenario
Limit is 100 requests/minute. Client sends 100 requests at 12:00:59 and 100 more at 12:01:00.

## Problem
Fixed window allows 200 requests in 2 seconds even though intended average is 100/minute.

## Better Options
- Sliding window counter
- Token bucket with bounded burst capacity

## Interview One-Liner
Fixed window is simple, but unfair at window boundaries.
