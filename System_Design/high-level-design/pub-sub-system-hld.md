# High-Level Design: Pub-Sub System (Message Broker like Kafka)

## System Overview
Design a distributed publish-subscribe messaging system like Apache Kafka, RabbitMQ, or Google Pub/Sub that enables asynchronous communication between services with high throughput, durability, and fault tolerance. System should support millions of messages per second with guaranteed message delivery.

---

## Requirements

### Functional Requirements
1. **Publish**: Producers publish messages to topics
2. **Subscribe**: Consumers subscribe to topics and receive messages
3. **Topics**: Logical channels for message categorization
4. **Partitions**: Parallel processing within topics
5. **Consumer Groups**: Multiple consumers share message load
6. **Message Ordering**: Guarantee order within partition
7. **Message Retention**: Store messages for configurable duration
8. **Dead Letter Queue**: Handle failed message processing
9. **Message Filtering**: Consumers filter messages by attributes
10. **Replay**: Consumers can replay messages from any offset

### Non-Functional Requirements
1. **High Throughput**: 10M+ messages/sec
2. **Low Latency**: < 10ms end-to-end (producer → consumer)
3. **Durability**: Messages persisted to disk (no data loss)
4. **Availability**: 99.99% uptime
5. **Scalability**: Horizontal scaling of brokers and partitions
6. **Fault Tolerance**: Automatic failover, replication
7. **Exactly-Once Delivery**: No duplicate message processing
8. **At-Least-Once Delivery**: Guarantee message delivery

---

## Capacity Estimation

### Traffic
- **Messages/second**: 10M messages/sec (peak: 50M)
- **Average message size**: 1KB
- **Topics**: 10,000 topics
- **Partitions per topic**: 10 partitions (avg)
- **Total partitions**: 100,000 partitions
- **Consumers**: 100,000 consumer instances
- **Consumer groups**: 10,000 groups

### Storage
- **Messages/day**: 10M × 86400 = 864B messages/day
- **Daily data**: 864B × 1KB = 864TB/day
- **Retention period**: 7 days (default)
- **Total storage**: 864TB × 7 = 6PB (raw)
- **With compression (5:1)**: 1.2PB
- **With replication (3x)**: 3.6PB

### Bandwidth
- **Writes**: 10M msg/sec × 1KB = 10GB/s = 80 Gbps
- **Reads**: 10M msg/sec × 1KB × 10 consumers (avg) = 100GB/s = 800 Gbps
- **Replication**: 10GB/s × 2 replicas = 20GB/s = 160 Gbps

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Producers (Applications)                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │  Web API │  │ Analytics│  │   IoT    │  │  Mobile  │        │
│  │  Service │  │  Service │  │ Devices  │  │  App     │        │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Producer Client Library                       │
│         (Batching, Compression, Partitioning Logic)              │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Load Balancer / Router                        │
│               (Partition Leader Discovery)                       │
└─────────────────────────┬───────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┬──────────────────┐
        │                 │                 │                  │
        ▼                 ▼                 ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   Broker 1   │  │   Broker 2   │  │   Broker 3   │  │   Broker N   │
│              │  │              │  │              │  │              │
│  Partition   │  │  Partition   │  │  Partition   │  │  Partition   │
│  Leaders     │  │  Leaders     │  │  Leaders     │  │  Leaders     │
│  + Replicas  │  │  + Replicas  │  │  + Replicas  │  │  + Replicas  │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                 │                  │
       └─────────────────┴─────────────────┴──────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Coordination Service                           │
│                  (ZooKeeper / etcd / Raft)                       │
│    - Broker registration                                         │
│    - Leader election                                             │
│    - Consumer group coordination                                 │
│    - Partition assignment                                        │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Consumer Groups                               │
│  ┌──────────────────────────────────────────────────────┐       │
│  │  Consumer Group 1 (Payment Service)                  │       │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐           │       │
│  │  │Consumer 1│  │Consumer 2│  │Consumer 3│           │       │
│  │  │Part 0,1  │  │Part 2,3  │  │Part 4,5  │           │       │
│  │  └──────────┘  └──────────┘  └──────────┘           │       │
│  └──────────────────────────────────────────────────────┘       │
│  ┌──────────────────────────────────────────────────────┐       │
│  │  Consumer Group 2 (Analytics Service)                │       │
│  │  ┌──────────┐  ┌──────────┐                         │       │
│  │  │Consumer 1│  │Consumer 2│                         │       │
│  │  └──────────┘  └──────────┘                         │       │
│  └──────────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────────┘

──────────────────── Storage Layer ────────────────────────────────

┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   Disk 1     │  │   Disk 2     │  │   Disk 3     │
│  (SSD/NVMe)  │  │  (SSD/NVMe)  │  │  (SSD/NVMe)  │
│              │  │              │  │              │
│  Segment     │  │  Segment     │  │  Segment     │
│  Files       │  │  Files       │  │  Files       │
└──────────────┘  └──────────────┘  └──────────────┘
```

---

## Core Components

### 1. Topic & Partition Model

**Topic**: Logical stream of messages (e.g., "order-events", "user-clicks")

**Partition**: Physical subdivision of a topic for parallelism

```
Topic: order-events (3 partitions)

Partition 0: [msg1, msg2, msg5, msg8, ...]
Partition 1: [msg3, msg6, msg9, ...]
Partition 2: [msg4, msg7, msg10, ...]

Key-based routing: hash(message.key) % num_partitions
```

**Why Partitions?**
1. **Parallelism**: Multiple consumers can read different partitions simultaneously
2. **Scalability**: Add more partitions as data grows
3. **Ordering**: Messages within a partition are ordered
4. **Performance**: Each partition is independent

**Schema**:
```sql
CREATE TABLE topics (
    topic_id BIGSERIAL PRIMARY KEY,
    topic_name VARCHAR(255) UNIQUE NOT NULL,
    num_partitions INT NOT NULL DEFAULT 1,
    replication_factor INT NOT NULL DEFAULT 3,
    retention_ms BIGINT DEFAULT 604800000, -- 7 days
    compression_type VARCHAR(20) DEFAULT 'gzip', -- none, gzip, snappy, lz4
    max_message_bytes INT DEFAULT 1048576, -- 1MB
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE partitions (
    partition_id BIGSERIAL PRIMARY KEY,
    topic_id BIGINT REFERENCES topics(topic_id),
    partition_num INT NOT NULL,
    leader_broker_id INT NOT NULL,
    replica_broker_ids INT[] NOT NULL,
    isr_broker_ids INT[], -- In-Sync Replicas
    first_offset BIGINT DEFAULT 0,
    last_offset BIGINT DEFAULT 0,
    UNIQUE (topic_id, partition_num)
);
```

---

### 2. Broker (Message Server)

**Responsibilities**:
- Accept messages from producers
- Store messages to disk (append-only log)
- Serve messages to consumers
- Replicate messages to other brokers
- Handle leader election for partitions

**Data Structure** (Append-Only Log):
```
Partition Log (on disk):

Segment 0: offset 0 - 999999
  00000000000000000000.log  (1GB)
  00000000000000000000.index
  00000000000000000000.timeindex

Segment 1: offset 1000000 - 1999999
  00000000001000000000.log
  00000000001000000000.index
  00000000001000000000.timeindex

Active Segment: offset 2000000 - current
  00000000002000000000.log (currently being written)
  00000000002000000000.index
  00000000002000000000.timeindex
```

**Message Format** (on disk):
```
┌──────────────────────────────────────────────────────┐
│ Offset (8 bytes)                                     │
├──────────────────────────────────────────────────────┤
│ Message Size (4 bytes)                               │
├──────────────────────────────────────────────────────┤
│ CRC (4 bytes) - Checksum for integrity              │
├──────────────────────────────────────────────────────┤
│ Magic Byte (1 byte) - Protocol version              │
├──────────────────────────────────────────────────────┤
│ Attributes (1 byte) - Compression, timestamp type   │
├──────────────────────────────────────────────────────┤
│ Timestamp (8 bytes)                                  │
├──────────────────────────────────────────────────────┤
│ Key Length (4 bytes)                                 │
├──────────────────────────────────────────────────────┤
│ Key (variable)                                       │
├──────────────────────────────────────────────────────┤
│ Value Length (4 bytes)                               │
├──────────────────────────────────────────────────────┤
│ Value (variable) - Actual message payload           │
└──────────────────────────────────────────────────────┘
```

**Implementation**:
```java
@Service
public class BrokerService {
    
    private Map<String, PartitionLog> partitionLogs = new ConcurrentHashMap<>();
    private ZooKeeperClient zkClient;
    
    // Accept message from producer
    public ProduceResponse produce(ProduceRequest request) {
        String topic = request.getTopic();
        int partition = request.getPartition();
        Message message = request.getMessage();
        
        // 1. Validate partition leadership
        if (!isLeader(topic, partition)) {
            throw new NotLeaderException("Forward to leader: " + getLeader(topic, partition));
        }
        
        // 2. Get partition log
        String partitionKey = topic + "-" + partition;
        PartitionLog log = partitionLogs.get(partitionKey);
        
        // 3. Assign offset
        long offset = log.getNextOffset();
        message.setOffset(offset);
        message.setTimestamp(System.currentTimeMillis());
        
        // 4. Write to local log (append)
        log.append(message);
        
        // 5. Replicate to followers (async)
        replicateToFollowers(topic, partition, message);
        
        // 6. Wait for acknowledgment based on acks config
        if (request.getAcks() == -1) { // all
            waitForAllISR(topic, partition, offset);
        } else if (request.getAcks() == 1) { // leader only
            // Already written, return immediately
        }
        
        return new ProduceResponse(offset, "SUCCESS");
    }
    
    // Serve messages to consumer
    public FetchResponse fetch(FetchRequest request) {
        String topic = request.getTopic();
        int partition = request.getPartition();
        long fromOffset = request.getFromOffset();
        int maxBytes = request.getMaxBytes();
        
        String partitionKey = topic + "-" + partition;
        PartitionLog log = partitionLogs.get(partitionKey);
        
        // Read messages from offset
        List<Message> messages = log.read(fromOffset, maxBytes);
        
        return new FetchResponse(messages, log.getHighWaterMark());
    }
}

// Partition Log (single partition on disk)
class PartitionLog {
    private String topicName;
    private int partitionNum;
    private List<LogSegment> segments;
    private LogSegment activeSegment;
    private AtomicLong nextOffset;
    private long highWaterMark; // Offset of last committed message (replicated to all ISR)
    
    public synchronized void append(Message message) {
        // Check if active segment is full (1GB)
        if (activeSegment.size() >= 1_073_741_824) {
            roll(); // Create new segment
        }
        
        // Serialize message
        ByteBuffer buffer = serializeMessage(message);
        
        // Append to segment file
        activeSegment.append(buffer);
        
        // Update index (offset → file position)
        activeSegment.updateIndex(message.getOffset(), activeSegment.position());
        
        // Increment offset
        nextOffset.incrementAndGet();
    }
    
    public List<Message> read(long fromOffset, int maxBytes) {
        List<Message> messages = new ArrayList<>();
        int bytesRead = 0;
        
        // Find segment containing fromOffset
        LogSegment segment = findSegment(fromOffset);
        
        if (segment == null) {
            return messages; // Offset too old (already cleaned up)
        }
        
        // Get file position from index
        long position = segment.getIndex().lookup(fromOffset);
        
        // Read messages sequentially
        RandomAccessFile file = segment.getFile();
        file.seek(position);
        
        while (bytesRead < maxBytes) {
            try {
                Message message = deserializeMessage(file);
                if (message.getOffset() < highWaterMark) {
                    messages.add(message);
                    bytesRead += message.size();
                } else {
                    break; // Reached uncommitted messages
                }
            } catch (EOFException e) {
                break; // End of segment
            }
        }
        
        return messages;
    }
    
    private void roll() {
        // Close active segment
        activeSegment.close();
        
        // Create new segment
        long baseOffset = nextOffset.get();
        activeSegment = new LogSegment(topicName, partitionNum, baseOffset);
        segments.add(activeSegment);
    }
}
```

---

### 3. Producer Client

**Features**:
- Message batching (reduce network calls)
- Compression (gzip, snappy, lz4)
- Partitioning strategy (round-robin, key-based, custom)
- Retry logic
- Idempotent producer (exactly-once)

**Implementation**:
```java
public class Producer {
    private String bootstrapServers;
    private Map<String, List<Message>> batchBuffer = new ConcurrentHashMap<>();
    private ScheduledExecutorService scheduler;
    
    public Producer(String bootstrapServers) {
        this.bootstrapServers = bootstrapServers;
        
        // Flush batches every 100ms
        scheduler = Executors.newScheduledThreadPool(1);
        scheduler.scheduleAtFixedRate(this::flushBatches, 100, 100, TimeUnit.MILLISECONDS);
    }
    
    public Future<ProduceResponse> send(String topic, String key, byte[] value) {
        Message message = new Message(key, value);
        
        // Determine partition
        int partition = selectPartition(topic, key);
        
        // Add to batch buffer
        String batchKey = topic + "-" + partition;
        batchBuffer.computeIfAbsent(batchKey, k -> new ArrayList<>()).add(message);
        
        // Return future
        CompletableFuture<ProduceResponse> future = new CompletableFuture<>();
        message.setFuture(future);
        
        // Flush immediately if batch is full (16KB)
        if (getBatchSize(batchKey) >= 16384) {
            flushBatch(topic, partition);
        }
        
        return future;
    }
    
    private void flushBatches() {
        for (Map.Entry<String, List<Message>> entry : batchBuffer.entrySet()) {
            String[] parts = entry.getKey().split("-");
            String topic = parts[0];
            int partition = Integer.parseInt(parts[1]);
            
            flushBatch(topic, partition);
        }
    }
    
    private void flushBatch(String topic, int partition) {
        String batchKey = topic + "-" + partition;
        List<Message> messages = batchBuffer.remove(batchKey);
        
        if (messages == null || messages.isEmpty()) {
            return;
        }
        
        // Compress batch
        byte[] compressed = compress(messages);
        
        // Send to broker (with retry)
        ProduceRequest request = new ProduceRequest(topic, partition, compressed);
        ProduceResponse response = sendWithRetry(request, 3);
        
        // Complete futures
        for (Message msg : messages) {
            msg.getFuture().complete(response);
        }
    }
    
    private int selectPartition(String topic, String key) {
        if (key == null) {
            // Round-robin
            return Math.abs(ThreadLocalRandom.current().nextInt()) % getPartitionCount(topic);
        } else {
            // Hash-based (ensures messages with same key go to same partition)
            return Math.abs(key.hashCode()) % getPartitionCount(topic);
        }
    }
    
    private ProduceResponse sendWithRetry(ProduceRequest request, int maxRetries) {
        for (int i = 0; i < maxRetries; i++) {
            try {
                // Get partition leader from metadata
                String leader = getPartitionLeader(request.getTopic(), request.getPartition());
                
                // Send HTTP/TCP request to broker
                HttpClient client = HttpClient.newHttpClient();
                HttpRequest httpRequest = HttpRequest.newBuilder()
                    .uri(URI.create("http://" + leader + "/produce"))
                    .POST(HttpRequest.BodyPublishers.ofByteArray(serialize(request)))
                    .build();
                
                HttpResponse<String> response = client.send(httpRequest, HttpResponse.BodyHandlers.ofString());
                
                return deserialize(response.body(), ProduceResponse.class);
                
            } catch (Exception e) {
                if (i == maxRetries - 1) {
                    throw new ProduceException("Failed after " + maxRetries + " retries", e);
                }
                // Exponential backoff
                Thread.sleep((long) Math.pow(2, i) * 100);
            }
        }
        throw new ProduceException("Should not reach here");
    }
}
```

**Usage**:
```java
Producer producer = new Producer("broker1:9092,broker2:9092,broker3:9092");

// Fire and forget
producer.send("order-events", "order123", orderJson.getBytes());

// Async with callback
producer.send("user-clicks", "user456", clickData.getBytes())
    .thenAccept(response -> {
        System.out.println("Message sent, offset: " + response.getOffset());
    })
    .exceptionally(ex -> {
        System.err.println("Send failed: " + ex.getMessage());
        return null;
    });

// Sync (blocking)
ProduceResponse response = producer.send("payments", "txn789", paymentData.getBytes()).get();
```

---

### 4. Consumer & Consumer Groups

**Consumer Group**: Multiple consumers that share the load of processing messages

**Partition Assignment**:
```
Topic: order-events (6 partitions)
Consumer Group: payment-service (3 consumers)

Assignment:
  Consumer 1: Partition 0, 1
  Consumer 2: Partition 2, 3
  Consumer 3: Partition 4, 5

Rule: Each partition is assigned to exactly ONE consumer in the group
```

**Rebalancing**: When a consumer joins/leaves, partitions are reassigned

**Implementation**:
```java
public class Consumer {
    private String bootstrapServers;
    private String groupId;
    private Set<String> subscribedTopics;
    private Map<TopicPartition, Long> offsets = new ConcurrentHashMap<>();
    private ConsumerCoordinator coordinator;
    
    public Consumer(String bootstrapServers, String groupId) {
        this.bootstrapServers = bootstrapServers;
        this.groupId = groupId;
        this.coordinator = new ConsumerCoordinator(bootstrapServers, groupId);
    }
    
    public void subscribe(List<String> topics) {
        this.subscribedTopics = new HashSet<>(topics);
        
        // Join consumer group and get partition assignment
        coordinator.joinGroup();
        Set<TopicPartition> assignment = coordinator.getAssignment();
        
        // Load committed offsets for assigned partitions
        for (TopicPartition tp : assignment) {
            Long committedOffset = coordinator.fetchCommittedOffset(tp);
            offsets.put(tp, committedOffset != null ? committedOffset : 0L);
        }
    }
    
    public ConsumerRecords poll(Duration timeout) {
        // Check for rebalance
        if (coordinator.needsRebalance()) {
            coordinator.rebalance();
            // Reload offsets after rebalance
        }
        
        ConsumerRecords records = new ConsumerRecords();
        long deadline = System.currentTimeMillis() + timeout.toMillis();
        
        for (TopicPartition tp : offsets.keySet()) {
            long currentOffset = offsets.get(tp);
            
            // Fetch messages from broker
            FetchRequest request = new FetchRequest(
                tp.topic(),
                tp.partition(),
                currentOffset,
                1048576 // 1MB max
            );
            
            FetchResponse response = fetchFromBroker(request);
            
            for (Message message : response.getMessages()) {
                records.add(new ConsumerRecord(
                    tp.topic(),
                    tp.partition(),
                    message.getOffset(),
                    message.getKey(),
                    message.getValue()
                ));
                
                // Update local offset (not committed yet)
                offsets.put(tp, message.getOffset() + 1);
            }
            
            if (System.currentTimeMillis() > deadline) {
                break;
            }
        }
        
        return records;
    }
    
    public void commitSync() {
        // Commit offsets to coordinator
        for (Map.Entry<TopicPartition, Long> entry : offsets.entrySet()) {
            coordinator.commitOffset(entry.getKey(), entry.getValue());
        }
    }
    
    public void commitAsync() {
        // Async commit (fire and forget)
        CompletableFuture.runAsync(() -> commitSync());
    }
}

// Consumer coordinator (manages group membership and partition assignment)
class ConsumerCoordinator {
    private String groupId;
    private String consumerId;
    private ZooKeeperClient zkClient;
    
    public void joinGroup() {
        // Register consumer in ZooKeeper
        consumerId = UUID.randomUUID().toString();
        zkClient.create("/consumers/" + groupId + "/" + consumerId, "");
        
        // Send heartbeat every 3 seconds
        startHeartbeat();
    }
    
    public Set<TopicPartition> getAssignment() {
        // Get all consumers in group
        List<String> consumers = zkClient.getChildren("/consumers/" + groupId);
        consumers.sort(String::compareTo); // Consistent ordering
        
        // Get all partitions for subscribed topics
        List<TopicPartition> allPartitions = new ArrayList<>();
        for (String topic : subscribedTopics) {
            int numPartitions = getPartitionCount(topic);
            for (int i = 0; i < numPartitions; i++) {
                allPartitions.add(new TopicPartition(topic, i));
            }
        }
        
        // Assign partitions using round-robin
        Set<TopicPartition> myAssignment = new HashSet<>();
        int consumerIndex = consumers.indexOf(consumerId);
        
        for (int i = 0; i < allPartitions.size(); i++) {
            if (i % consumers.size() == consumerIndex) {
                myAssignment.add(allPartitions.get(i));
            }
        }
        
        return myAssignment;
    }
    
    public void commitOffset(TopicPartition tp, long offset) {
        // Store offset in ZooKeeper or dedicated offset topic
        zkClient.createOrUpdate(
            "/consumers/" + groupId + "/offsets/" + tp.topic() + "/" + tp.partition(),
            String.valueOf(offset)
        );
    }
    
    public Long fetchCommittedOffset(TopicPartition tp) {
        String offsetStr = zkClient.getData(
            "/consumers/" + groupId + "/offsets/" + tp.topic() + "/" + tp.partition()
        );
        return offsetStr != null ? Long.parseLong(offsetStr) : null;
    }
}
```

**Usage**:
```java
Consumer consumer = new Consumer("broker1:9092,broker2:9092", "payment-service");
consumer.subscribe(Arrays.asList("order-events", "payment-events"));

while (true) {
    ConsumerRecords records = consumer.poll(Duration.ofMillis(1000));
    
    for (ConsumerRecord record : records) {
        System.out.println("Received: " + new String(record.value()));
        processMessage(record);
    }
    
    // Commit offsets after processing
    consumer.commitSync(); // or commitAsync()
}
```

---

### 5. Replication

**Goal**: High availability and durability

**Replication Factor**: Number of copies (typically 3)

```
Topic: order-events, Partition 0, Replication Factor: 3

Leader: Broker 1
Followers: Broker 2, Broker 3

Write path:
  Producer → Broker 1 (leader) → ACK (if acks=1)
                ↓
          Broker 2, 3 (async replication)
```

**ISR (In-Sync Replicas)**: Replicas that are caught up with leader

**Acknowledgment Modes**:
1. **acks=0**: Fire and forget (no acknowledgment, lowest latency, may lose data)
2. **acks=1**: Leader acknowledgment (medium latency, may lose data if leader fails before replication)
3. **acks=-1 (all)**: All ISR acknowledgment (highest durability, highest latency)

**Implementation**:
```java
class ReplicationManager {
    
    public void replicateToFollowers(String topic, int partition, Message message) {
        Partition part = getPartition(topic, partition);
        
        List<Integer> followerBrokers = part.getReplicaBrokerIds();
        followerBrokers.remove((Integer) part.getLeaderBrokerId()); // Exclude leader
        
        // Send replication request to all followers (async)
        List<CompletableFuture<Void>> futures = followerBrokers.stream()
            .map(brokerId -> CompletableFuture.runAsync(() -> {
                replicateToFollower(brokerId, topic, partition, message);
            }))
            .collect(Collectors.toList());
        
        // Don't wait for followers (async replication)
        // Leader tracks high water mark based on ISR progress
    }
    
    private void replicateToFollower(int brokerId, String topic, int partition, Message message) {
        String brokerAddress = getBrokerAddress(brokerId);
        
        try {
            // Send message to follower
            ReplicationRequest request = new ReplicationRequest(topic, partition, message);
            ReplicationResponse response = sendToFollower(brokerAddress, request);
            
            if (response.isSuccess()) {
                // Update ISR if follower is caught up
                updateISR(topic, partition, brokerId);
            }
        } catch (Exception e) {
            // Remove from ISR if replication fails
            removeFromISR(topic, partition, brokerId);
        }
    }
    
    // Follower receives replication request
    public void handleReplicationRequest(ReplicationRequest request) {
        String topic = request.getTopic();
        int partition = request.getPartition();
        Message message = request.getMessage();
        
        // Append to local log (same as leader)
        PartitionLog log = partitionLogs.get(topic + "-" + partition);
        log.append(message);
        
        // Send ACK back to leader
        sendACK(request.getLeaderId(), topic, partition, message.getOffset());
    }
}
```

---

### 6. Exactly-Once Semantics

**Challenge**: Prevent duplicate message processing

**Solutions**:

**1. Idempotent Producer**:
```java
// Producer assigns sequence number to each message
message.setProducerId(producerId);
message.setSequenceNumber(seqNum++);

// Broker deduplicates based on (producerId, sequenceNumber)
if (alreadyProcessed(message.getProducerId(), message.getSequenceNumber())) {
    return; // Duplicate, ignore
}
```

**2. Transactional Producer**:
```java
producer.initTransactions();

try {
    producer.beginTransaction();
    
    producer.send("order-events", orderMessage);
    producer.send("inventory-events", inventoryMessage);
    producer.send("payment-events", paymentMessage);
    
    producer.commitTransaction();
} catch (Exception e) {
    producer.abortTransaction();
}
```

**3. Idempotent Consumer**:
```java
// Store processed message IDs in database
Set<String> processedIds = new HashSet<>();

for (ConsumerRecord record : records) {
    String messageId = record.key();
    
    if (processedIds.contains(messageId)) {
        continue; // Already processed
    }
    
    processMessage(record);
    processedIds.add(messageId);
    
    // Persist processed ID
    db.insert("processed_messages", messageId);
}
```

---

### 7. Message Retention & Cleanup

**Retention Policies**:
1. **Time-based**: Delete messages older than X days
2. **Size-based**: Delete old segments when total size > X GB
3. **Compaction**: Keep only latest value for each key

**Log Compaction** (for changelogs):
```
Before compaction:
  offset 0: key=user123, value={name: "John", age: 30}
  offset 1: key=user456, value={name: "Jane", age: 25}
  offset 2: key=user123, value={name: "John", age: 31}  ← Updated
  offset 3: key=user789, value={name: "Bob", age: 40}
  offset 4: key=user456, value=null  ← Deleted (tombstone)

After compaction:
  offset 2: key=user123, value={name: "John", age: 31}  ← Latest
  offset 3: key=user789, value={name: "Bob", age: 40}
  offset 4: key=user456, value=null  ← Tombstone retained
```

**Implementation**:
```java
@Scheduled(cron = "0 0 2 * * *") // Daily at 2 AM
public void cleanupOldSegments() {
    for (PartitionLog log : partitionLogs.values()) {
        long retentionMs = log.getRetentionMs();
        long cutoffTime = System.currentTimeMillis() - retentionMs;
        
        List<LogSegment> segmentsToDelete = log.getSegments().stream()
            .filter(segment -> segment.getLastModified() < cutoffTime)
            .collect(Collectors.toList());
        
        for (LogSegment segment : segmentsToDelete) {
            // Delete segment files
            segment.delete();
            log.removeSegment(segment);
        }
    }
}
```

---

## Scalability & Performance

### 1. Partitioning Strategy

**Rule of Thumb**: 1 partition per CPU core per consumer

Example:
- Topic: order-events
- Expected throughput: 100K msg/sec
- Single consumer throughput: 10K msg/sec
- Number of consumers: 10
- **Partitions needed**: 10-20 partitions

### 2. Zero-Copy

**Problem**: Traditional I/O involves multiple data copies
```
Disk → Kernel buffer → Application buffer → Socket buffer → NIC
```

**Solution**: Use `sendfile()` system call (zero-copy)
```
Disk → Kernel buffer → NIC (direct transfer)
```

```java
// Java NIO zero-copy
FileChannel fileChannel = new RandomAccessFile(file, "r").getChannel();
SocketChannel socketChannel = SocketChannel.open();
fileChannel.transferTo(0, fileChannel.size(), socketChannel);
```

**Benefit**: 2-3x faster, 50% less CPU

### 3. Batching

**Producer**: Batch messages before sending (reduces network calls)
- Batch size: 16KB
- Linger time: 100ms

**Broker**: Batch writes to disk
- Write buffer: 64KB
- Flush interval: 1 second

### 4. Compression

**Compression Algorithms**:
- **gzip**: Best compression ratio (5x), slower
- **snappy**: Fast, good compression (2x)
- **lz4**: Fastest, moderate compression (1.5x)

**Example**:
```java
producer.setProperty("compression.type", "lz4");
```

### 5. Horizontal Scaling

**Add Brokers**:
```
Initial: 3 brokers (100K partitions)
After scaling: 10 brokers

Rebalance partitions across all brokers (automatic)
```

**Add Partitions** (to existing topic):
```bash
kafka-topics.sh --alter --topic order-events --partitions 20
```

**Note**: Cannot decrease partitions (would lose data)

---

## Technology Stack

| Component | Technology | Justification |
|-----------|-----------|---------------|
| **Language** | Java / Scala | JVM performance, mature ecosystem |
| **Coordination** | ZooKeeper / KRaft | Distributed consensus, leader election |
| **Storage** | Local disk (SSD/NVMe) | Sequential writes are fast |
| **Serialization** | Avro / Protobuf | Schema evolution, efficient |
| **Monitoring** | Prometheus + Grafana | Metrics and dashboards |
| **Deployment** | Kubernetes | Container orchestration |

---

## Interview Q&A

### Q1: How do you ensure message ordering?
**Answer**:
- Ordering is guaranteed **within a partition**, not across partitions
- Use same key for related messages → routed to same partition
- Single consumer per partition ensures ordered processing

### Q2: How do you handle broker failure?
**Answer**:
1. **Leader failure**: ZooKeeper detects (via heartbeat), elects new leader from ISR
2. **Follower failure**: Removed from ISR, catches up after recovery
3. **Network partition**: Broker with majority partitions becomes leader

### Q3: How do you prevent message loss?
**Answer**:
1. **Replication**: replication_factor=3
2. **Acknowledgment**: acks=all (wait for all ISR)
3. **Disk persistence**: fsync after every write
4. **Idempotent producer**: Retry without duplicates

### Q4: How do you prevent duplicate processing?
**Answer**:
1. **Exactly-once producer**: Transactional API
2. **Idempotent consumer**: Track processed message IDs
3. **Offset management**: Commit offsets after processing (not before)

### Q5: How do you handle slow consumers?
**Answer**:
1. **Consumer lag monitoring**: Alert if lag > threshold
2. **Add consumers**: Scale consumer group (if partitions available)
3. **Add partitions**: Increase parallelism
4. **Optimize processing**: Improve consumer code performance
5. **Dead letter queue**: Move failed messages to DLQ

### Q6: Kafka vs RabbitMQ?
**Answer**:
| Feature | Kafka | RabbitMQ |
|---------|-------|----------|
| **Model** | Pub-sub (log-based) | Queue (delete after consume) |
| **Throughput** | Very high (millions/sec) | Moderate (tens of thousands/sec) |
| **Ordering** | Per-partition | Per-queue |
| **Replay** | Yes (seek to any offset) | No |
| **Use case** | Event streaming, logs | Task queues, RPC |

### Q7: How do you monitor Kafka?
**Answer**:
**Metrics**:
- Throughput (messages/sec, bytes/sec)
- Latency (producer latency, consumer lag)
- Partition balance (even distribution)
- ISR shrink/expand (replication health)
- Disk usage (per broker)

**Alerts**:
- Consumer lag > 1M messages
- ISR < replication_factor (under-replicated)
- Broker disk > 80% full

### Q8: How do you handle large messages (>1MB)?
**Answer**:
1. **Increase max.message.bytes**: Not recommended (affects performance)
2. **External storage**: Store message in S3, send reference in Kafka
3. **Chunking**: Split message into multiple smaller messages
4. **Compression**: Compress large payloads

### Q9: How do you upgrade Kafka without downtime?
**Answer**:
1. **Rolling upgrade**: Upgrade brokers one at a time
2. **Blue-green deployment**: Run parallel cluster, migrate topics
3. **Compatibility**: Use compatible broker versions (e.g., 2.8 → 3.0)
4. **Test**: Validate on staging first

### Q10: How do you implement priority queue?
**Answer**:
- Kafka doesn't support priority natively
- **Workaround**: Use separate topics (high-priority-topic, low-priority-topic)
- Consumers poll high-priority first

---

## Cost Estimation (AWS - Monthly)

| Service | Specification | Cost |
|---------|--------------|------|
| **EC2** (Brokers) | 10 × i3.4xlarge (16 vCPU, 122GB, 2×1.9TB NVMe) | $12,000 |
| **EBS** (if not using instance storage) | 50TB gp3 SSD | $5,000 |
| **S3** (backups) | 10TB | $230 |
| **Data Transfer** | 100TB outbound | $9,000 |
| **ZooKeeper** (if not KRaft) | 3 × t3.medium | $90 |
| **Monitoring** | CloudWatch | $500 |
| **Total** | | **~$27,000/month** |

**Alternative**: Use managed service (AWS MSK, Confluent Cloud) - $40,000/month

---

**This comprehensive HLD covers a production-grade pub-sub messaging system!**
