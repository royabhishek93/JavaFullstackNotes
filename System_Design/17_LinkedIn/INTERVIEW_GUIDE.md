# LinkedIn — Interview Script
## Design a Professional Social Network (LinkedIn)
### Speak This Word-for-Word to Your Interviewer

> How to use this: Study PAGE 1 to internalize LinkedIn's two hard problems — graph queries and feed fan-out. They are separate systems that share the same connection data. Study the PYMK algorithm in STEP 7 until you can recite it from memory — that's the most unique part of LinkedIn vs. Instagram. All Senior Trap questions are real-world problems LinkedIn engineering has solved at 950M user scale.

# ═══════════════ PAGE 1 — START HERE ═══════════════

## BIG PICTURE (Understand This Before Anything Else)

> **► STUDY this diagram, don't draw it ◄**
> LinkedIn combines two of the hardest system design problems: a social graph at 950M user scale (connections are bidirectional, unlike Instagram follows), and a professional content feed with quality ranking requirements. The unique challenge is PYMK (People You May Know) — computing 2nd-degree connections requires graph traversal that is O(N×M) and must be pre-computed, not real-time. LinkedIn's bidirectional connections also mean every connection creates TWO rows in the connection store, and any query must read from both to maintain consistency.

```
                     ┌───────────────────────────────────────────────────────────┐
                     │                 LINKEDIN — DATA FLOW                       │
                     └───────────────────────────────────────────────────────────┘

  ┌──────────┐  Browse Feed  ┌──────────────┐             ┌────────────────────┐
  │  Browser │──────────────►│  API         │             │     Redis          │
  │  Mobile  │               │  Gateway     │             │  feed:{userId}     │
  │  App     │◄──────────────│  (Auth/Rate  │◄────────────│  (sorted set,      │
  │          │  Feed items   │   Limit)     │             │   pre-computed)    │
  └──────────┘               └──────┬───────┘             │                   │
       │                            │                     │  pymk:{userId}     │
       │  SSE (notif bell)          │  Route              │  (PYMK results)    │
       │  WebSocket (messages)      ▼                     │                   │
       │                   ┌──────────────┐               │  online:{userId}   │
       │                   │  Feed Svc    │  Fan-out       │  presence          │
       │                   │  (write/read)│───────────────►│                   │
       │                   └──────┬───────┘               │  session store     │
       │                          │                       └────────────────────┘
       │                          │
       │                   ┌──────▼───────┐               ┌────────────────────┐
       │                   │  Graph Svc   │  2-table      │    Cassandra        │
       │                   │  (connections│──────────────►│  connections_by_    │
       │                   │   + PYMK)    │               │  user              │
       │                   └──────┬───────┘               │  connections_by_   │
       │                          │                       │  friend            │
       │                   ┌──────▼───────┐               │  posts             │
       │                   │  Post Svc    │               │  messages          │
       │                   │  (create/    │               │  endorsements      │
       │                   │   read)      │               │  profile_views     │
       │                   └──────┬───────┘               └────────────────────┘
       │                          │
       │                   ┌──────▼───────┐               ┌────────────────────┐
       │                   │  Job Svc     │               │     MySQL          │
       │                   │  (search/    │               │  users             │
       │                   │   recommend) │               │  companies         │
       │                   └──────┬───────┘               │  jobs              │
       │                          │                       │  skills            │
       │                   ┌──────▼───────┐               └────────────────────┘
       │                   │    Kafka     │
       │                   │  (async fan- │               ┌────────────────────┐
       │                   │   out, notif │               │  Elasticsearch     │
       │                   │   events)    │               │  jobs index        │
       └───────────────────└──────────────┘               │  people search     │
                                                          │  company search    │
                                                          └────────────────────┘
```

---

## RAPID ANSWER — If You Only Have 5 Minutes

Say this verbatim if time is short:

"LinkedIn has two distinct hard problems: the connection graph and the content feed.

For the connection graph: connections are bidirectional. Alice connects with Bob — I store TWO Cassandra rows: (user_id=alice, friend_id=bob) AND (user_id=bob, friend_id=alice). This lets me answer 'get all connections of user X' with a single partition scan. No JOINs, O(1) partition read.

For PYMK — People You May Know: I take user X's 1st-degree connections, then get their connections (2nd-degree), count mutual connections per candidate, rank by that count, cache result in Redis for 1 hour. This is O(N×M) where N is X's connections and M is average connections per person. For a normal user with 300 connections: 90K reads. Expensive to compute, cheap to serve from cache.

For the feed: hybrid fan-out. Users with fewer than 10K connections get push fan-out — when they post, I write their post to all followers' Redis feed sorted sets. Users with more than 10K connections (Bill Gates, Satya Nadella) get pull fan-out — their followers pull the post at read time. This prevents one post from triggering 50M writes.

For job search: Elasticsearch with a bool query — must match keywords in title/description, filter by location, company, posted_after. Results ranked by relevance × recency × user's skill match score."

---

# ═══════════════ PAGE 2 — GLOSSARY ═══════════════

```
┌────────────────────────────────┬──────────────────────────────────────────────────────────┐
│ TERM                           │ WHAT IT MEANS                                            │
├────────────────────────────────┼──────────────────────────────────────────────────────────┤
│ PYMK                           │ People You May Know. LinkedIn's friend suggestion feature.│
│                                │ Based on 2nd-degree connections (friends of friends)     │
│                                │ ranked by mutual connection count.                       │
├────────────────────────────────┼──────────────────────────────────────────────────────────┤
│ 1st-Degree Connection          │ Users directly connected to you. You explicitly accepted │
│                                │ their invite (bidirectional, unlike Instagram follow).   │
├────────────────────────────────┼──────────────────────────────────────────────────────────┤
│ 2nd-Degree Connection          │ Friends of your friends. NOT directly connected to you.  │
│                                │ Core of PYMK algorithm.                                  │
├────────────────────────────────┼──────────────────────────────────────────────────────────┤
│ Bidirectional Connection       │ Unlike Twitter/Instagram "follow," LinkedIn connections  │
│                                │ require mutual acceptance. Both users see each other     │
│                                │ in their connections list. Requires 2 DB rows.           │
├────────────────────────────────┼──────────────────────────────────────────────────────────┤
│ Fan-out on Write               │ When user posts, immediately write to all followers'     │
│                                │ feed caches (Redis sorted sets). Feed reads are instant. │
│                                │ Expensive on write. Used for non-influencer users.       │
├────────────────────────────────┼──────────────────────────────────────────────────────────┤
│ Fan-out on Read                │ Don't pre-populate followers' feed caches. At read time, │
│                                │ fetch influencer's latest posts and merge. Used when     │
│                                │ user has > 10K connections (too expensive on write).     │
├────────────────────────────────┼──────────────────────────────────────────────────────────┤
│ Hybrid Fan-out                 │ Combination: push for normal users, pull for influencers │
│                                │ (> 10K connections). Feed at read = merge both buckets.  │
├────────────────────────────────┼──────────────────────────────────────────────────────────┤
│ Cassandra Two-Table Approach   │ For bidirectional connections: one table partitioned by  │
│                                │ user_id (get my connections), one by friend_id (get who  │
│                                │ added me). Both are Cassandra partition-key lookups.     │
├────────────────────────────────┼──────────────────────────────────────────────────────────┤
│ Neo4j / Graph DB               │ Purpose-built graph database. Excellent for recursive    │
│                                │ graph traversal (2nd, 3rd degree). LinkedIn actually     │
│                                │ uses custom graph store. In interview: mention as PYMK   │
│                                │ alternative to Cassandra two-table approach.             │
├────────────────────────────────┼──────────────────────────────────────────────────────────┤
│ Endorsement                    │ User A endorses User B for skill "Java." Stored in       │
│                                │ Cassandra: (endorsed_user_id, skill, endorser_id). Count │
│                                │ shown on B's profile. B notified via Kafka.              │
├────────────────────────────────┼──────────────────────────────────────────────────────────┤
│ Profile View                   │ LinkedIn Premium feature: see who viewed your profile.   │
│                                │ Stored in Cassandra: (viewed_user_id, viewer_id,         │
│                                │ viewed_at). Free users see count only, Premium see list. │
├────────────────────────────────┼──────────────────────────────────────────────────────────┤
│ InMail                         │ LinkedIn's paid messaging to non-connections. Limited    │
│                                │ credits for Premium users. Stored same as regular msgs  │
│                                │ with is_inmail=true flag. Much lower volume than regular │
│                                │ messaging.                                               │
├────────────────────────────────┼──────────────────────────────────────────────────────────┤
│ Feed Sorted Set (Redis)        │ ZADD feed:{userId} {timestamp} {postId}. Feed read =    │
│                                │ ZREVRANGE feed:{userId} 0 19 (top 20 recent posts).     │
├────────────────────────────────┼──────────────────────────────────────────────────────────┤
│ Soft Delete                    │ users.is_active = false instead of DELETE. Connections  │
│                                │ and posts remain in DB but filtered at read time.        │
│                                │ Prevents orphaned foreign keys and enables reactivation. │
├────────────────────────────────┼──────────────────────────────────────────────────────────┤
│ Super-Connector                │ User with 10,000+ connections (e.g. recruiters, CEOs).  │
│                                │ PYMK computation for them is expensive — use sampling.  │
├────────────────────────────────┼──────────────────────────────────────────────────────────┤
│ Skills Graph                   │ LinkedIn's structured taxonomy of skills (Java,          │
│                                │ Machine Learning, etc.). Normalized table for job-skill  │
│                                │ matching. Endorsements linked to this table.             │
└────────────────────────────────┴──────────────────────────────────────────────────────────┘
```

---

# ═══════════════ PAGE 3 — WHY EACH COMPONENT ═══════════════

```
┌──────────────────┬──────────────────────────────────┬──────────────────────────────────┐
│ TECHNOLOGY       │ WHY WE USE IT                    │ WHY NOT ALTERNATIVE               │
├──────────────────┼──────────────────────────────────┼──────────────────────────────────┤
│ Cassandra        │ Connections, posts, messages,     │ Not MySQL for connections: 950M  │
│ (Connections,    │ profile views — all high-volume  │ users × avg 300 connections =    │
│  Posts, Feed)    │ append-heavy time-series data.   │ 285B rows. MySQL table scans,    │
│                  │ Partition key design enables     │ index maintenance too expensive. │
│                  │ O(1) lookups. Linear scale-out.  │ Cassandra partitions handle it.  │
├──────────────────┼──────────────────────────────────┼──────────────────────────────────┤
│ MySQL            │ Users, companies, jobs — need    │ Not Cassandra for users: profile │
│ (Users,          │ relational integrity. Jobs need  │ page needs JOIN (user + company  │
│  Companies,      │ company FK. Companies need       │ + skills). Cassandra has no JOINs│
│  Jobs)           │ location, industry attributes.   │ MongoDB works but MySQL is more  │
│                  │ Data is normalized, stable.      │ mature for relational constraints.│
├──────────────────┼──────────────────────────────────┼──────────────────────────────────┤
│ Redis            │ Feed sorted sets: O(log N) insert│ Not Cassandra for feed: Cassandra │
│ (Feed, PYMK      │ O(1) range read. PYMK cache:     │ feed reads involve more I/O than  │
│  Cache, Session) │ avoids 90K Cassandra reads per   │ Redis in-memory sorted set.       │
│                  │ feed load. Sub-millisecond.      │ Not local HashMap: not shared     │
│                  │                                  │ across app instances.             │
├──────────────────┼──────────────────────────────────┼──────────────────────────────────┤
│ Elasticsearch    │ Job search: keyword in title/    │ Not MySQL FULLTEXT: poor at       │
│ (Jobs + People   │ description + location filter +  │ compound queries (text + geo +    │
│  Search)         │ skills match scoring. People     │ skill scoring). Not Cassandra:    │
│                  │ search: name + company + title.  │ no full-text inverted index.      │
├──────────────────┼──────────────────────────────────┼──────────────────────────────────┤
│ Kafka            │ Post fan-out to 300 connections  │ Not synchronous: posting should   │
│ (Async Fan-out   │ should be async. Notifications   │ return in <100ms; fan-out to 300  │
│  + Notifications)│ (endorsement, connection invite) │ feeds is slow synchronously.      │
│                  │ should not block the write path. │ Not RabbitMQ: Kafka replay on     │
│                  │ Reliable, ordered, replayable.   │ fan-out worker crash is critical. │
├──────────────────┼──────────────────────────────────┼──────────────────────────────────┤
│ Neo4j            │ For PYMK at extreme depth (3rd/  │ Why Cassandra two-table wins for  │
│ (PYMK alt)       │ 4th degree graph traversal).     │ LinkedIn: Cassandra already used  │
│                  │ Cypher query language is elegant │ for connections store, so avoiding │
│                  │ for "friends of friends" queries. │ additional infrastructure. Neo4j  │
│                  │ LinkedIn uses custom graph store. │ adds operational complexity.      │
├──────────────────┼──────────────────────────────────┼──────────────────────────────────┤
│ WebSocket        │ LinkedIn Messaging: bidirectional│ Not polling: 300M MAU × 1 poll/  │
│ (Messaging)      │ real-time chat. User sends +     │ 3sec = 100M requests/sec. Not     │
│                  │ receives messages on same         │ SSE: SSE is server→client only;   │
│                  │ connection. Long-lived.           │ messaging needs client→server too.│
└──────────────────┴──────────────────────────────────┴──────────────────────────────────┘
```

---

# ═══════════════ PAGE 4 — FULL INTERVIEW SCRIPT ═══════════════

## OPENING

Say this to start:

"LinkedIn is a professional social network with several distinct subsystems: profile management, connections (the social graph), the content feed, job search, and messaging. The two hardest design problems are: first, the bidirectional connection graph at 950M user scale — specifically the PYMK algorithm, which requires 2nd-degree graph traversal. Second, the hybrid fan-out for the content feed, which is similar to Instagram but with professional content quality requirements. Let me clarify requirements first."

---

## STEP 1 — Requirements Gathering

```
┌─────────────────────────────────────────────────────────────────────┐
│ CLARIFYING QUESTIONS TO ASK                                         │
├─────────────────────────────────────────────────────────────────────┤
│ 1. Should I cover messaging or focus on feed + connections?         │
│ 2. How deep should I go into job recommendations vs. just search?   │
│ 3. Do we need the LinkedIn Premium features (who viewed profile)?   │
│ 4. Should I cover LinkedIn Live (video) or focus on text/image?    │
│ 5. Is real-time notification critical or eventual-consistent OK?    │
│ 6. What scale — India-focused or global (950M users)?              │
└─────────────────────────────────────────────────────────────────────┘
```

**Functional Requirements:**
- Users can create and edit professional profiles (experience, skills, education)
- Users can connect with other users (bidirectional, requires acceptance)
- Users can post text/image content; connections see posts in their feed
- Feed is personalized — not purely chronological, includes engagement signals
- PYMK (People You May Know) suggests connections based on mutual connections
- Job search: search by title, skills, location, company
- Job recommendations: personalized based on user's profile
- Users can endorse connections for specific skills
- Messaging between connections (+ InMail for Premium)
- Notifications: connection request, endorsement, post reaction, mention

**Non-Functional Requirements:**
- Feed load time: < 200ms (pre-computed, served from Redis)
- PYMK freshness: can be 1 hour stale (computed by background job)
- Connection operations (add/remove): eventual consistency OK within 5 sec
- Messaging: real-time, < 1 sec delivery
- Job search: eventual consistency OK (new jobs visible within 30 sec of posting)
- Scale: 950M total users, 300M MAU, 50M posts/day

---

## STEP 2 — Capacity Estimation

```
┌───────────────────────────────────────────────────────────────────┐
│ CAPACITY NUMBERS                                                   │
├──────────────────────────────┬────────────────────────────────────┤
│ Total users                  │ 950 million                        │
│ Monthly active users (MAU)   │ 300 million                        │
│ Posts per day                │ 50 million                         │
│ Posts per second             │ ~580/sec                           │
│ Connections added per month  │ 100 million                        │
│ Connections added per sec    │ ~40/sec                            │
│ Average connections per user │ 300                                │
│ Total connection rows        │ 950M × 300 × 2 = 570 billion rows  │
│                              │ (2 rows per connection, both dirs) │
│ Job postings active          │ 10 million                         │
│ Job searches per day         │ 50 million                         │
│ PYMK compute per user        │ 300 connections × 300 = 90K reads  │
│ PYMK cache TTL               │ 1 hour                             │
│ Feed sorted set size         │ Top 1,000 posts per user in Redis  │
│ Influencer threshold         │ > 10,000 connections → pull fan-out│
│ InMail volume/day            │ ~5 million (much lower than msgs)  │
│ Profile views per day        │ 500 million                        │
└──────────────────────────────┴────────────────────────────────────┘
```

"570 billion connection rows is the scary number — that's why we use Cassandra with partition key on user_id, not MySQL with a single connections table."

---

## STEP 3 — Core Entities

- **User**: profile (name, headline, location, photo), experience, education, skills
- **Company**: company profile, industry, size, location, job postings
- **Connection**: bidirectional relationship between two users (pending/accepted states)
- **Post**: text/image content created by a user (with reactions, comments, shares)
- **Job**: job posting by a company (title, description, requirements, location, salary)
- **Skill**: normalized skill taxonomy (Java, Machine Learning, etc.)
- **Endorsement**: user A endorses user B for skill X
- **ProfileView**: user A viewed user B's profile (privacy-controlled)
- **Message**: direct message between users (or InMail for non-connections)
- **Notification**: in-app notification event (connection_request, endorse, mention, react)

---

## STEP 4 — API Design

```
# Profile
GET  /users/{userId}
     → Returns: full profile (from MySQL users + Cassandra skills/endorsements)
     → Cache in Redis: user:{userId} TTL 5 min

PUT  /users/{userId}
     → Update profile fields; invalidate Redis cache; update Elasticsearch index

# Connections
POST /connections { target_user_id }
     → Creates PENDING connection request
     → Kafka: connection-requested → notification to target

POST /connections/{connectionId}/accept
     → Inserts TWO Cassandra rows (bidirectional)
     → Kafka: connection-accepted → trigger PYMK recompute for both users

DELETE /connections/{connectionId}
     → Deletes both Cassandra rows (both directions)

GET  /users/{userId}/connections?page=1&size=20
     → Cassandra: SELECT FROM connections_by_user WHERE user_id=?

# PYMK
GET  /users/{userId}/pymk
     → Redis: GET pymk:{userId} (JSON list of suggested user_ids)
     → If miss: compute on demand (or return empty, background job fills)

# Feed
GET  /feed?page=0&size=20
     → Redis: ZREVRANGE feed:{userId} 0 19 (pre-computed sorted set)
     → Pull influencer posts at merge time
     → Re-rank by engagement model score

POST /posts { content_text, image_url, visibility }
     → MySQL: INSERT post
     → Kafka: post-created → feed fan-out worker

# Job Search
GET  /jobs/search?keywords=java+developer&location=bangalore&company=infosys&salary_min=1500000
     → Elasticsearch: bool query {must: [match title/description], filter: [geo, company, salary]}

# Endorsements
POST /endorsements { endorsed_user_id, skill_id }
     → Cassandra: INSERT endorsements (endorsed_user_id, skill_id, endorser_id, endorsed_at)
     → Kafka: endorsed → notify endorsed_user
```

---

> **► DRAW THIS on the whiteboard ◄**

## JSON REQUEST / RESPONSE EXAMPLES

```json
// GET /api/v1/feed?cursor=7234891&limit=20
// Response 200 OK:
{
  "posts": [
    {
      "postId": "7234891234567892",
      "author": { "userId": "user_abc", "name": "Alice Smith", "headline": "SDE at Google" },
      "content": "Excited to share that I'm joining Google as SDE III!",
      "likeCount": 842,
      "commentCount": 156,
      "createdAt": "2025-01-21T09:15:00Z"
    }
  ],
  "nextCursor": "7234891234560000"
}

// GET /api/v1/pymk?limit=10
// Response 200 OK:
{
  "suggestions": [
    {
      "userId": "user_xyz",
      "name": "Bob Johnson",
      "headline": "Product Manager at Flipkart",
      "mutualConnections": 12,
      "mutualConnectionNames": ["Alice Smith", "Charlie Brown"]
    }
  ]
}

// POST /api/v1/connections/{targetUserId}
// Response 200 OK:
{
  "status": "REQUEST_SENT",
  "targetUserId": "user_xyz",
  "message": "Connection request sent to Bob Johnson."
}
```

---

## STEP 5 — High-Level Architecture

► DRAW THIS ◄

```
                    ┌────────────────────────────────────────────────────────┐
                    │               HIGH-LEVEL ARCHITECTURE                  │
                    └────────────────────────────────────────────────────────┘

  Browser / Mobile
       │
       ▼
┌──────────────────────┐
│    API Gateway        │
│  (Auth/JWT, Rate      │
│   Limit, Route)       │
└──────┬───────────────┘
       │
┌──────┴────────────────────────────────────────────────┐
│                                                       │
▼              ▼              ▼              ▼           ▼
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│ Profile  │ │  Graph   │ │  Feed    │ │  Job     │ │  Msg     │
│ Service  │ │  Service │ │  Service │ │  Service │ │  Service │
│          │ │ (conn +  │ │ (create, │ │ (search, │ │(WebSocket│
│          │ │  PYMK)   │ │  read)   │ │  recom.) │ │  store)  │
└────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘
     │             │             │             │            │
     │             │             │             │            │
     ▼             ▼             ▼             ▼            ▼
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│  MySQL   │ │Cassandra │ │  Redis   │ │  Elastic-│ │Cassandra │
│ users    │ │connect-  │ │ feed:{}  │ │  search  │ │ messages │
│ companies│ │ions_by_  │ │ pymk:{}  │ │ jobs idx │ │ (by conv)│
│ jobs     │ │user/     │ │ user:{}  │ │ people   │ │          │
│ skills   │ │friend    │ │ session  │ │ idx      │ │          │
└──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘
                                │
                         ┌──────▼──────────────────────────────────────┐
                         │                  Kafka                       │
                         │   post-created → feed-fan-out-worker        │
                         │   connection-accepted → pymk-recompute      │
                         │   endorsed → notification-worker            │
                         │   job-posted → elasticsearch-indexer        │
                         └──────────────────────────────────────────────┘
                                │
             ┌──────────────────┤
             │                  │
             ▼                  ▼
   ┌──────────────────┐  ┌──────────────────────┐
   │  Feed Fan-out    │  │  Notification Service │
   │  Worker          │  │  (FCM/APNs/SSE bell)  │
   │  (writes Redis   │  │                      │
   │   sorted sets)   │  │                      │
   └──────────────────┘  └──────────────────────┘
```

---

> **► DRAW THIS on the whiteboard ◄**

## SEQUENCE DIAGRAM — PYMK (People You May Know)

```
  User App     PYMK Service      Cassandra       Redis      ML Ranker
     │               │               │              │              │
     │ GET /pymk     │               │              │              │
     │──────────────▶│               │              │              │
     │               │ GET PYMK:{uid}│              │              │
     │               │──────────────────────────────▶              │
     │               │◀──────────────────────────────              │
     │               │ [cache HIT → return immediately]            │
     │ {pymkList}    │              OR                             │
     │◀──────────────│                              │              │
     │               │ [cache MISS]                 │              │
     │               │               │              │              │
     │               │ SELECT connections of userId │              │
     │               │───────────────▶              │              │
     │               │◀───────────────              │              │
     │               │  [conn_ids[]  │              │              │
     │               │  N=300]       │              │              │
     │               │               │              │              │
     │               │ BATCH SELECT connections of each friend     │
     │               │ (2nd degree = N×M candidates)               │
     │               │───────────────▶              │              │
     │               │◀───────────────              │              │
     │               │  [2nd_degree_ids[]]          │              │
     │               │               │              │              │
     │               │ Count mutual connections per candidate       │
     │               │ Filter: remove self, existing, blocked       │
     │               │               │              │              │
     │               │ Rank by: mutual_count + industry + company   │
     │               │──────────────────────────────────────────▶  │
     │               │◀──────────────────────────────────────────  │
     │               │  [ranked PYMK list]          │              │
     │               │               │              │              │
     │               │ SET PYMK:{uid} list EX 3600  │              │
     │               │──────────────────────────────▶              │
     │ {pymkList}    │               │              │              │
     │◀──────────────│               │              │              │
```

## SEQUENCE DIAGRAM — SEND CONNECTION REQUEST

```
  User App     Connection Service    MySQL          Kafka    Notif Service
     │               │                  │              │           │
     │ POST /connect │                  │              │           │
     │ {targetUserId}│                  │              │           │
     │──────────────▶│                  │              │           │
     │               │ Check: already   │              │           │
     │               │ connected?       │              │           │
     │               │──────────────────▶              │           │
     │               │◀──────────────────              │           │
     │               │  [NO]            │              │           │
     │               │ INSERT connection_requests      │           │
     │               │ status=PENDING   │              │           │
     │               │──────────────────▶              │           │
     │ 200 {sent}    │                  │              │           │
     │◀──────────────│                  │              │           │
     │               │ publish connect_requested event │           │
     │               │──────────────────────────────────▶          │
     │               │                  │              │ push notif│
     │               │                  │              │──────────▶│
```

---

## STEP 6 — Database Schema

► DRAW THIS ◄

```
┌─────────────────────────────────────────────────────────────────────────┐
│                             MYSQL SCHEMA                                 │
└─────────────────────────────────────────────────────────────────────────┘

users
┌──────────────────┬───────────────────────────────────────────────────────┐
│ user_id          │ BIGINT PK AUTO_INCREMENT                              │
│ name             │ VARCHAR(200)                                          │
│ email            │ VARCHAR(200) UNIQUE                                   │
│ headline         │ VARCHAR(500)  ("Senior Engineer at Google")           │
│ location         │ VARCHAR(200)                                          │
│ profile_photo_url│ TEXT                                                  │
│ is_active        │ BOOLEAN DEFAULT TRUE  (soft delete)                   │
│ is_premium       │ BOOLEAN DEFAULT FALSE                                 │
│ connection_count │ INT DEFAULT 0  (denormalized counter, updated async)  │
│ created_at       │ TIMESTAMP                                             │
└──────────────────┴───────────────────────────────────────────────────────┘

companies
┌──────────────────┬───────────────────────────────────────────────────────┐
│ company_id       │ BIGINT PK                                             │
│ name             │ VARCHAR(200)                                          │
│ industry         │ VARCHAR(100)                                          │
│ size_range       │ ENUM('1-10','11-50','51-200','201-500','500+')        │
│ city             │ VARCHAR(100)                                          │
│ logo_url         │ TEXT                                                  │
└──────────────────┴───────────────────────────────────────────────────────┘

jobs
┌──────────────────┬───────────────────────────────────────────────────────┐
│ job_id           │ BIGINT PK                                             │
│ company_id       │ BIGINT FK → companies                                 │
│ title            │ VARCHAR(200)                                          │
│ description      │ TEXT                                                  │
│ location         │ VARCHAR(200)                                          │
│ is_remote        │ BOOLEAN                                               │
│ salary_min       │ BIGINT NULL  (annual, local currency paise/cents)     │
│ salary_max       │ BIGINT NULL                                           │
│ status           │ ENUM('OPEN','CLOSED','FILLED')                       │
│ posted_at        │ TIMESTAMP                                             │
│ INDEX            │ (company_id, posted_at)                              │
└──────────────────┴───────────────────────────────────────────────────────┘

skills  (normalized taxonomy)
┌──────────────────┬───────────────────────────────────────────────────────┐
│ skill_id         │ BIGINT PK                                             │
│ name             │ VARCHAR(100) UNIQUE  (e.g. "Java", "React", "SQL")    │
│ category         │ VARCHAR(100)  (e.g. "Programming Languages")          │
└──────────────────┴───────────────────────────────────────────────────────┘
```

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          CASSANDRA SCHEMA                                │
└─────────────────────────────────────────────────────────────────────────┘

connections_by_user
  PRIMARY KEY: (user_id, connected_user_id)
  Columns: connected_at TIMESTAMP, status ENUM (PENDING/ACCEPTED)
  → Query: "Get all connections of user Alice"
    SELECT * FROM connections_by_user WHERE user_id = alice_id
  → Partition: all Alice's connections on one Cassandra node
  → Write: INSERT (alice_id, bob_id, NOW(), ACCEPTED)

connections_by_friend  (mirror table — same data, different partition key)
  PRIMARY KEY: (connected_user_id, user_id)
  Columns: connected_at TIMESTAMP
  → Query: "Who has connected TO user Bob?" (inverse lookup)
    SELECT * FROM connections_by_friend WHERE connected_user_id = bob_id
  → WHY: needed for PYMK calculation — "find users whose connections
    include users that Alice is also connected to"

posts
  PRIMARY KEY: (user_id, created_at DESC)
  Columns: post_id UUID, content_text TEXT, image_url TEXT,
           visibility ENUM(PUBLIC/CONNECTIONS_ONLY), like_count INT,
           comment_count INT
  → Query: "Get posts by user X": SELECT WHERE user_id=X LIMIT 20
  → Feed fan-out reads from this table to get post content

endorsements
  PRIMARY KEY: (endorsed_user_id, skill_id, endorser_id)
  Columns: endorsed_at TIMESTAMP
  → Query: "How many people endorsed Alice for Java?"
    SELECT COUNT(*) WHERE endorsed_user_id=alice AND skill_id=java_skill
  → Query: "Did Bob endorse Alice for Java?"
    SELECT WHERE endorsed_user_id=alice AND skill_id=java AND endorser_id=bob

profile_views
  PRIMARY KEY: (viewed_user_id, viewed_at DESC)
  Columns: viewer_id BIGINT
  → Query: "Who viewed Bob's profile in last 7 days?" (Premium feature)
    SELECT WHERE viewed_user_id=bob AND viewed_at > 7_days_ago
  → TTL: 90 days (USING TTL 7776000 on each INSERT)

messages
  PRIMARY KEY: (conversation_id, sent_at DESC)
  Columns: message_id UUID, sender_id BIGINT, content TEXT, read_at TIMESTAMP NULL
  → conversation_id = hash(min(user1,user2), max(user1,user2)) — deterministic
  → Query: "Get last 50 messages in conversation between Alice and Bob"
    SELECT WHERE conversation_id=? LIMIT 50
```

---

> **► DRAW THIS on the whiteboard ◄**

## ER RELATIONSHIP DIAGRAM

```
┌──────────────────────────────────────────────────────────────────────┐
│                   LINKEDIN — ENTITY RELATIONSHIP                      │
└──────────────────────────────────────────────────────────────────────┘

┌─────────────────┐      ┌──────────────────────┐
│     users        │      │       companies       │
│    (MySQL)       │      │       (MySQL)         │
├─────────────────┤      ├──────────────────────┤
│ PK user_id UUID │      │ PK company_id UUID   │
│    name VARCHAR │      │    name VARCHAR      │
│    headline TEXT│      │    industry VARCHAR  │
│    location TEXT│      │    size_range ENUM   │
│ FK current_co   │─────▶│    logo_url TEXT     │
│    created_at TS│      └────────────┬─────────┘
└────────┬────────┘                   │ 1
         │                            │ N
         │ N          ┌───────────────▼──────────────┐
         │            │         job_postings           │
┌────────▼────────┐   │           (MySQL)             │
│  connections    │   ├──────────────────────────────┤
│   (Cassandra)   │   │ PK job_id UUID               │
├─────────────────┤   │ FK company_id UUID           │
│ PK user_id(PART)│   │    title VARCHAR             │
│    conn_id UUID │   │    skills_required SET<TEXT> │
│    connected_uid│   │    location VARCHAR          │
│    connected_at │   │    salary_range VARCHAR      │
└─────────────────┘   │    status ENUM(OPEN,CLOSED)  │
(dual rows: A→B, B→A) │    posted_at TIMESTAMP       │
                      └──────────────────────────────┘

  posts (Cassandra)            endorsements (Cassandra)
  ┌───────────────────────┐    ┌──────────────────────────┐
  │ PK post_id Snowflake  │    │ PK endorsed_id UUID(PART)│
  │ FK user_id UUID       │    │    skill VARCHAR (CLUST) │
  │    content TEXT       │    │    endorser_id UUID      │
  │    media_urls LIST    │    │    endorsed_at TIMESTAMP │
  │    created_at TS      │    └──────────────────────────┘
  └───────────────────────┘

  Redis:
  ┌────────────────────────────────────────────────────────┐
  │ feed:{userId}       ZSET (score→postId, max 500)       │
  │ PYMK:{userId}       LIST (cached PYMK results, TTL 1h) │
  │ online:{userId}     TTL 30s (presence)                 │
  │ session:{token}     HASH user session                  │
  └────────────────────────────────────────────────────────┘
```

---

## STEP 7 — Deep Dive: PYMK Algorithm

"People You May Know is LinkedIn's signature feature and the most algorithmically interesting part. Let me walk through it precisely."

► DRAW THIS ◄

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    PYMK ALGORITHM — STEP BY STEP                         │
│                    (Pre-computed hourly, not real-time)                  │
└─────────────────────────────────────────────────────────────────────────┘

  Input: User X  (e.g. Alice, connection_count=300)
       │
       ▼
  STEP 1: Get Alice's 1st-degree connections
  ┌─────────────────────────────────────────────────────────────────┐
  │  Cassandra: SELECT connected_user_id                            │
  │             FROM connections_by_user WHERE user_id = alice_id   │
  │  → Result: [bob, carol, dave, ...300 connections]              │
  └──────────────────────────────────┬──────────────────────────────┘
                                     │
                                     ▼
  STEP 2: Get 2nd-degree connections (friends of friends)
  ┌─────────────────────────────────────────────────────────────────┐
  │  For each of Alice's 300 connections:                           │
  │    Cassandra: SELECT connected_user_id                          │
  │               FROM connections_by_user WHERE user_id = friend   │
  │                                                                 │
  │  → Returns ~300 × 300 = 90,000 candidate user_ids              │
  │  → Batch these Cassandra reads for efficiency                  │
  │    (Cassandra IN clause or async parallel reads)               │
  └──────────────────────────────────┬──────────────────────────────┘
                                     │
                                     ▼
  STEP 3: Count mutual connections per candidate
  ┌─────────────────────────────────────────────────────────────────┐
  │  HashMap<userId, Integer> mutualCount                           │
  │  For each candidate in 90K list:                               │
  │    mutualCount[candidate]++                                    │
  │                                                                 │
  │  → evan: 15 mutual connections                                 │
  │  → frank: 3 mutual connections                                 │
  │  → grace: 1 mutual connection                                  │
  └──────────────────────────────────┬──────────────────────────────┘
                                     │
                                     ▼
  STEP 4: Filter
  ┌─────────────────────────────────────────────────────────────────┐
  │  Remove: alice herself (user X)                                 │
  │  Remove: alice's existing connections (already 1st degree)     │
  │  Remove: users who blocked alice                               │
  │  Remove: inactive users (is_active = false)                    │
  │  Remove: users with private profiles if not connected          │
  └──────────────────────────────────┬──────────────────────────────┘
                                     │
                                     ▼
  STEP 5: Rank remaining candidates
  ┌─────────────────────────────────────────────────────────────────┐
  │  Sort by: mutual_connections DESC                               │
  │  Tiebreak: same_company score + same_school score + industry   │
  │  Take top 25 candidates                                        │
  └──────────────────────────────────┬──────────────────────────────┘
                                     │
                                     ▼
  STEP 6: Cache result
  ┌─────────────────────────────────────────────────────────────────┐
  │  Redis: SETEX pymk:{aliceId} 3600 [{userId, mutual_count}, ...]│
  │  TTL: 1 hour (PYMK suggestions are stable, 1hr stale is fine)  │
  └─────────────────────────────────────────────────────────────────┘

  TRIGGER: Recompute pymk:{userId} when:
    - User X gains a new connection (most impactful)
    - User X removes a connection
    - Hourly background sweep for all active users
```

**Complexity analysis:**
"For a typical user with 300 connections, each with 300 connections: 90K Cassandra reads. That's expensive to do in real-time. So PYMK is always pre-computed as a background job and cached. API response time = 1 Redis GET = sub-millisecond."

---

## STEP 7B — Feed Fan-out (Hybrid Strategy)

```
┌─────────────────────────────────────────────────────────────────────────┐
│              HYBRID FEED FAN-OUT STRATEGY                                │
└─────────────────────────────────────────────────────────────────────────┘

  POST /posts  (Alice, 300 connections, normal user)
       │
       ▼
  MySQL: INSERT post row  →  Kafka: post-created { postId, userId=alice }
       │
       ▼
  Feed Fan-out Worker (Kafka consumer):
    1. Get all of alice's connections: connections_by_user WHERE user_id=alice
       → [bob, carol, dave, ...300 connection_ids]
    2. For each connection_id:
       Redis: ZADD feed:{connection_id} {timestamp} {post_id}
       → Adds alice's post to bob's feed, carol's feed, etc.
    3. Trim: ZREMRANGEBYRANK feed:{connection_id} 0 -1001
       (keep only 1000 most recent posts in feed)

  ─────────────────────────────────────────────────────────────────────

  POST /posts  (Bill Gates, 5M connections, influencer)
       │
       ▼
  MySQL: INSERT post row  →  Kafka: post-created { postId, userId=gates }
       │
       ▼
  Fan-out Worker: connection_count > 10K → SKIP fan-out
                  Mark post as: influencer_post = true

  ─────────────────────────────────────────────────────────────────────

  GET /feed  (Bob reading his feed)
       │
       ▼
  Feed Service:
    1. ZREVRANGE feed:{bob_id} 0 99  → pre-built posts from normal connections
    2. For each influencer Bob follows (connection_count > 10K):
       Cassandra: SELECT recent posts WHERE user_id = influencer_id LIMIT 5
    3. Merge + deduplicate + re-rank by engagement score
    4. Return top 20 posts to Bob
```

---

## STEP 8 — Scalability

**BOTTLENECK 1: Feed Fan-out for High-Connection Users**

"Average user has 300 connections — fan-out is 300 Redis writes. Total: 580 posts/sec × 300 = 174K Redis writes/sec. Redis handles 300K writes/sec — fine. But for the top 1% of users with 10K connections: 580/sec × 10K = 5.8M Redis writes/sec for that user segment alone. Solution: hybrid fan-out threshold at 10K. Users above threshold become 'pull' users. Fan-out workers check connection_count before writing."

**BOTTLENECK 2: PYMK Background Job at 300M MAU Scale**

"Computing PYMK for 300M MAU hourly = 300M × 90K Cassandra reads = 27 trillion reads/hour. That's impossible. Solution: tiered recompute. Compute PYMK for active users only (last 24h login) — maybe 50M users. For them: stagger recompute over the hour = 50M/3600 = ~14K PYMK computations/sec. Each computation does 90K Cassandra reads = 1.26B reads/sec across the Cassandra cluster. With 100-node Cassandra cluster at 100K reads/node/sec = 10B reads/sec capacity. Manageable."

**BOTTLENECK 3: 570 Billion Connection Rows**

"570B Cassandra rows across both tables. Cassandra handles petabytes. Key design: partition key = user_id, so all of Alice's connections are on one node (hot partition risk if super-connector). Mitigate: composite partition key (user_id % 100, user_id) to spread super-connector data. Most users are fine with pure user_id partitioning."

**BOTTLENECK 4: Profile View Storage for 500M Daily Views**

"500M profile view events/day × 30-day retention = 15B rows. Cassandra with TTL handles this. 15B × ~50 bytes = 750 GB. Across 20 Cassandra nodes = 37 GB/node. Comfortable. Query latency: partition key = viewed_user_id, so 'who viewed my profile' is a single partition scan. For Premium users (who can see viewer list): SELECT WHERE viewed_user_id=? AND viewed_at > 7_days_ago — efficient."

---

## WHAT NOT TO SAY ✗

- ✗ "I'll use a single connections table in MySQL with two columns: user1_id and user2_id" — at 570B rows, MySQL single table is catastrophic. And two-column bidirectional storage requires WHERE user1_id=X OR user2_id=X which never uses an index efficiently. Always two Cassandra tables.
- ✗ "PYMK can be computed on demand when the user opens the app" — for a user with 300 connections each having 300 connections = 90K Cassandra reads synchronously in an API call. This would take 500ms+. Always pre-computed background job, cached in Redis.
- ✗ "I'll fan-out all posts to all followers synchronously in the POST /posts API" — if you have 10K connections, the API call blocks for 10K Redis writes = seconds. Always async via Kafka.
- ✗ "Bill Gates with 5M LinkedIn connections gets push fan-out" — 5M Redis ZADD per Bill Gates post = catastrophic. Hybrid fan-out: influencers (>10K) are always pull. Say this without being asked — it shows you know the celebrity problem.
- ✗ "Messages are stored in MySQL" — LinkedIn messaging is high-volume, sequential, time-series. Cassandra with (conversation_id, sent_at) partition is the right model. MySQL will have table growth and index degradation problems.
- ✗ "PYMK uses Neo4j for real-time traversal" — Neo4j is valid to mention but say it's heavy infrastructure. Cassandra two-table approach avoids adding a separate graph database. LinkedIn's actual implementation is a custom graph store, but Cassandra is the right interview answer unless specifically designing for 3rd/4th degree traversal.
- ✗ "I'll delete connection rows when a user deactivates their account" — cascading deletes across 570B rows is a scheduled nightmare. Always soft delete: users.is_active = false. Filter at query time.

---

## SENIOR TRAP QUESTIONS (15 YOE Level)

### Category 1: Graph Scale

**Q: "A LinkedIn power user (recruiter) has 32,000 connections. Computing PYMK for them is O(32K × avg_300) = 9.6 million Cassandra reads. You said PYMK runs hourly. How do you handle this?"**

A: "For super-connectors, full PYMK computation is prohibitive. My solution: statistical sampling. Instead of reading all 32K connections' friend lists, I randomly sample 500 connections from their list. This gives 150K candidates (500 × 300) — more than enough to surface quality PYMK suggestions. The sampling is weighted by recency: connections made in the last 6 months are 3x more likely to be sampled than older connections. This approximation produces PYMK results indistinguishable from the full computation in user studies (mutual connections from a sample of 500 are usually the same top suggestions you'd get from 32K). Compute time drops from minutes to seconds. I'd also lower their recompute frequency: normal users get hourly recompute; super-connectors with 10K+ get daily recompute. PYMK suggestions for a recruiter don't need hourly freshness."

**Q: "User Alice removes her connection with Bob. What must happen to maintain consistency across both Cassandra tables and the PYMK cache?"**

A: "Connection removal requires writes to both Cassandra tables and cache invalidation. Transaction-wise: (1) DELETE FROM connections_by_user WHERE user_id=alice AND connected_user_id=bob. (2) DELETE FROM connections_by_friend WHERE connected_user_id=bob AND user_id=alice. These two Cassandra writes are NOT atomic — Cassandra has no multi-partition transactions. My approach: publish a Kafka event connection-removed {alice, bob}. A consumer does both deletes asynchronously. Between the two deletes there's a brief inconsistency window (Bob can still find Alice in connections_by_user for a fraction of a second) — this is acceptable for PYMK purposes. (3) DEL pymk:{alice_id} and DEL pymk:{bob_id} from Redis — invalidate both their PYMK caches. Background job recomputes both on next cycle. (4) DEL feed entries from bob's feed for alice's recent posts? No — feed is eventually consistent, posts from removed connections naturally age out of the sorted set. I don't proactively purge."

### Category 2: Feed Quality

**Q: "LinkedIn's feed should surface professional, high-quality content — not just viral entertainment. How does your ranking differ from Instagram's?"**

A: "LinkedIn's feed ranking has an additional quality signal layer that Instagram's engagement-maximizing model doesn't need. My ranking function uses: (1) Recency: post age decay (exponential decay over 72 hours). (2) Connection strength: posts from close connections rank higher than weak connections. Proxied by: frequency of profile views between users, message history, same company. (3) Engagement velocity: likes and comments in first 2 hours signal quality. (4) Content type score: original thought leadership content > reshares > pure job post spam. Implemented as a trained ML model (features: post length, has_original_image, is_reshare, comment_to_like_ratio). (5) Demotion rules: posts with > 3 hashtags spam-scored. Posts from accounts with recent spam flags get -50% score. This is different from Instagram which purely optimizes for engagement time-on-screen. LinkedIn optimizes for 'professional value' which requires the demotion signals that Instagram doesn't need."

**Q: "LinkedIn announces a new feature: 'Collaborative Articles' — where multiple people co-author a post. How does this affect your feed fan-out model?"**

A: "Collaborative articles break the single-author fan-out assumption. A post with 5 co-authors should appear in the feeds of all 5 co-authors' connections — the union of their networks. Changes required: (1) posts table gains a co_authors JSON column or separate post_authors table (post_id, user_id, role ENUM(PRIMARY/COLLABORATOR)). (2) Feed fan-out worker: for each new collaborative article, fan-out to the union of all co-authors' connections — not just the primary author. (3) Deduplication: if Bob is connected to both Alice and Carol who co-authored, he should see the post once. The fan-out worker must deduplicate: only ZADD if feed:{bob_id} doesn't already contain the post_id. Or: maintain a separate seen_posts bloom filter per user. (4) Notification: all co-authors get notified of reactions/comments (configurable). (5) PYMK implication: co-authoring someone is a strong signal for PYMK — weight collaborative article pairs higher than just mutual connections."

### Category 3: Privacy and Compliance

**Q: "GDPR 'Right to Erasure': a user requests complete deletion of their LinkedIn account. What do you actually delete, and what's your deletion approach given 570B connection rows?"**

A: "Right to Erasure is the hardest compliance problem in distributed systems. My approach is staged soft-then-hard deletion: Stage 1 (immediate, synchronous): SET users.is_active=false, users.email=NULL, users.name='Deleted User', users.profile_photo_url=NULL. All API queries filter by is_active=true — the user is immediately invisible everywhere on the platform. This satisfies GDPR's 'make inaccessible' requirement within 24 hours. Stage 2 (async, 30 days later): background deletion job. Delete both Cassandra connection rows for all their connections (could be millions of rows — run as a distributed job, 10K deletes/sec, takes minutes for super-connectors). Delete their posts from Cassandra posts table. Delete their messages (but only their side — the conversation partner keeps their own messages per GDPR guidance). Delete profile_views where they are either viewer or viewed. Delete endorsements they gave (endorsed_user loses the endorsement count). Stage 3 (metadata): anonymize analytics events — replace user_id with a hash in Kafka/data warehouse. The key insight: immediate soft delete satisfies the user-facing requirement. Async cleanup handles the infrastructure at manageable pace without impacting production traffic."

---

## KEY NUMBERS

```
┌──────────────────────────────────────────┬──────────────────────────────────────────┐
│ METRIC                                   │ VALUE / NOTES                            │
├──────────────────────────────────────────┼──────────────────────────────────────────┤
│ Total users                              │ 950 million                              │
│ Monthly active users                     │ 300 million                              │
│ Average connections per user             │ 300                                      │
│ Total connection rows (both directions)  │ ~570 billion                             │
│ Posts per day                            │ 50 million                               │
│ Fan-out per normal post (300 connections)│ 300 Redis ZADD operations                │
│ Influencer threshold                     │ > 10,000 connections → pull fan-out      │
│ PYMK computation cost (avg user)         │ 90K Cassandra reads                      │
│ PYMK cache TTL                           │ 1 hour                                   │
│ Feed sorted set size (Redis)             │ Top 1,000 posts per user                 │
│ Feed read latency                        │ < 10ms (Redis ZREVRANGE)                 │
│ Profile views per day                    │ 500 million                              │
│ Profile view Cassandra retention         │ 30 days (TTL per row)                    │
│ Active job postings                      │ 10 million                               │
│ Job search QPS                           │ ~580/sec average                         │
│ Connections added per month              │ 100 million = ~40/sec                    │
│ PYMK recompute frequency (active users)  │ Hourly                                   │
│ Super-connector sampling threshold       │ > 10K connections → sample 500           │
└──────────────────────────────────────────┴──────────────────────────────────────────┘
```
