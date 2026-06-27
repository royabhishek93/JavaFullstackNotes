# LC 208: Implement Trie (Prefix Tree)

**Link**: [leetcode.com/problems/implement-trie-prefix-tree](https://leetcode.com/problems/implement-trie-prefix-tree/)

## Problem
Implement a Trie with methods:
- `insert(String word)`
- `search(String word)`
- `startsWith(String prefix)`

## Optimized Approach: Trie Node with 26 Children

```java
class Trie {
    private static class Node {
        Node[] child = new Node[26];
        boolean isWord;
    }

    private final Node root;

    public Trie() {
        root = new Node();
    }

    public void insert(String word) {
        Node cur = root;
        for (char ch : word.toCharArray()) {
            int idx = ch - 'a';
            if (cur.child[idx] == null) cur.child[idx] = new Node();
            cur = cur.child[idx];
        }
        cur.isWord = true;
    }

    public boolean search(String word) {
        Node node = findNode(word);
        return node != null && node.isWord;
    }

    public boolean startsWith(String prefix) {
        return findNode(prefix) != null;
    }

    private Node findNode(String s) {
        Node cur = root;
        for (char ch : s.toCharArray()) {
            int idx = ch - 'a';
            if (cur.child[idx] == null) return null;
            cur = cur.child[idx];
        }
        return cur;
    }
}
```

**Time Complexity**: O(L) per operation  
**Space Complexity**: O(total inserted characters)

## Key Insights
- Node path represents prefix
- `isWord` distinguishes complete word from prefix

## Tips and Tricks
- Use a Trie when many queries share prefixes and repeated scans are too expensive.
- Keep node structure minimal: children plus just enough terminal metadata.
- Insertion and search logic should mirror each other for easier debugging.

## Related Problems
- LC 211 Design Add and Search Words Data Structure
