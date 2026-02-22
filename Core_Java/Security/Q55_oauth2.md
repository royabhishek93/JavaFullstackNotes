# 🎯 Q55: OAuth 2.0 Fundamentals?

> **Interview Frequency:** 45% | **Difficulty:** ⭐⭐⭐⭐ | **Study Time:** 4 minutes

---

## 🤔 Problem

App wants to let users login with Google instead of username/password.

---

## 📌 OAuth 2.0 Flow

1. **User clicks "Login with Google"**
2. **Redirected to Google login**
3. **User authenticates with Google**
4. **Google redirects back with auth code**
5. **App exchanges code for access token**
6. **App uses token to access user info**
7. **User logged in without sharing password**

---

## ✅ Spring Security OAuth

```java
@Configuration
@EnableWebSecurity
class SecurityConfig extends WebSecurityConfigurerAdapter {
    @Override
    protected void configure(HttpSecurity http) throws Exception {
        http
            .oauth2Login()
            .authorizationEndpoint()
            .userAuthorizationUri("https://accounts.google.com/o/oauth2/v2/auth")
            .and()
            .tokenEndpoint()
            .accessTokenUri("https://www.googleapis.com/oauth2/v4/token");
    }
}
```

---

## ✅ Benefits

1. **No password sharing** - Google holds credentials
2. **Single sign-on** - One account, many apps
3. **Third-party integration** - Use Google, GitHub, Facebook

---

## 💬 Interview Tip (Say This Exactly)

"OAuth 2.0 lets users authenticate via third-party (Google, GitHub). User never shares password with your app. Exchange auth code for token. Spring Security handles flow automatically."

---

**Last Updated:** February 22, 2026  
**Next: [Q56_spring_security.md](Q56_spring_security.md)**
