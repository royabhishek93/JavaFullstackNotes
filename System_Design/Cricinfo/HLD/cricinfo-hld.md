# Cricinfo (Live Cricket Scores & Stats) - High Level Design

## System Overview

A comprehensive cricket information platform like ESPNCricinfo that provides live ball-by-ball commentary, real-time scores, detailed player and team statistics, match schedules, historical data, news articles, video highlights, fantasy cricket integration, and push notifications for major events. The system must handle millions of concurrent users during popular matches (World Cup finals, IPL matches), deliver live updates with minimal latency (< 2 seconds), maintain accurate historical statistics for thousands of players and teams, support complex querying and analytics, and scale globally across multiple time zones.

## Requirements

### Functional Requirements

1. **Live Match Coverage**
   - Ball-by-ball commentary and scoring
   - Real-time score updates
   - Live match statistics (run rate, partnerships, fall of wickets)
   - Video highlights integration
   - Audio commentary streaming

2. **Match Management**
   - Schedule and manage matches
   - Multiple formats (Test, ODI, T20, franchise leagues)
   - Tournament brackets and standings
   - Match results and summaries

3. **Player & Team Statistics**
   - Comprehensive player profiles (batting avg, bowling avg, career stats)
   - Team rankings and statistics
   - Head-to-head comparisons
   - Historical records and milestones

4. **Content Management**
   - News articles and editorials
   - Expert analysis and opinions
   - Photo galleries
   - Video highlights and clips

5. **User Features**
   - Personalized feed (favorite teams/players)
   - Match alerts and notifications
   - Fantasy cricket integration
   - Social features (comments, reactions)

6. **Search & Discovery**
   - Search matches, players, teams
   - Advanced statistics filtering
   - Historical match archives

### Non-Functional Requirements

1. **Performance**
   - Live score latency < 2 seconds
   - Handle 10M concurrent users during major matches
   - API response time < 200ms (p95)
   - Search query response < 500ms

2. **Scalability**
   - Support 50K+ matches per year
   - Store statistics for 100K+ players
   - Handle 1000+ concurrent live matches
   - Scale to billions of ball-by-ball records

3. **Availability**
   - 99.95% uptime
   - Zero data loss for live matches
   - Graceful degradation during overload

4. **Consistency**
   - Strong consistency for live scores
   - Eventual consistency for statistics and rankings
   - Real-time updates across all clients

5. **Latency**
   - Live updates propagated to all users within 2 seconds
   - CDN-cached content served within 100ms globally

## Capacity Estimation

### Traffic Estimates

**Assumptions:**
- Total users: 100 million registered
- Daily Active Users (DAU): 20 million
- Peak concurrent users (major match): 10 million
- Average session duration: 20 minutes
- Matches per day: ~50 (across all formats and leagues)
- Major event concurrent users: 10M
- Regular match concurrent users: 100K

**Calculations:**

**Read Operations (Queries Per Second):**
- Score checks: 20M DAU * 30 checks/day / 86400 = ~7,000 QPS (average)
- During major match: 10M users * 1 check/minute / 60 = ~167K QPS (peak)
- Commentary/ball updates: 10M * 1 update/minute / 60 = ~167K QPS (peak)
- Stats/player pages: 20M * 5 views/day / 86400 = ~1,200 QPS
- News articles: 20M * 10 views/day / 86400 = ~2,300 QPS

**Total peak QPS: ~350K QPS (during World Cup final)**

**Write Operations:**
- Ball-by-ball updates: 50 matches * 600 balls/match / 21600s (6 hours) = ~1.4 writes/second
- During peak (100 concurrent matches): ~14 writes/second
- Statistics updates: Batch updates every 5 minutes = ~1-2 writes/second
- News articles: ~50 articles/day = ~0.001 writes/second

**Total writes: ~20 writes/second (manageable)**

### Storage Estimates

**Matches:**
- Historical matches: 500K matches
- Match metadata: ~10KB per match = 5GB
- Ball-by-ball data: 500K matches * 600 balls * 500 bytes = 150GB
- Commentary: 500K * 100KB = 50GB
- Total match data: ~205GB

**Players:**
- Total players: 100K
- Player profile: ~20KB per player = 2GB
- Career statistics: 100K * 10KB = 1GB
- Total player data: ~3GB

**Statistics & Aggregations:**
- Team statistics: 50 teams * 50KB = 2.5MB
- Rankings history: ~100MB
- Historical aggregations: ~500GB

**Media:**
- Images: 10M images * 200KB = 2TB
- Video highlights: 100K videos * 50MB = 5TB
- Total media: ~7TB

**News & Articles:**
- Articles: 1M articles * 50KB = 50GB
- Comments: 100M comments * 500 bytes = 50GB
- Total content: ~100GB

**Total Storage: ~8TB (primary data)**
**With replicas and backups: ~25TB**

**Growth:** ~2TB per year (new matches, media)

### Bandwidth Estimates

**Incoming:**
- Ball-by-ball updates: 14 updates/s * 1KB = 14 KB/s
- News/content uploads: ~100 KB/s
- Total incoming: ~120 KB/s (~1 Mbps)

**Outgoing:**
- Live score updates: 167K QPS * 2KB = 334 MB/s (peak)
- Commentary feed: 167K QPS * 5KB = 835 MB/s (peak)
- Images (via CDN): 1000 QPS * 200KB = 200 MB/s
- Video (via CDN): 500 streams * 2 Mbps = 1 Gbps
- Stats pages: 1200 QPS * 50KB = 60 MB/s

**Total outgoing: ~2.5 GB/s peak (~20 Gbps)**

**CDN offloads:** ~90% of static content
**Origin servers:** ~2.5 Gbps peak

## System Architecture

```
                                    [DNS]
                                      |
                              [CDN - CloudFlare]
                            (Images, videos, static content)
                                      |
                             [Global Load Balancer]
                           (GeoDNS, DDoS protection)
                                      |
                    +------------------+------------------+
                    |                                     |
              [Web Clients]                        [Mobile Apps]
                    |                                     |
                    +------------------+------------------+
                                      |
                               [API Gateway]
                          (Rate limit, Auth, Caching)
                                      |
        +--------------+-------------+---------------+-------------+
        |              |             |               |             |
   [Live Score   [Match        [Player/Team   [Content      [Notification
    Service]     Service]       Stats Service]  Service]     Service]
        |              |             |               |             |
        +-----+--------+-------------+---------------+-------------+
              |                      |
        [Message Queue - Kafka]  [Search Service]
        Topics: live-updates,    (Elasticsearch)
        stats-updates,           Player/Match/News search
        notifications
              |
        +-----+--------+-------------+---------------+-------------+
        |              |             |               |             |
   [Stats      [Ranking      [Analytics    [Media        [Push
   Aggregator]  Service]       Service]     Service]     Gateway]
        |              |             |               |
        +-----+--------+-------------+---------------+
                       |
        +--------------+----------------+--------------+
        |              |                |              |
   [PostgreSQL    [Redis Cache]    [MongoDB]     [InfluxDB]
   (Matches,      (Live scores,    (Ball-by-ball  (Time-series
   Players,       real-time data)  commentary,    metrics,
   Teams)]                         flexible docs) analytics)]
        |                                              |
   [Read Replicas]                              [S3/Object Store]
   (For analytics                               (Videos, images,
   and reporting)                               match archives)
                                                      |
                                                  [CDN Edge]
```

## Core Components

### 1. Live Score Service

**Responsibilities:**
- Ingest ball-by-ball updates from data entry operators
- Validate and process score updates
- Calculate derived metrics (run rate, required run rate, etc.)
- Publish updates to message queue
- Maintain current match state in Redis

**Data Entry Flow:**
```
Data Entry Operator → Admin Panel → Live Score Service → Kafka → Redis + DB
                                                              ↓
                                                        Subscribers
                                                    (Web, Mobile, WebSocket)
```

**Match State in Redis:**
```json
{
  "match_id": "IND_vs_AUS_2026_T20_Final",
  "status": "LIVE",
  "current_over": 15.3,
  "batting_team": "IND",
  "bowling_team": "AUS",
  "score": {
    "IND": {"runs": 142, "wickets": 3, "overs": 15.3},
    "AUS": {"runs": 0, "wickets": 0, "overs": 0}
  },
  "current_batsmen": [
    {"player_id": "V_KOHLI", "runs": 62, "balls": 41, "fours": 6, "sixes": 2},
    {"player_id": "S_IYER", "runs": 15, "balls": 12, "fours": 2, "sixes": 0}
  ],
  "current_bowler": {
    "player_id": "M_STARC", "overs": 3.3, "runs": 28, "wickets": 1, "economy": 8.24
  },
  "recent_overs": [...],
  "last_ball": {
    "ball_number": "15.3",
    "runs": 4,
    "type": "FOUR",
    "commentary": "Kohli pulls it magnificently through mid-wicket!"
  },
  "updated_at": 1712345678
}
```

**Caching Strategy:**
- Live match data in Redis with 2-hour TTL
- Auto-expire after match ends
- Fallback to PostgreSQL for historical data

### 2. Match Service

**Responsibilities:**
- Match CRUD operations
- Schedule management
- Match fixtures and results
- Tournament management
- Team lineups and playing XI

**API Endpoints:**
```
GET /api/v1/matches/live
GET /api/v1/matches/upcoming
GET /api/v1/matches/{matchId}
GET /api/v1/matches/{matchId}/scorecard
GET /api/v1/tournaments/{tournamentId}/standings
```

### 3. Player & Team Statistics Service

**Responsibilities:**
- Maintain player career statistics
- Calculate batting/bowling averages
- Update rankings
- Generate player comparisons
- Historical performance analysis

**Statistics Calculation:**
```python
# Batting Statistics
batting_avg = total_runs / dismissals
strike_rate = (total_runs / balls_faced) * 100
centuries = count(scores >= 100)
fifties = count(scores >= 50 and scores < 100)

# Bowling Statistics
bowling_avg = runs_conceded / wickets_taken
economy_rate = runs_conceded / overs_bowled
strike_rate = balls_bowled / wickets_taken
```

**Ranking Algorithm (ICC Rankings):**
```
Player Rating = (Runs scored * Weight) + (Wickets taken * Weight) - (Runs conceded * Penalty)
Weight based on:
- Opposition strength
- Home/away factor
- Match result
- Recent form (exponential decay over 2-3 years)
```

### 4. Real-Time Update Service (WebSocket)

**Responsibilities:**
- Maintain WebSocket connections with clients
- Subscribe to Kafka topics for live updates
- Push updates to connected clients
- Handle connection management and reconnection

**Architecture:**
```
Kafka (live-updates topic) → WebSocket Servers (cluster) → Clients

WebSocket Server:
- Manages ~100K connections per server
- Subscribes to Kafka topic
- Filters updates by match_id
- Pushes to subscribed clients

Client subscribes:
ws://api.cricinfo.com/live/{match_id}

Server pushes:
{
  "event": "BALL_UPDATE",
  "match_id": "IND_vs_AUS_2026_T20_Final",
  "over": 15.3,
  "runs": 4,
  "type": "FOUR",
  "batsman": "V_KOHLI",
  "score": {"IND": {"runs": 142, "wickets": 3}}
}
```

### 5. Search Service (Elasticsearch)

**Responsibilities:**
- Full-text search for players, teams, matches
- Advanced filtering (date ranges, formats, venues)
- Autocomplete suggestions
- Faceted search

**Indexed Data:**
```json
// Player Index
{
  "player_id": "V_KOHLI",
  "name": "Virat Kohli",
  "country": "India",
  "role": "Batsman",
  "batting_style": "Right-hand bat",
  "bowling_style": "Right-arm medium",
  "career_stats": {
    "matches": 500,
    "runs": 25000,
    "average": 52.5,
    "centuries": 75
  }
}

// Match Index
{
  "match_id": "IND_vs_AUS_2026_T20_Final",
  "teams": ["India", "Australia"],
  "venue": "Melbourne Cricket Ground",
  "date": "2026-11-15",
  "format": "T20",
  "tournament": "ICC T20 World Cup 2026",
  "result": "India won by 7 runs"
}
```

### 6. Notification Service

**Responsibilities:**
- Push notifications for match events (wickets, centuries, match start)
- Email notifications for news and updates
- SMS alerts for subscribed users
- User preference management

**Event Triggers:**
- Wicket fallen
- Century/Half-century scored
- Match start/end
- Close finish (last over)
- Favorite team/player milestone

**Technology:** Firebase Cloud Messaging (FCM), AWS SNS, Twilio

### 7. Content Service

**Responsibilities:**
- News article management
- Editorial content
- Photo galleries
- Video highlights
- Content categorization and tagging

**Content Storage:**
- Metadata in PostgreSQL
- Full text in PostgreSQL or MongoDB
- Images/videos in S3 with CDN

### 8. Analytics Service

**Responsibilities:**
- Match statistics aggregation
- Trend analysis
- Predictive analytics (win probability, player form)
- Historical comparisons
- Data visualization

**Metrics:**
- Real-time win probability
- Batsman form curve
- Bowler effectiveness over
- Pitch behavior analysis

### 9. Fantasy Cricket Integration

**Responsibilities:**
- Player performance scoring
- Fantasy points calculation
- Leaderboard management
- Contest management

**Fantasy Points:**
```
Batting: 1 run = 1 point, boundary = 1 bonus, six = 2 bonus
Bowling: 1 wicket = 25 points, maiden = 12 points
Fielding: 1 catch = 8 points, stumping = 12 points, run-out = 6 points
Bonus: Century = 16, Half-century = 8, 4 wickets = 16, 5 wickets = 32
```

## Database Schema

### Matches Table

```sql
CREATE TABLE matches (
    match_id VARCHAR(100) PRIMARY KEY,
    match_number INT,
    tournament_id VARCHAR(50),
    format VARCHAR(10), -- 'TEST', 'ODI', 'T20'
    venue_id INT REFERENCES venues(venue_id),
    match_date DATE,
    team1_id INT REFERENCES teams(team_id),
    team2_id INT REFERENCES teams(team_id),
    toss_winner_id INT,
    toss_decision VARCHAR(10), -- 'BAT', 'BOWL'
    match_status VARCHAR(20), -- 'SCHEDULED', 'LIVE', 'COMPLETED', 'ABANDONED'
    winning_team_id INT,
    result VARCHAR(255),
    match_type VARCHAR(50), -- 'INTERNATIONAL', 'DOMESTIC', 'LEAGUE'
    season VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_date (match_date DESC),
    INDEX idx_tournament (tournament_id, match_date),
    INDEX idx_status (match_status, match_date)
);
```

### Innings Table

```sql
CREATE TABLE innings (
    innings_id BIGSERIAL PRIMARY KEY,
    match_id VARCHAR(100) REFERENCES matches(match_id),
    innings_number INT, -- 1, 2, 3, 4 (for Test matches)
    batting_team_id INT REFERENCES teams(team_id),
    bowling_team_id INT REFERENCES teams(team_id),
    total_runs INT,
    total_wickets INT,
    total_overs DECIMAL(4,1),
    extras INT,
    declared BOOLEAN DEFAULT FALSE,
    all_out BOOLEAN DEFAULT FALSE,
    INDEX idx_match (match_id, innings_number)
);
```

### Ball By Ball Table (MongoDB for flexibility)

```javascript
// MongoDB Collection: ball_by_ball
{
  "_id": ObjectId("..."),
  "match_id": "IND_vs_AUS_2026_T20_Final",
  "innings": 1,
  "over": 15.3,
  "ball_number": 93,
  "batsman_id": "V_KOHLI",
  "non_striker_id": "S_IYER",
  "bowler_id": "M_STARC",
  "runs_scored": 4,
  "extras": 0,
  "extras_type": null, // 'WIDE', 'NO_BALL', 'BYE', 'LEG_BYE'
  "is_wicket": false,
  "wicket_type": null, // 'BOWLED', 'CAUGHT', 'LBW', 'RUN_OUT', etc.
  "fielder_id": null,
  "shot_type": "PULL",
  "shot_zone": "MID_WICKET",
  "commentary": "Kohli pulls it magnificently through mid-wicket!",
  "ball_speed_kmph": 142.5,
  "ball_type": "GOOD_LENGTH",
  "timestamp": ISODate("2026-11-15T19:45:32Z"),
  "metadata": {
    "score_at_ball": {"runs": 142, "wickets": 3},
    "partnership": 45,
    "required_run_rate": 8.5
  }
}

// Indexes
db.ball_by_ball.createIndex({"match_id": 1, "innings": 1, "over": 1})
db.ball_by_ball.createIndex({"batsman_id": 1, "timestamp": -1})
db.ball_by_ball.createIndex({"bowler_id": 1, "timestamp": -1})
```

### Players Table

```sql
CREATE TABLE players (
    player_id VARCHAR(50) PRIMARY KEY,
    full_name VARCHAR(255) NOT NULL,
    country VARCHAR(50),
    date_of_birth DATE,
    role VARCHAR(50), -- 'BATSMAN', 'BOWLER', 'ALL_ROUNDER', 'WICKET_KEEPER'
    batting_style VARCHAR(50), -- 'Right-hand bat', 'Left-hand bat'
    bowling_style VARCHAR(100), -- 'Right-arm fast', 'Left-arm spin', etc.
    profile_image_url VARCHAR(500),
    is_active BOOLEAN DEFAULT TRUE,
    debut_date DATE,
    retired_date DATE,
    jersey_number INT,
    height_cm INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_name (full_name),
    INDEX idx_country (country, is_active)
);
```

### Player Statistics Table (Aggregated)

```sql
CREATE TABLE player_statistics (
    stat_id BIGSERIAL PRIMARY KEY,
    player_id VARCHAR(50) REFERENCES players(player_id),
    format VARCHAR(10), -- 'TEST', 'ODI', 'T20'
    match_type VARCHAR(20), -- 'INTERNATIONAL', 'DOMESTIC', 'ALL'
    
    -- Batting Stats
    matches_played INT DEFAULT 0,
    innings_batted INT DEFAULT 0,
    runs_scored INT DEFAULT 0,
    highest_score INT DEFAULT 0,
    batting_average DECIMAL(6,2),
    strike_rate DECIMAL(6,2),
    centuries INT DEFAULT 0,
    half_centuries INT DEFAULT 0,
    fours INT DEFAULT 0,
    sixes INT DEFAULT 0,
    
    -- Bowling Stats
    innings_bowled INT DEFAULT 0,
    balls_bowled INT DEFAULT 0,
    runs_conceded INT DEFAULT 0,
    wickets_taken INT DEFAULT 0,
    bowling_average DECIMAL(6,2),
    economy_rate DECIMAL(4,2),
    bowling_strike_rate DECIMAL(6,2),
    five_wickets INT DEFAULT 0,
    ten_wickets INT DEFAULT 0,
    
    -- Fielding Stats
    catches INT DEFAULT 0,
    stumpings INT DEFAULT 0,
    run_outs INT DEFAULT 0,
    
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (player_id, format, match_type),
    INDEX idx_player_format (player_id, format)
);
```

### Teams Table

```sql
CREATE TABLE teams (
    team_id SERIAL PRIMARY KEY,
    team_name VARCHAR(255) NOT NULL,
    short_name VARCHAR(10),
    country VARCHAR(50),
    team_type VARCHAR(20), -- 'NATIONAL', 'FRANCHISE', 'CLUB'
    logo_url VARCHAR(500),
    home_ground VARCHAR(255),
    captain_id VARCHAR(50) REFERENCES players(player_id),
    coach VARCHAR(255),
    founded_year INT,
    is_active BOOLEAN DEFAULT TRUE,
    INDEX idx_country (country),
    INDEX idx_name (team_name)
);
```

### Venues Table

```sql
CREATE TABLE venues (
    venue_id SERIAL PRIMARY KEY,
    venue_name VARCHAR(255) NOT NULL,
    city VARCHAR(100),
    country VARCHAR(50),
    capacity INT,
    pitch_type VARCHAR(50), -- 'BATTING_FRIENDLY', 'BOWLING_FRIENDLY', 'BALANCED'
    timezone VARCHAR(50),
    latitude DECIMAL(9,6),
    longitude DECIMAL(9,6),
    established_year INT,
    INDEX idx_country_city (country, city)
);
```

### Rankings Table

```sql
CREATE TABLE rankings (
    ranking_id BIGSERIAL PRIMARY KEY,
    entity_type VARCHAR(20), -- 'PLAYER', 'TEAM'
    entity_id VARCHAR(50), -- player_id or team_id
    format VARCHAR(10), -- 'TEST', 'ODI', 'T20'
    category VARCHAR(20), -- 'BATTING', 'BOWLING', 'ALL_ROUNDER'
    rank INT,
    rating INT,
    ranking_date DATE,
    INDEX idx_entity_date (entity_type, entity_id, ranking_date DESC),
    INDEX idx_rank (format, category, rank)
);
```

### News Articles Table

```sql
CREATE TABLE articles (
    article_id BIGSERIAL PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    slug VARCHAR(500) UNIQUE,
    author_id INT,
    category VARCHAR(50), -- 'NEWS', 'ANALYSIS', 'OPINION', 'INTERVIEW'
    content TEXT,
    excerpt TEXT,
    featured_image_url VARCHAR(500),
    published_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    view_count BIGINT DEFAULT 0,
    is_featured BOOLEAN DEFAULT FALSE,
    tags TEXT[], -- Array of tags
    related_match_ids TEXT[],
    related_player_ids TEXT[],
    INDEX idx_published (published_at DESC),
    INDEX idx_category (category, published_at DESC),
    INDEX idx_slug (slug)
);
```

## API Design

### Live Matches

```
GET /api/v1/matches/live

Response: 200 OK
{
  "matches": [
    {
      "match_id": "IND_vs_AUS_2026_T20_Final",
      "format": "T20",
      "tournament": "ICC T20 World Cup 2026",
      "venue": "Melbourne Cricket Ground",
      "match_date": "2026-11-15",
      "status": "LIVE",
      "teams": {
        "team1": {
          "team_id": 1,
          "name": "India",
          "short_name": "IND",
          "score": {"runs": 142, "wickets": 3, "overs": 15.3}
        },
        "team2": {
          "team_id": 2,
          "name": "Australia",
          "short_name": "AUS",
          "score": {"runs": 0, "wickets": 0, "overs": 0}
        }
      },
      "current_state": {
        "batting_team": "IND",
        "current_over": 15.3,
        "run_rate": 9.2,
        "required_run_rate": null
      },
      "toss": {
        "winner": "India",
        "decision": "BAT"
      }
    }
  ]
}
```

### Match Details

```
GET /api/v1/matches/{matchId}

Response: 200 OK
{
  "match_id": "IND_vs_AUS_2026_T20_Final",
  "match_number": 45,
  "format": "T20",
  "tournament": {
    "tournament_id": "T20WC_2026",
    "name": "ICC T20 World Cup 2026",
    "season": "2026"
  },
  "venue": {
    "venue_id": 10,
    "name": "Melbourne Cricket Ground",
    "city": "Melbourne",
    "country": "Australia",
    "capacity": 100024
  },
  "match_date": "2026-11-15T19:00:00Z",
  "status": "LIVE",
  "toss": {
    "winner": "India",
    "decision": "BAT"
  },
  "teams": {
    "team1": {...},
    "team2": {...}
  },
  "innings": [
    {
      "innings_number": 1,
      "batting_team": "India",
      "bowling_team": "Australia",
      "total_runs": 142,
      "total_wickets": 3,
      "total_overs": 15.3,
      "run_rate": 9.2
    }
  ],
  "current_partnership": {
    "batsmen": [
      {
        "player_id": "V_KOHLI",
        "name": "Virat Kohli",
        "runs": 62,
        "balls": 41,
        "fours": 6,
        "sixes": 2,
        "strike_rate": 151.2,
        "on_strike": true
      },
      {
        "player_id": "S_IYER",
        "name": "Shreyas Iyer",
        "runs": 15,
        "balls": 12,
        "fours": 2,
        "sixes": 0,
        "strike_rate": 125.0,
        "on_strike": false
      }
    ],
    "partnership_runs": 45,
    "partnership_balls": 28
  },
  "current_bowler": {
    "player_id": "M_STARC",
    "name": "Mitchell Starc",
    "overs": 3.3,
    "maidens": 0,
    "runs": 28,
    "wickets": 1,
    "economy": 8.24
  },
  "recent_balls": [
    {"over": 15.3, "runs": 4, "type": "FOUR"},
    {"over": 15.2, "runs": 1, "type": "SINGLE"},
    {"over": 15.1, "runs": 6, "type": "SIX"}
  ]
}
```

### Ball-by-Ball Commentary

```
GET /api/v1/matches/{matchId}/commentary?over=15

Response: 200 OK
{
  "match_id": "IND_vs_AUS_2026_T20_Final",
  "innings": 1,
  "over": 15,
  "balls": [
    {
      "ball": 15.1,
      "batsman": "Virat Kohli",
      "bowler": "Mitchell Starc",
      "runs": 6,
      "type": "SIX",
      "commentary": "Kohli dances down the track and smashes it over long-on! Massive hit!",
      "timestamp": "2026-11-15T19:45:30Z"
    },
    {
      "ball": 15.2,
      "batsman": "Virat Kohli",
      "bowler": "Mitchell Starc",
      "runs": 1,
      "type": "SINGLE",
      "commentary": "Good length delivery, Kohli taps it to mid-off and takes a quick single.",
      "timestamp": "2026-11-15T19:45:55Z"
    }
  ]
}
```

### Player Statistics

```
GET /api/v1/players/{playerId}/statistics?format=T20

Response: 200 OK
{
  "player_id": "V_KOHLI",
  "full_name": "Virat Kohli",
  "country": "India",
  "role": "BATSMAN",
  "statistics": {
    "format": "T20",
    "batting": {
      "matches": 115,
      "innings": 110,
      "runs": 4008,
      "highest_score": 122,
      "average": 52.73,
      "strike_rate": 137.96,
      "centuries": 1,
      "half_centuries": 37,
      "fours": 325,
      "sixes": 117
    },
    "bowling": {
      "matches": 115,
      "innings": 7,
      "wickets": 4,
      "average": 64.25,
      "economy": 8.03,
      "strike_rate": 48.0
    },
    "fielding": {
      "catches": 58,
      "run_outs": 12
    }
  },
  "recent_form": [
    {"match_id": "...", "runs": 82, "balls": 53, "date": "2026-11-10"},
    {"match_id": "...", "runs": 64, "balls": 48, "date": "2026-11-08"}
  ],
  "milestones": [
    "Fastest to 3000 T20I runs",
    "Most runs in T20 World Cups"
  ]
}
```

### Search API

```
GET /api/v1/search?q=kohli&type=player

Response: 200 OK
{
  "results": [
    {
      "type": "PLAYER",
      "player_id": "V_KOHLI",
      "name": "Virat Kohli",
      "country": "India",
      "role": "BATSMAN",
      "profile_image_url": "...",
      "relevance_score": 0.95
    }
  ],
  "total_results": 1
}

GET /api/v1/search?q=india+australia&type=match&dateFrom=2026-01-01

Response: 200 OK
{
  "results": [
    {
      "type": "MATCH",
      "match_id": "IND_vs_AUS_2026_T20_Final",
      "teams": ["India", "Australia"],
      "venue": "Melbourne Cricket Ground",
      "date": "2026-11-15",
      "format": "T20",
      "result": "LIVE"
    }
  ],
  "total_results": 15
}
```

### WebSocket Live Updates

```
// Connect to WebSocket
ws://api.cricinfo.com/live/{match_id}

// Server sends updates
{
  "event": "BALL_UPDATE",
  "match_id": "IND_vs_AUS_2026_T20_Final",
  "ball": {
    "over": 15.3,
    "batsman": "Virat Kohli",
    "bowler": "Mitchell Starc",
    "runs": 4,
    "type": "FOUR",
    "commentary": "Kohli pulls it magnificently through mid-wicket!"
  },
  "score": {
    "IND": {"runs": 142, "wickets": 3, "overs": 15.3}
  },
  "timestamp": "2026-11-15T19:45:32Z"
}

{
  "event": "WICKET",
  "match_id": "IND_vs_AUS_2026_T20_Final",
  "wicket": {
    "batsman": "Shreyas Iyer",
    "dismissal_type": "CAUGHT",
    "fielder": "Glenn Maxwell",
    "bowler": "Mitchell Starc",
    "runs": 15,
    "balls": 12
  },
  "score": {
    "IND": {"runs": 142, "wickets": 4, "overs": 15.5}
  }
}

{
  "event": "MILESTONE",
  "match_id": "IND_vs_AUS_2026_T20_Final",
  "milestone": {
    "type": "CENTURY",
    "player": "Virat Kohli",
    "runs": 100,
    "balls": 58
  }
}
```

## Scalability Strategies

### 1. Read-Heavy Optimization

**Challenge:** Live matches generate 350K QPS during major events

**Solutions:**

**Multi-Layer Caching:**
```
Layer 1: CDN (CloudFlare)
- Static content (images, videos, CSS, JS)
- Cache TTL: 24 hours
- Reduces 90% of static requests

Layer 2: Redis (In-memory cache)
- Live match data: TTL 5 seconds
- Player statistics: TTL 5 minutes
- Match schedules: TTL 10 minutes
- Rankings: TTL 30 minutes

Layer 3: Database Read Replicas
- 5 read replicas for PostgreSQL
- Route read queries to replicas
- Geographic distribution (US, EU, Asia)

Layer 4: Application-level caching
- In-process cache for frequently accessed data
- LRU cache with 1000 entries
```

**Redis Caching Strategy:**
```python
def get_live_match_score(match_id):
    cache_key = f"live:match:{match_id}"
    
    # Try to get from cache
    cached_data = redis.get(cache_key)
    if cached_data:
        return json.loads(cached_data)
    
    # Cache miss - fetch from database
    match_data = db.query("""
        SELECT * FROM matches WHERE match_id = %s
    """, (match_id,))
    
    # Store in cache with 5-second TTL
    redis.setex(cache_key, 5, json.dumps(match_data))
    
    return match_data
```

### 2. Real-Time Updates with WebSocket

**Challenge:** Push updates to 10M concurrent users

**Solution: Fan-out Architecture**

```
Data Entry → Live Score Service → Kafka Topic → WebSocket Cluster → Clients

WebSocket Cluster:
- 100 WebSocket servers
- Each handles 100K connections = 10M total
- Subscribe to Kafka topic
- Filter by match_id
- Push to subscribed clients

Load Balancing:
- Sticky sessions based on user_id hash
- If server fails, reconnect to another server
- Auto-scaling based on connection count
```

**WebSocket Server Implementation:**
```python
class WebSocketServer:
    def __init__(self):
        self.connections = {}  # {match_id: [websocket1, websocket2, ...]}
        self.kafka_consumer = KafkaConsumer('live-updates')
    
    async def handle_connection(self, websocket, match_id):
        # Add connection to pool
        if match_id not in self.connections:
            self.connections[match_id] = []
        self.connections[match_id].append(websocket)
        
        # Send current match state
        current_state = get_live_match_score(match_id)
        await websocket.send(json.dumps(current_state))
        
        # Keep connection alive
        try:
            await websocket.wait_closed()
        finally:
            self.connections[match_id].remove(websocket)
    
    async def consume_updates(self):
        # Consume from Kafka and broadcast
        async for message in self.kafka_consumer:
            update = json.loads(message.value)
            match_id = update['match_id']
            
            # Broadcast to all subscribed clients
            if match_id in self.connections:
                tasks = [
                    ws.send(json.dumps(update))
                    for ws in self.connections[match_id]
                ]
                await asyncio.gather(*tasks, return_exceptions=True)
```

### 3. Database Partitioning

**Matches Table: Partition by Year**
```sql
CREATE TABLE matches (
    ...
) PARTITION BY RANGE (EXTRACT(YEAR FROM match_date));

CREATE TABLE matches_2024 PARTITION OF matches
    FOR VALUES FROM (2024) TO (2025);

CREATE TABLE matches_2025 PARTITION OF matches
    FOR VALUES FROM (2025) TO (2026);

CREATE TABLE matches_2026 PARTITION OF matches
    FOR VALUES FROM (2026) TO (2027);
```

**Ball-by-Ball Data: Sharding by match_id**
```
MongoDB Sharding:
- Shard key: match_id (hashed)
- 10 shards for distribution
- Each shard handles ~10% of matches
- Recent matches on SSD, historical on HDD
```

### 4. Search Optimization (Elasticsearch)

**Index Strategy:**
```
Indices:
- players (100K documents)
- matches (500K documents)
- articles (1M documents)

Sharding:
- Players: 2 shards, 1 replica
- Matches: 5 shards, 1 replica
- Articles: 5 shards, 1 replica

Optimization:
- Use filters instead of queries where possible
- Aggregate statistics at indexing time
- Use completion suggester for autocomplete
- Cache frequent queries
```

### 5. Media Delivery via CDN

**Strategy:**
```
S3 (Origin) → CloudFront (CDN) → Users

Image Processing:
- Generate multiple sizes on upload
- Lazy loading with progressive JPEGs
- WebP format for modern browsers
- Fallback to JPEG for older browsers

Video Delivery:
- Adaptive bitrate streaming (HLS/DASH)
- Multiple quality levels (360p, 480p, 720p, 1080p)
- CDN edge caching
- Geo-routing to nearest edge

Optimization:
- Pre-sign S3 URLs for security
- Set aggressive cache headers (1 year for immutable assets)
- Use CloudFront Lambda@Edge for image resizing on-the-fly
```

### 6. Analytics & Reporting

**Time-Series Data (InfluxDB):**
```
Measurements:
- match_metrics (run rate, wickets, partnerships)
- player_performance (runs per over, strike rate trends)
- user_engagement (page views, live viewers)

Retention Policies:
- Raw data: 30 days
- 1-minute aggregates: 1 year
- 1-hour aggregates: 5 years
- 1-day aggregates: Forever

Query Example:
SELECT mean(run_rate), max(run_rate)
FROM match_metrics
WHERE match_id = 'IND_vs_AUS_2026_T20_Final'
AND time > now() - 3h
GROUP BY time(10m)
```

## Technology Stack

| Component | Technology | Justification |
|-----------|-----------|---------------|
| **Frontend** | React + Next.js | SSR for SEO, fast page loads |
| **Mobile** | React Native / Flutter | Cross-platform mobile apps |
| **API Gateway** | Kong / AWS API Gateway | Rate limiting, caching, auth |
| **Backend Services** | Node.js / Go / Java Spring Boot | High concurrency, mature ecosystem |
| **Primary Database** | PostgreSQL 14+ | ACID, complex queries, JSON support |
| **Document Store** | MongoDB | Flexible schema for ball-by-ball data |
| **Cache** | Redis Cluster | In-memory speed, distributed locks |
| **Search** | Elasticsearch | Full-text search, analytics |
| **Time-Series DB** | InfluxDB | Optimized for metrics and analytics |
| **Message Queue** | Apache Kafka | High throughput, event streaming |
| **WebSocket** | Socket.io / uWebSockets | Real-time bidirectional communication |
| **Object Storage** | AWS S3 / Google Cloud Storage | Media files, backups |
| **CDN** | CloudFlare / AWS CloudFront | Global edge caching |
| **Monitoring** | Prometheus + Grafana | Metrics and dashboards |
| **Logging** | ELK Stack (Elasticsearch, Logstash, Kibana) | Centralized logging |
| **Container Orchestration** | Kubernetes | Auto-scaling, self-healing |
| **Load Balancer** | Nginx / AWS ALB | Layer 7 load balancing |

## Interview Q&A

### Question 1: How do you ensure live score updates reach all users within 2 seconds during a World Cup final with 10M concurrent users?

**Answer:**

**Multi-Tier Architecture with Kafka + WebSocket:**

```
Data Entry Operator → Live Score Service → Kafka → WebSocket Cluster → 10M Clients

Breakdown:
1. Data Entry: ~1 second (operator enters score)
2. Kafka Publish: ~10ms (message to Kafka topic)
3. Kafka to WebSocket Servers: ~50ms (100 servers consume message)
4. WebSocket Broadcast: ~500ms (broadcast to 100K clients per server)

Total: ~1.5 seconds (well within 2-second target)
```

**Implementation:**

```python
# Live Score Service
class LiveScoreService:
    def __init__(self):
        self.kafka_producer = KafkaProducer(
            bootstrap_servers=['kafka1:9092', 'kafka2:9092'],
            compression_type='lz4',  # Compress for bandwidth
            batch_size=16384,
            linger_ms=10  # Small batch delay for throughput
        )
    
    def update_score(self, match_id, ball_data):
        # Validate and process ball data
        validated_data = self.validate_ball_data(ball_data)
        
        # Calculate derived metrics
        enriched_data = self.enrich_data(validated_data)
        
        # Update Redis (fast in-memory update)
        self.update_redis(match_id, enriched_data)
        
        # Publish to Kafka (asynchronous)
        self.kafka_producer.send(
            topic='live-updates',
            key=match_id.encode(),
            value=json.dumps(enriched_data).encode()
        )
        
        # Update database (asynchronous, can be slower)
        self.async_update_database(match_id, enriched_data)

# WebSocket Server
class WebSocketHandler:
    def __init__(self):
        self.kafka_consumer = KafkaConsumer(
            'live-updates',
            bootstrap_servers=['kafka1:9092', 'kafka2:9092'],
            group_id='websocket-group',
            auto_offset_reset='latest',
            enable_auto_commit=True
        )
        self.connections = defaultdict(list)  # {match_id: [ws1, ws2, ...]}
    
    async def consume_and_broadcast(self):
        for message in self.kafka_consumer:
            update = json.loads(message.value)
            match_id = update['match_id']
            
            # Get all connections for this match
            websockets = self.connections.get(match_id, [])
            
            # Broadcast to all (parallel)
            await asyncio.gather(
                *[ws.send(json.dumps(update)) for ws in websockets],
                return_exceptions=True
            )
```

**Scalability:**

```
Number of WebSocket Servers: 100
Connections per server: 100,000
Total capacity: 10 million concurrent connections

Kafka:
- 10 partitions for 'live-updates' topic
- Each partition handles ~10 WebSocket servers
- 50K messages/second throughput (sufficient for 50 matches)

Load Balancing:
- Use consistent hashing on user_id
- Sticky sessions to maintain connection
- Auto-scale WebSocket servers based on connection count
```

**Optimization Techniques:**

1. **Binary Protocol:** Use MessagePack instead of JSON (30% smaller)
2. **Compression:** Enable WebSocket permessage-deflate
3. **Batching:** Send updates in micro-batches (every 100ms) instead of per-ball
4. **Filtering:** Only send relevant updates (user's subscribed matches)
5. **Heartbeat:** Ping/pong every 30 seconds to detect dead connections

### Question 2: How do you design the database schema to efficiently query player statistics across different formats, time periods, and opposition?

**Answer:**

**Hybrid Approach: Aggregated Tables + Raw Data**

```sql
-- 1. Pre-aggregated Statistics (Fast Queries)
CREATE TABLE player_statistics (
    stat_id BIGSERIAL PRIMARY KEY,
    player_id VARCHAR(50),
    format VARCHAR(10), -- 'TEST', 'ODI', 'T20'
    match_type VARCHAR(20), -- 'INTERNATIONAL', 'DOMESTIC'
    opposition_team_id INT, -- NULL for overall stats
    venue_id INT, -- NULL for overall stats
    year INT, -- NULL for career stats
    
    -- Batting
    matches INT,
    innings INT,
    runs INT,
    highest_score INT,
    average DECIMAL(6,2),
    strike_rate DECIMAL(6,2),
    centuries INT,
    fifties INT,
    
    -- Bowling
    wickets INT,
    bowling_average DECIMAL(6,2),
    economy DECIMAL(4,2),
    
    -- Fielding
    catches INT,
    run_outs INT,
    
    last_updated TIMESTAMP,
    
    INDEX idx_player_format (player_id, format),
    INDEX idx_player_opposition (player_id, opposition_team_id),
    INDEX idx_player_year (player_id, year)
);

-- 2. Raw Ball-by-Ball Data (MongoDB for Flexibility)
// Collection: ball_by_ball
{
  "_id": ObjectId("..."),
  "match_id": "IND_vs_AUS_2026_T20",
  "player_id": "V_KOHLI",
  "innings": 1,
  "over": 15.3,
  "runs_scored": 4,
  "is_wicket": false,
  "bowler_id": "M_STARC",
  "timestamp": ISODate("2026-11-15T19:45:32Z"),
  "metadata": {
    "format": "T20",
    "venue_id": 10,
    "opposition_team_id": 2,
    "year": 2026
  }
}

// Indexes for efficient querying
db.ball_by_ball.createIndex({"player_id": 1, "metadata.format": 1, "timestamp": -1})
db.ball_by_ball.createIndex({"player_id": 1, "metadata.opposition_team_id": 1})
db.ball_by_ball.createIndex({"match_id": 1, "innings": 1})
```

**Query Examples:**

```python
# Query 1: Get player stats vs specific opposition
def get_player_stats_vs_opposition(player_id, format, opposition_team_id):
    return db.query("""
        SELECT 
            SUM(runs) as total_runs,
            AVG(average) as batting_average,
            AVG(strike_rate) as strike_rate,
            SUM(centuries) as centuries
        FROM player_statistics
        WHERE player_id = %s 
          AND format = %s 
          AND opposition_team_id = %s
    """, (player_id, format, opposition_team_id))

# Query 2: Get recent form (last 10 innings) - use MongoDB
def get_recent_form(player_id, format, limit=10):
    return mongo.ball_by_ball.aggregate([
        {"$match": {
            "player_id": player_id,
            "metadata.format": format
        }},
        {"$sort": {"timestamp": -1}},
        {"$group": {
            "_id": "$match_id",
            "runs": {"$sum": "$runs_scored"},
            "balls": {"$sum": 1},
            "date": {"$first": "$timestamp"}
        }},
        {"$limit": limit},
        {"$sort": {"date": -1}}
    ])

# Query 3: Get stats at specific venue
def get_player_stats_at_venue(player_id, venue_id):
    return db.query("""
        SELECT 
            SUM(runs) as total_runs,
            AVG(average) as batting_average,
            SUM(matches) as matches_played
        FROM player_statistics
        WHERE player_id = %s AND venue_id = %s
    """, (player_id, venue_id))

# Query 4: Get stats in specific year
def get_player_stats_by_year(player_id, year):
    return db.query("""
        SELECT format, SUM(runs) as runs, AVG(average) as average
        FROM player_statistics
        WHERE player_id = %s AND year = %s
        GROUP BY format
    """, (player_id, year))
```

**Statistics Aggregation (Background Job):**

```python
class StatisticsAggregator:
    def aggregate_player_stats(self, player_id, match_id):
        """
        Run after each match to update aggregated statistics
        """
        # Get match details
        match = db.query("SELECT * FROM matches WHERE match_id = %s", (match_id,))
        
        # Get player performance in this match from MongoDB
        performance = mongo.ball_by_ball.aggregate([
            {"$match": {"match_id": match_id, "player_id": player_id}},
            {"$group": {
                "_id": None,
                "runs": {"$sum": "$runs_scored"},
                "balls": {"$sum": 1},
                "fours": {"$sum": {"$cond": [{"$eq": ["$runs_scored", 4]}, 1, 0]}},
                "sixes": {"$sum": {"$cond": [{"$eq": ["$runs_scored", 6]}, 1, 0]}}
            }}
        ]).next()
        
        # Update aggregated statistics (multiple dimensions)
        dimensions = [
            {"format": match.format},  # Overall stats for format
            {"format": match.format, "opposition_team_id": match.opposition_team_id},  # vs Opposition
            {"format": match.format, "venue_id": match.venue_id},  # At venue
            {"format": match.format, "year": match.year}  # In year
        ]
        
        for dim in dimensions:
            # Upsert statistics
            db.execute("""
                INSERT INTO player_statistics 
                (player_id, format, opposition_team_id, venue_id, year, 
                 matches, innings, runs, highest_score, average, strike_rate)
                VALUES (%s, %s, %s, %s, %s, 1, 1, %s, %s, %s, %s)
                ON CONFLICT (player_id, format, opposition_team_id, venue_id, year)
                DO UPDATE SET
                    matches = player_statistics.matches + 1,
                    innings = player_statistics.innings + 1,
                    runs = player_statistics.runs + EXCLUDED.runs,
                    highest_score = GREATEST(player_statistics.highest_score, EXCLUDED.highest_score),
                    average = (player_statistics.runs + EXCLUDED.runs) / (player_statistics.innings + 1),
                    strike_rate = (player_statistics.runs + EXCLUDED.runs) * 100.0 / 
                                 (player_statistics.balls_faced + %s),
                    last_updated = NOW()
            """, (player_id, dim.get('format'), dim.get('opposition_team_id'), 
                  dim.get('venue_id'), dim.get('year'),
                  performance['runs'], performance['runs'], 
                  performance['runs'], performance['runs'] * 100.0 / performance['balls'],
                  performance['balls']))
```

**Benefits:**
- Fast queries on aggregated data (< 50ms)
- Detailed drill-down using MongoDB
- Multiple query dimensions (format, opposition, venue, year)
- Incremental updates (no need to recalculate everything)

### Question 3: How would you implement a win probability calculator that updates in real-time during a match?

**Answer:**

**Machine Learning Model + Real-Time Inference**

**Model Training:**

```python
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split

class WinProbabilityModel:
    def __init__(self):
        self.model = GradientBoostingClassifier(n_estimators=100, max_depth=5)
    
    def prepare_features(self, match_state):
        """
        Extract features from current match state
        """
        features = {
            # Score-based features
            'current_score': match_state['runs'],
            'wickets_fallen': match_state['wickets'],
            'overs_completed': match_state['overs'],
            'current_run_rate': match_state['runs'] / match_state['overs'],
            'balls_remaining': (20 - match_state['overs']) * 6,  # For T20
            
            # Target-based (2nd innings only)
            'target': match_state.get('target', 0),
            'runs_required': match_state.get('target', 0) - match_state['runs'],
            'required_run_rate': (match_state.get('target', 0) - match_state['runs']) / 
                                (20 - match_state['overs']),
            
            # Venue features
            'venue_avg_first_innings': match_state['venue_stats']['avg_first_innings_score'],
            'venue_avg_second_innings': match_state['venue_stats']['avg_second_innings_score'],
            'venue_chase_success_rate': match_state['venue_stats']['chase_success_rate'],
            
            # Team strength
            'batting_team_rating': match_state['batting_team_rating'],
            'bowling_team_rating': match_state['bowling_team_rating'],
            
            # Current partnership
            'partnership_runs': match_state['current_partnership']['runs'],
            'partnership_balls': match_state['current_partnership']['balls'],
            
            # Batsmen quality
            'batsman1_average': match_state['batsman1']['career_average'],
            'batsman2_average': match_state['batsman2']['career_average'],
            'batsman1_strike_rate': match_state['batsman1']['career_strike_rate'],
            
            # Remaining batting resources
            'wickets_in_hand': 10 - match_state['wickets'],
            'powerplay_complete': match_state['overs'] > 6
        }
        
        return pd.DataFrame([features])
    
    def train(self, historical_matches):
        """
        Train model on historical match data
        """
        # Prepare training data
        X = []
        y = []
        
        for match in historical_matches:
            # Sample match states at different overs
            for over in range(1, 21):
                state_at_over = get_match_state_at_over(match, over)
                features = self.prepare_features(state_at_over)
                
                # Label: Did batting team win? (1 = yes, 0 = no)
                outcome = 1 if match['winner'] == state_at_over['batting_team'] else 0
                
                X.append(features)
                y.append(outcome)
        
        # Train model
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
        self.model.fit(X_train, y_train)
        
        # Evaluate
        accuracy = self.model.score(X_test, y_test)
        print(f"Model Accuracy: {accuracy}")
        
        # Save model
        joblib.dump(self.model, 'win_probability_model.pkl')
    
    def predict(self, match_state):
        """
        Predict win probability for current match state
        """
        features = self.prepare_features(match_state)
        win_prob = self.model.predict_proba(features)[0][1]  # Probability of class 1 (win)
        
        return {
            'batting_team_win_prob': round(win_prob * 100, 2),
            'bowling_team_win_prob': round((1 - win_prob) * 100, 2)
        }
```

**Real-Time Integration:**

```python
class WinProbabilityService:
    def __init__(self):
        self.model = joblib.load('win_probability_model.pkl')
        self.redis_client = redis.Redis()
    
    def update_win_probability(self, match_id, ball_update):
        """
        Calculate and cache win probability after each ball
        """
        # Get current match state
        match_state = self.get_match_state(match_id)
        
        # Predict win probability
        prediction = self.model.predict(match_state)
        
        # Cache in Redis
        cache_key = f"win_prob:{match_id}"
        self.redis_client.setex(
            cache_key,
            300,  # 5-minute TTL
            json.dumps(prediction)
        )
        
        # Publish to Kafka for real-time updates
        kafka_producer.send('match-analytics', {
            'match_id': match_id,
            'event': 'WIN_PROBABILITY_UPDATE',
            'data': prediction,
            'timestamp': time.time()
        })
        
        return prediction
    
    def get_win_probability(self, match_id):
        """
        Get cached win probability
        """
        cache_key = f"win_prob:{match_id}"
        cached = self.redis_client.get(cache_key)
        
        if cached:
            return json.loads(cached)
        
        # Calculate if not cached
        match_state = self.get_match_state(match_id)
        return self.model.predict(match_state)
```

**API Endpoint:**

```
GET /api/v1/matches/{matchId}/win-probability

Response: 200 OK
{
  "match_id": "IND_vs_AUS_2026_T20_Final",
  "current_state": {
    "innings": 2,
    "batting_team": "AUS",
    "score": {"runs": 85, "wickets": 3, "overs": 10.2},
    "target": 143,
    "runs_required": 58,
    "balls_remaining": 58,
    "required_run_rate": 6.0
  },
  "win_probability": {
    "AUS": 62.5,
    "IND": 37.5
  },
  "confidence": "HIGH",
  "last_updated": "2026-11-15T20:15:30Z"
}
```

**Visualization (Frontend):**
```javascript
// Win probability chart (updates in real-time)
const WinProbabilityChart = ({ matchId }) => {
  const [data, setData] = useState([]);
  
  useEffect(() => {
    const ws = new WebSocket(`wss://api.cricinfo.com/live/${matchId}`);
    
    ws.onmessage = (event) => {
      const update = JSON.parse(event.data);
      
      if (update.event === 'WIN_PROBABILITY_UPDATE') {
        setData(prev => [...prev, {
          over: update.data.current_over,
          teamA_prob: update.data.win_probability.AUS,
          teamB_prob: update.data.win_probability.IND
        }]);
      }
    };
    
    return () => ws.close();
  }, [matchId]);
  
  return <LineChart data={data} />;
};
```

**Benefits:**
- Real-time updates (< 2 seconds after each ball)
- Accurate predictions (based on historical data)
- Engaging user experience
- Low latency (cached in Redis)

---

**End of Document**
