# AWS Architecture - YouTube System Design

## Table of Contents
1. [Complete AWS Architecture](#complete-aws-architecture)
2. [AWS Services Breakdown](#aws-services-breakdown)
3. [Deployment Steps](#deployment-steps)
4. [Cost Estimation](#cost-estimation)
5. [Auto-Scaling Configuration](#auto-scaling-configuration)

---

## Complete AWS Architecture

### ASCII Diagram - AWS Infrastructure

```
┌───────────────────────────────────────────────────────────────────────────┐
│                        USERS (Global)                                      │
│  Web Browser       Mobile App      Smart TV                               │
└─────────────────────────┬─────────────────────────────────────────────────┘
                          │
                          │ HTTPS
                          ↓
┌───────────────────────────────────────────────────────────────────────────┐
│                   CloudFront (CDN)                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                       │
│  │ Edge Mumbai │  │ Edge US-East│  │ Edge Europe │                       │
│  │ Cache Videos│  │ Cache Videos│  │ Cache Videos│                       │
│  └─────────────┘  └─────────────┘  └─────────────┘                       │
│                                                                            │
│  Origin: S3 Bucket (youtube-videos-prod)                                  │
└─────────────────────────┬─────────────────────────────────────────────────┘
                          │
                          │ Cache Miss / API Requests
                          ↓
┌───────────────────────────────────────────────────────────────────────────┐
│                  Route 53 (DNS)                                            │
│  youtube.example.com → ALB                                                 │
└─────────────────────────┬─────────────────────────────────────────────────┘
                          │
                          ↓
┌───────────────────────────────────────────────────────────────────────────┐
│           Application Load Balancer (ALB)                                  │
│  - Health Checks                                                           │
│  - SSL Termination (ACM Certificate)                                       │
│  - Path-based Routing:                                                     │
│    /api/v1/videos/* → Video Service Target Group                          │
│    /api/v1/users/* → User Service Target Group                            │
└───────┬────────────────────┬────────────────────┬─────────────────────────┘
        │                    │                    │
        ↓                    ↓                    ↓
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  ECS/EKS CLUSTER │  │  ECS/EKS CLUSTER │  │  ECS/EKS CLUSTER │
│  (Video Service) │  │  (User Service)  │  │ (Comment Service)│
├──────────────────┤  ├──────────────────┤  ├──────────────────┤
│ EC2 Instance 1   │  │ EC2 Instance 1   │  │ EC2 Instance 1   │
│ - Docker         │  │ - Docker         │  │ - Docker         │
│ - Spring Boot    │  │ - Spring Boot    │  │ - Spring Boot    │
│                  │  │                  │  │                  │
│ EC2 Instance 2   │  │ EC2 Instance 2   │  │ EC2 Instance 2   │
│ (Auto-scaled)    │  │ (Auto-scaled)    │  │ (Auto-scaled)    │
└──────────────────┘  └──────────────────┘  └──────────────────┘
        │                    │                    │
        └────────────────────┴────────────────────┘
                          │
                          ↓
┌───────────────────────────────────────────────────────────────────────────┐
│                    ElastiCache (Redis Cluster)                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                       │
│  │ Primary Node│→ │ Replica 1   │  │ Replica 2   │                       │
│  │ Cache:      │  │ Read Replica│  │ Read Replica│                       │
│  │ - Videos    │  └─────────────┘  └─────────────┘                       │
│  │ - Sessions  │                                                           │
│  │ - Views     │  Automatic Failover                                      │
│  └─────────────┘                                                           │
└───────────────────────────────────────────────────────────────────────────┘
                          │
                          ↓
┌───────────────────────────────────────────────────────────────────────────┐
│                   Amazon MSK (Kafka)                                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                       │
│  │  Broker 1   │  │  Broker 2   │  │  Broker 3   │                       │
│  │  AZ-1       │  │  AZ-2       │  │  AZ-3       │                       │
│  └─────────────┘  └─────────────┘  └─────────────┘                       │
│                                                                            │
│  Topics: video-upload, comment-events, view-events                         │
└─────────────────────────┬─────────────────────────────────────────────────┘
                          │
                          │ Consume Events
                          ↓
┌───────────────────────────────────────────────────────────────────────────┐
│              Lambda Functions (Serverless)                                 │
│  ┌──────────────────────┐  ┌──────────────────────┐                      │
│  │ Video Processor      │  │ Thumbnail Generator  │                      │
│  │ - Trigger: S3 Upload │  │ - FFmpeg extraction  │                      │
│  │ - Invoke: Elastic    │  │ - Save to S3         │                      │
│  │   Transcoder         │  └──────────────────────┘                      │
│  └──────────────────────┘                                                 │
│                                                                            │
│  ┌──────────────────────┐  ┌──────────────────────┐                      │
│  │ Notification Service │  │ Analytics Aggregator │                      │
│  │ - SNS push           │  │ - DynamoDB writes    │                      │
│  └──────────────────────┘  └──────────────────────┘                      │
└───────────────────────────────────────────────────────────────────────────┘
                          │
                          ↓
┌───────────────────────────────────────────────────────────────────────────┐
│                      STORAGE LAYER                                         │
│                                                                            │
│  ┌───────────────────────────────────────────────────────┐               │
│  │ S3 (Object Storage)                                    │               │
│  ├───────────────────────────────────────────────────────┤               │
│  │ Bucket: youtube-videos-prod                           │               │
│  │ - videos/                                              │               │
│  │   └── 2024/01/15/video-123-1080p.mp4 (S3 Standard)   │               │
│  │   └── 2023/06/10/video-456-720p.mp4 (S3 IA)          │               │
│  │   └── 2021/03/01/video-789-360p.mp4 (S3 Glacier)     │               │
│  │ - thumbnails/thumb-123.jpg                            │               │
│  │                                                        │               │
│  │ Versioning: Enabled                                    │               │
│  │ Lifecycle Policy: Standard → IA (90d) → Glacier (1yr) │               │
│  │ Replication: Cross-region to S3 us-west-2             │               │
│  └───────────────────────────────────────────────────────┘               │
│                                                                            │
│  ┌───────────────────────────────────────────────────────┐               │
│  │ RDS PostgreSQL (Multi-AZ)                              │               │
│  ├───────────────────────────────────────────────────────┤               │
│  │ Master (AZ-1)        Standby (AZ-2)                   │               │
│  │ - users              - Auto Sync                       │               │
│  │ - videos             - Failover < 2min                │               │
│  │ - comments                                             │               │
│  │ - likes              Read Replicas (2):               │               │
│  │ - subscriptions      - Replica 1 (AZ-3)               │               │
│  │                      - Replica 2 (AZ-1)               │               │
│  │ Instance: db.r6g.4xlarge (128 GB RAM)                │               │
│  └───────────────────────────────────────────────────────┘               │
│                                                                            │
│  ┌───────────────────────────────────────────────────────┐               │
│  │ DocumentDB (MongoDB Compatible)                        │               │
│  ├───────────────────────────────────────────────────────┤               │
│  │ Primary Instance     Replica 1      Replica 2         │               │
│  │ - view_logs          - Read         - Read            │               │
│  │ - watch_history      - Failover     - Failover        │               │
│  │ - analytics_daily                                      │               │
│  │                                                        │               │
│  │ Sharding: By user_id                                   │               │
│  │ Instance: db.r6g.2xlarge                              │               │
│  └───────────────────────────────────────────────────────┘               │
│                                                                            │
│  ┌───────────────────────────────────────────────────────┐               │
│  │ OpenSearch (Elasticsearch)                             │               │
│  ├───────────────────────────────────────────────────────┤               │
│  │ Domain: youtube-search                                 │               │
│  │ - 3 Data Nodes (m5.large.search)                      │               │
│  │ - 3 Master Nodes                                       │               │
│  │ - Index: videos (title, description, tags)            │               │
│  │                                                        │               │
│  │ Snapshots: Automated daily to S3                       │               │
│  └───────────────────────────────────────────────────────┘               │
└───────────────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────────────┐
│                  MONITORING & LOGGING                                      │
│                                                                            │
│  CloudWatch          X-Ray              CloudTrail                        │
│  - Metrics           - Tracing          - API Audit                       │
│  - Logs              - Performance      - Compliance                      │
│  - Alarms            - Bottlenecks                                        │
│                                                                            │
│  SNS → PagerDuty (On-call alerts)                                         │
└───────────────────────────────────────────────────────────────────────────┘
```

---

## AWS Services Breakdown

### 1. Compute Services

#### EC2 (Elastic Compute Cloud)
**Use Case**: Run microservices (Video, User, Comment services)

**Instance Types**:
- **t3.medium** (2 vCPU, 4 GB RAM): Development/Staging
- **c6i.2xlarge** (8 vCPU, 16 GB RAM): Production API servers
- **c6i.4xlarge** (16 vCPU, 32 GB RAM): Video processing workers

**Auto Scaling Group**:
```yaml
MinSize: 2
MaxSize: 20
DesiredCapacity: 4
ScaleUp: CPU > 70% for 5 min → Add 2 instances
ScaleDown: CPU < 30% for 10 min → Remove 1 instance
```

---

#### ECS (Elastic Container Service) / EKS (Kubernetes)
**Use Case**: Container orchestration for microservices

**Why ECS/EKS?**
- Deploy Docker containers
- Blue-green deployments
- Service mesh (AWS App Mesh)

**Example ECS Task Definition**:
```json
{
  "family": "video-service",
  "taskRoleArn": "arn:aws:iam::123456789012:role/ecsTaskRole",
  "containerDefinitions": [
    {
      "name": "video-service",
      "image": "123456789012.dkr.ecr.us-east-1.amazonaws.com/video-service:latest",
      "memory": 2048,
      "cpu": 1024,
      "essential": true,
      "portMappings": [
        {
          "containerPort": 8081,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {"name": "SPRING_PROFILES_ACTIVE", "value": "prod"},
        {"name": "DB_HOST", "value": "youtube-db.us-east-1.rds.amazonaws.com"}
      ]
    }
  ]
}
```

---

#### Lambda (Serverless)
**Use Case**: Event-driven functions (thumbnail generation, notifications)

**Example Lambda Functions**:

1. **Thumbnail Generator**
```python
# lambda_function.py
import boto3
import subprocess

s3 = boto3.client('s3')

def lambda_handler(event, context):
    bucket = event['Records'][0]['s3']['bucket']['name']
    video_key = event['Records'][0]['s3']['object']['key']
    
    # Download video
    s3.download_file(bucket, video_key, '/tmp/video.mp4')
    
    # Extract thumbnail using FFmpeg
    subprocess.run([
        'ffmpeg', '-i', '/tmp/video.mp4', 
        '-ss', '00:00:05', '-vframes', '1', 
        '/tmp/thumbnail.jpg'
    ])
    
    # Upload thumbnail
    thumb_key = video_key.replace('.mp4', '-thumb.jpg')
    s3.upload_file('/tmp/thumbnail.jpg', bucket, thumb_key)
    
    return {'statusCode': 200, 'body': thumb_key}
```

2. **View Counter Aggregator**
```javascript
// Triggered every 5 minutes by CloudWatch Events
const AWS = require('aws-sdk');
const redis = require('redis');

exports.handler = async (event) => {
  const redisClient = redis.createClient({host: process.env.REDIS_HOST});
  
  // Get all view counts from Redis
  const keys = await redisClient.keys('views:*');
  const pipeline = redisClient.pipeline();
  
  keys.forEach(key => {
    const videoId = key.split(':')[1];
    const count = await redisClient.get(key);
    
    // Update PostgreSQL
    await updateDatabase(videoId, count);
    
    // Delete from Redis
    await redisClient.del(key);
  });
  
  return {statusCode: 200};
};
```

---

### 2. Storage Services

#### S3 (Simple Storage Service)
**Use Case**: Store videos, thumbnails

**Bucket Configuration**:
```bash
aws s3api create-bucket --bucket youtube-videos-prod --region us-east-1

# Enable versioning
aws s3api put-bucket-versioning --bucket youtube-videos-prod \
  --versioning-configuration Status=Enabled

# Lifecycle policy (auto-transition to cheaper storage)
aws s3api put-bucket-lifecycle-configuration --bucket youtube-videos-prod \
  --lifecycle-configuration file://lifecycle.json
```

**lifecycle.json**:
```json
{
  "Rules": [
    {
      "Id": "ArchiveOldVideos",
      "Status": "Enabled",
      "Transitions": [
        {
          "Days": 90,
          "StorageClass": "STANDARD_IA"
        },
        {
          "Days": 365,
          "StorageClass": "GLACIER"
        }
      ]
    }
  ]
}
```

**Cost Savings**:
- S3 Standard: $0.023/GB/month
- S3 IA: $0.0125/GB/month (45% cheaper)
- S3 Glacier: $0.004/GB/month (83% cheaper)

For 1 PB storage:
- All Standard: $23,000/month
- With Lifecycle: $10,000/month (60% older videos in Glacier)

---

#### EBS (Elastic Block Store)
**Use Case**: Database storage (RDS), container persistent volumes

**Volume Types**:
- **gp3**: General purpose SSD (3,000 IOPS)
- **io2**: Provisioned IOPS (64,000 IOPS) for databases

---

### 3. Database Services

#### RDS PostgreSQL (Multi-AZ)
**Use Case**: Structured data (users, videos, comments)

**Configuration**:
```bash
aws rds create-db-instance \
  --db-instance-identifier youtube-db \
  --db-instance-class db.r6g.4xlarge \
  --engine postgres \
  --engine-version 15.3 \
  --master-username admin \
  --master-user-password <secret> \
  --allocated-storage 1000 \
  --storage-type gp3 \
  --multi-az \
  --backup-retention-period 7 \
  --preferred-backup-window "03:00-04:00" \
  --vpc-security-group-ids sg-12345678
```

**Read Replicas** (for read scalability):
```bash
aws rds create-db-instance-read-replica \
  --db-instance-identifier youtube-db-replica-1 \
  --source-db-instance-identifier youtube-db
```

---

#### DocumentDB (MongoDB-compatible)
**Use Case**: Logs, analytics

**Configuration**:
```bash
aws docdb create-db-cluster \
  --db-cluster-identifier youtube-logs-cluster \
  --engine docdb \
  --master-username admin \
  --master-user-password <secret> \
  --vpc-security-group-ids sg-12345678
```

---

#### ElastiCache Redis
**Use Case**: Caching (video metadata, sessions, view counts)

**Configuration**:
```bash
aws elasticache create-replication-group \
  --replication-group-id youtube-cache \
  --replication-group-description "YouTube Redis Cache" \
  --engine redis \
  --cache-node-type cache.r6g.large \
  --num-cache-clusters 3 \
  --automatic-failover-enabled \
  --at-rest-encryption-enabled \
  --transit-encryption-enabled
```

---

### 4. Networking Services

#### CloudFront (CDN)
**Use Case**: Deliver videos globally with low latency

**Configuration**:
```bash
aws cloudfront create-distribution --origin-domain-name youtube-videos-prod.s3.amazonaws.com \
  --default-cache-behavior file://cache-behavior.json
```

**cache-behavior.json**:
```json
{
  "TargetOriginId": "S3-youtube-videos-prod",
  "ViewerProtocolPolicy": "redirect-to-https",
  "AllowedMethods": ["GET", "HEAD"],
  "Compress": true,
  "DefaultTTL": 86400,
  "MaxTTL": 31536000,
  "MinTTL": 0
}
```

**Benefits**:
- 200+ edge locations worldwide
- 50ms latency (vs 500ms direct S3)
- DDoS protection (AWS Shield)

---

#### ALB (Application Load Balancer)
**Use Case**: Distribute traffic to EC2 instances

**Configuration**:
```bash
aws elbv2 create-load-balancer \
  --name youtube-alb \
  --subnets subnet-12345 subnet-67890 \
  --security-groups sg-12345678 \
  --scheme internet-facing \
  --type application
```

**Path-Based Routing**:
```bash
# /api/v1/videos/* → Video Service
aws elbv2 create-rule \
  --listener-arn arn:aws:elasticloadbalancing:... \
  --conditions Field=path-pattern,Values=/api/v1/videos/* \
  --actions Type=forward,TargetGroupArn=arn:aws:elasticloadbalancing:.../video-service-tg
```

---

### 5. Message Queue

#### MSK (Managed Streaming for Kafka)
**Use Case**: Event-driven architecture (video processing, notifications)

**Configuration**:
```bash
aws kafka create-cluster \
  --cluster-name youtube-kafka \
  --broker-node-group-info file://broker-config.json \
  --kafka-version 3.5.1 \
  --number-of-broker-nodes 3
```

---

### 6. Video Processing

#### Elastic Transcoder / MediaConvert
**Use Case**: Convert videos to multiple resolutions

**Example MediaConvert Job**:
```json
{
  "Queue": "arn:aws:mediaconvert:us-east-1:123456789012:queues/Default",
  "Role": "arn:aws:iam::123456789012:role/MediaConvertRole",
  "Settings": {
    "Inputs": [
      {
        "FileInput": "s3://youtube-videos-prod/videos/video-123-original.mp4"
      }
    ],
    "OutputGroups": [
      {
        "OutputGroupSettings": {
          "Type": "FILE_GROUP_SETTINGS",
          "FileGroupSettings": {
            "Destination": "s3://youtube-videos-prod/videos/"
          }
        },
        "Outputs": [
          {
            "VideoDescription": {"Width": 1920, "Height": 1080},
            "NameModifier": "-1080p"
          },
          {
            "VideoDescription": {"Width": 1280, "Height": 720},
            "NameModifier": "-720p"
          },
          {
            "VideoDescription": {"Width": 640, "Height": 360},
            "NameModifier": "-360p"
          }
        ]
      }
    ]
  }
}
```

**Cost**: $0.015/minute transcoded

---

## Cost Estimation (Monthly)

### Scenario: 100M DAU, 1B video views/day

| Service | Configuration | Cost |
|---------|--------------|------|
| **EC2 (API Servers)** | 20x c6i.2xlarge (on-demand) | $6,000 |
| **EC2 (Video Workers)** | 50x c6i.4xlarge (spot 70% discount) | $5,000 |
| **RDS PostgreSQL** | db.r6g.4xlarge Multi-AZ + 2 replicas | $3,500 |
| **DocumentDB** | db.r6g.2xlarge x3 | $2,000 |
| **ElastiCache Redis** | cache.r6g.large x3 | $500 |
| **S3 Storage** | 1 PB (with lifecycle) | $10,000 |
| **CloudFront** | 10 PB data transfer | $80,000 |
| **MSK Kafka** | 3 brokers (kafka.m5.large) | $500 |
| **MediaConvert** | 10M min transcoding | $150,000 |
| **Lambda** | 10M invocations | $200 |
| **Data Transfer** | Out to internet (5 PB) | $25,000 |
| **CloudWatch** | Logs, metrics | $500 |
| **Total** | | **$283,200/month** |

**Optimizations**:
- Use Spot Instances for video workers: Save $10,000/month
- Reserved Instances for EC2/RDS (1-year): Save $3,000/month
- Compress videos better: Reduce CloudFront bandwidth
- **Optimized Total**: ~$250,000/month

---

## Auto-Scaling Configuration

### EC2 Auto Scaling

```bash
aws autoscaling create-auto-scaling-group \
  --auto-scaling-group-name video-service-asg \
  --launch-configuration-name video-service-lc \
  --min-size 2 \
  --max-size 20 \
  --desired-capacity 4 \
  --target-group-arns arn:aws:elasticloadbalancing:.../video-service-tg \
  --health-check-type ELB \
  --health-check-grace-period 300 \
  --vpc-zone-identifier "subnet-12345,subnet-67890"
```

**Scaling Policies**:
```bash
# Scale up when CPU > 70%
aws autoscaling put-scaling-policy \
  --auto-scaling-group-name video-service-asg \
  --policy-name scale-up \
  --scaling-adjustment 2 \
  --adjustment-type ChangeInCapacity \
  --cooldown 300

# Scale down when CPU < 30%
aws autoscaling put-scaling-policy \
  --auto-scaling-group-name video-service-asg \
  --policy-name scale-down \
  --scaling-adjustment -1 \
  --adjustment-type ChangeInCapacity \
  --cooldown 600
```

---

## Next Steps
- [Complete System Flow](../Flows/Video_Streaming_Flow.md)
- [Interview Guide](../INTERVIEW_GUIDE.md)
