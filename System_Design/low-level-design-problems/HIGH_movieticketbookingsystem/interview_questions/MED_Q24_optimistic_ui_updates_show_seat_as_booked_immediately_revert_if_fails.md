# Q24: Optimistic UI Updates - Show seat as booked immediately, revert if fails

### ✅ Solution: Optimistic Update + Rollback on Error

```javascript
class SeatBookingUI {
    
    async bookSeats(showId, seatIds) {
        // Step 1: Optimistic update (instant feedback)
        this.markSeatsAsBooked(seatIds);
        this.showSpinner('Booking...');
        
        try {
            // Step 2: Call API
            const response = await fetch('/api/bookings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    showId: showId,
                    seatIds: seatIds,
                    userId: this.userId
                })
            });
            
            if (!response.ok) {
                throw new Error('Booking failed');
            }
            
            const booking = await response.json();
            
            // Step 3: Server confirmed, proceed to payment
            this.hideSpinner();
            this.navigateToPayment(booking.id);
            
        } catch (error) {
            // Step 4: Rollback optimistic update
            this.markSeatsAsAvailable(seatIds);
            this.hideSpinner();
            
            // Show error
            this.showError('Seats no longer available. Please select again.');
            
            // Refresh seat map from server
            this.refreshSeatMap(showId);
        }
    }
    
    markSeatsAsBooked(seatIds) {
        seatIds.forEach(seatId => {
            const seat = document.getElementById('seat-' + seatId);
            seat.classList.remove('available');
            seat.classList.add('booked', 'optimistic');  // Visual indicator
            seat.disabled = true;
        });
    }
    
    markSeatsAsAvailable(seatIds) {
        seatIds.forEach(seatId => {
            const seat = document.getElementById('seat-' + seatId);
            seat.classList.remove('booked', 'optimistic');
            seat.classList.add('available');
            seat.disabled = false;
        });
    }
}
```

**Timeline:**

```
USER CLICKS "BOOK"
═══════════════════════════════════════════════════════════
0ms:   User clicks seats 5, 6
1ms:   UI instantly marks as booked (optimistic) ✅
       Show spinner "Booking..."
       
100ms: POST /api/bookings sent
       
200ms: Server response: SUCCESS
       Hide spinner
       Navigate to payment
       
FAILURE SCENARIO
═══════════════════════════════════════════════════════════
0ms:   User clicks seats 5, 6
1ms:   UI instantly marks as booked (optimistic) ✅
       Show spinner "Booking..."
       
100ms: POST /api/bookings sent
       
200ms: Server response: 409 CONFLICT (seats taken)
       Rollback: mark seats as available again ❌
       Show error: "Seats no longer available"
       Refresh seat map from server (latest state)
```

**Why This Works:**

```
✅ Perceived performance: User sees instant feedback
✅ Reality check: Server is source of truth
✅ Error handling: Clear rollback + error message
✅ State sync: Refresh from server after error
```

---
