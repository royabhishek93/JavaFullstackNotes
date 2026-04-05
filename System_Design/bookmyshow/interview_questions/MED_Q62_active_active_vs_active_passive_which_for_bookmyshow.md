# Q62: Active-Active vs Active-Passive - Which for BookMyShow?

**Difficulty:** ⭐⭐⭐⭐ (Staff)

```
ACTIVE-PASSIVE (Disaster Recovery)
═══════════════════════════════════════════════════════════
Primary (US-East-1)
- Handles 100% traffic
- Writes to primary database

Passive (EU-West-1)
- Standby (0% traffic)
- Database replication only
- Activates if primary fails

Pros: ✅ Simple, ✅ Lower cost
Cons: ❌ High latency for EU users, ❌ Wasted capacity


ACTIVE-ACTIVE (Recommended) ✅
═══════════════════════════════════════════════════════════
Region 1 (US-East-1)
- Handles Americas traffic
- Read + Write

Region 2 (EU-West-1)
- Handles Europe traffic
- Read + Write

Region 3 (AP-South-1)
- Handles Asia traffic
- Read + Write

Pros: ✅ Low latency globally, ✅ High availability
Cons: ❌ Complex, ❌ Data consistency challenges
```

**Data Partitioning Strategy:**

```java
@Service
public class RegionAwareBookingService {
    
    // Partition data by city (natural geographic isolation)
    public Booking createBooking(BookingRequest request) {
        
        Show show = showRepository.findById(request.getShowId());
        City city = cityRepository.findById(show.getCityId());
        
        // Route to region based on city
        String region = getRegionForCity(city);
        
        if (region.equals(getCurrentRegion())) {
            // Local write (fast)
            return bookingRepository.save(booking);
        } else {
            // Cross-region write (forward to correct region)
            return crossRegionClient.createBooking(region, request);
        }
    }
    
    private String getRegionForCity(City city) {
        // India cities → AP-South-1
        if (city.getCountry().equals("India")) {
            return "ap-south-1";
        }
        // Europe cities → EU-West-1
        else if (isEuropeanCountry(city.getCountry())) {
            return "eu-west-1";
        }
        // Default → US-East-1
        else {
            return "us-east-1";
        }
    }
}
```

---
