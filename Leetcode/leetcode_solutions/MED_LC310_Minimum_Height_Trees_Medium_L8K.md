# LC 310: Minimum Height Trees

**Link**: [leetcode.com/problems/minimum-height-trees](https://leetcode.com/problems/minimum-height-trees/)

## Problem
Given an undirected tree with `n` nodes, return all roots that produce minimum tree height.

## Optimized Approach: Topological Trimming of Leaves

```java
public List<Integer> findMinHeightTrees(int n, int[][] edges) {
    if (n == 1) return Collections.singletonList(0);

    List<Set<Integer>> graph = new ArrayList<>();
    for (int i = 0; i < n; i++) graph.add(new HashSet<>());

    for (int[] e : edges) {
        graph.get(e[0]).add(e[1]);
        graph.get(e[1]).add(e[0]);
    }

    List<Integer> leaves = new ArrayList<>();
    for (int i = 0; i < n; i++) {
        if (graph.get(i).size() == 1) leaves.add(i);
    }

    int remaining = n;
    while (remaining > 2) {
        remaining -= leaves.size();
        List<Integer> newLeaves = new ArrayList<>();

        for (int leaf : leaves) {
            int neighbor = graph.get(leaf).iterator().next();
            graph.get(neighbor).remove(leaf);
            if (graph.get(neighbor).size() == 1) newLeaves.add(neighbor);
        }

        leaves = newLeaves;
    }

    return leaves;
}
```

**Time Complexity**: O(V + E)  
**Space Complexity**: O(V + E)

## Key Insights
- MHT roots are tree centroids
- Repeatedly remove all current leaves
- Last 1 or 2 nodes are the answer

## Tips and Tricks
- This is BFS-like layering on an undirected tree.
- Avoid BFS from every node (too slow).

## Related Problems
- LC 207 Course Schedule
- LC 802 Find Eventual Safe States
