package com.urlshortener.generator;

/**
 * Strategy interface for generating unique short codes
 * Implementations include: Snowflake, Redis Counter, Hash-based
 */
public interface ShortCodeGenerator {

    /**
     * Generates a unique 7-character short code
     * @return Base62 encoded short code (e.g., "aBc123X")
     */
    String generate();

    /**
     * Validates if a short code format is correct
     * @param shortCode The code to validate
     * @return true if valid
     */
    boolean isValid(String shortCode);
}
