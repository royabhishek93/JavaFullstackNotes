package com.moviebooking.model.entity;

import jakarta.persistence.*;
import lombok.*;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

@Entity
@Table(name = "shows", indexes = {
    @Index(name = "idx_show_movie", columnList = "movie_id"),
    @Index(name = "idx_show_screen", columnList = "screen_id"),
    @Index(name = "idx_show_time", columnList = "show_time")
})
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Show extends BaseEntity {

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "movie_id", nullable = false)
    private Movie movie;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "screen_id", nullable = false)
    private Screen screen;

    @Column(name = "show_time", nullable = false)
    private LocalDateTime showTime;

    @Column(name = "end_time", nullable = false)
    private LocalDateTime endTime;

    @Column(name = "base_price", nullable = false, precision = 10, scale = 2)
    private BigDecimal basePrice;

    @OneToMany(mappedBy = "show", cascade = CascadeType.ALL, fetch = FetchType.LAZY)
    private List<Booking> bookings = new ArrayList<>();

    @Column(name = "available_seats")
    private Integer availableSeats;

    @Column(name = "is_active")
    private boolean isActive = true;

    public boolean hasAvailableSeats() {
        return availableSeats != null && availableSeats > 0;
    }
}
