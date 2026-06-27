# LC 127: Word Ladder

**Link**: [leetcode.com/problems/word-ladder](https://leetcode.com/problems/word-ladder/)

## Problem
Given `beginWord`, `endWord`, and a dictionary, return the shortest transformation sequence length where each step changes one character and stays in dictionary.

## Optimized Approach: BFS (Unweighted Shortest Path)

```java
public int ladderLength(String beginWord, String endWord, List<String> wordList) {
    Set<String> dict = new HashSet<>(wordList);
    if (!dict.contains(endWord)) return 0;

    Queue<String> queue = new LinkedList<>();
    queue.offer(beginWord);
    Set<String> visited = new HashSet<>();
    visited.add(beginWord);

    int level = 1;
    while (!queue.isEmpty()) {
        int size = queue.size();

        for (int i = 0; i < size; i++) {
            String word = queue.poll();
            if (word.equals(endWord)) return level;

            char[] arr = word.toCharArray();
            for (int p = 0; p < arr.length; p++) {
                char original = arr[p];
                for (char c = 'a'; c <= 'z'; c++) {
                    if (c == original) continue;
                    arr[p] = c;
                    String next = new String(arr);

                    if (dict.contains(next) && visited.add(next)) {
                        queue.offer(next);
                    }
                }
                arr[p] = original;
            }
        }

        level++;
    }

    return 0;
}
```

**Time Complexity**: O(N * L * 26) where N = word count, L = word length  
**Space Complexity**: O(N)

## Key Insights
- Graph is implicit; words are nodes
- Edge exists if words differ by one char
- BFS guarantees shortest path in unweighted graph

## Tips and Tricks
- Mark visited when enqueuing, not dequeuing.
- If asked to optimize further, discuss bidirectional BFS.

## Related Problems
- LC 752 Open the Lock
- LC 909 Snakes and Ladders
