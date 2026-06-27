package com.urlshortener.entity;

import lombok.*;

import javax.persistence.*;
import java.time.LocalDateTime;

/**
 * URL Mapping entity - stores short code to long URL mappings
 * Indexed for fast lookups by short_code
 */
@Entity
@Table(
    name = "url_mappings",
    indexes = {
        @Index(name = "idx_short_code", columnList = "short_code", unique = true),
        @Index(name = "idx_user_id", columnList = "user_id"),
        @Index(name = "idx_created_at", columnList = "created_at"),
        @Index(name = "idx_expires_at", columnList = "expires_at")
    }
)
@Getter
@Setter
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class URLMapping {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "short_code", nullable = false, unique = true, length = 10)
    private String shortCode;

    @Column(name = "long_url", nullable = false, columnDefinition = "TEXT")
    private String longURL;

    @Column(name = "user_id")
    private Long userId;

    @Column(name = "created_at", nullable = false)
    private LocalDateTime createdAt;

    @Column(name = "expires_at")
    private LocalDateTime expiresAt;

    @Column(name = "is_custom_alias")
    private Boolean isCustomAlias;

    @Enumerated(EnumType.STRING)
    @Column(name = "status", nullable = false)
    private URLStatus status;

    @Column(name = "click_count")
    private Long clickCount;

    /**
     * Checks if URL has expired
     */
    public boolean isExpired() {
        return expiresAt != null && LocalDateTime.now().isAfter(expiresAt);
    }

    /**
     * Increments click count (for database-level tracking)
     */
    public void incrementClickCount() {
        this.clickCount = (this.clickCount != null ? this.clickCount : 0L) + 1;
    }
}
