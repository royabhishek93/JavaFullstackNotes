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

**Last Updated:** February 22, 2026  
**Previous: [Q51_testcontainers.md](Q51_testcontainers.md) | Next: [../Security/Q53_auth_basics.md](../Security/Q53_auth_basics.md)**
