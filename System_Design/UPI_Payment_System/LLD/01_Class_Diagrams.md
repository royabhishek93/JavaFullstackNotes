# Low-Level Design - Class Diagrams & Core Implementation

## 1. Core Domain Classes

### 1.1 User & Account Domain

```java
/**
 * User entity representing UPI system user
 */
@Entity
@Table(name = "users")
public class User {
    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID userId;
    
    @Column(unique = true, nullable = false)
    private String phoneNumber;
    
    private String email;
    private String name;
    
    @Enumerated(EnumType.STRING)
    private KYCStatus kycStatus;
    
    @OneToMany(mappedBy = "user", cascade = CascadeType.ALL)
    private List<UPIHandle> upiHandles;
    
    @OneToMany(mappedBy = "user")
    private List<BankAccount> bankAccounts;
    
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
    
    // Getters, setters, constructors
}

/**
 * UPI Handle (Virtual Payment Address)
 */
@Entity
@Table(name = "upi_handles")
public class UPIHandle {
    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID handleId;
    
    @ManyToOne
    @JoinColumn(name = "user_id")
    private User user;
    
    @Column(unique = true, nullable = false)
    private String vpa; // user@bank
    
    private String bankCode;
    private boolean isPrimary;
    private boolean isActive;
    
    private LocalDateTime createdAt;
    
    // Business methods
    public boolean isValid() {
        return isActive && vpa.matches("^[a-zA-Z0-9._-]+@[a-zA-Z]+$");
    }
}

/**
 * Bank Account linked to user
 */
@Entity
@Table(name = "bank_accounts")
public class BankAccount {
    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID accountId;
    
    @ManyToOne
    @JoinColumn(name = "user_id")
    private User user;
    
    @ManyToOne
    @JoinColumn(name = "handle_id")
    private UPIHandle upiHandle;
    
    @Column(nullable = false)
    private String accountNumber;
    
    private String ifscCode;
    private String bankName;
    
    @Enumerated(EnumType.STRING)
    private AccountType accountType; // SAVINGS, CURRENT
    
    private BigDecimal cachedBalance; // For display only
    private boolean isPrimary;
    
    private LocalDateTime createdAt;
}

public enum KYCStatus {
    PENDING, VERIFIED, REJECTED, EXPIRED
}

public enum AccountType {
    SAVINGS, CURRENT, WALLET
}
```

### 1.2 Transaction Domain

```java
/**
 * Core transaction entity
 */
@Entity
@Table(name = "transactions", indexes = {
    @Index(name = "idx_sender", columnList = "sender_account_id,created_at"),
    @Index(name = "idx_receiver", columnList = "receiver_account_id,created_at"),
    @Index(name = "idx_npci", columnList = "npci_transaction_id", unique = true)
})
public class Transaction {
    @Id
    private String transactionId; // UUID generated
    
    @ManyToOne
    @JoinColumn(name = "sender_account_id")
    private BankAccount senderAccount;
    
    @ManyToOne
    @JoinColumn(name = "receiver_account_id")
    private BankAccount receiverAccount;
    
    private String senderVPA;
    private String receiverVPA;
    
    @Column(precision = 18, scale = 2)
    private BigDecimal amount;
    
    private String currency = "INR";
    
    @Enumerated(EnumType.STRING)
    private TransactionType transactionType;
    
    @Enumerated(EnumType.STRING)
    private TransactionStatus status;
    
    private String npciTransactionId;
    private String pspRefNumber;
    private String transactionNote;
    
    private LocalDateTime initiatedAt;
    private LocalDateTime completedAt;
    private String failureReason;
    
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
    
    // State transition method
    public void updateStatus(TransactionStatus newStatus, String reason) {
        if (!this.status.canTransitionTo(newStatus)) {
            throw new IllegalStateException(
                String.format("Invalid state transition from %s to %s", 
                    this.status, newStatus)
            );
        }
        this.status = newStatus;
        this.updatedAt = LocalDateTime.now();
        
        if (newStatus == TransactionStatus.SUCCESS || 
            newStatus == TransactionStatus.FAILED) {
            this.completedAt = LocalDateTime.now();
            this.failureReason = reason;
        }
    }
    
    // Business validation
    public void validate() {
        if (amount.compareTo(BigDecimal.ZERO) <= 0) {
            throw new ValidationException("Amount must be positive");
        }
        if (amount.compareTo(new BigDecimal("100000")) > 0) {
            throw new ValidationException("Amount exceeds limit");
        }
        if (senderVPA.equals(receiverVPA)) {
            throw new ValidationException("Cannot transfer to self");
        }
    }
}

public enum TransactionType {
    P2P,        // Person to Person
    P2M,        // Person to Merchant
    BILL_PAY,   // Bill Payment
    REFUND,     // Refund/Reversal
    REQUEST     // Money Request
}

public enum TransactionStatus {
    INITIATED {
        @Override
        public boolean canTransitionTo(TransactionStatus newStatus) {
            return newStatus == VALIDATING || newStatus == FAILED;
        }
    },
    VALIDATING {
        @Override
        public boolean canTransitionTo(TransactionStatus newStatus) {
            return newStatus == PENDING || newStatus == FAILED;
        }
    },
    PENDING {
        @Override
        public boolean canTransitionTo(TransactionStatus newStatus) {
            return newStatus == PREPARED || newStatus == FAILED || 
                   newStatus == PENDING_TIMEOUT;
        }
    },
    PREPARED {
        @Override
        public boolean canTransitionTo(TransactionStatus newStatus) {
            return newStatus == DEBITED || newStatus == FAILED;
        }
    },
    DEBITED {
        @Override
        public boolean canTransitionTo(TransactionStatus newStatus) {
            return newStatus == CREDITED || newStatus == REVERSING;
        }
    },
    CREDITED {
        @Override
        public boolean canTransitionTo(TransactionStatus newStatus) {
            return newStatus == SUCCESS;
        }
    },
    SUCCESS {
        @Override
        public boolean canTransitionTo(TransactionStatus newStatus) {
            return false; // Terminal state
        }
    },
    FAILED {
        @Override
        public boolean canTransitionTo(TransactionStatus newStatus) {
            return newStatus == REVERSING; // Can attempt reversal
        }
    },
    REVERSING {
        @Override
        public boolean canTransitionTo(TransactionStatus newStatus) {
            return newStatus == REVERSED || newStatus == REVERSAL_FAILED;
        }
    },
    REVERSED {
        @Override
        public boolean canTransitionTo(TransactionStatus newStatus) {
            return false; // Terminal state
        }
    },
    PENDING_TIMEOUT,
    REVERSAL_FAILED;
    
    public abstract boolean canTransitionTo(TransactionStatus newStatus);
}
```

### 1.3 Payment Request/Response Models

```java
/**
 * Payment initiation request
 */
@Data
@Validated
public class PaymentRequest {
    @NotBlank
    private String senderVPA;
    
    @NotBlank
    private String receiverVPA;
    
    @NotNull
    @DecimalMin(value = "0.01")
    @DecimalMax(value = "100000.00")
    private BigDecimal amount;
    
    @NotBlank
    @Size(min = 4, max = 6)
    private String encryptedMPIN; // Client-side encrypted
    
    private String transactionNote;
    
    @NotBlank
    private String deviceId; // For device binding
    
    @NotBlank
    private String idempotencyKey; // Client-generated UUID
    
    private TransactionType transactionType = TransactionType.P2P;
}

/**
 * Payment response
 */
@Data
public class PaymentResponse {
    private String transactionId;
    private TransactionStatus status;
    private String message;
    private BigDecimal amount;
    private String receiverName;
    private LocalDateTime timestamp;
    private String referenceNumber;
}

/**
 * Transaction status query request
 */
@Data
public class TransactionStatusRequest {
    private String transactionId;
    private String userId;
}
```

## 2. Service Layer Classes

### 2.1 Payment Service

```java
@Service
@Slf4j
public class PaymentService {
    
    private final TransactionRepository transactionRepository;
    private final VPAResolutionService vpaResolutionService;
    private final AuthService authService;
    private final NPCIAdapterService npciAdapter;
    private final IdempotencyService idempotencyService;
    private final FraudDetectionService fraudDetectionService;
    private final EventPublisher eventPublisher;
    
    /**
     * Initiate payment transaction
     */
    @Transactional
    public PaymentResponse initiatePayment(PaymentRequest request) {
        log.info("Payment initiated: {} -> {}, amount: {}", 
            request.getSenderVPA(), request.getReceiverVPA(), request.getAmount());
        
        // 1. Check idempotency
        Optional<Transaction> existingTxn = 
            idempotencyService.checkIdempotency(request.getIdempotencyKey());
        if (existingTxn.isPresent()) {
            log.info("Duplicate request detected: {}", request.getIdempotencyKey());
            return buildResponse(existingTxn.get());
        }
        
        // 2. Create transaction record
        Transaction transaction = createTransaction(request);
        transaction.updateStatus(TransactionStatus.INITIATED, null);
        transactionRepository.save(transaction);
        
        try {
            // 3. Validate VPAs
            BankAccount senderAccount = 
                vpaResolutionService.resolveVPA(request.getSenderVPA());
            BankAccount receiverAccount = 
                vpaResolutionService.resolveVPA(request.getReceiverVPA());
            
            transaction.setSenderAccount(senderAccount);
            transaction.setReceiverAccount(receiverAccount);
            transaction.updateStatus(TransactionStatus.VALIDATING, null);
            
            // 4. Authenticate user (MPIN validation)
            authService.validateMPIN(
                senderAccount.getUser(), 
                request.getEncryptedMPIN(), 
                request.getDeviceId()
            );
            
            // 5. Fraud detection check
            FraudScore fraudScore = 
                fraudDetectionService.assessRisk(transaction);
            if (fraudScore.isHighRisk()) {
                throw new FraudDetectedException(
                    "Transaction blocked by fraud detection"
                );
            }
            
            // 6. Execute transaction via NPCI
            transaction.updateStatus(TransactionStatus.PENDING, null);
            transactionRepository.save(transaction);
            
            NPCIResponse npciResponse = 
                npciAdapter.executeTransaction(transaction);
            
            // 7. Update status based on response
            if (npciResponse.isSuccess()) {
                transaction.setNpciTransactionId(npciResponse.getTransactionId());
                transaction.updateStatus(TransactionStatus.SUCCESS, null);
                
                // Publish success event
                eventPublisher.publish(
                    new TransactionSuccessEvent(transaction)
                );
            } else {
                transaction.updateStatus(
                    TransactionStatus.FAILED, 
                    npciResponse.getErrorMessage()
                );
            }
            
        } catch (VPANotFoundException | MPINValidationException e) {
            log.error("Validation failed: {}", e.getMessage());
            transaction.updateStatus(TransactionStatus.FAILED, e.getMessage());
            throw new PaymentException(e.getMessage(), e);
            
        } catch (Exception e) {
            log.error("Payment processing failed", e);
            transaction.updateStatus(TransactionStatus.FAILED, "System error");
            
            // Attempt reversal if needed
            attemptReversal(transaction);
            throw new PaymentException("Payment failed", e);
            
        } finally {
            transactionRepository.save(transaction);
            idempotencyService.recordTransaction(
                request.getIdempotencyKey(), 
                transaction
            );
        }
        
        return buildResponse(transaction);
    }
    
    /**
     * Query transaction status
     */
    @Transactional(readOnly = true)
    public TransactionStatus getTransactionStatus(String transactionId) {
        Transaction transaction = transactionRepository
            .findById(transactionId)
            .orElseThrow(() -> new TransactionNotFoundException(transactionId));
        
        return transaction.getStatus();
    }
    
    /**
     * Attempt reversal for failed transaction
     */
    private void attemptReversal(Transaction transaction) {
        if (transaction.getStatus() == TransactionStatus.DEBITED) {
            transaction.updateStatus(TransactionStatus.REVERSING, null);
            eventPublisher.publish(
                new ReversalRequiredEvent(transaction)
            );
        }
    }
    
    private Transaction createTransaction(PaymentRequest request) {
        Transaction txn = new Transaction();
        txn.setTransactionId(UUID.randomUUID().toString());
        txn.setSenderVPA(request.getSenderVPA());
        txn.setReceiverVPA(request.getReceiverVPA());
        txn.setAmount(request.getAmount());
        txn.setTransactionType(request.getTransactionType());
        txn.setTransactionNote(request.getTransactionNote());
        txn.setInitiatedAt(LocalDateTime.now());
        txn.setCreatedAt(LocalDateTime.now());
        return txn;
    }
    
    private PaymentResponse buildResponse(Transaction transaction) {
        PaymentResponse response = new PaymentResponse();
        response.setTransactionId(transaction.getTransactionId());
        response.setStatus(transaction.getStatus());
        response.setAmount(transaction.getAmount());
        response.setTimestamp(transaction.getCompletedAt());
        
        if (transaction.getStatus() == TransactionStatus.SUCCESS) {
            response.setMessage("Payment successful");
        } else {
            response.setMessage(transaction.getFailureReason());
        }
        
        return response;
    }
}
```

### 2.2 Two-Phase Commit Coordinator

```java
@Service
@Slf4j
public class TwoPhaseCommitCoordinator {
    
    private final NPCIAdapterService npciAdapter;
    private final TransactionRepository transactionRepository;
    
    /**
     * Execute distributed transaction using 2PC protocol
     */
    public boolean executeDistributedTransaction(Transaction transaction) {
        String txnId = transaction.getTransactionId();
        log.info("Starting 2PC for transaction: {}", txnId);
        
        try {
            // PHASE 1: PREPARE
            log.info("Phase 1: Prepare - {}", txnId);
            
            // Prepare sender bank (lock funds)
            PrepareResponse senderPrepare = 
                npciAdapter.prepareSenderBank(transaction);
            
            if (!senderPrepare.isReady()) {
                log.error("Sender prepare failed: {}", senderPrepare.getReason());
                rollback(transaction, Phase.PREPARE);
                return false;
            }
            
            transaction.updateStatus(TransactionStatus.PREPARED, null);
            transactionRepository.save(transaction);
            
            // Prepare receiver bank (validate account)
            PrepareResponse receiverPrepare = 
                npciAdapter.prepareReceiverBank(transaction);
            
            if (!receiverPrepare.isReady()) {
                log.error("Receiver prepare failed: {}", receiverPrepare.getReason());
                rollback(transaction, Phase.PREPARE);
                return false;
            }
            
            // PHASE 2: COMMIT
            log.info("Phase 2: Commit - {}", txnId);
            
            // Commit debit
            CommitResponse senderCommit = 
                npciAdapter.commitSenderBank(transaction);
            
            if (!senderCommit.isSuccess()) {
                log.error("Sender commit failed: {}", senderCommit.getReason());
                rollback(transaction, Phase.COMMIT);
                return false;
            }
            
            transaction.updateStatus(TransactionStatus.DEBITED, null);
            transactionRepository.save(transaction);
            
            // Commit credit
            CommitResponse receiverCommit = 
                npciAdapter.commitReceiverBank(transaction);
            
            if (!receiverCommit.isSuccess()) {
                log.error("Receiver commit failed - CRITICAL: {}", 
                    receiverCommit.getReason());
                // This is a critical failure - debit succeeded but credit failed
                // Trigger immediate reversal
                transaction.updateStatus(TransactionStatus.REVERSING, 
                    "Credit failed after debit");
                transactionRepository.save(transaction);
                return false;
            }
            
            transaction.updateStatus(TransactionStatus.CREDITED, null);
            transaction.updateStatus(TransactionStatus.SUCCESS, null);
            transactionRepository.save(transaction);
            
            log.info("2PC completed successfully: {}", txnId);
            return true;
            
        } catch (Exception e) {
            log.error("2PC failed with exception: {}", txnId, e);
            rollback(transaction, Phase.COMMIT);
            return false;
        }
    }
    
    private void rollback(Transaction transaction, Phase phase) {
        log.warn("Rolling back transaction: {} at phase: {}", 
            transaction.getTransactionId(), phase);
        
        try {
            npciAdapter.rollback(transaction, phase);
            transaction.updateStatus(TransactionStatus.FAILED, 
                "Rolled back at " + phase);
        } catch (Exception e) {
            log.error("Rollback failed - manual intervention required", e);
            // Alert operations team
        }
    }
    
    private enum Phase {
        PREPARE, COMMIT
    }
}
```

## 3. Supporting Service Classes

### 3.1 Idempotency Service

```java
@Service
public class IdempotencyService {
    
    private final RedisTemplate<String, String> redisTemplate;
    private final ObjectMapper objectMapper;
    private static final String IDEMPOTENCY_KEY_PREFIX = "idem:";
    private static final Duration TTL = Duration.ofHours(24);
    
    /**
     * Check if request with this idempotency key was already processed
     */
    public Optional<Transaction> checkIdempotency(String idempotencyKey) {
        String key = IDEMPOTENCY_KEY_PREFIX + idempotencyKey;
        String cachedData = redisTemplate.opsForValue().get(key);
        
        if (cachedData != null) {
            try {
                Transaction transaction = 
                    objectMapper.readValue(cachedData, Transaction.class);
                return Optional.of(transaction);
            } catch (JsonProcessingException e) {
                // Log and return empty - will process as new
                return Optional.empty();
            }
        }
        
        return Optional.empty();
    }
    
    /**
     * Record transaction for idempotency
     */
    public void recordTransaction(String idempotencyKey, Transaction transaction) {
        String key = IDEMPOTENCY_KEY_PREFIX + idempotencyKey;
        try {
            String data = objectMapper.writeValueAsString(transaction);
            redisTemplate.opsForValue().set(key, data, TTL);
        } catch (JsonProcessingException e) {
            // Log error but don't fail transaction
        }
    }
}
```

### 3.2 VPA Resolution Service

```java
@Service
public class VPAResolutionService {
    
    private final BankAccountRepository bankAccountRepository;
    private final UPIHandleRepository upiHandleRepository;
    private final RedisTemplate<String, BankAccount> cache;
    private static final Duration CACHE_TTL = Duration.ofMinutes(60);
    
    /**
     * Resolve VPA to bank account
     */
    @Cacheable(value = "vpa", key = "#vpa")
    public BankAccount resolveVPA(String vpa) {
        // Try cache first
        String cacheKey = "vpa:" + vpa;
        BankAccount cached = cache.opsForValue().get(cacheKey);
        if (cached != null) {
            return cached;
        }
        
        // Query database
        UPIHandle handle = upiHandleRepository.findByVpa(vpa)
            .orElseThrow(() -> new VPANotFoundException(vpa));
        
        if (!handle.isActive()) {
            throw new VPAInactiveException(vpa);
        }
        
        BankAccount account = bankAccountRepository
            .findByUpiHandle(handle)
            .orElseThrow(() -> new AccountNotFoundException(vpa));
        
        // Cache result
        cache.opsForValue().set(cacheKey, account, CACHE_TTL);
        
        return account;
    }
}
```

## 4. Class Relationship Diagram (ASCII)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CLASS RELATIONSHIP DIAGRAM                          │
└─────────────────────────────────────────────────────────────────────────────┘

                    ┌──────────────────┐
                    │   PaymentAPI     │
                    │   Controller     │
                    └────────┬─────────┘
                             │
                             │ uses
                             ▼
                    ┌──────────────────┐
                    │ PaymentService   │
                    └────────┬─────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
         ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│VPAResolution    │ │ AuthService     │ │ Fraud           │
│Service          │ │                 │ │ Detection       │
└─────────────────┘ └─────────────────┘ └─────────────────┘
         │
         │ resolves
         ▼
┌─────────────────┐         ┌─────────────────┐
│ UPIHandle       │◄────────│ User            │
└─────────────────┘   owns  └─────────────────┘
         │                           │
         │                           │
         ▼                           ▼
┌─────────────────┐         ┌─────────────────┐
│ BankAccount     │◄────────│ BankAccount     │
└─────────────────┘  linked └─────────────────┘
         │                           │
         │                           │
         └───────────┬───────────────┘
                     │
                     │ references
                     ▼
            ┌─────────────────┐
            │  Transaction    │
            └────────┬────────┘
                     │
                     │ processed by
                     ▼
            ┌─────────────────┐
            │ 2PC Coordinator │
            └────────┬────────┘
                     │
                     │ calls
                     ▼
            ┌─────────────────┐
            │ NPCI Adapter    │
            └─────────────────┘
```
