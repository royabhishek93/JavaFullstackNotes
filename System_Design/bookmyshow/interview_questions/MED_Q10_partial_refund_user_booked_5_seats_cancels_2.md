# Q10: Partial Refund - User booked 5 seats, cancels 2

### Difficulty: ⭐⭐⭐ (Senior)

### ✅ Solution:

```java
@Service
public class PartialRefundService {
    
    @Transactional
    public RefundResponse processPartialCancellation(
            String bookingId,
            List<Long> seatIdsToCancel) {
        
        Booking booking = bookingRepository.findById(bookingId)
            .orElseThrow();
        
        // Validate seats belong to this booking
        List<BookingSeat> bookingSeats = bookingSeatRepository
            .findByBookingId(bookingId);
        
        List<Long> validSeatIds = bookingSeats.stream()
            .map(BookingSeat::getSeatId)
            .collect(Collectors.toList());
        
        if (!validSeatIds.containsAll(seatIdsToCancel)) {
            throw new InvalidSeatsException("Invalid seat selection");
        }
        
        // Calculate refund for selected seats only
        BigDecimal pricePerSeat = booking.getTotalPrice()
            .divide(BigDecimal.valueOf(booking.getTotalSeats()), 
                    2, RoundingMode.HALF_UP);
        
        BigDecimal refundAmount = pricePerSeat
            .multiply(BigDecimal.valueOf(seatIdsToCancel.size()));
        
        // Process partial refund
        Refund refund = stripeClient.refund(
            RefundRequest.builder()
                .paymentIntentId(booking.getPaymentId())
                .amount(refundAmount)
                .reason("partial_cancellation")
                .metadata(Map.of(
                    "booking_id", bookingId,
                    "cancelled_seats", seatIdsToCancel.toString()
                ))
                .build()
        );
        
        // Update booking
        booking.setTotalSeats(booking.getTotalSeats() - seatIdsToCancel.size());
        booking.setTotalPrice(booking.getTotalPrice().subtract(refundAmount));
        bookingRepository.save(booking);
        
        // Release cancelled seats
        seatRepository.releaseSeats(
            booking.getShowId(), 
            seatIdsToCancel
        );
        
        // Delete cancelled booking_seat records
        bookingSeatRepository.deleteByBookingIdAndSeatIdIn(
            bookingId, 
            seatIdsToCancel
        );
        
        return RefundResponse.builder()
            .refundAmount(refundAmount)
            .remainingSeats(booking.getTotalSeats())
            .build();
    }
}
```

---

## Key Takeaways:

```
Q06: Payment Timeout
✅ Poll gateway with exponential backoff
✅ Use idempotency keys
✅ Webhook for eventual consistency

Q07: Refund Logic
✅ Business rules based on time
✅ Partial refunds supported
✅ Release seats atomically

Q08: Idempotency
✅ Prevent duplicate operations
✅ Cache responses
✅ Handle concurrent requests

Q09: Webhooks
✅ Verify signatures
✅ Idempotent processing
✅ Retry handling

Q10: Partial Refunds
✅ Calculate per-seat price
✅ Update booking totals
✅ Release specific seats
```

This demonstrates production-level payment handling! 🎯
