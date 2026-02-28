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

## ⚠️ Common Pitfalls

**Pitfall 1: Disabling CSRF for browser apps**
```java
// ❌ Disables CSRF for form-based login
http.csrf(csrf -> csrf.disable());

// ✅ Keep CSRF for browser apps, disable only for stateless APIs
```

**Pitfall 2: Overly broad permitAll**
```java
// ❌ Exposes everything
http.authorizeHttpRequests(authz -> authz
    .requestMatchers("/**").permitAll()
);

// ✅ Restrict public endpoints only
http.authorizeHttpRequests(authz -> authz
    .requestMatchers("/public/**", "/login").permitAll()
    .anyRequest().authenticated()
);
```

**Pitfall 3: Misordered matchers**
```java
// ❌ Specific rules after anyRequest()
authz.anyRequest().authenticated();
authz.requestMatchers("/admin/**").hasRole("ADMIN");  // Never reached!

// ✅ Order matters
authz.requestMatchers("/admin/**").hasRole("ADMIN")
     .anyRequest().authenticated();
```

**Pitfall 4: Using @PreAuthorize without enabling method security**
```java
// ❌ Annotation ignored if method security not enabled
@PreAuthorize("hasRole('ADMIN')")
public void adminTask() {}

// ✅ Enable method security
@EnableMethodSecurity
```

---

## 🛑 When NOT to Use Default Config

- ❌ Stateless APIs using JWT (disable sessions + CSRF)
- ❌ Custom auth flows (use AuthenticationProvider)
- ❌ Reactive apps (use Spring Security for WebFlux)
- ✅ DO use: Standard form login, role-based access, simple apps

---

**Last Updated:** February 22, 2026  
**Next: [Q57_password_hashing.md](Q57_password_hashing.md)**
