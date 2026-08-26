# String & Immutability Questions

Interview preparation for Java String memory management and immutable object design.

## Quick Q&A Files (2-5 minutes per question)

| Q# | Question | Study Time |
|----|----------|-----------|
| [Q1](string-pool-vs-heap.md) | Where does `"hello"` go in memory? | 2m |
| [Q2](string-concatenation.md) | Why does `c == d` return false when both are `"hi"`? | 2m |
| [Q3](string-intern-method.md) | What does `.intern()` do and when to use it? | 2m |
| [Q4](string-garbage-collection.md) | How does garbage collection work with String Pool? | 2m |
| [Q5](immutable-class-requirements.md) | What makes a class immutable? | 2m |
| [Q6](defensive-copying-vs-clone.md) | Difference between `new ArrayList<>(list)` and `.clone()`? | 3m |
| [Q7](return-mutable-collections.md) | How do you return mutable collections safely? | 3m |

## Deep-Dive Guides (_Guides/ - 45-90 minutes)

- **[java-string-memory-allocation.md](_Guides/java-string-memory-allocation.md)** - Complete string memory model (45-60 min)
- **[java-immutable-complete-guide.md](_Guides/java-immutable-complete-guide.md)** - Building immutable classes (60-90 min)

## Interview Prep Strategy

1. **Start here:** Q1-Q5 (core concepts - 10 minutes total)
2. **Then:** Q6-Q7 (defensive programming - 6 minutes)
3. **Deep dive:** Either guide file for 45-90 minute mastery
4. **Practice:** Implement an immutable custom class (1-2 hours)

## Interview Frequency

- **75%** - Q1 String pool memory
- **70%** - Q2 String concatenation  
- **65%** - Q5 Immutable class requirements
- **50%** - Q3 String intern, Q7 Return collections safely
- **45%** - Q6 Defensive copying
- **35%** - Q4 String GC

---

**Suggested study time:** 30-45 minutes for all Q&A files + 1-2 hours for guides
