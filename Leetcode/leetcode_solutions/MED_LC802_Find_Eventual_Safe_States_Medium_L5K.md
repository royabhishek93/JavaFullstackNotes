# LC 802: Find Eventual Safe States

**Link**: [leetcode.com/problems/find-eventual-safe-states](https://leetcode.com/problems/find-eventual-safe-states/)

## Problem
In a directed graph, return all nodes that are eventually safe (all paths from them end in terminal nodes).

## Optimized Approach: Reverse Graph + Kahn's Algorithm

```java
public List<Integer> eventualSafeNodes(int[][] graph) {
    int n = graph.length;
    List<List<Integer>> reverse = new ArrayList<>();
    for (int i = 0; i < n; i++) reverse.add(new ArrayList<>());

    int[] outdegree = new int[n];
    for (int u = 0; u < n; u++) {
        outdegree[u] = graph[u].length;
        for (int v : graph[u]) {
            reverse.get(v).add(u);
        }
    }

    Queue<Integer> queue = new LinkedList<>();
    for (int i = 0; i < n; i++) {
        if (outdegree[i] == 0) queue.offer(i);
    }

    boolean[] safe = new boolean[n];
    while (!queue.isEmpty()) {
        int node = queue.poll();
        safe[node] = true;

        for (int prev : reverse.get(node)) {
            if (--outdegree[prev] == 0) {
                queue.offer(prev);
            }
        }
    }

    List<Integer> ans = new ArrayList<>();
    for (int i = 0; i < n; i++) if (safe[i]) ans.add(i);
    return ans;
}
```

**Time Complexity**: O(V + E)  
**Space Complexity**: O(V + E)

## Key Insights
- Unsafe nodes are those that can reach a cycle
- Terminal nodes are safe by definition
- Reverse-graph topological elimination identifies all safe nodes

## Tips and Tricks
- Think "remove nodes that are definitely safe" iteratively.
- DFS-color approach is also acceptable.

## Related Problems
- LC 207 Course Schedule
- LC 210 Course Schedule II
