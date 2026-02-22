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

**Last Updated:** February 22, 2026  
**Next: [Q51_testcontainers.md](Q51_testcontainers.md)**
