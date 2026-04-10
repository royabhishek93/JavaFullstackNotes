# Chess Game (Online Multiplayer) - High-Level Design

## 1. System Overview

An online multiplayer chess platform enables real-time chess matches between players globally, supporting rated and unrated games, tournaments, puzzle solving, game analysis with chess engines, live spectator mode, and comprehensive player statistics. The system must handle millions of concurrent games, provide sub-100ms move latency, ensure fair play with anti-cheating mechanisms, support various time controls (blitz, rapid, classical), and maintain accurate ELO ratings.

## 2. Requirements

### Functional Requirements
- **Matchmaking**: Pair players based on ELO rating, time control preferences
- **Game Play**: Real-time move validation, check/checkmate detection
- **Time Controls**: Support bullet (1min), blitz (3-5min), rapid (10-15min), classical (30min+)
- **Game Analysis**: Post-game analysis with chess engine (Stockfish)
- **Puzzles**: Daily chess puzzles, tactical training
- **Tournaments**: Create and manage tournaments with brackets
- **Spectator Mode**: Watch live games in real-time
- **Chat System**: In-game chat, emojis, premoves
- **Game History**: Store all games with PGN (Portable Game Notation)
- **Leaderboard**: Global and regional rankings

### Non-Functional Requirements
- **Latency**: Move propagation < 100ms globally
- **Availability**: 99.9% uptime
- **Scalability**: Support 1M+ concurrent games
- **Consistency**: Strong consistency for game state
- **Fairness**: Anti-cheat detection, fair matchmaking
- **Performance**: Matchmaking < 5 seconds

## 3. Capacity Estimation

### Scale Assumptions
- **Total Users**: 50M registered, 2M DAU
- **Concurrent Games**: 500K active games at peak
- **Daily Games**: 5M games/day
- **Average Game Duration**: 15 minutes
- **Move Frequency**: ~40 moves per game, 1 move per 22 seconds
- **Game State Size**: 5KB per game

### Storage Estimation
- **User Profiles**: 50M users × 3KB = 150GB
- **Game Records**: 5M games/day × 5KB × 365 = 9.125TB/year
- **Historical Games** (5 years): ~45TB
- **Puzzles & Training**: ~10GB
- **Total Storage**: ~50TB (with replicas: 150TB)

### Bandwidth
- **Move Traffic**: 500K games × 1 move/22s × 1KB = 22.7MB/s
- **Spectator Traffic**: 100K spectators × 1KB/s = 100MB/s
- **Total Bandwidth**: ~150MB/s (peak)

### QPS Estimation
- **Move Requests**: 500K games / 22s = 22,727 QPS
- **Game Creation**: 5M games/day / 86400s = 58 QPS
- **Matchmaking**: 116 QPS (2 players per game)

## 4. System Architecture

```
┌──────────────┐                    ┌─────────────────┐
│   Web App    │◄───────────────────┤   CDN (Static)  │
│  (React)     │                    │   Cloudflare    │
└──────┬───────┘                    └─────────────────┘
       │
       │                             ┌─────────────────┐
       └─────────────────────────────►  API Gateway    │
                                     │  (Rate Limit,   │
┌──────────────┐                    │   Auth)         │
│   Mobile     │◄───────────────────┤                 │
│   Apps       │                    └────────┬────────┘
└──────────────┘                             │
                              ┌──────────────┼──────────────┐
                              │              │              │
                    ┌─────────▼────┐  ┌─────▼─────┐  ┌────▼──────┐
                    │ WebSocket    │  │   User    │  │  Auth     │
                    │  Gateway     │  │  Service  │  │  Service  │
                    │ (Socket.io)  │  └───────────┘  └───────────┘
                    └─────────┬────┘
                              │
                    ┌─────────▼────────────┐
                    │  Game Orchestrator   │
                    │  (Redis Pub/Sub)     │
                    └─────────┬────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
  ┌─────▼──────┐    ┌────────▼────────┐    ┌──────▼────────┐
  │Matchmaking │    │   Game Engine   │    │   Analysis    │
  │  Service   │    │   Service       │    │   Service     │
  │  (ELO)     │    │   (Chess Logic) │    │  (Stockfish)  │
  └─────┬──────┘    └────────┬────────┘    └──────┬────────┘
        │                    │                     │
        └────────────────────┼─────────────────────┘
                             │
              ┌──────────────▼──────────────┐
              │    Message Queue (Kafka)    │
              │  Topics: moves, games,      │
              │          matchmaking         │
              └──────────────┬──────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
  ┌─────▼──────┐    ┌───────▼────────┐   ┌──────▼────────┐
  │Tournament  │    │  Anti-Cheat    │   │ Notification  │
  │  Service   │    │   Service      │   │   Service     │
  └────────────┘    └────────────────┘   └───────────────┘

┌───────────────────────────────────────────────────────────────┐
│                        Data Layer                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ PostgreSQL   │  │    Redis     │  │  MongoDB     │       │
│  │ (Users,      │  │  (Game State,│  │ (Game        │       │
│  │  Ratings)    │  │   Sessions)  │  │  History)    │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
└───────────────────────────────────────────────────────────────┘
```

## 5. Core Components

### WebSocket Gateway
- **Persistent Connections**: Maintain WebSocket connections for real-time moves
- **Connection Pooling**: Handle 1M+ concurrent connections
- **Heartbeat**: Ping/pong every 30 seconds to detect disconnections
- **Reconnection Logic**: Resume game state on reconnection
- **Message Protocol**: Binary protocol for efficient move transmission

### Game Engine Service
- **Move Validation**: Validate legal moves using chess rules engine
- **State Management**: Maintain current board state (FEN notation)
- **Check/Checkmate Detection**: Detect game-ending conditions
- **Time Management**: Track remaining time per player
- **Draw Conditions**: Detect stalemate, threefold repetition, 50-move rule
- **Premove Support**: Queue moves for instant execution

### Matchmaking Service
- **ELO-Based Matching**: Pair players within ±100 ELO range
- **Queue Management**: Separate queues per time control
- **Expansion Algorithm**: Gradually expand ELO range if no match found
- **Priority Queue**: Premium members get faster matches
- **Geo-Matching**: Prefer players in same region for lower latency

### Analysis Service
- **Chess Engine**: Stockfish integration for move analysis
- **Best Move Calculation**: Calculate best move with depth 20+
- **Position Evaluation**: Evaluate position (+2.5 advantage to white)
- **Opening Book**: Identify opening variations
- **Batch Analysis**: Queue analysis jobs, process asynchronously

### Anti-Cheat Service
- **Move Time Analysis**: Detect consistent instant moves (engine assistance)
- **Accuracy Scoring**: Compare player moves with engine recommendations
- **Pattern Detection**: Flag suspicious move patterns
- **Browser Tab Detection**: Detect if player switches tabs frequently
- **Fair Play Algorithm**: ML model predicts cheating probability

## 6. Database Design

### Schema Design

```sql
-- Users Table
CREATE TABLE users (
    user_id BIGSERIAL PRIMARY KEY,
    username VARCHAR(30) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(128),
    country VARCHAR(50),
    elo_rating INT DEFAULT 1200,
    blitz_rating INT DEFAULT 1200,
    rapid_rating INT DEFAULT 1200,
    bullet_rating INT DEFAULT 1200,
    games_played INT DEFAULT 0,
    wins INT DEFAULT 0,
    losses INT DEFAULT 0,
    draws INT DEFAULT 0,
    premium_member BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    last_seen TIMESTAMP,
    INDEX idx_username (username),
    INDEX idx_elo (elo_rating DESC)
);

-- Games Table (Partitioned by date)
CREATE TABLE games (
    game_id BIGSERIAL,
    white_player_id BIGINT REFERENCES users(user_id),
    black_player_id BIGINT REFERENCES users(user_id),
    time_control VARCHAR(20), -- BULLET, BLITZ, RAPID, CLASSICAL
    rated BOOLEAN DEFAULT TRUE,
    result VARCHAR(10), -- WHITE_WIN, BLACK_WIN, DRAW, ONGOING
    termination VARCHAR(30), -- CHECKMATE, RESIGNATION, TIMEOUT, DRAW_AGREEMENT
    white_elo_before INT,
    black_elo_before INT,
    white_elo_after INT,
    black_elo_after INT,
    pgn TEXT, -- Portable Game Notation
    fen TEXT, -- Final position
    total_moves INT,
    duration_seconds INT,
    started_at TIMESTAMP,
    ended_at TIMESTAMP,
    PRIMARY KEY (game_id, started_at),
    INDEX idx_white (white_player_id, started_at),
    INDEX idx_black (black_player_id, started_at)
) PARTITION BY RANGE (started_at);

-- Create partitions
CREATE TABLE games_2026_04 PARTITION OF games
    FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');

-- Active Games (Redis-backed, in-memory)
-- Stored in Redis for low-latency access
-- Key: game:{game_id}
-- Value: JSON with game state
{
  "game_id": 12345,
  "white_player_id": 1001,
  "black_player_id": 1002,
  "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
  "moves": ["e4", "e5", "Nf3"],
  "white_time_remaining": 180,
  "black_time_remaining": 180,
  "current_turn": "white",
  "status": "ONGOING"
}

-- Moves Table (NoSQL - MongoDB for flexibility)
CREATE COLLECTION moves (
    move_id: ObjectId,
    game_id: Long,
    move_number: Int,
    player_color: String, // "white" or "black"
    move_notation: String, // "e4", "Nf3", "O-O"
    fen_after_move: String,
    time_taken_ms: Int,
    time_remaining: Int,
    evaluation: Float, // Stockfish evaluation
    best_move: String, // Engine's recommended move
    timestamp: Date,
    INDEX (game_id, move_number)
)

-- Matchmaking Queue (Redis Sorted Set)
-- Key: matchmaking:{time_control}
-- Score: ELO rating
-- Value: user_id
ZADD matchmaking:blitz 1500 user_1001
ZADD matchmaking:blitz 1520 user_1002

-- Puzzles Table
CREATE TABLE puzzles (
    puzzle_id SERIAL PRIMARY KEY,
    fen VARCHAR(100) NOT NULL,
    solution JSONB, -- ["e4", "exd5", "Qxd5"]
    difficulty INT, -- 1-10
    rating INT, -- 1200-2800
    themes VARCHAR(100), -- "fork,pin,discovered_attack"
    popularity INT DEFAULT 0,
    INDEX idx_rating (rating)
);

-- Puzzle Attempts Table
CREATE TABLE puzzle_attempts (
    attempt_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id),
    puzzle_id INT REFERENCES puzzles(puzzle_id),
    solved BOOLEAN,
    time_taken_seconds INT,
    attempted_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_user_puzzle (user_id, puzzle_id)
);

-- Tournaments Table
CREATE TABLE tournaments (
    tournament_id SERIAL PRIMARY KEY,
    name VARCHAR(255),
    time_control VARCHAR(20),
    rounds INT,
    max_players INT,
    entry_fee DECIMAL(10,2),
    prize_pool DECIMAL(10,2),
    status VARCHAR(20), -- REGISTRATION, ONGOING, COMPLETED
    starts_at TIMESTAMP,
    ends_at TIMESTAMP,
    INDEX idx_status (status, starts_at)
);

-- Tournament Participants Table
CREATE TABLE tournament_participants (
    participant_id BIGSERIAL PRIMARY KEY,
    tournament_id INT REFERENCES tournaments(tournament_id),
    user_id BIGINT REFERENCES users(user_id),
    score DECIMAL(3,1) DEFAULT 0.0,
    rank INT,
    UNIQUE(tournament_id, user_id)
);
```

## 7. API Design

### Start Matchmaking
```http
POST /api/v1/matchmaking/join
Authorization: Bearer <jwt_token>

{
  "time_control": "BLITZ",
  "rated": true,
  "color_preference": "random" // white, black, random
}

Response: 202 Accepted
{
  "queue_id": "queue_abc123",
  "estimated_wait_time": 5,
  "message": "Searching for opponent..."
}

// WebSocket notification when match found
{
  "event": "MATCH_FOUND",
  "game_id": 12345,
  "opponent": {
    "username": "GrandMaster99",
    "rating": 1520,
    "country": "US"
  },
  "your_color": "white",
  "time_control": "BLITZ",
  "initial_time": 180
}
```

### Make Move
```http
POST /api/v1/games/{game_id}/move
Authorization: Bearer <jwt_token>

{
  "move": "e4", // SAN notation
  "time_remaining": 178
}

Response: 200 OK
{
  "move_number": 1,
  "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
  "legal_moves": ["e5", "e6", "c5", "c6", "Nf6", ...],
  "check": false,
  "checkmate": false,
  "draw": false
}

// WebSocket broadcast to opponent and spectators
{
  "event": "MOVE_MADE",
  "game_id": 12345,
  "move": "e4",
  "move_number": 1,
  "time_remaining": {
    "white": 178,
    "black": 180
  },
  "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
}
```

### Get Game State
```http
GET /api/v1/games/{game_id}
Authorization: Bearer <jwt_token>

Response: 200 OK
{
  "game_id": 12345,
  "white_player": {
    "username": "Player1",
    "rating": 1500
  },
  "black_player": {
    "username": "Player2",
    "rating": 1520
  },
  "fen": "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3",
  "moves": ["e4", "e5", "Nf3", "Nc6"],
  "time_remaining": {
    "white": 175,
    "black": 172
  },
  "status": "ONGOING",
  "current_turn": "white"
}
```

### Request Game Analysis
```http
POST /api/v1/games/{game_id}/analyze
Authorization: Bearer <jwt_token>

Response: 202 Accepted
{
  "analysis_id": "analysis_xyz789",
  "status": "QUEUED",
  "estimated_time": 30
}

// Retrieve analysis result
GET /api/v1/analysis/{analysis_id}

Response: 200 OK
{
  "game_id": 12345,
  "accuracy": {
    "white": 87.5,
    "black": 91.2
  },
  "critical_mistakes": [
    {
      "move_number": 12,
      "player": "white",
      "move_played": "Qxf7",
      "best_move": "Ng5",
      "evaluation_drop": -2.8
    }
  ],
  "opening": "Italian Game, Classical Variation"
}
```

## 8. Scalability Strategy

### Horizontal Scaling
- **Stateless Game Engine**: Scale game engine horizontally
- **WebSocket Sharding**: Partition connections by user_id hash
- **Read Replicas**: Route game history queries to read replicas

### Redis for Active Games
```
Why Redis for active games:
1. Sub-millisecond read/write latency
2. TTL for automatic cleanup (games expire after 24 hours of inactivity)
3. Pub/Sub for real-time move broadcasting
4. Atomic operations (SETEX, INCR for time tracking)

Key Structure:
- game:{game_id} → Game state (JSON)
- game:{game_id}:moves → List of moves
- game:{game_id}:spectators → Set of spectator user_ids
- matchmaking:{time_control} → Sorted set (score=ELO, value=user_id)
```

### Database Sharding
```
Shard Key Strategy:
- Users: Shard by user_id % 10
- Games: Partition by started_at (monthly partitions)
- Moves: Store in MongoDB, shard by game_id

Read Replicas:
- 3 read replicas per shard
- Game history queries → read replicas
- Live games → Redis (no DB hit)
```

### Caching Strategy
```
Redis Cache:
- User profiles (1 hour TTL)
- Leaderboard (5 min TTL)
- Puzzle of the day (24 hour TTL)
- Opening book (never expire)

CDN Cache:
- Static assets (chess pieces, board themes)
- User avatars (1 day TTL)
```

### Geo-Distribution
```
Regions:
- US-East, US-West, EU-Central, AP-Southeast

Routing Strategy:
- Matchmaking: Prefer same-region opponents
- WebSocket: Connect to nearest edge server
- Game State: Replicate to primary region only (strong consistency)
```

## 9. Fault Tolerance & High Availability

### WebSocket Reconnection
```javascript
class ChessWebSocket {
  connect() {
    this.ws = new WebSocket(WS_URL);
    
    this.ws.onclose = () => {
      // Exponential backoff reconnection
      setTimeout(() => this.connect(), this.backoff);
      this.backoff = Math.min(this.backoff * 2, 30000);
    };
    
    this.ws.onopen = () => {
      // Resume game state
      this.send({
        type: 'RESUME_GAME',
        game_id: this.gameId,
        last_move_number: this.lastMoveNumber
      });
    };
  }
}
```

### Time Synchronization
```python
# Server-authoritative time tracking
class TimeManager:
    def make_move(self, game_id, move, client_time_remaining):
        server_time = redis.get(f"game:{game_id}:time")
        actual_time_elapsed = time.time() - server_time['last_move_time']
        
        # Trust server time, not client
        new_time = server_time['remaining'] - actual_time_elapsed
        
        if new_time <= 0:
            end_game(game_id, "TIMEOUT")
            return {"error": "Time expired"}
        
        redis.setex(f"game:{game_id}:time", 86400, {
            "remaining": new_time,
            "last_move_time": time.time()
        })
```

### Game State Recovery
```
If server crashes during game:
1. Game state persisted in Redis (replicated across 3 nodes)
2. On reconnection, client requests game state
3. Server retrieves from Redis, resumes game
4. Time adjusted for disconnection period (grace period: 30s)
```

### Anti-Cheat Detection
```python
def detect_cheating(game_id, user_id):
    moves = get_moves(game_id, user_id)
    
    # Calculate move accuracy
    engine_matches = sum(1 for move in moves if move['played'] == move['best_move'])
    accuracy = engine_matches / len(moves)
    
    # Check move times (engine-assisted moves are instant)
    avg_move_time = sum(move['time_taken_ms'] for move in moves) / len(moves)
    
    if accuracy > 0.95 and avg_move_time < 500:
        flag_for_review(user_id, "High accuracy + fast moves")
    
    # Check browser activity (tab switching)
    if get_tab_switches(game_id, user_id) > 10:
        flag_for_review(user_id, "Excessive tab switching")
```

## 10. Technology Stack

| Component | Technology | Justification |
|-----------|-----------|---------------|
| **Frontend** | React + TypeScript | Component-based, type-safe |
| **WebSocket** | Socket.io / uWebSockets.js | Real-time bidirectional communication |
| **API Gateway** | Kong | Rate limiting, auth |
| **Backend** | Node.js / Go | High concurrency, low latency |
| **Chess Engine** | Stockfish (C++) | Industry-standard chess engine |
| **Real-time DB** | Redis Cluster | Sub-ms latency, pub/sub |
| **Primary DB** | PostgreSQL 14+ | ACID, complex queries |
| **Document Store** | MongoDB | Flexible schema for moves |
| **Message Queue** | Apache Kafka | Event streaming |
| **CDN** | Cloudflare | Global edge caching |
| **Monitoring** | Prometheus + Grafana | Metrics, dashboards |
| **Logging** | ELK Stack | Centralized logging |

## 11. Interview Discussion Points

### Q1: How do you ensure move validation is correct and prevent cheating?

**Answer**: Server-authoritative game logic:

```python
def validate_move(game_id, player_id, move):
    # 1. Retrieve current game state from Redis
    game_state = redis.get(f"game:{game_id}")
    
    # 2. Verify it's player's turn
    if game_state['current_turn'] != get_player_color(player_id):
        return {"error": "Not your turn"}
    
    # 3. Use chess library to validate move
    board = chess.Board(game_state['fen'])
    try:
        legal_move = board.parse_san(move)
        board.push(legal_move)
    except:
        return {"error": "Illegal move"}
    
    # 4. Update game state
    game_state['fen'] = board.fen()
    game_state['moves'].append(move)
    game_state['current_turn'] = 'black' if game_state['current_turn'] == 'white' else 'white'
    
    # 5. Check game-ending conditions
    if board.is_checkmate():
        game_state['status'] = 'CHECKMATE'
    elif board.is_stalemate():
        game_state['status'] = 'DRAW'
    
    redis.setex(f"game:{game_id}", 86400, game_state)
    
    # Never trust client - all logic on server
    return {"status": "success", "fen": board.fen()}
```

### Q2: How do you implement ELO rating updates after a game?

**Answer**: ELO calculation with K-factor:

```python
def update_elo_ratings(game_id):
    game = db.get_game(game_id)
    
    # ELO formula: new_rating = old_rating + K * (actual_score - expected_score)
    K = 32 if game.time_control == 'BULLET' else 24
    
    # Calculate expected score
    expected_white = 1 / (1 + 10**((game.black_elo - game.white_elo) / 400))
    expected_black = 1 - expected_white
    
    # Actual score (1 = win, 0.5 = draw, 0 = loss)
    if game.result == 'WHITE_WIN':
        actual_white, actual_black = 1, 0
    elif game.result == 'BLACK_WIN':
        actual_white, actual_black = 0, 1
    else:
        actual_white, actual_black = 0.5, 0.5
    
    # Update ratings
    white_new_elo = game.white_elo + K * (actual_white - expected_white)
    black_new_elo = game.black_elo + K * (actual_black - expected_black)
    
    # Update database
    db.execute("""
        UPDATE users SET elo_rating = CASE
            WHEN user_id = %s THEN %s
            WHEN user_id = %s THEN %s
        END
        WHERE user_id IN (%s, %s)
    """, (game.white_player_id, white_new_elo, 
          game.black_player_id, black_new_elo,
          game.white_player_id, game.black_player_id))
```

### Q3: How do you handle matchmaking efficiently?

**Answer**: Redis Sorted Sets with ELO-based matching:

```python
def find_match(user_id, time_control, elo_rating):
    queue_key = f"matchmaking:{time_control}"
    
    # Add user to queue (score = ELO)
    redis.zadd(queue_key, {user_id: elo_rating})
    
    # Find opponents within ±100 ELO range
    candidates = redis.zrangebyscore(
        queue_key, 
        elo_rating - 100, 
        elo_rating + 100
    )
    
    # Remove self from candidates
    candidates.remove(user_id)
    
    if candidates:
        # Match with closest ELO opponent
        opponent_id = min(candidates, key=lambda x: abs(redis.zscore(queue_key, x) - elo_rating))
        
        # Remove both from queue
        redis.zrem(queue_key, user_id, opponent_id)
        
        # Create game
        game_id = create_game(user_id, opponent_id, time_control)
        
        # Notify both players via WebSocket
        notify_match_found(user_id, opponent_id, game_id)
        
        return game_id
    else:
        # Expand range after 5 seconds
        schedule_range_expansion(user_id, time_control, elo_rating)
        return None
```

### Q4: How do you implement spectator mode efficiently?

**Answer**: Redis Pub/Sub for move broadcasting:

```python
class SpectatorService:
    def join_as_spectator(self, user_id, game_id):
        # Add to spectators set
        redis.sadd(f"game:{game_id}:spectators", user_id)
        
        # Subscribe to game channel
        pubsub = redis.pubsub()
        pubsub.subscribe(f"game:{game_id}:moves")
        
        # Send current game state
        game_state = redis.get(f"game:{game_id}")
        websocket.send(user_id, {
            "type": "GAME_STATE",
            "game_id": game_id,
            "fen": game_state['fen'],
            "moves": game_state['moves']
        })
        
        # Stream future moves
        for message in pubsub.listen():
            websocket.send(user_id, message['data'])
    
    def broadcast_move(self, game_id, move):
        # Publish move to all subscribers (players + spectators)
        redis.publish(f"game:{game_id}:moves", json.dumps({
            "type": "MOVE",
            "move": move,
            "fen": game_state['fen']
        }))
```

### Q5: How do you handle time synchronization across clients?

**Answer**: Server-authoritative time with NTP sync:

```python
class TimeController:
    def __init__(self, game_id):
        self.game_id = game_id
        self.start_time = time.time()
    
    def get_remaining_time(self, player_color):
        game_state = redis.hgetall(f"game:{self.game_id}:time")
        
        # Calculate elapsed time since last move
        if game_state['current_turn'] == player_color:
            elapsed = time.time() - float(game_state['last_move_time'])
            remaining = float(game_state[f'{player_color}_time']) - elapsed
        else:
            remaining = float(game_state[f'{player_color}_time'])
        
        return max(remaining, 0)
    
    def make_move(self, player_color, move):
        # Update time
        remaining = self.get_remaining_time(player_color)
        
        if remaining <= 0:
            end_game(self.game_id, f"{player_color}_TIMEOUT")
            return False
        
        # Store updated time
        redis.hset(f"game:{self.game_id}:time", f"{player_color}_time", remaining)
        redis.hset(f"game:{self.game_id}:time", "last_move_time", time.time())
        
        # Broadcast time update to clients
        broadcast_time_update(self.game_id, player_color, remaining)
        
        return True
```

---

**End of Document**
