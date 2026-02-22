# 🎯 Q40: CORS and API Security Basics

> **Interview Frequency:** 50% | **Difficulty:** ⭐⭐⭐ | **Study Time:** 3 minutes

---

## 🤔 Problem

Frontend on domain1.com can't call API on domain2.com. CORS error!

---

## 📌 CORS (Cross-Origin Resource Sharing)

Browser blocks cross-origin requests by default for security.

```java
@Configuration
class CorsConfig {
    @Bean
    public WebMvcConfigurer corsConfigurer() {
        return new WebMvcConfigurer() {
            @Override
            public void addCorsMappings(CorsRegistry registry) {
                registry.addMapping("/api/**")
                    .allowedOrigins("https://frontend.com")
                    .allowedMethods("GET", "POST", "PUT", "DELETE")
                    .allowCredentials(true)
                    .maxAge(3600);
            }
        };
    }
}
```

---

## 📌 Security Best Practices

1. **HTTPS only** - Encrypt in transit
2. **API keys** - Validate every request
3. **Rate limiting** - Prevent abuse (100 req/min)
4. **Input validation** - Prevent injection attacks
5. **CORS whitelist** - Only trusted origins
6. **CSP headers** - Prevent XSS
7. **CSRF tokens** - For state-changing requests

---

## 💬 Interview Tip (Say This Exactly)

"Enable CORS only for trusted origins. Always use HTTPS. Add rate limiting. Validate all inputs. Use API keys or JWT for authentication. Add security headers (CSP, X-Frame-Options)."

---

**Last Updated:** February 22, 2026  
**Previous: [Q39_pagination_filtering.md](Q39_pagination_filtering.md) | Next: [../Performance_JVM/Q41_garbage_collection_types.md](../Performance_JVM/Q41_garbage_collection_types.md)**
