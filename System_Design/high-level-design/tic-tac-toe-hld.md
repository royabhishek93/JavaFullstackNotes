# Tic-Tac-Toe Online Multiplayer - High-Level Design

## 1. System Overview

An online multiplayer Tic-Tac-Toe game is a real-time gaming platform that allows players to compete against each other over the internet. The system must support real-time gameplay with minimal latency, implement matchmaking to pair players, handle game state synchronization, detect and prevent cheating, support multiple concurrent games, provide leaderboards and rankings, scale to millions of concurrent players, and maintain game history for replay and analytics.

## 2. Requirements

### Functional Requirements
- **User Management**: Registration, authentication, player profiles
- **Matchmaking**: Random matchmaking, play with friends, skill-based matching
- **Game Session**: Create game, join game, real-time moves, turn management
- **Game Rules**: Validate moves, detect win/draw conditions
- **Real-time Communication**: WebSocket for instant move updates
- **Chat**: In-game chat between players
- **Leaderboard**: Global rankings, win/loss statistics
- **Game History**: Store completed games, replay capability
- **Spectator Mode**: Watch ongoing games
- **Rematch**: Request rematch after game ends
- **Timeouts**: Auto-forfeit if player doesn't move within time limit

### Non-Functional Requirements
- **Latency**: Move propagation < 100ms
- **Availability**: 99.9% uptime
- **Scalability**: Support 10M+ concurrent players, 5M+ simultaneous games
- **Consistency**: Strong consistency for game state
- **Security**: Prevent move manipulation, cheat detection
- **Real-time**: WebSocket connections for all active games
- **Fairness**: Fair matchmaking, timeout handling

## 3. Capacity Estimation

### Scale Assumptions
- **Total Users**: 50 million registered users
- **Daily Active Users (DAU)**: 5 million users
- **Concurrent Players**: 500K concurrent active players
- **Concurrent Games**: 250K simultaneous games
- **Average Game Duration**: 3 minutes
- **Games per Day**: 10M games
- **Moves per Game**: Average 7 moves
- **Total Moves per Day**: 70M moves = 810 moves/sec (peak: 5000/sec)

### Storage Estimation
- **Users**: 50M users × 5KB = 250GB
- **Game Sessions**: 10M games/day × 2KB × 365 = 7.3TB/year
- **Moves History**: 70M moves/day × 200 bytes × 365 = 5.11TB/year
- **Leaderboard Data**: 50M users × 500 bytes = 25GB
- **Chat Messages**: 20M messages/day × 500 bytes × 365 = 3.65TB/year
- **Total Storage** (5 years): ~80TB (with replicas: 240TB)

### Bandwidth
- **WebSocket Traffic**: 500K connections × 1KB/sec = 500MB/s
- **Move Updates**: 810 moves/sec × 2KB = 1.62MB/s

### Computation
- **Game State Updates**: 810 updates/sec
- **Matchmaking**: 2M matchmaking requests/day = 23 requests/sec

## 4. System Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                      Client Layer                              │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐                        │
│  │   Web   │  │   iOS   │  │ Android │                        │
│  │(React)  │  │  Swift  │  │ Kotlin  │                        │
│  └────┬────┘  └────┬────┘  └────┬────┘                        │
└───────┼────────────┼────────────┼────────────────────────────┘
        │            │            │
        └────────────┼────────────┘
                     │
          ┌──────────▼──────────┐
          │  Load Balancer      │
          │  (WebSocket-aware)  │
          └──────────┬──────────┘
                     │
        ┌────────────┼────────────────────┐
        │            │                    │
   ┌────▼────┐  ┌───▼──────┐  ┌──────▼──────┐
   │ Game    │  │  Match   │  │    User     │
   │ Server  │  │  Making  │  │   Service   │
   │ (WS)    │  │  Service │  │             │
   └────┬────┘  └───┬──────┘  └──────┬──────┘
        │           │                 │
        └───────────┼─────────────────┘
                    │
        ┌───────────┼──────────────────┐
        │           │                  │
   ┌────▼─────┐ ┌──▼────────┐  ┌──────▼──────┐
   │  Game    │ │Leaderboard│  │    Chat     │
   │  State   │ │  Service  │  │   Service   │
   │  Service │ │           │  │             │
   └────┬─────┘ └──┬────────┘  └──────┬──────┘
        │          │                   │
        └──────────┼───────────────────┘
                   │
        ┌──────────▼──────────────────────┐
        │   Message Queue (Redis Pub/Sub) │
        │  - game.move                    │
        │  - game.end                     │
        └──────────┬──────────────────────┘
                   │
        ┌──────────┼────────────┐
        │          │            │
   ┌────▼────┐ ┌──▼──────┐ ┌───▼──────┐
   │Analytics│ │ History │ │  Notif.  │
   │ Service │ │ Service │ │  Service │
   └─────────┘ └─────────┘ └──────────┘

┌──────────────────────────────────────────────────────────────┐
│                    Data Layer                                │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐            │
│  │PostgreSQL  │  │   Redis    │  │  MongoDB   │            │
│  │ (Users,    │  │ (Active    │  │  (Game     │            │
│  │Leaderboard)│  │  Games)    │  │  History)  │            │
│  └────────────┘  └────────────┘  └────────────┘            │
└──────────────────────────────────────────────────────────────┘
```

## 5. Core Components

### Game Server (Critical Component)
```python
class GameServer:
    def __init__(self):
        self.active_connections = {}  # {user_id: websocket}
        self.redis = Redis()
    
    async def handle_connection(self, websocket, user_id):
        """Handle WebSocket connection"""
        
        # Register connection
        self.active_connections[user_id] = websocket
        
        try:
            async for message in websocket:
                await self.handle_message(user_id, message)
        except WebSocketDisconnect:
            await self.handle_disconnect(user_id)
        finally:
            del self.active_connections[user_id]
    
    async def handle_message(self, user_id, message):
        """Handle incoming messages"""
        
        data = json.loads(message)
        message_type = data['type']
        
        if message_type == 'MAKE_MOVE':
            await self.handle_move(user_id, data)
        elif message_type == 'CHAT_MESSAGE':
            await self.handle_chat(user_id, data)
        elif message_type == 'RESIGN':
            await self.handle_resign(user_id)
    
    async def handle_move(self, user_id, data):
        """Process player move"""
        
        game_id = data['game_id']
        position = data['position']  # 0-8 for 3x3 grid
        
        # Get game state from Redis
        game_state = self.redis.hgetall(f"game:{game_id}")
        
        if not game_state:
            await self.send_error(user_id, "Game not found")
            return
        
        # Validate move
        validation_result = self.validate_move(game_state, user_id, position)
        if not validation_result['valid']:
            await self.send_error(user_id, validation_result['error'])
            return
        
        # Apply move
        new_state = self.apply_move(game_state, user_id, position)
        
        # Check win condition
        game_result = self.check_game_end(new_state)
        
        if game_result:
            # Game ended
            new_state['status'] = 'COMPLETED'
            new_state['result'] = game_result
            new_state['ended_at'] = datetime.now().isoformat()
            
            # Update database
            await self.save_game_result(game_id, game_result)
            
            # Update leaderboard
            await leaderboard_service.update_stats(
                winner_id=game_result.get('winner_id'),
                loser_id=game_result.get('loser_id')
            )
        
        # Save state to Redis
        self.redis.hmset(f"game:{game_id}", new_state)
        
        # Broadcast move to both players
        await self.broadcast_game_state(game_id, new_state)
    
    def validate_move(self, game_state, user_id, position):
        """Validate if move is legal"""
        
        # Check if it's player's turn
        if game_state['current_turn'] != user_id:
            return {'valid': False, 'error': 'Not your turn'}
        
        # Check if position is valid (0-8)
        if position < 0 or position > 8:
            return {'valid': False, 'error': 'Invalid position'}
        
        # Check if position is empty
        board = json.loads(game_state['board'])
        if board[position] is not None:
            return {'valid': False, 'error': 'Position already occupied'}
        
        # Check timeout
        last_move_time = datetime.fromisoformat(game_state['last_move_time'])
        if (datetime.now() - last_move_time).seconds > TURN_TIMEOUT:
            return {'valid': False, 'error': 'Move timeout'}
        
        return {'valid': True}
    
    def apply_move(self, game_state, user_id, position):
        """Apply move to game state"""
        
        board = json.loads(game_state['board'])
        
        # Determine player symbol (X or O)
        symbol = 'X' if user_id == game_state['player_x_id'] else 'O'
        
        # Update board
        board[position] = symbol
        
        # Switch turn
        next_player = (
            game_state['player_o_id'] 
            if user_id == game_state['player_x_id'] 
            else game_state['player_x_id']
        )
        
        # Update state
        new_state = dict(game_state)
        new_state['board'] = json.dumps(board)
        new_state['current_turn'] = next_player
        new_state['last_move_time'] = datetime.now().isoformat()
        new_state['move_count'] = int(game_state['move_count']) + 1
        
        return new_state
    
    def check_game_end(self, game_state):
        """Check if game has ended (win or draw)"""
        
        board = json.loads(game_state['board'])
        
        # Winning combinations
        winning_combos = [
            [0, 1, 2], [3, 4, 5], [6, 7, 8],  # Rows
            [0, 3, 6], [1, 4, 7], [2, 5, 8],  # Columns
            [0, 4, 8], [2, 4, 6]              # Diagonals
        ]
        
        # Check for win
        for combo in winning_combos:
            if (board[combo[0]] and 
                board[combo[0]] == board[combo[1]] == board[combo[2]]):
                
                winner_symbol = board[combo[0]]
                winner_id = (
                    game_state['player_x_id'] 
                    if winner_symbol == 'X' 
                    else game_state['player_o_id']
                )
                loser_id = (
                    game_state['player_o_id'] 
                    if winner_id == game_state['player_x_id'] 
                    else game_state['player_x_id']
                )
                
                return {
                    'type': 'WIN',
                    'winner_id': winner_id,
                    'loser_id': loser_id,
                    'winning_combo': combo
                }
        
        # Check for draw
        if all(cell is not None for cell in board):
            return {
                'type': 'DRAW',
                'player_x_id': game_state['player_x_id'],
                'player_o_id': game_state['player_o_id']
            }
        
        # Game continues
        return None
    
    async def broadcast_game_state(self, game_id, game_state):
        """Send game state to both players"""
        
        player_x_id = game_state['player_x_id']
        player_o_id = game_state['player_o_id']
        
        message = {
            'type': 'GAME_UPDATE',
            'game_id': game_id,
            'board': json.loads(game_state['board']),
            'current_turn': game_state['current_turn'],
            'status': game_state.get('status', 'IN_PROGRESS'),
            'result': game_state.get('result')
        }
        
        # Send to both players
        if player_x_id in self.active_connections:
            await self.active_connections[player_x_id].send(json.dumps(message))
        
        if player_o_id in self.active_connections:
            await self.active_connections[player_o_id].send(json.dumps(message))
```

### Matchmaking Service
```python
class MatchmakingService:
    def __init__(self):
        self.redis = Redis()
        self.matchmaking_queue = "matchmaking:queue"
    
    def add_to_queue(self, user_id, skill_rating):
        """Add player to matchmaking queue"""
        
        # Check if player already in queue
        if self.redis.sismember(f"matchmaking:active", user_id):
            raise AlreadyInQueueException()
        
        # Add to sorted set (sorted by skill rating)
        self.redis.zadd(self.matchmaking_queue, {user_id: skill_rating})
        self.redis.sadd(f"matchmaking:active", user_id)
        
        # Start matchmaking
        match = self.find_match(user_id, skill_rating)
        
        return match
    
    def find_match(self, user_id, skill_rating):
        """Find suitable opponent"""
        
        # Get players with similar skill rating (±100 points)
        min_rating = skill_rating - 100
        max_rating = skill_rating + 100
        
        candidates = self.redis.zrangebyscore(
            self.matchmaking_queue,
            min_rating,
            max_rating
        )
        
        # Remove self from candidates
        candidates = [c for c in candidates if c != user_id]
        
        if not candidates:
            return None
        
        # Match with first candidate
        opponent_id = candidates[0]
        
        # Remove both players from queue
        self.redis.zrem(self.matchmaking_queue, user_id, opponent_id)
        self.redis.srem(f"matchmaking:active", user_id, opponent_id)
        
        # Create game
        game = self.create_game(user_id, opponent_id)
        
        return game
    
    def create_game(self, player_x_id, player_o_id):
        """Create new game session"""
        
        game_id = str(uuid.uuid4())
        
        # Initialize game state
        game_state = {
            'game_id': game_id,
            'player_x_id': player_x_id,
            'player_o_id': player_o_id,
            'board': json.dumps([None] * 9),
            'current_turn': player_x_id,  # X starts
            'status': 'IN_PROGRESS',
            'started_at': datetime.now().isoformat(),
            'last_move_time': datetime.now().isoformat(),
            'move_count': 0
        }
        
        # Store in Redis (expires in 1 hour)
        self.redis.hmset(f"game:{game_id}", game_state)
        self.redis.expire(f"game:{game_id}", 3600)
        
        # Add to player's active games
        self.redis.sadd(f"user_games:{player_x_id}", game_id)
        self.redis.sadd(f"user_games:{player_o_id}", game_id)
        
        return {
            'game_id': game_id,
            'opponent_id': player_o_id,
            'your_symbol': 'X',
            'starts': True
        }
```

### Leaderboard Service
```python
class LeaderboardService:
    def __init__(self):
        self.redis = Redis()
    
    async def update_stats(self, winner_id, loser_id):
        """Update player statistics after game"""
        
        with db.transaction():
            # Update winner stats
            db.execute("""
                UPDATE users
                SET wins = wins + 1,
                    total_games = total_games + 1,
                    rating = rating + 10
                WHERE user_id = ?
            """, winner_id)
            
            # Update loser stats
            db.execute("""
                UPDATE users
                SET losses = losses + 1,
                    total_games = total_games + 1,
                    rating = rating - 5
                WHERE user_id = ?
            """, loser_id)
        
        # Update Redis leaderboard (sorted set by rating)
        winner_rating = self.get_user_rating(winner_id)
        loser_rating = self.get_user_rating(loser_id)
        
        self.redis.zadd("leaderboard:global", {
            winner_id: winner_rating,
            loser_id: loser_rating
        })
        
        # Invalidate cache
        self.redis.delete(f"stats:{winner_id}")
        self.redis.delete(f"stats:{loser_id}")
    
    def get_leaderboard(self, page=1, limit=100):
        """Get global leaderboard"""
        
        start = (page - 1) * limit
        end = start + limit - 1
        
        # Get top players from Redis sorted set
        top_players = self.redis.zrevrange(
            "leaderboard:global",
            start,
            end,
            withscores=True
        )
        
        # Fetch player details
        leaderboard = []
        for user_id, rating in top_players:
            user = get_user(user_id)
            leaderboard.append({
                'rank': start + len(leaderboard) + 1,
                'user_id': user_id,
                'username': user.username,
                'rating': int(rating),
                'wins': user.wins,
                'losses': user.losses,
                'total_games': user.total_games,
                'win_rate': user.wins / user.total_games if user.total_games > 0 else 0
            })
        
        return leaderboard
```

### Timeout Handler
```python
class TimeoutHandler:
    TURN_TIMEOUT = 30  # seconds
    
    async def check_timeouts(self):
        """Periodic job to check for timed out games"""
        
        while True:
            await asyncio.sleep(5)  # Check every 5 seconds
            
            # Get all active games
            game_keys = redis.keys("game:*")
            
            for game_key in game_keys:
                game_state = redis.hgetall(game_key)
                
                if game_state['status'] != 'IN_PROGRESS':
                    continue
                
                last_move_time = datetime.fromisoformat(game_state['last_move_time'])
                elapsed = (datetime.now() - last_move_time).seconds
                
                if elapsed > self.TURN_TIMEOUT:
                    # Timeout occurred
                    current_player = game_state['current_turn']
                    opponent = (
                        game_state['player_o_id'] 
                        if current_player == game_state['player_x_id'] 
                        else game_state['player_x_id']
                    )
                    
                    # Award win to opponent
                    await self.forfeit_game(
                        game_state['game_id'],
                        loser_id=current_player,
                        winner_id=opponent,
                        reason='TIMEOUT'
                    )
```

## 6. Database Design

```sql
-- Users Table
CREATE TABLE users (
    user_id BIGSERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(128),
    rating INT DEFAULT 1000,
    wins INT DEFAULT 0,
    losses INT DEFAULT 0,
    draws INT DEFAULT 0,
    total_games INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    last_active TIMESTAMP,
    INDEX idx_rating (rating),
    INDEX idx_username (username)
);

-- Games Table (MongoDB)
{
  "_id": ObjectId,
  "game_id": "uuid",
  "player_x_id": 123,
  "player_o_id": 456,
  "moves": [
    {"player": "X", "position": 4, "timestamp": ISODate},
    {"player": "O", "position": 0, "timestamp": ISODate}
  ],
  "result": {
    "type": "WIN",
    "winner_id": 123,
    "winning_combo": [0, 4, 8]
  },
  "started_at": ISODate,
  "ended_at": ISODate,
  "duration_seconds": 180
}
```

## 7. API Design

### Create Game
```http
POST /api/v1/matchmaking/find
Authorization: Bearer <token>

Response: 200 OK
{
  "game_id": "uuid",
  "opponent": {
    "user_id": 456,
    "username": "player2"
  },
  "your_symbol": "X",
  "starts": true
}
```

### WebSocket Messages
```javascript
// Client → Server: Make move
{
  "type": "MAKE_MOVE",
  "game_id": "uuid",
  "position": 4
}

// Server → Client: Game update
{
  "type": "GAME_UPDATE",
  "board": ["X", null, "O", ...],
  "current_turn": "user_id",
  "status": "IN_PROGRESS"
}

// Server → Client: Game ended
{
  "type": "GAME_END",
  "result": {
    "type": "WIN",
    "winner_id": 123,
    "winning_combo": [0, 4, 8]
  }
}
```

## 8. Scalability Strategy

- **Game State**: Store in Redis for fast access
- **WebSocket**: Distribute connections across multiple servers
- **Matchmaking**: Redis sorted sets for efficient matching
- **Leaderboard**: Redis sorted sets, cached rankings

## 9. Technology Stack

| Component | Technology |
|-----------|-----------|
| **Backend** | Node.js, WebSocket |
| **Database** | PostgreSQL, Redis |
| **Game History** | MongoDB |
| **Real-time** | Socket.io |
| **Cache** | Redis |

## 10. Interview Discussion Points

### Q1: How do you prevent cheating?

**Answer**: Server-side validation of all moves, rate limiting, detect impossible move patterns.

### Q2: How do you handle disconnections?

**Answer**: Buffer game state for 30 seconds, allow reconnection, forfeit if timeout exceeded.

### Q3: How do you scale WebSocket connections?

**Answer**: Use sticky sessions with load balancer, Redis pub/sub for cross-server communication.

---

**End of Document**
