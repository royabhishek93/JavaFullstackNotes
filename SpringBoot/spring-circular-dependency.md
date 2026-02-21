# Spring Circular Dependency (Beginner-Friendly)

## Scenario
- Bean A depends on Bean B.
- Bean B depends on Bean A.

## What Happens?
- Spring starts creating A, but A needs B.
- Spring starts creating B, but B needs A.
- It becomes a loop, so Spring cannot finish creating the beans.

## How Spring Resolves It
- **Constructor injection:** Spring fails fast with a circular dependency error.
- **Setter/field injection:** Spring can sometimes break the loop by creating one bean first, then injecting the other later (not guaranteed for all cases).

## How to Fix (Easy Options)
- **Remove the circle:** move shared logic to a new bean C that both A and B use.
- **Use setter injection + `@Lazy`:** delay one side so the loop breaks at startup.
- **Refactor responsibilities:** if A and B both need each other, the design is likely too tightly coupled.

## Tiny A/B/C Example
```java
@Component
public class A {
	private final C c;

	public A(C c) {
		this.c = c;
	}
}

@Component
public class B {
	private final C c;

	public B(C c) {
		this.c = c;
	}
}

@Component
public class C {
	// shared logic used by both A and B
}
```

Here, A and B both depend on C, so there is no circular dependency.

## Interview Questions (With Short Answers)
**Q1: What is a circular dependency in Spring?**
A: When two or more beans depend on each other in a loop (A needs B, and B needs A).

**Q2: What happens if A depends on B and B depends on A?**
A: Spring gets stuck while creating beans and cannot finish the context.

**Q3: Why does constructor injection fail with circular dependencies?**
A: Constructors need fully created dependencies up front, so Spring cannot build either bean first.

**Q4: Can setter/field injection resolve it?**
A: Sometimes yes. Spring can create one bean first, then inject the other later. It is not guaranteed for all cases.

**Q5: What is the cleanest fix?**
A: Remove the cycle by moving shared logic to a new bean (C) or redesigning responsibilities.

**Q6: When is `@Lazy` used?**
A: To delay one dependency so the loop breaks at startup, but it is a workaround, not the best design.
