# LC 138: Copy List with Random Pointer

**Link**: [leetcode.com/problems/copy-list-with-random-pointer](https://leetcode.com/problems/copy-list-with-random-pointer/)

## Problem
A linked list of length n is given such that each node contains an additional random pointer, which could point to any node in the list, or null. Construct a deep copy of the list. The copy should consist of exactly n brand-new nodes, with each node in the new list pointing to the new nodes of the copy by both its next and random pointers.

### Examples
Similar structure but with random pointers added to normal linked list pointers.

## Optimized Approach: Three-Pass with HashMap

```java
class Node {
    int val;
    Node next;
    Node random;
    
    public Node(int val) {
        this.val = val;
        this.next = null;
        this.random = null;
    }
}

public Node copyRandomList(Node head) {
    if (head == null) return null;

    // Map: original node -> copied node
    Map<Node, Node> nodeMap = new HashMap<>();

    // Pass 1: Create all nodes
    Node current = head;
    while (current != null) {
        nodeMap.put(current, new Node(current.val));
        current = current.next;
    }

    // Pass 2: Set next and random pointers
    current = head;
    while (current != null) {
        Node copyNode = nodeMap.get(current);
        copyNode.next = nodeMap.get(current.next);
        copyNode.random = nodeMap.get(current.random);
        current = current.next;
    }

    return nodeMap.get(head);
}
```

**Time Complexity**: O(n) - two passes  
**Space Complexity**: O(n) - HashMap

## Key Insights
- **Two pointers complexity**: next + random
- **HashMap essential**: Maps original to copy for easy reference
- **Two passes**: Create nodes first, then link them
- **Handles null pointers**: HashMap.get(null) returns null

## Interview Walkthrough
1. **Problem**: Deep copy linked list with random pointers
2. **Challenge**: Random pointers can go anywhere
3. **Naive approach**: Create node, try to link immediately (circular references)
4. **Better approach**:
   - Pass 1: Create all nodes, store in HashMap
   - Pass 2: Set pointers using HashMap lookups
5. **Why it works**: All nodes exist, HashMap gives instant access

## Why This Approach (Optimal)
- ✅ **O(n) time**: Two linear passes
- ✅ **Handles cycles**: HashMap approach doesn't require ordering
- ✅ **Simple**: Clear two-phase process

## Alternative: In-place with Node Interleaving
```java
// Interleave original and copied nodes
// More space-efficient (O(1) extra)
// More complex code
```

## Common Mistakes
- Trying to create and link simultaneously (circular reference)
- Forgetting HashMap.get() can return null
- Not creating all nodes first
- Using value comparison instead of reference

## Tips and Tricks
- "HashMap maps original nodes to their copies"
- "Pass 1: Create all copies (isolated nodes)"
- "Pass 2: Link using HashMap lookups"
- "Any pointers to null become null in copy"

## Related Problems
- **LC 133**: Clone Graph (similar concept)
- **LC 2**: Add Two Numbers (linked list)
- **LC 25**: Reverse Nodes in k-Group (linked list manipulation)
