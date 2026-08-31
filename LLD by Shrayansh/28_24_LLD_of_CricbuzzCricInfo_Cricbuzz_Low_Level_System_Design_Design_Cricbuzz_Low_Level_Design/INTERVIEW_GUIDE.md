# 🏏 Cricbuzz/CricInfo - Low Level Design Interview Guide
## _15 YOE Architect-Level Conversational Script_

---

## 📋 **Table of Contents**
1. [Architecture Diagram](#1-architecture-diagram)
2. [API Design](#2-api-design)
3. [ER Diagram & Database Design](#3-er-diagram--database-design)
4. [Sequence Diagrams](#4-sequence-diagrams)
5. [Scenario-First Explanations](#5-scenario-first-explanations)
6. [Cross Questions](#6-cross-questions)
7. [Trade-offs](#7-trade-offs)
8. [Senior Trap Questions](#8-senior-trap-questions)
9. [Technology Choices](#9-technology-choices)

---

## **Design Pattern Used**: Observer Pattern (for live score updates)

**Interviewer**: "Design a system like Cricbuzz that shows live cricket scores."

**You**: "Great question! Let me clarify scope:
1. Live ball-by-ball score updates?
2. Match statistics (run rate, partnerships)?
3. Push notifications to millions of users?
4. Commentary feed?
5. Player statistics tracking?"

**Interviewer**: "Yes, focus on live score updates and how you'd push to millions of users efficiently."

**You**: "Perfect. The core challenge is: **How do you push real-time updates to millions of concurrent viewers without overwhelming your servers?**

Key insights:
1. **Observer Pattern**: Match state changes notify all subscribers
2. **Fan-out architecture**: One score update → millions of push notifications
3. **Read-heavy system**: 10,000:1 read-to-write ratio (many viewers, few scorers)

Let me show you the complete design..."

---

## 1. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       CRICBUZZ ARCHITECTURE                                  │
└─────────────────────────────────────────────────────────────────────────────┘

                    ┌──────────────────┐
                    │   SCORER/UMPIRE  │
                    │   (Admin App)    │
                    └────────┬─────────┘
                             │ Updates ball-by-ball
                             ▼
                    ┌──────────────────┐
                    │  MATCH SERVICE   │
                    │                  │
                    │  Match State     │
                    │  Current Over    │
                    │  Current Score   │
                    └────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
    │ SUBJECT      │ │ EVENT BUS    │ │  CACHE       │
    │ (Observable)  │ │ (Kafka)      │ │  (Redis)     │
    │              │ │              │ │              │
    │ Observers[]  │ │ match-events │ │ Current Score│
    └──────┬───────┘ └──────┬───────┘ └──────────────┘
           │                │
           │ notify()       │ publish()
           ▼                ▼
    ┌──────────────────────────────────┐
    │      FAN-OUT LAYER               │
    │                                  │
    │  ┌────────┐ ┌────────┐ ┌───────┐│
    │  │WebSocket│ │  Push  │ │  SMS  ││
    │  │ Server  │ │ Notif  │ │Gateway││
    │  └────┬───┘ └────┬───┘ └───┬───┘│
    └───────┼──────────┼─────────┼────┘
            │          │         │
            ▼          ▼         ▼
    ┌─────────────────────────────────┐
    │     10 MILLION CONCURRENT       │
    │          VIEWERS                │
    └─────────────────────────────────┘

    OBSERVER PATTERN CORE:
    ┌────────────────────────────────┐
    │  Match implements Subject      │
    │                                │
    │  List<Observer> observers      │
    │                                │
    │  void notifyObservers() {      │
    │    for (obs : observers) {     │
    │      obs.update(matchState)    │
    │    }                           │
    │  }                             │
    └────────────────────────────────┘
```

### **Why This Design?**

**You**: "Critical insight: This is a **massively read-heavy, write-light system**.

- **Writes**: ~1 update per ball (6 balls/over × ~20 overs = 120 updates per innings)
- **Reads**: 10 million concurrent viewers checking score every few seconds

**Solution**: 
1. **Observer Pattern** at the domain level - Match notifies all registered observers when state changes
2. **Fan-out via message queue** (Kafka) - Decouples score update from notification delivery
3. **Multiple notification channels** - WebSocket (web/app), Push (mobile), SMS (feature phones)
4. **Aggressive caching** - Current score cached in Redis, served without hitting DB"

---

## 2. API Design

### **2.1 Match & Score APIs**

```http
GET /api/v1/matches/live
Response: 200 OK
{
  "matches": [
    {
      "matchId": "match-1234",
      "team1": "India",
      "team2": "Australia",
      "status": "IN_PROGRESS",
      "currentScore": {
        "battingTeam": "India",
        "runs": 245,
        "wickets": 4,
        "overs": 38.2
      }
    }
  ]
}

---

GET /api/v1/matches/{matchId}/score
Response: 200 OK
{
  "matchId": "match-1234",
  "innings": 1,
  "battingTeam": "India",
  "score": {
    "runs": 245,
    "wickets": 4,
    "overs": "38.2",
    "runRate": 6.39,
    "requiredRunRate": null
  },
  "currentBatsmen": [
    {"name": "Virat Kohli", "runs": 89, "balls": 76, "fours": 8, "sixes": 2},
    {"name": "Rohit Sharma", "runs": 45, "balls": 38, "fours": 5, "sixes": 1}
  ],
  "currentBowler": {"name": "Pat Cummins", "overs": "7.2", "runs": 42, "wickets": 2},
  "lastBalls": ["1", "4", "W", "0", "2", "6"]  // Last 6 balls
}

---

POST /api/v1/matches/{matchId}/ball  (Admin/Scorer only)
Request:
{
  "over": 38,
  "ballNumber": 3,
  "runs": 4,
  "extras": null,
  "wicket": null,
  "batsmanOnStrike": "player-123",
  "bowler": "player-456"
}

Response: 200 OK
{
  "eventId": "event-9999",
  "updatedScore": {
    "runs": 249,
    "wickets": 4,
    "overs": "38.3"
  },
  "notificationsSent": 10234567  // Fanned out to subscribers
}
```

### **2.2 Real-Time Subscription APIs**

```http
GET /ws/matches/{matchId}/live  (WebSocket upgrade)
// Client subscribes to live updates

Server pushes:
{
  "type": "BALL_UPDATE",
  "matchId": "match-1234",
  "ball": {
    "over": 38,
    "ballNumber": 3,
    "runs": 4,
    "commentary": "FOUR! Kohli drives through covers"
  },
  "updatedScore": {"runs": 249, "wickets": 4, "overs": "38.3"}
}

---

POST /api/v1/users/{userId}/subscriptions
Request:
{
  "matchId": "match-1234",
  "notifyOn": ["WICKET", "BOUNDARY", "MILESTONE"]  // Selective notifications
}

Response: 200 OK
{
  "subscriptionId": "sub-5678"
}
```

### **Why This API Design?**

**You**: "Key decisions:
1. **WebSocket for real-time**: Persistent connection, server pushes updates (no polling!)
2. **Selective notifications**: Users can choose WICKET/BOUNDARY only (reduce notification fatigue)
3. **Separate scorer API**: Write path isolated from read path (different rate limits, auth)
4. **`lastBalls` array**: Quick visual for 'this over' - very common UI pattern"

---

## 3. ER Diagram & Database Design

```sql
CREATE TABLE matches (
    match_id VARCHAR(50) PRIMARY KEY,
    team1_id VARCHAR(50) NOT NULL,
    team2_id VARCHAR(50) NOT NULL,
    match_type VARCHAR(20),  -- TEST, ODI, T20
    status VARCHAR(20) DEFAULT 'SCHEDULED',
    venue VARCHAR(255),
    start_time TIMESTAMP,
    
    CHECK (status IN ('SCHEDULED', 'IN_PROGRESS', 'COMPLETED', 'ABANDONED'))
);

CREATE TABLE innings (
    innings_id VARCHAR(50) PRIMARY KEY,
    match_id VARCHAR(50) NOT NULL,
    innings_number INT NOT NULL,
    batting_team_id VARCHAR(50) NOT NULL,
    total_runs INT DEFAULT 0,
    total_wickets INT DEFAULT 0,
    total_overs DECIMAL(4,1) DEFAULT 0.0,
    
    FOREIGN KEY (match_id) REFERENCES matches(match_id),
    INDEX idx_match_id (match_id)
);

-- CRITICAL: Ball-by-ball event log (append-only, high write throughput)
CREATE TABLE ball_events (
    event_id VARCHAR(50) PRIMARY KEY,
    innings_id VARCHAR(50) NOT NULL,
    over_number INT NOT NULL,
    ball_number INT NOT NULL,
    batsman_id VARCHAR(50) NOT NULL,
    bowler_id VARCHAR(50) NOT NULL,
    runs INT DEFAULT 0,
    extras VARCHAR(20),  -- WIDE, NO_BALL, BYE, LEG_BYE
    wicket_type VARCHAR(20),  -- BOWLED, CAUGHT, LBW, RUN_OUT, etc.
    commentary TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (innings_id) REFERENCES innings(innings_id),
    INDEX idx_innings_over (innings_id, over_number, ball_number)
);

CREATE TABLE player_match_stats (
    player_id VARCHAR(50) NOT NULL,
    match_id VARCHAR(50) NOT NULL,
    runs_scored INT DEFAULT 0,
    balls_faced INT DEFAULT 0,
    fours INT DEFAULT 0,
    sixes INT DEFAULT 0,
    wickets_taken INT DEFAULT 0,
    overs_bowled DECIMAL(4,1) DEFAULT 0.0,
    
    PRIMARY KEY (player_id, match_id)
);
```

### **Why This Schema?**

**You**: "Key design:
1. **`ball_events` is append-only**: Every ball is a new row - immutable event log. Perfect for replay, undo (in case of umpire review reversals!).
2. **Denormalized current score**: `innings.total_runs` updated on every ball for fast reads. Don't recalculate from `ball_events` on every score check!
3. **`extras` and `wicket_type` nullable**: Most balls are neither - efficient storage."

---

## 4. Sequence Diagrams

### **4.1 Ball Update → Fan-out to Millions**

```
Scorer   MatchService   EventBus(Kafka)   NotificationWorkers   Redis Cache   10M Users
  │           │                │                   │                │            │
  │─POST ball─▶│               │                   │                │            │
  │           ├─updateScore────┼──────────────────────────────────▶│            │
  │           │  Redis: runs+=4                     │                │            │
  │           │                │                   │                │            │
  │           ├─publish(BallEvent)──▶│               │                │            │
  │           │                │  Partition by matchId              │            │
  │           │                ├─consume──────────▶│                │            │
  │           │                │                   │  Fan-out to:   │            │
  │           │                │                   │  - WebSocket connections     │
  │           │                │                   │  - Push notification service │
  │           │                │                   │  - SMS gateway (milestones) │
  │           │                │                   ├─────────────────────────▶│
  │◀ACK 200───│               │                   │                │            │
```

**You**: "This is the KEY architectural decision: **Kafka decouples score update from notification delivery**. If notification service is slow/down, score updates still succeed. Notifications catch up via consumer lag."

---

## 5. Scenario-First Explanations

### **5.1 Why Observer Pattern at Domain Level?**

**You**: "At the CODE level (not infra level), Match uses Observer Pattern:

```java
interface MatchObserver {
    void onBallUpdate(BallEvent event);
    void onWicket(WicketEvent event);
    void onInningsEnd(InningsEndEvent event);
}

class Match {
    private List<MatchObserver> observers = new ArrayList<>();
    
    void addObserver(MatchObserver observer) {
        observers.add(observer);
    }
    
    void recordBall(Ball ball) {
        // Update internal state
        currentInnings.addBall(ball);
        
        // Notify all observers
        BallEvent event = new BallEvent(this, ball);
        for (MatchObserver observer : observers) {
            observer.onBallUpdate(event);
        }
    }
}

// Concrete observers:
class ScoreCacheUpdater implements MatchObserver {
    public void onBallUpdate(BallEvent event) {
        redis.updateScore(event.getMatchId(), event.getNewScore());
    }
}

class NotificationPublisher implements MatchObserver {
    public void onBallUpdate(BallEvent event) {
        kafkaProducer.send("match-events", event);
    }
}

class StatsAggregator implements MatchObserver {
    public void onBallUpdate(BallEvent event) {
        playerStatsService.updateStats(event);
    }
}
```

**Why this matters**: Adding a new feature (e.g., 'Send Slack notification to premium users') = just add new Observer class. Zero changes to Match class! Open/Closed Principle in action."

### **5.2 Why Redis for Current Score?**

**You**: "Scenario: 10 million users refresh score simultaneously.

**Without cache**:
```sql
SELECT SUM(runs), COUNT(wicket_type) 
FROM ball_events 
WHERE innings_id = ?;
-- Aggregation query on potentially 300+ rows, run 10 million times/sec!
-- Database melts! 🔥
```

**With Redis cache**:
```java
class ScoreCacheService {
    void updateScore(String matchId, Score newScore) {
        redis.hset("match:" + matchId + ":score", Map.of(
            "runs", newScore.getRuns(),
            "wickets", newScore.getWickets(),
            "overs", newScore.getOvers()
        ));
        // O(1) write
    }
    
    Score getScore(String matchId) {
        Map<String, String> data = redis.hgetall("match:" + matchId + ":score");
        return Score.from(data);
        // O(1) read, sub-millisecond!
    }
}
```

**Numbers**: Redis handles 100,000+ reads/sec on single instance. 10M concurrent users with 5-second poll = 2M reads/sec → Need ~20 Redis replicas (read replicas), trivial to scale horizontally."

---

## 6. Cross Questions

**Interviewer**: "How do you handle 10 million WebSocket connections?"

**You**: "This requires **horizontal scaling with sticky sessions**:

```
Load Balancer (Layer 4 - TCP)
        │
        ├──▶ WebSocket Server 1 (100K connections)
        ├──▶ WebSocket Server 2 (100K connections)
        ├──▶ WebSocket Server 3 (100K connections)
        │        ... (100 servers total for 10M connections)
        
Each server subscribes to Kafka topic 'match-events'
When event arrives, server pushes to ITS connected clients only
```

**Implementation**:
```java
@ServerEndpoint("/ws/matches/{matchId}")
public class MatchWebSocketServer {
    private static Map<String, Set<Session>> matchSubscribers = new ConcurrentHashMap<>();
    
    @OnOpen
    public void onOpen(Session session, @PathParam("matchId") String matchId) {
        matchSubscribers.computeIfAbsent(matchId, k -> ConcurrentHashMap.newKeySet())
                       .add(session);
    }
    
    @KafkaListener(topics = "match-events")
    public void onMatchEvent(BallEvent event) {
        Set<Session> subscribers = matchSubscribers.get(event.getMatchId());
        if (subscribers != null) {
            String json = objectMapper.writeValueAsString(event);
            subscribers.parallelStream().forEach(session -> {
                if (session.isOpen()) {
                    session.getAsyncRemote().sendText(json);
                }
            });
        }
    }
}
```

**Key insight**: Each server only fans-out to ITS OWN connections. Kafka consumer group ensures all servers get every event (broadcast, not partition-based consumption for this use case)."

---

## 7. Trade-offs

### **7.1 WebSocket vs Polling vs SSE**

| Aspect | WebSocket | Polling | SSE |
|--------|-----------|---------|-----|
| **Server Load** | Low (push-based) | High (repeated requests) | Low |
| **Latency** | <100ms | 2-5 sec (poll interval) | <100ms |
| **Complexity** | High | Low | Medium |

**You**: "Cricbuzz uses **WebSocket primarily**, **polling fallback** for old browsers/networks that block WebSocket."

---

## 8. Senior Trap Questions

### **Trap: "Just use polling every 1 second, it's simple!"**

**❌ Junior**: "Polling is fine, just reduce interval."

**✅ Senior**: "At 10M users polling every 1 second = 10M requests/sec sustained load. Compare to WebSocket: 10M persistent connections (memory overhead) but ZERO repeated requests. 

**Math**:
- Polling: 10M req/sec × 200 bytes avg = 2GB/sec bandwidth
- WebSocket: Only send data on actual score change (~1 event per 30 seconds during play) = negligible bandwidth

**Real-world**: Cricbuzz reportedly handles 25M+ concurrent users during India matches. Pure polling would require insane infrastructure costs."

---

## 9. Technology Choices

### **9.1 Message Queue: Kafka vs Redis Pub/Sub**

**You**: "**Kafka** for match events (need replay for late-joining viewers - 'catch up' on missed balls). **Redis Pub/Sub** would lose messages if consumer momentarily disconnects - unacceptable for sports scores."

### **9.2 Database: Cassandra vs PostgreSQL for ball_events**

**You**: "For ball-by-ball events across THOUSANDS of matches happening historically, **Cassandra** wins:
- Write-heavy (append-only ball events)
- Time-series-like access pattern (by match, by over)
- Horizontal scalability for historical data (IPL alone = 74 matches/season × 300 balls = huge volume)

PostgreSQL for **current match state** (needs ACID for score consistency), Cassandra for **historical ball-by-ball archive**."

---

## 🎓 **Final Tips**

1. **Observer Pattern**: Nail the domain-level pattern (Match notifies observers)
2. **Fan-out Architecture**: Kafka + WebSocket servers for millions of concurrent users
3. **Cache-first reads**: Redis for current score, never query aggregate from event log
4. **Read-heavy system**: Emphasize 10,000:1 read-write ratio drives all design decisions

Good luck! This tests your understanding of **real-time systems at massive scale**. 🚀
