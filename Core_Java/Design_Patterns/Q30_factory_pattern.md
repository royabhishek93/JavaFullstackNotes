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

## ⚠️ Common Pitfalls

**Pitfall 1: Factory with switch/if-else explosion**
```java
// ❌ Adding new type requires modifying factory
class DatabaseFactory {
    static Database create(String type) {
        if (type.equals("mysql")) return new MySQLDatabase();
        else if (type.equals("postgres")) return new PostgresDatabase();
        else if (type.equals("mongo")) return new MongoDatabase();
        // Adding new DB = modify this method (violates Open-Closed)
    }
}

// ✅ Use map of factories or service provider
class DatabaseFactory {
    static Map<String, Supplier<Database>> factories = Map.of(
        "mysql", MySQLDatabase::new,
        "postgres", PostgresDatabase::new
    );
    static Database create(String type) {
        return factories.get(type).get();
    }
}
```

**Pitfall 2: Not handling unknown types**
```java
// ❌ No handling for invalid type
Database db = DatabaseFactory.create("oracle");  // NullPointerException!

// ✅ Throw exception or return default
static Database create(String type) {
    return factories.getOrDefault(type, () -> {
        throw new IllegalArgumentException("Unknown DB: " + type);
    }).get();
}
```

**Pitfall 3: Factory doing too much**
```java
// ❌ Factory with business logic
class DatabaseFactory {
    static Database create(String type) {
        Database db = new MySQLDatabase();
        db.connect();  // Don't do this here!
        db.executeSchema();  // Factory should just create!
        return db;
    }
}

// ✅ Factory only creates, caller configures
Database db = DatabaseFactory.create("mysql");
db.connect();
```

---

## 🛑 When NOT to Use Factory

- ❌ Only one implementation (no abstraction needed)
- ❌ Simple constructor is sufficient
- ❌ Dependency injection handles creation (Spring)
- ✅ DO use: Multiple implementations chosen at runtime

---

---

**Last Updated:** February 22, 2026  
**Next: [Q31_builder_pattern.md](Q31_builder_pattern.md)**
