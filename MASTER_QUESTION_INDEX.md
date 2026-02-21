# 📑 Master Question Index - All 27 Individual Q&A Files

> **Complete directory of all bite-sized interview Q&A files organized by topic**
> 
> **Study time:** 2-5 minutes per question | **Total coverage:** 32 interview questions across 3 topics

---

## 🔥 CORE JAVA (7 Questions)

### String Memory & Allocation (4 Questions)

| # | Question | File | Time | Topics |
|---|----------|------|------|--------|
| Q1 | Where does `"hello"` go in memory? | [Q1_string_pool_memory.md](Core_Java/Q1_string_pool_memory.md) | 2 min | String Pool, Heap, Literals |
| Q2 | Why does `c == d` return false when both are `"hi"`? | [Q2_string_concatenation.md](Core_Java/Q2_string_concatenation.md) | 2 min | Runtime Concat, Reference vs Content |
| Q3 | What does `.intern()` do and when to use it? | [Q3_string_intern_method.md](Core_Java/Q3_string_intern_method.md) | 2 min | String Pool Optimization, Memory Cost |
| Q4 | How does garbage collection work with String Pool? | [Q4_string_garbage_collection.md](Core_Java/Q4_string_garbage_collection.md) | 2 min | GC, Pool Lifecycle, Memory Management |

**Study these if:** Your interview involves Java fundamentals, backend development, memory optimization

**Key concepts:** String Pool vs Heap allocation, `==` vs `.equals()`, memory optimization through pooling

---

### Immutable Classes & Defensive Copying (3 Questions)

| # | Question | File | Time | Topics |
|---|----------|------|------|--------|
| Q5 | What makes a class immutable? | [Q5_immutable_class_requirements.md](Core_Java/Q5_immutable_class_requirements.md) | 2 min | final class, final fields, no setters, defensive copy |
| Q6 | What's the difference between `new ArrayList<>(list)` and `.clone()`? | [Q6_defensive_copying_vs_clone.md](Core_Java/Q6_defensive_copying_vs_clone.md) | 3 min | Deep vs Shallow Copy, When to Use |
| Q7 | How do you return mutable collections safely? | [Q7_return_mutable_collections.md](Core_Java/Q7_return_mutable_collections.md) | 3 min | Collections.unmodifiable, List.copyOf, Encapsulation |

**Study these if:** You're designing DTOs, value objects, or thread-safe code

**Key concepts:** Four requirements for immutability, defensive copying patterns, safe collection returns

---

### Bonus: Multithreading & Concurrency (in reference documents)
- Full reference: [java-multithreading-concurrency-guide.md](Core_Java/java-multithreading-concurrency-guide.md) (2500+ lines)
- Volatile reference: [java-volatile-atomic-interview.md](Core_Java/java-volatile-atomic-interview.md)
- Async reference: [java-non-blocking-vs-async-interview.md](Core_Java/java-non-blocking-vs-async-interview.md)

---

## ✨ MODERN JAVA 8-21 (12 Questions)

### Interface Evolution (5 Questions)

| # | Question | File | Time | Topics |
|---|----------|------|------|--------|
| Q1 | What was the main problem before Java 8 interfaces? | [Q1_interface_problem_before_java8.md](Java8to21/Q1_interface_problem_before_java8.md) | 2 min | API Evolution, Breaking Changes |
| Q2 | What is a default method? | [Q2_default_methods.md](Java8to21/Q2_default_methods.md) | 2 min | Default Implementation, Optional Override |
| Q3 | What are static methods in interfaces for? | [Q3_static_methods_interfaces.md](Java8to21/Q3_static_methods_interfaces.md) | 2 min | Factory Pattern, Utilities, Non-polymorphic |
| Q4 | What about Java 9+ private methods in interfaces? | [Q4_private_methods_interfaces.md](Java8to21/Q4_private_methods_interfaces.md) | 2 min | Code Reuse, Internal Logic, DRY Principle |
| Q5 | What happens with conflicting default methods? | [Q5_conflicting_default_methods.md](Java8to21/Q5_conflicting_default_methods.md) | 3 min | Diamond Problem, Resolution, super keyword |

**Study these if:** Your interview involves modern Java APIs, framework design, or backward compatibility

**Key concepts:** Default methods, static methods, private methods (Java 9+), conflict resolution

---

### Data Classes & Type Safety (2 Questions)

| # | Question | File | Time | Topics |
|---|----------|------|------|--------|
| Q6 | What are Records and why were they added? | [Q6_records_introduced.md](Java8to21/Q6_records_introduced.md) | 3 min | Boilerplate Elimination, Immutability, DTOs |
| Q7 | What about Sealed Classes? | [Q7_sealed_classes.md](Java8to21/Q7_sealed_classes.md) | 3 min | Controlled Inheritance, Type Safety, Java 17 |

**Study these if:** Your interview involves data modeling, DTOs, or Java 15+

**Key concepts:** Records vs traditional classes, Sealed classes for inheritance control

---

### Modern Syntax & Async (3 Questions)

| # | Question | File | Time | Topics |
|---|----------|------|------|--------|
| Q8 | What is Pattern Matching? | [Q8_pattern_matching.md](Java8to21/Q8_pattern_matching.md) | 2 min | Type Checking, Casting, Java 16+ |
| Q9 | What are Text Blocks? | [Q9_text_blocks.md](Java8to21/Q9_text_blocks.md) | 2 min | Multiline Strings, JSON/SQL, Java 13+ |
| Q10 | What is CompletableFuture? | [Q10_completablefuture_basics.md](Java8to21/Q10_completablefuture_basics.md) | 3 min | Async Operations, Non-blocking, Promise Pattern |

**Study these if:** Your interview mentions code cleanliness, Java 16+, or async APIs

**Key concepts:** Pattern matching, Text blocks, CompletableFuture basics

---

### Async Composition & Error Handling (2 Questions)

| # | Question | File | Time | Topics |
|---|----------|------|------|--------|
| Q11 | How do you chain async operations? | [Q11_chaining_completablefutures.md](Java8to21/Q11_chaining_completablefutures.md) | 3 min | thenCompose, thenApply, Non-blocking Chains |
| Q12 | How do you handle exceptions in async? | [Q12_exception_handling_completablefuture.md](Java8to21/Q12_exception_handling_completablefuture.md) | 3 min | exceptionally(), handle(), whenComplete() |

**Study these if:** Your interview involves reactive programming or async APIs

**Key concepts:** Async chaining, exception handling in async pipelines

---

## 🌟 SPRING BOOT (5 Questions)

### Bean Scopes & Configuration (5 Questions)

| # | Question | File | Time | Topics |
|---|----------|------|------|--------|
| Q1 | What are the main bean scopes in Spring? | [Q1_bean_scopes.md](SpringBoot/Q1_bean_scopes.md) | 3 min | Singleton, Prototype, Request, Session, Application |
| Q2 | What happens when you inject Prototype into Singleton? | [Q2_prototype_in_singleton.md](SpringBoot/Q2_prototype_in_singleton.md) | 3 min | ObjectFactory, ObjectProvider, Scope Mismatch |
| Q3 | Is a Singleton bean thread-safe? | [Q3_singleton_thread_safety.md](SpringBoot/Q3_singleton_thread_safety.md) | 3 min | Race Conditions, Atomic, Synchronized, Immutability |
| Q4 | What's the difference between Singleton and ThreadLocal? | [Q4_singleton_vs_threadlocal.md](SpringBoot/Q4_singleton_vs_threadlocal.md) | 3 min | One-per-Container vs One-per-Thread, Memory |
| Q5 | How does Spring handle circular dependencies? | [Q5_circular_dependencies.md](SpringBoot/Q5_circular_dependencies.md) | 3 min | Detection, Setter Injection, @Lazy, ObjectFactory |

**Study these if:** You're working with Spring Boot or backend frameworks

**Key concepts:** Bean scopes, thread-safety, circular dependency resolution

---

## 🎯 Quick Navigation by Scenario

### Scenario 1: Last-Minute Prep (30 minutes)
Pick 8-10 questions that match your role:
- Backend API: Q1, Q2, Q5 (Core_Java) + Q6, Q10, Q11 (Java8to21) + Q1, Q3 (SpringBoot)
- Data Systems: Q5, Q6, Q7 (Core_Java) + Q6 (Java8to21) + Q1, Q2 (SpringBoot)
- Reactive/Async: Q14, Q15 (in reference docs) + Q10, Q11, Q12 (Java8to21) + Q4 (SpringBoot)

### Scenario 2: One-Hour Study
- Core Java: Study Q1-Q4 (String Memory, 8 mins)
- Core Java: Study Q5-Q7 (Immutability, 8 mins)
- Java8to21: Study Q1-Q3 (Interface Methods, 6 mins)
- Java8to21: Study Q6, Q10 (Records & CompletableFuture, 6 mins)
- SpringBoot: Study Q1, Q3 (Bean Scopes & Thread Safety, 6 mins)
- Practice: Say answers out loud (20 mins)

### Scenario 3: Full Study (3 hours)
- Read all 27 individual question files (81 mins)
- Read consolidated guides (1.5 hours)
- Practice 5-10 favorites (30 mins)

---

## 📊 Statistics

| Metric | Count |
|--------|-------|
| **Total Questions** | 27 |
| **Core Java** | 7 |
| **Java 8-21** | 12 |
| **Spring Boot** | 5 |
| | |
| **Total Study Time** | ~90 minutes |
| **Avg Time per Question** | 3.3 minutes |
| **Fastest Study** | Individual Q file (2 mins) |
| **Comprehensive Study** | Consolidated guides (1.5 hours) |
| **Deep Mastery** | Full references (4-6 hours) |

---

## 📂 File Structure

```
Individual Question Files (27 total):
├── Core_Java/
│   ├── Q1_string_pool_memory.md
│   ├── Q2_string_concatenation.md
│   ├── Q3_string_intern_method.md
│   ├── Q4_string_garbage_collection.md
│   ├── Q5_immutable_class_requirements.md
│   ├── Q6_defensive_copying_vs_clone.md
│   └── Q7_return_mutable_collections.md
│
├── Java8to21/
│   ├── Q1_interface_problem_before_java8.md
│   ├── Q2_default_methods.md
│   ├── Q3_static_methods_interfaces.md
│   ├── Q4_private_methods_interfaces.md
│   ├── Q5_conflicting_default_methods.md
│   ├── Q6_records_introduced.md
│   ├── Q7_sealed_classes.md
│   ├── Q8_pattern_matching.md
│   ├── Q9_text_blocks.md
│   ├── Q10_completablefuture_basics.md
│   ├── Q11_chaining_completablefutures.md
│   └── Q12_exception_handling_completablefuture.md
│
└── SpringBoot/
    ├── Q1_bean_scopes.md
    ├── Q2_prototype_in_singleton.md
    ├── Q3_singleton_thread_safety.md
    ├── Q4_singleton_vs_threadlocal.md
    └── Q5_circular_dependencies.md

Consolidated Guides (3 total):
├── Core_Java/CORE_JAVA_QA_REFERENCE.md (15 Q&As)
├── Java8to21/JAVA8TO21_QA_REFERENCE.md (12 Q&As)
└── SpringBoot/SPRINGBOOT_QA_REFERENCE.md (5 Q&As)

Full References (8+ documents):
├── Core_Java/java-string-memory-allocation.md
├── Core_Java/java-immutable-complete-guide.md
├── Core_Java/java-multithreading-concurrency-guide.md
├── Core_Java/java-volatile-atomic-interview.md
├── Core_Java/java-non-blocking-vs-async-interview.md
├── Java8to21/java-interface-default-static-methods.md
├── Java8to21/java-completablefuture-interview.md
├── Java8to21/java-9-to-21-features.md
└── Spring*/ (bean scopes, circular deps, singleton concurrency)

Navigation (3 guides):
├── MASTER_QUESTION_INDEX.md (this file)
├── INDIVIDUAL_QUESTIONS_GUIDE.md
└── STRUCTURE_SUMMARY.md
```

---

## ✅ Each Question File Includes

- **Study Time:** 2-5 minutes estimate
- **Problem:** Real challenge being solved
- **Why It Happens:** Root cause explanation
- **❌ Wrong Code:** Common mistakes shown
- **✅ Right Code:** Correct solution
- **Interview Tip:** Exact answer to give in interview
- **Quick Checklist:** Key points to remember
- **Next Question:** Navigation to related topic

---

## 🚀 How to Use This Index

### Method 1: Search by Topic
1. Find your topic above (String Memory, Bean Scopes, etc.)
2. Click any question link
3. Study 2-5 minutes per question
4. Move to next related question

### Method 2: Search by Study Time
- **2 mins:** Q1, Q2, Q3, Q4, Q8, Q9 (in respective folders)
- **3 mins:** Q5, Q6, Q7 + Q10, Q11, Q12 + Q1-Q5 (SpringBoot)

### Method 3: Search by Interview Role
- **Backend API:** [Q1-Q2 Core], [Q1-Q3 Java8to21], [Q1, Q3 Spring]
- **Data Systems:** [Q5-Q7 Core], [Q6 Java8to21], [Q1-Q2 Spring]
- **Reactive:** [Reference docs], [Q10-Q12 Java8to21], [Q4 Spring]

---

## 💡 Pro Tips

- **Bookmark this page** for quick reference during interview prep
- **Print the table** above for offline studying
- **Follow "Next: Study Q..." links** to maintain topic continuity
- **Review Quick Checklists** the night before interview
- **Say Interview Tips out loud** to practice delivery

---

**Last Updated:** February 22, 2026  
**Total Repository Questions:** 32 (27 individual files shown above + 5 in consolidated guides only)
