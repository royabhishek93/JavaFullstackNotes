# Q28: Read Replicas - Scale show search to 1M queries/sec

### Difficulty: ⭐⭐⭐ (Senior)

### ✅ Solution: Read Replicas + Load Balancing

```java
@Configuration
public class DatabaseConfig {
    
    @Bean
    @Primary
    public DataSource writeDataSource() {
        // Master database (writes)
        HikariConfig config = new HikariConfig();
        config.setJdbcUrl("jdbc:postgresql://db-master:5432/bookmyshow");
        config.setMaximumPoolSize(100);
        return new HikariDataSource(config);
    }
    
    @Bean
    public DataSource readDataSource1() {
        // Read replica 1
        return createReadReplica("db-read-1");
    }
    
    @Bean
    public DataSource readDataSource2() {
        // Read replica 2
        return createReadReplica("db-read-2");
    }
    
    @Bean
    public DataSource readDataSource3() {
        // Read replica 3
        return createReadReplica("db-read-3");
    }
    
    @Bean
    public DataSource routingDataSource() {
        ReplicationRoutingDataSource routing = 
            new ReplicationRoutingDataSource();
        
        routing.setDefaultTargetDataSource(writeDataSource());
        
        Map<Object, Object> dataSources = new HashMap<>();
        dataSources.put("write", writeDataSource());
        dataSources.put("read1", readDataSource1());
        dataSources.put("read2", readDataSource2());
        dataSources.put("read3", readDataSource3());
        
        routing.setTargetDataSources(dataSources);
        
        return routing;
    }
}

public class ReplicationRoutingDataSource 
        extends AbstractRoutingDataSource {
    
    private final AtomicInteger counter = new AtomicInteger(0);
    
    @Override
    protected Object determineCurrentLookupKey() {
        // Check transaction type
        boolean isReadOnly = TransactionSynchronizationManager
            .isCurrentTransactionReadOnly();
        
        if (isReadOnly) {
            // Round-robin across read replicas
            int index = counter.getAndIncrement() % 3;
            return "read" + (index + 1);
        } else {
            // Route to master for writes
            return "write";
        }
    }
}
```

**Usage:**

```java
@Service
public class ShowSearchService {
    
    // Read from replica (load balanced)
    @Transactional(readOnly = true)
    public List<Show> searchShows(SearchCriteria criteria) {
        return showRepository.findByCriteria(criteria);
        // ↑ Routed to read replica (round-robin)
    }
    
    // Write to master
    @Transactional
    public Show createShow(ShowRequest request) {
        Show show = new Show();
        // ... populate
        return showRepository.save(show);
        // ↑ Routed to master
    }
}
```

**Replication Lag Handling:**

```java
@Service
public class ReplicationAwareService {
    
    @Transactional
    public Booking createBookingWithReadAfterWrite(
            BookingRequest request) {
        
        // Write to master
        Booking booking = bookingRepository.save(
            createBooking(request)
        );
        
        // Force next read from master (avoid replication lag)
        TransactionSynchronizationManager.setCurrentTransactionReadOnly(false);
        
        // This will read from master, not replica
        Booking confirmed = bookingRepository.findById(booking.getId())
            .orElseThrow();
        
        return confirmed;
    }
}
```

**Architecture:**

```
MASTER (WRITE)
═══════════════════════════════════════════════════════════
db-master: 1k writes/sec
    │
    ├── Replication (async) → db-read-1
    ├── Replication (async) → db-read-2
    └── Replication (async) → db-read-3
    
READ REPLICAS (READ)
═══════════════════════════════════════════════════════════
db-read-1: 10k reads/sec
db-read-2: 10k reads/sec
db-read-3: 10k reads/sec
────────────────────────────
Total: 30k reads/sec

With caching (80% hit rate):
Effective: 150k reads/sec ✅
```

---
