# Q07: Refund Logic - User cancels 2 hours before show

### Difficulty: ⭐⭐⭐ (Senior)

### Business Rules:
```
Cancellation Windows:
- >24 hours before: 100% refund
- 12-24 hours before: 50% refund  
- <12 hours before: No refund
- After show starts: No refund
```

### ✅ Solution:

```java
@Service
public class RefundService {
    
    @Transactional
    public RefundResponse processCancellation(
            String bookingId, 
            String userId) {
        
        // Step 1: Validate booking
        Booking booking = bookingRepository.findById(bookingId)
            .orElseThrow(() -> new BookingNotFoundException(bookingId));
        
        if (!booking.getUserId().equals(userId)) {
            throw new UnauthorizedException("Not your booking");
        }
        
        if (booking.getStatus() != BookingStatus.CONFIRMED) {
            throw new InvalidStateException("Booking not confirmed");
        }
        
        // Step 2: Calculate refund amount
        Show show = showRepository.findById(booking.getShowId())
            .orElseThrow();
        
        LocalDateTime showTime = LocalDateTime.of(
            show.getShowDate(), 
            show.getStartTime()
        );
        
        Duration timeUntilShow = Duration.between(
            LocalDateTime.now(), 
            showTime
        );
        
        BigDecimal refundPercentage = calculateRefundPercentage(
            timeUntilShow
        );
        
        if (refundPercentage.compareTo(BigDecimal.ZERO) == 0) {
            throw new RefundNotAllowedException(
                "Cannot cancel less than 12 hours before show"
            );
        }
        
        BigDecimal refundAmount = booking.getTotalPrice()
            .multiply(refundPercentage)
            .divide(BigDecimal.valueOf(100));
        
        // Step 3: Process refund with payment gateway
        Payment payment = paymentRepository
            .findByBookingId(bookingId)
            .orElseThrow();
        
        Refund refund = stripeClient.refund(
            RefundRequest.builder()
                .paymentIntentId(payment.getTransactionId())
                .amount(refundAmount)
                .reason("requested_by_customer")
                .idempotencyKey("refund_" + bookingId)
                .build()
        );
        
        // Step 4: Update database
        booking.setStatus(BookingStatus.CANCELLED);
        booking.setCancelledAt(LocalDateTime.now());
        bookingRepository.save(booking);
        
        payment.setStatus(PaymentStatus.REFUNDED);
        payment.setRefundedAt(LocalDateTime.now());
        paymentRepository.save(payment);
        
        // Step 5: Release seats
        List<SeatAvailability> seats = seatRepository
            .findByBookingId(bookingId);
        
        seats.forEach(seat -> {
            seat.setStatus(SeatStatus.AVAILABLE);
            seat.setBookingId(null);
        });
        
        seatRepository.saveAll(seats);
        
        // Step 6: Update show count
        showRepository.incrementAvailableSeats(
            booking.getShowId(), 
            seats.size()
        );
        
        // Step 7: Invalidate cache
        cacheService.delete("show:" + booking.getShowId() + ":seats");
        
        // Step 8: Notify user
        notificationService.sendRefundConfirmation(
            userId, 
            refundAmount
        );
        
        return RefundResponse.builder()
            .refundAmount(refundAmount)
            .refundPercentage(refundPercentage)
            .estimatedDays(5-7)  // Stripe refund timeline
            .build();
    }
    
    private BigDecimal calculateRefundPercentage(Duration timeUntilShow) {
        long hours = timeUntilShow.toHours();
        
        if (hours >= 24) {
            return BigDecimal.valueOf(100);  // Full refund
        } else if (hours >= 12) {
            return BigDecimal.valueOf(50);   // Half refund
        } else {
            return BigDecimal.ZERO;          // No refund
        }
    }
}
```

---
