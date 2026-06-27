package com.urlshortener.generator;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Component;

/**
 * Redis atomic counter-based short code generator (RECOMMENDED)
 * Uses Redis INCR for globally unique, collision-free IDs
 *
 * Pros:
 * - No collisions (atomic increment)
 * - Simple implementation
 * - High availability with Redis Cluster
 *
 * Cons:
 * - Requires Redis connection
 * - Predictable sequences (can be mitigated with base62 encoding)
 */
@Slf4j
@Component("redisCounterGenerator")
@RequiredArgsConstructor
public class RedisCounterShortCodeGenerator implements ShortCodeGenerator {

    private static final String BASE62 =
        "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz";

    private static final int SHORT_CODE_LENGTH = 7;
    private static final String COUNTER_KEY = "url:shortener:counter";

    private final RedisTemplate<String, Long> redisTemplate;

    @Override
    public String generate() {
        // Atomically increment Redis counter
        Long id = redisTemplate.opsForValue().increment(COUNTER_KEY, 1);

        if (id == null) {
            throw new RuntimeException("Failed to generate ID from Redis counter");
        }

        log.debug("Generated ID: {}", id);

        return toBase62(id, SHORT_CODE_LENGTH);
    }

    @Override
    public boolean isValid(String shortCode) {
        if (shortCode == null || shortCode.length() != SHORT_CODE_LENGTH) {
            return false;
        }
        return shortCode.chars().allMatch(c -> BASE62.indexOf(c) >= 0);
    }

    /**
     * Converts a long number to Base62 string
     *
     * @param num The number to encode
     * @param length Target length (pads with zeros if needed)
     * @return Base62 encoded string
     */
    private String toBase62(long num, int length) {
        if (num == 0) {
            return "0".repeat(length);
        }

        StringBuilder sb = new StringBuilder();
        while (num > 0) {
            int remainder = (int) (num % 62);
            sb.append(BASE62.charAt(remainder));
            num /= 62;
        }

        String result = sb.reverse().toString();
        if (result.length() < length) {
            result = "0".repeat(length - result.length()) + result;
        }

        return result;
    }

    /**
     * Gets current counter value (for monitoring)
     */
    public Long getCurrentCounter() {
        return redisTemplate.opsForValue().get(COUNTER_KEY);
    }

    /**
     * Sets initial counter value (use carefully!)
     */
    public void setCounter(Long value) {
        redisTemplate.opsForValue().set(COUNTER_KEY, value);
        log.warn("Counter manually set to: {}", value);
    }
}
