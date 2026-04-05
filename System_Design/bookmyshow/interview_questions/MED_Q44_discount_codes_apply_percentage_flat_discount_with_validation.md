# Q44: Discount Codes - Apply percentage/flat discount with validation

### Difficulty: ⭐⭐⭐ (Senior)

### ✅ Solution: Coupon Validation Engine

```java
@Service
public class DiscountService {
    
    @Transactional
    public DiscountResult applyDiscount(
            String bookingId,
            String couponCode) {
        
        // Step 1: Validate booking
        Booking booking = bookingRepository.findById(bookingId)
            .orElseThrow();
        
        if (booking.getStatus() != BookingStatus.PENDING) {
            throw new InvalidBookingStateException(
                "Can only apply discount to pending bookings"
            );
        }
        
        // Step 2: Validate coupon
        Offer offer = offerRepository.findByCode(couponCode)
            .orElseThrow(() -> new InvalidCouponException("Coupon not found"));
        
        validateOffer(offer, booking);
        
        // Step 3: Check usage limits
        if (offer.getMaxUses() != null) {
            int currentUses = offer.getCurrentUses();
            if (currentUses >= offer.getMaxUses()) {
                throw new CouponExpiredException("Coupon usage limit exceeded");
            }
        }
        
        // Step 4: Check user-specific limits
        int userUsageCount = userOfferUsageRepository
            .countByUserIdAndOfferId(booking.getUserId(), offer.getId());
        
        if (userUsageCount > 0 && !offer.isMultipleUsePerUser()) {
            throw new CouponAlreadyUsedException(
                "You have already used this coupon"
            );
        }
        
        // Step 5: Calculate discount
        BigDecimal discountAmount = calculateDiscount(offer, booking);
        
        // Step 6: Apply discount
        booking.setOfferId(offer.getId());
        booking.setDiscountAmount(discountAmount);
        booking.setFinalPrice(
            booking.getTotalPrice().subtract(discountAmount)
        );
        
        bookingRepository.save(booking);
        
        // Step 7: Increment usage count
        offer.setCurrentUses(offer.getCurrentUses() + 1);
        offerRepository.save(offer);
        
        // Step 8: Record user usage
        userOfferUsageRepository.save(
            UserOfferUsage.builder()
                .userId(booking.getUserId())
                .offerId(offer.getId())
                .bookingId(booking.getId())
                .discountAmount(discountAmount)
                .usedAt(LocalDateTime.now())
                .build()
        );
        
        return DiscountResult.success(discountAmount, booking.getFinalPrice());
    }
    
    private void validateOffer(Offer offer, Booking booking) {
        
        // Check active status
        if (!offer.isActive()) {
            throw new CouponInactiveException("Coupon is not active");
        }
        
        // Check validity dates
        LocalDateTime now = LocalDateTime.now();
        if (now.isBefore(offer.getValidFrom()) || 
            now.isAfter(offer.getValidUntil())) {
            throw new CouponExpiredException(
                "Coupon is not valid at this time"
            );
        }
        
        // Check minimum booking amount
        if (offer.getMinBookingAmount() != null &&
            booking.getTotalPrice().compareTo(offer.getMinBookingAmount()) < 0) {
            throw new MinimumAmountNotMetException(
                "Minimum booking amount: " + offer.getMinBookingAmount()
            );
        }
        
        // Check movie restrictions
        if (offer.getApplicableMovies() != null && 
            !offer.getApplicableMovies().isEmpty()) {
            
            Long movieId = booking.getShow().getMovieId();
            if (!offer.getApplicableMovies().contains(movieId)) {
                throw new CouponNotApplicableException(
                    "Coupon not valid for this movie"
                );
            }
        }
        
        // Check theater restrictions
        if (offer.getApplicableTheaters() != null &&
            !offer.getApplicableTheaters().isEmpty()) {
            
            Long theaterId = booking.getShow().getTheaterId();
            if (!offer.getApplicableTheaters().contains(theaterId)) {
                throw new CouponNotApplicableException(
                    "Coupon not valid for this theater"
                );
            }
        }
    }
    
    private BigDecimal calculateDiscount(Offer offer, Booking booking) {
        
        BigDecimal discount;
        
        if (offer.getDiscountType() == DiscountType.PERCENTAGE) {
            // Percentage discount
            discount = booking.getTotalPrice()
                .multiply(offer.getDiscountValue())
                .divide(BigDecimal.valueOf(100), 2, RoundingMode.HALF_UP);
            
            // Apply max discount cap
            if (offer.getMaxDiscount() != null &&
                discount.compareTo(offer.getMaxDiscount()) > 0) {
                discount = offer.getMaxDiscount();
            }
            
        } else {
            // Flat discount
            discount = offer.getDiscountValue();
        }
        
        // Discount cannot exceed total price
        if (discount.compareTo(booking.getTotalPrice()) > 0) {
            discount = booking.getTotalPrice();
        }
        
        return discount;
    }
}
```

**Example Coupons:**

```
FLAT50
═══════════════════════════════════════════════════════════
Type: FLAT
Value: ₹50
Min Amount: ₹200
Max Uses: 10,000
Valid: 2026-01-01 to 2026-01-31

Example:
Booking: ₹500 → Apply FLAT50 → Final: ₹450 ✅
Booking: ₹150 → Apply FLAT50 → Error: Min ₹200 ❌


BMS20
═══════════════════════════════════════════════════════════
Type: PERCENTAGE
Value: 20%
Max Discount: ₹100
Min Amount: ₹300
Max Uses: Unlimited
Valid: Always

Example:
Booking: ₹500 → Discount: ₹100 (20% = ₹100, capped) ✅
Booking: ₹300 → Discount: ₹60 (20% = ₹60) ✅
Booking: ₹200 → Error: Min ₹300 ❌
```

---
