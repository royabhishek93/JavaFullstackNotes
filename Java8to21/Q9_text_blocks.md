# Q9: What are text blocks (Java 13+)?

**Study Time:** 2-3 minutes

---

## Problem

Before text blocks, multiline strings were a pain with manual escaping and concatenation.

## ❌ Before: String Concatenation Hell

```java
// ❌ Hard to read SQL
String query = "SELECT * FROM payments WHERE " +
    "status = 'completed' AND " +
    "amount > 100 AND " +
    "created_at > '2024-01-01'";

// ❌ Escaped newlines and quotes everywhere
String json = "{\"user\": \"john\", " +
    "\"email\": \"john@example.com\", " +
    "\"status\": \"active\"}";

// ❌ HTML escaping nightmare
String html = "<html>" +
    "<body>" +
    "<h1>Welcome</h1>" +
    "</body>" +
    "</html>";
```

## ✅ Text Blocks: Clean Multiline Strings

```java
// ✅ Java 13+: Use triple quotes
String query = """
    SELECT * FROM payments WHERE 
    status = 'completed' AND 
    amount > 100 AND 
    created_at > '2024-01-01'
    """;

// ✅ JSON is readable
String json = """
    {
        "user": "john",
        "email": "john@example.com",
        "status": "active"
    }
    """;

// ✅ HTML stays clean
String html = """
    <html>
      <body>
        <h1>Welcome</h1>
      </body>
    </html>
    """;
```

## Key Rules

### Rule 1: Triple Quotes
```java
String text = """
    This is a text block.
    It can span multiple lines.
    """;
```

### Rule 2: Opening Quote Position
```java
// ✅ Correct: Opening triple-quote on same line or next line
String ok1 = """Line 1
               Line 2""";

String ok2 = """
           Line 1
           Line 2
           """;

// ❌ Wrong: Opening quotes can't be followed by content on same line
// String bad = """Hello
```

### Rule 3: Escape Sequences Still Work
```java
String text = """
    Tab\tseparated
    Quote: \"hello\"
    Newline after this:\
    (continued)
    """;
```

## Indentation: Automatic Trimming

```java
// Text blocks automatically trim leading whitespace
String sql = """
    SELECT * FROM users
    WHERE age > 18
    """;
// Result: "SELECT * FROM users\nWHERE age > 18\n"

// Use backslash to escape newline (no newline added)
String noNewline = """
    Line 1\
    Line 2
    """;
// Result: "Line 1Line 2\n"
```

## Real Example: SQL Embedded

```java
public class UserRepository {
    private final DataSource ds;
    
    public List<User> findActive() {
        String sql = """
            SELECT id, name, email FROM users
            WHERE status = 'active'
            AND created_at > CURRENT_DATE - INTERVAL '1 year'
            ORDER BY created_at DESC
            """;
        return queryUsers(sql);
    }
    
    private List<User> queryUsers(String sql) {
        // Use sql here - it's clean and readable
        try (Connection conn = ds.getConnection();
             Statement stmt = conn.createStatement()) {
            ResultSet rs = stmt.executeQuery(sql);
            // Process results...
        }
        return List.of();
    }
}
```

## Real Example: Formatted Text

```java
public String buildReport(String name, int sales, double total) {
    return """
        ===== SALES REPORT =====
        Agent: %s
        Sales: %d
        Total: $%.2f
        
        This report is confidential.
        """.formatted(name, sales, total);
}

// Usage
String report = buildReport("John Smith", 150, 25000.50);
// ✅ Produces formatted output with proper spacing!
```

## Real Example: JSON Response

```java
public record ApiResponse(String status, String message) {
    
    public static ApiResponse success(String data) {
        return new ApiResponse("success", formatJson(data));
    }
    
    private static String formatJson(String data) {
        return """
            {
              "status": "success",
              "data": %s,
              "timestamp": "%s"
            }
            """.formatted(data, Instant.now());
    }
}
```

## Evolution Timeline

```
Java 13: First preview
Java 14: Second preview
Java 15: Third preview (finalized with enhanced features)
Java 16+: Standard feature
```

## When Text Blocks Are Useful

🔥 **MUST KNOW:**
- SQL queries embedded in code
- JSON/XML payloads in tests
- HTML templates
- Multiline error messages

✅ **SHOULD KNOW:**
- Shell scripts as strings
- YAML configuration
- API request bodies

👍 **GOOD TO KNOW:**
- Text blocks as documentation examples
- Complex regular expressions

## Interview Tip

"Text blocks (Java 13+) use triple quotes `\"\"\"` for readable multiline strings without escape sequences. They automatically trim leading whitespace based on the closing quotes' indentation. Perfect for SQL, JSON, and XML. Use `.formatted()` for parameterization. This reduces boilerplate and makes code more maintainable."

## Quick Checklist

- ✅ Triple quotes `"""` for multiline
- ✅ No escape sequences needed for quotes  
- ✅ Automatic whitespace trimming
- ✅ Use backslash `\` to escape newlines
- ✅ `.formatted()` for parameters
- ✅ Escape sequences still work (`\t`, `\n`, etc)
- ✅ Available in Java 13+

---

## ⚠️ Common Pitfalls

**Pitfall 1: Indentation confusion - leading spaces included when you don't expect**

❌ **Wrong approach:**
```java
String xml = """
     <root>
       <child>value</child>
     </root>
    """;

// ❌ Includes those leading spaces!
// Result: "     <root>\n       <child>value</child>\n     </root>"
// Breaks XML parsing if indentation-sensitive
```
**Why it fails:** Text blocks trim common leading whitespace across ALL lines, but inconsistent indentation fails.

✅ **Right approach:**
```java
// Align closing triple-quotes with content
String xml = """
    <root>
      <child>value</child>
    </root>
    """;
// Result: "<root>\n  <child>value</child>\n</root>"
// Or use consistent indentation throughout
```

---

**Pitfall 2: Trying to use text blocks for code templates (don't - leads to brittle strings)**

❌ **Wrong approach:**
```java
String javaCode = """
    public class %s {
        private String name = "%s";
        
        public void doSomething() {
            System.out.println(name);
        }
    }
    """;

// Using String.format() later - error-prone
String classCode = String.format(javaCode, "MyClass", "test");
// What if you forget a placeholder?
```
**Why it fails:** Generating code via string templates is brittle and hard to maintain.

✅ **Right approach:**
```java
// For SQL: use prepared statements, not template strings
String sql = """
    SELECT * FROM users
    WHERE id = ?
    """;
// Use binding, not string substitution

// For code generation: use JavaPoet or similar tools
// Don't treat code as plain text
```

---

## 🛑 When NOT to Use Text Blocks

1. **For single-line strings** → Use regular string literals
2. **For code generation** → Use code generation libraries (JavaPoet)
3. **For security-sensitive data** → Don't embed secrets in text blocks
4. **In Java < 13** → Not available, use traditional concatenation

---

**Next:** Study Q10 on CompletableFuture for async operations
