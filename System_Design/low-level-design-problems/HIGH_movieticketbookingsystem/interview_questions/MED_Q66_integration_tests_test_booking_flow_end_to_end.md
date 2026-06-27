# Q66: Integration Tests - Test booking flow end-to-end

**Difficulty:** ⭐⭐⭐ (Senior)

```java
@SpringBootTest(webEnvironment = WebEnvironment.RANDOM_PORT)
@Testcontainers
public class BookingIntegrationTest {
    
    @Container
    static PostgreSQLContainer<?> postgres = 
        new PostgreSQLContainer<>("postgres:15");
    
    @Container
    static GenericContainer<?> redis = 
        new GenericContainer<>("redis:7");
    
    @Autowired
    private TestRestTemplate restTemplate;
    
    @Test
    public void testCompleteBookingFlow() {
        
        // Step 1: Create user
        UserRequest userReq = new UserRequest("test@example.com", "password");
        ResponseEntity<User> userResp = restTemplate.postForEntity(
            "/api/users", userReq, User.class
        );
        assertEquals(201, userResp.getStatusCodeValue());
        Long userId = userResp.getBody().getId();
        
        // Step 2: Search shows
        ResponseEntity<ShowSearchResponse> showsResp = restTemplate.getForEntity(
            "/api/shows/search?city=Mumbai&movie=Avengers", 
            ShowSearchResponse.class
        );
        assertEquals(200, showsResp.getStatusCodeValue());
        Long showId = showsResp.getBody().getShows().get(0).getId();
        
        // Step 3: Get available seats
        ResponseEntity<SeatMapResponse> seatsResp = restTemplate.getForEntity(
            "/api/shows/" + showId + "/seats",
            SeatMapResponse.class
        );
        List<Long> availableSeats = seatsResp.getBody().getAvailableSeats();
        assertTrue(availableSeats.size() > 0);
        
        // Step 4: Create booking
        BookingRequest bookingReq = BookingRequest.builder()
            .userId(userId)
            .showId(showId)
            .seatIds(List.of(availableSeats.get(0), availableSeats.get(1)))
            .build();
        
        ResponseEntity<Booking> bookingResp = restTemplate.postForEntity(
            "/api/bookings", bookingReq, Booking.class
        );
        assertEquals(201, bookingResp.getStatusCodeValue());
        Booking booking = bookingResp.getBody();
        assertEquals(BookingStatus.PENDING, booking.getStatus());
        
        // Step 5: Process payment
        PaymentRequest paymentReq = PaymentRequest.builder()
            .bookingId(booking.getId())
            .paymentMethodId("pm_test_123")
            .amount(booking.getTotalPrice())
            .build();
        
        ResponseEntity<Payment> paymentResp = restTemplate.postForEntity(
            "/api/payments", paymentReq, Payment.class
        );
        assertEquals(200, paymentResp.getStatusCodeValue());
        
        // Step 6: Verify booking confirmed
        ResponseEntity<Booking> confirmedBooking = restTemplate.getForEntity(
            "/api/bookings/" + booking.getId(),
            Booking.class
        );
        assertEquals(BookingStatus.CONFIRMED, 
            confirmedBooking.getBody().getStatus());
        
        // Step 7: Verify seats marked as booked
        ResponseEntity<SeatMapResponse> updatedSeats = restTemplate.getForEntity(
            "/api/shows/" + showId + "/seats",
            SeatMapResponse.class
        );
        assertFalse(updatedSeats.getBody()
            .getAvailableSeats()
            .containsAll(List.of(availableSeats.get(0), availableSeats.get(1))));
    }
}
```

---
