package com.moviebooking.model.entity;

import jakarta.persistence.*;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import lombok.*;

import java.util.ArrayList;
import java.util.List;

@Entity
@Table(name = "movies", indexes = {
    @Index(name = "idx_movie_title", columnList = "title")
})
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Movie extends BaseEntity {

    @NotBlank(message = "Movie title is required")
    @Column(nullable = false)
    private String title;

    @Column(length = 2000)
    private String description;

    @Min(value = 1, message = "Duration must be at least 1 minute")
    @Column(nullable = false)
    private Integer durationMinutes;

    private String language;

    private String genre;

    private String rating;  // PG, PG-13, R, etc.

    @Column(name = "poster_url")
    private String posterUrl;

    @OneToMany(mappedBy = "movie", fetch = FetchType.LAZY)
    private List<Show> shows = new ArrayList<>();

    @Column(name = "is_active")
    private boolean isActive = true;
}
