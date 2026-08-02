# LinkedIn - High Level Design

## 1. Overview

LinkedIn is a professional social networking platform that connects professionals, enables job searching, facilitates business networking, and provides a platform for content sharing and professional development. The platform serves users, companies, recruiters, and advertisers.

**Key Features:**
- Professional profile creation and management
- Connection management and networking
- News feed with professional content
- Job posting and application system
- Messaging and communication
- Company pages and follower system
- Content creation and sharing (posts, articles, videos)
- Skill endorsements and recommendations
- Premium subscriptions
- Advertisement platform

## 2. Requirements

### 2.1 Functional Requirements

**Core Features:**

1. **User Profile Management**
   - Create and edit professional profiles
   - Work experience, education, skills
   - Profile photo and banner
   - Headline and summary
   - Custom URL
   - Profile views tracking

2. **Connection System**
   - Send/accept/reject connection requests
   - 1st, 2nd, 3rd degree connections
   - Follow without connecting
   - Connection recommendations
   - Import contacts

3. **News Feed**
   - Personalized feed algorithm
   - Posts (text, images, videos, documents)
   - Engagement (like, comment, share, repost)
   - Sponsored content
   - Feed filtering and customization

4. **Job System**
   - Job posting by companies
   - Job search with filters
   - Job applications
   - Application tracking
   - Job recommendations
   - Easy Apply feature

5. **Messaging**
   - One-on-one messaging
   - Group messaging
   - Message search
   - Attachments
   - Read receipts
   - Typing indicators

6. **Company Pages**
   - Company profiles
   - Follower system
   - Company updates
   - Employee listings
   - Job postings

7. **Content Platform**
   - Publishing articles
   - Video uploads
   - Polls and surveys
   - Document sharing (SlideShare integration)
   - Hashtag system

8. **Professional Features**
   - Skill endorsements
   - Recommendations
   - Certifications
   - Projects showcase
   - Volunteer experience

9. **Premium Features**
   - InMail credits
   - Who viewed your profile
   - Advanced search filters
   - Learning courses
   - Premium badges

10. **Search**
    - People search
    - Job search
    - Company search
    - Content search
    - Advanced filters

### 2.2 Non-Functional Requirements

1. **Availability**: 99.99% uptime
2. **Scalability**: Support 900M+ users, billions of connections
3. **Performance**:
   - Feed load < 2s
   - Search results < 1s
   - Message delivery < 500ms
4. **Consistency**: Eventual consistency for feed, strong for messaging
5. **Security**: Data privacy, GDPR compliance
6. **Reliability**: No data loss for messages and connections
7. **Low Latency**: Global CDN for fast content delivery

### 2.3 Extended Requirements

- Mobile apps (iOS, Android)
- Real-time notifications
- Analytics dashboard for companies
- AI-powered recommendations
- Video streaming
- Live events (LinkedIn Live)
- Newsletter platform
- Creator mode
- Open to work badge

## 3. Capacity Estimation and Constraints

### 3.1 Traffic Estimates

**Assumptions:**
- 900 million total users
- 300 million monthly active users (MAU)
- 100 million daily active users (DAU)
- Each user creates 2 posts per month
- Average 20 feed views per session
- Average 2 sessions per day

**Calculations:**
- Daily posts: 300M * 2 / 30 = 20 million posts/day
- Posts per second (average): 20M / 86400 = 231 posts/sec
- Posts per second (peak): 231 * 5 = 1,155 posts/sec
- Feed views: 100M * 2 * 20 = 4 billion views/day
- Feed requests per second: 4B / 86400 = 46,296 QPS
- Read:Write ratio: ~200:1

### 3.2 Storage Estimates

**User Data:**
- User profiles: 900M * 10 KB = 9 TB
- Profile photos: 900M * 200 KB = 180 TB

**Connection Data:**
- Average connections per user: 500
- Total connections: 900M * 500 / 2 = 225 billion connections
- Connection record: 16 bytes (user1_id + user2_id)
- Total: 225B * 16 bytes = 3.6 TB

**Posts and Content:**
- Post metadata: 20 KB per post
- Daily posts: 20M * 20 KB = 400 GB/day
- Annual: 400 GB * 365 = 146 TB/year
- 5-year retention: 730 TB

**Media Storage:**
- Images: 50% of posts, 500 KB avg = 10M * 500 KB = 5 TB/day
- Videos: 10% of posts, 50 MB avg = 2M * 50 MB = 100 TB/day
- Total media (5 years): ~190 PB

**Total Storage:** ~200 PB with replication

### 3.3 Bandwidth Estimates

**Incoming:**
- Posts: 1,155/sec * 20 KB = 23 MB/s
- Media uploads: 100 MB/s (compressed)
- Total: ~150 MB/s

**Outgoing:**
- Feed requests: 46,296 QPS * 100 KB = 4.6 GB/s
- Media downloads: 2 GB/s
- Total: ~7 GB/s

## 4. System Architecture

### 4.1 High-Level Architecture

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Web App    │    │  Mobile Apps │    │  API Clients │
│              │    │  (iOS/Android)    │              │
└──────┬───────┘    └──────┬───────┘    └──────┬───────┘
       │                   │                    │
       └───────────────────┼────────────────────┘
                           │
                  ┌────────▼─────────┐
                  │   API Gateway    │
                  │  (Auth, Rate     │
                  │   Limiting)      │
                  └────────┬─────────┘
                           │
       ┌───────────────────┼───────────────────────┐
       │                   │                       │
┌──────▼──────┐    ┌──────▼──────┐        ┌──────▼──────┐
│   Profile   │    │   Feed      │        │  Connection │
│   Service   │    │   Service   │        │   Service   │
└──────┬──────┘    └──────┬──────┘        └──────┬──────┘
       │                   │                       │
┌──────▼──────┐    ┌──────▼──────┐        ┌──────▼──────┐
│   Job       │    │  Messaging  │        │   Search    │
│   Service   │    │   Service   │        │   Service   │
└──────┬──────┘    └──────┬──────┘        └──────┬──────┘
       │                   │                       │
┌──────▼──────┐    ┌──────▼──────┐        ┌──────▼──────┐
│  Company    │    │Notification │        │Recommendation│
│   Service   │    │   Service   │        │   Service    │
└──────┬──────┘    └──────┬──────┘        └──────┬──────┘
       │                   │                       │
       └───────────────────┼───────────────────────┘
                           │
              ┌────────────▼────────────┐
              │   Message Queue (Kafka)      │
              └────────────┬────────────┘
                           │
       ┌───────────────────┼───────────────────────┐
       │                   │                       │
┌──────▼──────┐    ┌──────▼──────┐        ┌──────▼──────┐
│ PostgreSQL  │    │   Cassandra │        │    Redis    │
│ (Profiles)  │    │   (Posts)   │        │   (Cache)   │
└─────────────┘    └─────────────┘        └─────────────┘
       │                   │                       │
┌──────▼──────┐    ┌──────▼──────┐        ┌──────▼──────┐
│   Neo4j     │    │Elasticsearch│        │     S3      │
│(Connections)│    │  (Search)   │        │   (Media)   │
└─────────────┘    └─────────────┘        └─────────────┘
```

### 4.2 Data Flow

**Feed Generation Flow:**
```
User opens feed
  → Feed Service checks cache
  → If miss, Fan-out Service aggregates
  → Rank posts by ML model
  → Return personalized feed
  → Cache for next request
```

## 5. Core Components

### 5.1 Profile Service

**Responsibilities:**
- User profile CRUD operations
- Work experience and education management
- Skills management
- Privacy settings
- Profile completeness scoring
- Profile view tracking

**Profile Schema:**
```sql
users
- user_id (PK)
- email (unique)
- password_hash
- first_name
- last_name
- headline
- summary
- profile_photo_url
- banner_image_url
- location
- industry
- current_position
- created_at
- updated_at
- profile_views_count
- connection_count

work_experiences
- experience_id (PK)
- user_id (FK)
- company_id (FK)
- title
- employment_type (full-time, part-time, contract)
- start_date
- end_date
- is_current
- description
- location

educations
- education_id (PK)
- user_id (FK)
- school
- degree
- field_of_study
- start_year
- end_year
- grade
- activities

skills
- skill_id (PK)
- user_id (FK)
- skill_name
- endorsement_count
- is_top_skill

certifications
- certification_id (PK)
- user_id (FK)
- name
- issuing_organization
- issue_date
- expiration_date
- credential_id
- credential_url
```

**Profile Completeness:**
```python
def calculate_profile_strength(user_id):
    score = 0
    weights = {
        "profile_photo": 10,
        "headline": 10,
        "summary": 15,
        "work_experience": 20,
        "education": 15,
        "skills": 15,
        "connections": 15
    }
    
    user = get_user(user_id)
    if user.profile_photo_url:
        score += weights["profile_photo"]
    if user.headline:
        score += weights["headline"]
    if user.summary:
        score += weights["summary"]
    
    experiences = get_work_experiences(user_id)
    if len(experiences) >= 1:
        score += weights["work_experience"]
    
    educations = get_educations(user_id)
    if len(educations) >= 1:
        score += weights["education"]
    
    skills = get_skills(user_id)
    if len(skills) >= 5:
        score += weights["skills"]
    
    connections = get_connection_count(user_id)
    if connections >= 50:
        score += weights["connections"]
    
    return score  # 0-100
```

**Technology:**
- Service: Java/Spring Boot
- Database: PostgreSQL (relational data)
- Cache: Redis for frequently viewed profiles
- Search: Elasticsearch for profile search

### 5.2 Connection Service

**Responsibilities:**
- Connection request management
- Connection degree calculation (1st, 2nd, 3rd)
- Follow system
- Connection recommendations
- Mutual connections

**Graph Database (Neo4j):**
```cypher
// User node
(:User {user_id: UUID, name: String})

// Connection relationship
(:User)-[:CONNECTED {since: DateTime}]->(:User)

// Follow relationship
(:User)-[:FOLLOWS {since: DateTime}]->(:User)

// Company relationship
(:User)-[:WORKS_AT {title: String, since: DateTime}]->(:Company)

// School relationship
(:User)-[:STUDIED_AT {degree: String, field: String}]->(:School)
```

**Connection Degrees:**
```cypher
// 1st degree connections
MATCH (me:User {user_id: $my_id})-[:CONNECTED]-(friend:User)
RETURN friend

// 2nd degree connections
MATCH (me:User {user_id: $my_id})-[:CONNECTED]-()-[:CONNECTED]-(friend:User)
WHERE NOT (me)-[:CONNECTED]-(friend) AND me <> friend
RETURN DISTINCT friend

// 3rd degree connections
MATCH (me:User {user_id: $my_id})-[:CONNECTED*3]-(friend:User)
WHERE NOT (me)-[:CONNECTED*1..2]-(friend) AND me <> friend
RETURN DISTINCT friend
```

**Connection Recommendations:**
```cypher
// People You May Know (PYMK) algorithm
MATCH (me:User {user_id: $my_id})-[:CONNECTED]-(friend)-[:CONNECTED]-(suggestion:User)
WHERE NOT (me)-[:CONNECTED]-(suggestion) 
  AND me <> suggestion
WITH suggestion, COUNT(DISTINCT friend) as mutual_friends
ORDER BY mutual_friends DESC
LIMIT 20

MATCH (suggestion)-[:WORKS_AT]->(company)<-[:WORKS_AT]-(me)
RETURN suggestion, mutual_friends, company.name as common_company
```

**Connection Request Flow:**
```python
def send_connection_request(from_user_id, to_user_id, message=None):
    # Check if already connected
    if are_connected(from_user_id, to_user_id):
        return {"error": "Already connected"}
    
    # Check if pending request exists
    existing = db.connection_requests.find_one({
        "from_user_id": from_user_id,
        "to_user_id": to_user_id,
        "status": "pending"
    })
    if existing:
        return {"error": "Request already sent"}
    
    # Create connection request
    request = {
        "request_id": uuid4(),
        "from_user_id": from_user_id,
        "to_user_id": to_user_id,
        "message": message,
        "status": "pending",
        "created_at": now()
    }
    db.connection_requests.insert_one(request)
    
    # Send notification
    send_notification(to_user_id, "connection_request", {
        "from_user": get_user(from_user_id),
        "message": message
    })
    
    return {"success": True, "request_id": request.request_id}

def accept_connection_request(request_id, user_id):
    # Verify request is for this user
    request = db.connection_requests.find_one({
        "request_id": request_id,
        "to_user_id": user_id,
        "status": "pending"
    })
    
    if not request:
        return {"error": "Invalid request"}
    
    # Update request status
    db.connection_requests.update_one(
        {"request_id": request_id},
        {"$set": {"status": "accepted", "accepted_at": now()}}
    )
    
    # Create connection in graph database
    neo4j.run("""
        MATCH (u1:User {user_id: $user1}), (u2:User {user_id: $user2})
        CREATE (u1)-[:CONNECTED {since: datetime()}]->(u2)
        CREATE (u2)-[:CONNECTED {since: datetime()}]->(u1)
    """, user1=request.from_user_id, user2=user_id)
    
    # Update connection counts
    db.users.update_one(
        {"user_id": request.from_user_id},
        {"$inc": {"connection_count": 1}}
    )
    db.users.update_one(
        {"user_id": user_id},
        {"$inc": {"connection_count": 1}}
    )
    
    # Send notification
    send_notification(request.from_user_id, "connection_accepted", {
        "user": get_user(user_id)
    })
    
    # Trigger PYMK update
    update_connection_recommendations(request.from_user_id)
    update_connection_recommendations(user_id)
    
    return {"success": True}
```

**Technology:**
- Service: Java/Spring Boot
- Graph DB: Neo4j (connection graph)
- Relational DB: PostgreSQL (requests)
- Cache: Redis

### 5.3 Feed Service

**Responsibilities:**
- Feed generation and ranking
- Post creation and management
- Engagement tracking (likes, comments, shares)
- Feed personalization
- Sponsored content integration

**Feed Architecture (Fan-out on Write):**

**Hybrid Approach:**
- **Fan-out for regular users**: Pre-compute feeds
- **Pull for celebrities**: Compute on-demand (too many followers)

**Post Creation Flow:**
```python
def create_post(user_id, content, media_urls=None, visibility="connections"):
    # Create post
    post = {
        "post_id": uuid4(),
        "author_id": user_id,
        "content": content,
        "media_urls": media_urls or [],
        "visibility": visibility,
        "created_at": now(),
        "engagement": {
            "likes_count": 0,
            "comments_count": 0,
            "shares_count": 0
        }
    }
    
    # Store in Cassandra (time-series)
    cassandra.execute("""
        INSERT INTO posts (post_id, author_id, content, media_urls, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, post.values())
    
    # Index in Elasticsearch for search
    elasticsearch.index(index="posts", id=post.post_id, body=post)
    
    # Publish to Kafka for fan-out
    kafka.produce("post_created", {
        "post_id": post.post_id,
        "author_id": user_id,
        "created_at": post.created_at
    })
    
    return post
```

**Fan-out Service (Background):**
```python
def fanout_post(post_id, author_id):
    # Get author's followers/connections
    connections = get_connections(author_id, limit=5000)
    
    if len(connections) > 5000:
        # Celebrity: Don't fan-out, users will pull
        redis.sadd(f"celebrity:{author_id}", post_id)
        return
    
    # Fan-out to each connection's feed
    for connection_id in connections:
        # Add to user's feed timeline (sorted set by timestamp)
        redis.zadd(
            f"feed:{connection_id}",
            {post_id: post.created_at.timestamp()}
        )
        
        # Keep only recent 1000 posts in feed
        redis.zremrangebyrank(f"feed:{connection_id}", 0, -1001)
```

**Feed Retrieval:**
```python
def get_user_feed(user_id, page=0, page_size=20):
    # Check cache
    cache_key = f"feed:{user_id}:page:{page}"
    cached = redis.get(cache_key)
    if cached:
        return json.loads(cached)
    
    # Get post IDs from sorted set
    start = page * page_size
    end = start + page_size - 1
    post_ids = redis.zrevrange(f"feed:{user_id}", start, end)
    
    # Pull from celebrities user follows
    celebrities = get_followed_celebrities(user_id)
    for celebrity_id in celebrities:
        celebrity_posts = redis.smembers(f"celebrity:{celebrity_id}")
        post_ids.extend(celebrity_posts[:10])  # Top 10 recent posts
    
    # Fetch post details from Cassandra
    posts = []
    for post_id in post_ids:
        post = cassandra.execute(
            "SELECT * FROM posts WHERE post_id = ?", 
            [post_id]
        ).one()
        posts.append(post)
    
    # Rank posts by ML model
    ranked_posts = rank_posts(user_id, posts)
    
    # Add engagement data
    for post in ranked_posts:
        post["engagement"] = get_engagement_stats(post.post_id)
        post["user_liked"] = has_user_liked(user_id, post.post_id)
    
    # Cache for 5 minutes
    redis.setex(cache_key, 300, json.dumps(ranked_posts))
    
    return ranked_posts
```

**Ranking Algorithm:**
```python
def rank_posts(user_id, posts):
    """ML-based post ranking"""
    
    user_profile = get_user_profile(user_id)
    user_history = get_engagement_history(user_id)
    
    scored_posts = []
    for post in posts:
        score = 0
        
        # Recency (decay function)
        age_hours = (now() - post.created_at).total_seconds() / 3600
        recency_score = 1 / (1 + age_hours/24)  # Decay over days
        score += recency_score * 0.3
        
        # Connection strength
        connection_strength = get_connection_strength(user_id, post.author_id)
        score += connection_strength * 0.25
        
        # Engagement velocity
        engagement_rate = post.engagement.likes_count / max(age_hours, 1)
        score += min(engagement_rate / 10, 1) * 0.2
        
        # Content relevance
        relevance = calculate_content_relevance(user_profile, post)
        score += relevance * 0.15
        
        # Interaction history with author
        author_interaction = get_author_interaction_score(user_id, post.author_id)
        score += author_interaction * 0.1
        
        scored_posts.append((post, score))
    
    # Sort by score descending
    ranked = sorted(scored_posts, key=lambda x: x[1], reverse=True)
    
    return [post for post, score in ranked]
```

**Engagement Handling:**
```python
def like_post(user_id, post_id):
    # Check if already liked
    if redis.sismember(f"post:{post_id}:likes", user_id):
        return {"error": "Already liked"}
    
    # Add to likes set
    redis.sadd(f"post:{post_id}:likes", user_id)
    
    # Increment counter
    redis.incr(f"post:{post_id}:likes:count")
    
    # Update in Cassandra
    cassandra.execute("""
        UPDATE posts 
        SET engagement.likes_count = engagement.likes_count + 1
        WHERE post_id = ?
    """, [post_id])
    
    # Send notification to post author
    post = get_post(post_id)
    send_notification(post.author_id, "post_liked", {
        "user": get_user(user_id),
        "post_id": post_id
    })
    
    # Publish event for analytics
    kafka.produce("engagement", {
        "type": "like",
        "user_id": user_id,
        "post_id": post_id,
        "timestamp": now()
    })
    
    return {"success": True}
```

**Technology:**
- Service: Java/Spring Boot
- Database: Cassandra (time-series posts)
- Cache: Redis (feeds, engagement counts)
- Queue: Kafka (fan-out, analytics)
- ML: Python/TensorFlow (ranking model)

### 5.4 Job Service

**Responsibilities:**
- Job posting management
- Job search with filters
- Job application tracking
- Job recommendations
- Easy Apply feature
- Applicant tracking system (ATS) integration

**Job Schema:**
```sql
jobs
- job_id (PK)
- company_id (FK)
- title
- description
- location
- employment_type (full-time, part-time, contract, internship)
- seniority_level (entry, associate, mid-senior, director, executive)
- industry
- function
- required_skills (JSONB)
- salary_range
- posted_by (user_id)
- posted_at
- expires_at
- application_count
- view_count
- is_active

job_applications
- application_id (PK)
- job_id (FK)
- applicant_id (FK)
- resume_url
- cover_letter
- status (submitted, reviewed, interview, offered, rejected, withdrawn)
- applied_at
- updated_at

saved_jobs
- user_id (FK)
- job_id (FK)
- saved_at
```

**Job Search (Elasticsearch):**
```json
{
  "query": {
    "bool": {
      "must": [
        {
          "multi_match": {
            "query": "software engineer",
            "fields": ["title^3", "description", "required_skills"]
          }
        }
      ],
      "filter": [
        {"terms": {"location": ["San Francisco", "Remote"]}},
        {"terms": {"employment_type": ["full-time"]}},
        {"range": {"posted_at": {"gte": "now-30d"}}},
        {"term": {"is_active": true}}
      ]
    }
  },
  "sort": [
    {"_score": {"order": "desc"}},
    {"posted_at": {"order": "desc"}}
  ]
}
```

**Job Recommendations:**
```python
def recommend_jobs(user_id, limit=20):
    """ML-based job recommendations"""
    
    user = get_user(user_id)
    user_skills = get_user_skills(user_id)
    user_experience = get_work_experiences(user_id)
    
    # Feature extraction
    features = {
        "skills": [skill.skill_name for skill in user_skills],
        "current_title": user_experience[0].title if user_experience else "",
        "industry": user.industry,
        "location": user.location,
        "seniority": calculate_seniority(user_experience)
    }
    
    # Query Elasticsearch with boosting
    query = {
        "query": {
            "bool": {
                "should": [
                    # Boost jobs matching user skills
                    {
                        "terms": {
                            "required_skills": features["skills"],
                            "boost": 2.0
                        }
                    },
                    # Boost jobs in user's industry
                    {
                        "term": {
                            "industry": features["industry"],
                            "boost": 1.5
                        }
                    },
                    # Boost jobs at user's seniority level
                    {
                        "term": {
                            "seniority_level": features["seniority"],
                            "boost": 1.3
                        }
                    },
                    # Boost jobs in user's location
                    {
                        "match": {
                            "location": features["location"],
                            "boost": 1.2
                        }
                    }
                ],
                "minimum_should_match": 1
            }
        },
        "size": limit
    }
    
    results = elasticsearch.search(index="jobs", body=query)
    
    # Post-process with ML model
    recommendations = ml_model.rank(user_id, results["hits"]["hits"])
    
    return recommendations
```

**Easy Apply:**
```python
def easy_apply(user_id, job_id):
    """One-click job application using LinkedIn profile"""
    
    # Check if already applied
    existing = db.job_applications.find_one({
        "applicant_id": user_id,
        "job_id": job_id
    })
    if existing:
        return {"error": "Already applied"}
    
    # Generate resume from profile
    resume_pdf = generate_resume_from_profile(user_id)
    resume_url = upload_to_s3(resume_pdf)
    
    # Create application
    application = {
        "application_id": uuid4(),
        "job_id": job_id,
        "applicant_id": user_id,
        "resume_url": resume_url,
        "status": "submitted",
        "applied_at": now()
    }
    db.job_applications.insert_one(application)
    
    # Update job application count
    db.jobs.update_one(
        {"job_id": job_id},
        {"$inc": {"application_count": 1}}
    )
    
    # Notify recruiter
    job = get_job(job_id)
    send_notification(job.posted_by, "new_application", {
        "applicant": get_user(user_id),
        "job": job
    })
    
    return {"success": True, "application_id": application.application_id}
```

**Technology:**
- Service: Java/Spring Boot
- Database: PostgreSQL
- Search: Elasticsearch
- ML: Python/Scikit-learn (recommendations)
- Storage: S3 (resumes)

### 5.5 Messaging Service

**Responsibilities:**
- One-on-one messaging
- Group conversations
- Message delivery and read receipts
- Real-time updates
- Message search
- File attachments

**Messaging Architecture:**

**Database Schema (Cassandra):**
```sql
conversations
- conversation_id (PK)
- participant_ids (Set<UUID>)
- is_group (boolean)
- created_at
- updated_at
- last_message_at

messages
- conversation_id (Partition Key)
- message_id (Clustering Key, timeuuid)
- sender_id
- content
- attachments (List<Text>)
- sent_at
- delivered_at
- read_by (Map<UUID, timestamp>)
- is_deleted

-- Secondary index for user's conversations
conversation_members
- user_id (Partition Key)
- conversation_id (Clustering Key)
- last_read_at
- unread_count
```

**WebSocket for Real-time:**
```python
# Client connects to WebSocket
websocket.on_connect(user_id):
    # Subscribe to user's conversation updates
    redis_pubsub.subscribe(f"user:{user_id}:messages")
    
    # Send online presence
    redis.sadd("online_users", user_id)
    redis.expire(f"online:{user_id}", 300)  # 5 min TTL

# Send message
def send_message(sender_id, conversation_id, content, attachments=None):
    # Create message
    message = {
        "message_id": timeuuid(),
        "conversation_id": conversation_id,
        "sender_id": sender_id,
        "content": content,
        "attachments": attachments or [],
        "sent_at": now()
    }
    
    # Store in Cassandra
    cassandra.execute("""
        INSERT INTO messages (conversation_id, message_id, sender_id, content, sent_at)
        VALUES (?, ?, ?, ?, ?)
    """, message.values())
    
    # Get conversation participants
    conversation = get_conversation(conversation_id)
    recipients = [uid for uid in conversation.participant_ids if uid != sender_id]
    
    # Publish to recipients via Redis Pub/Sub
    for recipient_id in recipients:
        redis_pubsub.publish(f"user:{recipient_id}:messages", json.dumps(message))
        
        # Increment unread count
        redis.incr(f"unread:{recipient_id}:{conversation_id}")
    
    # Update conversation last_message_at
    cassandra.execute("""
        UPDATE conversations 
        SET last_message_at = ?
        WHERE conversation_id = ?
    """, [now(), conversation_id])
    
    # Send push notification if recipient offline
    for recipient_id in recipients:
        if not is_user_online(recipient_id):
            send_push_notification(recipient_id, "new_message", {
                "sender": get_user(sender_id),
                "preview": content[:50]
            })
    
    return message

# Mark as read
def mark_as_read(user_id, conversation_id, message_id):
    # Update message read_by
    cassandra.execute("""
        UPDATE messages 
        SET read_by = read_by + {?: ?}
        WHERE conversation_id = ? AND message_id = ?
    """, [user_id, now(), conversation_id, message_id])
    
    # Reset unread count
    redis.delete(f"unread:{user_id}:{conversation_id}")
    
    # Send read receipt to sender
    message = get_message(conversation_id, message_id)
    redis_pubsub.publish(f"user:{message.sender_id}:receipts", json.dumps({
        "conversation_id": conversation_id,
        "message_id": message_id,
        "read_by": user_id,
        "read_at": now()
    }))
```

**Message Search (Elasticsearch):**
```python
def search_messages(user_id, query, conversation_id=None):
    # Get user's conversations
    conversations = get_user_conversations(user_id)
    conversation_ids = [c.conversation_id for c in conversations]
    
    # Search in Elasticsearch
    search_query = {
        "query": {
            "bool": {
                "must": [
                    {"match": {"content": query}}
                ],
                "filter": [
                    {"terms": {"conversation_id": conversation_ids}}
                ]
            }
        },
        "highlight": {
            "fields": {"content": {}}
        },
        "sort": [{"sent_at": "desc"}]
    }
    
    if conversation_id:
        search_query["query"]["bool"]["filter"].append(
            {"term": {"conversation_id": conversation_id}}
        )
    
    results = elasticsearch.search(index="messages", body=search_query)
    return results["hits"]["hits"]
```

**Technology:**
- Service: Node.js (WebSocket support)
- Database: Cassandra (message storage)
- Real-time: WebSocket + Redis Pub/Sub
- Search: Elasticsearch
- Storage: S3 (attachments)

### 5.6 Search Service

**Responsibilities:**
- People search with filters
- Job search
- Company search
- Content search
- Autocomplete suggestions
- Advanced filters

**Elasticsearch Indices:**
```json
// People index
{
  "user_id": "u123",
  "name": "John Doe",
  "headline": "Software Engineer at Google",
  "location": "San Francisco, CA",
  "industry": "Technology",
  "current_company": "Google",
  "current_title": "Software Engineer",
  "skills": ["Python", "Java", "Machine Learning"],
  "experience_years": 5,
  "connection_count": 500,
  "profile_completeness": 85
}

// Jobs index
{
  "job_id": "j456",
  "title": "Senior Software Engineer",
  "company": "Google",
  "location": "San Francisco, CA",
  "employment_type": "full-time",
  "seniority_level": "mid-senior",
  "required_skills": ["Python", "Kubernetes", "AWS"],
  "posted_at": "2026-04-01",
  "application_count": 120
}

// Posts index
{
  "post_id": "p789",
  "author_id": "u123",
  "author_name": "John Doe",
  "content": "Excited to share...",
  "hashtags": ["ai", "machinelearning"],
  "created_at": "2026-04-07T10:00:00Z",
  "engagement_score": 125
}
```

**People Search:**
```python
def search_people(query, filters=None, user_id=None):
    search_query = {
        "query": {
            "bool": {
                "must": [
                    {
                        "multi_match": {
                            "query": query,
                            "fields": ["name^3", "headline^2", "current_title", "skills"],
                            "type": "best_fields"
                        }
                    }
                ],
                "filter": []
            }
        },
        "sort": []
    }
    
    # Apply filters
    if filters:
        if filters.get("location"):
            search_query["query"]["bool"]["filter"].append(
                {"match": {"location": filters["location"]}}
            )
        if filters.get("current_company"):
            search_query["query"]["bool"]["filter"].append(
                {"term": {"current_company": filters["current_company"]}}
            )
        if filters.get("industry"):
            search_query["query"]["bool"]["filter"].append(
                {"term": {"industry": filters["industry"]}}
            )
    
    # Personalized ranking
    if user_id:
        user_connections = get_connection_ids(user_id)
        
        # Boost 1st degree connections
        search_query["query"]["bool"]["should"] = [
            {
                "terms": {
                    "user_id": user_connections,
                    "boost": 3.0
                }
            }
        ]
    
    # Sort by relevance and connection count
    search_query["sort"] = [
        {"_score": {"order": "desc"}},
        {"connection_count": {"order": "desc"}}
    ]
    
    results = elasticsearch.search(index="people", body=search_query)
    
    # Enrich with connection degree
    for hit in results["hits"]["hits"]:
        hit["connection_degree"] = get_connection_degree(user_id, hit["_source"]["user_id"])
    
    return results
```

**Technology:**
- Service: Python/Flask
- Search: Elasticsearch
- Cache: Redis

### 5.7 Notification Service

**Responsibilities:**
- Multi-channel notifications (in-app, email, push, SMS)
- Notification preferences management
- Notification aggregation (batching)
- Real-time delivery
- Notification history

**Notification Types:**
- Connection requests
- Post engagement (likes, comments)
- Job applications
- Messages
- Profile views
- Mentions
- Endorsements

**Notification Schema:**
```sql
notifications
- notification_id (PK)
- user_id (FK)
- type (connection_request, post_liked, job_application, message, etc.)
- actor_id (who triggered the notification)
- entity_id (post_id, job_id, etc.)
- content (JSONB)
- is_read
- created_at

notification_preferences
- user_id (PK)
- type (notification type)
- in_app (boolean)
- email (boolean)
- push (boolean)
- sms (boolean)
```

**Notification Aggregation:**
```python
def aggregate_notifications(user_id):
    """Batch similar notifications"""
    
    # Get recent notifications
    recent = db.notifications.find({
        "user_id": user_id,
        "created_at": {"$gte": now() - timedelta(hours=1)},
        "is_aggregated": False
    })
    
    # Group by type and entity
    grouped = {}
    for notif in recent:
        key = (notif.type, notif.entity_id)
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(notif)
    
    # Create aggregated notifications
    aggregated = []
    for (notif_type, entity_id), notifications in grouped.items():
        if len(notifications) > 1:
            actors = [n.actor_id for n in notifications]
            
            aggregated_notif = {
                "notification_id": uuid4(),
                "user_id": user_id,
                "type": notif_type + "_aggregated",
                "actor_ids": actors,
                "entity_id": entity_id,
                "content": f"{len(actors)} people {notif_type.replace('_', ' ')}",
                "is_read": False,
                "created_at": now()
            }
            
            # Mark original notifications as aggregated
            for n in notifications:
                db.notifications.update_one(
                    {"notification_id": n.notification_id},
                    {"$set": {"is_aggregated": True}}
                )
            
            aggregated.append(aggregated_notif)
    
    if aggregated:
        db.notifications.insert_many(aggregated)
```

**Technology:**
- Service: Node.js
- Database: PostgreSQL
- Queue: Kafka
- Push: Firebase Cloud Messaging
- Email: SendGrid

### 5.8 Recommendation Service

**Responsibilities:**
- Connection recommendations (PYMK)
- Job recommendations
- Content recommendations
- Skills to add recommendations
- People to follow recommendations

**ML-Based Recommendations:**

**Connection Recommendations:**
```python
class ConnectionRecommender:
    def recommend_connections(self, user_id, limit=10):
        """Hybrid recommendation approach"""
        
        # Feature 1: Mutual connections
        mutual_recs = self.mutual_connection_recommendations(user_id)
        
        # Feature 2: Common workplace/school
        workplace_recs = self.workplace_recommendations(user_id)
        
        # Feature 3: Similar profiles (collaborative filtering)
        similar_recs = self.collaborative_filtering(user_id)
        
        # Feature 4: People viewed your profile
        profile_viewers = self.profile_viewer_recommendations(user_id)
        
        # Combine and rank
        candidates = {}
        for rec in mutual_recs:
            candidates[rec["user_id"]] = candidates.get(rec["user_id"], 0) + 0.4
        for rec in workplace_recs:
            candidates[rec["user_id"]] = candidates.get(rec["user_id"], 0) + 0.3
        for rec in similar_recs:
            candidates[rec["user_id"]] = candidates.get(rec["user_id"], 0) + 0.2
        for rec in profile_viewers:
            candidates[rec["user_id"]] = candidates.get(rec["user_id"], 0) + 0.1
        
        # Sort by score
        ranked = sorted(candidates.items(), key=lambda x: x[1], reverse=True)
        
        # Fetch user details
        recommendations = []
        for user_id, score in ranked[:limit]:
            user = get_user(user_id)
            recommendations.append({
                "user": user,
                "score": score,
                "reason": self.generate_reason(user_id, candidates)
            })
        
        return recommendations
    
    def mutual_connection_recommendations(self, user_id):
        """People with most mutual connections"""
        result = neo4j.run("""
            MATCH (me:User {user_id: $user_id})-[:CONNECTED]-(friend)-[:CONNECTED]-(suggestion:User)
            WHERE NOT (me)-[:CONNECTED]-(suggestion) 
              AND me <> suggestion
            WITH suggestion, COUNT(DISTINCT friend) as mutual_count
            ORDER BY mutual_count DESC
            LIMIT 20
            RETURN suggestion.user_id as user_id, mutual_count
        """, user_id=user_id)
        
        return list(result)
```

**Technology:**
- Service: Python
- ML: TensorFlow/PyTorch
- Graph: Neo4j
- Feature Store: Redis
- Model Serving: TensorFlow Serving

## 6. Database Design

(Covered in individual service sections above)

## 7. API Design

### 7.1 Profile APIs

```
GET /api/v1/users/{user_id}/profile
  Response: { user profile with experience, education, skills }

PUT /api/v1/users/{user_id}/profile
  Body: { updated fields }
  Response: { success }

POST /api/v1/users/{user_id}/experience
  Body: { title, company, start_date, end_date, description }
  Response: { experience_id }

POST /api/v1/users/{user_id}/skills
  Body: { skill_name }
  Response: { skill_id }

POST /api/v1/users/{from_user_id}/endorse/{to_user_id}/skill/{skill_id}
  Response: { success }
```

### 7.2 Connection APIs

```
POST /api/v1/connections/request
  Body: { to_user_id, message }
  Response: { request_id }

PUT /api/v1/connections/requests/{request_id}/accept
  Response: { success }

PUT /api/v1/connections/requests/{request_id}/reject
  Response: { success }

GET /api/v1/users/{user_id}/connections
  Query: page, limit
  Response: { connections: [...], total }

GET /api/v1/users/{user_id}/recommendations/connections
  Query: limit
  Response: { recommendations: [{user, mutual_count, reason}] }
```

### 7.3 Feed APIs

```
GET /api/v1/feed
  Query: page, limit
  Response: { posts: [...], next_page_token }

POST /api/v1/posts
  Body: { content, media_urls, visibility }
  Response: { post_id }

POST /api/v1/posts/{post_id}/like
  Response: { success, likes_count }

POST /api/v1/posts/{post_id}/comment
  Body: { content }
  Response: { comment_id }

POST /api/v1/posts/{post_id}/share
  Body: { comment }
  Response: { success }
```

### 7.4 Job APIs

```
GET /api/v1/jobs/search
  Query: q, location, employment_type, seniority, page
  Response: { jobs: [...], total }

POST /api/v1/jobs (Company)
  Body: { title, description, location, required_skills, ... }
  Response: { job_id }

POST /api/v1/jobs/{job_id}/apply
  Body: { resume_url, cover_letter }
  Response: { application_id }

GET /api/v1/jobs/recommendations
  Query: limit
  Response: { jobs: [{job, match_score, matched_skills}] }
```

### 7.5 Messaging APIs

```
POST /api/v1/conversations
  Body: { participant_ids, first_message }
  Response: { conversation_id }

GET /api/v1/conversations
  Query: page
  Response: { conversations: [{id, participants, last_message, unread_count}] }

POST /api/v1/conversations/{conversation_id}/messages
  Body: { content, attachments }
  Response: { message_id }

GET /api/v1/conversations/{conversation_id}/messages
  Query: page, limit
  Response: { messages: [...] }

PUT /api/v1/conversations/{conversation_id}/read
  Body: { last_read_message_id }
  Response: { success }
```

## 8. Scalability and Performance

### 8.1 Feed Scalability

**Challenges:**
- 100M DAU generating 4B feed views/day
- Celebrities with millions of followers

**Solutions:**
1. **Hybrid Fan-out**: Fan-out for regular users, pull for celebrities
2. **Feed Caching**: Pre-compute and cache feeds
3. **ML Ranking**: Offline batch ranking + online personalization
4. **CDN**: Cache static content

### 8.2 Database Sharding

**User Data (PostgreSQL):**
- Shard by user_id (consistent hashing)
- 256 logical shards, distributed across physical servers

**Connection Graph (Neo4j):**
- Shard by user_id ranges
- Co-locate 1st degree connections

**Posts (Cassandra):**
- Partition by post_id
- Distribute evenly with consistent hashing

### 8.3 Caching Strategy

**Multi-Level Cache:**
1. **CDN**: Static assets (images, videos, CSS, JS)
2. **Redis**: Hot data (feeds, profiles, connections)
3. **Application Cache**: In-memory LRU cache

**Cache Invalidation:**
- Time-based (TTL)
- Event-driven (on updates)

### 8.4 Search Optimization

**Elasticsearch:**
- 10 shards per index
- 2 replicas for HA
- Separate indices for people, jobs, posts, companies

### 8.5 Real-time System

**WebSocket Gateway:**
- Horizontally scaled WebSocket servers
- Sticky sessions for connection affinity
- Redis Pub/Sub for message broadcasting

### 8.6 Global Distribution

**Multi-Region Deployment:**
- US-East, US-West, EU, Asia-Pacific regions
- Route53 for geo-routing
- Cross-region replication for critical data

## 9. Technology Stack

**Backend:**
- Java/Spring Boot: Core services
- Python: ML, recommendations
- Node.js: Real-time (messaging, notifications)

**Databases:**
- PostgreSQL: User profiles, jobs
- Cassandra: Posts, messages
- Neo4j: Connection graph
- Redis: Cache, real-time

**Search:** Elasticsearch

**Queue:** Apache Kafka

**Storage:** AWS S3

**CDN:** CloudFront

**Infrastructure:** AWS/Kubernetes

**Monitoring:** Prometheus, Grafana, ELK

**ML:** TensorFlow, PyTorch

## 10. Interview Questions & Answers

### Q1: How do you design the news feed system for LinkedIn?

**Answer:**
The feed system is the most complex component with billions of views daily.

**Architecture Choice: Hybrid Fan-out**

**For Regular Users (Fan-out on Write):**
- Pre-compute feeds when post is created
- Store in user's feed timeline (Redis sorted set)
- Fast read (just fetch from cache)

**For Celebrities (Fan-out on Read):**
- Don't pre-compute (too many followers)
- Fetch posts on-demand when user loads feed
- Cache results

**Feed Generation Flow:**
```
1. User creates post
2. Determine author type (regular vs celebrity)
3. If regular:
   - Fanout to all connections (< 5K)
   - Add post_id to each connection's feed timeline
4. If celebrity:
   - Add to celebrity post list
   - Followers pull on demand
```

**Feed Retrieval:**
```
1. User requests feed
2. Fetch post IDs from user's timeline (Redis)
3. Pull recent posts from celebrities user follows
4. Fetch full post objects (Cassandra)
5. Rank posts with ML model
6. Add engagement data
7. Return paginated results
```

**Ranking Algorithm:**
- Recency (30%)
- Connection strength (25%)
- Engagement velocity (20%)
- Content relevance (15%)
- Author interaction history (10%)

**Scalability:**
- Redis Cluster for feed timelines (TB scale)
- Cassandra for post storage (PB scale)
- Kafka for async fan-out processing
- ML model inference in < 100ms

### Q2: How do you handle connection degree calculation efficiently?

**Answer:**
Connection degrees (1st, 2nd, 3rd) are fundamental to LinkedIn's network.

**Graph Database (Neo4j):**
Store relationships as a graph, not relational tables.

**Precomputation:**
Don't calculate degrees in real-time. Pre-compute and cache.

**1st Degree:**
```cypher
MATCH (me:User {user_id: $user_id})-[:CONNECTED]-(friend:User)
RETURN friend
```
- Direct query, very fast
- Cache result in Redis: `connections:1st:{user_id}` → Set of user IDs

**2nd Degree:**
```cypher
MATCH (me:User {user_id: $user_id})-[:CONNECTED]-()-[:CONNECTED]-(friend:User)
WHERE NOT (me)-[:CONNECTED]-(friend) AND me <> friend
RETURN DISTINCT friend
```
- More expensive, cache aggressively
- Pre-compute for active users
- Cache: `connections:2nd:{user_id}` → Set of user IDs

**3rd Degree:**
Too expensive to compute in real-time. Approximations:
- Sample based approach
- Display "3rd+" without exact calculation
- Show specific 3rd connections only in context (profile view)

**Optimization: Connection Count**
Instead of fetching all 2nd degree connections:
```cypher
MATCH (me:User {user_id: $user_id})-[:CONNECTED]-()-[:CONNECTED]-(friend:User)
WHERE NOT (me)-[:CONNECTED]-(friend) AND me <> friend
RETURN COUNT(DISTINCT friend) as count
```

**Mutual Connections:**
```cypher
MATCH (me:User {user_id: $my_id})-[:CONNECTED]-(mutual)-[:CONNECTED]-(other:User {user_id: $other_id})
RETURN COUNT(DISTINCT mutual) as mutual_count
```

**Update Strategy:**
- On new connection: Invalidate 2nd degree cache for both users
- Background job recalculates affected users
- Eventual consistency acceptable

**Sharding:**
- Shard graph by user ID ranges
- Co-locate 1st degree connections on same shard
- Cross-shard queries for 2nd/3rd degrees

### Q3: How do you design the job recommendation system?

**Answer:**
Job recommendations are critical for engagement and revenue.

**Multi-Signal Approach:**

**1. Content-Based Filtering:**
Match job requirements with user profile.

**Features:**
- User skills vs job required skills (Jaccard similarity)
- User title vs job title (NLP similarity)
- User seniority vs job seniority (exact match)
- User location vs job location (geo-distance)

**Scoring:**
```python
def content_score(user, job):
    skill_match = jaccard_similarity(user.skills, job.required_skills)
    title_match = cosine_similarity(embed(user.title), embed(job.title))
    seniority_match = 1.0 if user.seniority == job.seniority else 0.5
    location_match = 1.0 if user.location == job.location or job.location == "Remote" else 0.3
    
    score = (skill_match * 0.4 + 
             title_match * 0.3 + 
             seniority_match * 0.2 + 
             location_match * 0.1)
    
    return score
```

**2. Collaborative Filtering:**
Find similar users and recommend jobs they applied to.

```python
def collaborative_score(user_id, job_id):
    # Find similar users (cosine similarity on embeddings)
    similar_users = get_similar_users(user_id, limit=100)
    
    # Count how many similar users applied to this job
    applications = db.job_applications.count({
        "applicant_id": {"$in": similar_users},
        "job_id": job_id
    })
    
    # Normalize by number of similar users
    score = applications / len(similar_users)
    
    return score
```

**3. Behavioral Signals:**
- Jobs user viewed but didn't apply (interest signal)
- Jobs user saved
- Jobs similar to ones user applied to
- Companies user follows

**4. Network Signals:**
- Jobs posted by connections
- Jobs where connections work
- Jobs with many applicants from user's network

**5. Freshness:**
Recently posted jobs get a boost.

**Ensemble Model:**
```python
def final_recommendation_score(user_id, job_id):
    content = content_score(user, job)
    collaborative = collaborative_score(user_id, job_id)
    behavioral = behavioral_score(user_id, job_id)
    network = network_score(user_id, job_id)
    freshness = freshness_score(job)
    
    # Weighted combination
    final_score = (content * 0.35 + 
                   collaborative * 0.25 + 
                   behavioral * 0.20 + 
                   network * 0.15 + 
                   freshness * 0.05)
    
    return final_score
```

**Offline + Online:**
- **Offline**: Batch process generates candidate set (top 1000 jobs per user)
- **Online**: Real-time ranking when user views job feed
- **A/B Testing**: Continuously test ranking variations

**Cold Start Problem:**
- New users: Use demographic and declared interests
- New jobs: Give initial boost, rely on content-based matching

**Scalability:**
- Elasticsearch for candidate generation
- Redis for feature caching
- Model inference in < 100ms
- Pre-compute embeddings

This comprehensive LinkedIn design covers all critical aspects of a professional social network, from profile management to job recommendations, with emphasis on graph algorithms, feed generation, and ML-powered recommendations.
