# LC 269: Alien Dictionary

**Link**: [leetcode.com/problems/alien-dictionary](https://leetcode.com/problems/alien-dictionary/)

## Problem
Given a sorted list of words in an alien language, return a valid character order. If invalid, return empty string.

## Optimized Approach: Graph + Kahn's Topological Sort

```java
public String alienOrder(String[] words) {
    Map<Character, Set<Character>> graph = new HashMap<>();
    Map<Character, Integer> indegree = new HashMap<>();

    for (String w : words) {
        for (char c : w.toCharArray()) {
            graph.putIfAbsent(c, new HashSet<>());
            indegree.putIfAbsent(c, 0);
        }
    }

    for (int i = 0; i < words.length - 1; i++) {
        String w1 = words[i], w2 = words[i + 1];
        if (w1.length() > w2.length() && w1.startsWith(w2)) return "";

        int len = Math.min(w1.length(), w2.length());
        for (int j = 0; j < len; j++) {
            char c1 = w1.charAt(j), c2 = w2.charAt(j);
            if (c1 != c2) {
                if (graph.get(c1).add(c2)) {
                    indegree.put(c2, indegree.get(c2) + 1);
                }
                break;
            }
        }
    }

    Queue<Character> queue = new LinkedList<>();
    for (char c : indegree.keySet()) {
        if (indegree.get(c) == 0) queue.offer(c);
    }

    StringBuilder order = new StringBuilder();
    while (!queue.isEmpty()) {
        char cur = queue.poll();
        order.append(cur);
        for (char next : graph.get(cur)) {
            indegree.put(next, indegree.get(next) - 1);
            if (indegree.get(next) == 0) queue.offer(next);
        }
    }

    return order.length() == indegree.size() ? order.toString() : "";
}
```

**Time Complexity**: O(C) where C is total chars across words  
**Space Complexity**: O(U + E) where U is unique chars

## Key Insights
- Compare adjacent words to infer first differing character order
- Prefix invalid case must be handled explicitly
- Cycle in graph means no valid alphabet

## Tips and Tricks
- Mention this as topological sort with string constraints.
- Avoid adding duplicate edges, otherwise indegree breaks.

## Related Problems
- LC 207 Course Schedule
- LC 210 Course Schedule II
