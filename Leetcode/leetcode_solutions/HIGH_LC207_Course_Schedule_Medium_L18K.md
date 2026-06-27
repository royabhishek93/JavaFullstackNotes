# LC 207: Course Schedule

**Link**: [leetcode.com/problems/course-schedule](https://leetcode.com/problems/course-schedule/)

## Problem
There are n courses labeled from 0 to n - 1, and you are given an array prerequisites where prerequisites[i] = [ai, bi] indicates that you must take course bi first if you want to take course ai. Return true if you can finish all n courses. Otherwise, return false.

### Examples
- Input: numCourses = 2, prerequisites = [[1,0]] → Output: true
- Input: numCourses = 2, prerequisites = [[1,0],[0,1]] → Output: false (cycle!)
- Input: numCourses = 4, prerequisites = [[1,0],[2,0],[3,1],[3,2]] → Output: true

## Optimized Approach: Topological Sort (DFS with Colors)

```java
public boolean canFinish(int numCourses, int[][] prerequisites) {
    // Build adjacency list
    List<List<Integer>> graph = new ArrayList<>();
    for (int i = 0; i < numCourses; i++) {
        graph.add(new ArrayList<>());
    }
    
    for (int[] prereq : prerequisites) {
        graph.get(prereq[1]).add(prereq[0]);  // prereq[1] -> prereq[0]
    }

    // States: 0 = unvisited, 1 = visiting, 2 = visited
    int[] state = new int[numCourses];

    for (int i = 0; i < numCourses; i++) {
        if (state[i] == 0) {
            if (hasCycle(i, graph, state)) {
                return false;
            }
        }
    }

    return true;
}

private boolean hasCycle(int course, List<List<Integer>> graph, int[] state) {
    if (state[course] == 1) {
        return true;  // Found cycle: visiting state revisited
    }

    if (state[course] == 2) {
        return false;  // Already fully processed
    }

    // Mark as visiting
    state[course] = 1;

    // Check all dependent courses
    for (int dependent : graph.get(course)) {
        if (hasCycle(dependent, graph, state)) {
            return true;
        }
    }

    // Mark as visited (fully processed)
    state[course] = 2;
    return false;
}
```

**Time Complexity**: O(V + E) - graph traversal  
**Space Complexity**: O(V) - recursion + graph

## Key Insights
- **Topological sort problem**: Can finish all if no cycle
- **DFS three-color scheme**:
  - 0 = unvisited (white)
  - 1 = currently visiting (gray)
  - 2 = fully visited (black)
- **Cycle detection**: State 1 revisited = cycle
- **Graph direction**: prereq[1] → prereq[0]

## Interview Walkthrough
1. **Problem**: Can complete all courses?
2. **Key insight**: Cycles = impossible to complete
3. **DFS approach**:
   - For each unvisited course, DFS its dependencies
   - If revisit "visiting" node = cycle
   - Mark complete when all dependencies done
4. **Example**: [[1,0],[0,1]]
   ```
   Start course 0: state[0]=1
     Check dependency 1: state[1]=1
       Check dependency 0: state[0]=1 (already visiting!) → CYCLE
   ```

## Why This Approach (Optimal)
- ✅ **O(V+E) time**: Single DFS pass
- ✅ **O(V) space**: State array
- ✅ **Detects cycles**: Color scheme is elegant
- ✅ **Reusable**: Same algorithm for topological sort

## Alternative: Kahn's Algorithm (BFS + In-degree)
```java
// Count in-degree for each course
// Process courses with in-degree 0
// More intuitive for some interviewers
```

## Common Mistakes
- Wrong graph direction
- Only checking visited (miss cycle with 1→2→1)
- Not returning true when cycle found
- Forgetting to initialize graph

## Tips and Tricks
- "This is cycle detection in directed graph"
- "DFS with three states: unvisited, visiting, visited"
- "If we see 'visiting' state again = cycle found"
- "Think topologically: can we order courses?"

## Related Problems
- **LC 210**: Course Schedule II (return topological order)
- **LC 300**: Longest Increasing Subsequence (DP variant)
- **LC alien-order**: Similar topological sort
