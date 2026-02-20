# Copilot Instructions for JavaFullstackNotes

## Repository Purpose
JavaFullstackNotes is a **Java and Spring interview preparation repository** with deep, scenario-based explanations of advanced topics. The goal is to help developers understand complex concepts through detailed walkthroughs, not just quick reference guides.

## Repository Structure
```
Java/              → Modern Java features (9-21), memory management, language features
Spring/            → Spring framework concepts, bean scopes, dependency injection, concurrency
```

## Key Documentation Patterns

### 1. **Scenario-First Approach**
Every note begins with a real-world scenario, not abstract definitions:
- Start with: "Given [code], what happens?"
- Include code examples that reproduce the issue
- Walk through step-by-step execution
- Explain the "why" behind the behavior

**Example structure:**
```
## Scenario
[Code snippet showing the problem]

## Key Principle
[Core concept explanation]

## Step-by-Step Analysis
[Detailed walkthrough]

## Interview Q&A
[Common questions]
```

### 2. **Interview-First Content**
- Focus on questions interviewers actually ask
- Include both simple and trick questions
- Provide concise, accurate answers (not opinion)
- Reference production use cases

### 3. **Visual Priority Organization**
Use emoji/priority tables to guide focus:
- 🔥 MUST KNOW (production critical, first interviews)
- ✅ SHOULD KNOW (common, good to mention)
- 👍 GOOD TO KNOW (differentiator knowledge)
- ⚙️ NICHE (specialized, low priority)

### 4. **Precision Over Breadth**
- Explain specific behaviors deeply (e.g., when strings go to pool vs heap)
- Avoid generic advice; ground in JVM/Spring internals
- Include edge cases and limitations
- Document what surprised you, not what you already knew

## Common Concepts to Document

### Java Files Should Cover:
- Memory management (stack, heap, string pool)
- Language features and their production use
- Version-specific behavior changes
- Performance implications

### Spring Files Should Cover:
- Bean lifecycle and scopes
- Dependency injection edge cases
- Concurrency and thread safety
- Common misunderstandings (e.g., prototype in singleton)

## Content Guidelines

1. **Code Examples**: Always executable, include expected output
2. **Edge Cases**: Document surprising behavior (e.g., `c == d` comparison)
3. **Pitfalls**: Highlight what causes bugs in production
4. **Cross-References**: Link related concepts when they clarify understanding

## File Naming Convention
- Use kebab-case: `spring-bean-scopes.md`, `java-9-to-21-features.md`
- Prefix with topic: topic name
- Avoid version numbers in filename unless they're core to understanding

## When Adding New Content
- Identify the "gotcha" or misunderstanding that leads to bugs
- Structure explanation around a concrete scenario
- Include at least one code example showing the unexpected behavior
- Add interview Q&A based on what you'd ask candidates
- Reference related files if they provide complementary knowledge
