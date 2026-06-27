package com.urlshortener.service;

import com.github.benmanes.caffeine.cache.Cache;
import com.github.benmanes.caffeine.cache.Caffeine;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.util.Optional;
import java.util.concurrent.TimeUnit;

/**
 * Multi-layer caching service
 * L1: Local in-memory cache (Caffeine) - ~1ms latency
 * L2: Distributed cache (Redis) - ~5ms latency
 * L3: Database - ~50ms latency
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class CacheService {

    private final RedisTemplate<String, String> redisTemplate;

    // L1 Cache: Local in-memory (Caffeine)
    // Size: 10,000 entries, TTL: 5 minutes
    private final Cache<String, String> localCache = Caffeine.newBuilder()
        .maximumSize(10_000)
        .expireAfterWrite(5, TimeUnit.MINUTES)
        .recordStats()
        .build();

    private static final String REDIS_KEY_PREFIX = "url:short:";
    private static final String REVERSE_KEY_PREFIX = "url:long:";

    /**
     * Gets value from local cache (L1)
     */
    public Optional<String> getFromLocalCache(String shortCode) {
        String value = localCache.getIfPresent(shortCode);
        if (value != null) {
            log.debug("Local cache hit: {}", shortCode);
        }
        return Optional.ofNullable(value);
    }

    /**
     * Gets value from Redis (L2)
     */
    public Optional<String> getFromRedis(String shortCode) {
        try {
            String key = REDIS_KEY_PREFIX + shortCode;
            String value = redisTemplate.opsForValue().get(key);

            if (value != null) {
                log.debug("Redis cache hit: {}", shortCode);
            }

            return Optional.ofNullable(value);
        } catch (Exception e) {
            log.error("Redis error: {}", e.getMessage());
            return Optional.empty();
        }
    }

    /**
     * Puts value in local cache
     */
    public void putInLocalCache(String shortCode, String longURL) {
        localCache.put(shortCode, longURL);
    }

    /**
     * Puts value in Redis with TTL
     */
    public void putInRedis(String shortCode, String longURL, long ttlSeconds) {
        try {
            String key = REDIS_KEY_PREFIX + shortCode;
            redisTemplate.opsForValue().set(key, longURL, Duration.ofSeconds(ttlSeconds));

            // Also cache reverse mapping for duplicate detection
            String reverseKey = REVERSE_KEY_PREFIX + longURL;
            redisTemplate.opsForValue().set(reverseKey, shortCode, Duration.ofHours(24));

            log.debug("Cached in Redis: {} -> {}", shortCode, longURL);
        } catch (Exception e) {
            log.error("Failed to cache in Redis: {}", e.getMessage());
        }
    }

    /**
     * Puts value in both L1 and L2 caches
     */
    public void put(String shortCode, String longURL) {
        putInLocalCache(shortCode, longURL);
        putInRedis(shortCode, longURL, 3600); // 1 hour default TTL
    }

    /**
     * Gets short code by long URL (for duplicate detection)
     */
    public Optional<String> getShortCodeByLongURL(String longURL) {
        try {
            String key = REVERSE_KEY_PREFIX + longURL;
            String shortCode = redisTemplate.opsForValue().get(key);
            return Optional.ofNullable(shortCode);
        } catch (Exception e) {
            log.error("Redis error: {}", e.getMessage());
            return Optional.empty();
        }
    }

    /**
     * Evicts entry from all cache layers
     */
    public void evict(String shortCode) {
        // Evict from local cache
        localCache.invalidate(shortCode);

        // Evict from Redis
        try {
            String key = REDIS_KEY_PREFIX + shortCode;
            redisTemplate.delete(key);
            log.debug("Evicted from cache: {}", shortCode);
        } catch (Exception e) {
            log.error("Failed to evict from Redis: {}", e.getMessage());
        }
    }

    /**
     * Gets cache statistics (for monitoring)
     */
    public CacheStats getStats() {
        com.github.benmanes.caffeine.cache.stats.CacheStats stats = localCache.stats();

        return CacheStats.builder()
            .l1Size(localCache.estimatedSize())
            .l1HitRate(stats.hitRate())
            .l1HitCount(stats.hitCount())
            .l1MissCount(stats.missCount())
            .l1EvictionCount(stats.evictionCount())
            .build();
    }
}
