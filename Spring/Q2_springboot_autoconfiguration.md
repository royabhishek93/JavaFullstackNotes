# Q2: Spring Boot Auto-Configuration (Entry Point + spring.factories)

**Study Time:** 10-12 minutes | **Frequency:** 75% in interviews 🔥 | **Difficulty:** ⭐⭐⭐⭐

---

## Scenario

**Given this code, what happens at startup?**

```java
@SpringBootApplication
public class DemoApplication {
    public static void main(String[] args) {
        SpringApplication.run(DemoApplication.class, args);
    }
}
```

You add `spring-boot-starter-web` and run the app. Without writing any Tomcat or MVC bean, the app still starts an embedded server and exposes REST endpoints. **Why?**

---

## Key Principle

`@SpringBootApplication` is a **meta-annotation** that triggers three critical behaviors:

1. `@SpringBootConfiguration` - Marks the class as a source of bean definitions
2. `@EnableAutoConfiguration` - Activates auto-config based on classpath and conditions
3. `@ComponentScan` - Scans current package and sub-packages for components

Auto-configuration is driven by **registries** found in `spring.factories` (older versions) or `AutoConfiguration.imports` (newer versions).

---

## Step-by-Step Analysis

### 1) Entry Point: `@SpringBootApplication`

```java
@SpringBootApplication
public class DemoApplication { ... }
```

This expands to:

```java
@SpringBootConfiguration
@EnableAutoConfiguration
@ComponentScan
```

### 2) Component Scanning

- Spring scans the package of `DemoApplication` and its sub-packages.
- Finds `@RestController`, `@Service`, `@Repository`, `@Configuration`, etc.
- Registers them as beans in the `ApplicationContext`.

### 3) Enable Auto-Configuration

This triggers Spring Boot to **load configuration classes** from:

- `META-INF/spring.factories` (Spring Boot 2.x and earlier)
- `META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports` (Spring Boot 3.x+)

These files list auto-configuration classes like:

```
org.springframework.boot.autoconfigure.web.servlet.DispatcherServletAutoConfiguration
org.springframework.boot.autoconfigure.web.servlet.ServletWebServerFactoryAutoConfiguration
org.springframework.boot.autoconfigure.jackson.JacksonAutoConfiguration
```

### 4) Conditions Decide What Activates

Each auto-config class has conditions like:

```java
@ConditionalOnClass(Servlet.class)
@ConditionalOnMissingBean(DispatcherServlet.class)
```

So the decision is **deterministic**:

- If `tomcat-embedded.jar` is on the classpath
- Then activate `ServletWebServerFactoryAutoConfiguration`
- Which registers a `TomcatServletWebServerFactory` bean
- Which starts embedded Tomcat

---

## Visual Startup Flow

```
@SpringBootApplication
   ├─ @SpringBootConfiguration  → registers config class
   ├─ @ComponentScan            → finds your beans
   └─ @EnableAutoConfiguration  → loads auto-configs
            ├─ spring.factories / AutoConfiguration.imports
            ├─ evaluate @Conditional...
            └─ register beans if conditions match
```

---

## Example: Why Tomcat Starts Automatically

```java
// In auto-config jar
@ConditionalOnClass(Servlet.class)
@ConditionalOnMissingBean(ServletWebServerFactory.class)
public class ServletWebServerFactoryAutoConfiguration {
    
    @Bean
    public TomcatServletWebServerFactory tomcatFactory() {
        return new TomcatServletWebServerFactory();
    }
}
```

- `spring-boot-starter-web` brings `tomcat-embed-core` on the classpath.
- Condition matches.
- Bean is created.
- Embedded Tomcat starts.

---

## Interview Q&A

### Q1: What exactly does `@SpringBootApplication` do?

**Answer:**
```
It is a meta-annotation combining:
- @SpringBootConfiguration  → config class
- @EnableAutoConfiguration  → loads auto-config classes
- @ComponentScan            → scans for components
```

---

### Q2: Where does Spring Boot find auto-configurations?

**Answer:**
```
Spring Boot reads:
- META-INF/spring.factories (Boot 2.x and earlier)
- META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports (Boot 3.x+)

These files list the auto-configuration classes to import.
```

---

### Q3: How does Spring decide which auto-config to apply?

**Answer:**
```
Each auto-config class is guarded by @Conditional annotations like:
- @ConditionalOnClass
- @ConditionalOnMissingBean
- @ConditionalOnProperty

If conditions match, the configuration is activated.
```

---

### Q4: How do I disable an auto-configuration?

**Answer:**
```java
@SpringBootApplication(exclude = {
    DataSourceAutoConfiguration.class
})
public class DemoApplication { ... }
```

Or in application.properties:
```
spring.autoconfigure.exclude=org.springframework.boot.autoconfigure.jdbc.DataSourceAutoConfiguration
```

---

### Q5: What is the difference between `spring.factories` and `AutoConfiguration.imports`?

**Answer:**
```
- spring.factories: legacy registry for auto-configuration classes
- AutoConfiguration.imports: newer, direct import list used by Boot 3.x

Both are functionally similar, just different mechanisms.
```

---

## Common Pitfalls

```java
❌ Pitfall 1: Placing main class in a sub-package
// Component scan only scans its package + sub-packages
// If main class is deep in hierarchy, upper packages are skipped

✅ Fix: Move main class to root package
com.example.app.DemoApplication

❌ Pitfall 2: Missing dependency
// If tomcat-embed-core is not on classpath
// No embedded server is created

✅ Fix: Add spring-boot-starter-web

❌ Pitfall 3: Custom bean prevents auto-config
// If you define your own DispatcherServlet bean
// @ConditionalOnMissingBean fails and Boot skips its auto-config

✅ Fix: Remove custom bean or use @Primary carefully
```

---

## Interview Answer (Concise)

**Q: "How does Spring Boot auto-configuration work?"**

**Answer:**

> "The entry point is `@SpringBootApplication`, which expands to `@SpringBootConfiguration`, `@EnableAutoConfiguration`, and `@ComponentScan`. `@EnableAutoConfiguration` loads auto-config classes from `spring.factories` (Boot 2) or `AutoConfiguration.imports` (Boot 3). Each auto-config class is guarded by `@Conditional` annotations so it only activates when the classpath and properties match. For example, if `tomcat-embed-core` is present, Boot registers a `ServletWebServerFactory` and starts embedded Tomcat automatically."

---

## Key Takeaways

| Concept | Why It Matters | Interview Score |
|---------|----------------|-----------------|
| Meta-annotations | Explains startup behavior | ⭐⭐⭐⭐⭐ |
| Auto-config registries | Shows where config comes from | ⭐⭐⭐⭐ |
| Conditional annotations | Explains decision logic | ⭐⭐⭐⭐⭐ |
| Embedded server trigger | Common interview question | ⭐⭐⭐⭐ |
| Disable auto-config | Practical production control | ⭐⭐⭐⭐ |
