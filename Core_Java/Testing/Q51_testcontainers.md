# 🎯 Q51: TestContainers for Integration Testing?

> **Interview Frequency:** 42% | **Difficulty:** ⭐⭐⭐⭐ | **Study Time:** 4 minutes

---

## 🤔 Problem

Need real Postgres for tests, not H2 mock. How?

---

## 📌 TestContainers

```java
@SpringBootTest
@Testcontainers
class RepositoryTest {
    @Container
    static PostgreSQLContainer<?> postgres = 
        new PostgreSQLContainer<>("postgres:14")
            .withDatabaseName("test");
    
    @Autowired
    ProductRepository repo;
    
    @Test
    void testRepository() {
        repo.save(new Product("Phone"));
        assertEquals(1, repo.count());  // Real DB!
    }
}
```

---

## 📌 Supported Containers

- PostgreSQL, MySQL, MongoDB
- Redis, Kafka, RabbitMQ
- Elasticsearch, Cassandra
- Any Docker image

---

## ✅ Benefits

- **Real databases** - No mock limitations
- **Isolated** - Each test gets fresh container
- **Reproducible** - Same env locally and CI/CD
- **Easy** - One annotation

---

## 💬 Interview Tip (Say This Exactly)

"Use TestContainers for integration tests with real DBs. Docker required. Starts fresh container per test (slow but reliable). Great for CI/CD pipelines."

---

**Last Updated:** February 22, 2026  
**Next: [Q52_contract_testing.md](Q52_contract_testing.md)**
