# LC 133: Clone Graph

**Link**: [leetcode.com/problems/clone-graph](https://leetcode.com/problems/clone-graph/)

## Problem
Return a deep copy of an undirected connected graph.

## Optimized Approach: BFS + HashMap Mapping

```java
public Node cloneGraph(Node node) {
    if (node == null) return null;

    Map<Node, Node> map = new HashMap<>();
    Queue<Node> queue = new LinkedList<>();

    map.put(node, new Node(node.val));
    queue.offer(node);

    while (!queue.isEmpty()) {
        Node cur = queue.poll();

        for (Node nei : cur.neighbors) {
            if (!map.containsKey(nei)) {
                map.put(nei, new Node(nei.val));
                queue.offer(nei);
            }
            map.get(cur).neighbors.add(map.get(nei));
        }
    }

    return map.get(node);
}
```

**Time Complexity**: O(V + E)  
**Space Complexity**: O(V)

## Key Insights
- Use map from original node to cloned node
- Graph may contain cycles; mapping prevents infinite loops
- Build nodes and edges in one BFS pass

## Tips and Tricks
- Deep copy means no shared node references with original.
- DFS variant is equally valid in interviews.

## Related Problems
- LC 200 Number of Islands
- LC 207 Course Schedule
