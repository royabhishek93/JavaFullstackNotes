package com.moviebooking.service;

import com.moviebooking.exception.PaymentFailedException;
import com.moviebooking.exception.Resource NotFoundException;
import com.moviebooking.exception.SeatNotAvailableException;
import com.moviebooking.model.entity.*;
import com.moviebooking.model.enums.*;
import com.moviebooking.repository.*;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Isolation;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;

/**
 * Core booking service with thread-safe seat locking and payment processing.
 *
 * Key Design Decisions for 10 YOE Interview:
 * 1. Pessimistic locking with TTL to prevent double booking
 * 2. Transaction management with proper rollback on payment failure
 * 3. Idempotency support for retry scenarios
 * 4. Separation of concerns: locking, payment, and confirmation
 */
@Service
@Slf4j
@RequiredArgsConstructor
public class BookingService {

    private final SeatRepository seatRepository;
    private final BookingRepository bookingRepository;
    private final BookingSeatRepository bookingSeatRepository;
    private final ShowRepository showRepository;
    private final UserRepository userRepository;
    private final PaymentService paymentService;
    private final SeatLockService seatLockService;

    @Value("${app.booking.seat-lock-duration-minutes:10}")
    private int lockDurationMinutes;

    @Value("${app.booking.max-seats-per-booking:10}")
    private int maxSeatsPerBooking;

    /**
     * Main booking flow with proper concurrency control.
     *
     * Flow:
     * 1. Validate request (idempotency, seat count)
     * 2. Lock seats (with TTL)
     * 3. Process payment
     * 4. Confirm booking (or rollback on failure)
     *
     * @param userId User ID
     * @param showId Show ID
     * @param seatIds List of seat IDs to book
     * @param paymentMethod Payment method
     * @param idempotencyKey Unique key for idempotency
     * @return Confirmed booking
     */
    @Transactional(isolation = Isolation.READ_COMMITTED, rollbackFor = Exception.class)
    public Booking createBooking(
            UUID userId,
            UUID showId,
            List<UUID> seatIds,
            PaymentMethod paymentMethod,
            String idempotencyKey
    ) {
        log.info("Starting booking for user={}, show={}, seats={}, idempotencyKey={}",
                userId, showId, seatIds.size(), idempotencyKey);

        // Step 1: Check idempotency - prevent duplicate bookings
        Booking existingBooking = bookingRepository.findByIdempotencyKey(idempotencyKey);
        if (existingBooking != null) {
            log.info("Returning existing booking for idempotencyKey={}", idempotencyKey);
            return existingBooking;
        }

        // Step 2: Validate request
        validateBookingRequest(seatIds);

        // Step 3: Fetch entities
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new ResourceNotFoundException("User", userId));
        Show show = showRepository.findById(showId)
                .orElseThrow(() -> new ResourceNotFoundException("Show", showId));

        // Step 4: Lock seats (Critical Section - Pessimistic Locking)
        List<Seat> seats = lockSeats(show, seatIds, user);

        try {
            // Step 5: Calculate total amount
            BigDecimal totalAmount = calculateTotalAmount(seats, show);

            // Step 6: Create pending booking
            Booking booking = createPendingBooking(user, show, totalAmount, idempotencyKey);

            // Step 7: Link seats to booking
            linkSeatsToBooking(booking, seats, show);

            // Step 8: Process payment
            Payment payment = paymentService.processPayment(booking, paymentMethod, totalAmount);

            if (!payment.isSuccessful()) {
                throw new PaymentFailedException("Payment processing failed: " + payment.getGatewayResponse());
            }

            // Step 9: Confirm booking and mark seats as BOOKED
            confirmBooking(booking, seats);

            log.info("Booking completed successfully: bookingId={}, bookingCode={}",
                    booking.getId(), booking.getBookingCode());

            return booking;

        } catch (Exception e) {
            log.error("Booking failed, rolling back seat locks for show={}, seats={}",
                    showId, seatIds, e);
            // Rollback: Release locked seats
            releaseSeats(seats);
            throw e;
        }
    }

    /**
     * Lock seats with pessimistic locking to prevent race conditions.
     * Uses SELECT FOR UPDATE to acquire database-level locks.
     */
    private List<Seat> lockSeats(Show show, List<UUID> seatIds, User user) {
        LocalDateTime lockUntil = LocalDateTime.now().plusMinutes(lockDurationMinutes);

        // Acquire locks on seats (this will block other transactions)
        List<Seat> seats = seatRepository.findAllByIdForUpdate(seatIds);

        if (seats.size() != seatIds.size()) {
            throw new SeatNotAvailableException("Some seats not found");
        }

        // Validate and lock each seat
        for (Seat seat : seats) {
            if (!seat.canBeLocked()) {
                throw new SeatNotAvailableException(
                        String.format("Seat %s is not available", seat.getSeatNumber())
                );
            }

            // Lock the seat
            seat.setStatus(SeatStatus.LOCKED);
            seat.setLockedBy(user);
            seat.setLockedAt(LocalDateTime.now());
            seat.setLockedUntil(lockUntil);
        }

        seatRepository.saveAll(seats);

        log.info("Locked {} seats for user={}, lockUntil={}", seats.size(), user.getId(), lockUntil);

        return seats;
    }

    /**
     * Release locked seats (called on booking failure or timeout)
     */
    private void releaseSeats(List<Seat> seats) {
        for (Seat seat : seats) {
            if (seat.getStatus() == SeatStatus.LOCKED) {
                seat.setStatus(SeatStatus.AVAILABLE);
                seat.setLockedBy(null);
                seat.setLockedAt(null);
                seat.setLockedUntil(null);
            }
        }
        seatRepository.saveAll(seats);
        log.info("Released {} seats", seats.size());
    }

    /**
     * Confirm booking and mark seats as permanently BOOKED
     */
    private void confirmBooking(Booking booking, List<Seat> seats) {
        // Update booking status
        booking.setStatus(BookingStatus.CONFIRMED);
        booking.setBookingCode(generateBookingCode());
        bookingRepository.save(booking);

        // Mark seats as BOOKED (release locks)
        for (Seat seat : seats) {
            seat.setStatus(SeatStatus.BOOKED);
            seat.setLockedBy(null);
            seat.setLockedAt(null);
            seat.setLockedUntil(null);
        }
        seatRepository.saveAll(seats);

        // Update show available seats count
        Show show = booking.getShow();
        show.setAvailableSeats(show.getAvailableSeats() - seats.size());
        showRepository.save(show);
    }

    /**
     * Calculate total amount based on seat types and show pricing
     */
    private BigDecimal calculateTotalAmount(List<Seat> seats, Show show) {
        return seats.stream()
                .map(seat -> {
                    BigDecimal seatPrice = seat.getBasePrice()
                            .multiply(BigDecimal.valueOf(seat.getSeatType().getPriceMultiplier()));
                    return seatPrice.multiply(show.getBasePrice());
                })
                .reduce(BigDecimal.ZERO, BigDecimal::add);
    }

    /**
     * Create pending booking record
     */
    private Booking createPendingBooking(User user, Show show, BigDecimal totalAmount, String idempotencyKey) {
        Booking booking = Booking.builder()
                .user(user)
                .show(show)
                .status(BookingStatus.PENDING)
                .totalAmount(totalAmount)
                .idempotencyKey(idempotencyKey)
                .build();

        return bookingRepository.save(booking);
    }

    /**
     * Link seats to booking via BookingSeat join table
     */
    private void linkSeatsToBooking(Booking booking, List<Seat> seats, Show show) {
        for (Seat seat : seats) {
            BigDecimal seatPrice = seat.getBasePrice()
                    .multiply(BigDecimal.valueOf(seat.getSeatType().getPriceMultiplier()))
                    .multiply(show.getBasePrice());

            BookingSeat bookingSeat = BookingSeat.builder()
                    .booking(booking)
                    .seat(seat)
                    .price(seatPrice)
                    .build();

            bookingSeatRepository.save(bookingSeat);
        }
    }

    /**
     * Validate booking request
     */
    private void validateBookingRequest(List<UUID> seatIds) {
        if (seatIds == null || seatIds.isEmpty()) {
            throw new IllegalArgumentException("Seat IDs cannot be empty");
        }

        if (seatIds.size() > maxSeatsPerBooking) {
            throw new IllegalArgumentException(
                    String.format("Cannot book more than %d seats at once", maxSeatsPerBooking)
            );
        }
    }

    /**
     * Generate unique booking code (e.g., BK20260410ABCD)
     */
    private String generateBookingCode() {
        String timestamp = LocalDateTime.now().format(
                java.time.format.DateTimeFormatter.ofPattern("yyyyMMddHHmmss")
        );
        String random = UUID.randomUUID().toString().substring(0, 4).toUpperCase();
        return "BK" + timestamp + random;
    }

    /**
     * Cancel booking with refund
     */
    @Transactional
    public void cancelBooking(UUID bookingId, UUID userId) {
        Booking booking = bookingRepository.findById(bookingId)
                .orElseThrow(() -> new ResourceNotFoundException("Booking", bookingId));

        // Validate ownership
        if (!booking.getUser().getId().equals(userId)) {
            throw new IllegalArgumentException("User not authorized to cancel this booking");
        }

        if (!booking.canBeCancelled()) {
            throw new IllegalArgumentException(
                    String.format("Booking cannot be cancelled in status: %s", booking.getStatus())
            );
        }

        // Update booking status
        booking.setStatus(BookingStatus.CANCELLED);
        bookingRepository.save(booking);

        // Release seats
        List<Seat> seats = booking.getBookingSeats().stream()
                .map(BookingSeat::getSeat)
                .toList();

        for (Seat seat : seats) {
            seat.setStatus(SeatStatus.AVAILABLE);
        }
        seatRepository.saveAll(seats);

        // Process refund
        if (booking.getPayment() != null && booking.getPayment().isSuccessful()) {
            paymentService.processRefund(booking.getPayment());
        }

        log.info("Booking cancelled: bookingId={}", bookingId);
    }

    /**
     * Get booking by ID
     */
    @Transactional(readOnly = true)
    public Booking getBooking(UUID bookingId) {
        return bookingRepository.findById(bookingId)
                .orElseThrow(() -> new ResourceNotFoundException("Booking", bookingId));
    }

    /**
     * Get user bookings
     */
    @Transactional(readOnly = true)
    public List<Booking> getUserBookings(UUID userId) {
        return bookingRepository.findByUserIdOrderByCreatedAtDesc(userId);
    }
}
