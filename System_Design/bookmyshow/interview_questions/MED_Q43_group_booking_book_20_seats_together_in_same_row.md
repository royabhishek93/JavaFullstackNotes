# Q43: Group Booking - Book 20 seats together in same row

### Difficulty: ⭐⭐⭐⭐ (Staff)

### ✅ Solution: Contiguous Seat Allocation

```java
@Service
public class GroupBookingService {
    
    @Transactional
    public GroupBookingResponse bookGroupSeats(
            Long showId, 
            int seatCount,
            GroupPreferences preferences) {
        
        // Step 1: Find contiguous seats
        List<ContiguousSeats> options = findContiguousSeats(
            showId,
            seatCount,
            preferences
        );
        
        if (options.isEmpty()) {
            throw new NoContiguousSeatsException(
                "No " + seatCount + " contiguous seats available"
            );
        }
        
        // Step 2: Select best option
        ContiguousSeats bestOption = selectBestOption(options, preferences);
        
        // Step 3: Reserve all seats atomically
        List<Long> seatIds = bestOption.getSeatIds();
        
        int updated = seatRepository.reserveSeatsAtomic(
            showId,
            seatIds,
            bookingId,
            LocalDateTime.now().plusMinutes(15)
        );
        
        if (updated != seatIds.size()) {
            throw new ConcurrentBookingException(
                "Some seats were taken during booking"
            );
        }
        
        // Step 4: Create group booking
        Booking booking = new Booking();
        booking.setGroupBooking(true);
        booking.setTotalSeats(seatCount);
        // ... populate
        
        return GroupBookingResponse.success(booking, bestOption);
    }
    
    private List<ContiguousSeats> findContiguousSeats(
            Long showId,
            int requiredCount,
            GroupPreferences preferences) {
        
        List<ContiguousSeats> options = new ArrayList<>();
        
        // Get all seats for show
        List<SeatAvailability> allSeats = seatRepository
            .findByShowIdOrderByRowAndNumber(showId);
        
        // Group by row
        Map<String, List<SeatAvailability>> seatsByRow = allSeats.stream()
            .collect(Collectors.groupingBy(
                seat -> seat.getSeat().getSeatRow()
            ));
        
        // Find contiguous blocks in each row
        for (Map.Entry<String, List<SeatAvailability>> entry : 
                seatsByRow.entrySet()) {
            
            String row = entry.getKey();
            List<SeatAvailability> rowSeats = entry.getValue();
            
            // Sort by seat number
            rowSeats.sort(Comparator.comparing(
                seat -> seat.getSeat().getSeatNumber()
            ));
            
            // Find contiguous available seats
            List<SeatAvailability> currentBlock = new ArrayList<>();
            
            for (SeatAvailability seat : rowSeats) {
                if (seat.getStatus() == SeatStatus.AVAILABLE) {
                    // Check if contiguous with last seat
                    if (currentBlock.isEmpty() ||
                        isContiguous(currentBlock.get(currentBlock.size() - 1), seat)) {
                        currentBlock.add(seat);
                        
                        // Found enough contiguous seats
                        if (currentBlock.size() == requiredCount) {
                            options.add(new ContiguousSeats(
                                row,
                                currentBlock.stream()
                                    .map(SeatAvailability::getSeatId)
                                    .collect(Collectors.toList()),
                                calculateRowScore(row, preferences)
                            ));
                            
                            // Keep searching for more options
                            currentBlock.clear();
                        }
                    } else {
                        // Not contiguous, start new block
                        currentBlock.clear();
                        currentBlock.add(seat);
                    }
                } else {
                    // Seat taken, reset block
                    currentBlock.clear();
                }
            }
        }
        
        return options;
    }
    
    private boolean isContiguous(SeatAvailability seat1, SeatAvailability seat2) {
        // Check if seat2 is immediately after seat1
        return seat1.getSeat().getSeatRow()
                   .equals(seat2.getSeat().getSeatRow()) &&
               seat2.getSeat().getSeatNumber() == 
                   seat1.getSeat().getSeatNumber() + 1;
    }
    
    private ContiguousSeats selectBestOption(
            List<ContiguousSeats> options,
            GroupPreferences preferences) {
        
        // Sort by score (row preference)
        return options.stream()
            .max(Comparator.comparing(ContiguousSeats::getScore))
            .orElseThrow();
    }
    
    private double calculateRowScore(String row, GroupPreferences preferences) {
        // Row preferences: Middle rows better than front/back
        char rowChar = row.charAt(0);
        int rowNumber = rowChar - 'A';  // A=0, B=1, C=2, ...
        
        // Assume 10 rows total
        int totalRows = 10;
        int middleRow = totalRows / 2;
        
        // Distance from middle row
        double distanceFromMiddle = Math.abs(rowNumber - middleRow);
        
        // Score: closer to middle = higher score
        double score = 1.0 - (distanceFromMiddle / totalRows);
        
        // Apply user preferences
        if (preferences.getPreferredRow() != null &&
            preferences.getPreferredRow().equals(row)) {
            score += 0.5;  // Boost preferred row
        }
        
        return score;
    }
}

@Data
class ContiguousSeats {
    private final String row;
    private final List<Long> seatIds;
    private final double score;
}

@Data
class GroupPreferences {
    private String preferredRow;  // "D", "E", etc.
    private SeatType seatType;    // REGULAR, PREMIUM, RECLINER
}
```

**SQL Optimization:**

```sql
-- Find contiguous seats using window functions
WITH ranked_seats AS (
    SELECT 
        sa.show_id,
        s.seat_row,
        s.seat_number,
        sa.status,
        s.seat_number - ROW_NUMBER() OVER (
            PARTITION BY sa.show_id, s.seat_row 
            ORDER BY s.seat_number
        ) AS grp
    FROM seat_availability sa
    JOIN seat s ON sa.seat_id = s.id
    WHERE sa.show_id = 123
      AND sa.status = 'AVAILABLE'
),
contiguous_blocks AS (
    SELECT 
        show_id,
        seat_row,
        grp,
        COUNT(*) AS block_size,
        MIN(seat_number) AS start_seat,
        MAX(seat_number) AS end_seat
    FROM ranked_seats
    GROUP BY show_id, seat_row, grp
    HAVING COUNT(*) >= 20  -- Required seat count
)
SELECT * FROM contiguous_blocks
ORDER BY seat_row, start_seat;
```

---
