# Checked vs Unchecked Exceptions

**Study Time:** 8-10 minutes | **Frequency:** 70% in interviews | **Difficulty:** ⭐⭐⭐

---

## 🤔 Problem Scenario

Why are some exceptions checked and others not?

```java
// Checked exception - MUST handle or declare
public void readFile(String path) throws IOException {
    FileInputStream fis = new FileInputStream(path);  // Checked!
    // Compiler: "Must catch IOException or declare throws"
}

// Unchecked exception - Don't have to handle
public void divide(int a, int b) {
    return a / b;  // ArithmeticException if b == 0
    // Compiler: "No need to catch or declare"
}

public void process(String data) {
    String value = data.substring(10);  // StringIndexOutOfBoundsException
    // Compiler: "No need to catch or declare"
}
```

**Question:** Why the difference? When to use each?

---

## 🧠 Key Principle: Exception Hierarchy

```
Throwable
├── Error (JVM errors - don't catch)
│   ├── OutOfMemoryError
│   └── StackOverflowError
│
└── Exception
    ├── Checked Exception (extends Exception)
    │   ├── IOException
    │   ├── SQLException
    │   ├── FileNotFoundException
    │   └── ParseException
    │
    └── RuntimeException (extends Exception) - UNCHECKED
        ├── NullPointerException
        ├── ArithmeticException
        ├── ArrayIndexOutOfBoundsException
        ├── ClassCastException
        └── IllegalArgumentException
```

---

## 📊 Checked vs Unchecked

| Aspect | Checked | Unchecked |
|--------|---------|-----------|
| **Extends** | Exception | RuntimeException |
| **Must catch?** | YES (or declare) | NO |
| **Compiler enforces?** | YES | NO |
| **Recoverable?** | Usually YES | Usually NO (programming error) |
| **Examples** | IO, SQL, Parse | Null, Index, Cast |
| **When thrown** | Runtime (external) | Programming error |

---

## ✅ Scenario 1: Checked Exception (Must Handle)

```java
public class FileProcessor {
    
    // Option 1: Catch and handle
    public void readFileHandled(String path) {
        try {
            FileInputStream fis = new FileInputStream(path);
            // Read file
        } catch (IOException e) {
            System.err.println("Cannot read file: " + e.getMessage());
        }
    }

    // Option 2: Declare and let caller handle
    public void readFileDeclared(String path) throws IOException {
        FileInputStream fis = new FileInputStream(path);
        // Read file
    }

    // Option 3: Wrap and throw custom exception
    public void readFileWrapped(String path) throws DataException {
        try {
            FileInputStream fis = new FileInputStream(path);
        } catch (IOException e) {
            throw new DataException("Failed to load data", e);
        }
    }
}
```

**Key point:** Compiler REQUIRES handling checked exceptions.

---

## ✅ Scenario 2: Unchecked Exception (Programming Error)

```java
public class DataProcessor {
    
    // NO try-catch needed - these are programming errors
    
    public void processArray(int[] arr) {
        int value = arr[10];  // ArrayIndexOutOfBoundsException if arr.length < 10
        // If this happens, it's a BUG - should fix code, not catch
    }

    public void castType(Object obj) {
        String str = (String) obj;  // ClassCastException if not String
        // If happens, it's a BUG - check type first or fix caller
    }

    public void divideNumbers(int a, int b) {
        int result = a / b;  // ArithmeticException if b == 0
        // If happens, caller shouldn't divide by zero - that's their bug
    }

    public void processNullable(String data) {
        if (data == null) {
            throw new IllegalArgumentException("data cannot be null");
        }
        System.out.println(data.length());  // No NPE now
    }
}
```

**Key point:** No compiler enforcement - developer's responsibility to prevent.

---

## ✅ Scenario 3: When to Throw Checked Exception

```java
// Checked exception: Problem external to your code
public class DatabaseConnection {
    
    public void connect(String url) throws SQLException {
        // Connection fails due to database issue (not our bug)
        // Caller should handle - retry, use fallback, etc.
    }
    
    public void write(Data data) throws IOException {
        // File I/O fails due to system issue
        // Caller should handle - try again, log, alert user, etc.
    }
}

// Usage
public class Application {
    public static void main(String[] args) {
        DatabaseConnection db = new DatabaseConnection();
        
        try {
            db.connect("jdbc:mysql://localhost:3306/db");
            db.write(new Data());
        } catch (SQLException e) {
            logger.error("Database error: " + e.getMessage());
            // Retry logic, fallback, etc.
        } catch (IOException e) {
            logger.error("File error: " + e.getMessage());
            // Retry logic, fallback, etc.
        }
    }
}
```

---

## ✅ Scenario 4: When to Throw Unchecked Exception

```java
// Unchecked exception: Programming error
public class Calculator {
    
    public int divide(int a, int b) {
        // Unchecked - caller should validate input before calling
        if (b == 0) {
            throw new IllegalArgumentException("Divisor cannot be zero");
        }
        return a / b;
    }

    public String getElement(List<String> list, int index) {
        // Unchecked - caller should check bounds before calling
        if (index < 0 || index >= list.size()) {
            throw new IndexOutOfBoundsException("Index: " + index + ", Size: " + list.size());
        }
        return list.get(index);
    }

    public <T> T cast(Object obj, Class<T> type) {
        // Unchecked - caller should verify type before casting
        if (!type.isInstance(obj)) {
            throw new ClassCastException("Expected " + type + " but got " + obj.getClass());
        }
        return (T) obj;
    }
}

// Usage - Caller's responsibility to validate
public class Usage {
    public void calculate() {
        Calculator calc = new Calculator();
        
        int divisor = getUserInput();  // Validate first
        if (divisor == 0) {
            displayError("Divisor cannot be zero");
            return;
        }
        
        int result = calc.divide(100, divisor);  // Safe to call
    }
}
```

---

## ❌ Common Mistakes

### ❌ Mistake 1: Catching Exception (Too Broad)

```java
// WRONG - Catches too much
try {
    int result = array[index];
} catch (Exception e) {
    // Could catch ArrayIndexOutOfBoundsException (programming error)
    // Or catch IOException from elsewhere (resource error)
    // Can't handle both properly
}

// CORRECT - Catch specific exception
try {
    int result = array[index];
} catch (ArrayIndexOutOfBoundsException e) {
    logger.error("Invalid index: " + index);
}
```

---

### ❌ Mistake 2: Swallowing Exceptions

```java
// WRONG - Exception lost
try {
    database.connect(url);
} catch (SQLException e) {
    // Silent failure - bug may go unnoticed for days!
}

// CORRECT - Log or rethrow
try {
    database.connect(url);
} catch (SQLException e) {
    logger.error("Database connection failed: " + e.getMessage(), e);
    throw new ApplicationException("Cannot connect to database", e);
}
```

---

### ❌ Mistake 3: Throwing Checked Exception for Programming Error

```java
// WRONG - Programmer error thrown as checked
public void processArray(int[] arr) throws IOException {
    // IOException? This has nothing to do with file I/O!
    if (arr == null) {
        throw new IOException("Array cannot be null");
    }
    // Confuses caller
}

// CORRECT - Unchecked for programming error
public void processArray(int[] arr) {
    if (arr == null) {
        throw new IllegalArgumentException("Array cannot be null");
    }
    // Clear that caller should validate
}
```

---

### ❌ Mistake 4: Declaring Too Many Exceptions

```java
// WRONG - Declares exception that might not be thrown
public void process() throws IOException, SQLException, ParseException {
    // Only IO operations, no SQL or parsing!
    FileInputStream fis = new FileInputStream("file.txt");
}

// CORRECT - Declare only what's thrown
public void process() throws IOException {
    FileInputStream fis = new FileInputStream("file.txt");
}

// Even better - Catch and rethrow if needed
public void process() throws DataException {
    try {
        FileInputStream fis = new FileInputStream("file.txt");
    } catch (IOException e) {
        throw new DataException("Failed to load data", e);
    }
}
```

---

## 💬 Interview Tip (Exact Answer)

"Use checked exceptions for recoverable, expected errors (I/O, network, SQL). Use unchecked for programming mistakes (invalid params, nulls). Checked exceptions force handling but can clutter APIs, so modern Java often wraps checked exceptions into unchecked at boundaries."

---

## ☑️ Quick Checklist

- Checked: recoverable, external failures (I/O, DB, network).
- Unchecked: programming errors (nulls, invalid params, index).
- Checked must be caught or declared.
- Unchecked do not require declaration.
- Wrap checked exceptions at API boundaries when needed.

---

## 🎯 Interview Q&A

### Q1: "Difference between checked and unchecked?"

**Answer (30 seconds):**
```
Checked: Extends Exception (not RuntimeException)
- Compiler enforces handling
- Must catch or declare throws
- Example: IOException, SQLException
- Use: External problems (file, database, network)

Unchecked: Extends RuntimeException
- No compiler enforcement
- Don't have to catch
- Example: NullPointerException, ArrayIndexOutOfBounds
- Use: Programming errors (null check, bounds check, etc.)
```

---

### Q2: "When to use checked vs unchecked?"

**Answer:**
```
CHECKED (External problems):
- File I/O (file missing, permissions)
- Database (connection failed, query error)
- Network (timeout, connection refused)
- Parsing (invalid format)

UNCHECKED (Programming errors):
- Null validation (should check before calling)
- Array bounds (should check size first)
- Type casting (should verify type first)
- Illegal arguments (caller should validate)

RULE OF THUMB:
- Is this a recoverable error? → Checked
- Is this a programming mistake? → Unchecked
```

---

### Q3: "Should I create custom exceptions?"

**Answer:**
```
YES, create custom exception when:
1. Need domain-specific error
2. Want different handling at different levels

Examples:

Custom Checked:
public class PaymentException extends Exception {
    // Used when payment service unavailable (recoverable)
}

Custom Unchecked:
public class ValidationException extends RuntimeException {
    // Used for input validation errors (caller's bug)
}

Usage:
try {
    paymentService.charge(amount);
} catch (PaymentException e) {
    // Retry, use fallback payment method, etc.
}

if (amount < 0) {
    throw new ValidationException("Amount must be positive");
}

DON'T:
- Extend Exception unnecessarily (use standard ones first)
- Create checked exceptions for programming errors
- Create unchecked exceptions for recoverable errors
```

---

### Q4: "Catch Exception - okay?"

**Answer:**
```
NO - Too broad!

try {
    riskyOperation();
} catch (Exception e) {
    // Could catch ANY exception
    // You don't know what went wrong
}

CORRECT:
try {
    connection = db.connect();  // Throws SQLException
    data = file.read();         // Throws IOException
} catch (SQLException e) {
    logger.error("Database error", e);
} catch (IOException e) {
    logger.error("File error", e);
}

OR:
try {
    riskyOperation();
} catch (Exception e) {
    logger.error("Unexpected error", e);
    throw new RuntimeException("Unhandled", e);  // Bail out
}

Only use catch (Exception) when:
- Catching all is intentional
- You're logging/monitoring
- You're wrapping for a caller
```

---

## 📚 Common Checked Exceptions

```
IOException (file operations)
├── FileNotFoundException
├── SocketException
└── EOFException

SQLException (database)

ParseException (parsing)

ClassNotFoundException

InterruptedException (threading)

CloneNotSupportedException

ReflectiveOperationException
```

---

## 📚 Common Unchecked Exceptions

```
RuntimeException
├── NullPointerException (null access)
├── ArrayIndexOutOfBoundsException (invalid index)
├── ClassCastException (invalid type cast)
├── IllegalArgumentException (bad parameter)
├── IllegalStateException (wrong state for operation)
├── UnsupportedOperationException (not implemented)
└── ArithmeticException (e.g., divide by zero)

Error (don't catch)
├── OutOfMemoryError
├── StackOverflowError
└── VirtualMachineError
```

---

## 🔑 Key Takeaways

| Concept | Why Important | Interview Score |
|---------|---------------|-----------------|
| Checked/unchecked distinction | Core Java concept | ⭐⭐⭐⭐⭐ |
| When to use each | Design decision | ⭐⭐⭐⭐⭐ |
| Exception propagation | Error handling | ⭐⭐⭐⭐ |
| Custom exceptions | Domain modeling | ⭐⭐⭐⭐ |
| Catch specific vs broad | Code quality | ⭐⭐⭐⭐ |

---

**Priority:** ✅ SHOULD KNOW (70% interview frequency)

**Related Topics:**
- [Exception Handling Best Practices](#)
- [Exception Propagation in Overriding](#)
- [Custom Exception Design](#)

---

**Last Updated:** March 5, 2026
