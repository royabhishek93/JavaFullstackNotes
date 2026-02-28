# 🎯 Q52: Contract Testing (Pact, Spring Cloud Contract)?

> **Interview Frequency:** 40% | **Difficulty:** ⭐⭐⭐⭐ | **Study Time:** 4 minutes

---

## 🤔 Problem

Microservice A calls Service B. B's API changes. A breaks! How to prevent?

---

## 📌 Contract Testing

Defines agreement between consumer and provider.

```java
// Consumer side (Service A)
@Test
void testProviderContract() {
    // THIS is the contract - what A expects from B
    given()
        .when().get("/users/1")
        .then()
        .statusCode(200)
        .body("name", equalTo("John"));
}

// Provider side (Service B)
// Provider must satisfy this contract
@RunWith(SpringRunner.class)
@SpringBootTest
class ProviderContractTest {
    @Test
    void verifyContract() {
        // Verify B's endpoint matches contract from A
    }
}
```

---

## 📌 Tools

- **Pact** - Consumer-driven contracts
- **Spring Cloud Contract** - Provider-driven contracts
- **OpenAPI/Swagger** - API First approach

---

## 💬 Interview Tip (Say This Exactly)

"Contract testing prevents integration failures. Consumer defines what it expects (contract), provider verifies it satisfies. Prevents 'I changed my API' surprises between microservices."

---

## ⚠️ Common Pitfalls

**Pitfall 1: Contracts not versioned**
```text
// ❌ Provider changes response, old contract still used

// ✅ Version contracts with API versions
```

**Pitfall 2: Treating contract tests as full integration tests**
```text
// ❌ Contract tests replace real integration tests

// ✅ Use both: contracts for compatibility, integration for runtime behavior
```

**Pitfall 3: Not sharing stubs with consumers**
```text
// ❌ Provider generates stubs but consumers never use them

// ✅ Publish stubs to artifact repo (Nexus, Artifactory)
```

---

## 🛑 When NOT to Use Contract Testing

- ❌ Monolith with single codebase
- ❌ Tight release coordination (no independent deploys)
- ✅ DO use: Microservices with independent teams

---

**Last Updated:** February 22, 2026  
**Previous: [Q51_testcontainers.md](Q51_testcontainers.md) | Next: [../Security/Q53_auth_basics.md](../Security/Q53_auth_basics.md)**
