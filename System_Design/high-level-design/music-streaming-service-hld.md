# Music Streaming Service - High-Level Design

## System Overview
A music streaming platform like Spotify, Apple Music, or YouTube Music enables users to stream millions of songs on-demand, create and share playlists, discover new music through recommendations, download tracks for offline listening, and follow artists. The system handles massive concurrent streams, adaptive bitrate streaming for different network conditions, real-time

 personalization, and complex licensing/royalty calculations.

## Requirements

### Functional Requirements
1. **Music Catalog**: Browse 70M+ songs, albums, artists, genres, podcasts
2. **Streaming**: On-demand playback with adaptive bitrate (64kbps to 320kbps)
3. **Playlist Management**: Create, edit, share, collaborate on playlists
4. **Search & Discovery**: Search songs, artists, albums; auto-complete, fuzzy matching
5. **Personalization**: Discover Weekly, Daily Mix, Release Radar (ML-powered)
6. **Social Features**: Follow artists/users, share songs, collaborative playlists
7. **Offline Mode**: Download songs for offline playback (with DRM)
8. **Radio & Podcasts**: Internet radio stations, podcast streaming
9. **Lyrics**: Synchronized lyrics display
10. **User Library**: Save songs, albums, artists; listening history
11. **Queue Management**: Play queue, shuffle, repeat, crossfade
12. **Multi-Device**: Seamless handoff between devices (Spotify Connect)

### Non-Functional Requirements
- **Availability**: 99.99% uptime (52 minutes downtime/year)
- **Latency**: < 200ms to start streaming, < 50ms for playback control
- **Throughput**: 100M concurrent streams at peak
- **Scalability**: Support 500M users, 70M songs, 5B playlists
- **Bandwidth**: Adaptive bitrate (64-320 kbps), optimize for mobile networks
- **Storage**: 70M songs * 10MB avg = 700TB audio files
- **CDN**: 95% cache hit rate for popular songs
- **Consistency**: Eventual consistency for playlists, strong for licensing

## Capacity Estimation

### Traffic Estimates
- **Daily Active Users (DAU)**: 200M users
- **Average listening time per user**: 2 hours/day
- **Average song length**: 3.5 minutes
- **Songs played per day**: 200M * (120 / 3.5) = 6.86B songs/day
- **Songs per second**: 6.86B / 86400 = 79,398 songs/second (average)
- **Peak Streams**: 79,398 * 2 = 158,796 concurrent streams
- **Read:Write Ratio**: 99:1 (streaming vs uploads/edits)

### Storage Estimates
- **Audio Files**:
  - Total songs: 70M
  - Multiple formats: MP3 (320kbps), AAC (256kbps), OGG (160kbps)
  - Average size per song per format: 10MB
  - Total: 70M * 10MB * 3 formats = 2.1PB
  
- **Metadata**:
  - Song metadata: 70M * 5KB = 350GB
  - User profiles: 500M * 10KB = 5TB
  - Playlists: 5B * 2KB = 10TB
  - Listening history: 6.86B/day * 1KB * 365 days = 2.5TB/year
  
- **Total Storage (with replication 3x)**: 2.1PB * 3 = 6.3PB

### Bandwidth Estimates
- **Average bitrate**: 160 kbps (balanced quality)
- **Concurrent streams**: 100M (peak)
- **Total bandwidth**: 100M * 160 kbps = 16 Tbps = 2 TB/s
- **CDN costs**: $0.02/GB = 2TB/s * 86400s * $0.02 = $3.5M/day
- **Monthly bandwidth cost**: $105M

### Cache Estimates
- **Hot Songs (top 10K)**: 10K * 10MB = 100GB
- **User sessions**: 100M concurrent * 10KB = 1TB
- **Playlist cache**: 1M hot playlists * 100KB = 100GB
- **Total Cache**: 1.2TB (distributed across CDN)

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Client Applications                                │
│       (Mobile Apps, Web Player, Desktop Apps, Smart Speakers, Cars)         │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │ HTTPS/HLS/DASH
┌──────────────────────────────▼──────────────────────────────────────────────┐
│                         CDN (CloudFront/Akamai)                              │
│         (Audio Streaming, Album Art, Edge Caching, ABR)                      │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────────────┐
│                API Gateway (Kong) + Load Balancer                            │
│          (Auth, Rate Limiting, API Versioning, WebSocket)                    │
└───┬──────┬──────────┬─────────┬──────────┬──────────┬──────────┬───────────┘
    │      │          │         │          │          │          │
┌───▼──┐ ┌─▼──────┐ ┌▼────────┐ ┌▼────────┐ ┌▼───────┐ ┌▼───────┐ ┌▼───────┐
│Catalog│ │Stream │ │Playlist │ │Recommend│ │Social  │ │Search  │ │User    │
│Service│ │Service│ │Service  │ │Service  │ │Service │ │Service │ │Service │
└───┬──┘ └───┬───┘ └────┬────┘ └────┬────┘ └────┬───┘ └───┬────┘ └───┬────┘
    │        │          │           │          │         │         │
┌───▼────────▼──────────▼───────────▼──────────▼─────────▼─────────▼────┐
│                  Redis Cluster (Cache + Session)                        │
│        (User Sessions, Hot Songs, Playlist Cache, Play Queue)           │
└─────────────────────────────────┬───────────────────────────────────────┘
                                  │
┌─────────────────────────────────▼───────────────────────────────────────┐
│           PostgreSQL Cluster (Primary + Replicas)                        │
│      (Users, Songs, Albums, Artists, Playlists, Subscriptions)          │
└─────────────────────────────────┬───────────────────────────────────────┘
                                  │
┌─────────────────────────────────▼───────────────────────────────────────┐
│                Cassandra Cluster (Wide Column Store)                     │
│         (Listening History, Play Events, User Activity Logs)            │
└─────────────────────────────────┬───────────────────────────────────────┘
                                  │
┌─────────────────────────────────▼───────────────────────────────────────┐
│                  Kafka (Event Streaming Platform)                        │
│     (Play Events, Skip Events, Like Events, Analytics Events)           │
└───┬─────────┬──────────┬──────────┬───────────┬──────────┬─────────────┘
    │         │          │          │           │          │
┌───▼───┐ ┌──▼────┐ ┌───▼─────┐ ┌──▼──────┐ ┌──▼─────┐ ┌─▼────────┐
│ML     │ │Royalty│ │Analytics│ │Notif    │ │Metrics │ │Fraud     │
│Engine │ │Calc   │ │Pipeline │ │Service  │ │Aggr    │ │Detection │
│(Spark)│ │Service│ │(Flink)  │ │         │ │        │ │          │
└───────┘ └───────┘ └─────────┘ └─────────┘ └────────┘ └──────────┘

┌──────────────────────────────────────────────────────────────────┐
│                       Storage Layer                               │
├────────────────┬──────────────────────┬────────────────────────┤
│ S3/GCS         │ Elasticsearch        │ Neo4j (Graph DB)       │
│ (Audio Files)  │ (Song Search)        │ (Social Graph, Recs)   │
└────────────────┴──────────────────────┴────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│              External Integrations                                │
├───────────────┬──────────────────┬────────────────────────────┤
│ Music Labels  │ Payment Gateways │ Lyrics Providers           │
│ (Licensing)   │ (Stripe, PayPal) │ (Musixmatch, Genius)       │
└───────────────┴──────────────────┴────────────────────────────┘
```

## Core Components

### 1. Catalog Service
**Responsibilities**:
- Song, album, artist metadata management
- Genre classification and tagging
- Album art, artist photos
- Music label and licensing information
- Content ingestion pipeline

**Technology**: Spring Boot, PostgreSQL
**Cache**: Redis (hot songs, artists)
**CDN**: S3 + CloudFront (album art, metadata)

**Data Model**:
```java
@Entity
public class Song {
    @Id
    private UUID songId;
    private String title;
    private String isrc; // International Standard Recording Code
    private Integer durationMs;
    private Boolean explicit;
    private Integer releaseYear;
    private List<UUID> artistIds;
    private UUID albumId;
    private List<String> genres;
    private String audioFileKey; // S3 key
    private Map<String, String> audioFormats; // Format -> S3 key
    private Integer popularity; // 0-100
    private Instant createdAt;
}
```

### 2. Stream Service
**Responsibilities**:
- Audio streaming with adaptive bitrate
- Format transcoding (MP3, AAC, OGG, FLAC)
- CDN integration and cache warming
- Playback tracking and analytics
- DRM (Digital Rights Management)

**Technology**: Go (for high throughput), FFmpeg (transcoding)
**Storage**: S3 (audio files)
**CDN**: CloudFront with edge locations
**Protocol**: HLS (HTTP Live Streaming), DASH

**Adaptive Bitrate Streaming**:
```go
// Stream handler with ABR
func (s *StreamService) StreamSong(w http.ResponseWriter, r *http.Request) {
    songID := r.URL.Query().Get("song_id")
    quality := s.detectQuality(r) // Detect network speed
    
    // Get appropriate audio file
    audioFile, err := s.getAudioFile(songID, quality)
    if err != nil {
        http.Error(w, "Song not found", http.StatusNotFound)
        return
    }
    
    // Serve via HLS (chunked streaming)
    s.serveHLS(w, r, audioFile)
    
    // Track play event
    go s.trackPlayEvent(songID, r.Header.Get("User-ID"))
}

func (s *StreamService) detectQuality(r *http.Request) string {
    // Check user preference
    userQuality := r.Header.Get("X-Preferred-Quality")
    if userQuality != "" {
        return userQuality
    }
    
    // Check network speed (from client hint)
    downlinkMbps := r.Header.Get("Downlink")
    if downlinkMbps != "" {
        downlink, _ := strconv.ParseFloat(downlinkMbps, 64)
        
        if downlink > 5.0 {
            return "high" // 320kbps
        } else if downlink > 2.0 {
            return "normal" // 160kbps
        } else {
            return "low" // 64kbps
        }
    }
    
    return "normal" // Default
}
```

**CDN Cache Strategy**:
```
- Hot songs (top 10K): Always cached at edge
- Warm songs (top 100K): Cached on first request
- Cold songs: Origin fetch, cache for 24 hours
- Cache warming: Pre-load trending songs at 2 AM
```

### 3. Recommendation Service
**Responsibilities**:
- Personalized song recommendations
- Discover Weekly, Daily Mix generation
- Collaborative filtering (user-user, item-item)
- Content-based filtering (audio features)
- Trending and viral detection

**Technology**: Python (Scikit-learn, TensorFlow), Apache Spark
**Database**: Cassandra (user preferences), Neo4j (user graph)
**Cache**: Redis (precomputed recommendations)

**Recommendation Algorithms**:

**1. Collaborative Filtering**:
```python
class CollaborativeFiltering:
    
    def recommend_songs(self, user_id, n=30):
        # Get user's listening history
        user_songs = self.get_user_songs(user_id)
        
        # Find similar users (cosine similarity)
        similar_users = self.find_similar_users(user_id, k=100)
        
        # Get songs from similar users
        candidate_songs = self.get_songs_from_users(similar_users)
        
        # Filter out already listened songs
        new_songs = [s for s in candidate_songs if s not in user_songs]
        
        # Rank by score
        ranked = self.rank_songs(new_songs, user_id)
        
        return ranked[:n]
    
    def find_similar_users(self, user_id, k):
        # Use matrix factorization (ALS)
        user_vector = self.user_factors[user_id]
        
        # Compute cosine similarity with all users
        similarities = cosine_similarity([user_vector], self.user_factors)[0]
        
        # Get top K similar users
        top_k_indices = np.argsort(similarities)[-k-1:-1][::-1]
        
        return top_k_indices
```

**2. Content-Based Filtering**:
```python
class ContentBasedFiltering:
    
    def recommend_by_features(self, song_id, n=30):
        # Get audio features of the song
        features = self.get_audio_features(song_id)
        
        # Find songs with similar features
        similar_songs = self.find_similar_by_features(features, k=n)
        
        return similar_songs
    
    def get_audio_features(self, song_id):
        # Features from audio analysis:
        # - Tempo (BPM)
        # - Key and mode
        # - Energy (0-1)
        # - Danceability (0-1)
        # - Valence (positivity, 0-1)
        # - Acousticness (0-1)
        # - Instrumentalness (0-1)
        # - Loudness (dB)
        
        return self.feature_cache.get(song_id)
```

**3. Hybrid Approach**:
```python
class HybridRecommendation:
    
    def generate_discover_weekly(self, user_id):
        # Combine collaborative and content-based
        cf_songs = self.cf.recommend_songs(user_id, n=50)
        cb_songs = self.cb.recommend_from_user_taste(user_id, n=50)
        
        # Merge with weighted scores
        combined = self.merge_recommendations(cf_songs, cb_songs, 
                                             cf_weight=0.6, cb_weight=0.4)
        
        # Filter by freshness (avoid very recent plays)
        fresh = self.filter_by_freshness(combined, user_id)
        
        # Diversity: Ensure genre variety
        diverse = self.ensure_diversity(fresh)
        
        return diverse[:30]
```

**Precomputation**:
```python
# Generate recommendations offline (nightly batch job)
@scheduled(cron="0 2 * * *")  # 2 AM daily
def precompute_recommendations():
    for user_id in active_users:
        recommendations = hybrid.generate_discover_weekly(user_id)
        
        # Cache for 7 days
        redis.setex(f"discover_weekly:{user_id}", 
                   7 * 24 * 3600, 
                   json.dumps(recommendations))
```

### 4. Playlist Service
**Responsibilities**:
- Create, edit, delete playlists
- Add/remove songs from playlists
- Collaborative playlists (multiple editors)
- Playlist sharing and following
- Smart playlists (auto-generated)

**Technology**: Spring Boot, PostgreSQL
**Cache**: Redis (hot playlists)
**Real-time**: WebSocket (collaborative editing)

**Collaborative Editing**:
```java
@Service
public class CollaborativePlaylistService {
    
    @MessageMapping("/playlist/{playlistId}/edit")
    @SendTo("/topic/playlist/{playlistId}")
    public PlaylistUpdate handlePlaylistEdit(PlaylistEditEvent event) {
        // Optimistic locking for concurrent edits
        Playlist playlist = playlistRepository
            .findByIdWithLock(event.getPlaylistId());
        
        // Apply edit
        switch (event.getAction()) {
            case ADD_SONG:
                playlist.addSong(event.getSongId(), event.getPosition());
                break;
            case REMOVE_SONG:
                playlist.removeSong(event.getSongId());
                break;
            case REORDER:
                playlist.reorder(event.getFromIndex(), event.getToIndex());
                break;
        }
        
        // Increment version for optimistic locking
        playlist.setVersion(playlist.getVersion() + 1);
        playlistRepository.save(playlist);
        
        // Invalidate cache
        redis.del("playlist:" + event.getPlaylistId());
        
        // Broadcast to all connected clients
        return new PlaylistUpdate(playlist, event.getUserId());
    }
}
```

### 5. Search Service
**Responsibilities**:
- Full-text search for songs, artists, albums, playlists
- Auto-complete and suggestions
- Fuzzy matching for typos
- Trending searches
- Search filters (genre, year, etc.)

**Technology**: Elasticsearch
**Cache**: Redis (popular searches)

**Search Implementation**:
```json
// Elasticsearch index mapping
{
  "mappings": {
    "properties": {
      "title": {
        "type": "text",
        "analyzer": "standard",
        "fields": {
          "autocomplete": {
            "type": "search_as_you_type"
          },
          "keyword": {
            "type": "keyword"
          }
        }
      },
      "artist": {
        "type": "text",
        "analyzer": "standard"
      },
      "album": {
        "type": "text"
      },
      "genres": {
        "type": "keyword"
      },
      "popularity": {
        "type": "integer"
      },
      "release_year": {
        "type": "integer"
      }
    }
  }
}
```

```java
// Search with autocomplete and fuzzy matching
public SearchResult search(String query, SearchFilter filter) {
    BoolQueryBuilder queryBuilder = QueryBuilders.boolQuery();
    
    // Multi-match with fuzziness
    queryBuilder.must(QueryBuilders.multiMatchQuery(query)
        .field("title", 3.0f)  // Boost title matches
        .field("artist", 2.0f)
        .field("album", 1.0f)
        .fuzziness(Fuzziness.AUTO)
        .prefixLength(2));
    
    // Apply filters
    if (filter.getGenres() != null) {
        queryBuilder.filter(QueryBuilders.termsQuery("genres", 
                                                    filter.getGenres()));
    }
    
    if (filter.getYearRange() != null) {
        queryBuilder.filter(QueryBuilders.rangeQuery("release_year")
            .gte(filter.getYearRange().getFrom())
            .lte(filter.getYearRange().getTo()));
    }
    
    // Sort by relevance, then popularity
    SearchRequest searchRequest = new SearchRequest("songs")
        .source(new SearchSourceBuilder()
            .query(queryBuilder)
            .sort("_score", SortOrder.DESC)
            .sort("popularity", SortOrder.DESC)
            .size(20));
    
    SearchResponse response = esClient.search(searchRequest);
    
    return parseSearchResponse(response);
}
```

### 6. Social Service
**Responsibilities**:
- Follow/unfollow artists and users
- Activity feed (friends' listening activity)
- Share songs, albums, playlists
- Collaborative playlists
- User profiles and bio

**Technology**: Spring Boot, Neo4j (graph database)
**Cache**: Redis (friend list, feed)

**Social Graph**:
```cypher
// Neo4j graph model
(:User {userId, name, avatar})-[:FOLLOWS]->(:Artist {artistId, name})
(:User)-[:FOLLOWS]->(:User)
(:User)-[:CREATED]->(:Playlist {playlistId, name})
(:User)-[:LISTENED_TO {timestamp, count}]->(:Song)
(:User)-[:LIKED]->(:Song)
```

**Activity Feed**:
```java
public List<Activity> getActivityFeed(String userId, int limit) {
    // Get user's friends
    List<String> friends = neo4j.execute(
        "MATCH (u:User {userId: $userId})-[:FOLLOWS]->(f:User) " +
        "RETURN f.userId",
        Map.of("userId", userId)
    );
    
    // Get recent activities from friends
    List<Activity> activities = cassandra.execute(
        "SELECT * FROM user_activities " +
        "WHERE user_id IN ? " +
        "AND timestamp > ? " +
        "ORDER BY timestamp DESC " +
        "LIMIT ?",
        friends, 
        Instant.now().minus(7, ChronoUnit.DAYS),
        limit
    );
    
    return activities;
}
```

### 7. User Service
**Responsibilities**:
- User registration and authentication
- Profile management
- Subscription management (free, premium, family)
- Payment processing
- User preferences (audio quality, explicit content filter)

**Technology**: Spring Boot, PostgreSQL, Stripe
**Auth**: OAuth2, JWT
**Cache**: Redis (user sessions)

## Database Design

### PostgreSQL (Relational Data)

**Users Table**:
```sql
CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    display_name VARCHAR(100),
    country_code CHAR(2),
    subscription_tier VARCHAR(20) NOT NULL DEFAULT 'FREE',
    subscription_expires_at TIMESTAMP,
    audio_quality_preference VARCHAR(20) DEFAULT 'NORMAL',
    explicit_content_filter BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_login_at TIMESTAMP,
    CONSTRAINT chk_subscription_tier CHECK (subscription_tier IN 
        ('FREE', 'PREMIUM', 'FAMILY', 'STUDENT'))
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_subscription ON users(subscription_tier, subscription_expires_at);
```

**Songs Table**:
```sql
CREATE TABLE songs (
    song_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    isrc VARCHAR(20) UNIQUE, -- International Standard Recording Code
    duration_ms INTEGER NOT NULL,
    explicit BOOLEAN DEFAULT FALSE,
    release_year INTEGER,
    album_id UUID REFERENCES albums(album_id),
    popularity INTEGER DEFAULT 0, -- 0-100
    audio_file_key VARCHAR(500) NOT NULL, -- S3 key
    audio_formats JSONB, -- {format: s3_key}
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_songs_title ON songs USING gin(to_tsvector('english', title));
CREATE INDEX idx_songs_album ON songs(album_id);
CREATE INDEX idx_songs_popularity ON songs(popularity DESC);
CREATE INDEX idx_songs_release_year ON songs(release_year DESC);
```

**Artists Table**:
```sql
CREATE TABLE artists (
    artist_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    bio TEXT,
    genres VARCHAR(200), -- Comma-separated
    image_url VARCHAR(500),
    monthly_listeners INTEGER DEFAULT 0,
    verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_artists_name ON artists USING gin(to_tsvector('english', name));
CREATE INDEX idx_artists_listeners ON artists(monthly_listeners DESC);
```

**Albums Table**:
```sql
CREATE TABLE albums (
    album_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    album_type VARCHAR(20) NOT NULL, -- ALBUM, SINGLE, COMPILATION
    release_date DATE NOT NULL,
    cover_image_url VARCHAR(500),
    label VARCHAR(100),
    total_tracks INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_album_type CHECK (album_type IN 
        ('ALBUM', 'SINGLE', 'EP', 'COMPILATION'))
);

CREATE INDEX idx_albums_title ON albums USING gin(to_tsvector('english', title));
CREATE INDEX idx_albums_release_date ON albums(release_date DESC);
```

**Song Artists (Many-to-Many)**:
```sql
CREATE TABLE song_artists (
    song_id UUID REFERENCES songs(song_id),
    artist_id UUID REFERENCES artists(artist_id),
    role VARCHAR(50) NOT NULL DEFAULT 'PRIMARY', -- PRIMARY, FEATURED, COMPOSER
    PRIMARY KEY (song_id, artist_id, role)
);

CREATE INDEX idx_song_artists_artist ON song_artists(artist_id);
```

**Playlists Table**:
```sql
CREATE TABLE playlists (
    playlist_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES users(user_id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    is_public BOOLEAN DEFAULT TRUE,
    is_collaborative BOOLEAN DEFAULT FALSE,
    cover_image_url VARCHAR(500),
    follower_count INTEGER DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_playlists_owner ON playlists(owner_id);
CREATE INDEX idx_playlists_public ON playlists(is_public, follower_count DESC);
```

**Playlist Songs Table**:
```sql
CREATE TABLE playlist_songs (
    playlist_id UUID REFERENCES playlists(playlist_id),
    song_id UUID REFERENCES songs(song_id),
    position INTEGER NOT NULL,
    added_by UUID REFERENCES users(user_id),
    added_at TIMESTAMP NOT NULL DEFAULT NOW(),
    PRIMARY KEY (playlist_id, song_id),
    UNIQUE (playlist_id, position)
);

CREATE INDEX idx_playlist_songs_position ON playlist_songs(playlist_id, position);
```

### Cassandra (Time-Series Data)

**Listening History**:
```cql
CREATE TABLE listening_history (
    user_id UUID,
    played_at TIMESTAMP,
    song_id UUID,
    duration_ms INT,
    completion_percentage INT, -- 0-100
    skipped BOOLEAN,
    device_type TEXT,
    PRIMARY KEY (user_id, played_at)
) WITH CLUSTERING ORDER BY (played_at DESC);
```

**Play Events (for analytics)**:
```cql
CREATE TABLE play_events (
    event_id TIMEUUID PRIMARY KEY,
    user_id UUID,
    song_id UUID,
    artist_id UUID,
    album_id UUID,
    timestamp TIMESTAMP,
    duration_ms INT,
    completion_percentage INT,
    context TEXT, -- playlist, album, radio, search
    context_id UUID,
    device_type TEXT,
    country_code TEXT
);

CREATE INDEX ON play_events (song_id);
CREATE INDEX ON play_events (user_id);
```

### Neo4j (Graph Data)

**Social Graph**:
```cypher
// Users
CREATE (:User {userId: UUID, username: STRING, avatar: STRING})

// Relationships
(:User)-[:FOLLOWS {since: TIMESTAMP}]->(:Artist)
(:User)-[:FOLLOWS {since: TIMESTAMP}]->(:User)
(:User)-[:LIKED {timestamp: TIMESTAMP}]->(:Song)
(:User)-[:SAVED {timestamp: TIMESTAMP}]->(:Album)
(:Song)-[:IN_ALBUM]->(:Album)
(:Song)-[:BY_ARTIST]->(:Artist)
```

## API Design

### 1. Search Songs
```http
GET /api/v1/search?q=bohemian+rhapsody&type=track&limit=20
Authorization: Bearer <jwt_token>

Response: 200 OK
{
  "tracks": [
    {
      "song_id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "Bohemian Rhapsody",
      "artists": [
        {"artist_id": "...", "name": "Queen"}
      ],
      "album": {
        "album_id": "...",
        "title": "A Night at the Opera",
        "cover_image_url": "https://cdn.example.com/album.jpg"
      },
      "duration_ms": 354000,
      "explicit": false,
      "popularity": 95
    }
  ],
  "total": 1
}
```

### 2. Get Song Stream URL
```http
GET /api/v1/songs/{song_id}/stream?quality=high
Authorization: Bearer <jwt_token>

Response: 200 OK
{
  "stream_url": "https://cdn.example.com/stream/550e8400.m3u8",
  "format": "HLS",
  "bitrate": 320,
  "expires_at": "2026-04-07T11:00:00Z",
  "cdn_headers": {
    "X-CDN-Token": "eyJ..."
  }
}
```

### 3. Create Playlist
```http
POST /api/v1/playlists
Authorization: Bearer <jwt_token>
Content-Type: application/json

Request:
{
  "name": "Road Trip Vibes",
  "description": "Perfect songs for long drives",
  "is_public": true,
  "is_collaborative": false
}

Response: 201 Created
{
  "playlist_id": "660e8400-e29b-41d4-a716-446655440000",
  "name": "Road Trip Vibes",
  "description": "Perfect songs for long drives",
  "owner": {
    "user_id": "...",
    "username": "john_doe"
  },
  "is_public": true,
  "is_collaborative": false,
  "follower_count": 0,
  "created_at": "2026-04-07T10:30:00Z"
}
```

### 4. Add Songs to Playlist
```http
POST /api/v1/playlists/{playlist_id}/tracks
Authorization: Bearer <jwt_token>
Content-Type: application/json

Request:
{
  "song_ids": [
    "770e8400-e29b-41d4-a716-446655440000",
    "880e8400-e29b-41d4-a716-446655440000"
  ],
  "position": 0  // Insert at beginning
}

Response: 200 OK
{
  "playlist_id": "660e8400-e29b-41d4-a716-446655440000",
  "tracks_added": 2,
  "snapshot_id": "abc123"  // For conflict resolution
}
```

### 5. Get Personalized Recommendations
```http
GET /api/v1/recommendations/discover-weekly
Authorization: Bearer <jwt_token>

Response: 200 OK
{
  "playlist_id": "discover_weekly_user_123",
  "name": "Discover Weekly",
  "description": "Your weekly mixtape of fresh music",
  "tracks": [
    {
      "song_id": "...",
      "title": "New Song Title",
      "artists": [...],
      "album": {...},
      "reason": "Based on your recent listening to Queen"
    }
  ],
  "refreshes_at": "2026-04-14T00:00:00Z"
}
```

### 6. Get User's Playlists
```http
GET /api/v1/users/me/playlists?limit=20&offset=0
Authorization: Bearer <jwt_token>

Response: 200 OK
{
  "playlists": [
    {
      "playlist_id": "...",
      "name": "Road Trip Vibes",
      "description": "Perfect songs for long drives",
      "track_count": 45,
      "cover_image_url": "...",
      "is_public": true,
      "updated_at": "2026-04-07T10:30:00Z"
    }
  ],
  "total": 15,
  "has_more": false
}
```

### 7. Track Play Event
```http
POST /api/v1/play-events
Authorization: Bearer <jwt_token>
Content-Type: application/json

Request:
{
  "song_id": "550e8400-e29b-41d4-a716-446655440000",
  "played_at": "2026-04-07T10:35:00Z",
  "duration_ms": 354000,
  "completion_percentage": 95,
  "skipped": false,
  "context": "playlist",
  "context_id": "660e8400-e29b-41d4-a716-446655440000"
}

Response: 202 Accepted
{
  "event_id": "aa0e8400-e29b-41d4-a716-446655440000",
  "status": "recorded"
}
```

### 8. Follow Artist
```http
PUT /api/v1/users/me/following/artists/{artist_id}
Authorization: Bearer <jwt_token>

Response: 200 OK
{
  "artist_id": "bb0e8400-e29b-41d4-a716-446655440000",
  "name": "Queen",
  "following": true,
  "followed_at": "2026-04-07T10:40:00Z"
}
```

### 9. Get Listening History
```http
GET /api/v1/users/me/history?limit=50
Authorization: Bearer <jwt_token>

Response: 200 OK
{
  "items": [
    {
      "played_at": "2026-04-07T10:35:00Z",
      "song": {
        "song_id": "...",
        "title": "Bohemian Rhapsody",
        "artists": [...],
        "duration_ms": 354000
      },
      "context": {
        "type": "playlist",
        "id": "...",
        "name": "Road Trip Vibes"
      }
    }
  ],
  "has_more": true,
  "cursor": "eyJ..."
}
```

### 10. Download Song (Offline)
```http
POST /api/v1/songs/{song_id}/download
Authorization: Bearer <jwt_token>

Response: 200 OK
{
  "download_url": "https://cdn.example.com/download/550e8400.enc",
  "license_key": "eyJ...",  // DRM license
  "expires_at": "2026-05-07T10:00:00Z",
  "file_size_bytes": 10485760
}
```

## Caching Strategy

### Redis Cache Layers

**1. Song Metadata Cache**
```
Key Pattern: song:{song_id}
TTL: 1 hour
Value: Song JSON
```

**2. Hot Songs Cache (CDN)**
```
Key Pattern: audio:{song_id}:{quality}
TTL: 7 days
Value: Audio file (HLS segments)
Location: Edge servers worldwide
```

**3. User Session Cache**
```
Key Pattern: session:{user_id}
TTL: 24 hours
Value: JWT, preferences, current playback
```

**4. Playlist Cache**
```
Key Pattern: playlist:{playlist_id}
TTL: 5 minutes
Value: Playlist with songs
```

**5. Recommendation Cache**
```
Key Pattern: reco:discover_weekly:{user_id}
TTL: 7 days
Value: Precomputed recommendations
```

**6. Search Cache**
```
Key Pattern: search:{query_hash}
TTL: 1 hour
Value: Search results
```

## Scalability

### Horizontal Scaling
- **Stateless services**: All microservices are stateless, scale horizontally
- **CDN**: 95% of traffic served from edge (reduced origin load)
- **Database sharding**: Shard by user_id (listening history, playlists)
- **Read replicas**: 1 primary + 5 read replicas for catalog queries
- **Kafka partitions**: 100 partitions for play events (parallel processing)

### CDN Optimization
- **Cache warming**: Pre-load trending songs to edge servers
- **Geo-routing**: Route users to nearest edge location
- **Compression**: Use Opus codec for better quality at lower bitrates
- **Adaptive streaming**: HLS with multiple bitrates (64, 128, 160, 320 kbps)

### Load Balancing
- **Geographic LB**: Route to nearest data center
- **Service mesh**: Istio for inter-service communication
- **Circuit breaker**: Protect downstream services from cascading failures

## Fault Tolerance & High Availability

- **Multi-region deployment**: Active-active in 3 regions
- **Database replication**: Cross-region async replication
- **CDN failover**: Automatic origin failover
- **Circuit breaker**: Fallback to cached recommendations if ML service is down
- **Graceful degradation**: If lyrics service is down, skip lyrics display
- **Retry logic**: Exponential backoff for failed streaming requests
- **RTO**: 5 minutes, **RPO**: 1 minute

## Technology Stack

| Layer | Technology |
|-------|------------|
| **Client** | React Native, Flutter, Electron |
| **CDN** | CloudFront, Akamai |
| **API Gateway** | Kong |
| **Services** | Spring Boot, Go |
| **Message Queue** | Apache Kafka |
| **Cache** | Redis Cluster |
| **RDBMS** | PostgreSQL |
| **NoSQL** | Cassandra |
| **Graph DB** | Neo4j |
| **Search** | Elasticsearch |
| **ML** | Python, Spark, TensorFlow |
| **Storage** | S3, GCS |
| **Streaming** | HLS, DASH, FFmpeg |
| **Monitoring** | Prometheus, Grafana |
| **Logging** | ELK Stack |
| **Container** | Docker, Kubernetes |

## Interview Discussion Points

### Q1: How do you handle 100M concurrent streams without overloading the origin?

**Answer**: Multi-layered CDN strategy with edge caching:

1. **CDN Edge Locations**: 200+ edge locations worldwide
2. **Cache Hierarchy**:
   - Edge (95% hit rate): Top 10K songs always cached
   - Regional (3% hit rate): Top 100K songs cached on first request
   - Origin (2% hit rate): Cold songs fetched from S3

3. **Cache Warming**:
```python
@scheduled(cron="0 2 * * *")  # 2 AM daily
def warm_cdn_cache():
    # Get trending songs
    trending = analytics.get_trending_songs(limit=10000)
    
    # Pre-fetch to CDN edge
    for song in trending:
        for quality in ['low', 'normal', 'high']:
            cdn.warm_cache(song.audio_url, quality)
```

4. **Adaptive Bitrate**: Reduce bandwidth by 40% using ABR

**Result**: 98% of traffic served from edge, origin handles only 2% of requests

---

### Q2: How do you generate personalized recommendations efficiently?

**Answer**: Hybrid approach with offline precomputation and online serving:

**Offline (Batch Processing)**:
```python
# Run nightly on Spark cluster
def generate_all_recommendations():
    # 1. Train collaborative filtering model
    model = ALS(rank=50, maxIter=10)
    user_song_matrix = load_listening_history()
    model.fit(user_song_matrix)
    
    # 2. Generate recommendations for all active users
    for user_id in active_users:
        recommendations = model.predict(user_id, n=100)
        
        # Store in Redis for fast retrieval
        redis.setex(f"reco:{user_id}", 7*24*3600, recommendations)
```

**Online (Real-time Adjustment)**:
```python
def get_recommendations(user_id):
    # Fetch precomputed recommendations
    base_reco = redis.get(f"reco:{user_id}")
    
    # Real-time adjustments
    recent_plays = cassandra.get_recent_plays(user_id, hours=24)
    
    # Filter out recently played songs
    filtered = [s for s in base_reco if s not in recent_plays]
    
    # Boost based on current context (time of day, mood)
    boosted = apply_contextual_boost(filtered, user_id)
    
    return boosted[:30]
```

**Trade-offs**:
- Precomputation: High accuracy, stale data (refreshed weekly)
- Real-time: Lower accuracy, fresh data
- Hybrid: Best of both worlds

---

### Q3: How do you calculate royalties for millions of plays per day?

**Answer**: Async event processing with Kafka and batch aggregation:

```java
// 1. Track every play event to Kafka
@PostMapping("/play-events")
public void trackPlay(PlayEvent event) {
    kafkaProducer.send("play_events", event);
}

// 2. Kafka consumer aggregates plays per song per day
@KafkaListener(topics = "play_events")
public void aggregatePlays(PlayEvent event) {
    String key = event.getSongId() + ":" + LocalDate.now();
    
    // Increment play count in Redis
    redis.incr("plays:" + key);
}

// 3. Nightly batch job calculates royalties
@Scheduled(cron = "0 3 * * *")  // 3 AM daily
public void calculateRoyalties() {
    LocalDate yesterday = LocalDate.now().minusDays(1);
    
    // Get all plays from Redis
    Map<String, Long> plays = redis.getAll("plays:*:" + yesterday);
    
    // Calculate royalty per song
    for (Entry<String, Long> entry : plays.entrySet()) {
        String songId = entry.getKey().split(":")[1];
        long playCount = entry.getValue();
        
        Song song = songRepository.findById(songId);
        BigDecimal royaltyPerPlay = calculateRoyaltyRate(song);
        BigDecimal totalRoyalty = royaltyPerPlay.multiply(new BigDecimal(playCount));
        
        // Distribute to rights holders
        distributeRoyalty(song, totalRoyalty);
    }
}
```

**Royalty Distribution**:
- Record label: 60%
- Artist: 30%
- Songwriter: 10%

---

### Q4: How do you implement offline mode with DRM?

**Answer**: Encrypted download with license key:

```java
@PostMapping("/songs/{songId}/download")
public DownloadResponse downloadSong(String songId, String userId) {
    // 1. Verify user has premium subscription
    User user = userService.getUser(userId);
    if (user.getSubscriptionTier() == SubscriptionTier.FREE) {
        throw new FeatureNotAvailableException("Offline mode requires premium");
    }
    
    // 2. Check download limit (premium: 10K songs)
    int downloadCount = downloadRepository.countByUserId(userId);
    if (downloadCount >= 10000) {
        throw new DownloadLimitExceededException();
    }
    
    // 3. Generate encrypted download URL
    String encryptedFileKey = encryptionService.encrypt(song.getAudioFileKey());
    String downloadUrl = s3.generatePresignedUrl(encryptedFileKey, Duration.ofHours(1));
    
    // 4. Generate DRM license key
    DRMLicense license = drmService.generateLicense(userId, songId, Duration.ofDays(30));
    
    // 5. Track download
    downloadRepository.save(new Download(userId, songId, Instant.now()));
    
    return new DownloadResponse(downloadUrl, license.getKey(), license.getExpiresAt());
}

// Client-side decryption
class OfflinePlayer {
    fun play(encryptedFile: File, licenseKey: String) {
        // Verify license is valid
        if (!drmClient.verifyLicense(licenseKey)) {
            throw LicenseExpiredException()
        }
        
        // Decrypt audio
        val decryptedAudio = decrypt(encryptedFile, licenseKey)
        
        // Play
        mediaPlayer.play(decryptedAudio)
    }
}
```

**DRM Enforcement**:
- Encrypted files cannot be played without valid license
- License expires after 30 days
- License revoked if subscription ends
- Max 3 devices per user

---

### Q5: How do you handle graceful degradation when recommendation service is down?

**Answer**: Multi-layered fallback strategy:

```java
@Service
public class RecommendationService {
    
    @CircuitBreaker(name = "mlRecommendation", fallbackMethod = "fallbackRecommendation")
    public List<Song> getRecommendations(String userId) {
        // Primary: ML-powered personalized recommendations
        return mlService.getPersonalizedRecommendations(userId);
    }
    
    // Fallback 1: Cached recommendations
    public List<Song> fallbackRecommendation(String userId, Exception e) {
        List<Song> cached = redis.get("reco:" + userId);
        if (cached != null) {
            return cached;
        }
        
        // Fallback 2: Rule-based recommendations
        return fallbackRuleBased(userId, e);
    }
    
    // Fallback 2: Simple rule-based recommendations
    public List<Song> fallbackRuleBased(String userId, Exception e) {
        // Get user's top genres
        List<String> topGenres = userService.getTopGenres(userId);
        
        // Get popular songs in those genres
        List<Song> songs = songRepository.findPopularByGenres(topGenres, 30);
        
        if (!songs.isEmpty()) {
            return songs;
        }
        
        // Fallback 3: Global trending songs
        return fallbackTrending(userId, e);
    }
    
    // Fallback 3: Global trending (always works)
    public List<Song> fallbackTrending(String userId, Exception e) {
        return songRepository.findTrending(30);
    }
}
```

**Fallback Hierarchy**:
1. **ML-powered recommendations** (best quality, requires ML service)
2. **Cached recommendations** (good quality, 7-day stale data)
3. **Rule-based recommendations** (okay quality, based on user's genres)
4. **Global trending** (lowest quality, always available)

**Result**: System never fails to show recommendations, even if ML service is completely down

## Cost Estimation

| Component | Monthly Cost |
|-----------|--------------|
| **Compute** | $50,000 |
| **Database** | $30,000 |
| **Storage (S3)** | $16,000 |
| **CDN (Bandwidth)** | $105,000,000 |
| **Kafka** | $10,000 |
| **Redis** | $5,000 |
| **ML Infrastructure** | $20,000 |
| **Monitoring** | $5,000 |
| **Total** | **$105,136,000/month** |

**Revenue** (assuming 50M premium users @ $10/month): $500M/month  
**Profit**: $395M/month

---

**Document Version**: 1.0  
**Last Updated**: 2026-04-07  
**Review Status**: Production-Ready
