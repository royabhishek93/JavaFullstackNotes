# LC 210: Course Schedule II

**Link**: [leetcode.com/problems/course-schedule-ii](https://leetcode.com/problems/course-schedule-ii/)

## Problem
Return an ordering of courses you should take to finish all courses. If impossible, return an empty array.

## Optimized Approach: Kahn's Algorithm (BFS Topological Sort)

```java
public int[] findOrder(int numCourses, int[][] prerequisites) {
    List<List<Integer>> graph = new ArrayList<>();
    for (int i = 0; i < numCourses; i++) graph.add(new ArrayList<>());

    int[] indegree = new int[numCourses];
    for (int[] edge : prerequisites) {
        int course = edge[0], pre = edge[1];
        graph.get(pre).add(course);
        indegree[course]++;
    }

    Queue<Integer> queue = new LinkedList<>();
    for (int i = 0; i < numCourses; i++) {
        if (indegree[i] == 0) queue.offer(i);
    }

    int[] order = new int[numCourses];
    int idx = 0;

    while (!queue.isEmpty()) {
        int cur = queue.poll();
        order[idx++] = cur;

        for (int next : graph.get(cur)) {
            if (--indegree[next] == 0) queue.offer(next);
        }
    }

    return idx == numCourses ? order : new int[0];
}
```

**Time Complexity**: O(V + E)  
**Space Complexity**: O(V + E)

## Key Insights
- Course order exists only if graph is DAG
- Topological sort gives valid order
- If processed count < `numCourses`, cycle exists

## Tips and Tricks
- LC 207 asks boolean; LC 210 asks actual ordering.
- Kahn's algorithm is interview-friendly and iterative.

## Related Problems
- LC 207 Course Schedule
- LC 269 Alien Dictionary
