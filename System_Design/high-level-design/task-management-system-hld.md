# Task Management System - High-Level Design

## 1. System Overview

A Task Management System (like Jira/Trello) is a collaborative platform for managing projects, tracking tasks, assigning work, and monitoring progress. The system must support multiple project methodologies (Scrum, Kanban), handle complex workflows, provide real-time collaboration, scale to thousands of concurrent users, support rich permissions and hierarchies, integrate with external tools, and maintain audit trails for compliance.

## 2. Requirements

### Functional Requirements
- **Project Management**: Create projects, set deadlines, track progress
- **Task Management**: Create tasks (user stories, bugs, epics), subtasks, task dependencies
- **Board Views**: Kanban boards, Scrum boards, list view, calendar view
- **Workflow**: Customizable workflows (To Do, In Progress, Done), status transitions
- **Assignment**: Assign tasks to users, teams, set priority
- **Sprints**: Create sprints, sprint planning, burndown charts
- **Comments**: Add comments, mentions, attachments
- **Notifications**: Real-time alerts for task updates, mentions, assignments
- **Search & Filters**: Advanced search, saved filters, JQL-like query language
- **Labels & Tags**: Categorize tasks with labels, custom fields
- **Time Tracking**: Log work hours, estimate time, track progress
- **Reporting**: Generate reports (velocity, burndown, cumulative flow)
- **Permissions**: Role-based access control (admin, member, viewer)
- **Integrations**: GitHub, Slack, email notifications

### Non-Functional Requirements
- **Availability**: 99.9% uptime
- **Scalability**: Support 100K+ organizations, 10M+ users
- **Performance**: Task updates < 200ms, board load < 500ms
- **Consistency**: Eventual consistency for non-critical updates, strong consistency for task state
- **Real-time**: Sub-second updates for collaborative editing
- **Security**: Data isolation per organization, encryption at rest
- **Audit**: Complete audit trail for compliance

## 3. Capacity Estimation

### Scale Assumptions
- **Total Organizations**: 100K organizations
- **Total Users**: 10 million users
- **Daily Active Users (DAU)**: 2 million users
- **Tasks per Day**: 500K tasks created = 5.8 tasks/sec (peak: 50/sec)
- **Updates per Day**: 5M task updates = 58 updates/sec (peak: 500/sec)
- **Comments per Day**: 1M comments = 11.6 comments/sec
- **Average Tasks per Project**: 1000 tasks
- **Average Users per Organization**: 100 users

### Storage Estimation
- **Users**: 10M users × 5KB = 50GB
- **Organizations**: 100K orgs × 10KB = 1GB
- **Projects**: 1M projects × 20KB = 20GB
- **Tasks**: 100M tasks × 10KB = 1TB
- **Comments**: 200M comments × 1KB = 200GB
- **Attachments**: 50M files × 2MB = 100TB (stored in S3)
- **Activity Logs**: 1B events × 500 bytes = 500GB
- **Total Storage** (5 years): ~102TB (with replicas: 300TB)

### Bandwidth
- **Ingress**: 75 writes/sec × 10KB = 750KB/s
- **Egress**: 5000 reads/sec × 20KB = 100MB/s

## 4. System Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                      Client Layer                              │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐          │
│  │   Web   │  │  Desktop│  │  Mobile │  │   API   │          │
│  │ (React) │  │ Electron│  │ Native  │  │ Clients │          │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘          │
└───────┼────────────┼────────────┼────────────┼────────────────┘
        │            │            │            │
        └────────────┼────────────┼────────────┘
                     │
          ┌──────────▼──────────┐
          │  API Gateway        │
          │  - Auth             │
          │  - Rate Limiting    │
          └──────────┬──────────┘
                     │
        ┌────────────┼────────────────────┐
        │            │                    │
   ┌────▼─────┐ ┌───▼──────┐  ┌──────▼──────┐
   │ Project  │ │   Task   │  │    User     │
   │ Service  │ │  Service │  │   Service   │
   └────┬─────┘ └───┬──────┘  └──────┬──────┘
        │           │                 │
        └───────────┼─────────────────┘
                    │
        ┌───────────┼──────────────────────┐
        │           │                      │
   ┌────▼─────┐ ┌──▼────────┐  ┌──────▼──────┐
   │  Sprint  │ │  Comment  │  │ Notification│
   │ Service  │ │  Service  │  │   Service   │
   └────┬─────┘ └──┬────────┘  └──────┬──────┘
        │          │                   │
        └──────────┼───────────────────┘
                   │
        ┌──────────▼──────────────────────┐
        │   Message Queue (Kafka)         │
        │  - task.created                 │
        │  - task.updated                 │
        │  - comment.added                │
        └──────────┬──────────────────────┘
                   │
        ┌──────────┼────────────┐
        │          │            │
   ┌────▼────┐ ┌──▼──────┐ ┌───▼──────┐
   │ Search  │ │Activity │ │Reporting │
   │ Service │ │ Service │ │ Service  │
   └─────────┘ └─────────┘ └──────────┘

┌──────────────────────────────────────────────────────────────┐
│                    Data Layer                                │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐            │
│  │PostgreSQL  │  │   Redis    │  │  MongoDB   │            │
│  │ (Core Data)│  │  (Cache,   │  │ (Activity  │            │
│  │            │  │  Real-time)│  │   Logs)    │            │
│  └────────────┘  └────────────┘  └────────────┘            │
│                                                              │
│  ┌────────────┐  ┌────────────┐                            │
│  │Elasticsearch│  │  Amazon S3 │                            │
│  │  (Search)  │  │(Attachments)│                            │
│  └────────────┘  └────────────┘                            │
└──────────────────────────────────────────────────────────────┘
```

## 5. Core Components

### Task Service (Core Component)
```python
class TaskService:
    def create_task(self, task_data):
        """Create a new task"""
        with db.transaction():
            # Validate permissions
            if not self.has_permission(task_data['user_id'], task_data['project_id'], 'CREATE_TASK'):
                raise UnauthorizedException()
            
            # Generate task key (e.g., PROJ-123)
            project = get_project(task_data['project_id'])
            task_number = self.get_next_task_number(task_data['project_id'])
            task_key = f"{project.key}-{task_number}"
            
            # Create task
            task = Task(
                task_key=task_key,
                title=task_data['title'],
                description=task_data.get('description', ''),
                task_type=task_data['type'],  # STORY, BUG, EPIC, SUBTASK
                project_id=task_data['project_id'],
                reporter_id=task_data['user_id'],
                assignee_id=task_data.get('assignee_id'),
                priority=task_data.get('priority', 'MEDIUM'),
                status=task_data.get('status', 'TODO'),
                story_points=task_data.get('story_points'),
                due_date=task_data.get('due_date'),
                parent_task_id=task_data.get('parent_task_id'),
                sprint_id=task_data.get('sprint_id'),
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            db.save(task)
            
            # Process labels
            if 'labels' in task_data:
                for label_name in task_data['labels']:
                    label = self.get_or_create_label(task_data['project_id'], label_name)
                    db.save(TaskLabel(task_id=task.id, label_id=label.id))
            
            # Create activity log
            activity_service.log(
                entity_type='TASK',
                entity_id=task.id,
                user_id=task_data['user_id'],
                action='CREATED',
                changes=None
            )
            
            # Index in Elasticsearch
            search_service.index_task(task)
            
            # Emit event
            kafka.send('task.created', {
                'task_id': task.id,
                'project_id': task.project_id,
                'assignee_id': task.assignee_id
            })
            
            # Invalidate cache
            redis.delete(f"project_tasks:{task.project_id}")
            
            return task
    
    def update_task(self, task_id, updates, user_id):
        """Update task with change tracking"""
        with db.transaction():
            # Lock task for update
            task = db.query("""
                SELECT * FROM tasks WHERE task_id = ? FOR UPDATE
            """, task_id).first()
            
            if not task:
                raise NotFoundException()
            
            # Check permissions
            if not self.has_permission(user_id, task.project_id, 'EDIT_TASK'):
                raise UnauthorizedException()
            
            # Track changes
            changes = {}
            for field, new_value in updates.items():
                old_value = getattr(task, field)
                if old_value != new_value:
                    changes[field] = {'from': old_value, 'to': new_value}
                    setattr(task, field, new_value)
            
            if not changes:
                return task
            
            task.updated_at = datetime.now()
            db.save(task)
            
            # Log activity
            activity_service.log(
                entity_type='TASK',
                entity_id=task.id,
                user_id=user_id,
                action='UPDATED',
                changes=changes
            )
            
            # Update search index
            search_service.update_task(task)
            
            # Emit event
            kafka.send('task.updated', {
                'task_id': task.id,
                'changes': changes
            })
            
            # Notify assignee if assigned
            if 'assignee_id' in changes and changes['assignee_id']['to']:
                notification_service.notify(
                    changes['assignee_id']['to'],
                    f"Task {task.task_key} assigned to you",
                    task.id
                )
            
            # Invalidate caches
            redis.delete(f"task:{task_id}")
            redis.delete(f"project_tasks:{task.project_id}")
            
            return task
    
    def transition_status(self, task_id, new_status, user_id):
        """Transition task through workflow"""
        with db.transaction():
            task = get_task(task_id)
            
            # Get workflow
            workflow = workflow_service.get_workflow(task.project_id)
            
            # Validate transition
            if not workflow.can_transition(task.status, new_status):
                raise InvalidTransitionException(
                    f"Cannot transition from {task.status} to {new_status}"
                )
            
            # Update status
            old_status = task.status
            task.status = new_status
            task.updated_at = datetime.now()
            db.save(task)
            
            # Log activity
            activity_service.log(
                entity_type='TASK',
                entity_id=task.id,
                user_id=user_id,
                action='STATUS_CHANGED',
                changes={'status': {'from': old_status, 'to': new_status}}
            )
            
            # Broadcast update via WebSocket
            websocket_service.broadcast(
                f"project:{task.project_id}",
                {
                    'type': 'TASK_STATUS_CHANGED',
                    'task_id': task.id,
                    'old_status': old_status,
                    'new_status': new_status
                }
            )
            
            return task
```

### Board Service
```python
class BoardService:
    def get_kanban_board(self, project_id, user_id):
        """Get Kanban board view"""
        
        # Check cache
        cache_key = f"kanban_board:{project_id}"
        cached = redis.get(cache_key)
        if cached:
            return json.loads(cached)
        
        # Get project workflow
        workflow = workflow_service.get_workflow(project_id)
        
        # Initialize board structure
        board = {
            'columns': []
        }
        
        # Get tasks for each status column
        for status in workflow.statuses:
            tasks = db.query("""
                SELECT * FROM tasks
                WHERE project_id = ? AND status = ?
                ORDER BY position, created_at
            """, project_id, status.name).all()
            
            board['columns'].append({
                'status': status.name,
                'display_name': status.display_name,
                'tasks': [self.serialize_task(task) for task in tasks],
                'wip_limit': status.wip_limit
            })
        
        # Cache for 1 minute
        redis.setex(cache_key, 60, json.dumps(board))
        
        return board
    
    def move_task(self, task_id, new_status, new_position, user_id):
        """Move task to new column/position"""
        with db.transaction():
            task = get_task(task_id)
            
            # Update status
            self.transition_status(task_id, new_status, user_id)
            
            # Update position
            task.position = new_position
            db.save(task)
            
            # Reorder other tasks
            self.reorder_tasks(task.project_id, new_status, task.id, new_position)
            
            # Invalidate cache
            redis.delete(f"kanban_board:{task.project_id}")
            
            return task
```

### Sprint Service
```python
class SprintService:
    def create_sprint(self, sprint_data):
        """Create a sprint"""
        sprint = Sprint(
            name=sprint_data['name'],
            project_id=sprint_data['project_id'],
            start_date=sprint_data['start_date'],
            end_date=sprint_data['end_date'],
            goal=sprint_data.get('goal', ''),
            status='PLANNED',
            created_at=datetime.now()
        )
        db.save(sprint)
        return sprint
    
    def start_sprint(self, sprint_id):
        """Start a sprint"""
        sprint = get_sprint(sprint_id)
        sprint.status = 'ACTIVE'
        sprint.started_at = datetime.now()
        db.save(sprint)
        return sprint
    
    def complete_sprint(self, sprint_id):
        """Complete a sprint"""
        with db.transaction():
            sprint = get_sprint(sprint_id)
            sprint.status = 'COMPLETED'
            sprint.completed_at = datetime.now()
            db.save(sprint)
            
            # Move incomplete tasks to backlog
            incomplete_tasks = db.query("""
                SELECT * FROM tasks
                WHERE sprint_id = ? AND status != 'DONE'
            """, sprint_id).all()
            
            for task in incomplete_tasks:
                task.sprint_id = None
                db.save(task)
            
            return sprint
    
    def get_burndown_data(self, sprint_id):
        """Generate burndown chart data"""
        sprint = get_sprint(sprint_id)
        
        # Get sprint duration in days
        duration = (sprint.end_date - sprint.start_date).days
        
        # Calculate ideal burndown
        total_points = db.query("""
            SELECT SUM(story_points) FROM tasks
            WHERE sprint_id = ?
        """, sprint_id).scalar() or 0
        
        ideal_burndown = []
        for day in range(duration + 1):
            remaining = total_points * (1 - day / duration)
            ideal_burndown.append({
                'day': day,
                'remaining': remaining
            })
        
        # Calculate actual burndown
        actual_burndown = []
        current_date = sprint.start_date
        
        while current_date <= min(sprint.end_date, datetime.now().date()):
            remaining = db.query("""
                SELECT SUM(story_points) FROM tasks
                WHERE sprint_id = ? AND status != 'DONE'
                AND updated_at <= ?
            """, sprint_id, current_date).scalar() or 0
            
            actual_burndown.append({
                'date': current_date.isoformat(),
                'remaining': remaining
            })
            
            current_date += timedelta(days=1)
        
        return {
            'ideal': ideal_burndown,
            'actual': actual_burndown,
            'total_points': total_points
        }
```

### Workflow Service
```python
class WorkflowService:
    def get_workflow(self, project_id):
        """Get project workflow"""
        cached = redis.get(f"workflow:{project_id}")
        if cached:
            return json.loads(cached)
        
        workflow = db.query("""
            SELECT * FROM workflows WHERE project_id = ?
        """, project_id).first()
        
        if not workflow:
            # Use default workflow
            workflow = self.get_default_workflow()
        
        redis.setex(f"workflow:{project_id}", 3600, json.dumps(workflow))
        return workflow
    
    def get_default_workflow(self):
        """Default Scrum workflow"""
        return {
            'statuses': [
                {'name': 'TODO', 'display_name': 'To Do', 'wip_limit': None},
                {'name': 'IN_PROGRESS', 'display_name': 'In Progress', 'wip_limit': 5},
                {'name': 'CODE_REVIEW', 'display_name': 'Code Review', 'wip_limit': 3},
                {'name': 'TESTING', 'display_name': 'Testing', 'wip_limit': None},
                {'name': 'DONE', 'display_name': 'Done', 'wip_limit': None}
            ],
            'transitions': [
                {'from': 'TODO', 'to': 'IN_PROGRESS'},
                {'from': 'IN_PROGRESS', 'to': 'CODE_REVIEW'},
                {'from': 'CODE_REVIEW', 'to': 'IN_PROGRESS'},
                {'from': 'CODE_REVIEW', 'to': 'TESTING'},
                {'from': 'TESTING', 'to': 'IN_PROGRESS'},
                {'from': 'TESTING', 'to': 'DONE'}
            ]
        }
```

### Search Service
```python
class SearchService:
    def search_tasks(self, query, filters, user_id):
        """Search tasks with JQL-like syntax"""
        
        # Parse query (e.g., "project = PROJ AND status = TODO AND assignee = currentUser()")
        parsed = self.parse_query(query, user_id)
        
        # Build Elasticsearch query
        must_clauses = []
        filter_clauses = []
        
        if parsed['text_query']:
            must_clauses.append({
                "multi_match": {
                    "query": parsed['text_query'],
                    "fields": ["title^2", "description", "task_key"],
                    "fuzziness": "AUTO"
                }
            })
        
        # Apply filters
        for field, value in parsed['filters'].items():
            if field == 'project':
                filter_clauses.append({"term": {"project_id": value}})
            elif field == 'status':
                filter_clauses.append({"term": {"status": value}})
            elif field == 'assignee':
                filter_clauses.append({"term": {"assignee_id": value}})
            elif field == 'priority':
                filter_clauses.append({"term": {"priority": value}})
        
        # Execute search
        results = elasticsearch.search(
            index="tasks",
            body={
                "query": {
                    "bool": {
                        "must": must_clauses,
                        "filter": filter_clauses
                    }
                },
                "sort": parsed.get('sort', [{"created_at": "desc"}]),
                "size": 100
            }
        )
        
        return [hit['_source'] for hit in results['hits']['hits']]
```

## 6. Database Design

```sql
-- Organizations Table
CREATE TABLE organizations (
    org_id BIGSERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    subdomain VARCHAR(100) UNIQUE,
    plan VARCHAR(50), -- FREE, PREMIUM, ENTERPRISE
    created_at TIMESTAMP DEFAULT NOW()
);

-- Projects Table
CREATE TABLE projects (
    project_id BIGSERIAL PRIMARY KEY,
    org_id BIGINT REFERENCES organizations(org_id),
    name VARCHAR(255) NOT NULL,
    key VARCHAR(10) UNIQUE NOT NULL, -- e.g., PROJ
    description TEXT,
    project_type VARCHAR(50), -- SCRUM, KANBAN
    lead_id BIGINT REFERENCES users(user_id),
    created_at TIMESTAMP DEFAULT NOW(),
    is_archived BOOLEAN DEFAULT FALSE,
    INDEX idx_org (org_id)
);

-- Tasks Table
CREATE TABLE tasks (
    task_id BIGSERIAL PRIMARY KEY,
    task_key VARCHAR(20) UNIQUE NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    task_type VARCHAR(50), -- STORY, BUG, EPIC, SUBTASK
    project_id BIGINT REFERENCES projects(project_id),
    reporter_id BIGINT REFERENCES users(user_id),
    assignee_id BIGINT REFERENCES users(user_id),
    parent_task_id BIGINT REFERENCES tasks(task_id),
    sprint_id BIGINT REFERENCES sprints(sprint_id),
    priority VARCHAR(20), -- LOW, MEDIUM, HIGH, CRITICAL
    status VARCHAR(50),
    story_points INT,
    due_date DATE,
    position INT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_project (project_id),
    INDEX idx_assignee (assignee_id),
    INDEX idx_status (status),
    INDEX idx_sprint (sprint_id)
);

-- Sprints Table
CREATE TABLE sprints (
    sprint_id BIGSERIAL PRIMARY KEY,
    project_id BIGINT REFERENCES projects(project_id),
    name VARCHAR(255),
    goal TEXT,
    start_date DATE,
    end_date DATE,
    status VARCHAR(50), -- PLANNED, ACTIVE, COMPLETED
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    INDEX idx_project (project_id)
);

-- Comments Table
CREATE TABLE comments (
    comment_id BIGSERIAL PRIMARY KEY,
    task_id BIGINT REFERENCES tasks(task_id),
    user_id BIGINT REFERENCES users(user_id),
    content TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_task (task_id)
);

-- Activity Logs Table (MongoDB)
{
  "_id": ObjectId,
  "entity_type": "TASK",
  "entity_id": 123,
  "user_id": 456,
  "action": "UPDATED",
  "changes": {
    "status": {"from": "TODO", "to": "IN_PROGRESS"}
  },
  "timestamp": ISODate
}
```

## 7. API Design

### Create Task
```http
POST /api/v1/tasks
Authorization: Bearer <token>

{
  "project_id": 1,
  "title": "Implement login feature",
  "type": "STORY",
  "priority": "HIGH",
  "assignee_id": 123,
  "story_points": 5
}

Response: 201 Created
{
  "task_id": 456,
  "task_key": "PROJ-123",
  "title": "Implement login feature",
  "status": "TODO"
}
```

### Get Board
```http
GET /api/v1/projects/{project_id}/board
Authorization: Bearer <token>

Response: 200 OK
{
  "columns": [
    {
      "status": "TODO",
      "tasks": [...]
    }
  ]
}
```

## 8. Scalability Strategy

- **Database Sharding**: Shard by org_id
- **Caching**: Redis for boards, tasks
- **WebSockets**: Real-time updates
- **Message Queue**: Kafka for async processing

## 9. Technology Stack

| Component | Technology |
|-----------|-----------|
| **Backend** | Node.js, TypeScript |
| **Database** | PostgreSQL |
| **Cache** | Redis |
| **Real-time** | Socket.io |
| **Search** | Elasticsearch |
| **Queue** | Kafka |

## 10. Interview Discussion Points

### Q1: How do you handle real-time collaboration?

**Answer**: Use WebSockets to broadcast task updates to all users viewing the board. Implement optimistic UI updates with conflict resolution.

### Q2: How do you implement task dependencies?

**Answer**: Store dependencies in a separate table, use graph algorithms to detect cycles, block status transitions if dependencies not met.

### Q3: How do you scale the board view?

**Answer**: Cache board data in Redis with short TTL, use pagination for large projects, implement virtual scrolling in UI.

---

**End of Document**
