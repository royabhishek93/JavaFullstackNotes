# LC 752: Open the Lock

**Link**: [leetcode.com/problems/open-the-lock](https://leetcode.com/problems/open-the-lock/)

## Problem
You start at "0000" and can rotate one wheel by +1 or -1 each move. Return minimum moves to reach target while avoiding deadends.

## Optimized Approach: BFS on State Graph

```java
public int openLock(String[] deadends, String target) {
    Set<String> dead = new HashSet<>(Arrays.asList(deadends));
    if (dead.contains("0000")) return -1;
    if (target.equals("0000")) return 0;

    Queue<String> queue = new LinkedList<>();
    Set<String> visited = new HashSet<>();
    queue.offer("0000");
    visited.add("0000");

    int steps = 0;
    while (!queue.isEmpty()) {
        int size = queue.size();
        for (int i = 0; i < size; i++) {
            String cur = queue.poll();
            if (cur.equals(target)) return steps;

            for (String next : neighbors(cur)) {
                if (!dead.contains(next) && visited.add(next)) {
                    queue.offer(next);
                }
            }
        }
        steps++;
    }

    return -1;
}

private List<String> neighbors(String s) {
    List<String> list = new ArrayList<>();
    char[] arr = s.toCharArray();

    for (int i = 0; i < 4; i++) {
        char old = arr[i];

        arr[i] = old == '9' ? '0' : (char) (old + 1);
        list.add(new String(arr));

        arr[i] = old == '0' ? '9' : (char) (old - 1);
        list.add(new String(arr));

        arr[i] = old;
    }

    return list;
}
```

**Time Complexity**: O(10^4) worst case states  
**Space Complexity**: O(10^4)

## Key Insights
- Each lock combination is a graph node
- Each move changes one wheel by one step
- BFS finds minimum moves in unweighted state graph

## Tips and Tricks
- Validate deadend at start before BFS.
- This is a great pattern match with Word Ladder.

## Related Problems
- LC 127 Word Ladder
- LC 909 Snakes and Ladders
