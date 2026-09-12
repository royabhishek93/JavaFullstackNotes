# 📁 File System - Low Level Design Interview Guide
## _15 YOE Architect-Level Conversational Script_

**📘 Difficulty: Intermediate** — assumes you already know the core patterns; focuses on applying them to a real, moderately complex system.

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

## **Design Pattern Used**: Composite Pattern

**Interviewer**: "Design a File System (like Unix directory structure)."

**You**: "Perfect textbook question for **Composite Pattern**! The core insight: **A directory contains files AND other directories - both should be treated uniformly through a common interface (recursive tree structure).**"

---

## 1. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                   FILE SYSTEM ARCHITECTURE                           │
└─────────────────────────────────────────────────────────────────────┘

                    ┌──────────────────────┐
                    │   FileSystemEntry     │  ◄── Common Interface (Composite Pattern)
                    │     (interface)       │
                    │                       │
                    │  getSize()            │
                    │  getName()            │
                    │  delete()             │
                    │  ls()                 │
                    └───────────┬───────────┘
                                │
                  ┌─────────────┴─────────────┐
                  ▼                           ▼
        ┌──────────────────┐        ┌──────────────────┐
        │       FILE        │        │    DIRECTORY      │
        │     (Leaf)        │        │   (Composite)     │
        │                   │        │                   │
        │  content: bytes   │        │  children: List<   │
        │  size: long       │        │   FileSystemEntry> │
        │                   │        │                   │
        │  getSize() =      │        │  getSize() =      │
        │    content.length │        │    SUM(children.  │
        │                   │        │       getSize())  │
        └───────────────────┘        └─────────┬─────────┘
                                                │ contains
                                    ┌───────────┼───────────┐
                                    ▼           ▼           ▼
                              [File: a.txt] [Dir: docs] [File: b.txt]
                                                │
                                          ┌─────┴─────┐
                                          ▼           ▼
                                    [File: c.txt] [File: d.txt]

    TREE STRUCTURE EXAMPLE:
    /root
    ├── documents/          (Directory - Composite)
    │   ├── resume.pdf      (File - Leaf)
    │   └── photos/         (Directory - Composite, nested!)
    │       └── vacation.jpg (File - Leaf)
    └── notes.txt           (File - Leaf)
```

---

## 2. API Design

```http
POST /api/v1/files
Request: {"path": "/documents/resume.pdf", "content": "<base64>", "size": 204800}
Response: 201 CREATED
{"path": "/documents/resume.pdf", "size": 204800, "type": "FILE"}

---

POST /api/v1/directories
Request: {"path": "/documents/photos"}
Response: 201 CREATED
{"path": "/documents/photos", "type": "DIRECTORY"}

---

GET /api/v1/directories/{path}/size
Response: 200 OK
{"path": "/documents", "totalSize": 5242880}  // Recursive sum of all children

---

GET /api/v1/directories/{path}?recursive=true
Response: 200 OK
{
  "path": "/documents",
  "type": "DIRECTORY",
  "children": [
    {"name": "resume.pdf", "type": "FILE", "size": 204800},
    {"name": "photos", "type": "DIRECTORY", "children": [...]}
  ]
}

---

DELETE /api/v1/files/{path}
Response: 204 NO_CONTENT
// If directory, recursively deletes ALL children
```

---

## 3. ER Diagram & Database Design

```sql
-- Adjacency list model for tree structure
CREATE TABLE file_system_entries (
    entry_id VARCHAR(50) PRIMARY KEY,
    parent_id VARCHAR(50),  -- NULL for root
    name VARCHAR(255) NOT NULL,
    entry_type VARCHAR(10) NOT NULL,  -- FILE or DIRECTORY
    size BIGINT DEFAULT 0,  -- 0 for directories initially, calculated
    content_path VARCHAR(500),  -- Physical storage path for files
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CHECK (entry_type IN ('FILE', 'DIRECTORY')),
    FOREIGN KEY (parent_id) REFERENCES file_system_entries(entry_id),
    UNIQUE (parent_id, name),  -- No duplicate names in same directory
    INDEX idx_parent (parent_id)
);
```

**You**: "For large-scale distributed file systems (like Google Drive), you'd use **materialized path** or **nested set model** instead of pure adjacency list, for faster subtree queries without recursive CTEs. But adjacency list is the right choice for interview-level clarity and moderate-scale systems."

---

## 4. Sequence Diagrams

```
Client   Directory("root")   Directory("docs")   File("resume.pdf")
  │              │                    │                   │
  │─getSize()───▶│                    │                   │
  │              │  for each child:   │                   │
  │              ├─getSize()──────────▶│                   │
  │              │                    │  for each child:  │
  │              │                    ├─getSize()──────────▶│
  │              │                    │                   │  return 204800
  │              │                    │◀──────────────────│
  │              │                    │  sum children      │
  │              │◀───────────────────│  return 204800     │
  │              │  sum = 204800      │                   │
  │◀total=204800─│                    │                   │
```

---

## 5. Scenario-First Explanations

### **5.1 Why Composite Pattern (Not Separate File/Directory Classes)?**

**You**: "Without Composite Pattern:
```java
// ❌ Client code needs type checking everywhere!
long calculateTotalSize(Object entry) {
    if (entry instanceof File) {
        return ((File) entry).getSize();
    } else if (entry instanceof Directory) {
        Directory dir = (Directory) entry;
        long total = 0;
        for (Object child : dir.getChildren()) {
            total += calculateTotalSize(child);  // Recursive, but ugly instanceof checks
        }
        return total;
    }
    throw new IllegalArgumentException();
}
```

With Composite Pattern:
```java
interface FileSystemEntry {
    long getSize();
    String getName();
    void delete();
}

class File implements FileSystemEntry {
    private byte[] content;
    private String name;
    
    public long getSize() {
        return content.length;  // Base case
    }
    
    public void delete() {
        storageService.deletePhysicalFile(this);
    }
}

class Directory implements FileSystemEntry {
    private List<FileSystemEntry> children = new ArrayList<>();
    private String name;
    
    public long getSize() {
        // Recursive case - works for BOTH files and nested directories!
        return children.stream()
            .mapToLong(FileSystemEntry::getSize)
            .sum();
    }
    
    public void delete() {
        // Recursively delete all children first
        for (FileSystemEntry child : new ArrayList<>(children)) {
            child.delete();  // Polymorphic call - works whether child is File or Directory!
        }
        children.clear();
    }
    
    public void add(FileSystemEntry entry) {
        children.add(entry);
    }
}

// Client code - beautifully simple, no type checking!
long totalSize = rootDirectory.getSize();  // Works uniformly!
```

**Key insight**: The client (calling code) treats `File` and `Directory` IDENTICALLY through the `FileSystemEntry` interface. This is the essence of Composite Pattern - **uniform treatment of individual objects (Leaf) and compositions of objects (Composite)**."

### **5.2 Why Recursive Delete Needs Careful Ordering?**

**You**: "Directory deletion must happen **bottom-up** (children first, then parent):

```java
class Directory implements FileSystemEntry {
    public void delete() {
        // CRITICAL: Delete children FIRST (recursive, depth-first)
        for (FileSystemEntry child : new ArrayList<>(children)) {
            child.delete();
        }
        // THEN clear this directory's own resources
        children.clear();
        metadataService.removeDirectoryEntry(this);
    }
}
```

**Why the ArrayList copy?** `new ArrayList<>(children)` avoids `ConcurrentModificationException` - if child.delete() somehow modifies the parent's children list during iteration (e.g., via callback), we're iterating a snapshot, not the live list."

---

## 6. Cross Questions

**Interviewer**: "How would you implement symbolic links (shortcuts)?"

**You**: "Add a new Composite Pattern participant - `SymbolicLink`:

```java
class SymbolicLink implements FileSystemEntry {
    private FileSystemEntry target;  // Points to actual File or Directory
    private String linkName;
    
    public long getSize() {
        return target.getSize();  // Delegate to actual target
    }
    
    public void delete() {
        // Deleting a symlink does NOT delete the target!
        metadataService.removeSymlinkEntry(this);
    }
}
```

**Key design decision**: Deleting a symlink must NOT cascade to the target (unlike deleting a real file/directory). This is exactly how Unix `rm` vs `rm -rf` on symlinks behaves - shows understanding of real file system semantics."

---

## 7. Trade-offs

### **In-Memory Tree vs Database-Backed Tree**

| Aspect | In-Memory Tree | DB Adjacency List |
|--------|-----------------|---------------------|
| **Speed** | Instant | Network/disk latency |
| **Persistence** | Lost on restart | Durable |
| **Scale** | Limited by RAM | Scales to billions of files |

**You**: "For an actual OS file system, it's disk-backed with in-memory caching (inode cache). For a cloud storage service (Google Drive style), DB-backed with adjacency list + caching layer is the practical choice."

---

## 8. Senior Trap Questions

### **Trap: "Just use recursion without memoization, file systems aren't that deep!"**

**✅ Senior**: "Actually, `getSize()` recalculating on EVERY call is O(N) where N = total files in subtree. For frequently-accessed large directories (e.g., checking home directory size repeatedly), this is wasteful:

```java
class Directory implements FileSystemEntry {
    private Long cachedSize = null;  // Lazy cache
    private boolean isDirty = true;
    
    public long getSize() {
        if (isDirty) {
            cachedSize = children.stream().mapToLong(FileSystemEntry::getSize).sum();
            isDirty = false;
        }
        return cachedSize;
    }
    
    public void add(FileSystemEntry entry) {
        children.add(entry);
        invalidateSizeCache();  // Mark dirty, propagate up if needed
    }
    
    void invalidateSizeCache() {
        isDirty = true;
        if (parent != null) parent.invalidateSizeCache();  // Propagate upward
    }
}
```

Real file systems (ext4, NTFS) maintain size metadata incrementally rather than recalculating on every stat() call - this caching insight shows production awareness."

---

## 9. Technology Choices

**You**: "**Object storage (S3)** for actual file content (blobs), **PostgreSQL/DynamoDB** for the hierarchical metadata (directory tree structure). Never store large binary file content directly in relational DB rows - use blob storage + reference."

---

## 🔥 Real-World Production Issue: The Recursive `getSize()` That Caused a Stack Overflow

*In plain English: recursion depth controlled by user data (like folder nesting) can be abused to crash the service.*

**The war story:**

"A cloud file-sync product used the Composite Pattern's natural recursive `getSize()` (directory sums children's sizes recursively) exactly as this guide describes. It worked flawlessly for years — until a customer with a deeply nested build-tool cache directory (think `node_modules`-style nesting, 8,000+ levels deep due to a symlink misconfiguration on their end) synced their folder."

```
getSize() call stack for the misbehaving directory:

Directory.getSize()
  -> child Directory.getSize()
       -> child Directory.getSize()
            -> child Directory.getSize()
                 ... 8,000+ levels of recursion ...
                      -> StackOverflowError

Every size-check request for this customer's account crashed the
file-indexing service worker handling it -> and since MULTIPLE
customers' requests were processed on shared worker threads,
one customer's pathological directory structure degraded
size-check latency for OTHER customers on the same worker pool
```

**Root cause:** recursion depth in the Composite Pattern's traversal is bounded only by the ACTUAL data (directory nesting depth), which is attacker/user-controlled input in a multi-tenant system — nobody had put an explicit depth limit or converted the recursion to an iterative, heap-allocated stack-based traversal.

**The fix:** converted `getSize()`/`ls()` traversal from language-level recursion (which uses the limited JVM call stack) to an explicit iterative traversal using a `Deque` as an explicit stack (heap-allocated, effectively unbounded by depth), PLUS added a configurable max-depth safety limit that rejects/flags pathologically deep directory structures at upload/sync time.

**Lesson for a new developer:** "The Composite Pattern's recursive traversal is elegant and simple to write — but recursion depth is bounded by the CALL STACK, and if the depth is driven by user-controlled/external data (folder nesting, JSON nesting, org-chart depth), a sufficiently deep structure becomes a denial-of-service vector. For any Composite traversal exposed to external/untrusted data, either enforce a max-depth limit or use an explicit iterative traversal instead of language-level recursion."

---

## 🎓 **Final Tips**

1. **Composite Pattern**: Uniform interface for File (Leaf) and Directory (Composite)
2. **Recursive Operations**: getSize(), delete() naturally recursive through tree
3. **Bottom-up Deletion**: Children before parent
4. **Caching Consideration**: Avoid O(N) recalculation for frequently accessed sizes

Good luck! File System is THE canonical Composite Pattern interview question. 🚀
