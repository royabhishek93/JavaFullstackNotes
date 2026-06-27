package com.urlshortener.entity;

/**
 * URL status enumeration
 */
public enum URLStatus {
    /**
     * Active and accessible
     */
    ACTIVE,

    /**
     * Expired (past expiration date)
     */
    EXPIRED,

    /**
     * Soft deleted by user
     */
    DELETED
}
