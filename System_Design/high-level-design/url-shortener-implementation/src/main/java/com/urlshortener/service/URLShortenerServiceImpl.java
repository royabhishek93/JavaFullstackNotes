package com.urlshortener.service;

import com.urlshortener.dto.*;
import com.urlshortener.entity.URLMapping;
import com.urlshortener.entity.URLStatus;
import com.urlshortener.exception.*;
import com.urlshortener.generator.ShortCodeGenerator;
import com.urlshortener.repository.URLRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.Optional;

/**
 * Implementation of URL shortener service with multi-layer caching,
 * security validation, and analytics tracking
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class URLShortenerServiceImpl implements URLShortenerService {

    private final ShortCodeGenerator shortCodeGenerator;
    private final URLRepository urlRepository;
    private final CacheService cacheService;
    private final AnalyticsService analyticsService;
    private final SecurityService securityService;
    private final RateLimiter rateLimiter;
    private final ValidationService validationService;
    private final UserService userService;

    @Override
    @Transactional
    public ShortURLResponse createShortURL(ShortURLRequest request) {
        log.info("Creating short URL for: {}", request.getLongURL());

        // 1. Rate limiting
        String userId = getCurrentUserId();
        if (!rateLimiter.allowRequest(userId)) {
            throw new RateLimitExceededException(
                "Rate limit exceeded. Please try again later."
            );
        }

        // 2. Validate URL format
        if (!validationService.isValidURL(request.getLongURL())) {
            throw new InvalidURLException("Invalid URL format");
        }

        // 3. Security check (malicious URL detection)
        if (!securityService.isSafeURL(request.getLongURL())) {
            throw new MaliciousURLException(
                "URL flagged as potentially malicious"
            );
        }

        // 4. Check for duplicates (idempotency)
        Optional<String> existingCode = checkDuplicate(request.getLongURL());
        if (existingCode.isPresent()) {
            log.info("URL already shortened: {}", existingCode.get());
            return buildResponse(urlRepository.findByShortCode(existingCode.get()).orElseThrow());
        }

        // 5. Generate short code
        String shortCode;
        if (request.getCustomAlias() != null) {
            // Custom alias requested
            if (!validationService.isValidAlias(request.getCustomAlias())) {
                throw new InvalidAliasException("Invalid alias format");
            }
            if (urlRepository.existsByShortCode(request.getCustomAlias())) {
                throw new AliasAlreadyExistsException(
                    "Alias already taken: " + request.getCustomAlias()
                );
            }
            shortCode = request.getCustomAlias();
        } else {
            // Generate unique short code
            shortCode = generateUniqueShortCode();
        }

        // 6. Create URL mapping entity
        URLMapping mapping = URLMapping.builder()
            .shortCode(shortCode)
            .longURL(request.getLongURL())
            .userId(getUserIdOrNull(userId))
            .createdAt(LocalDateTime.now())
            .expiresAt(request.getExpiresAt())
            .isCustomAlias(request.getCustomAlias() != null)
            .status(URLStatus.ACTIVE)
            .clickCount(0L)
            .build();

        // 7. Save to database
        URLMapping savedMapping = urlRepository.save(mapping);

        // 8. Cache the mapping (optional pre-population for premium users)
        if (isPremiumUser(userId)) {
            cacheService.put(shortCode, request.getLongURL());
        }

        // 9. Publish creation event for analytics
        analyticsService.publishCreationEvent(savedMapping);

        log.info("Short URL created: {} -> {}", shortCode, request.getLongURL());

        return buildResponse(savedMapping);
    }

    @Override
    public String getLongURL(String shortCode) {
        log.debug("Resolving short code: {}", shortCode);

        // 1. Check local in-memory cache (L1)
        Optional<String> cachedURL = cacheService.getFromLocalCache(shortCode);
        if (cachedURL.isPresent()) {
            log.debug("Cache hit (L1): {}", shortCode);
            return cachedURL.get();
        }

        // 2. Check Redis distributed cache (L2)
        cachedURL = cacheService.getFromRedis(shortCode);
        if (cachedURL.isPresent()) {
            log.debug("Cache hit (L2): {}", shortCode);
            // Populate L1 cache
            cacheService.putInLocalCache(shortCode, cachedURL.get());
            return cachedURL.get();
        }

        // 3. Cache miss - fetch from database (L3)
        log.debug("Cache miss - querying database: {}", shortCode);
        URLMapping mapping = urlRepository.findByShortCodeAndStatus(
            shortCode,
            URLStatus.ACTIVE
        ).orElseThrow(() -> new URLNotFoundException(
            "Short code not found: " + shortCode
        ));

        // 4. Check expiration
        if (mapping.isExpired()) {
            throw new URLExpiredException("This URL has expired");
        }

        String longURL = mapping.getLongURL();

        // 5. Populate caches (TTL: 1 hour for hot URLs)
        cacheService.putInRedis(shortCode, longURL, 3600); // 1 hour
        cacheService.putInLocalCache(shortCode, longURL);

        return longURL;
    }

    @Override
    public URLInfo getURLInfo(String shortCode) {
        URLMapping mapping = urlRepository.findByShortCode(shortCode)
            .orElseThrow(() -> new URLNotFoundException(
                "Short code not found: " + shortCode
            ));

        // Get real-time click count from Redis
        Long clickCount = analyticsService.getClickCount(shortCode);

        return URLInfo.builder()
            .shortCode(mapping.getShortCode())
            .longURL(mapping.getLongURL())
            .createdAt(mapping.getCreatedAt())
            .expiresAt(mapping.getExpiresAt())
            .clickCount(clickCount != null ? clickCount : mapping.getClickCount())
            .status(mapping.getStatus())
            .isCustomAlias(mapping.isCustomAlias())
            .build();
    }

    @Override
    @Transactional
    public void updateURL(String shortCode, UpdateURLRequest request) {
        URLMapping mapping = urlRepository.findByShortCode(shortCode)
            .orElseThrow(() -> new URLNotFoundException(
                "Short code not found: " + shortCode
            ));

        // Authorization check
        String currentUserId = getCurrentUserId();
        if (!isAuthorized(currentUserId, mapping)) {
            throw new UnauthorizedException(
                "You don't have permission to update this URL"
            );
        }

        // Update fields
        if (request.getNewLongURL() != null) {
            if (!validationService.isValidURL(request.getNewLongURL())) {
                throw new InvalidURLException("Invalid URL format");
            }
            mapping.setLongURL(request.getNewLongURL());
        }

        if (request.getNewExpiresAt() != null) {
            mapping.setExpiresAt(request.getNewExpiresAt());
        }

        urlRepository.save(mapping);

        // Invalidate cache
        cacheService.evict(shortCode);

        log.info("Updated URL mapping: {}", shortCode);
    }

    @Override
    @Transactional
    public void deleteURL(String shortCode) {
        URLMapping mapping = urlRepository.findByShortCode(shortCode)
            .orElseThrow(() -> new URLNotFoundException(
                "Short code not found: " + shortCode
            ));

        // Authorization check
        String currentUserId = getCurrentUserId();
        if (!isAuthorized(currentUserId, mapping)) {
            throw new UnauthorizedException(
                "You don't have permission to delete this URL"
            );
        }

        // Soft delete (mark as DELETED)
        mapping.setStatus(URLStatus.DELETED);
        urlRepository.save(mapping);

        // Invalidate cache
        cacheService.evict(shortCode);

        log.info("Deleted URL mapping: {}", shortCode);
    }

    @Override
    public AnalyticsResponse getAnalytics(String shortCode, AnalyticsFilter filter) {
        // Verify URL exists
        if (!urlRepository.existsByShortCode(shortCode)) {
            throw new URLNotFoundException("Short code not found: " + shortCode);
        }

        return analyticsService.getAnalytics(shortCode, filter);
    }

    // ========================================================================
    // Private Helper Methods
    // ========================================================================

    private String generateUniqueShortCode() {
        int maxRetries = 5;
        for (int i = 0; i < maxRetries; i++) {
            String shortCode = shortCodeGenerator.generate();
            if (!urlRepository.existsByShortCode(shortCode)) {
                return shortCode;
            }
            log.warn("Collision detected, retrying... (attempt {})", i + 1);
        }
        throw new ShortCodeGenerationException(
            "Failed to generate unique short code after " + maxRetries + " attempts"
        );
    }

    private Optional<String> checkDuplicate(String longURL) {
        // Check cache first
        Optional<String> cached = cacheService.getShortCodeByLongURL(longURL);
        if (cached.isPresent()) {
            return cached;
        }

        // Check database
        return urlRepository.findByLongURL(longURL)
            .map(URLMapping::getShortCode);
    }

    private ShortURLResponse buildResponse(URLMapping mapping) {
        String baseURL = getBaseURL(); // e.g., "https://short.ly"
        return ShortURLResponse.builder()
            .shortURL(baseURL + "/" + mapping.getShortCode())
            .shortCode(mapping.getShortCode())
            .longURL(mapping.getLongURL())
            .createdAt(mapping.getCreatedAt())
            .expiresAt(mapping.getExpiresAt())
            .build();
    }

    private String getCurrentUserId() {
        // Extract from Spring Security context or API key
        return SecurityContextHolder.getContext()
            .getAuthentication()
            .getName();
    }

    private Long getUserIdOrNull(String userId) {
        if ("anonymous".equals(userId)) {
            return null;
        }
        return Long.parseLong(userId);
    }

    private boolean isPremiumUser(String userId) {
        // Check user tier from database or cache
        return userService.getUserTier(userId) == UserTier.PREMIUM;
    }

    private boolean isAuthorized(String currentUserId, URLMapping mapping) {
        // Admins can modify any URL
        if (hasRole("ADMIN")) {
            return true;
        }

        // Users can only modify their own URLs
        return mapping.getUserId() != null &&
               mapping.getUserId().equals(Long.parseLong(currentUserId));
    }

    private boolean hasRole(String role) {
        return SecurityContextHolder.getContext()
            .getAuthentication()
            .getAuthorities()
            .stream()
            .anyMatch(auth -> auth.getAuthority().equals("ROLE_" + role));
    }

    private String getBaseURL() {
        return "https://short.ly"; // From configuration
    }
}
