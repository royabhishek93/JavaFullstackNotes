# LeetCode 207: Course Schedule (Cycle Detection & Topological Sort)

## 🎯 Problem Statement

You are given a number of courses labeled from `0` to `numCourses - 1` and a list of prerequisite pairs where `prerequisites[i] = [course, prereq]` indicates that you must take course `prereq` before taking `course`.

Determine if it's possible to finish all courses. Return `true` if you can finish all courses, `false` if a circular dependency exists.

**Constraints:**
- `1 <= numCourses <= 2000`
- `0 <= prerequisites.length <= 5000`
- All prerequisite pairs are unique

---

## 🔥 Scenario: The Impossible Schedule

Imagine you're a student registering for courses:

```java
// Scenario 1: Valid schedule ✅
int numCourses = 2;
int[][] prerequisites = {{1, 0}}; // Take course 0 before course 1
// Can finish? YES - take 0 first, then 1

// Scenario 2: Circular dependency ❌
int numCourses = 2;
int[][] prerequisites = {{1, 0}, {0, 1}}; // Need 0 before 1, but need 1 before 0
// Can finish? NO - deadlock!

// Scenario 3: Complex valid (Topological sort needed)
int numCourses = 4;
int[][] prerequisites = {{1, 0}, {2, 0}, {3, 1}, {3, 2}};
//  0 → 1 → 3
//  0 → 2 → 3
// Order: 0, then (1,2 in any order), then 3 ✅
```

---

## 🏗️ Key Concepts

### 1. **Graph Representation**
- `prereq → course` forms a **directed edge**
- Cycle in graph = courses that can't be completed
- **Topological sort** = valid completion order (only exists in DAGs)

### 2. **Kahn's Algorithm (BFS-based Topological Sort)**
- Track **indegree** (number of prerequisites) for each course
- Start with courses having 0 prerequisites
- Process in BFS order, decrementing indegree of dependent courses
- If all courses processed → No cycle ✅
- If some courses remain → Cycle exists ❌

### 3. **Why Indegree Matters**
- **Indegree = 0**: Course has no prerequisites (can start immediately)
- **Indegree > 0**: Course depends on others (must wait)
- When we complete a course, decrement indegree of courses depending on it

---

## 📊 Solution: Kahn's Algorithm (BFS Topological Sort)

```java
public class CourseSchedule {
    
    public static boolean canFinish(int numCourses, int[][] prerequisites) {
        // Step 1: Initialize graph and indegree
        List<List<Integer>> graph = new ArrayList<>();
        int[] indegree = new int[numCourses];
        
        for (int i = 0; i < numCourses; i++) {
            graph.add(new ArrayList<>());
        }
        
        // Step 2: Build graph
        // prerequisites[i] = [course, prereq]
        // Edge: prereq → course (prereq must be taken before course)
        for (int[] pre : prerequisites) {
            int course = pre[0];
            int prereq = pre[1];
            
            graph.get(prereq).add(course);  // prereq points to course
            indegree[course]++;              // course depends on prereq
        }
        
        // Step 3: Find all courses with 0 prerequisites (starting points)
        Queue<Integer> queue = new LinkedList<>();
        for (int i = 0; i < numCourses; i++) {
            if (indegree[i] == 0) {
                queue.offer(i);
            }
        }
        
        // Step 4: Process courses in topological order
        int count = 0;
        while (!queue.isEmpty()) {
            int curr = queue.poll();
            count++;  // Successfully processed this course
            
            // For each course that depends on current course
            for (int neighbor : graph.get(curr)) {
                indegree[neighbor]--;  // One less prerequisite
                
                // If all prerequisites satisfied, can now take this course
                if (indegree[neighbor] == 0) {
                    queue.offer(neighbor);
                }
            }
        }
        
        // If we processed all courses, no cycle exists
        return count == numCourses;
    }
    
    public static void main(String[] args) {
        // Test Case 1: Simple valid schedule
        System.out.println("Test 1: " + canFinish(2, new int[][]{{1, 0}})); // true
        
        // Test Case 2: Circular dependency
        System.out.println("Test 2: " + canFinish(2, new int[][]{{1, 0}, {0, 1}})); // false
        
        // Test Case 3: Complex valid
        System.out.println("Test 3: " + canFinish(4, new int[][]{{1, 0}, {2, 0}, {3, 1}, {3, 2}})); // true
        
        // Test Case 4: No prerequisites
        System.out.println("Test 4: " + canFinish(3, new int[][]{})); // true
        
        // Test Case 5: Self-loop
        System.out.println("Test 5: " + canFinish(1, new int[][]{{0, 0}})); // false
    }
}
```

---

## 🚶 Step-by-Step Walkthrough

### Example: `canFinish(4, [[1,0], [2,0], [3,1], [3,2]])`

#### Step 1: Understanding Prerequisites & Building Indegree Array

**Prerequisites breakdown:**
```
[1, 0] → Course 1 depends on course 0 (take 0 before 1)
[2, 0] → Course 2 depends on course 0 (take 0 before 2)
[3, 1] → Course 3 depends on course 1 (take 1 before 3)
[3, 2] → Course 3 depends on course 2 (take 2 before 3)
```

**Building indegree (prerequisites count for each course):**
```
Processing [1, 0]: Course 1 needs course 0        → indegree[1]++ = 1
Processing [2, 0]: Course 2 needs course 0        → indegree[2]++ = 1
Processing [3, 1]: Course 3 needs course 1        → indegree[3]++ = 1
Processing [3, 2]: Course 3 needs course 2        → indegree[3]++ = 2

Final indegree array: [0, 1, 1, 2]
```

**What this means:**
```
Course 0: indegree[0] = 0  ✅ (no prerequisites → can take immediately)
Course 1: indegree[1] = 1  ⏳ (needs 1 course: course 0)
Course 2: indegree[2] = 1  ⏳ (needs 1 course: course 0)
Course 3: indegree[3] = 2  ⏳ (needs 2 courses: courses 1 AND 2)
```

#### Step 2: Graph Structure & Visual Dependencies

```
Graph structure:          Dependency chain:
0 → 1                     
0 → 2                          0
1 → 3                         ╱ ╲
2 → 3                        1   2
                              ╲ ╱
                               3

Which translates to:
- To take course 1: must finish 0 first
- To take course 2: must finish 0 first
- To take course 3: must finish both 1 and 2 first
```

#### Step 3: Algorithm Execution (BFS with Indegree)

```
Indegree array:   [0, 1, 1, 2]
Graph relations:  0→1, 0→2, 1→3, 2→3

INITIALIZATION:
  • Find all courses with indegree 0 (prerequisites satisfied)
  • Only course 0 has indegree 0
  • queue = [0]
  • count = 0

ITERATION 1: Process course 0
  • count++ = 1  (successfully completed 1 course)
  • Course 0 points to: 1, 2
  • Decrement indegree of dependent courses:
      - indegree[1]-- : 1 → 0 ✅ (prerequisites now satisfied, add to queue)
      - indegree[2]-- : 1 → 0 ✅ (prerequisites now satisfied, add to queue)
  • queue = [1, 2]
  • indegree = [0, 0, 0, 2]

ITERATION 2: Process course 1
  • count++ = 2  (successfully completed 2 courses)
  • Course 1 points to: 3
  • Decrement indegree of dependent courses:
      - indegree[3]-- : 2 → 1 ⏳ (still needs course 2, don't add yet)
  • queue = [2]
  • indegree = [0, 0, 0, 1]

ITERATION 3: Process course 2
  • count++ = 3  (successfully completed 3 courses)
  • Course 2 points to: 3
  • Decrement indegree of dependent courses:
      - indegree[3]-- : 1 → 0 ✅ (both prerequisites now satisfied, add to queue)
  • queue = [3]
  • indegree = [0, 0, 0, 0]

ITERATION 4: Process course 3
  • count++ = 4  (successfully completed 4 courses)
  • Course 3 points to: (nothing)
  • queue = []
  • indegree = [0, 0, 0, 0]

FINAL CHECK:
  • count (4) == numCourses (4) ✅
  • All courses processed → NO CYCLE
  • Return: true
```

#### Why This Works (Cycle Detection):

```
If there WAS a cycle, example: [[1,0], [0,1]]
  indegree = [1, 1]
  No course has indegree 0
  queue remains empty
  count = 0 (never process any course)
  count (0) != numCourses (2) → CYCLE DETECTED
  Return: false
```

---

## ⏱️ Complexity Analysis

| Aspect | Complexity | Explanation |
|--------|-----------|-------------|
| **Time** | **O(V + E)** | V = numCourses, E = prerequisites. Each vertex/edge visited once |
| **Space** | **O(V + E)** | Graph adjacency list + indegree array + queue |

---

## 🎯 Alternative: DFS Cycle Detection

```java
public static boolean canFinishDFS(int numCourses, int[][] prerequisites) {
    List<List<Integer>> graph = new ArrayList<>();
    int[] state = new int[numCourses]; // 0: unvisited, 1: visiting, 2: visited
    
    for (int i = 0; i < numCourses; i++) {
        graph.add(new ArrayList<>());
    }
    
    for (int[] pre : prerequisites) {
        graph.get(pre[1]).add(pre[0]);
    }
    
    for (int i = 0; i < numCourses; i++) {
        if (hasCycle(i, graph, state)) {
            return false;
        }
    }
    
    return true;
}

private static boolean hasCycle(int course, List<List<Integer>> graph, int[] state) {
    if (state[course] == 1) return true;  // Currently visiting → cycle detected
    if (state[course] == 2) return false; // Already visited → no cycle
    
    state[course] = 1;  // Mark as visiting
    
    for (int neighbor : graph.get(course)) {
        if (hasCycle(neighbor, graph, state)) {
            return true;
        }
    }
    
    state[course] = 2;  // Mark as visited
    return false;
}
```

**When to use:**
- BFS (Kahn's): Cleaner, iterative, better for large graphs
- DFS: More intuitive for those familiar with recursion

---

## 🧠 Interview Q&A

### Q1: "What's the difference between this problem and topological sort?"
**A:** This problem **is** topological sort with cycle detection. We're finding if a valid topological ordering exists (DAG = acyclic). If a cycle exists, no topological order is possible.

### Q2: "Why do we use indegree instead of just detecting cycles?"
**A:** Indegree-based BFS is more efficient:
- Directly builds topological order
- Single pass through graph (no need to visit all paths)
- Detects cycles as a byproduct (unprocessed nodes at end)

### Q3: "What if a course has no prerequisites?"
**A:** It starts with indegree = 0, added to queue immediately. Processed first in topological order.

### Q4: "How do you detect if a cycle exists?"
**A:** After processing all reachable courses:
- If `count < numCourses` → some courses unreached → cycle exists ❌
- If `count == numCourses` → all courses processed → no cycle ✅

### Q5: "What happens with disconnected components?"
**A:** The algorithm handles it automatically:
```
Courses: [0, 1, 2, 3]
Prerequisites: [[1, 0], [3, 2]]  // Two separate chains

Processing:
- Both 0 and 2 have indegree 0, both added to queue
- Process independently, all 4 courses eventually processed
- Returns true ✅
```

### Q6: "Can we return the actual course order?"
**A:** Yes! Collect courses as they're dequeued:
```java
List<Integer> order = new ArrayList<>();
while (!queue.isEmpty()) {
    int curr = queue.poll();
    order.add(curr);  // ← Add this line
    // ... rest of loop
}
```

### Q7: "What's the difference between `prerequisites[i] = [a, b]` meaning 'take b before a' vs 'take a before b'?"
**A:** Critical to understand the input format!
- **Our format:** `[course, prereq]` → `prereq → course` (prereq must be taken first)
- Some problems use reverse: `[prereq, course]` → Always read problem carefully!

---

## 🔍 Edge Cases

| Case | Example | Result |
|------|---------|--------|
| **No prerequisites** | `canFinish(3, [])` | `true` |
| **Self-loop** | `canFinish(1, [[0, 0]])` | `false` |
| **Two-course cycle** | `canFinish(2, [[1, 0], [0, 1]])` | `false` |
| **Long chain** | `canFinish(5, [[1,0],[2,1],[3,2],[4,3]])` | `true` |
| **Multiple cycles** | `canFinish(3, [[1,0],[2,1],[0,2]])` | `false` |
| **Valid complete graph** | `canFinish(3, [[1,0],[2,0],[2,1]])` | `true` |

---

## 💡 Key Takeaways

🔥 **MUST KNOW:** 
- Kahn's algorithm with indegree tracking
- How to detect cycles (count != numCourses)
- Graph construction from prerequisites

✅ **SHOULD KNOW:**
- DFS cycle detection alternative
- How to extract actual topological order
- Handling disconnected components

👍 **GOOD TO KNOW:**
- Time complexity derivation (V + E)
- Why BFS is preferred over DFS here
- Variations with weighted graphs

---

## 📝 Follow-up Problems

1. **LeetCode 210** - Course Schedule II (return actual order)
2. **LeetCode 269** - Alien Dictionary (topological sort with inheritance)
3. **LeetCode 1203** - Sort Items by Groups Respecting Dependencies (multi-level)

---

## 🎤 Interview Tips

✅ **Do:**
- Explain graph construction clearly
- Walk through a complete example with indices
- Mention time/space complexity
- Discuss alternative approaches (DFS)

❌ **Don't:**
- Confuse indegree with outdegree
- Forget to handle courses with no prerequisites
- Return incomplete orders or wrong cycle detection
- Miss the V + E complexity clarification

---

## Complete Solution with Input Validation

```java
import java.util.*;

public class CourseScheduleSolution {
    
    public static boolean canFinish(int numCourses, int[][] prerequisites) {
        if (numCourses <= 0) return false;
        if (prerequisites == null || prerequisites.length == 0) return true;
        
        List<List<Integer>> graph = new ArrayList<>();
        int[] indegree = new int[numCourses];
        
        for (int i = 0; i < numCourses; i++) {
            graph.add(new ArrayList<>());
        }
        
        for (int[] pre : prerequisites) {
            if (pre[0] == pre[1]) return false; // Self-loop
            graph.get(pre[1]).add(pre[0]);
            indegree[pre[0]]++;
        }
        
        Queue<Integer> queue = new LinkedList<>();
        for (int i = 0; i < numCourses; i++) {
            if (indegree[i] == 0) {
                queue.offer(i);
            }
        }
        
        int count = 0;
        while (!queue.isEmpty()) {
            int curr = queue.poll();
            count++;
            
            for (int neighbor : graph.get(curr)) {
                indegree[neighbor]--;
                if (indegree[neighbor] == 0) {
                    queue.offer(neighbor);
                }
            }
        }
        
        return count == numCourses;
    }
    
    public static void main(String[] args) {
        // Comprehensive test cases
        System.out.println("=== Course Schedule Tests ===");
        System.out.println("Test 1 (Simple valid): " + canFinish(2, new int[][]{{1, 0}}));
        System.out.println("Test 2 (Simple cycle): " + canFinish(2, new int[][]{{1, 0}, {0, 1}}));
        System.out.println("Test 3 (Complex DAG): " + canFinish(4, new int[][]{{1,0},{2,0},{3,1},{3,2}}));
        System.out.println("Test 4 (No deps): " + canFinish(3, new int[][]{}));
        System.out.println("Test 5 (Self-loop): " + canFinish(1, new int[][]{{0, 0}}));
        System.out.println("Test 6 (Chain): " + canFinish(5, new int[][]{{1,0},{2,1},{3,2},{4,3}}));
        System.out.println("Test 7 (Complex cycle): " + canFinish(3, new int[][]{{1,0},{2,1},{0,2}}));
    }
}
```

