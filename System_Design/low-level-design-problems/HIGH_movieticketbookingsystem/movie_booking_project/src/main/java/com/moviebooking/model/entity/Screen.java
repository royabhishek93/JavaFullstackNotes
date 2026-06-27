package com.moviebooking.model.entity;

import jakarta.persistence.*;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import lombok.*;

import java.util.ArrayList;
import java.util.List;

@Entity
@Table(name = "screens", indexes = {
    @Index(name = "idx_screen_theater", columnList = "theater_id")
})
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Screen extends BaseEntity {

    @NotBlank(message = "Screen name is required")
    @Column(nullable = false)
    private String name;

    @Min(value = 1, message = "Total seats must be at least 1")
    @Column(name = "total_seats", nullable = false)
    private Integer totalSeats;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "theater_id", nullable = false)
    private Theater theater;

    @OneToMany(mappedBy = "screen", cascade = CascadeType.ALL, fetch = FetchType.LAZY)
    private List<Seat> seats = new ArrayList<>();

    @OneToMany(mappedBy = "screen", fetch = FetchType.LAZY)
    private List<Show> shows = new ArrayList<>();

    @Column(name = "is_active")
    private boolean isActive = true;
}
