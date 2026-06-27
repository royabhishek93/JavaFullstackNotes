package com.urlshortener.service;

import com.urlshortener.dto.*;
import com.urlshortener.exception.*;

/**
 * Main service interface for URL shortening operations
 * Handles creation, retrieval, updates, and analytics for short URLs
 */
public interface URLShortenerService {

    /**
     * Creates a short URL from a long URL
     * @param request Contains long URL, custom alias (optional), expiry (optional)
     * @return Short URL details including the generated short code
     * @throws InvalidURLException if URL is malformed or malicious
     * @throws AliasAlreadyExistsException if custom alias is taken
     * @throws RateLimitExceededException if user exceeded rate limit
     */
    ShortURLResponse createShortURL(ShortURLRequest request);

    /**
     * Retrieves the long URL for a given short code
     * @param shortCode The 7-character short code
     * @return The original long URL
     * @throws URLNotFoundException if short code doesn't exist
     * @throws URLExpiredException if URL has expired
     */
    String getLongURL(String shortCode);

    /**
     * Gets detailed information about a URL
     * @param shortCode The short code
     * @return URL metadata and statistics
     */
    URLInfo getURLInfo(String shortCode);

    /**
     * Updates an existing URL mapping
     * @param shortCode The short code to update
     * @param request Update parameters (new long URL, new expiry)
     * @throws URLNotFoundException if short code doesn't exist
     * @throws UnauthorizedException if user doesn't own the URL
     */
    void updateURL(String shortCode, UpdateURLRequest request);

    /**
     * Soft deletes a URL (marks as DELETED status)
     * @param shortCode The short code to delete
     * @throws URLNotFoundException if short code doesn't exist
     */
    void deleteURL(String shortCode);

    /**
     * Retrieves analytics for a URL
     * @param shortCode The short code
     * @param filter Date range and grouping options
     * @return Aggregated click statistics
     */
    AnalyticsResponse getAnalytics(String shortCode, AnalyticsFilter filter);
}
