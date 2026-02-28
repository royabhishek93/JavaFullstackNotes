# 🎯 Q50: Spring Boot Test Slices?

> **Interview Frequency:** 45% | **Difficulty:** ⭐⭐⭐ | **Study Time:** 3 minutes

---

## 🤔 Problem

Test only REST layer without loading database. How?

---

## 📌 Test Slices

| Annotation | Loads | Use |
|------------|-------|-----|
| `@WebMvcTest` | Web layer only | REST controllers |
| `@DataJpaTest` | JPA layer only | Repository |
| `@DataMongoTest` | Mongo layer | Mongo repository |
| `@SpringBootTest` | Full context | Integration tests |

---

## ✅ Example

```java
@WebMvcTest(ProductController.class)
class ControllerTest {
    @MockBean
    ProductService service;
    
    @Autowired
    MockMvc mockMvc;
    
    @Test
    void testGetProduct() throws Exception {
        given(service.getProduct(1)).willReturn(new Product("Phone"));
        
        mockMvc.perform(get("/products/1"))
            .andExpect(status().isOk());
    }
}
```

---

## 💬 Interview Tip (Say This Exactly)

"Use @WebMvcTest for controller tests (fast, no DB). Use @DataJpaTest for repository tests. Use @SpringBootTest for full integration. Test slices are faster than full context."

---

## ⚠️ Common Pitfalls

**Pitfall 1: Using @SpringBootTest for everything**
```java
// ❌ Loads full context for simple controller test
@SpringBootTest
class ControllerTest { }

// ✅ Use @WebMvcTest
@WebMvcTest(ProductController.class)
class ControllerTest { }
```

**Pitfall 2: Forgetting to mock dependencies in slices**
```java
// ❌ Missing @MockBean
@WebMvcTest(ProductController.class)
class ControllerTest { }

// ✅ Provide mocks
@MockBean ProductService service;
```

**Pitfall 3: Mixing slice annotations**
```java
// ❌ Conflicting slices
@WebMvcTest
@DataJpaTest
class ConfusingTest { }

// ✅ Use one slice per test
```

---

## 🛑 When NOT to Use Test Slices

- ❌ Cross-layer workflows (use @SpringBootTest)
- ❌ Complex integration with multiple layers
- ✅ DO use: Fast, focused layer tests

---

**Last Updated:** February 22, 2026  
**Next: [Q51_testcontainers.md](Q51_testcontainers.md)**
