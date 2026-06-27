# Q45: Dynamic Pricing - Increase price based on demand

### Difficulty: ⭐⭐⭐⭐ (Staff)

### ✅ Solution: Surge Pricing Algorithm

```java
@Service
public class DynamicPricingService {
    
    public BigDecimal calculateDynamicPrice(Long showId, SeatType seatType) {
        
        Show show = showRepository.findById(showId).orElseThrow();
        
        // Base price
        BigDecimal basePrice = seatPricingRepository
            .findByShowIdAndSeatType(showId, seatType)
            .map(SeatPricing::getPrice)
            .orElse(show.getBasePrice());
        
        // Calculate surge multiplier
        double surgeMultiplier = calculateSurgeMultiplier(show);
        
        // Apply multiplier
        BigDecimal dynamicPrice = basePrice
            .multiply(BigDecimal.valueOf(surgeMultiplier))
            .setScale(2, RoundingMode.HALF_UP);
        
        return dynamicPrice;
    }
    
    private double calculateSurgeMultiplier(Show show) {
        
        double multiplier = 1.0;
        
        // Factor 1: Occupancy rate
        double occupancyRate = 1.0 - 
            ((double) show.getAvailableSeats() / show.getTotalSeats());
        
        if (occupancyRate > 0.9) {
            multiplier += 0.5;  // 50% surge for >90% full
        } else if (occupancyRate > 0.7) {
            multiplier += 0.3;  // 30% surge for >70% full
        } else if (occupancyRate > 0.5) {
            multiplier += 0.15;  // 15% surge for >50% full
        }
        
        // Factor 2: Time until show
        Duration timeUntilShow = Duration.between(
            LocalDateTime.now(),
            LocalDateTime.of(show.getShowDate(), show.getStartTime())
        );
        
        long hoursUntilShow = timeUntilShow.toHours();
        
        if (hoursUntilShow <= 2) {
            multiplier += 0.2;  // Last-minute surge
        } else if (hoursUntilShow <= 6) {
            multiplier += 0.1;  // Same-day surge
        }
        
        // Factor 3: Day of week
        DayOfWeek dayOfWeek = show.getShowDate().getDayOfWeek();
        if (dayOfWeek == DayOfWeek.SATURDAY || dayOfWeek == DayOfWeek.SUNDAY) {
            multiplier += 0.1;  // Weekend surge
        }
        
        // Factor 4: Time of day (peak hours)
        LocalTime startTime = show.getStartTime();
        if (startTime.isAfter(LocalTime.of(18, 0)) &&
            startTime.isBefore(LocalTime.of(22, 0))) {
            multiplier += 0.1;  // Prime-time surge (6 PM - 10 PM)
        }
        
        // Factor 5: Movie popularity
        double popularityScore = analyticsService
            .getMoviePopularityScore(show.getMovieId());
        
        if (popularityScore > 0.8) {
            multiplier += 0.2;  // Blockbuster surge
        }
        
        // Cap surge at 2x (100% increase)
        return Math.min(multiplier, 2.0);
    }
}
```

**Dynamic Pricing Example:**

```
SHOW: Avengers - Saturday 8 PM
BASE PRICE: ₹200

SURGE CALCULATION
═══════════════════════════════════════════════════════════
Occupancy: 85% → +30% surge
Time until show: 3 hours → +10% surge
Day: Saturday → +10% surge
Time: 8 PM → +10% surge (prime time)
Movie popularity: 0.9 → +20% surge

Total surge: 1.0 + 0.3 + 0.1 + 0.1 + 0.1 + 0.2 = 1.8x

FINAL PRICE: ₹200 × 1.8 = ₹360 ✅

Timeline:
══════════════════════════════════════════════════════════
5 PM (3 hours before): ₹360 (high surge)
6 PM (2 hours before): ₹400 (last-minute surge)
7:30 PM (30 min before): ₹400 (capped at 2x)
```

---

## Key Takeaways:

```
Q41: Seat Expiry
✅ Scheduled job every 30 seconds
✅ Batch update expired reservations
✅ 15-minute TTL
✅ Simpler than Redis TTL

Q42: Overbooking
✅ 5% overbooking factor
✅ Dynamic adjustment based on no-show rate
✅ Conflict resolution (upgrade or refund + voucher)
✅ Cap at 10% max

Q43: Group Booking
✅ Find contiguous seats in same row
✅ Window function for optimization
✅ Atomic reservation
✅ Row preference scoring

Q44: Discount Codes
✅ Validate active, date range, min amount
✅ Check usage limits (global + per-user)
✅ Calculate percentage or flat discount
✅ Apply max discount cap

Q45: Dynamic Pricing
✅ Surge based on occupancy, time, day, popularity
✅ 1.8x surge example (Avengers Saturday 8 PM)
✅ Cap at 2x max
✅ Real-time price calculation
```

This demonstrates production business logic expertise! 🎯
