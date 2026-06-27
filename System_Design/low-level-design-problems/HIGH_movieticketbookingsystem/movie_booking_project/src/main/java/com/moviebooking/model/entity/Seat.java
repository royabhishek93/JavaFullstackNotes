package com.moviebooking.model.entity;

import com.moviebooking.model.enums.SeatStatus;
import com.moviebooking.model.enums.SeatType;
import jakarta.persistence.*;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.NotBlank;
import lombok.*;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Entity
@Table(name = "seats", indexes = {
    @Index(name = "idx_seat_screen", columnList = "screen_id"),
    @Index(name = "idx_seat_status", columnList = "status"),
    @Index(name = "idx_seat_locked_until", columnList = "locked_until")
})
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Seat extends BaseEntity {

    @NotBlank(message = "Seat number is required")
    @Column(name = "seat_number", nullable = false)
    private String seatNumber;

    @NotBlank(message = "Row is required")
    @Column(nullable = false)
    private String row;

    @Column(name = "column_number", nullable = false)
    private Integer columnNumber;

    @Enumerated(EnumType.STRING)
    @Column(name = "seat_type", nullable = false)
    private SeatType seatType = SeatType.REGULAR;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private SeatStatus status = SeatStatus.AVAILABLE;

    @DecimalMin(value = "0.0", inclusive = false, message = "Price must be greater than 0")
    @Column(nullable = false, precision = 10, scale = 2)
    private BigDecimal basePrice;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "screen_id", nullable = false)
    private Screen screen;

    // Locking mechanism for concurrency control
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "locked_by_user_id")
    private User lockedBy;

    @Column(name = "locked_at")
    private LocalDateTime lockedAt;

    @Column(name = "locked_until")
    private LocalDateTime lockedUntil;

    /**
     * Check if seat can be locked
     */
    public boolean canBeLocked() {
        if (status == SeatStatus.AVAILABLE) {
            return true;
        }
        // If locked but lock expired
        return status == SeatStatus.LOCKED &&
               lockedUntil != null &&
               lockedUntil.isBefore(LocalDateTime.now());
    }

    /**
     * Check if lock is still valid
     */
    public boolean isLockValid() {
        return status == SeatStatus.LOCKED &&
               lockedUntil != null &&
               lockedUntil.isAfter(LocalDateTime.now());
    }
}
