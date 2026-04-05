# Q47: Scalping Prevention - Prevent bots from bulk-buying tickets

### Difficulty: ⭐⭐⭐⭐ (Staff)

### ✅ Solution: Multi-Layer Bot Detection

```java
@Service
public class ScalpingPreventionService {
    
    // Layer 1: CAPTCHA for suspicious requests
    public void validateCaptcha(String token, String ipAddress) {
        
        RecaptchaResponse response = recaptchaClient.verify(token);
        
        if (!response.isSuccess() || response.getScore() < 0.5) {
            log.warn("CAPTCHA failed: ip={}, score={}", 
                    ipAddress, response.getScore());
            throw new CaptchaFailedException("Please complete CAPTCHA");
        }
    }
    
    // Layer 2: Rate limiting per user
    public void checkUserRateLimit(Long userId) {
        
        String key = "booking:rate:" + userId;
        
        Long bookingsInLastHour = redisTemplate.opsForValue()
            .increment(key);
        
        if (bookingsInLastHour == 1) {
            // First booking, set expiry
            redisTemplate.expire(key, Duration.ofHours(1));
        }
        
        // Max 5 bookings per user per hour
        if (bookingsInLastHour > 5) {
            log.warn("Rate limit exceeded: user={}, count={}", 
                    userId, bookingsInLastHour);
            throw new RateLimitExceededException(
                "You can only book 5 shows per hour"
            );
        }
    }
    
    // Layer 3: Device fingerprinting
    public void checkDeviceFingerprint(String fingerprint) {
        
        String key = "device:bookings:" + fingerprint;
        
        Long bookingsFromDevice = redisTemplate.opsForValue()
            .increment(key);
        
        if (bookingsFromDevice == 1) {
            redisTemplate.expire(key, Duration.ofHours(24));
        }
        
        // Max 10 bookings per device per day
        if (bookingsFromDevice > 10) {
            throw new SuspiciousActivityException(
                "Too many bookings from this device"
            );
        }
    }
    
    // Layer 4: Velocity checks
    public void checkBookingVelocity(Long userId, Long showId) {
        
        // Check if user is booking too fast
        List<Booking> recentBookings = bookingRepository
            .findByUserIdAndCreatedAtAfter(
                userId,
                LocalDateTime.now().minusMinutes(5)
            );
        
        if (recentBookings.size() >= 3) {
            throw new VelocityException(
                "Please wait before making another booking"
            );
        }
        
        // Check if multiple users booking same show rapidly
        Long recentBookingsForShow = bookingRepository
            .countByShowIdAndCreatedAtAfter(
                showId,
                LocalDateTime.now().minusSeconds(30)
            );
        
        if (recentBookingsForShow > 50) {
            // Possible bot attack
            log.error("High velocity detected: show={}, count={}", 
                     showId, recentBookingsForShow);
            
            // Enable CAPTCHA for all requests
            showSecurityService.enableCaptcha(showId);
        }
    }
    
    // Layer 5: Max seats per transaction
    public void validateSeatCount(int seatCount) {
        
        // Max 10 seats per booking (prevent bulk buying)
        if (seatCount > 10) {
            throw new InvalidSeatCountException(
                "Maximum 10 seats allowed per booking"
            );
        }
    }
    
    // Layer 6: Phone verification for high-value bookings
    public void requirePhoneVerification(Booking booking) {
        
        // Require verification for bookings >₹5000
        if (booking.getTotalPrice().compareTo(
                BigDecimal.valueOf(5000)) > 0) {
            
            if (!userService.isPhoneVerified(booking.getUserId())) {
                throw new VerificationRequiredException(
                    "Please verify your phone number for this booking"
                );
            }
        }
    }
}

@RestController
@RequestMapping("/api/bookings")
public class BookingController {
    
    @PostMapping
    public BookingResponse createBooking(
            @RequestBody BookingRequest request,
            @RequestHeader("X-Fingerprint") String fingerprint,
            @RequestHeader("X-Recaptcha-Token") String captchaToken,
            HttpServletRequest httpRequest) {
        
        String ipAddress = getClientIp(httpRequest);
        
        // Run all anti-scalping checks
        scalpingPrevention.validateCaptcha(captchaToken, ipAddress);
        scalpingPrevention.checkUserRateLimit(request.getUserId());
        scalpingPrevention.checkDeviceFingerprint(fingerprint);
        scalpingPrevention.checkBookingVelocity(
            request.getUserId(), 
            request.getShowId()
        );
        scalpingPrevention.validateSeatCount(request.getSeatIds().size());
        
        // Create booking
        Booking booking = bookingService.createBooking(request);
        
        // Additional check after booking created
        scalpingPrevention.requirePhoneVerification(booking);
        
        return BookingResponse.from(booking);
    }
}
```

**Honeypot Technique:**

```java
// Add invisible field to form (bots will fill it)
@Component
public class HoneypotValidator {
    
    public void validate(BookingRequest request) {
        
        // Hidden field in form: "website" (should be empty)
        if (request.getHoneypotField() != null && 
            !request.getHoneypotField().isEmpty()) {
            
            log.warn("Honeypot triggered: user={}, value={}", 
                    request.getUserId(), 
                    request.getHoneypotField());
            
            // Silently reject (don't tell bot it failed)
            throw new BookingFailedException("Seats unavailable");
        }
    }
}
```

---
