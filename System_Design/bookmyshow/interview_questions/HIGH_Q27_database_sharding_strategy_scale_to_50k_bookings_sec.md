# Q27: Database Sharding Strategy - Scale to 50k bookings/sec

### Difficulty: ⭐⭐⭐⭐ (Staff)

### ✅ Solution: Shard by City ID

**Why City ID?**

```
SHARDING KEY EVALUATION
═══════════════════════════════════════════════════════════
Option 1: user_id
❌ Cross-city queries expensive (show search)
❌ Load imbalance (some users book more)

Option 2: show_id
❌ Hot shards (popular movies)
❌ Can't query by user efficiently

Option 3: city_id ✅
✓ Natural data isolation
✓ Queries scoped to city (show search)
✓ Even load distribution (50 cities)
✓ No cross-shard queries for 95% of operations
```

**Sharding Implementation:**

```java
@Configuration
public class ShardingConfig {
    
    private static final int TOTAL_SHARDS = 50;
    
    @Bean
    public ShardingStrategy shardingStrategy() {
        return new CityBasedSharding(TOTAL_SHARDS);
    }
}

public class CityBasedSharding implements ShardingStrategy {
    
    private final int totalShards;
    private final List<DataSource> dataSources;
    
    public CityBasedSharding(int totalShards) {
        this.totalShards = totalShards;
        this.dataSources = initializeDataSources(totalShards);
    }
    
    @Override
    public DataSource getShard(Long cityId) {
        int shardIndex = (int) (cityId % totalShards);
        return dataSources.get(shardIndex);
    }
    
    @Override
    public List<DataSource> getAllShards() {
        return dataSources;
    }
    
    private List<DataSource> initializeDataSources(int count) {
        List<DataSource> sources = new ArrayList<>();
        
        for (int i = 0; i < count; i++) {
            HikariConfig config = new HikariConfig();
            config.setJdbcUrl(
                String.format("jdbc:postgresql://db-shard-%d:5432/bookmyshow", i)
            );
            config.setUsername("app_user");
            config.setPassword(System.getenv("DB_PASSWORD"));
            config.setMaximumPoolSize(50);
            config.setMinimumIdle(10);
            
            sources.add(new HikariDataSource(config));
        }
        
        return sources;
    }
}
```

**Query Routing:**

```java
@Service
public class ShardedBookingService {
    
    private final ShardingStrategy sharding;
    
    public Booking createBooking(BookingRequest request) {
        // Step 1: Determine city from show
        Show show = showRepository.findById(request.getShowId());
        Long cityId = show.getTheater().getCityId();
        
        // Step 2: Route to correct shard
        DataSource shard = sharding.getShard(cityId);
        
        // Step 3: Execute on shard
        return executeOnShard(shard, () -> {
            return doCreateBooking(request);
        });
    }
    
    public List<Booking> getUserBookings(Long userId) {
        // User bookings across all cities → scatter-gather
        List<CompletableFuture<List<Booking>>> futures = 
            new ArrayList<>();
        
        for (DataSource shard : sharding.getAllShards()) {
            futures.add(CompletableFuture.supplyAsync(() ->
                executeOnShard(shard, () -> 
                    findBookingsByUserId(userId)
                )
            ));
        }
        
        // Gather results from all shards
        return futures.stream()
            .map(CompletableFuture::join)
            .flatMap(List::stream)
            .sorted(Comparator.comparing(Booking::getCreatedAt).reversed())
            .collect(Collectors.toList());
    }
}
```

**Shard Mapping Table (Global):**

```sql
-- Stored in a small global database (not sharded)
CREATE TABLE shard_mapping (
    city_id BIGINT PRIMARY KEY,
    shard_index INT NOT NULL,
    shard_host VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO shard_mapping VALUES
    (1, 0, 'db-shard-0.us-east-1.rds.amazonaws.com', TRUE),
    (2, 1, 'db-shard-1.us-east-1.rds.amazonaws.com', TRUE),
    (3, 2, 'db-shard-2.us-east-1.rds.amazonaws.com', TRUE),
    ...
```

**Performance:**

```
SINGLE DATABASE
═══════════════════════════════════════════════════════════
Capacity: 1k writes/sec
Peak load: 50k writes/sec
Result: 50x overload ❌

50 SHARDS (by city_id)
═══════════════════════════════════════════════════════════
Capacity per shard: 1k writes/sec
Total capacity: 50k writes/sec ✅
Average load per shard: 1k writes/sec
Result: Perfect distribution ✅
```

---
