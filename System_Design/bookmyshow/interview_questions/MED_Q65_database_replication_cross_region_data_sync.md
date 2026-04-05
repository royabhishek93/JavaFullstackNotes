# Q65: Database Replication - Cross-region data sync

**Difficulty:** ⭐⭐⭐⭐ (Staff)

```sql
-- PRIMARY (US-East-1)
-- All writes go here

-- READ REPLICAS (Same Region)
-- Lag: 100-500ms (acceptable)

-- CROSS-REGION REPLICAS
-- EU-West-1: Lag 1-2 seconds
-- AP-South-1: Lag 2-5 seconds


-- Replication Configuration
CREATE PUBLICATION booking_pub FOR TABLE 
    booking, seat_availability, payment;

-- Subscribe from other regions
CREATE SUBSCRIPTION eu_west_sub
CONNECTION 'host=primary.us-east-1.rds.amazonaws.com'
PUBLICATION booking_pub;
```

---

## Q66-Q70: Testing Strategies
