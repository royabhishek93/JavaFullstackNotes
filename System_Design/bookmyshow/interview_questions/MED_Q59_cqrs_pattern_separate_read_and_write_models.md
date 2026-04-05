# Q59: CQRS Pattern - Separate read and write models

### Difficulty: ⭐⭐⭐⭐⭐ (Principal)

### ✅ Solution: Command-Query Separation

```java
// WRITE MODEL (Commands)
@Service
public class BookingCommandService {
    
    private final BookingRepository bookingRepository;
    private final EventPublisher eventPublisher;
    
    @Transactional
    public Booking createBooking(CreateBookingCommand command) {
        
        // Write to primary database (normalized)
        Booking booking = new Booking();
        booking.setId(UUID.randomUUID().toString());
        booking.setUserId(command.getUserId());
        booking.setShowId(command.getShowId());
        booking.setStatus(BookingStatus.PENDING);
        
        bookingRepository.save(booking);
        
        // Publish event for read model update
        eventPublisher.publish(new BookingCreatedEvent(booking));
        
        return booking;
    }
    
    @Transactional
    public void confirmBooking(ConfirmBookingCommand command) {
        
        Booking booking = bookingRepository
            .findById(command.getBookingId())
            .orElseThrow();
        
        booking.setStatus(BookingStatus.CONFIRMED);
        bookingRepository.save(booking);
        
        // Publish event
        eventPublisher.publish(new BookingConfirmedEvent(booking));
    }
}

// READ MODEL (Queries)
@Service
public class BookingQueryService {
    
    private final JdbcTemplate readTemplate;  // Read replica
    
    // Optimized for reading (denormalized)
    public BookingDetails getBookingDetails(String bookingId) {
        
        String sql = """
            SELECT 
                b.id,
                b.booking_date,
                b.total_price,
                u.name AS user_name,
                u.email AS user_email,
                m.title AS movie_title,
                t.name AS theater_name,
                s.show_date,
                s.start_time,
                GROUP_CONCAT(st.seat_row || st.seat_number) AS seats
            FROM booking_read_model b
            JOIN user_read_model u ON b.user_id = u.id
            JOIN show_read_model s ON b.show_id = s.id
            JOIN movie_read_model m ON s.movie_id = m.id
            JOIN theater_read_model t ON s.theater_id = t.id
            JOIN seat_read_model st ON st.booking_id = b.id
            WHERE b.id = ?
            GROUP BY b.id
        """;
        
        return readTemplate.queryForObject(sql, 
            new BookingDetailsRowMapper(), bookingId);
    }
    
    // Optimized query (single table)
    public List<UserBookingSummary> getUserBookings(Long userId) {
        
        String sql = """
            SELECT id, movie_title, theater_name, show_date, 
                   total_price, status
            FROM booking_read_model
            WHERE user_id = ?
            ORDER BY booking_date DESC
            LIMIT 50
        """;
        
        return readTemplate.query(sql, 
            new BookingSummaryRowMapper(), userId);
    }
}

// Event Handler (Updates Read Model)
@Component
public class BookingReadModelUpdater {
    
    @KafkaListener(topics = "booking-events")
    public void onBookingCreated(BookingCreatedEvent event) {
        
        // Fetch related data
        Show show = showService.getShow(event.getShowId());
        Movie movie = movieService.getMovie(show.getMovieId());
        Theater theater = theaterService.getTheater(show.getTheaterId());
        User user = userService.getUser(event.getUserId());
        
        // Insert into denormalized read model
        String sql = """
            INSERT INTO booking_read_model 
            (id, user_id, user_name, user_email, movie_title, 
             theater_name, show_date, total_price, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """;
        
        jdbcTemplate.update(sql,
            event.getBookingId(),
            user.getId(),
            user.getName(),
            user.getEmail(),
            movie.getTitle(),
            theater.getName(),
            show.getShowDate(),
            event.getTotalPrice(),
            "PENDING"
        );
    }
    
    @KafkaListener(topics = "booking-events")
    public void onBookingConfirmed(BookingConfirmedEvent event) {
        
        // Update read model
        String sql = """
            UPDATE booking_read_model 
            SET status = 'CONFIRMED', confirmed_at = NOW()
            WHERE id = ?
        """;
        
        jdbcTemplate.update(sql, event.getBookingId());
    }
}
```

**CQRS Architecture:**

```
WRITE SIDE (Commands)
═══════════════════════════════════════════════════════════
API → Command Handler → Write DB (Normalized)
                    ↓
                Event Bus (Kafka)
                    ↓
READ SIDE (Queries)
═══════════════════════════════════════════════════════════
              Read Model Updater → Read DB (Denormalized)
                                      ↑
                              API ← Query Handler


WRITE DB (Normalized)
═══════════════════════════════════════════════════════════
booking: id, user_id, show_id, status
booking_seat: booking_id, seat_id
seat: id, screen_id, row, number


READ DB (Denormalized for fast queries)
═══════════════════════════════════════════════════════════
booking_read_model:
  id, user_id, user_name, user_email,
  movie_title, theater_name, show_date, start_time,
  seats (comma-separated), total_price, status, confirmed_at

Benefits:
✅ Fast reads (no JOINs, single table scan)
✅ Independent scaling (scale read DB separately)
✅ Read replica can lag without affecting writes
```

---
