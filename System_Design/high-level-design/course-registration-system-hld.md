# Course Registration System - High-Level Design

## 1. System Overview

A course registration system manages academic course enrollment for universities, handling course catalogs, student registration, waitlists, prerequisite validation, schedule conflict detection, seat capacity management, instructor assignments, grade management, and transcript generation. The system must support tens of thousands of concurrent students during registration periods, ensure no overbooking of courses, validate complex prerequisite chains, detect time conflicts, and maintain FERPA compliance for student data privacy.

## 2. Requirements

### Functional Requirements
- **Course Catalog**: Browse courses by department, level, instructor
- **Registration**: Enroll in courses with real-time availability
- **Waitlist Management**: Join waitlist for full courses
- **Prerequisite Validation**: Verify student meets prerequisites
- **Schedule Conflict Detection**: Prevent time conflicts
- **Drop/Add Period**: Modify registration during add/drop window
- **Grade Management**: Professors submit grades, students view
- **Transcript Generation**: Generate official transcripts
- **Advising**: Track degree progress, suggest courses
- **Payment Integration**: Calculate and process tuition fees

### Non-Functional Requirements
- **Scalability**: Handle 50K+ concurrent students during registration
- **Availability**: 99.9% uptime during registration periods
- **Consistency**: Strong consistency for seat availability
- **Performance**: Registration < 2s, search < 500ms
- **Fairness**: Priority registration based on seniority, time slots
- **Compliance**: FERPA-compliant data handling

## 3. Capacity Estimation

### Scale Assumptions
- **Total Students**: 50,000 students
- **Total Courses**: 5,000 courses per semester
- **Average Class Size**: 30 students
- **Registrations/Semester**: 50K students × 5 courses = 250K registrations
- **Peak Load**: 10K students registering simultaneously (first day)
- **Registration Data Size**: 2KB per registration

### Storage Estimation
- **Student Data**: 50K students × 5KB = 250MB
- **Course Data**: 5K courses × 3KB = 15MB per semester
- **Registration Data**: 250K registrations × 2KB × 8 semesters = 4GB
- **Grade History** (4 years): ~20GB
- **Total Storage**: ~30GB (with replicas: 90GB)

### Bandwidth
- **Peak Registration**: 10K students × 2KB = 20MB
- **Search Traffic**: 50K students × 10 searches × 10KB = 5GB/day
- **QPS**: Peak 200 QPS during registration window

## 4. System Architecture

```
┌──────────────┐                    ┌─────────────────┐
│   Student    │◄───────────────────┤   API Gateway   │
│   Portal     │                    │   (Rate Limit,  │
└──────────────┘                    │    Auth)        │
                                    └────────┬────────┘
┌──────────────┐                             │
│   Faculty    │◄────────────────────────────┘
│   Portal     │                             │
└──────────────┘              ┌──────────────┴──────────────┐
                              │                             │
                    ┌─────────▼─────────┐       ┌──────────▼──────────┐
                    │  Search Service   │       │ Registration Service│
                    │ (Elasticsearch)   │       │ (Strong Consistency)│
                    └───────────────────┘       └──────────┬──────────┘
                                                            │
        ┌───────────────────────────────────────────────────┼──────────┐
        │                                                   │          │
 ┌──────▼──────┐  ┌────────────┐  ┌──────────────┐  ┌────▼─────┐  ┌──▼──────┐
 │Prerequisite │  │  Schedule  │  │   Waitlist   │  │  Grade   │  │Payment  │
 │  Validator  │  │  Conflict  │  │   Service    │  │ Service  │  │Service  │
 │             │  │  Detector  │  │              │  │          │  │         │
 └──────┬──────┘  └──────┬─────┘  └──────┬───────┘  └────┬─────┘  └──┬──────┘
        │                │                │               │           │
        └────────────────┼────────────────┴───────────────┼───────────┘
                         │                                │
              ┌──────────▼────────────────────────────────▼──┐
              │    Message Queue (Kafka)                     │
              │  Topics: registrations, grades,              │
              │          notifications                       │
              └──────────┬───────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
 ┌──────▼──────┐  ┌─────▼──────┐  ┌─────▼────────┐
 │Notification │  │ Analytics  │  │   Audit      │
 │  Service    │  │  Service   │  │   Service    │
 └─────────────┘  └────────────┘  └──────────────┘

┌───────────────────────────────────────────────────────────┐
│                    Data Layer                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │ PostgreSQL   │  │    Redis     │  │Elasticsearch │   │
│  │ (Students,   │  │  (Sessions,  │  │ (Course      │   │
│  │  Courses)    │  │   Capacity)  │  │  Search)     │   │
│  └──────────────┘  └──────────────┘  └──────────────┘   │
└───────────────────────────────────────────────────────────┘
```

## 5. Core Components

### Registration Service
- **Seat Locking**: Lock seat during registration (5-minute timeout)
- **Atomic Registration**: Ensure course not overbooked
- **Idempotency**: Prevent duplicate registrations
- **Priority Handling**: Senior students get priority time slots
- **Concurrent Control**: Handle simultaneous registrations

### Prerequisite Validator
- **Graph Traversal**: Check prerequisite chain (BFS/DFS)
- **Concurrent Prerequisite**: Support AND/OR prerequisites
- **Grade Requirement**: Verify minimum grade in prerequisite
- **Waiver Support**: Honor prerequisite waivers
- **Corequisite**: Validate courses must be taken together

### Schedule Conflict Detector
- **Time Overlap**: Detect overlapping class times
- **Multi-Section**: Allow same course, different sections
- **Online Courses**: No conflict for online courses
- **Exam Conflicts**: Flag final exam conflicts
- **Lab/Lecture**: Ensure lab matches lecture section

### Waitlist Service
- **FIFO Queue**: Maintain waitlist per course
- **Auto-Enrollment**: Automatically enroll when seat opens
- **Position Tracking**: Show waitlist position
- **Expiration**: Remove if student doesn't respond within 24 hours
- **Priority Consideration**: Faculty can override waitlist order

## 6. Database Design

### Schema Design

```sql
-- Students Table
CREATE TABLE students (
    student_id INT PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    major VARCHAR(100),
    class_year INT, -- 1=Freshman, 2=Sophomore, 3=Junior, 4=Senior
    gpa DECIMAL(3,2),
    credits_completed INT DEFAULT 0,
    registration_time_slot TIMESTAMP,
    status VARCHAR(20) DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_email (email),
    INDEX idx_time_slot (registration_time_slot)
);

-- Courses Table
CREATE TABLE courses (
    course_id SERIAL PRIMARY KEY,
    course_code VARCHAR(20) UNIQUE NOT NULL,
    course_name VARCHAR(255),
    department VARCHAR(50),
    credits INT,
    level INT, -- 100, 200, 300, 400
    description TEXT,
    syllabus_url VARCHAR(500),
    INDEX idx_department (department),
    INDEX idx_level (level)
);

-- Course Sections Table
CREATE TABLE course_sections (
    section_id SERIAL PRIMARY KEY,
    course_id INT REFERENCES courses(course_id),
    section_number VARCHAR(10),
    semester VARCHAR(20), -- FALL_2026, SPRING_2027
    instructor_id INT,
    max_capacity INT,
    enrolled_count INT DEFAULT 0,
    location VARCHAR(100),
    days_of_week VARCHAR(10), -- MWF, TTH
    start_time TIME,
    end_time TIME,
    status VARCHAR(20) DEFAULT 'OPEN', -- OPEN, FULL, CLOSED
    UNIQUE(course_id, section_number, semester),
    INDEX idx_course_semester (course_id, semester),
    INDEX idx_status (status)
);

-- Prerequisites Table (supports complex prerequisite logic)
CREATE TABLE prerequisites (
    prerequisite_id SERIAL PRIMARY KEY,
    course_id INT REFERENCES courses(course_id),
    prerequisite_course_id INT REFERENCES courses(course_id),
    min_grade VARCHAR(2), -- C-, C, C+, B-, B, B+, A-, A
    prerequisite_type VARCHAR(10) DEFAULT 'AND', -- AND, OR
    INDEX idx_course (course_id)
);

-- Registrations Table (Partitioned by semester)
CREATE TABLE registrations (
    registration_id BIGSERIAL,
    student_id INT REFERENCES students(student_id),
    section_id INT REFERENCES course_sections(section_id),
    semester VARCHAR(20),
    registration_date TIMESTAMP DEFAULT NOW(),
    status VARCHAR(20) DEFAULT 'ENROLLED', -- ENROLLED, DROPPED, WITHDRAWN
    grade VARCHAR(2), -- A, A-, B+, B, etc.
    grade_points DECIMAL(3,2),
    idempotency_key VARCHAR(100) UNIQUE,
    PRIMARY KEY (registration_id, semester),
    UNIQUE(student_id, section_id, semester),
    INDEX idx_student_semester (student_id, semester),
    INDEX idx_section (section_id)
) PARTITION BY LIST (semester);

-- Create partitions per semester
CREATE TABLE registrations_fall_2026 PARTITION OF registrations
    FOR VALUES IN ('FALL_2026');

-- Waitlist Table
CREATE TABLE waitlist (
    waitlist_id BIGSERIAL PRIMARY KEY,
    student_id INT REFERENCES students(student_id),
    section_id INT REFERENCES course_sections(section_id),
    joined_at TIMESTAMP DEFAULT NOW(),
    position INT,
    notified BOOLEAN DEFAULT FALSE,
    expires_at TIMESTAMP,
    UNIQUE(student_id, section_id),
    INDEX idx_section_position (section_id, position)
);

-- Degree Requirements Table
CREATE TABLE degree_requirements (
    requirement_id SERIAL PRIMARY KEY,
    major VARCHAR(100),
    category VARCHAR(50), -- CORE, ELECTIVE, GENERAL_ED
    course_id INT REFERENCES courses(course_id),
    credits_required INT,
    required BOOLEAN DEFAULT TRUE
);

-- Academic History (for prerequisite checking)
CREATE TABLE academic_history (
    history_id BIGSERIAL PRIMARY KEY,
    student_id INT REFERENCES students(student_id),
    course_id INT REFERENCES courses(course_id),
    semester VARCHAR(20),
    grade VARCHAR(2),
    grade_points DECIMAL(3,2),
    credits INT,
    INDEX idx_student (student_id),
    INDEX idx_student_course (student_id, course_id)
);
```

## 7. API Design

### Search Courses
```http
GET /api/v1/courses/search?department=CS&level=300&semester=FALL_2026

Response: 200 OK
{
  "courses": [
    {
      "course_id": 12345,
      "course_code": "CS301",
      "course_name": "Data Structures",
      "credits": 4,
      "sections": [
        {
          "section_id": 5678,
          "section_number": "001",
          "instructor": "Dr. Smith",
          "days": "MWF",
          "time": "10:00 AM - 11:15 AM",
          "available_seats": 15,
          "max_capacity": 30,
          "location": "Room 101"
        }
      ]
    }
  ]
}
```

### Register for Course
```http
POST /api/v1/registrations
Authorization: Bearer <jwt_token>
Idempotency-Key: <unique_key>

{
  "student_id": 1001,
  "section_id": 5678,
  "semester": "FALL_2026"
}

Response: 201 Created
{
  "registration_id": 98765,
  "status": "ENROLLED",
  "course": "CS301 - Data Structures",
  "section": "001",
  "credits": 4,
  "message": "Successfully registered"
}

// If course full:
Response: 409 Conflict
{
  "error": "COURSE_FULL",
  "waitlist_available": true,
  "waitlist_position": 5
}

// If prerequisite not met:
Response: 400 Bad Request
{
  "error": "PREREQUISITE_NOT_MET",
  "required_courses": ["CS201"],
  "message": "Must complete CS201 with grade C or better"
}
```

### Check Prerequisites
```http
GET /api/v1/students/{student_id}/prerequisites/check?course_id=12345

Response: 200 OK
{
  "eligible": true,
  "prerequisites_met": [
    {
      "course_code": "CS201",
      "grade": "B+",
      "semester": "SPRING_2026"
    }
  ],
  "prerequisites_missing": []
}
```

### Join Waitlist
```http
POST /api/v1/waitlist
Authorization: Bearer <jwt_token>

{
  "student_id": 1001,
  "section_id": 5678
}

Response: 200 OK
{
  "waitlist_id": 7890,
  "position": 5,
  "estimated_chance": "MEDIUM",
  "message": "You'll be notified if a seat becomes available"
}
```

### Submit Grade (Faculty)
```http
POST /api/v1/grades
Authorization: Bearer <faculty_jwt_token>

{
  "section_id": 5678,
  "grades": [
    {"student_id": 1001, "grade": "A", "grade_points": 4.0},
    {"student_id": 1002, "grade": "B+", "grade_points": 3.3}
  ]
}

Response: 200 OK
{
  "grades_submitted": 2,
  "status": "SUCCESS"
}
```

## 8. Scalability Strategy

### Seat Locking with Redis
```python
def register_for_course(student_id, section_id):
    lock_key = f"section_lock:{section_id}"
    
    # Acquire distributed lock
    lock = redis.set(lock_key, student_id, nx=True, ex=300)
    
    if not lock:
        return {"error": "Course being modified, retry"}
    
    try:
        # Check capacity
        section = db.get_section(section_id)
        if section.enrolled_count >= section.max_capacity:
            return {"error": "COURSE_FULL"}
        
        # Increment enrolled count atomically
        new_count = redis.incr(f"enrolled:{section_id}")
        
        if new_count > section.max_capacity:
            # Rollback
            redis.decr(f"enrolled:{section_id}")
            return {"error": "COURSE_FULL"}
        
        # Create registration
        registration = db.execute("""
            INSERT INTO registrations (student_id, section_id, semester)
            VALUES (%s, %s, %s)
            ON CONFLICT (student_id, section_id, semester) DO NOTHING
            RETURNING registration_id
        """, (student_id, section_id, semester))
        
        if registration:
            # Update database
            db.execute("""
                UPDATE course_sections 
                SET enrolled_count = enrolled_count + 1
                WHERE section_id = %s
            """, (section_id,))
            
            return {"registration_id": registration.registration_id}
        else:
            # Already registered
            redis.decr(f"enrolled:{section_id}")
            return {"error": "ALREADY_REGISTERED"}
            
    finally:
        redis.delete(lock_key)
```

### Prerequisite Validation (Graph Traversal)
```python
def check_prerequisites(student_id, course_id):
    # Get prerequisites (can be AND/OR)
    prerequisites = db.query("""
        SELECT prerequisite_course_id, min_grade, prerequisite_type
        FROM prerequisites
        WHERE course_id = %s
    """, (course_id,))
    
    if not prerequisites:
        return {"eligible": True}
    
    # Get student's completed courses
    completed = db.query("""
        SELECT course_id, grade, grade_points
        FROM academic_history
        WHERE student_id = %s
    """, (student_id,))
    
    completed_map = {c.course_id: c for c in completed}
    
    # Check prerequisites (recursive for nested prerequisites)
    def check_prerequisite_group(prereqs, logic):
        results = []
        for prereq in prereqs:
            if prereq.prerequisite_course_id in completed_map:
                completed_course = completed_map[prereq.prerequisite_course_id]
                grade_met = completed_course.grade_points >= grade_to_points(prereq.min_grade)
                results.append(grade_met)
            else:
                results.append(False)
        
        if logic == 'AND':
            return all(results)
        else:  # OR
            return any(results)
    
    eligible = check_prerequisite_group(prerequisites, prerequisites[0].prerequisite_type)
    
    return {"eligible": eligible, "prerequisites": prerequisites, "completed": completed}
```

### Schedule Conflict Detection
```python
def detect_schedule_conflict(student_id, new_section_id):
    # Get student's current schedule
    current_schedule = db.query("""
        SELECT cs.days_of_week, cs.start_time, cs.end_time
        FROM registrations r
        JOIN course_sections cs ON r.section_id = cs.section_id
        WHERE r.student_id = %s AND r.status = 'ENROLLED'
    """, (student_id,))
    
    # Get new section details
    new_section = db.get_section(new_section_id)
    
    # Check for time conflicts
    for enrolled in current_schedule:
        # Check if days overlap
        days_overlap = any(day in new_section.days_of_week for day in enrolled.days_of_week)
        
        if days_overlap:
            # Check if times overlap
            time_overlap = (
                (enrolled.start_time <= new_section.start_time < enrolled.end_time) or
                (enrolled.start_time < new_section.end_time <= enrolled.end_time) or
                (new_section.start_time <= enrolled.start_time and new_section.end_time >= enrolled.end_time)
            )
            
            if time_overlap:
                return {
                    "conflict": True,
                    "conflicting_course": enrolled.course_code,
                    "time": f"{enrolled.days_of_week} {enrolled.start_time}-{enrolled.end_time}"
                }
    
    return {"conflict": False}
```

## 9. Fault Tolerance & High Availability

### Automatic Waitlist Processing
```python
def process_waitlist(section_id):
    # Check if seat available
    section = db.get_section(section_id)
    
    while section.enrolled_count < section.max_capacity:
        # Get next waitlisted student
        waitlist_entry = db.query("""
            SELECT student_id, waitlist_id
            FROM waitlist
            WHERE section_id = %s AND notified = FALSE
            ORDER BY position ASC
            LIMIT 1
        """, (section_id,))
        
        if not waitlist_entry:
            break
        
        # Notify student
        notify_student(waitlist_entry.student_id, section_id)
        
        # Mark as notified, set expiration (24 hours)
        db.execute("""
            UPDATE waitlist
            SET notified = TRUE, expires_at = NOW() + INTERVAL '24 hours'
            WHERE waitlist_id = %s
        """, (waitlist_entry.waitlist_id,))
        
        # Wait for response (check periodically)
        break  # Only process one at a time
```

### Priority Registration Time Slots
```python
def calculate_registration_time(student):
    # Priority: Credits completed (seniority)
    base_time = registration_start_date
    
    if student.credits_completed >= 90:  # Senior
        offset = 0
    elif student.credits_completed >= 60:  # Junior
        offset = 1 * 86400  # 1 day later
    elif student.credits_completed >= 30:  # Sophomore
        offset = 2 * 86400  # 2 days later
    else:  # Freshman
        offset = 3 * 86400  # 3 days later
    
    # Add random offset within day (prevent thundering herd)
    random_offset = random.randint(0, 28800)  # 0-8 hours
    
    registration_time = base_time + offset + random_offset
    
    return registration_time
```

## 10. Technology Stack

| Component | Technology | Justification |
|-----------|-----------|---------------|
| **Frontend** | React | Component-based UI |
| **API Gateway** | Kong | Rate limiting, auth |
| **Backend** | Java Spring Boot | Enterprise, complex business logic |
| **Primary DB** | PostgreSQL 14+ | ACID, partitioning |
| **Cache** | Redis Cluster | Real-time capacity tracking |
| **Search** | Elasticsearch | Course search, filtering |
| **Message Queue** | Apache Kafka | Event streaming |
| **Monitoring** | Prometheus + Grafana | Metrics, dashboards |

## 11. Interview Discussion Points

### Q1: How do you prevent course overbooking during concurrent registrations?

**Answer**: Use Redis atomic operations with distributed locks and database constraints to ensure seat count never exceeds capacity.

### Q2: How do you validate complex prerequisite chains?

**Answer**: Model prerequisites as directed graph, use BFS/DFS to traverse and check all paths. Support AND/OR logic for flexible prerequisite requirements.

### Q3: How do you handle priority registration fairly?

**Answer**: Assign time slots based on credits completed (seniority) with random offset to prevent thundering herd. Enforce registration windows at API Gateway.

### Q4: How do you detect and prevent schedule conflicts?

**Answer**: Check time overlap using interval comparison. Validate before registration, store schedule in normalized format for efficient querying.

### Q5: How do you process waitlists automatically?

**Answer**: When seat opens (drop/withdrawal), trigger background job to notify next waitlisted student. Set 24-hour expiration, auto-process if no response.

---

**End of Document**
