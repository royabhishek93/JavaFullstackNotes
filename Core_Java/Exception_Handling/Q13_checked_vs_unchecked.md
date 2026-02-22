# 🎯 Q13: Checked vs Unchecked Exceptions - Design Trade-offs?

> **Interview Frequency:** 85% | **Difficulty:** ⭐⭐⭐⭐ | **Study Time:** 3 minutes

---

## 🤔 Problem

Understanding when to use checked vs unchecked exceptions and why this design choice matters.

### Code Scenario
```java
// Checked exception - must catch or declare
public void readFile(String path) throws IOException {
    Files.readAllLines(Paths.get(path));
}

// Unchecked exception - optional to catch
public void parseJSON(String json) {
    JSONParser parser = new JSONParser();
    parser.parse(json);  // Can throw JSONException (unchecked)
}
```

---

## 📌 Why It Happens

**Checked Exceptions (extends Exception):**
- Compiler **forces** you to handle or declare
- Use for **recoverable** conditions (file not found, network timeout)
- Throws must be declared in method signature

**Unchecked Exceptions (extends RuntimeException):**
- Compiler **does NOT force** handling
- Use for **programming errors** (null pointer, wrong parameter)
- No throws declaration needed

---

## ❌ Wrong (Over-using Checked Exceptions)

```java
// WRONG: Checked exception for programming error
public void divide(int a, int b) throws IllegalArgumentException {
    if (b == 0) {
        throw new IllegalArgumentException("Divisor cannot be zero");
    }
    return a / b;
}
// Caller FORCED to catch even though it's a programming error!

// WRONG: Wrapping in checked and throwing (brittle)
public User findUser(long id) throws UserNotFoundException {
    // ...
}
// Every caller MUST handle, even if they don't care
service.findUser(123);  // Won't compile without catch!
```

---

## ✅ Right (Strategic Exception Choice)

```java
// RIGHT: Unchecked for programming errors
public void divide(int a, int b) {
    if (b == 0) {
        throw new IllegalArgumentException("Divisor cannot be zero");
    }
    return a / b;
}
// Caller can choose to catch - their responsibility

// RIGHT: Checked for recoverable conditions
public void readConfigFile(String path) throws IOException {
    return Files.readAllLines(Paths.get(path));
}
// IOException is recoverable - caller should handle

// RIGHT: Wrap checked as unchecked in external API
public List<User> getAllUsers() {  // No throws declared!
    try {
        return database.query("SELECT * FROM users");
    } catch (SQLException e) {
        throw new RuntimeException("Database error", e);  // Wrap as unchecked
    }
}
// Caller doesn't need to handle SQL errors - we did
```

---

## 💬 Interview Tip (Say This Exactly)

"Use checked exceptions for recoverable, expected errors (IOException, timeout). Use unchecked exceptions for programming mistakes (null params, divide-by-zero). Checked exceptions force handling but can clutter code. Modern Java prefers unchecked for APIs."

---

## ☑️ Quick Checklist

- ✅ **Checked (IOException, SQLException):** Client CAN recover
- ✅ **Unchecked (NullPointerException, IllegalArgumentException):** Programming error
- ✅ Checked exceptions must be caught or declared in `throws`
- ✅ Unchecked exceptions don't need declaration
- ✅ Don't over-use checked exceptions (causes checked exception inflation)
- ✅ Wrap checked exceptions as unchecked when needed
- ✅ Cause chain: `new RuntimeException("message", cause)`

---

## 📚 Real Flipkart Scenario

```java
// Payment processing - smart exception handling

// CHECKED: Network timeout happens, should retry
public void chargeCard(String cardId, double amount) 
    throws PaymentGatewayTimeoutException {
    // Can recover by retrying
    httpClient.post(paymentGateway, request);
}

// UNCHECKED: Programming error - invalid amount
public void validateAmount(double amount) {
    if (amount <= 0) {
        throw new IllegalArgumentException("Amount must be positive");
    }
}

// API: Wrap checked as unchecked for cleaner client code
public Payment processOrder(Order order) {  // No throws!
    try {
        validateAmount(order.getTotal());        // Unchecked OK
        return chargeCard(order.cardId, order.total);
    } catch (PaymentGatewayTimeoutException e) {
        // WE handle the timeout - retry logic
        return retryPayment(order, 3);
    } catch (Exception e) {
        // Programming errors bubble up as unchecked
        throw new RuntimeException("Payment failed", e);
    }
}
```

---

## ➡️ Bonus Follow-ups

1. **"Should you create custom checked exceptions?"** → Rarely. Most APIs use unchecked now (Spring, Kafka, etc.)
2. **"Why did Java add checked exceptions?"** → Force explicit error handling, but proved too verbose
3. **"What's better practice in 2026?"** → Unchecked exceptions + proper logging

---

## 🔗 Related Questions

- **Q14:** When to create custom exceptions
- **Q16:** Exception handling in async code
- **Q58:** Security (exception handling in auth)

---

**Last Updated:** February 22, 2026  
**Next: [Q14_custom_exceptions.md](Q14_custom_exceptions.md)**
