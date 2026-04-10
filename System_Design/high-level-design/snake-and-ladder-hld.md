# Snake and Ladder Game - High-Level Design

## System Overview
An online multiplayer Snake and Ladder board game platform that supports real-time gameplay for 2-4 players, matchmaking, leaderboards, tournaments, chat, spectator mode, and replay functionality. The system handles game state synchronization, turn management, random dice rolls with fairness guarantees, and maintains comprehensive game statistics.

## Requirements

### Functional Requirements
1. **Game Modes**: Multiplayer (2-4 players), Single-player (vs AI), Private rooms, Quick match
2. **Matchmaking**: Skill-based matching, create/join rooms, invite friends
3. **Game Mechanics**: Dice roll (1-6), move piece, handle snakes/ladders, winning condition
4. **Real-time Sync**: WebSocket for live updates, turn notifications, player movements
5. **Chat**: In-game text chat, emojis, quick messages
6. **Leaderboard**: Global, weekly, friend-based rankings
7. **Statistics**: Win rate, games played, average position, longest winning streak
8. **Spectator Mode**: Watch ongoing games, follow specific players
9. **Replay**: Save and replay game history
10. **Tournaments**: Scheduled tournaments, bracket system, prizes
11. **Customization**: Board themes, piece skins, dice designs
12. **Fair Play**: Prevent cheating, validate moves server-side, detect bots

### Non-Functional Requirements
- **Availability**: 99.9% uptime (43 minutes downtime/month)
- **Latency**: < 100ms for move updates, < 50ms for dice roll
- **Throughput**: Support 100K concurrent games (400K concurrent players)
- **Scalability**: Handle 10M registered users, 1M daily active users
- **Consistency**: Strong consistency for game state, eventual for leaderboards
- **Fairness**: Cryptographically secure random dice rolls
- **Real-time**: WebSocket connections for all players in a game

## Capacity Estimation

### Traffic Estimates
- **Daily Active Users (DAU)**: 1M players
- **Concurrent games**: 100K games (average 3 players per game)
- **Concurrent players**: 300K players
- **Games per day**: 5M games
- **Average game duration**: 10 minutes
- **Moves per game**: 50 moves (average)
- **Total moves per day**: 5M * 50 = 250M moves

### Storage Estimates
- **Users**: 10M * 5KB = 50GB
- **Games**: 5M games/day * 10KB = 50GB/day = 18TB/year
- **Moves**: 250M moves/day * 500 bytes = 125GB/day = 45TB/year
- **Chat messages**: 5M games * 20 messages * 200 bytes = 20GB/day = 7TB/year
- **Total Storage (3 years)**: (18TB + 45TB + 7TB) * 3 = 210TB

### Bandwidth Estimates
- **WebSocket messages**: 300K connections * 100 bytes/sec = 30MB/s = 240 Mbps
- **HTTP requests**: 10K req/sec * 5KB = 50MB/s = 400 Mbps
- **Total Bandwidth**: 640 Mbps

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Client Applications                                │
│              (Web Browser, Mobile Apps, Desktop Client)                      │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │ HTTPS/WSS
┌──────────────────────────────▼──────────────────────────────────────────────┐
│                API Gateway + WebSocket Gateway                               │
│          (Load Balancing, Auth, Rate Limiting, Protocol Switch)              │
└──────┬────────────┬──────────┬──────────┬──────────┬─────────────┬─────────┘
       │            │          │          │          │             │
  ┌────▼────┐  ┌───▼──────┐ ┌─▼────┐ ┌───▼────┐ ┌──▼──────┐ ┌────▼─────┐
  │Game     │  │Matchmaking│ │Chat  │ │User    │ │Leaderboard│ │Spectator│
  │Service  │  │Service    │ │Service│ │Service │ │Service   │ │Service  │
  └────┬────┘  └─────┬─────┘ └──┬───┘ └───┬────┘ └─────┬────┘ └─────┬────┘
       │            │          │         │          │            │
  ┌────▼────────────▼──────────▼─────────▼──────────▼────────────▼────┐
  │              Redis Cluster (Cache + Pub/Sub)                        │
  │    (Game State, Active Players, Matchmaking Queue, Sessions)        │
  └─────────────────────────────┬───────────────────────────────────────┘
                                │
  ┌─────────────────────────────▼───────────────────────────────────────┐
  │           PostgreSQL Cluster (Primary + Replicas)                    │
  │      (Users, Games, Moves, Statistics, Leaderboards)                │
  └─────────────────────────────┬───────────────────────────────────────┘
                                │
  ┌─────────────────────────────▼───────────────────────────────────────┐
  │              MongoDB (Document Store)                                │
  │         (Game History, Replays, Chat Archives)                      │
  └─────────────────────────────┬───────────────────────────────────────┘
                                │
  ┌─────────────────────────────▼───────────────────────────────────────┐
  │                  Kafka (Event Streaming)                             │
  │      (Game Events, Move Events, Achievement Events)                 │
  └───┬─────────────┬───────────────┬───────────────────────────────────┘
      │             │               │
 ┌────▼──────┐ ┌───▼────────┐ ┌───▼──────────┐
 │Analytics  │ │Achievement │ │Notification  │
 │Pipeline   │ │Service     │ │Service       │
 └───────────┘ └────────────┘ └──────────────┘
```

## Core Components

### 1. Game Service
**Responsibilities**:
- Create and manage game rooms
- Maintain game state (board, player positions, turn order)
- Process moves and validate them
- Generate dice rolls with cryptographic fairness
- Determine winners and end games
- Sync game state via WebSocket

**Technology**: Spring Boot, WebSocket, Redis
**State Storage**: Redis (active games), PostgreSQL (completed games)

**Game State Model**:
```java
@Data
public class GameState {
    private String gameId;
    private List<Player> players;
    private Board board;
    private int currentTurn; // Index of current player
    private GameStatus status; // WAITING, IN_PROGRESS, COMPLETED, ABANDONED
    private Instant startTime;
    private Instant lastMoveTime;
    private List<Move> moveHistory;
    private String winnerId;
}

@Data
public class Board {
    private static final int BOARD_SIZE = 100;
    private Map<Integer, Integer> snakes; // Position -> destination
    private Map<Integer, Integer> ladders; // Position -> destination
    
    // Standard board setup
    public Board() {
        snakes = Map.of(
            17, 7,
            54, 34,
            62, 19,
            64, 60,
            87, 36,
            93, 73,
            95, 75,
            99, 78
        );
        
        ladders = Map.of(
            4, 14,
            9, 31,
            20, 38,
            28, 84,
            40, 59,
            51, 67,
            63, 81,
            71, 91
        );
    }
}

@Data
public class Player {
    private String userId;
    private String username;
    private String avatar;
    private int position; // 0-100
    private int order; // 1, 2, 3, 4
    private PlayerStatus status; // ACTIVE, DISCONNECTED, LEFT
}
```

**Move Processing**:
```java
@Service
public class GameService {
    
    @Transactional
    public MoveResult processMove(String gameId, String userId) {
        // 1. Load game state from Redis
        GameState game = getGameState(gameId);
        
        // 2. Validate move
        validateMove(game, userId);
        
        // 3. Roll dice (cryptographically random)
        int diceValue = rollDice(game);
        
        // 4. Calculate new position
        Player player = game.getPlayerByUserId(userId);
        int oldPosition = player.getPosition();
        int newPosition = Math.min(oldPosition + diceValue, 100);
        
        // 5. Check for snake or ladder
        newPosition = checkSnakeOrLadder(game.getBoard(), newPosition);
        
        // 6. Update player position
        player.setPosition(newPosition);
        
        // 7. Check for winner
        boolean won = (newPosition == 100);
        if (won) {
            game.setStatus(GameStatus.COMPLETED);
            game.setWinnerId(userId);
            handleGameEnd(game);
        } else {
            // Advance turn to next player
            game.setCurrentTurn((game.getCurrentTurn() + 1) % game.getPlayers().size());
        }
        
        // 8. Save move
        Move move = new Move(gameId, userId, oldPosition, newPosition, 
                            diceValue, Instant.now());
        game.getMoveHistory().add(move);
        
        // 9. Update game state in Redis
        saveGameState(game);
        
        // 10. Broadcast move to all players via WebSocket
        broadcastMove(game, move);
        
        // 11. Publish event to Kafka
        kafkaProducer.send("game.moves", new MoveEvent(game, move));
        
        return new MoveResult(diceValue, oldPosition, newPosition, won);
    }
    
    private void validateMove(GameState game, String userId) {
        // Check game is in progress
        if (game.getStatus() != GameStatus.IN_PROGRESS) {
            throw new GameNotInProgressException();
        }
        
        // Check it's player's turn
        Player currentPlayer = game.getPlayers().get(game.getCurrentTurn());
        if (!currentPlayer.getUserId().equals(userId)) {
            throw new NotYourTurnException();
        }
        
        // Check player is active
        if (currentPlayer.getStatus() != PlayerStatus.ACTIVE) {
            throw new PlayerNotActiveException();
        }
    }
    
    private int rollDice(GameState game) {
        // Use cryptographically secure random
        // SHA-256(gameId + currentTurn + timestamp + serverSecret)
        String input = game.getGameId() + 
                      game.getCurrentTurn() + 
                      System.nanoTime() + 
                      serverSecret;
        
        byte[] hash = sha256(input);
        int value = (Math.abs(ByteBuffer.wrap(hash).getInt()) % 6) + 1;
        
        return value; // 1-6
    }
    
    private int checkSnakeOrLadder(Board board, int position) {
        // Check for snake
        if (board.getSnakes().containsKey(position)) {
            int destination = board.getSnakes().get(position);
            return destination; // Snake bite, go down
        }
        
        // Check for ladder
        if (board.getLadders().containsKey(position)) {
            int destination = board.getLadders().get(position);
            return destination; // Climb ladder, go up
        }
        
        return position; // No snake or ladder
    }
    
    private void broadcastMove(GameState game, Move move) {
        // Send to all players in game room
        for (Player player : game.getPlayers()) {
            webSocketService.sendToUser(player.getUserId(), 
                new MoveUpdate(move));
        }
        
        // Send to spectators
        spectatorService.broadcastToSpectators(game.getGameId(), 
            new MoveUpdate(move));
    }
}
```

### 2. Matchmaking Service
**Responsibilities**:
- Quick match: Find players of similar skill level
- Create private rooms with invite codes
- Join existing rooms
- Handle player ready status
- Start game when all players ready

**Technology**: Spring Boot, Redis (matchmaking queue)

**Matchmaking Algorithm**:
```java
@Service
public class MatchmakingService {
    
    public void joinMatchmaking(String userId, SkillLevel skill) {
        // Add player to matchmaking queue
        redis.zadd("matchmaking:" + skill, 
                  System.currentTimeMillis(), userId);
        
        // Notify player they're in queue
        notificationService.sendToUser(userId, "Searching for players...");
        
        // Trigger matchmaking process
        triggerMatchmaking(skill);
    }
    
    @Scheduled(fixedRate = 1000) // Run every second
    public void processMatchmaking() {
        for (SkillLevel skill : SkillLevel.values()) {
            // Get players in queue
            Set<String> players = redis.zrange("matchmaking:" + skill, 0, -1);
            
            if (players.size() >= 2) {
                // Create game with 2-4 players
                int numPlayers = Math.min(players.size(), 4);
                List<String> matched = new ArrayList<>(players)
                    .subList(0, numPlayers);
                
                // Remove from queue
                redis.zrem("matchmaking:" + skill, matched.toArray());
                
                // Create game
                GameState game = gameService.createGame(matched);
                
                // Notify players
                for (String userId : matched) {
                    notificationService.sendToUser(userId, 
                        new GameFoundNotification(game.getGameId()));
                }
            }
        }
    }
}
```

### 3. Leaderboard Service
**Responsibilities**:
- Track player statistics (games played, won, win rate)
- Maintain global, weekly, friend-based leaderboards
- Calculate rankings and rating points
- Handle tie-breaking

**Technology**: Spring Boot, Redis (sorted sets), PostgreSQL

**Leaderboard Implementation**:
```java
@Service
public class LeaderboardService {
    
    public void updatePlayerStats(String userId, boolean won) {
        // Update stats in database
        PlayerStats stats = statsRepository.findByUserId(userId);
        stats.setGamesPlayed(stats.getGamesPlayed() + 1);
        if (won) {
            stats.setGamesWon(stats.getGamesWon() + 1);
            stats.setCurrentStreak(stats.getCurrentStreak() + 1);
            stats.setLongestStreak(Math.max(stats.getLongestStreak(), 
                                           stats.getCurrentStreak()));
        } else {
            stats.setCurrentStreak(0);
        }
        stats.setWinRate((double) stats.getGamesWon() / stats.getGamesPlayed());
        statsRepository.save(stats);
        
        // Update Redis leaderboard (sorted by rating)
        int newRating = calculateRating(stats);
        redis.zadd("leaderboard:global", newRating, userId);
        
        // Update weekly leaderboard
        String weekKey = "leaderboard:week:" + getCurrentWeek();
        redis.zadd(weekKey, newRating, userId);
        redis.expire(weekKey, Duration.ofDays(14)); // Keep for 2 weeks
    }
    
    public List<LeaderboardEntry> getGlobalLeaderboard(int offset, int limit) {
        // Get top players from Redis sorted set
        Set<ZSetOperations.TypedTuple<String>> entries = 
            redis.zrevrangeWithScores("leaderboard:global", offset, offset + limit - 1);
        
        List<LeaderboardEntry> leaderboard = new ArrayList<>();
        int rank = offset + 1;
        
        for (ZSetOperations.TypedTuple<String> entry : entries) {
            String userId = entry.getValue();
            int rating = entry.getScore().intValue();
            
            User user = userService.getUser(userId);
            PlayerStats stats = statsRepository.findByUserId(userId);
            
            leaderboard.add(new LeaderboardEntry(
                rank++, userId, user.getUsername(), user.getAvatar(),
                rating, stats.getGamesPlayed(), stats.getWinRate()
            ));
        }
        
        return leaderboard;
    }
    
    private int calculateRating(PlayerStats stats) {
        // ELO-like rating system
        int baseRating = 1000;
        int winsBonus = stats.getGamesWon() * 10;
        int winRateBonus = (int) (stats.getWinRate() * 500);
        int streakBonus = stats.getCurrentStreak() * 5;
        
        return baseRating + winsBonus + winRateBonus + streakBonus;
    }
}
```

### 4. Spectator Service
**Responsibilities**:
- Allow users to watch ongoing games
- Stream game events to spectators
- Handle spectator chat
- List popular games to watch

**Technology**: Spring Boot, WebSocket, Redis

**Spectator Implementation**:
```java
@Service
public class SpectatorService {
    
    public void joinAsSpectator(String userId, String gameId) {
        // Add to spectators set
        redis.sadd("game:" + gameId + ":spectators", userId);
        
        // Get current game state
        GameState game = gameService.getGameState(gameId);
        
        // Send full game state to spectator
        webSocketService.sendToUser(userId, 
            new GameStateSnapshot(game));
        
        // Notify players that someone is watching
        broadcastToPlayers(gameId, 
            new SpectatorJoinedNotification(userId));
    }
    
    public void broadcastToSpectators(String gameId, Object event) {
        // Get all spectators
        Set<String> spectators = redis.smembers("game:" + gameId + ":spectators");
        
        // Send event to each spectator
        for (String spectatorId : spectators) {
            webSocketService.sendToUser(spectatorId, event);
        }
    }
}
```

### 5. Chat Service
**Responsibilities**:
- In-game text chat between players
- Support emojis and quick messages
- Filter profanity
- Store chat history

**Technology**: Spring Boot, WebSocket, MongoDB

### 6. Achievement Service
**Responsibilities**:
- Track player achievements (first win, 10 wins, 100 wins, etc.)
- Award badges and titles
- Trigger notifications for unlocked achievements

**Technology**: Spring Boot, Kafka (event-driven)

## Database Design

### Users Table (PostgreSQL)
```sql
CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    avatar_url VARCHAR(500),
    skill_level VARCHAR(20) DEFAULT 'BEGINNER',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_login_at TIMESTAMP,
    CONSTRAINT chk_skill_level CHECK (skill_level IN 
        ('BEGINNER', 'INTERMEDIATE', 'ADVANCED', 'EXPERT'))
);

CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_skill_level ON users(skill_level);
```

### Games Table (PostgreSQL)
```sql
CREATE TABLE games (
    game_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    game_mode VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'WAITING',
    winner_id UUID REFERENCES users(user_id),
    num_players SMALLINT NOT NULL,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    duration_seconds INTEGER,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_game_mode CHECK (game_mode IN 
        ('MULTIPLAYER', 'SINGLE_PLAYER', 'TOURNAMENT')),
    CONSTRAINT chk_status CHECK (status IN 
        ('WAITING', 'IN_PROGRESS', 'COMPLETED', 'ABANDONED'))
);

CREATE INDEX idx_games_status ON games(status);
CREATE INDEX idx_games_winner ON games(winner_id);
CREATE INDEX idx_games_created_at ON games(created_at DESC);
```

### Game Players Table (PostgreSQL)
```sql
CREATE TABLE game_players (
    game_id UUID REFERENCES games(game_id),
    user_id UUID REFERENCES users(user_id),
    player_order SMALLINT NOT NULL,
    final_position INTEGER,
    is_winner BOOLEAN DEFAULT FALSE,
    joined_at TIMESTAMP NOT NULL DEFAULT NOW(),
    left_at TIMESTAMP,
    PRIMARY KEY (game_id, user_id)
);

CREATE INDEX idx_game_players_user ON game_players(user_id, joined_at DESC);
```

### Moves Table (PostgreSQL)
```sql
CREATE TABLE moves (
    move_id BIGSERIAL PRIMARY KEY,
    game_id UUID NOT NULL REFERENCES games(game_id),
    user_id UUID NOT NULL REFERENCES users(user_id),
    move_number INTEGER NOT NULL,
    dice_value SMALLINT NOT NULL,
    from_position INTEGER NOT NULL,
    to_position INTEGER NOT NULL,
    move_type VARCHAR(20) NOT NULL, -- NORMAL, SNAKE, LADDER
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_dice_value CHECK (dice_value >= 1 AND dice_value <= 6),
    CONSTRAINT chk_move_type CHECK (move_type IN 
        ('NORMAL', 'SNAKE', 'LADDER', 'WINNING'))
);

CREATE INDEX idx_moves_game ON moves(game_id, move_number);
CREATE INDEX idx_moves_user ON moves(user_id, created_at DESC);
```

### Player Statistics Table (PostgreSQL)
```sql
CREATE TABLE player_statistics (
    user_id UUID PRIMARY KEY REFERENCES users(user_id),
    games_played INTEGER DEFAULT 0,
    games_won INTEGER DEFAULT 0,
    win_rate DECIMAL(5, 4) DEFAULT 0,
    total_moves INTEGER DEFAULT 0,
    total_snakes_hit INTEGER DEFAULT 0,
    total_ladders_climbed INTEGER DEFAULT 0,
    current_streak INTEGER DEFAULT 0,
    longest_streak INTEGER DEFAULT 0,
    rating INTEGER DEFAULT 1000,
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_player_stats_rating ON player_statistics(rating DESC);
CREATE INDEX idx_player_stats_win_rate ON player_statistics(win_rate DESC);
```

### Game History (MongoDB)
```javascript
{
  "_id": ObjectId("..."),
  "game_id": "550e8400-e29b-41d4-a716-446655440000",
  "players": [
    {
      "user_id": "660e8400-...",
      "username": "player1",
      "final_position": 100,
      "is_winner": true
    }
  ],
  "moves": [
    {
      "move_number": 1,
      "user_id": "660e8400-...",
      "dice_value": 4,
      "from_position": 0,
      "to_position": 4,
      "move_type": "NORMAL",
      "timestamp": ISODate("2026-04-07T10:30:00Z")
    }
  ],
  "duration_seconds": 420,
  "created_at": ISODate("2026-04-07T10:30:00Z"),
  "completed_at": ISODate("2026-04-07T10:37:00Z")
}
```

## API Design

### 1. Create Game Room
```http
POST /api/v1/games/create
Authorization: Bearer <jwt_token>

Request:
{
  "game_mode": "MULTIPLAYER",
  "max_players": 4,
  "is_private": true
}

Response: 201 Created
{
  "game_id": "550e8400-e29b-41d4-a716-446655440000",
  "invite_code": "ABC123",
  "max_players": 4,
  "current_players": 1,
  "status": "WAITING",
  "created_at": "2026-04-07T10:30:00Z"
}
```

### 2. Join Game Room
```http
POST /api/v1/games/{game_id}/join
Authorization: Bearer <jwt_token>

Response: 200 OK
{
  "game_id": "550e8400-e29b-41d4-a716-446655440000",
  "player_order": 2,
  "players": [
    {"username": "player1", "avatar": "...", "ready": true},
    {"username": "player2", "avatar": "...", "ready": false}
  ],
  "status": "WAITING"
}
```

### 3. Roll Dice and Move (WebSocket)
```javascript
// Send move request
ws.send(JSON.stringify({
  "action": "ROLL_DICE",
  "game_id": "550e8400-e29b-41d4-a716-446655440000"
}));

// Receive move result
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data);
  /*
  {
    "type": "MOVE_UPDATE",
    "user_id": "660e8400-...",
    "username": "player1",
    "dice_value": 5,
    "from_position": 10,
    "to_position": 34,
    "move_type": "LADDER",
    "is_winner": false,
    "next_player": "player2"
  }
  */
};
```

### 4. Get Leaderboard
```http
GET /api/v1/leaderboard?type=global&offset=0&limit=50
Authorization: Bearer <jwt_token>

Response: 200 OK
{
  "leaderboard": [
    {
      "rank": 1,
      "user_id": "...",
      "username": "pro_player",
      "avatar": "...",
      "rating": 2500,
      "games_played": 1000,
      "win_rate": 0.85
    }
  ],
  "total_count": 1000000,
  "user_rank": 1523
}
```

### 5. Get Player Statistics
```http
GET /api/v1/users/{user_id}/stats
Authorization: Bearer <jwt_token>

Response: 200 OK
{
  "user_id": "660e8400-e29b-41d4-a716-446655440000",
  "games_played": 250,
  "games_won": 180,
  "win_rate": 0.72,
  "rating": 1850,
  "current_streak": 5,
  "longest_streak": 12,
  "total_snakes_hit": 45,
  "total_ladders_climbed": 78,
  "favorite_position": 71,
  "achievements": ["first_win", "win_10_games", "win_100_games"]
}
```

### 6. Watch Game (Spectator)
```http
POST /api/v1/games/{game_id}/spectate
Authorization: Bearer <jwt_token>

Response: 200 OK
{
  "game_id": "550e8400-e29b-41d4-a716-446655440000",
  "websocket_url": "wss://api.game.com/spectate/550e8400",
  "current_state": {
    "players": [...],
    "current_turn": 2,
    "move_number": 25
  }
}
```

### 7. Get Game Replay
```http
GET /api/v1/games/{game_id}/replay
Authorization: Bearer <jwt_token>

Response: 200 OK
{
  "game_id": "550e8400-e29b-41d4-a716-446655440000",
  "players": [...],
  "moves": [
    {
      "move_number": 1,
      "user_id": "...",
      "dice_value": 4,
      "from_position": 0,
      "to_position": 4,
      "timestamp": "2026-04-07T10:30:00Z"
    }
  ],
  "duration_seconds": 420,
  "winner": {...}
}
```

## Caching Strategy

**1. Active Game State (Redis Hash)**
```
Key: game:{game_id}
TTL: 2 hours (extend on each move)
Value: JSON of GameState
```

**2. Matchmaking Queue (Redis Sorted Set)**
```
Key: matchmaking:{skill_level}
Score: Timestamp (for FIFO)
Member: user_id
```

**3. Leaderboard (Redis Sorted Set)**
```
Key: leaderboard:global
Score: Rating
Member: user_id
```

**4. Player Sessions (Redis Hash)**
```
Key: session:{user_id}
TTL: 24 hours
Value: JWT, active_game_id, status
```

## Scalability

### WebSocket Scaling
- 300K concurrent WebSocket connections
- 30 WebSocket servers, 10K connections each
- Sticky sessions (user always connects to same server)
- Redis Pub/Sub for cross-server messaging

### Database Sharding
- Games sharded by game_id
- Users sharded by user_id
- Moves partitioned by created_at (monthly partitions)

### Horizontal Scaling
- Stateless services, scale horizontally
- Redis Cluster for distributed caching
- Kafka for async event processing

## Fault Tolerance

- **Disconnect Handling**: If player disconnects, auto-skip turn after 30 seconds
- **Game Abandonment**: If 50% players leave, mark game as abandoned
- **State Recovery**: Game state persisted to Redis, recover on reconnect
- **Idempotency**: Moves identified by unique move_id, prevent duplicate processing

## Technology Stack

| Layer | Technology |
|-------|------------|
| **Client** | React, Unity (mobile) |
| **API Gateway** | Kong |
| **WebSocket** | Spring WebSocket, Socket.io |
| **Services** | Spring Boot |
| **Cache** | Redis Cluster |
| **RDBMS** | PostgreSQL |
| **NoSQL** | MongoDB |
| **Message Queue** | Kafka |
| **Monitoring** | Prometheus, Grafana |
| **Container** | Docker, Kubernetes |

## Interview Discussion Points

### Q1: How do you ensure fair dice rolls?

**Answer**: Use cryptographic hashing:

```java
public int rollDice(String gameId, int turn) {
    // Inputs: gameId, turn, timestamp, server secret
    String input = gameId + turn + System.nanoTime() + SECRET_KEY;
    
    // SHA-256 hash
    byte[] hash = sha256(input.getBytes());
    
    // Convert to dice value (1-6)
    int value = (Math.abs(ByteBuffer.wrap(hash).getInt()) % 6) + 1;
    
    // Store dice result with hash for verification
    redis.set("dice:" + gameId + ":" + turn, 
             value + ":" + Base64.encode(hash));
    
    return value;
}
```

**Verification**: Players can verify dice roll was fair by checking hash matches.

---

### Q2: How do you handle player disconnections?

**Answer**: Implement auto-skip with reconnection grace period:

```java
@Scheduled(fixedRate = 10000) // Every 10 seconds
public void checkPlayerTimeouts() {
    Set<String> activeGames = redis.smembers("games:active");
    
    for (String gameId : activeGames) {
        GameState game = getGameState(gameId);
        Player currentPlayer = game.getCurrentPlayer();
        
        // Check if current player's turn has timed out (30 seconds)
        if (game.getLastMoveTime().isBefore(
                Instant.now().minus(30, ChronoUnit.SECONDS))) {
            
            // Auto-skip turn
            skipTurn(gameId, currentPlayer.getUserId());
            
            // Mark player as disconnected
            currentPlayer.setStatus(PlayerStatus.DISCONNECTED);
            
            // If player doesn't reconnect in 2 minutes, remove from game
            schedulePlayerRemoval(gameId, currentPlayer.getUserId(), 
                                 Duration.ofMinutes(2));
        }
    }
}
```

**Grace Period**: Allow 2 minutes to reconnect, preserve game state, send push notification.

---

### Q3: How do you implement spectator mode efficiently?

**Answer**: Use Redis Pub/Sub for broadcasting:

```java
// When move happens, publish to game channel
public void broadcastMove(String gameId, Move move) {
    // Publish to Redis channel
    redis.publish("game:" + gameId, serialize(move));
}

// Spectators subscribe to game channel
public void joinAsSpectator(String userId, String gameId) {
    // Subscribe to Redis channel
    redis.subscribe("game:" + gameId, (channel, message) -> {
        // Forward to spectator's WebSocket
        webSocketService.sendToUser(userId, deserialize(message));
    });
}
```

**Benefit**: Decouples players from spectators, scales to unlimited spectators per game.

---

### Q4: How do you prevent cheating?

**Answer**: Server-side validation:

1. **Validate Turn**: Ensure it's player's turn
2. **Validate Move**: Recalculate position server-side, reject client's position
3. **Secure Dice**: Generate dice roll on server, not client
4. **Rate Limiting**: Max 1 move per 2 seconds
5. **Detect Bots**: Track move timing patterns, flag suspicious activity

```java
public void validateMove(GameState game, String userId, int clientPosition) {
    // Recalculate position server-side
    int serverPosition = calculatePosition(game, userId);
    
    // Reject if mismatch
    if (serverPosition != clientPosition) {
        flagCheating(userId);
        throw new CheatDetectedException();
    }
}
```

---

### Q5: How do you implement tournaments?

**Answer**: Bracket system with scheduled matches:

```java
public class TournamentService {
    
    public void createTournament(int numPlayers) {
        // Create bracket (single elimination)
        TournamentBracket bracket = new TournamentBracket(numPlayers);
        
        // Schedule first round matches
        for (Match match : bracket.getRound(1)) {
            gameService.createGame(match.getPlayers(), 
                                  match.getScheduledTime());
        }
        
        // Winner of each match advances to next round
    }
    
    @KafkaListener(topics = "game.completed")
    public void handleGameCompleted(GameCompletedEvent event) {
        if (event.isTournamentGame()) {
            // Advance winner to next round
            bracket.recordWinner(event.getMatchId(), event.getWinnerId());
            
            // Schedule next match if ready
            Match nextMatch = bracket.getNextMatch();
            if (nextMatch.isReady()) {
                gameService.createGame(nextMatch.getPlayers(), 
                                      nextMatch.getScheduledTime());
            }
        }
    }
}
```

## Cost Estimation

| Component | Monthly Cost |
|-----------|--------------|
| **Compute (EKS)** | $5,000 |
| **Database (RDS)** | $2,000 |
| **Redis** | $1,000 |
| **MongoDB** | $500 |
| **Kafka** | $500 |
| **Monitoring** | $200 |
| **Total** | **$9,200/month** |

**Revenue** (assuming 10% of 1M DAU pay $5/month): $500,000/month  
**Profit**: $490,800/month

---

**Document Version**: 1.0  
**Last Updated**: 2026-04-07  
**Review Status**: Production-Ready
