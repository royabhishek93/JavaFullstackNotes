# Q48: GDPR Compliance - Right to deletion, data export

### Difficulty: ⭐⭐⭐⭐ (Staff)

### ✅ Solution: Data Anonymization + Export

```java
@Service
public class GDPRComplianceService {
    
    // Right to be forgotten (Article 17)
    @Transactional
    public void deleteUserData(Long userId, DeletionRequest request) {
        
        User user = userRepository.findById(userId).orElseThrow();
        
        // Step 1: Validate deletion request
        if (hasPendingBookings(userId)) {
            throw new DeletionNotAllowedException(
                "Cannot delete account with pending bookings"
            );
        }
        
        // Step 2: Anonymize user data (don't hard delete)
        user.setEmail("deleted_" + userId + "@anonymized.com");
        user.setPhone("0000000000");
        user.setFullName("Deleted User");
        user.setDeleted(true);
        user.setDeletedAt(LocalDateTime.now());
        user.setDeletionReason(request.getReason());
        
        userRepository.save(user);
        
        // Step 3: Anonymize related data
        anonymizeBookingData(userId);
        anonymizePaymentData(userId);
        anonymizeAuditLogs(userId);
        
        // Step 4: Remove from search indexes
        elasticsearchService.deleteUserFromIndex(userId);
        
        // Step 5: Remove from cache
        cacheService.evict("user:" + userId);
        
        // Step 6: Schedule hard deletion after 30 days
        scheduledDeletionService.schedule(userId, 30);
        
        log.info("User data anonymized: userId={}", userId);
    }
    
    private void anonymizeBookingData(Long userId) {
        
        List<Booking> bookings = bookingRepository.findByUserId(userId);
        
        for (Booking booking : bookings) {
            // Keep booking ID and show info (for analytics)
            // Anonymize user reference
            booking.setUserId(null);  // Remove user link
            booking.setAnonymized(true);
        }
        
        bookingRepository.saveAll(bookings);
    }
    
    // Right to data portability (Article 20)
    public DataExportResponse exportUserData(Long userId) {
        
        User user = userRepository.findById(userId).orElseThrow();
        
        // Collect all user data
        UserDataExport export = UserDataExport.builder()
            .profile(UserProfileData.from(user))
            .bookings(exportBookings(userId))
            .payments(exportPayments(userId))
            .preferences(exportPreferences(userId))
            .auditLogs(exportAuditLogs(userId))
            .exportedAt(LocalDateTime.now())
            .build();
        
        // Generate downloadable file
        String json = JsonUtils.toJsonPretty(export);
        byte[] zipData = zipService.compress("user_data.json", json);
        
        // Store in S3 with expiring link
        String s3Key = "exports/" + userId + "/" + UUID.randomUUID() + ".zip";
        s3Client.putObject("bookmyshow-exports", s3Key, zipData);
        
        // Generate presigned URL (valid for 24 hours)
        String downloadUrl = s3Client.generatePresignedUrl(
            "bookmyshow-exports",
            s3Key,
            Duration.ofHours(24)
        );
        
        // Notify user
        emailService.sendDataExportEmail(user.getEmail(), downloadUrl);
        
        return DataExportResponse.builder()
            .downloadUrl(downloadUrl)
            .expiresAt(LocalDateTime.now().plusHours(24))
            .build();
    }
    
    private List<BookingData> exportBookings(Long userId) {
        return bookingRepository.findByUserId(userId)
            .stream()
            .map(booking -> BookingData.builder()
                .bookingId(booking.getId())
                .movieName(booking.getShow().getMovie().getTitle())
                .theaterName(booking.getShow().getTheater().getName())
                .showDate(booking.getShow().getShowDate())
                .showTime(booking.getShow().getStartTime())
                .seats(booking.getSeats().stream()
                    .map(seat -> seat.getSeatRow() + seat.getSeatNumber())
                    .collect(Collectors.toList()))
                .totalPrice(booking.getTotalPrice())
                .bookingDate(booking.getCreatedAt())
                .status(booking.getStatus())
                .build())
            .collect(Collectors.toList());
    }
}

@Data
@Builder
class UserDataExport {
    private UserProfileData profile;
    private List<BookingData> bookings;
    private List<PaymentData> payments;
    private PreferencesData preferences;
    private List<AuditLogData> auditLogs;
    private LocalDateTime exportedAt;
}
```

**GDPR Retention Policy:**

```sql
-- Retention periods
CREATE TABLE retention_policy (
    data_type VARCHAR(50) PRIMARY KEY,
    retention_days INT NOT NULL,
    deletion_method VARCHAR(20) NOT NULL  -- HARD, SOFT, ANONYMIZE
);

INSERT INTO retention_policy VALUES
    ('user_profile', 90, 'ANONYMIZE'),     -- 90 days after deletion request
    ('booking_data', 2555, 'ANONYMIZE'),   -- 7 years (tax law)
    ('payment_data', 2555, 'ANONYMIZE'),   -- 7 years (PCI requirement)
    ('audit_logs', 2555, 'HARD'),          -- 7 years
    ('session_logs', 90, 'HARD'),          -- 90 days
    ('marketing_consent', 0, 'HARD');      -- Immediate deletion
```

---
