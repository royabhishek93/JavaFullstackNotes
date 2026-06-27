# Pointer Manipulation: Linked List Pattern

## 🎯 When to Use
- Linked list operations (reverse, merge, cycle detection)
- Two-pointer techniques
- Manipulation without extra space
- Track previous, current, next pointers

## 📝 Master Template

```java
public ListNode solve(ListNode head) {
    // Step 1: Initialize pointers
    ListNode prev = null;
    ListNode current = head;
    ListNode next = null;
    
    // Step 2: Iterate through list
    while (current != null) {
        // Step 3: Save next node before modification
        next = current.next;
        
        // Step 4: Modify pointers
        current.next = prev;
        
        // Step 5: Move pointers forward
        prev = current;
        current = next;
    }
    
    // Step 6: Return new head
    return prev;
}
```

## 🔄 Problem Variations & Modifications

### ✅ LC 206: Reverse Linked List (IMPLEMENTED - Iterative)
**What changes**: Nothing - this IS the template
**Difficulty**: Easy
```java
public ListNode reverseList(ListNode head) {
    ListNode prev = null;
    ListNode current = head;
    
    while (current != null) {
        ListNode next = current.next;
        current.next = prev;
        prev = current;
        current = next;
    }
    
    return prev;
}
```
**Complexity**: O(n) time, O(1) space

---

### LC 206: Reverse Linked List (Recursive Version)
**What changes**: Use recursion instead of iteration
**Difficulty**: Easy
```java
public ListNode reverseListRecursive(ListNode head) {
    // Base case: null or single node
    if (head == null || head.next == null) {
        return head;
    }
    
    // Reverse the rest
    ListNode newHead = reverseListRecursive(head.next);
    
    // Put head at end
    head.next.next = head;
    head.next = null;
    
    return newHead;
}
```
**Complexity**: O(n) time, O(n) space (recursion stack)

---

### LC 92: Reverse Linked List II (Partial Reverse)
**What changes**: Reverse only from position left to right
**Difficulty**: Medium
```java
public ListNode reverseBetween(ListNode head, int left, int right) {
    if (left == right) return head;
    
    ListNode dummy = new ListNode(0);
    dummy.next = head;
    
    ListNode prevLeft = dummy;
    ListNode current = head;
    
    // Move to position before left
    for (int i = 0; i < left - 1; i++) {
        prevLeft = current;
        current = current.next;
    }
    
    // Reverse from left to right
    ListNode prev = null;
    for (int i = 0; i < right - left + 1; i++) {
        ListNode next = current.next;
        current.next = prev;
        prev = current;
        current = next;
    }
    
    // Connect
    prevLeft.next.next = current;
    prevLeft.next = prev;
    
    return dummy.next;
}
```
**Key Additions**:
- Dummy node for edge cases
- Navigate to correct position
- Reconnect after reversal

---

### LC 24: Swap Nodes in Pairs
**What changes**: Swap adjacent pairs
**Difficulty**: Medium
```java
public ListNode swapPairs(ListNode head) {
    if (head == null || head.next == null) return head;
    
    ListNode dummy = new ListNode(0);
    dummy.next = head;
    ListNode prev = dummy;
    
    while (prev.next != null && prev.next.next != null) {
        // Identify nodes to swap
        ListNode first = prev.next;
        ListNode second = prev.next.next;
        
        // Swap
        prev.next = second;
        first.next = second.next;
        second.next = first;
        
        // Move to next pair
        prev = first;
    }
    
    return dummy.next;
}
```
**Key**: Swap by redirecting pointers, not values

---

### LC 141: Linked List Cycle Detection (Floyd's Algorithm)
**What changes**: Two pointers moving at different speeds
**Difficulty**: Easy
```java
public boolean hasCycle(ListNode head) {
    if (head == null || head.next == null) return false;
    
    ListNode slow = head;
    ListNode fast = head.next;
    
    while (slow != fast) {
        if (fast == null || fast.next == null) return false;
        
        slow = slow.next;
        fast = fast.next.next;
    }
    
    return true;
}
```
**Key Insight**: Fast pointer catches slow in cycle

---

### LC 142: Find Cycle Start (Floyd's Algorithm Extended)
**What changes**: Find the starting node of cycle
**Difficulty**: Medium
```java
public ListNode detectCycle(ListNode head) {
    if (head == null || head.next == null) return null;
    
    ListNode slow = head, fast = head;
    
    // Find intersection point
    while (fast != null && fast.next != null) {
        slow = slow.next;
        fast = fast.next.next;
        
        if (slow == fast) break;
    }
    
    // No cycle
    if (fast == null || fast.next == null) return null;
    
    // Find cycle start
    ListNode p1 = head;
    ListNode p2 = slow;
    
    while (p1 != p2) {
        p1 = p1.next;
        p2 = p2.next;
    }
    
    return p1;
}
```
**Key**: Math property: distance to cycle start is same from head and intersection

---

### LC 25: Reverse Nodes in k-Group
**What changes**: Reverse in groups of k
**Difficulty**: Hard
```java
public ListNode reverseKGroup(ListNode head, int k) {
    ListNode dummy = new ListNode(0);
    dummy.next = head;
    ListNode prevGroup = dummy;
    
    while (true) {
        // Check if k nodes exist
        ListNode kThNode = prevGroup;
        for (int i = 0; i < k; i++) {
            kThNode = kThNode.next;
            if (kThNode == null) return dummy.next;
        }
        
        // Reverse k nodes
        ListNode groupPrev = kThNode.next;
        ListNode current = prevGroup.next;
        
        for (int i = 0; i < k; i++) {
            ListNode next = current.next;
            current.next = groupPrev;
            groupPrev = current;
            current = next;
        }
        
        ListNode temp = prevGroup.next;
        prevGroup.next = kThNode;
        prevGroup = temp;
    }
}
```
**Key Changes**: Validate k nodes exist before reversing

---

## 💡 Key Insights

### Three Pointer Pattern:
```java
ListNode prev = null;
ListNode current = head;
ListNode next = null;
```

### Always Save Next:
```java
// WRONG: next = current.next after modifying current
current.next = prev;  // This changes current.next!

// RIGHT: Save before modifying
ListNode next = current.next;
current.next = prev;
```

### Dummy Node Benefits:
- Handles reversal of head to new node
- Simplifies edge cases
- Often required for linked list problems

## Tips and Tricks

1. **Always save next**: "First I save the next pointer..."
2. **Draw the reversals**: Show pointer changes on paper
3. **Test edge cases**: null, single node, two nodes
4. **Use dummy node**: "I'll use a dummy to simplify..."
5. **Explain space**: "This is O(1) space, only pointer changes..."

## 📝 Practice Checklist

- [ ] Implement reverse linked list (iterative)
- [ ] Implement reverse linked list (recursive)
- [ ] Reverse partial list (LC 92)
- [ ] Detect cycle with Floyd's algorithm
- [ ] Find cycle start node
- [ ] Reverse k-group
