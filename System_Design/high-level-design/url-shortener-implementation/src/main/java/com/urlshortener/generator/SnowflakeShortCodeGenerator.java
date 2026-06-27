package com.urlshortener.generator;

import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

/**
 * Twitter Snowflake-based short code generator
 * Generates unique IDs using timestamp + machine ID + sequence
 *
 * 64-bit ID structure:
 * - 1 bit: unused (always 0)
 * - 41 bits: timestamp (milliseconds since EPOCH)
 * - 10 bits: machine ID (0-1023)
 * - 12 bits: sequence number (0-4095)
 */
@Slf4j
@Component("snowflakeGenerator")
public class SnowflakeShortCodeGenerator implements ShortCodeGenerator {

    // Base62 characters (0-9, A-Z, a-z)
    private static final String BASE62 =
        "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz";

    private static final int SHORT_CODE_LENGTH = 7;

    // Snowflake components
    private static final long EPOCH = 1704067200000L; // 2024-01-01 00:00:00 UTC
    private static final long MACHINE_ID_BITS = 10L;
    private static final long SEQUENCE_BITS = 12L;

    private static final long MAX_MACHINE_ID = (1L << MACHINE_ID_BITS) - 1;
    private static final long MAX_SEQUENCE = (1L << SEQUENCE_BITS) - 1;

    private static final long MACHINE_ID_SHIFT = SEQUENCE_BITS;
    private static final long TIMESTAMP_SHIFT = MACHINE_ID_BITS + SEQUENCE_BITS;

    private final long machineId;
    private long sequence = 0L;
    private long lastTimestamp = -1L;

    public SnowflakeShortCodeGenerator() {
        // Machine ID from environment variable or random
        this.machineId = getMachineId();
        log.info("Initialized SnowflakeGenerator with machineId: {}", machineId);
    }

    @Override
    public synchronized String generate() {
        long id = nextId();
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
     * Generates next unique 64-bit ID using Snowflake algorithm
     *
     * @return Unique 64-bit ID
     */
    private synchronized long nextId() {
        long timestamp = System.currentTimeMillis();

        // Clock moved backwards - wait until it catches up
        if (timestamp < lastTimestamp) {
            long diff = lastTimestamp - timestamp;
            log.error("Clock moved backwards by {} ms", diff);
            throw new RuntimeException(
                "Clock moved backwards. Refusing to generate ID for " + diff + " ms"
            );
        }

        // Same millisecond - increment sequence
        if (timestamp == lastTimestamp) {
            sequence = (sequence + 1) & MAX_SEQUENCE;

            // Sequence overflow - wait for next millisecond
            if (sequence == 0) {
                timestamp = waitNextMillis(lastTimestamp);
            }
        } else {
            // New millisecond - reset sequence
            sequence = 0L;
        }

        lastTimestamp = timestamp;

        // Construct 64-bit ID
        return ((timestamp - EPOCH) << TIMESTAMP_SHIFT)
             | (machineId << MACHINE_ID_SHIFT)
             | sequence;
    }

    /**
     * Waits until next millisecond
     */
    private long waitNextMillis(long lastTimestamp) {
        long timestamp = System.currentTimeMillis();
        while (timestamp <= lastTimestamp) {
            timestamp = System.currentTimeMillis();
        }
        return timestamp;
    }

    /**
     * Converts a long ID to Base62 string
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

        // Reverse and pad with leading zeros if needed
        String result = sb.reverse().toString();
        if (result.length() < length) {
            result = "0".repeat(length - result.length()) + result;
        }

        return result;
    }

    /**
     * Gets machine ID from environment or generates random
     */
    private long getMachineId() {
        String machineIdStr = System.getenv("MACHINE_ID");
        if (machineIdStr != null) {
            long id = Long.parseLong(machineIdStr);
            if (id >= 0 && id <= MAX_MACHINE_ID) {
                return id;
            }
        }

        // Generate random machine ID (not ideal for production)
        long randomId = (long) (Math.random() * MAX_MACHINE_ID);
        log.warn("Using random machine ID: {}. " +
                 "Set MACHINE_ID env variable for production!", randomId);
        return randomId;
    }
}
