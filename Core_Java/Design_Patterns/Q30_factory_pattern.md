# 🎯 Q30: Factory vs Abstract Factory patterns?

> **Interview Frequency:** 55% | **Difficulty:** ⭐⭐⭐ | **Study Time:** 3 minutes

---

## 🤔 Problem

Create database connections: MySQL, PostgreSQL, MongoDB. Who decides which type?

---

## 📌 Comparison

### **Factory Pattern** (Simple)
```java
class DatabaseFactory {
    static Database create(String type) {
        switch(type) {
            case "mysql": return new MySQLDatabase();
            case "postgres": return new PostgresDatabase();
        }
    }
}
// Usage: Database db = DatabaseFactory.create("mysql");
```

### **Abstract Factory** (Family)
```java
interface DatabaseFactory {
    Connection createConnection();
    StatementBuilder createStatementBuilder();
}
class MySQLFactory implements DatabaseFactory { }
class PostgresFactory implements DatabaseFactory { }
// Usage: Creates related objects together
```

---

## 💬 Interview Tip (Say This Exactly)

"Factory for single object creation. Abstract factory for creating families of related objects. Abstract factory when you need multiple objects to work together (connection + statement builder)."

---

**Last Updated:** February 22, 2026  
**Next: [Q31_builder_pattern.md](Q31_builder_pattern.md)**
