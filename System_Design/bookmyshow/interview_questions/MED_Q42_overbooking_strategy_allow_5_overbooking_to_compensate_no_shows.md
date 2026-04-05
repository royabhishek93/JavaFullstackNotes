# Q42: Overbooking Strategy - Allow 5% overbooking to compensate no-shows

### Difficulty: ⭐⭐⭐⭐ (Staff)

### ✅ Solution: Dynamic Overbooking with Risk Management

```java
@Service
public class OverbookingService {
    
    private static final double OVERBOOKING_FACTOR = 1.05;  // 5% overbooking
    
    public boolean canAcceptBooking(Long showId, int requestedSeats) {
        
        Show show = showRepository.findById(showId).orElseThrow();
        
        // Calculate overbooking limit
        int physicalCapacity = show.getTotalSeats();
        int overbookingLimit = (int) (physicalCapacity * OVERBOOKING_FACTOR);
        
        // Current bookings (CONFIRMED only, not PENDING)
        int confirmedBookings = bookingRepository
            .countConfirmedSeatsByShowId(showId);
        
        // Check if we can accept
        boolean canAccept = (confirmedBookings + requestedSeats) <= overbookingLimit;
        
        if (!canAccept) {
            log.info("Overbooking limit reached: show={}, limit={}, current={}",
                    showId, overbookingLimit, confirmedBookings);
        }
        
        return canAccept;
    }
    
    // Risk-based overbooking (adjust based on historical data)
    public double calculateOverbookingFactor(Long showId) {
        
        Show show = showRepository.findById(showId).orElseThrow();
        
        // Historical no-show rate for this show type
        double noShowRate = analyticsService
            .getNoShowRate(show.getMovieId(), show.getTheaterId());
        
        // Time until show
        Duration timeUntilShow = Duration.between(
            LocalDateTime.now(),
            LocalDateTime.of(show.getShowDate(), show.getStartTime())
        );
        
        double overbookingFactor;
        
        if (timeUntilShow.toHours() > 24) {
            // Far in future: higher no-show risk
            overbookingFactor = 1.0 + (noShowRate * 1.2);
        } else if (timeUntilShow.toHours() > 6) {
            // Same day: medium risk
            overbookingFactor = 1.0 + (noShowRate * 0.8);
        } else {
            // Within 6 hours: low risk
            overbookingFactor = 1.0 + (noShowRate * 0.5);
        }
        
        // Cap at 10% max overbooking
        return Math.min(overbookingFactor, 1.10);
    }
}

// Handle overbooking conflict (more confirmed bookings than physical seats)
@Service
public class OverbookingConflictResolver {
    
    public void resolveConflict(Long showId) {
        
        Show show = showRepository.findById(showId).orElseThrow();
        
        int physicalCapacity = show.getTotalSeats();
        int confirmedBookings = bookingRepository
            .countConfirmedSeatsByShowId(showId);
        
        if (confirmedBookings <= physicalCapacity) {
            return;  // No conflict
        }
        
        int excess = confirmedBookings - physicalCapacity;
        
        log.error("Overbooking conflict: show={}, capacity={}, booked={}",
                 showId, physicalCapacity, confirmedBookings);
        
        // Strategy 1: Upgrade to better show (same movie, later time)
        List<Booking> affectedBookings = findVoluntaryRebookings(showId, excess);
        
        for (Booking booking : affectedBookings) {
            // Offer upgrade to IMAX or later show
            Show alternateShow = findAlternateShow(booking);
            
            if (alternateShow != null) {
                // Rebook and compensate
                rebookWithCompensation(booking, alternateShow);
            }
        }
        
        // Strategy 2: Partial refund + voucher for remaining conflicts
        List<Booking> remainingConflicts = 
            findBookingsToCancel(showId, excess - affectedBookings.size());
        
        for (Booking booking : remainingConflicts) {
            // Full refund + 20% voucher
            refundService.processRefund(booking.getId(), RefundReason.OVERBOOKING);
            voucherService.issue(booking.getUserId(), 
                booking.getTotalPrice().multiply(BigDecimal.valueOf(0.2)));
            
            // Notify user
            notificationService.sendOverbookingApology(booking);
        }
    }
    
    private List<Booking> findVoluntaryRebookings(Long showId, int count) {
        // Find bookings made earliest (most likely to accept rebooking)
        return bookingRepository
            .findByShowIdOrderByCreatedAtAsc(showId)
            .stream()
            .limit(count)
            .collect(Collectors.toList());
    }
}
```

**Overbooking Example:**

```
SHOW CAPACITY: 100 seats
OVERBOOKING LIMIT: 105 seats (5%)

BOOKING TIMELINE
═══════════════════════════════════════════════════════════
Day 1:  80 bookings confirmed
Day 2:  95 bookings confirmed
Day 3:  103 bookings confirmed (overbooking active)
Day 4:  105 bookings confirmed (limit reached)
Day 5:  106th booking request → REJECTED ❌

CONFLICT RESOLUTION (if all 105 show up)
═══════════════════════════════════════════════════════════
Physical capacity: 100 seats
Confirmed bookings: 105 bookings
Excess: 5 bookings

Resolution:
- 3 users offered upgrade to IMAX show (free) ✅
- 2 users given full refund + 20% voucher ✅
```

---
