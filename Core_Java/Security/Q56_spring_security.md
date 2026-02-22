# 🎯 Q56: Spring Security Configuration?

> **Interview Frequency:** 48% | **Difficulty:** ⭐⭐⭐⭐ | **Study Time:** 4 minutes

---

## 🤔 Problem

Protect endpoints: /public (anyone), /user (authenticated), /admin (ADMIN role).

---

## 📌 Configuration

```java
@Configuration
@EnableWebSecurity
public class SecurityConfig {
    @Bean
    SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
            .authorizeHttpRequests(authz -> authz
                .requestMatchers("/public/**").permitAll()
                .requestMatchers("/user/**").authenticated()
                .requestMatchers("/admin/**").hasRole("ADMIN")
                .anyRequest().authenticated()
            )
            .formLogin(form -> form
                .loginPage("/login")
                .defaultSuccessUrl("/dashboard")
            )
            .logout(logout -> logout
                .logoutSuccessUrl("/login")
            );
        return http.build();
    }
}
```

---

## ✅ Authentication Providers

- **Form login** - Username/password
- **JWT/Token** - Stateless
- **LDAP** - Enterprise auth
- **OAuth 2.0** - Third-party
- **Custom** - Implement `AuthenticationProvider`

---

## 💬 Interview Tip (Say This Exactly)

"Spring Security: authorize endpoints with `@PreAuthorize` or config. Authenticate with form/JWT/OAuth. Use HttpSecurity to configure filters. Implement custom AuthenticationProvider for special auth logic."

---

**Last Updated:** February 22, 2026  
**Next: [Q57_password_hashing.md](Q57_password_hashing.md)**
