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

## ⚠️ Common Pitfalls

**Pitfall 1: Confusing OAuth (authorization) with authentication**
```text
// ❌ Using OAuth access token as proof of identity
Access token = permission, not identity

// ✅ Use OpenID Connect for authentication (ID token)
```

**Pitfall 2: Missing state parameter (CSRF)**
```text
// ❌ No state = CSRF risk
https://accounts.google.com/o/oauth2/v2/auth?client_id=...&redirect_uri=...

// ✅ Include state and verify on callback
state=secureRandomValue
```

**Pitfall 3: Using implicit flow**
```text
// ❌ Implicit flow exposes tokens in browser

// ✅ Use Authorization Code + PKCE (best practice)
```

**Pitfall 4: Storing client secret in frontend**
```js
// ❌ Client secret in JavaScript bundle
const CLIENT_SECRET = "abc123";

// ✅ Keep secret on backend, use PKCE for public clients
```

---

## 🛑 When NOT to Use OAuth 2.0

- ❌ First-party app with only username/password
- ❌ No third-party access needed (overkill)
- ❌ Offline systems without internet connectivity
- ✅ DO use: SSO, third-party login, delegated access

---

**Last Updated:** February 22, 2026  
**Next: [Q56_spring_security.md](Q56_spring_security.md)**
