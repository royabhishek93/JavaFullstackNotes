# StackOverflow - High-Level Design

## 1. System Overview

StackOverflow is a large-scale question-and-answer platform where programmers ask technical questions, provide answers, and build reputation through community voting. The system must handle millions of users globally, support complex full-text search, implement gamification (reputation, badges), provide real-time updates, ensure content quality through voting, prevent spam and abuse, scale search infrastructure, and maintain high availability with low latency worldwide.

## 2. Requirements

### Functional Requirements
- **Question Management**: Ask questions with title, body, tags, code snippets
- **Answer Management**: Post answers, accept best answer, edit answers
- **Voting System**: Upvote/downvote questions and answers
- **Comments**: Add comments to questions and answers
- **Tags**: Categorize questions with tags, tag suggestions, tag wiki
- **Search**: Full-text search across questions, answers, users, tags
- **Reputation System**: Earn reputation points through contributions
- **Badges**: Award badges for achievements
- **User Profiles**: Track reputation, badges, activity, favorites
- **Moderation**: Flag content, close questions, delete spam
- **Favorites**: Bookmark questions for later
- **Notifications**: Alerts for answers, comments, votes, badges

### Non-Functional Requirements
- **Availability**: 99.95% uptime
- **Scalability**: Support 100M+ users, 20M+ questions
- **Performance**: Search results < 300ms, page load < 500ms
- **Consistency**: Eventual consistency for votes, strong consistency for posts
- **Search Quality**: Relevant results, typo tolerance, rank by relevance
- **Content Quality**: Prevent duplicate questions, detect spam
- **SEO**: Optimized for search engines (Google-friendly URLs)
- **Real-time**: Live updates for votes, new answers

## 3. Capacity Estimation

### Scale Assumptions
- **Total Users**: 100 million registered users
- **Daily Active Users (DAU)**: 10 million users
- **Questions per Day**: 50K questions = 0.58 questions/sec (peak: 5/sec)
- **Answers per Day**: 150K answers = 1.74 answers/sec (peak: 15/sec)
- **Votes per Day**: 5M votes = 58 votes/sec (peak: 200/sec)
- **Comments per Day**: 200K comments = 2.3 comments/sec
- **Searches per Day**: 20M searches = 231 searches/sec (peak: 1000/sec)
- **Read:Write Ratio**: 100:1 (read-heavy)

### Storage Estimation
- **Users**: 100M users × 5KB = 500GB
- **Questions**: 20M questions × 5KB = 100GB
- **Answers**: 50M answers × 3KB = 150GB
- **Comments**: 100M comments × 500 bytes = 50GB
- **Votes**: 500M votes × 20 bytes = 10GB
- **Tags**: 100K tags × 2KB = 200MB
- **Reputation History**: 100M users × 50 events × 100 bytes = 500GB
- **Search Index**: 20M questions × 10KB = 200GB
- **Total Storage** (5 years): ~1.5TB (with replicas: 4.5TB)

### Bandwidth
- **Ingress**: 2 writes/sec × 5KB = 10KB/s
- **Egress**: 2000 reads/sec × 50KB = 100MB/s

## 4. System Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                      Client Layer                              │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐                        │
│  │   Web   │  │  Mobile │  │   API   │                        │
│  │ Browser │  │   Apps  │  │ Clients │                        │
│  └────┬────┘  └────┬────┘  └────┬────┘                        │
└───────┼────────────┼────────────┼────────────────────────────┘
        │            │            │
        └────────────┼────────────┘
                     │
          ┌──────────▼──────────┐
          │   CDN (CloudFront)  │
          │  - Static Assets    │
          │  - Images           │
          └──────────┬──────────┘
                     │
          ┌──────────▼──────────┐
          │  Load Balancer      │
          │  (NGINX)            │
          └──────────┬──────────┘
                     │
        ┌────────────┼────────────────────┐
        │            │                    │
   ┌────▼────┐  ┌───▼──────┐  ┌──────▼──────┐
   │Question │  │  Answer  │  │    User     │
   │ Service │  │ Service  │  │   Service   │
   └────┬────┘  └───┬──────┘  └──────┬──────┘
        │           │                 │
        └───────────┼─────────────────┘
                    │
        ┌───────────┼──────────────────────┐
        │           │                      │
   ┌────▼─────┐ ┌──▼────────┐  ┌──────▼──────┐
   │  Vote    │ │  Comment  │  │  Reputation │
   │ Service  │ │  Service  │  │   Service   │
   └────┬─────┘ └──┬────────┘  └──────┬──────┘
        │          │                   │
        └──────────┼───────────────────┘
                   │
        ┌──────────┼────────────────────┐
        │          │                    │
   ┌────▼─────┐ ┌─▼─────────┐  ┌───────▼──────┐
   │  Search  │ │  Tag      │  │  Notification│
   │ Service  │ │  Service  │  │   Service    │
   │(Elastic) │ │           │  │              │
   └──────────┘ └───────────┘  └──────────────┘

┌──────────────────────────────────────────────────────────────┐
│                    Data Layer                                │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐            │
│  │PostgreSQL  │  │   Redis    │  │Elasticsearch│            │
│  │ (Core Data)│  │  (Cache)   │  │  (Search)  │            │
│  └────────────┘  └────────────┘  └────────────┘            │
└──────────────────────────────────────────────────────────────┘
```

## 5. Core Components

### Question Service
- **Create Question**:
```python
class QuestionService:
    def create_question(self, question_data):
        with db.transaction():
            # Validate question
            self.validate_question(question_data)
            
            # Check for duplicates
            similar = self.find_similar_questions(question_data['title'])
            if similar:
                return {"error": "Similar questions found", "similar": similar}
            
            # Create question
            question = Question(
                title=question_data['title'],
                body=question_data['body'],
                user_id=question_data['user_id'],
                created_at=datetime.now(),
                view_count=0,
                score=0
            )
            db.save(question)
            
            # Process tags
            tag_ids = tag_service.process_tags(question_data['tags'])
            for tag_id in tag_ids:
                db.save(QuestionTag(question_id=question.id, tag_id=tag_id))
            
            # Index in Elasticsearch
            search_service.index_question(question)
            
            # Award reputation
            reputation_service.award(question_data['user_id'], 'QUESTION_ASKED', 0)
            
            return question
    
    def find_similar_questions(self, title):
        """Find similar questions to prevent duplicates"""
        results = elasticsearch.search(
            index="questions",
            body={
                "query": {
                    "more_like_this": {
                        "fields": ["title", "body"],
                        "like": title,
                        "min_term_freq": 1,
                        "max_query_terms": 12
                    }
                },
                "size": 5
            }
        )
        return [hit['_source'] for hit in results['hits']['hits']]
```

### Answer Service
- **Post Answer**:
```python
class AnswerService:
    def create_answer(self, answer_data):
        with db.transaction():
            # Validate answer
            if len(answer_data['body']) < 30:
                raise ValidationException("Answer too short")
            
            # Create answer
            answer = Answer(
                question_id=answer_data['question_id'],
                body=answer_data['body'],
                user_id=answer_data['user_id'],
                created_at=datetime.now(),
                score=0,
                is_accepted=False
            )
            db.save(answer)
            
            # Update question answer count
            db.execute("""
                UPDATE questions 
                SET answer_count = answer_count + 1
                WHERE question_id = ?
            """, answer_data['question_id'])
            
            # Notify question author
            question = get_question(answer_data['question_id'])
            notification_service.notify(
                question.user_id,
                f"New answer to your question: {question.title}",
                answer.id
            )
            
            # Award reputation
            reputation_service.award(answer_data['user_id'], 'ANSWER_POSTED', 0)
            
            return answer
    
    def accept_answer(self, question_id, answer_id, user_id):
        """Mark answer as accepted (by question author)"""
        with db.transaction():
            question = get_question(question_id)
            
            # Only question author can accept
            if question.user_id != user_id:
                raise UnauthorizedException()
            
            # Unaccept previous answer if exists
            db.execute("""
                UPDATE answers 
                SET is_accepted = FALSE
                WHERE question_id = ? AND is_accepted = TRUE
            """, question_id)
            
            # Accept new answer
            db.execute("""
                UPDATE answers 
                SET is_accepted = TRUE
                WHERE answer_id = ?
            """, answer_id)
            
            # Award reputation to answer author
            answer = get_answer(answer_id)
            reputation_service.award(answer.user_id, 'ANSWER_ACCEPTED', 15)
```

### Vote Service (Critical Component)
- **Vote System**:
```python
class VoteService:
    def vote(self, user_id, entity_type, entity_id, vote_type):
        """
        Vote on question or answer
        entity_type: 'question' or 'answer'
        vote_type: 'upvote' or 'downvote'
        """
        
        # Check if user has enough reputation to downvote (requires 125 rep)
        if vote_type == 'downvote':
            user_rep = reputation_service.get_reputation(user_id)
            if user_rep < 125:
                raise InsufficientReputationException()
        
        with db.transaction():
            # Check if user already voted
            existing_vote = db.query("""
                SELECT * FROM votes
                WHERE user_id = ? AND entity_type = ? AND entity_id = ?
            """, user_id, entity_type, entity_id).first()
            
            if existing_vote:
                if existing_vote.vote_type == vote_type:
                    # Remove vote (undo)
                    db.delete(existing_vote)
                    score_delta = -1 if vote_type == 'upvote' else 1
                    rep_delta = -10 if vote_type == 'upvote' else 2
                else:
                    # Change vote
                    existing_vote.vote_type = vote_type
                    db.save(existing_vote)
                    score_delta = 2 if vote_type == 'upvote' else -2
                    rep_delta = 20 if vote_type == 'upvote' else -12
            else:
                # New vote
                vote = Vote(
                    user_id=user_id,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    vote_type=vote_type,
                    created_at=datetime.now()
                )
                db.save(vote)
                score_delta = 1 if vote_type == 'upvote' else -1
                rep_delta = 10 if vote_type == 'upvote' else -2
            
            # Update score
            table = 'questions' if entity_type == 'question' else 'answers'
            db.execute(f"""
                UPDATE {table}
                SET score = score + ?
                WHERE {entity_type}_id = ?
            """, score_delta, entity_id)
            
            # Update author's reputation
            author_id = self.get_author_id(entity_type, entity_id)
            reputation_service.award(author_id, f'{vote_type.upper()}', rep_delta)
            
            # Invalidate cache
            redis.delete(f"{entity_type}:{entity_id}")
            
            return {"score_delta": score_delta, "rep_delta": rep_delta}
    
    def get_author_id(self, entity_type, entity_id):
        if entity_type == 'question':
            return db.query("SELECT user_id FROM questions WHERE question_id = ?", entity_id).scalar()
        else:
            return db.query("SELECT user_id FROM answers WHERE answer_id = ?", entity_id).scalar()
```

### Reputation Service
- **Reputation Tracking**:
```python
class ReputationService:
    REPUTATION_EVENTS = {
        'ANSWER_ACCEPTED': 15,
        'UPVOTE': 10,
        'DOWNVOTE': -2,
        'ANSWER_UPVOTED': 10,
        'QUESTION_UPVOTED': 5,
        'ACCEPT_ANSWER': 2,  # Question author accepts an answer
        'ANSWER_DOWNVOTED': -2,
        'QUESTION_DOWNVOTED': -2,
        'SPAM_FLAGGED': -100
    }
    
    def award(self, user_id, event_type, custom_points=None):
        """Award reputation points"""
        
        points = custom_points if custom_points is not None else self.REPUTATION_EVENTS.get(event_type, 0)
        
        with db.transaction():
            # Update user reputation
            db.execute("""
                UPDATE users
                SET reputation = reputation + ?
                WHERE user_id = ?
            """, points, user_id)
            
            # Log reputation change
            db.save(ReputationHistory(
                user_id=user_id,
                event_type=event_type,
                points=points,
                created_at=datetime.now()
            ))
            
            # Invalidate cache
            redis.delete(f"reputation:{user_id}")
            
            # Check for badge eligibility
            badge_service.check_badges(user_id)
    
    def get_reputation(self, user_id):
        """Get user's current reputation"""
        cached = redis.get(f"reputation:{user_id}")
        if cached:
            return int(cached)
        
        rep = db.query("SELECT reputation FROM users WHERE user_id = ?", user_id).scalar()
        redis.setex(f"reputation:{user_id}", 300, rep)
        return rep
```

### Search Service
- **Elasticsearch Indexing**:
```python
class SearchService:
    def index_question(self, question):
        """Index question in Elasticsearch"""
        
        # Get tags
        tags = db.query("""
            SELECT t.name FROM tags t
            JOIN question_tags qt ON t.tag_id = qt.tag_id
            WHERE qt.question_id = ?
        """, question.id).all()
        
        # Index document
        elasticsearch.index(
            index="questions",
            id=question.id,
            body={
                "title": question.title,
                "body": question.body,
                "tags": [tag.name for tag in tags],
                "user_id": question.user_id,
                "score": question.score,
                "answer_count": question.answer_count,
                "view_count": question.view_count,
                "created_at": question.created_at.isoformat(),
                "is_answered": question.answer_count > 0,
                "has_accepted_answer": question.has_accepted_answer
            }
        )
    
    def search(self, query, filters=None, page=1, size=20):
        """Search questions"""
        
        # Build search query
        must_clauses = [
            {
                "multi_match": {
                    "query": query,
                    "fields": ["title^3", "body", "tags^2"],
                    "type": "best_fields",
                    "fuzziness": "AUTO"
                }
            }
        ]
        
        # Apply filters
        filter_clauses = []
        if filters:
            if 'tags' in filters:
                filter_clauses.append({"terms": {"tags": filters['tags']}})
            if 'answered' in filters:
                filter_clauses.append({"term": {"is_answered": filters['answered']}})
        
        # Execute search
        results = elasticsearch.search(
            index="questions",
            body={
                "query": {
                    "bool": {
                        "must": must_clauses,
                        "filter": filter_clauses
                    }
                },
                "sort": [
                    {"_score": "desc"},
                    {"score": "desc"},
                    {"created_at": "desc"}
                ],
                "from": (page - 1) * size,
                "size": size,
                "highlight": {
                    "fields": {
                        "title": {},
                        "body": {}
                    }
                }
            }
        )
        
        return {
            "questions": [hit['_source'] for hit in results['hits']['hits']],
            "total": results['hits']['total']['value'],
            "page": page,
            "size": size
        }
```

### Tag Service
- **Tag Management**:
```python
class TagService:
    def process_tags(self, tag_names):
        """Process and normalize tags"""
        tag_ids = []
        
        for tag_name in tag_names[:5]:  # Max 5 tags per question
            # Normalize tag name
            normalized = tag_name.lower().strip().replace(' ', '-')
            
            # Get or create tag
            tag = db.query("SELECT * FROM tags WHERE name = ?", normalized).first()
            
            if not tag:
                tag = Tag(
                    name=normalized,
                    description="",
                    usage_count=0,
                    created_at=datetime.now()
                )
                db.save(tag)
            
            # Increment usage count
            db.execute("""
                UPDATE tags SET usage_count = usage_count + 1
                WHERE tag_id = ?
            """, tag.id)
            
            tag_ids.append(tag.id)
        
        return tag_ids
    
    def suggest_tags(self, query):
        """Suggest tags based on prefix"""
        return db.query("""
            SELECT name, usage_count
            FROM tags
            WHERE name LIKE ?
            ORDER BY usage_count DESC
            LIMIT 10
        """, f"{query}%").all()
```

### Badge Service
- **Badge Awards**:
```python
class BadgeService:
    BADGES = {
        'BRONZE': [
            {'name': 'Student', 'criteria': 'first_question', 'points': 0},
            {'name': 'Teacher', 'criteria': 'first_answer', 'points': 0},
            {'name': 'Scholar', 'criteria': 'first_accepted_answer', 'points': 0}
        ],
        'SILVER': [
            {'name': 'Notable Question', 'criteria': 'question_views_2500', 'points': 0},
            {'name': 'Good Answer', 'criteria': 'answer_upvotes_25', 'points': 0}
        ],
        'GOLD': [
            {'name': 'Famous Question', 'criteria': 'question_views_10000', 'points': 0},
            {'name': 'Great Answer', 'criteria': 'answer_upvotes_100', 'points': 0}
        ]
    }
    
    def check_badges(self, user_id):
        """Check if user earned any new badges"""
        
        # Get user stats
        stats = self.get_user_stats(user_id)
        
        for badge_tier, badges in self.BADGES.items():
            for badge_def in badges:
                # Check if user already has badge
                has_badge = db.query("""
                    SELECT 1 FROM user_badges
                    WHERE user_id = ? AND badge_name = ?
                """, user_id, badge_def['name']).scalar()
                
                if has_badge:
                    continue
                
                # Check criteria
                if self.meets_criteria(stats, badge_def['criteria']):
                    self.award_badge(user_id, badge_def['name'], badge_tier)
    
    def meets_criteria(self, stats, criteria):
        if criteria == 'first_question':
            return stats['question_count'] >= 1
        elif criteria == 'first_answer':
            return stats['answer_count'] >= 1
        elif criteria == 'first_accepted_answer':
            return stats['accepted_answer_count'] >= 1
        elif criteria == 'question_views_2500':
            return stats['max_question_views'] >= 2500
        # ... more criteria
        return False
    
    def award_badge(self, user_id, badge_name, tier):
        db.save(UserBadge(
            user_id=user_id,
            badge_name=badge_name,
            tier=tier,
            awarded_at=datetime.now()
        ))
        
        notification_service.notify(user_id, f"You earned the {badge_name} badge!", None)
```

## 6. Database Design

```sql
-- Users Table
CREATE TABLE users (
    user_id BIGSERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(128),
    display_name VARCHAR(100),
    about_me TEXT,
    location VARCHAR(100),
    website VARCHAR(255),
    profile_image_url VARCHAR(500),
    reputation INT DEFAULT 1,
    badge_count_bronze INT DEFAULT 0,
    badge_count_silver INT DEFAULT 0,
    badge_count_gold INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    last_seen TIMESTAMP,
    INDEX idx_reputation (reputation),
    INDEX idx_username (username)
);

-- Questions Table
CREATE TABLE questions (
    question_id BIGSERIAL PRIMARY KEY,
    title VARCHAR(300) NOT NULL,
    body TEXT NOT NULL,
    user_id BIGINT REFERENCES users(user_id),
    score INT DEFAULT 0,
    view_count INT DEFAULT 0,
    answer_count INT DEFAULT 0,
    has_accepted_answer BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    closed_at TIMESTAMP,
    close_reason VARCHAR(100),
    is_deleted BOOLEAN DEFAULT FALSE,
    INDEX idx_user (user_id),
    INDEX idx_score (score),
    INDEX idx_created (created_at),
    FULLTEXT INDEX idx_fulltext (title, body)
);

-- Answers Table
CREATE TABLE answers (
    answer_id BIGSERIAL PRIMARY KEY,
    question_id BIGINT REFERENCES questions(question_id),
    body TEXT NOT NULL,
    user_id BIGINT REFERENCES users(user_id),
    score INT DEFAULT 0,
    is_accepted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    is_deleted BOOLEAN DEFAULT FALSE,
    INDEX idx_question (question_id),
    INDEX idx_user (user_id),
    INDEX idx_score (score)
);

-- Tags Table
CREATE TABLE tags (
    tag_id BIGSERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    usage_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_name (name),
    INDEX idx_usage (usage_count)
);

-- Question Tags Table
CREATE TABLE question_tags (
    question_id BIGINT REFERENCES questions(question_id),
    tag_id BIGINT REFERENCES tags(tag_id),
    PRIMARY KEY (question_id, tag_id),
    INDEX idx_tag (tag_id)
);

-- Votes Table
CREATE TABLE votes (
    vote_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id),
    entity_type VARCHAR(20), -- 'question' or 'answer'
    entity_id BIGINT,
    vote_type VARCHAR(20), -- 'upvote' or 'downvote'
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (user_id, entity_type, entity_id),
    INDEX idx_entity (entity_type, entity_id)
);

-- Comments Table
CREATE TABLE comments (
    comment_id BIGSERIAL PRIMARY KEY,
    entity_type VARCHAR(20), -- 'question' or 'answer'
    entity_id BIGINT,
    user_id BIGINT REFERENCES users(user_id),
    body TEXT NOT NULL,
    score INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    is_deleted BOOLEAN DEFAULT FALSE,
    INDEX idx_entity (entity_type, entity_id)
);

-- Reputation History Table
CREATE TABLE reputation_history (
    history_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id),
    event_type VARCHAR(50),
    points INT,
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_user (user_id)
);

-- Badges Table
CREATE TABLE badges (
    badge_id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    tier VARCHAR(20), -- BRONZE, SILVER, GOLD
    criteria VARCHAR(100)
);

-- User Badges Table
CREATE TABLE user_badges (
    user_id BIGINT REFERENCES users(user_id),
    badge_id INT REFERENCES badges(badge_id),
    awarded_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (user_id, badge_id),
    INDEX idx_user (user_id)
);
```

## 7. API Design

### Ask Question
```http
POST /api/v1/questions
Authorization: Bearer <token>

{
  "title": "How to reverse a linked list in Python?",
  "body": "I'm trying to reverse a linked list...",
  "tags": ["python", "linked-list", "algorithms"]
}

Response: 201 Created
{
  "question_id": 123,
  "title": "How to reverse a linked list in Python?",
  "score": 0,
  "view_count": 0,
  "created_at": "2026-04-07T10:00:00Z",
  "url": "/questions/123/how-to-reverse-linked-list-python"
}
```

### Search Questions
```http
GET /api/v1/search?q=python+django&tags=python&page=1
Authorization: Bearer <token>

Response: 200 OK
{
  "questions": [...],
  "total": 1234,
  "page": 1
}
```

### Vote
```http
POST /api/v1/questions/123/vote
Authorization: Bearer <token>

{
  "vote_type": "upvote"
}

Response: 200 OK
{
  "score": 5,
  "vote_type": "upvote"
}
```

## 8. Scalability Strategy

- **Database Sharding**: Shard by question_id % 8
- **Caching**: Redis for hot questions, user reputation
- **Search**: Elasticsearch with 10 shards
- **CDN**: Cache static content globally

## 9. Technology Stack

| Component | Technology |
|-----------|-----------|
| **Backend** | C# ASP.NET Core |
| **Database** | PostgreSQL, SQL Server |
| **Search** | Elasticsearch |
| **Cache** | Redis |
| **CDN** | CloudFlare |
| **Monitoring** | Prometheus |

## 10. Interview Discussion Points

### Q1: How do you prevent duplicate questions?

**Answer**: Use Elasticsearch "more_like_this" query to find similar questions before posting.

### Q2: How does the reputation system work?

**Answer**: Track reputation events in a separate table, update user reputation atomically in transactions.

### Q3: How do you rank search results?

**Answer**: Combine text relevance score with metadata (score, answer_count, view_count) using Elasticsearch function_score.

### Q4: How do you handle vote fraud?

**Answer**: Rate limit votes per user, detect suspicious patterns (e.g., always voting for same user), require minimum reputation for downvotes.

### Q5: How do you scale search?

**Answer**: Use Elasticsearch cluster with multiple shards and replicas, cache popular searches in Redis.

---

**End of Document**
