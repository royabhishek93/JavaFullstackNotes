# Notification Service - Complete LLD Interview Guide

**Interview Duration: 45 minutes | Difficulty: Medium | Must-Know: ⭐⭐⭐**

---

## CONVERSATIONAL SCRIPT (How to approach in interview)

### Phase 1: Requirements Clarification (5 mins)

**You:** "Let me understand the requirements for the Notification Service."

**Functional Requirements:**
- "Support multiple notification channels - Email, SMS, Push notifications"
- "Allow users to subscribe to different types of notifications"
- "Send notifications to multiple recipients"
- "Support notification templates"
- "Handle notification priorities - high, medium, low"
- "Should we support scheduled notifications?"

**Interviewer:** "Yes, support scheduled notifications. Also add retry logic for failures."

**You:** "Got it. For non-functional requirements:"
- "High availability - notifications should not be lost"
- "Scalability - handle millions of notifications per day"
- "Rate limiting - respect third-party API limits"
- "Async processing - don't block the caller"
- "Extensible - easy to add new channels"
- "Monitoring - track delivery status"

**Interviewer:** "Good. Focus on extensibility and async processing."

---

### Phase 2: Core Design Approach (5 mins)

**You:** "I'll use an event-driven architecture with these design patterns:"

```
┌──────────────────────────────────────────────────────────────┐
│           NOTIFICATION SERVICE ARCHITECTURE                  │
└──────────────────────────────────────────────────────────────┘

Design Patterns:
1. Observer Pattern     - Notify multiple subscribers
2. Factory Pattern      - Create different channel senders
3. Template Method      - Common notification flow
4. Strategy Pattern     - Different retry strategies
5. Chain of Responsibility - Notification pipeline

Flow:
┌─────────┐     ┌─────────────┐     ┌──────────┐     ┌─────────┐
│ Client  │────→│ Notification │────→│  Queue   │────→│Processor│
│         │     │  Service     │     │ (Kafka)  │     │         │
└─────────┘     └─────────────┘     └──────────┘     └────┬────┘
                                                            │
                        ┌───────────────────────────────────┤
                        ↓                ↓                  ↓
                  ┌──────────┐    ┌──────────┐     ┌──────────┐
                  │  Email   │    │   SMS    │     │   Push   │
                  │  Sender  │    │  Sender  │     │  Sender  │
                  └──────────┘    └──────────┘     └──────────┘
                        ↓                ↓                  ↓
                  ┌──────────┐    ┌──────────┐     ┌──────────┐
                  │SendGrid  │    │  Twilio  │     │   FCM    │
                  │   API    │    │   API    │     │   API    │
                  └──────────┘    └──────────┘     └──────────┘
```

---

### Phase 3: Class Diagram (5 mins)

**You:** "Let me design the core classes:"

```
┌─────────────────────────────────────────────────────────────┐
│                    CLASS STRUCTURE                          │
└─────────────────────────────────────────────────────────────┘

┌────────────────────────┐
│  NotificationService   │ (Facade)
│  ────────────────────  │
│  - queue: Queue        │
│  - factory: Factory    │
│  ────────────────────  │
│  + send(Notification)  │
│  + sendBulk(List)      │
│  + schedule(Notif)     │
└────────┬───────────────┘
         │
         │ uses
         ↓
┌────────────────────────┐
│   Notification         │ (Abstract)
│  ────────────────────  │
│  - id: String          │
│  - recipient: Recipient│
│  - type: NotifType     │
│  - priority: Priority  │
│  - content: String     │
│  - metadata: Map       │
│  - timestamp           │
│  ────────────────────  │
│  + validate()          │
│  + getChannel()        │
└────────┬───────────────┘
         │
         ▲
         │
    ┌────┴────┬─────────┬───────────┐
    │         │         │           │
┌───▼────┐ ┌──▼───┐ ┌──▼────┐ ┌────▼──────┐
│ Email  │ │ SMS  │ │ Push  │ │ InApp     │
│ Notif  │ │ Notif│ │ Notif │ │ Notif     │
└────────┘ └──────┘ └───────┘ └───────────┘


┌────────────────────────┐
│  NotificationSender    │ (Interface)
│  ────────────────────  │
│  + send(Notification)  │
│  + sendBatch(List)     │
└────────┬───────────────┘
         │
         ▲
         │
    ┌────┴────┬─────────┬───────────┐
    │         │         │           │
┌───▼────┐ ┌──▼───┐ ┌──▼────┐ ┌────▼──────┐
│ Email  │ │ SMS  │ │ Push  │ │ InApp     │
│ Sender │ │Sender│ │Sender │ │ Sender    │
└────────┘ └──────┘ └───────┘ └───────────┘


┌────────────────────────┐
│  SenderFactory         │ (Factory Pattern)
│  ────────────────────  │
│  + getSender(Channel)  │
└────────────────────────┘


┌────────────────────────┐
│  RetryPolicy           │ (Strategy Pattern)
│  ────────────────────  │
│  + shouldRetry(attempt)│
│  + getDelayMs(attempt) │
└────────┬───────────────┘
         │
         ▲
         │
    ┌────┴────┬──────────────┐
    │         │              │
┌───▼─────┐ ┌─▼────────┐ ┌──▼──────┐
│ Fixed   │ │Exponential│ │  No     │
│ Retry   │ │  Backoff  │ │ Retry   │
└─────────┘ └───────────┘ └─────────┘


┌────────────────────────┐
│  NotificationQueue     │
│  ────────────────────  │
│  + enqueue(Notif)      │
│  + dequeue(): Notif    │
│  + peek(): Notif       │
└────────────────────────┘


┌────────────────────────┐
│  NotificationObserver  │ (Observer Pattern)
│  ────────────────────  │
│  + onSent(Notif)       │
│  + onFailed(Notif)     │
└────────┬───────────────┘
         │
         ▲
         │
    ┌────┴────┬──────────┐
    │         │          │
┌───▼─────┐ ┌─▼──────┐ ┌─▼────────┐
│ Logger  │ │Metrics │ │Analytics │
│Observer │ │Observer│ │Observer  │
└─────────┘ └────────┘ └──────────┘


┌────────────────────────┐
│  TemplateEngine        │
│  ────────────────────  │
│  + render(template,    │
│           params)      │
└────────────────────────┘


┌────────────────────────┐
│  RateLimiter           │
│  ────────────────────  │
│  + allowRequest():bool │
└────────────────────────┘
```

---

### Phase 4: Core Implementation (20 mins)

**You:** "Let me implement the key components:"

#### 1. Enums and Data Classes

```java
public enum NotificationType {
    EMAIL,
    SMS,
    PUSH,
    IN_APP
}

public enum Priority {
    HIGH(1),
    MEDIUM(2),
    LOW(3);
    
    private final int level;
    
    Priority(int level) {
        this.level = level;
    }
    
    public int getLevel() {
        return level;
    }
}

public enum NotificationStatus {
    PENDING,
    SENT,
    FAILED,
    RETRYING
}

public class Recipient {
    private String email;
    private String phone;
    private String deviceToken;
    private String userId;
    
    // Constructor, getters, setters
    public Recipient(String userId) {
        this.userId = userId;
    }
    
    public void setEmail(String email) { this.email = email; }
    public void setPhone(String phone) { this.phone = phone; }
    public void setDeviceToken(String token) { this.deviceToken = token; }
    
    public String getEmail() { return email; }
    public String getPhone() { return phone; }
    public String getDeviceToken() { return deviceToken; }
    public String getUserId() { return userId; }
}
```

---

#### 2. Notification (Abstract Base Class)

```java
import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

public abstract class Notification {
    protected String id;
    protected Recipient recipient;
    protected NotificationType type;
    protected Priority priority;
    protected String subject;
    protected String content;
    protected Map<String, Object> metadata;
    protected LocalDateTime timestamp;
    protected NotificationStatus status;
    protected int retryCount;
    
    public Notification(Recipient recipient, String subject, String content, Priority priority) {
        this.id = UUID.randomUUID().toString();
        this.recipient = recipient;
        this.subject = subject;
        this.content = content;
        this.priority = priority;
        this.metadata = new HashMap<>();
        this.timestamp = LocalDateTime.now();
        this.status = NotificationStatus.PENDING;
        this.retryCount = 0;
    }
    
    public abstract boolean validate();
    public abstract NotificationType getType();
    
    // Getters and setters
    public String getId() { return id; }
    public Recipient getRecipient() { return recipient; }
    public String getSubject() { return subject; }
    public String getContent() { return content; }
    public Priority getPriority() { return priority; }
    public NotificationStatus getStatus() { return status; }
    public int getRetryCount() { return retryCount; }
    
    public void setStatus(NotificationStatus status) { this.status = status; }
    public void incrementRetryCount() { this.retryCount++; }
    
    public void addMetadata(String key, Object value) {
        metadata.put(key, value);
    }
    
    public Object getMetadata(String key) {
        return metadata.get(key);
    }
}
```

---

#### 3. Concrete Notification Classes

```java
public class EmailNotification extends Notification {
    private String fromEmail;
    private List<String> ccEmails;
    private List<String> attachments;
    
    public EmailNotification(Recipient recipient, String subject, 
                            String content, Priority priority) {
        super(recipient, subject, content, priority);
        this.type = NotificationType.EMAIL;
        this.ccEmails = new ArrayList<>();
        this.attachments = new ArrayList<>();
    }
    
    @Override
    public boolean validate() {
        return recipient.getEmail() != null && 
               !recipient.getEmail().isEmpty() &&
               content != null && !content.isEmpty();
    }
    
    @Override
    public NotificationType getType() {
        return NotificationType.EMAIL;
    }
    
    // Additional methods
    public void setFromEmail(String fromEmail) { this.fromEmail = fromEmail; }
    public void addCcEmail(String email) { ccEmails.add(email); }
    public void addAttachment(String attachment) { attachments.add(attachment); }
    
    public String getFromEmail() { return fromEmail; }
    public List<String> getCcEmails() { return ccEmails; }
    public List<String> getAttachments() { return attachments; }
}

public class SmsNotification extends Notification {
    private String senderName;
    
    public SmsNotification(Recipient recipient, String content, Priority priority) {
        super(recipient, "", content, priority); // SMS has no subject
        this.type = NotificationType.SMS;
    }
    
    @Override
    public boolean validate() {
        return recipient.getPhone() != null && 
               !recipient.getPhone().isEmpty() &&
               content != null && 
               content.length() <= 160; // SMS character limit
    }
    
    @Override
    public NotificationType getType() {
        return NotificationType.SMS;
    }
    
    public void setSenderName(String name) { this.senderName = name; }
    public String getSenderName() { return senderName; }
}

public class PushNotification extends Notification {
    private String imageUrl;
    private String actionUrl;
    private Map<String, String> customData;
    
    public PushNotification(Recipient recipient, String title, 
                           String message, Priority priority) {
        super(recipient, title, message, priority);
        this.type = NotificationType.PUSH;
        this.customData = new HashMap<>();
    }
    
    @Override
    public boolean validate() {
        return recipient.getDeviceToken() != null && 
               !recipient.getDeviceToken().isEmpty() &&
               content != null && !content.isEmpty();
    }
    
    @Override
    public NotificationType getType() {
        return NotificationType.PUSH;
    }
    
    public void setImageUrl(String url) { this.imageUrl = url; }
    public void setActionUrl(String url) { this.actionUrl = url; }
    public void addCustomData(String key, String value) { 
        customData.put(key, value); 
    }
    
    public String getImageUrl() { return imageUrl; }
    public String getActionUrl() { return actionUrl; }
    public Map<String, String> getCustomData() { return customData; }
}
```

---

#### 4. NotificationSender Interface & Implementations

```java
public interface NotificationSender {
    boolean send(Notification notification);
    boolean sendBatch(List<Notification> notifications);
    String getChannelName();
}

// Template Method Pattern - Common flow for all senders
public abstract class BaseNotificationSender implements NotificationSender {
    protected RateLimiter rateLimiter;
    protected RetryPolicy retryPolicy;
    
    public BaseNotificationSender() {
        this.rateLimiter = new RateLimiter(100, 60); // 100 requests per minute
        this.retryPolicy = new ExponentialBackoffRetry();
    }
    
    @Override
    public boolean send(Notification notification) {
        // Validate
        if (!notification.validate()) {
            System.out.println("Validation failed for notification: " + notification.getId());
            return false;
        }
        
        // Rate limiting
        if (!rateLimiter.allowRequest()) {
            System.out.println("Rate limit exceeded. Queueing for retry.");
            return false;
        }
        
        // Send with retry logic
        return sendWithRetry(notification);
    }
    
    private boolean sendWithRetry(Notification notification) {
        int maxRetries = 3;
        
        while (notification.getRetryCount() < maxRetries) {
            try {
                boolean success = sendInternal(notification);
                if (success) {
                    notification.setStatus(NotificationStatus.SENT);
                    return true;
                }
            } catch (Exception e) {
                System.out.println("Send failed: " + e.getMessage());
            }
            
            notification.incrementRetryCount();
            notification.setStatus(NotificationStatus.RETRYING);
            
            if (retryPolicy.shouldRetry(notification.getRetryCount())) {
                long delay = retryPolicy.getDelayMs(notification.getRetryCount());
                sleep(delay);
            }
        }
        
        notification.setStatus(NotificationStatus.FAILED);
        return false;
    }
    
    // Abstract method - implemented by concrete senders
    protected abstract boolean sendInternal(Notification notification) throws Exception;
    
    private void sleep(long millis) {
        try {
            Thread.sleep(millis);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }
}

// Concrete Implementations
public class EmailSender extends BaseNotificationSender {
    
    @Override
    protected boolean sendInternal(Notification notification) throws Exception {
        EmailNotification email = (EmailNotification) notification;
        
        System.out.println("=== Sending Email ===");
        System.out.println("To: " + email.getRecipient().getEmail());
        System.out.println("Subject: " + email.getSubject());
        System.out.println("Content: " + email.getContent());
        
        // Simulate API call to SendGrid/AWS SES
        boolean success = callEmailAPI(email);
        
        if (success) {
            System.out.println("✓ Email sent successfully!");
        }
        
        return success;
    }
    
    private boolean callEmailAPI(EmailNotification email) {
        // Simulate external API call
        // In production: Use SendGrid, AWS SES, etc.
        try {
            Thread.sleep(100); // Simulate network delay
            return Math.random() > 0.1; // 90% success rate
        } catch (InterruptedException e) {
            return false;
        }
    }
    
    @Override
    public boolean sendBatch(List<Notification> notifications) {
        // Batch sending optimization
        return notifications.stream()
            .allMatch(this::send);
    }
    
    @Override
    public String getChannelName() {
        return "EMAIL";
    }
}

public class SmsSender extends BaseNotificationSender {
    
    @Override
    protected boolean sendInternal(Notification notification) throws Exception {
        SmsNotification sms = (SmsNotification) notification;
        
        System.out.println("=== Sending SMS ===");
        System.out.println("To: " + sms.getRecipient().getPhone());
        System.out.println("Message: " + sms.getContent());
        
        // Simulate API call to Twilio
        boolean success = callSmsAPI(sms);
        
        if (success) {
            System.out.println("✓ SMS sent successfully!");
        }
        
        return success;
    }
    
    private boolean callSmsAPI(SmsNotification sms) {
        // Simulate external API call
        try {
            Thread.sleep(150); // Simulate network delay
            return Math.random() > 0.15; // 85% success rate
        } catch (InterruptedException e) {
            return false;
        }
    }
    
    @Override
    public boolean sendBatch(List<Notification> notifications) {
        return notifications.stream()
            .allMatch(this::send);
    }
    
    @Override
    public String getChannelName() {
        return "SMS";
    }
}

public class PushNotificationSender extends BaseNotificationSender {
    
    @Override
    protected boolean sendInternal(Notification notification) throws Exception {
        PushNotification push = (PushNotification) notification;
        
        System.out.println("=== Sending Push Notification ===");
        System.out.println("To Device: " + push.getRecipient().getDeviceToken());
        System.out.println("Title: " + push.getSubject());
        System.out.println("Message: " + push.getContent());
        
        // Simulate API call to FCM/APNS
        boolean success = callPushAPI(push);
        
        if (success) {
            System.out.println("✓ Push notification sent successfully!");
        }
        
        return success;
    }
    
    private boolean callPushAPI(PushNotification push) {
        // Simulate external API call
        try {
            Thread.sleep(120); // Simulate network delay
            return Math.random() > 0.05; // 95% success rate
        } catch (InterruptedException e) {
            return false;
        }
    }
    
    @Override
    public boolean sendBatch(List<Notification> notifications) {
        return notifications.stream()
            .allMatch(this::send);
    }
    
    @Override
    public String getChannelName() {
        return "PUSH";
    }
}
```

---

#### 5. Factory Pattern

```java
public class NotificationSenderFactory {
    private static final Map<NotificationType, NotificationSender> senders = new HashMap<>();
    
    static {
        senders.put(NotificationType.EMAIL, new EmailSender());
        senders.put(NotificationType.SMS, new SmsSender());
        senders.put(NotificationType.PUSH, new PushNotificationSender());
    }
    
    public static NotificationSender getSender(NotificationType type) {
        NotificationSender sender = senders.get(type);
        if (sender == null) {
            throw new IllegalArgumentException("No sender found for type: " + type);
        }
        return sender;
    }
    
    // Allow adding custom senders
    public static void registerSender(NotificationType type, NotificationSender sender) {
        senders.put(type, sender);
    }
}
```

---

#### 6. Retry Policy (Strategy Pattern)

```java
public interface RetryPolicy {
    boolean shouldRetry(int attemptNumber);
    long getDelayMs(int attemptNumber);
}

public class NoRetryPolicy implements RetryPolicy {
    @Override
    public boolean shouldRetry(int attemptNumber) {
        return false;
    }
    
    @Override
    public long getDelayMs(int attemptNumber) {
        return 0;
    }
}

public class FixedRetryPolicy implements RetryPolicy {
    private final int maxRetries;
    private final long delayMs;
    
    public FixedRetryPolicy(int maxRetries, long delayMs) {
        this.maxRetries = maxRetries;
        this.delayMs = delayMs;
    }
    
    @Override
    public boolean shouldRetry(int attemptNumber) {
        return attemptNumber < maxRetries;
    }
    
    @Override
    public long getDelayMs(int attemptNumber) {
        return delayMs;
    }
}

public class ExponentialBackoffRetry implements RetryPolicy {
    private final int maxRetries;
    private final long initialDelayMs;
    private final int multiplier;
    
    public ExponentialBackoffRetry() {
        this(3, 1000, 2); // 1s, 2s, 4s
    }
    
    public ExponentialBackoffRetry(int maxRetries, long initialDelayMs, int multiplier) {
        this.maxRetries = maxRetries;
        this.initialDelayMs = initialDelayMs;
        this.multiplier = multiplier;
    }
    
    @Override
    public boolean shouldRetry(int attemptNumber) {
        return attemptNumber < maxRetries;
    }
    
    @Override
    public long getDelayMs(int attemptNumber) {
        return initialDelayMs * (long) Math.pow(multiplier, attemptNumber - 1);
    }
}
```

---

#### 7. Rate Limiter

```java
import java.util.concurrent.atomic.AtomicInteger;
import java.time.Instant;

public class RateLimiter {
    private final int maxRequests;
    private final long windowSeconds;
    private final AtomicInteger currentRequests;
    private long windowStart;
    
    public RateLimiter(int maxRequests, long windowSeconds) {
        this.maxRequests = maxRequests;
        this.windowSeconds = windowSeconds;
        this.currentRequests = new AtomicInteger(0);
        this.windowStart = Instant.now().getEpochSecond();
    }
    
    public synchronized boolean allowRequest() {
        long now = Instant.now().getEpochSecond();
        
        // Reset window if expired
        if (now - windowStart >= windowSeconds) {
            currentRequests.set(0);
            windowStart = now;
        }
        
        // Check if under limit
        if (currentRequests.get() < maxRequests) {
            currentRequests.incrementAndGet();
            return true;
        }
        
        return false;
    }
    
    public int getCurrentRequests() {
        return currentRequests.get();
    }
}
```

---

#### 8. Observer Pattern for Monitoring

```java
public interface NotificationObserver {
    void onNotificationSent(Notification notification);
    void onNotificationFailed(Notification notification, String reason);
}

public class LoggingObserver implements NotificationObserver {
    @Override
    public void onNotificationSent(Notification notification) {
        System.out.println("[LOG] Notification sent: " + notification.getId() + 
                          " Type: " + notification.getType());
    }
    
    @Override
    public void onNotificationFailed(Notification notification, String reason) {
        System.err.println("[LOG] Notification failed: " + notification.getId() + 
                          " Reason: " + reason);
    }
}

public class MetricsObserver implements NotificationObserver {
    private int sentCount = 0;
    private int failedCount = 0;
    
    @Override
    public void onNotificationSent(Notification notification) {
        sentCount++;
    }
    
    @Override
    public void onNotificationFailed(Notification notification, String reason) {
        failedCount++;
    }
    
    public void printMetrics() {
        System.out.println("\n=== Notification Metrics ===");
        System.out.println("Sent: " + sentCount);
        System.out.println("Failed: " + failedCount);
        System.out.println("Success Rate: " + 
            (sentCount * 100.0 / (sentCount + failedCount)) + "%");
        System.out.println("============================\n");
    }
}
```

---

#### 9. Main Notification Service (Facade)

```java
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.*;

public class NotificationService {
    private final ExecutorService executorService;
    private final BlockingQueue<Notification> notificationQueue;
    private final List<NotificationObserver> observers;
    private volatile boolean running;
    
    public NotificationService(int threadPoolSize) {
        this.executorService = Executors.newFixedThreadPool(threadPoolSize);
        this.notificationQueue = new LinkedBlockingQueue<>();
        this.observers = new ArrayList<>();
        this.running = false;
    }
    
    public void registerObserver(NotificationObserver observer) {
        observers.add(observer);
    }
    
    public void start() {
        running = true;
        
        // Start worker threads to process queue
        for (int i = 0; i < 5; i++) {
            executorService.submit(this::processNotifications);
        }
        
        System.out.println("Notification Service started with 5 workers");
    }
    
    public void stop() {
        running = false;
        executorService.shutdown();
        try {
            if (!executorService.awaitTermination(60, TimeUnit.SECONDS)) {
                executorService.shutdownNow();
            }
        } catch (InterruptedException e) {
            executorService.shutdownNow();
        }
        System.out.println("Notification Service stopped");
    }
    
    // Async send - returns immediately
    public void sendAsync(Notification notification) {
        try {
            notificationQueue.put(notification);
            System.out.println("Notification queued: " + notification.getId());
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            System.err.println("Failed to queue notification");
        }
    }
    
    // Sync send - waits for completion
    public boolean sendSync(Notification notification) {
        NotificationSender sender = NotificationSenderFactory.getSender(notification.getType());
        boolean success = sender.send(notification);
        
        if (success) {
            notifyObservers(notification, true, null);
        } else {
            notifyObservers(notification, false, "Send failed after retries");
        }
        
        return success;
    }
    
    // Bulk send
    public void sendBulk(List<Notification> notifications) {
        for (Notification notification : notifications) {
            sendAsync(notification);
        }
    }
    
    // Worker thread method
    private void processNotifications() {
        while (running || !notificationQueue.isEmpty()) {
            try {
                Notification notification = notificationQueue.poll(1, TimeUnit.SECONDS);
                
                if (notification != null) {
                    NotificationSender sender = NotificationSenderFactory.getSender(
                        notification.getType()
                    );
                    
                    boolean success = sender.send(notification);
                    
                    if (success) {
                        notifyObservers(notification, true, null);
                    } else {
                        notifyObservers(notification, false, "Send failed");
                    }
                }
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                break;
            }
        }
    }
    
    private void notifyObservers(Notification notification, boolean success, String reason) {
        for (NotificationObserver observer : observers) {
            if (success) {
                observer.onNotificationSent(notification);
            } else {
                observer.onNotificationFailed(notification, reason);
            }
        }
    }
    
    public int getQueueSize() {
        return notificationQueue.size();
    }
}
```

---

### Phase 5: Usage Example (5 mins)

**You:** "Here's a complete demo:"

```java
public class NotificationServiceDemo {
    public static void main(String[] args) throws InterruptedException {
        // Initialize service
        NotificationService service = new NotificationService(5);
        
        // Register observers
        service.registerObserver(new LoggingObserver());
        MetricsObserver metricsObserver = new MetricsObserver();
        service.registerObserver(metricsObserver);
        
        // Start service
        service.start();
        
        System.out.println("\n=== Notification Service Demo ===\n");
        
        // Test 1: Email notification
        Recipient user1 = new Recipient("user1");
        user1.setEmail("user1@example.com");
        
        EmailNotification email = new EmailNotification(
            user1,
            "Welcome to Our Platform",
            "Thank you for signing up!",
            Priority.HIGH
        );
        email.setFromEmail("noreply@platform.com");
        
        service.sendAsync(email);
        
        // Test 2: SMS notification
        Recipient user2 = new Recipient("user2");
        user2.setPhone("+1234567890");
        
        SmsNotification sms = new SmsNotification(
            user2,
            "Your OTP is: 123456",
            Priority.HIGH
        );
        
        service.sendAsync(sms);
        
        // Test 3: Push notification
        Recipient user3 = new Recipient("user3");
        user3.setDeviceToken("device_token_xyz");
        
        PushNotification push = new PushNotification(
            user3,
            "New Message",
            "You have a new message from John",
            Priority.MEDIUM
        );
        push.setImageUrl("https://example.com/image.png");
        
        service.sendAsync(push);
        
        // Test 4: Bulk notifications
        System.out.println("\n--- Sending bulk notifications ---\n");
        List<Notification> bulkNotifications = new ArrayList<>();
        
        for (int i = 0; i < 10; i++) {
            Recipient user = new Recipient("user" + i);
            user.setEmail("user" + i + "@example.com");
            
            EmailNotification bulkEmail = new EmailNotification(
                user,
                "Daily Update",
                "Your daily digest is ready!",
                Priority.LOW
            );
            
            bulkNotifications.add(bulkEmail);
        }
        
        service.sendBulk(bulkNotifications);
        
        // Wait for processing
        Thread.sleep(5000);
        
        // Print metrics
        metricsObserver.printMetrics();
        
        // Stop service
        service.stop();
    }
}
```

---

### Phase 6: Advanced Features (5 mins)

**You:** "Let me show some advanced features:"

#### 1. Template Engine

```java
public class TemplateEngine {
    private final Map<String, String> templates = new HashMap<>();
    
    public TemplateEngine() {
        // Load templates
        templates.put("welcome_email", 
            "Hello {{name}},\n\nWelcome to {{platform}}!\n\nBest regards,\nTeam");
        templates.put("otp_sms", 
            "Your OTP is: {{otp}}. Valid for {{validity}} minutes.");
    }
    
    public String render(String templateId, Map<String, String> params) {
        String template = templates.get(templateId);
        if (template == null) {
            throw new IllegalArgumentException("Template not found: " + templateId);
        }
        
        String result = template;
        for (Map.Entry<String, String> entry : params.entrySet()) {
            result = result.replace("{{" + entry.getKey() + "}}", entry.getValue());
        }
        
        return result;
    }
}

// Usage:
TemplateEngine engine = new TemplateEngine();
Map<String, String> params = Map.of(
    "name", "John",
    "platform", "MyApp"
);
String content = engine.render("welcome_email", params);
```

#### 2. Scheduled Notifications

```java
public class ScheduledNotificationService {
    private final ScheduledExecutorService scheduler;
    private final NotificationService notificationService;
    
    public ScheduledNotificationService(NotificationService service) {
        this.scheduler = Executors.newScheduledThreadPool(2);
        this.notificationService = service;
    }
    
    public void schedule(Notification notification, long delaySeconds) {
        scheduler.schedule(
            () -> notificationService.sendAsync(notification),
            delaySeconds,
            TimeUnit.SECONDS
        );
        
        System.out.println("Notification scheduled for " + delaySeconds + "s later");
    }
    
    public void scheduleRecurring(Notification notification, 
                                  long initialDelay, 
                                  long period, 
                                  TimeUnit unit) {
        scheduler.scheduleAtFixedRate(
            () -> notificationService.sendAsync(notification),
            initialDelay,
            period,
            unit
        );
        
        System.out.println("Recurring notification scheduled");
    }
    
    public void shutdown() {
        scheduler.shutdown();
    }
}
```

#### 3. Preference Management

```java
public class NotificationPreferences {
    private final Map<String, Set<NotificationType>> userPreferences;
    
    public NotificationPreferences() {
        this.userPreferences = new ConcurrentHashMap<>();
    }
    
    public void subscribe(String userId, NotificationType type) {
        userPreferences.computeIfAbsent(userId, k -> new HashSet<>()).add(type);
    }
    
    public void unsubscribe(String userId, NotificationType type) {
        Set<NotificationType> prefs = userPreferences.get(userId);
        if (prefs != null) {
            prefs.remove(type);
        }
    }
    
    public boolean isSubscribed(String userId, NotificationType type) {
        Set<NotificationType> prefs = userPreferences.get(userId);
        return prefs != null && prefs.contains(type);
    }
    
    public boolean canSend(Notification notification) {
        String userId = notification.getRecipient().getUserId();
        return isSubscribed(userId, notification.getType());
    }
}
```

---

## SOLID PRINCIPLES IN DEPTH

**You:** "Let me walk through how SOLID principles make this notification system maintainable and extensible."

---

### 1. Single Responsibility Principle (SRP)

**Purpose:** Each class should have only ONE reason to change.

**Problem it solves:**
Without SRP, notification logic becomes tangled:
```java
// BAD: NotificationService doing everything
class NotificationService {
    // Sending logic
    public void sendEmail(String to, String subject, String body) { ... }
    public void sendSMS(String phone, String message) { ... }
    
    // Queue management
    public void enqueue(Notification n) { ... }
    
    // Retry logic
    public void retry(Notification n) { ... }
    
    // Rate limiting
    public boolean checkRateLimit() { ... }
    
    // Template rendering
    public String renderTemplate(String template, Map<String, String> vars) { ... }
    
    // Logging and metrics
    public void logSuccess() { ... }
}
// Too many responsibilities! Any change risks breaking everything.
```

**Advantages:**
- ✅ **Clear ownership** - Each team member owns specific classes
- ✅ **Easy to test** - Mock one responsibility at a time
- ✅ **Parallel development** - Different devs work on different classes
- ✅ **Localized changes** - Fix retry logic without touching email sending

**In our design:**
```java
// GOOD: Separated responsibilities

// EmailSender: ONLY sends emails
class EmailNotificationSender implements NotificationSender {
    public void send(Notification notification) {
        // Only email-specific logic
    }
}

// SmsSender: ONLY sends SMS
class SmsNotificationSender implements NotificationSender {
    public void send(Notification notification) {
        // Only SMS-specific logic
    }
}

// RetryPolicy: ONLY determines retry behavior
interface RetryPolicy {
    boolean shouldRetry(int attemptCount);
    long getDelayMs(int attemptCount);
}

// RateLimiter: ONLY enforces rate limits
class RateLimiter {
    public boolean allowRequest(String userId) { ... }
}

// TemplateEngine: ONLY renders templates
class TemplateEngine {
    public String render(String template, Map<String, String> vars) { ... }
}

// NotificationObserver: ONLY handles observability
interface NotificationObserver {
    void onSuccess(Notification notification);
    void onFailure(Notification notification, Exception e);
}
```

**Interview tip:** "If I need to change retry logic, I only touch `RetryPolicy`. If I need to add WhatsApp channel, I create `WhatsAppSender` without touching email/SMS. Each class has one clear job."

---

### 2. Open/Closed Principle (OCP)

**Purpose:** Classes should be OPEN for extension but CLOSED for modification.

**Problem it solves:**
Without OCP, adding channels requires modifying core logic:
```java
// BAD: Hard-coded channel logic
class NotificationService {
    public void send(Notification n) {
        if (n.type == EMAIL) {
            sendEmail(n);
        } else if (n.type == SMS) {
            sendSMS(n);
        } else if (n.type == PUSH) {
            sendPush(n);
        }
        // To add WhatsApp, you MODIFY this method - RISKY!
    }
}
```

**Advantages:**
- ✅ **Zero regression** - Existing channels unaffected
- ✅ **Easy to add channels** - Just create new sender class
- ✅ **A/B testing** - Deploy new channels without changing core
- ✅ **Stable core** - NotificationService never changes

**In our design:**
```java
// GOOD: Interface-based extensibility

interface NotificationSender {
    void send(Notification notification);
    NotificationType getSupportedType();
}

class EmailNotificationSender implements NotificationSender {
    @Override
    public NotificationType getSupportedType() { return NotificationType.EMAIL; }
    
    @Override
    public void send(Notification notification) { /* Email logic */ }
}

class SmsNotificationSender implements NotificationSender {
    @Override
    public NotificationType getSupportedType() { return NotificationType.SMS; }
    
    @Override
    public void send(Notification notification) { /* SMS logic */ }
}

// NEW: Add WhatsApp - zero changes to existing code!
class WhatsAppNotificationSender implements NotificationSender {
    @Override
    public NotificationType getSupportedType() { return NotificationType.WHATSAPP; }
    
    @Override
    public void send(Notification notification) { /* WhatsApp logic */ }
}

class NotificationService {
    private Map<NotificationType, NotificationSender> senders = new HashMap<>();
    
    public void registerSender(NotificationSender sender) {
        senders.put(sender.getSupportedType(), sender);
    }
    
    public void send(Notification notification) {
        NotificationSender sender = senders.get(notification.getType());
        sender.send(notification);  // Works for ANY sender!
    }
}

// Usage:
service.registerSender(new EmailNotificationSender());
service.registerSender(new SmsNotificationSender());
service.registerSender(new WhatsAppNotificationSender());  // NEW - no modification!
```

**Interview tip:** "To add Slack notifications, I create `SlackNotificationSender` implementing the interface and register it. Zero changes to `NotificationService`. The system is closed for modification but open for extension."

---

### 3. Liskov Substitution Principle (LSP)

**Purpose:** Subclasses must be substitutable for their parent classes without breaking behavior.

**Problem it solves:**
Without LSP, some senders violate contracts:
```java
// BAD: Violates LSP
interface NotificationSender {
    void send(Notification n);  // Contract: Always attempts to send
}

class EmailSender implements NotificationSender {
    @Override
    public void send(Notification n) {
        // Sends email as expected
    }
}

class MockSender implements NotificationSender {
    @Override
    public void send(Notification n) {
        throw new UnsupportedOperationException("Mock only!");  // BREAKS CONTRACT!
    }
}

// Code expecting send() behavior will crash:
NotificationSender sender = new MockSender();
sender.send(notification);  // BOOM! Exception instead of sending
```

**Advantages:**
- ✅ **Predictable behavior** - All senders work the same way
- ✅ **Polymorphism works** - Can swap senders at runtime
- ✅ **Testing is easy** - Mock senders behave like real ones
- ✅ **No surprises** - Code doesn't break when switching implementations

**In our design:**
```java
// GOOD: All senders honor the contract

interface NotificationSender {
    void send(Notification notification) throws NotificationException;
    NotificationType getSupportedType();
}

class EmailNotificationSender implements NotificationSender {
    @Override
    public void send(Notification notification) throws NotificationException {
        try {
            // Send email
        } catch (Exception e) {
            throw new NotificationException("Email failed", e);  // ✓ Honors contract
        }
    }
    
    @Override
    public NotificationType getSupportedType() { return NotificationType.EMAIL; }  // ✓ Works
}

class SmsNotificationSender implements NotificationSender {
    @Override
    public void send(Notification notification) throws NotificationException {
        try {
            // Send SMS
        } catch (Exception e) {
            throw new NotificationException("SMS failed", e);  // ✓ Honors contract
        }
    }
    
    @Override
    public NotificationType getSupportedType() { return NotificationType.SMS; }  // ✓ Works
}

class MockNotificationSender implements NotificationSender {
    private List<Notification> sent = new ArrayList<>();
    
    @Override
    public void send(Notification notification) {
        sent.add(notification);  // ✓ Doesn't throw, behaves like real sender
    }
    
    @Override
    public NotificationType getSupportedType() { return NotificationType.EMAIL; }  // ✓ Works
}

// Polymorphism works perfectly:
NotificationSender sender = new EmailNotificationSender();  // Or Sms or Mock
sender.send(notification);  // Works for ANY sender, no surprises
```

**Interview tip:** "Any code that works with `NotificationSender` will work with `EmailSender`, `SmsSender`, or `MockSender`. They all honor the contract - `send()` either succeeds or throws `NotificationException`, never crashes unexpectedly."

---

### 4. Interface Segregation Principle (ISP)

**Purpose:** Clients should not be forced to depend on interfaces they don't use.

**Problem it solves:**
Without ISP, interfaces become bloated:
```java
// BAD: Fat interface forces unnecessary implementations
interface NotificationSender {
    void send(Notification n);
    void sendBulk(List<Notification> list);     // Not all need bulk
    void schedule(Notification n, long delay);   // Not all support scheduling
    void cancel(String notificationId);          // Not all support cancellation
    void retry(Notification n);                  // Not all support retry
    void validate(Notification n);               // Not all need validation
}

// Simple SMS sender must implement ALL methods!
class SmsSender implements NotificationSender {
    @Override
    public void sendBulk(List<Notification> list) { 
        throw new UnsupportedOperationException();  // Forced!
    }
    
    @Override
    public void schedule(Notification n, long delay) {
        throw new UnsupportedOperationException();  // Forced!
    }
}
```

**Advantages:**
- ✅ **Lean interfaces** - Only necessary methods
- ✅ **Better cohesion** - Related methods grouped
- ✅ **No dummy code** - No forced implementations
- ✅ **Clear contracts** - Interface tells you what to expect

**In our design:**
```java
// GOOD: Segregated interfaces

// Core: Every sender must implement this
interface NotificationSender {
    void send(Notification notification) throws NotificationException;
    NotificationType getSupportedType();
}

// Optional: Only for senders that support bulk
interface BulkNotificationSender extends NotificationSender {
    void sendBulk(List<Notification> notifications);
}

// Optional: Only for senders that support scheduling
interface SchedulableNotificationSender extends NotificationSender {
    void schedule(Notification notification, long delayMs);
    void cancel(String notificationId);
}

// Optional: Only for senders that support rich content
interface RichContentSender extends NotificationSender {
    void sendWithAttachment(Notification notification, byte[] attachment);
}

// Implement only what you need:

// Simple SMS: Just basic send
class SmsSender implements NotificationSender {
    // Only implements send() - nothing else!
}

// Email: Supports attachments
class EmailSender implements NotificationSender, RichContentSender {
    @Override
    public void sendWithAttachment(Notification n, byte[] attachment) {
        // Email can handle attachments
    }
}

// Push: Supports scheduling
class PushSender implements NotificationSender, SchedulableNotificationSender {
    @Override
    public void schedule(Notification n, long delayMs) {
        // Push can be scheduled
    }
}

// WhatsApp: Supports bulk + scheduling
class WhatsAppSender implements NotificationSender, 
                                 BulkNotificationSender,
                                 SchedulableNotificationSender {
    // Implements all three interfaces - by choice!
}
```

**Interview tip:** "Core interface has only `send()` and `getSupportedType()`. If a sender supports bulk, it implements `BulkNotificationSender`. If it supports scheduling, it implements `SchedulableNotificationSender`. Clients depend only on what they need."

---

### 5. Dependency Inversion Principle (DIP)

**Purpose:** High-level modules should not depend on low-level modules. Both should depend on abstractions.

**Problem it solves:**
Without DIP, high-level code is tightly coupled:
```java
// BAD: NotificationService tightly coupled to concrete senders
class NotificationService {
    private EmailNotificationSender emailSender = new EmailNotificationSender();  // TIGHT!
    private SmsNotificationSender smsSender = new SmsNotificationSender();        // TIGHT!
    
    public void send(Notification notification) {
        if (notification.getType() == EMAIL) {
            emailSender.send(notification);  // Can't swap implementations
        } else if (notification.getType() == SMS) {
            smsSender.send(notification);    // Can't test with mocks
        }
    }
}
```

**Advantages:**
- ✅ **Loose coupling** - Easy to swap senders
- ✅ **Testability** - Inject mock senders for testing
- ✅ **Flexibility** - Change senders at runtime
- ✅ **Maintainability** - Low-level changes don't affect high-level

**In our design:**
```java
// GOOD: Depend on abstractions (interfaces)

interface NotificationSender {
    void send(Notification notification) throws NotificationException;
    NotificationType getSupportedType();
}

class NotificationService {
    // Depend on interface, not concrete class!
    private Map<NotificationType, NotificationSender> senders = new HashMap<>();
    
    // Dependency Injection via method
    public void registerSender(NotificationSender sender) {
        senders.put(sender.getSupportedType(), sender);
    }
    
    public void send(Notification notification) {
        NotificationSender sender = senders.get(notification.getType());
        if (sender == null) {
            throw new IllegalStateException("No sender for " + notification.getType());
        }
        sender.send(notification);  // Don't care about concrete implementation!
    }
}

// Concrete implementations:
class EmailNotificationSender implements NotificationSender { ... }
class SmsNotificationSender implements NotificationSender { ... }
class MockNotificationSender implements NotificationSender { ... }

// Production usage - inject real senders:
NotificationService service = new NotificationService();
service.registerSender(new EmailNotificationSender());
service.registerSender(new SmsNotificationSender());

// Test usage - inject mock senders:
NotificationService testService = new NotificationService();
testService.registerSender(new MockNotificationSender());

// Runtime flexibility - swap sender without changing code:
service.registerSender(new ImprovedEmailSender());  // Replaces old email sender
```

**Interview tip:** "NotificationService doesn't know if it's using AWS SES, SendGrid, or Twilio - it just calls `send()` on the interface. I can inject any sender at runtime. For testing, I inject mock senders that record calls instead of hitting real APIs."

---

## KEY TAKEAWAYS

### Design Patterns Used:
✅ **Observer Pattern** - Notify multiple observers (logging, metrics)
✅ **Factory Pattern** - Create different notification senders
✅ **Template Method** - Common send flow in BaseNotificationSender
✅ **Strategy Pattern** - Different retry policies
✅ **Facade Pattern** - NotificationService simplifies complex subsystem

### SOLID Principles Applied:
✅ **Single Responsibility (SRP)** - EmailSender sends emails, RetryPolicy handles retries, RateLimiter enforces limits
✅ **Open/Closed (OCP)** - Add new channels by creating new sender classes, zero changes to core
✅ **Liskov Substitution (LSP)** - All NotificationSender implementations are interchangeable
✅ **Interface Segregation (ISP)** - Separate interfaces for core sending, bulk, scheduling, rich content
✅ **Dependency Inversion (DIP)** - NotificationService depends on NotificationSender interface, not concrete implementations

### Key Features:
✅ **Async Processing** - Non-blocking with queue
✅ **Retry Logic** - Exponential backoff
✅ **Rate Limiting** - Respect third-party limits
✅ **Observer Pattern** - Monitoring and logging
✅ **Thread Safety** - Concurrent queue, thread pool
✅ **Extensibility** - Easy to add new channels

---

## COMMON MISTAKES TO AVOID

❌ Blocking the caller (always use async for notifications)
❌ No retry logic (networks fail)
❌ Not handling rate limits (external APIs have limits)
❌ Missing observability (no logging/metrics)
❌ Hard-coded notification content (use templates)
❌ Not validating before sending
❌ Forgetting thread safety

---

## REAL-WORLD APPLICATIONS

✅ **User Onboarding** - Welcome emails, SMS verification
✅ **Transactional Alerts** - Order confirmations, payment receipts
✅ **Marketing Campaigns** - Bulk emails, push notifications
✅ **System Alerts** - Server down, high CPU usage
✅ **Social Media** - Likes, comments, mentions
✅ **E-commerce** - Order tracking, delivery updates

---

**END OF NOTIFICATION SERVICE GUIDE**

This pattern covers **Logging Framework** and most event-driven systems!
