# Interface Evolution (Java 8/9) - Interview Overview

**Use this file as a map. Full topic-wise guides are linked below.**

---

## Why This Exists

These topics repeat across multiple notes. To avoid duplication and keep learning linear, this file points to the dedicated Q-files.

---

## Study Map (Topic-Wise)

1) Problem before Java 8 (breaking interface changes)
- [Java8to21/Q1_interface_problem_before_java8.md](Java8to21/Q1_interface_problem_before_java8.md)

2) Default methods (syntax + behavior)
- [Java8to21/Q2_default_methods.md](Java8to21/Q2_default_methods.md)

3) Static methods in interfaces (factories/utilities)
- [Java8to21/Q3_static_methods_interfaces.md](Java8to21/Q3_static_methods_interfaces.md)

4) Private methods in interfaces (Java 9+ reuse)
- [Java8to21/Q4_private_methods_interfaces.md](Java8to21/Q4_private_methods_interfaces.md)

5) Conflicting defaults (diamond problem)
- [Java8to21/Q5_conflicting_default_methods.md](Java8to21/Q5_conflicting_default_methods.md)

---

## Quick Recall

- Default methods: optional behavior, backward compatibility.
- Static methods: utilities/factories on the interface.
- Private methods: internal reuse for defaults.
- Conflict resolution: override and choose `InterfaceName.super.method()`.

---

## Interview Answer (One-Liner)

> "Java 8 added default and static methods to evolve interfaces without breaking implementations; Java 9 added private methods for internal reuse. Conflicting defaults require an explicit override."

