# Distributed Logging Framework - High Level Design

## 1. Overview

A distributed logging framework (like ELK Stack - Elasticsearch, Logstash, Kibana) provides centralized log collection, processing, storage, and analysis for microservices architectures. It enables real-time log aggregation, search, monitoring, alerting, and visualization across thousands of distributed services.

**Key Features:**
- Centralized log collection from multiple sources
- Real-time log streaming and processing
- Structured and unstructured log support
- Full-text search across logs
- Log parsing and enrichment
- Alerting and anomaly detection
- Visualization dashboards
- Log retention and archival
- Access control and security

## 2. Requirements

### 2.1 Functional Requirements

**Core Features:**

1. **Log Collection**
   - Support multiple log sources (application logs, system logs, container logs)
   - Multiple log formats (JSON, plain text, syslog)
   - Log shipping from distributed services
   - Auto-discovery of new services
   - Batch and streaming ingestion

2. **Log Processing**
   - Log parsing and structure extraction
   - Field enrichment and transformation
   - Filtering and sampling
   - Log normalization
   - Multi-line log handling
   - Grok pattern matching

3. **Log Storage**
   - Time-series optimized storage
   - Compression
   - Indexing for fast search
   - Data retention policies
   - Hot/warm/cold tier storage
   - Log archival to S3/Glacier

4. **Log Search and Query**
   - Full-text search
   - Field-based filtering
   - Time range queries
   - Aggregations and analytics
   - Regular expression support
   - Query DSL

5. **Visualization**
   - Real-time log tailing
   - Custom dashboards
   - Time-series charts
   - Log distribution graphs
   - Heat maps
   - Geo-mapping

6. **Alerting**
   - Threshold-based alerts
   - Anomaly detection
   - Pattern matching alerts
   - Multi-channel notifications (email, Slack, PagerDuty)
   - Alert suppression and throttling

7. **Access Control**
   - Role-based access control (RBAC)
   - Field-level security
   - Audit logging
   - Data isolation by tenant

### 2.2 Non-Functional Requirements

1. **Scalability**: Handle 1TB+ logs per day, 100K+ events per second
2. **Performance**:
   - Ingestion latency < 1s
   - Search query response < 2s
   - Real-time streaming with < 5s delay
3. **Availability**: 99.9% uptime
4. **Reliability**: No log loss (at-least-once delivery)
5. **Durability**: Persistent storage with replication
6. **Cost Efficiency**: Optimize storage costs with tiering
7. **Security**: Encryption in transit and at rest

### 2.3 Extended Requirements

- Log correlation across services (trace ID)
- Machine learning for anomaly detection
- Log sampling for high-volume services
- Multi-tenancy support
- Integration with APM tools
- Log forwarding to external systems
- Compliance with GDPR (PII masking)

## 3. Capacity Estimation and Constraints

### 3.1 Traffic Estimates

**Assumptions:**
- 500 microservices
- Each service generates 1000 log entries per minute
- Average log size: 1 KB
- Peak traffic: 5x average

**Calculations:**
- Log entries per second: (500 * 1000) / 60 = 8,333 logs/sec
- Peak: 8,333 * 5 = 41,665 logs/sec
- Data ingestion rate: 8,333 logs/sec * 1 KB = 8.3 MB/sec
- Peak ingestion: 41.6 MB/sec
- Daily volume: 8.3 MB/sec * 86400 = 717 GB/day
- Monthly volume: 717 GB * 30 = 21.5 TB/month

### 3.2 Storage Estimates

**Log Retention:**
- Hot tier (searchable): 7 days = 717 GB * 7 = 5 TB
- Warm tier (searchable, compressed): 23 days = 717 GB * 23 * 0.5 = 8.2 TB
- Cold tier (archived): 11 months = 21.5 TB * 11 * 0.2 = 47.3 TB
- Total: ~60 TB

**With replication (3x):**
- Hot + Warm: (5 TB + 8.2 TB) * 3 = 39.6 TB
- Cold (S3): 47.3 TB (S3 has built-in durability)
- Total: ~87 TB

### 3.3 Bandwidth Estimates

**Incoming:**
- Average: 8.3 MB/sec
- Peak: 41.6 MB/sec

**Outgoing (Query):**
- 100 concurrent users
- Average query returns 1000 logs * 1 KB = 1 MB
- Query rate: 10 QPS
- Bandwidth: 10 QPS * 1 MB = 10 MB/sec

## 4. System Architecture

### 4.1 High-Level Architecture (ELK-style)

```
┌─────────────────────────────────────────────────────────────┐
│                     Application Layer                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │Service 1 │  │Service 2 │  │Service 3 │  │Service N │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
│       │             │             │             │           │
│  ┌────▼─────────────▼─────────────▼─────────────▼──────┐   │
│  │          Log Collection Agents (Beats)             │   │
│  │  (Filebeat, Metricbeat, Container Logs)            │   │
│  └────────────────────────┬────────────────────────────┘   │
└───────────────────────────┼────────────────────────────────┘
                            │
                            │ (Forward logs)
                            │
              ┌─────────────▼──────────────┐
              │      Message Queue         │
              │        (Kafka)             │
              │  (Buffer, Replay, Scale)   │
              └─────────────┬──────────────┘
                            │
                            │
              ┌─────────────▼──────────────┐
              │    Log Processing Layer    │
              │       (Logstash)           │
              │  - Parsing                 │
              │  - Filtering               │
              │  - Enrichment              │
              │  - Transformation          │
              └─────────────┬──────────────┘
                            │
                            │
       ┌────────────────────┼────────────────────┐
       │                    │                    │
       │                    │                    │
┌──────▼──────┐     ┌──────▼──────┐     ┌──────▼──────┐
│Elasticsearch│     │Elasticsearch│     │Elasticsearch│
│   Node 1    │     │   Node 2    │     │   Node N    │
│ (Hot Tier)  │     │ (Warm Tier) │     │ (Cold Tier) │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                    │                    │
       └────────────────────┼────────────────────┘
                            │
                            │
              ┌─────────────▼──────────────┐
              │    Visualization Layer     │
              │        (Kibana)            │
              │  - Dashboards              │
              │  - Search UI               │
              │  - Alerting                │
              └────────────────────────────┘
                            │
              ┌─────────────▼──────────────┐
              │      Alert Manager         │
              │  - Email, Slack, PagerDuty │
              └────────────────────────────┘
```

### 4.2 Data Flow

```
Application → Agent → Kafka → Logstash → Elasticsearch → Kibana
                                     ↓
                               (Archive)
                                     ↓
                                    S3
```

## 5. Core Components

### 5.1 Log Collection Agents (Beats)

**Responsibilities:**
- Monitor log files on disk
- Tail container logs (Docker, Kubernetes)
- Parse and structure logs locally
- Buffer logs during network issues
- Compress and batch logs
- Add metadata (host, service, environment)

**Types of Beats:**
1. **Filebeat**: File-based log collection
2. **Metricbeat**: System and service metrics
3. **Packetbeat**: Network packet analysis
4. **Auditbeat**: Audit data
5. **Heartbeat**: Uptime monitoring

**Filebeat Configuration Example:**
```yaml
filebeat.inputs:
  - type: log
    enabled: true
    paths:
      - /var/log/app/*.log
    fields:
      service: payment-service
      environment: production
    multiline:
      pattern: '^[0-9]{4}-[0-9]{2}-[0-9]{2}'
      negate: true
      match: after
    json.keys_under_root: true
    json.add_error_key: true

output.kafka:
  hosts: ["kafka1:9092", "kafka2:9092"]
  topic: "logs"
  partition.round_robin:
    reachable_only: false
  required_acks: 1
  compression: gzip
  max_message_bytes: 1000000
```

**Structured Logging (Application Side):**
```java
// Instead of:
logger.info("User " + userId + " made payment of " + amount);

// Use structured logging:
logger.info("Payment processed", 
    kv("user_id", userId),
    kv("amount", amount),
    kv("currency", "USD"),
    kv("trace_id", traceId)
);

// Output JSON:
{
  "timestamp": "2026-04-07T10:30:00.123Z",
  "level": "INFO",
  "message": "Payment processed",
  "user_id": "12345",
  "amount": 99.99,
  "currency": "USD",
  "trace_id": "abc123",
  "service": "payment-service",
  "host": "host-123"
}
```

**Technology:**
- Filebeat/Fluentd/Fluent Bit
- Lightweight agents (< 50 MB memory)
- Written in Go (Filebeat)

### 5.2 Message Queue (Kafka)

**Responsibilities:**
- Buffer logs between collection and processing
- Handle traffic spikes
- Enable replay for processing failures
- Provide multiple consumer groups
- Guarantee at-least-once delivery

**Why Kafka?**
1. **High throughput**: Millions of messages/sec
2. **Durability**: Persistent storage with replication
3. **Scalability**: Horizontal scaling with partitions
4. **Replay**: Process historical logs
5. **Decoupling**: Producers and consumers independent

**Kafka Topic Configuration:**
```yaml
topics:
  - name: logs
    partitions: 30  # For parallelism
    replication_factor: 3
    retention.ms: 604800000  # 7 days
    compression.type: gzip
    min.insync.replicas: 2
```

**Partitioning Strategy:**
- Partition by service_name (co-locate logs from same service)
- Or partition by hash(service_name + host) for better distribution

**Consumer Groups:**
- Logstash processors (consumer group: logstash-processors)
- Real-time alerting (consumer group: alerting-service)
- Backup archiver (consumer group: log-archiver)

**Technology:**
- Apache Kafka
- Zookeeper for cluster coordination
- Schema Registry for message schemas

### 5.3 Log Processing (Logstash)

**Responsibilities:**
- Parse unstructured logs
- Extract fields using patterns
- Enrich logs with additional context
- Filter and drop unwanted logs
- Transform and normalize data
- Route logs to different destinations

**Logstash Pipeline:**

**Input → Filter → Output**

**Example Configuration:**
```ruby
input {
  kafka {
    bootstrap_servers => "kafka1:9092,kafka2:9092"
    topics => ["logs"]
    consumer_threads => 4
    codec => json
    group_id => "logstash-processors"
  }
}

filter {
  # Parse timestamp
  date {
    match => ["timestamp", "ISO8601"]
    target => "@timestamp"
  }
  
  # Grok parsing for unstructured logs
  if [message] =~ /^[0-9]{4}-[0-9]{2}-[0-9]{2}/ {
    grok {
      match => {
        "message" => "%{TIMESTAMP_ISO8601:timestamp} %{LOGLEVEL:level} \[%{DATA:service}\] %{GREEDYDATA:message_text}"
      }
    }
  }
  
  # Extract trace ID from message
  if [message] =~ /trace_id=/ {
    grok {
      match => {
        "message" => "trace_id=%{WORD:trace_id}"
      }
    }
  }
  
  # GeoIP enrichment
  if [client_ip] {
    geoip {
      source => "client_ip"
      target => "geoip"
    }
  }
  
  # Drop debug logs in production
  if [level] == "DEBUG" and [environment] == "production" {
    drop {}
  }
  
  # Mask PII (credit card numbers)
  mutate {
    gsub => [
      "message", "\d{4}-\d{4}-\d{4}-\d{4}", "XXXX-XXXX-XXXX-XXXX"
    ]
  }
  
  # Add computed fields
  ruby {
    code => "event.set('log_size', event.to_json.bytesize)"
  }
}

output {
  elasticsearch {
    hosts => ["es1:9200", "es2:9200"]
    index => "logs-%{[service]}-%{+YYYY.MM.dd}"
    template_name => "logs"
    template_overwrite => true
  }
  
  # Send errors to separate index
  if [level] == "ERROR" {
    elasticsearch {
      hosts => ["es1:9200"]
      index => "errors-%{+YYYY.MM.dd}"
    }
  }
  
  # Archive to S3
  s3 {
    region => "us-east-1"
    bucket => "logs-archive"
    time_file => 15  # Rotate every 15 minutes
    codec => "json_lines"
  }
}
```

**Logstash Pipelines (Parallel Processing):**
```yaml
pipelines:
  - pipeline.id: app-logs
    path.config: "/etc/logstash/app-logs.conf"
    pipeline.workers: 8
    
  - pipeline.id: system-logs
    path.config: "/etc/logstash/system-logs.conf"
    pipeline.workers: 4
```

**Technology:**
- Logstash (JRuby-based)
- Alternative: Fluentd (Ruby), Vector (Rust)
- Plugin ecosystem for inputs/filters/outputs

### 5.4 Storage (Elasticsearch)

**Responsibilities:**
- Store structured logs
- Index logs for fast search
- Support full-text and field-based queries
- Aggregations and analytics
- Data retention management
- Hot/warm/cold tier management

**Index Strategy:**

**Time-Based Indices:**
```
logs-service1-2026.04.07
logs-service1-2026.04.08
logs-service2-2026.04.07
```

**Benefits:**
- Easy deletion of old data (drop entire index)
- Optimized for time-range queries
- Parallel search across multiple indices

**Index Template:**
```json
{
  "index_patterns": ["logs-*"],
  "settings": {
    "number_of_shards": 5,
    "number_of_replicas": 2,
    "refresh_interval": "5s",
    "codec": "best_compression",
    "index.lifecycle.name": "logs_policy"
  },
  "mappings": {
    "properties": {
      "@timestamp": {"type": "date"},
      "level": {"type": "keyword"},
      "service": {"type": "keyword"},
      "host": {"type": "keyword"},
      "message": {"type": "text"},
      "trace_id": {"type": "keyword"},
      "user_id": {"type": "keyword"},
      "request_id": {"type": "keyword"},
      "duration_ms": {"type": "long"},
      "status_code": {"type": "integer"},
      "geoip": {
        "properties": {
          "location": {"type": "geo_point"}
        }
      }
    }
  }
}
```

**Index Lifecycle Management (ILM):**
```json
{
  "policy": "logs_policy",
  "phases": {
    "hot": {
      "min_age": "0ms",
      "actions": {
        "rollover": {
          "max_size": "50GB",
          "max_age": "1d"
        },
        "set_priority": {
          "priority": 100
        }
      }
    },
    "warm": {
      "min_age": "7d",
      "actions": {
        "allocate": {
          "require": {
            "data": "warm"
          }
        },
        "forcemerge": {
          "max_num_segments": 1
        },
        "shrink": {
          "number_of_shards": 1
        },
        "set_priority": {
          "priority": 50
        }
      }
    },
    "cold": {
      "min_age": "30d",
      "actions": {
        "allocate": {
          "require": {
            "data": "cold"
          }
        },
        "freeze": {},
        "set_priority": {
          "priority": 0
        }
      }
    },
    "delete": {
      "min_age": "90d",
      "actions": {
        "delete": {}
      }
    }
  }
}
```

**Query Examples:**

**Full-Text Search:**
```json
GET /logs-*/_search
{
  "query": {
    "match": {
      "message": "payment failed"
    }
  },
  "sort": [{"@timestamp": "desc"}],
  "size": 100
}
```

**Field-Based Filter:**
```json
GET /logs-*/_search
{
  "query": {
    "bool": {
      "must": [
        {"term": {"level": "ERROR"}},
        {"term": {"service": "payment-service"}}
      ],
      "filter": [
        {
          "range": {
            "@timestamp": {
              "gte": "now-1h"
            }
          }
        }
      ]
    }
  }
}
```

**Aggregation (Error Count by Service):**
```json
GET /logs-*/_search
{
  "size": 0,
  "query": {
    "bool": {
      "must": [{"term": {"level": "ERROR"}}],
      "filter": [{"range": {"@timestamp": {"gte": "now-24h"}}}]
    }
  },
  "aggs": {
    "errors_by_service": {
      "terms": {
        "field": "service",
        "size": 20
      }
    }
  }
}
```

**Trace Logs:**
```json
GET /logs-*/_search
{
  "query": {
    "term": {"trace_id": "abc123xyz"}
  },
  "sort": [{"@timestamp": "asc"}]
}
```

**Technology:**
- Elasticsearch 8.x
- Lucene-based indexing
- Distributed, horizontally scalable
- RESTful API

### 5.5 Visualization and Search (Kibana)

**Responsibilities:**
- Web UI for log search
- Dashboard creation and management
- Visualization widgets (charts, graphs, maps)
- Saved searches and filters
- Real-time log tailing (Live Tail)
- Alert rule configuration

**Key Features:**

**1. Discover (Search Interface):**
- Search bar with query DSL
- Time picker (last 15 min, 1 hour, 1 day, custom)
- Field filters
- Document view and JSON view
- Export to CSV

**2. Dashboards:**
- Time-series charts (line, area, bar)
- Pie charts (log distribution)
- Data tables
- Heat maps (error rates)
- Geo maps (requests by location)
- Metric displays (total errors, P99 latency)

**Example Dashboard:**
```
┌─────────────────────────────────────────────────────────┐
│  Service Health Dashboard                               │
├─────────────────────────────────────────────────────────┤
│  ┌───────────────┐  ┌───────────────┐  ┌─────────────┐ │
│  │ Total Logs    │  │ Error Rate    │  │ P99 Latency │ │
│  │  1.2M         │  │  0.03%        │  │  245ms      │ │
│  └───────────────┘  └───────────────┘  └─────────────┘ │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │ Error Count Over Time (Last 24h)                 │  │
│  │  [Line Chart showing spikes]                     │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  ┌──────────────────┐  ┌──────────────────────────┐   │
│  │ Top 10 Services  │  │ Error Distribution       │   │
│  │ by Error Count   │  │ [Pie Chart]              │   │
│  │ [Bar Chart]      │  │                          │   │
│  └──────────────────┘  └──────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

**3. Alerts:**

**Threshold Alert:**
```yaml
name: "High Error Rate"
conditions:
  - type: threshold
    index: "logs-*"
    query:
      bool:
        must:
          - term: {level: "ERROR"}
    timeField: "@timestamp"
    timeWindowSize: 5
    timeWindowUnit: "m"
    threshold:
      - alert: 100  # Alert if > 100 errors in 5 min
      - warning: 50
actions:
  - email:
      to: ["oncall@company.com"]
      subject: "High error rate detected"
  - slack:
      webhook_url: "https://hooks.slack.com/..."
      message: "Error rate exceeded threshold"
```

**Anomaly Detection Alert:**
```yaml
name: "Unusual Log Volume"
ml_job: "log_volume_anomaly"
conditions:
  - anomaly_score > 75
actions:
  - pagerduty:
      integration_key: "xxx"
      severity: "error"
```

**Technology:**
- Kibana (Node.js + React)
- Kibana Lens (drag-drop viz builder)
- Watcher/Alerting API
- Canvas for infographics

### 5.6 Alerting Service

**Responsibilities:**
- Monitor log patterns in real-time
- Evaluate alert rules
- Suppress duplicate alerts
- Route alerts to channels
- Alert escalation
- Alert acknowledgment tracking

**Alert Rule Types:**

**1. Threshold-based:**
```python
if count(logs where level="ERROR" in last 5 min) > 100:
    send_alert("High error rate")
```

**2. Pattern-based:**
```python
if logs contain "OutOfMemoryError":
    send_alert("OOM detected", severity="critical")
```

**3. Anomaly-based (ML):**
```python
if anomaly_score(log_volume) > 75:
    send_alert("Unusual log volume detected")
```

**4. Absence-based:**
```python
if no logs from "payment-service" in last 5 min:
    send_alert("Service down or not logging")
```

**Alert Deduplication:**
```python
def should_send_alert(alert):
    # Check if same alert sent in last 15 minutes
    recent_alerts = get_recent_alerts(
        rule_id=alert.rule_id,
        time_window=timedelta(minutes=15)
    )
    
    if recent_alerts:
        # Suppress duplicate
        return False
    
    return True
```

**Alert Aggregation:**
```python
# Instead of sending 100 individual alerts:
# "ERROR in service A"
# "ERROR in service A"
# ...

# Send one aggregated alert:
# "100 ERRORs in service A in last 5 minutes"
```

**Technology:**
- ElastAlert (Python-based)
- Prometheus Alertmanager
- Custom alerting service
- Integration: PagerDuty, OpsGenie, Slack, Email

### 5.7 Log Archival Service

**Responsibilities:**
- Archive old logs to cold storage
- Compress logs for storage efficiency
- Restore archived logs on demand
- Manage retention policies
- Cost optimization

**Archival Strategy:**

**Tiered Storage:**
1. **Hot (0-7 days)**: Elasticsearch, full search capability
2. **Warm (7-30 days)**: Elasticsearch, compressed, slower search
3. **Cold (30-90 days)**: S3 Glacier, restore on demand
4. **Delete (> 90 days)**: Permanently delete (unless compliance requirement)

**Archival Process:**
```python
def archive_old_indices():
    # Get indices older than 30 days
    old_indices = es.cat.indices(format="json")
    for index in old_indices:
        if index_age(index) > 30:
            # Export to S3
            export_index_to_s3(index)
            
            # Verify backup
            if verify_s3_backup(index):
                # Delete from Elasticsearch
                es.indices.delete(index=index.name)
```

**Restore from Archive:**
```python
def restore_archived_logs(date_range):
    # Find relevant S3 objects
    s3_objects = s3.list_objects(
        bucket="logs-archive",
        prefix=f"logs-{date_range}"
    )
    
    # Download and re-index
    for obj in s3_objects:
        logs = s3.get_object(obj)
        
        # Create temporary index
        temp_index = f"logs-restored-{uuid4()}"
        
        # Bulk index
        es.bulk(index=temp_index, body=logs)
    
    return temp_index
```

**Cost Optimization:**
```
Hot storage: $0.25/GB/month (SSD)
Warm storage: $0.10/GB/month (HDD)
Cold storage (S3): $0.004/GB/month
Glacier Deep Archive: $0.001/GB/month

Example:
- 1 TB hot (7 days): $250/month
- 3 TB warm (23 days): $300/month
- 22 TB cold (11 months): $88/month
Total: $638/month vs. $5,750/month (all hot)
```

**Technology:**
- AWS S3 / Google Cloud Storage
- S3 Lifecycle Policies
- Snapshot and Restore API
- Curator (Elasticsearch maintenance tool)

## 6. Database Design

### 6.1 Elasticsearch Index Structure

(Covered in section 5.4)

### 6.2 Metadata Database (PostgreSQL)

For storing metadata about indices, retention policies, users:

```sql
indices_metadata
- index_name (PK)
- index_pattern (e.g., logs-service1-*)
- creation_date
- size_bytes
- document_count
- retention_days
- lifecycle_policy
- archived_to_s3
- archived_at

users
- user_id (PK)
- username
- email
- role (admin, developer, viewer)
- allowed_indices (ARRAY)

alert_rules
- rule_id (PK)
- name
- description
- index_pattern
- query (JSONB)
- condition
- actions (JSONB)
- is_enabled
- created_by
- created_at

alert_history
- alert_id (PK)
- rule_id (FK)
- triggered_at
- severity
- message
- acknowledged_at
- acknowledged_by
```

## 7. API Design

### 7.1 Ingestion API

```
POST /api/v1/logs
  Body: [
    {
      "timestamp": "2026-04-07T10:30:00Z",
      "level": "ERROR",
      "service": "payment-service",
      "message": "Payment failed",
      "trace_id": "abc123",
      "user_id": "12345"
    }
  ]
  Response: {"success": true, "ingested": 1}

POST /api/v1/logs/batch
  Body: {"logs": [...]}  // Up to 1000 logs
  Response: {"success": true, "ingested": 1000}
```

### 7.2 Search API

```
GET /api/v1/search
  Query: q, service, level, start_time, end_time, size, from
  Response: {
    "total": 1234,
    "logs": [...]
  }

POST /api/v1/search
  Body: {
    "query": {"match": {"message": "error"}},
    "filters": {"service": "payment-service"},
    "time_range": {"start": "now-1h", "end": "now"}
  }
  Response: {"hits": [...], "total": 456}

GET /api/v1/trace/{trace_id}
  Response: {"logs": [...], "spans": [...]}
```

### 7.3 Aggregation API

```
POST /api/v1/aggregate
  Body: {
    "agg_type": "terms",
    "field": "service",
    "filters": {"level": "ERROR"},
    "time_range": {"start": "now-24h"}
  }
  Response: {
    "buckets": [
      {"key": "payment-service", "doc_count": 123},
      {"key": "user-service", "doc_count": 45}
    ]
  }

POST /api/v1/timeseries
  Body: {
    "interval": "1h",
    "metric": "count",
    "filters": {"level": "ERROR"},
    "time_range": {"start": "now-24h"}
  }
  Response: {
    "data": [
      {"timestamp": "2026-04-07T00:00:00Z", "value": 45},
      {"timestamp": "2026-04-07T01:00:00Z", "value": 67},
      ...
    ]
  }
```

### 7.4 Alert API

```
POST /api/v1/alerts
  Body: {
    "name": "High Error Rate",
    "condition": {"threshold": 100, "window": "5m"},
    "actions": [{"type": "email", "recipients": [...]}]
  }
  Response: {"alert_id": "a123"}

GET /api/v1/alerts
  Response: {"alerts": [...]}

PUT /api/v1/alerts/{alert_id}/enable
  Response: {"success": true}

DELETE /api/v1/alerts/{alert_id}
  Response: {"success": true}

GET /api/v1/alerts/history
  Query: start_time, end_time
  Response: {"alerts": [...]}
```

### 7.5 Archive API

```
POST /api/v1/archive
  Body: {
    "index_pattern": "logs-2026.03.*",
    "destination": "s3://logs-archive/"
  }
  Response: {"job_id": "j123", "status": "in_progress"}

POST /api/v1/restore
  Body: {
    "date_range": {"start": "2026-03-01", "end": "2026-03-31"},
    "index_name": "logs-restored-march"
  }
  Response: {"job_id": "j456", "estimated_time": "30m"}

GET /api/v1/archive/jobs/{job_id}
  Response: {
    "job_id": "j123",
    "status": "completed",
    "progress": 100
  }
```

## 8. Scalability and Performance

### 8.1 Horizontal Scaling

**Elasticsearch Cluster:**
- Master nodes: 3 (cluster coordination)
- Data nodes (hot): 10 (active indexing and search)
- Data nodes (warm): 5 (older data, less frequent access)
- Coordinating nodes: 3 (query routing)

**Logstash:**
- Deploy multiple Logstash instances
- Kafka consumer groups for parallel processing
- Auto-scaling based on Kafka lag

**Kafka:**
- 30 partitions for logs topic (parallel processing)
- 3 brokers with replication factor 3
- Increase partitions as throughput grows

### 8.2 Ingestion Optimization

**Batch Processing:**
- Batch logs before sending (100-1000 logs per request)
- Compress batches (gzip)
- Use bulk API for Elasticsearch

**Asynchronous Processing:**
- Kafka buffer decouples producers and consumers
- Logstash processes logs asynchronously
- Non-blocking agents

**Sampling:**
For very high-volume services:
```python
# Sample 10% of DEBUG logs, keep all ERROR/WARN
if log.level == "DEBUG" and random() > 0.1:
    drop_log()
```

### 8.3 Query Optimization

**Index Optimization:**
- Time-based indices (prune old indices from search)
- Index aliases for logical grouping
- Field data caching for aggregations

**Query Optimization:**
- Use filters instead of queries (cacheable)
- Limit result size (default 10, max 1000)
- Use scroll API for large result sets
- Pre-aggregate common queries

**Example:**
```json
// Slow (full text search + sort)
GET /logs-*/_search
{
  "query": {"match_all": {}},
  "sort": [{"@timestamp": "desc"}],
  "size": 10000
}

// Fast (filter + limit)
GET /logs-*/_search
{
  "query": {
    "bool": {
      "filter": [
        {"term": {"service": "payment-service"}},
        {"range": {"@timestamp": {"gte": "now-1h"}}}
      ]
    }
  },
  "size": 100
}
```

### 8.4 Storage Optimization

**Compression:**
- Enable "best_compression" codec
- Reduces storage by 50-70%
- Trade-off: Slightly slower indexing

**Forcemerge:**
- Merge segments for warm indices
- Reduces storage and improves query speed

**TTL and Deletion:**
- Automatic deletion via ILM policies
- Delete by query for selective cleanup

**Sharding Strategy:**
- Don't over-shard (each shard has overhead)
- Target shard size: 20-50 GB
- Use rollover for dynamic sharding

### 8.5 High Availability

**Elasticsearch:**
- 3 master nodes (quorum)
- 2 replica shards per primary
- Cross-zone deployment

**Kafka:**
- 3 brokers across availability zones
- Replication factor 3
- Min in-sync replicas: 2

**Logstash:**
- Stateless, easy to replace
- Multiple instances behind load balancer
- Auto-restart on failure

**Disaster Recovery:**
- Automated snapshots to S3 (daily)
- Cross-region replication for critical logs
- Restore testing quarterly

## 9. Technology Stack

**Log Collection:**
- Filebeat / Fluentd / Fluent Bit

**Message Queue:**
- Apache Kafka
- Zookeeper

**Processing:**
- Logstash / Fluentd / Vector

**Storage:**
- Elasticsearch
- PostgreSQL (metadata)

**Visualization:**
- Kibana
- Grafana (for metrics)

**Alerting:**
- ElastAlert / Prometheus Alertmanager

**Archive:**
- AWS S3 / S3 Glacier

**Infrastructure:**
- Kubernetes for orchestration
- Docker for containers

**Monitoring:**
- Prometheus + Grafana (for logging infrastructure)
- Self-monitoring (logs about logs)

## 10. Interview Questions & Answers

### Q1: How do you handle log ingestion spikes without losing data?

**Answer:**
Log ingestion can spike during incidents, deployments, or traffic surges. We use multiple strategies:

**1. Kafka as Buffer:**
- Kafka sits between log agents and processors
- Persistent queue that stores logs on disk
- Even if Logstash/Elasticsearch is down, logs are safe
- TTL configured (7 days) for retention

**2. Back-pressure Handling:**
```python
# Agent-side throttling
if kafka_lag > threshold:
    # Slow down log production
    sleep(backoff_time)
    # Or sample logs (keep errors, sample debug)
```

**3. Auto-scaling:**
- Monitor Kafka consumer lag
- If lag > 100K messages, scale up Logstash instances
- Kubernetes HPA based on Kafka lag metric

**4. Prioritization:**
- Multiple Kafka topics: errors, warnings, info
- Process errors first, then warnings, then info
- Separate consumer groups with different priorities

**5. Overflow Handling:**
```python
if elasticsearch_indexing_fails:
    # Write to backup location (S3)
    write_to_s3(logs)
    # Re-index later from S3
```

**6. Rate Limiting at Source:**
- Application-side rate limiting for log generation
- If same error repeats 1000 times, log once with counter

### Q2: How do you design the log search system for fast queries?

**Answer:**
Fast search is critical for log analysis during incidents.

**Index Design:**

**Time-based Partitioning:**
```
logs-2026.04.07
logs-2026.04.08
logs-2026.04.09
```
- Query only relevant date indices
- Skip 90% of data if searching last 24 hours

**Field Types:**
- Use `keyword` for exact match fields (service, host, level)
- Use `text` for full-text search (message)
- Use `date` for timestamp (range queries)
- Don't index unnecessary fields (`index: false`)

**Indexing Optimization:**
```json
{
  "mappings": {
    "properties": {
      "level": {
        "type": "keyword"  // Fast filters
      },
      "message": {
        "type": "text",
        "fields": {
          "keyword": {  // For exact match and aggregations
            "type": "keyword",
            "ignore_above": 256
          }
        }
      },
      "debug_data": {
        "type": "text",
        "index": false  // Store but don't index (save space)
      }
    }
  }
}
```

**Query Optimization:**

**Use Filters (Cached):**
```json
{
  "query": {
    "bool": {
      "filter": [  // Filters are cached
        {"term": {"level": "ERROR"}},
        {"term": {"service": "payment-service"}},
        {"range": {"@timestamp": {"gte": "now-1h"}}}
      ]
    }
  }
}
```

**Avoid Wildcards at Start:**
```json
// Slow
{"wildcard": {"message": "*error*"}}

// Fast
{"match": {"message": "error"}}
```

**Use Index Aliases:**
```json
POST /_aliases
{
  "actions": [
    {
      "add": {
        "index": "logs-2026.04.*",
        "alias": "logs-recent",
        "filter": {
          "range": {"@timestamp": {"gte": "now-7d"}}
        }
      }
    }
  ]
}

// Query alias instead of multiple indices
GET /logs-recent/_search {...}
```

**Caching:**
- Query result caching (Redis)
- Common queries cached for 5 minutes
- Field data caching for aggregations

**Shard Tuning:**
- Target shard size: 30-50 GB
- More shards = more parallel processing
- But too many shards = overhead

### Q3: How do you correlate logs across microservices for distributed tracing?

**Answer:**
In microservices, a single request spans multiple services. Correlating logs is essential for debugging.

**Trace ID Propagation:**

**1. Generate Trace ID at Entry Point:**
```java
// API Gateway generates trace ID
String traceId = UUID.randomUUID().toString();
MDC.put("trace_id", traceId);

// Add to HTTP headers for downstream services
httpRequest.setHeader("X-Trace-Id", traceId);
```

**2. Propagate Trace ID:**
```java
// Service A receives request
String traceId = request.getHeader("X-Trace-Id");
MDC.put("trace_id", traceId);

// Service A calls Service B
httpClient.setHeader("X-Trace-Id", traceId);
```

**3. Log with Trace ID:**
```java
// All logs automatically include trace_id from MDC
logger.info("Processing payment", kv("amount", 100));

// Output:
{
  "timestamp": "2026-04-07T10:30:00Z",
  "level": "INFO",
  "message": "Processing payment",
  "trace_id": "abc123",  // Automatically included
  "service": "payment-service",
  "amount": 100
}
```

**4. Query by Trace ID:**
```json
GET /logs-*/_search
{
  "query": {
    "term": {"trace_id": "abc123"}
  },
  "sort": [{"@timestamp": "asc"}]
}

// Returns all logs across services for this request
// [
//   {service: "api-gateway", message: "Request received"},
//   {service: "auth-service", message: "User authenticated"},
//   {service: "payment-service", message: "Processing payment"},
//   {service: "payment-service", message: "Payment succeeded"},
//   {service: "notification-service", message: "Email sent"}
// ]
```

**Span ID for Sub-operations:**
```java
// For finer granularity, use span IDs
String spanId = UUID.randomUUID().toString();
MDC.put("span_id", spanId);
MDC.put("parent_span_id", parentSpanId);

// Creates hierarchical trace:
// Trace ID: abc123
//   ├─ Span 1: API Gateway
//   ├─ Span 2: Auth Service
//   └─ Span 3: Payment Service
//       ├─ Span 3.1: Validate card
//       └─ Span 3.2: Charge card
```

**Integration with Distributed Tracing:**
- OpenTelemetry for trace generation
- Jaeger/Zipkin for trace visualization
- Logs enriched with trace context
- Unified view: traces + logs

**Kibana Trace UI:**
```
Trace: abc123 (Total: 450ms)
├─ API Gateway (10ms)
│   Logs: [Request received, Routing to payment service]
├─ Auth Service (50ms)
│   Logs: [Validating token, User authenticated]
└─ Payment Service (390ms)
    Logs: [Processing payment, Calling payment gateway, Payment succeeded]
```

### Q4: How do you handle personally identifiable information (PII) in logs?

**Answer:**
Logging PII violates GDPR and other privacy regulations. Multiple strategies:

**1. Don't Log PII:**
```java
// Bad
logger.info("User login: " + email + ", SSN: " + ssn);

// Good
logger.info("User login", kv("user_id", userId));  // Use ID, not PII
```

**2. PII Masking in Application:**
```java
public class PiiMasker {
    public static String maskEmail(String email) {
        String[] parts = email.split("@");
        return parts[0].substring(0, 2) + "***@" + parts[1];
    }
    
    public static String maskCreditCard(String cc) {
        return "XXXX-XXXX-XXXX-" + cc.substring(cc.length() - 4);
    }
}

logger.info("Payment processed", 
    kv("email", PiiMasker.maskEmail(email)),
    kv("card", PiiMasker.maskCreditCard(cardNumber))
);
```

**3. PII Scrubbing in Logstash:**
```ruby
filter {
  # Mask credit card numbers
  mutate {
    gsub => [
      "message", "\d{4}-\d{4}-\d{4}-\d{4}", "XXXX-XXXX-XXXX-XXXX"
    ]
  }
  
  # Mask email addresses
  mutate {
    gsub => [
      "message", "[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", "***@***"
    ]
  }
  
  # Mask SSN
  mutate {
    gsub => [
      "message", "\d{3}-\d{2}-\d{4}", "XXX-XX-XXXX"
    ]
  }
  
  # Drop fields containing PII
  mutate {
    remove_field => ["ssn", "credit_card", "password"]
  }
}
```

**4. Field-Level Security (Elasticsearch):**
```json
// Restrict access to sensitive fields
{
  "role": "developer",
  "indices": {
    "logs-*": {
      "field_security": {
        "grant": ["*"],
        "except": ["user.email", "user.phone", "credit_card"]
      }
    }
  }
}
```

**5. Separate PII Logs:**
- Store PII in separate, highly secured index
- Encrypt at rest
- Stricter access control
- Shorter retention (30 days vs 90 days)

**6. Tokenization:**
```java
// Instead of logging email
String emailToken = tokenizationService.tokenize(email);
logger.info("User login", kv("email_token", emailToken));

// To retrieve original email (audit trail):
String email = tokenizationService.detokenize(emailToken);
```

**7. Audit Logging:**
- Log who accessed PII
- Alert on unusual PII access patterns

This comprehensive logging framework design covers all aspects of building a production-grade distributed logging system with emphasis on scalability, performance, and compliance.
