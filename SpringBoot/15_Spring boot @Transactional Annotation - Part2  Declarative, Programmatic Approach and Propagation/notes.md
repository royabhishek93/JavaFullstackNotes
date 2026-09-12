# Spring Boot @Transactional — Declarative vs Programmatic, and Transaction Propagation

## What is this? (Plain English)

Think of the transaction manager hierarchy like a restaurant franchise contract. `TransactionManager` is just the brand name on the door — an empty marker interface with nothing inside. `PlatformTransactionManager` is the franchise agreement every branch must sign: it defines exactly three operations every branch must support — `getTransaction`, `commit`, and `rollback` — but doesn't say *how* to do them. `AbstractPlatformTransactionManager` is the corporate head office's standard operating procedure — a default implementation of those three methods that most branches (JDBC, JPA, Hibernate, JTA) can reuse as-is, overriding only the parts that are specific to their own "kitchen" (their database technology).

**Declarative vs Programmatic** is the difference between ordering off a menu versus cooking it yourself. Declarative (`@Transactional`) means you just slap the annotation on a method and Spring Boot silently figures out which transaction manager to use, opens the transaction, commits it, or rolls it back — you never see any of that machinery. Programmatic means you personally write the "get transaction → do work → commit/rollback" code by hand. It's more work, but it gives you fine control over exactly which lines of code are wrapped in a transaction.

**Propagation** is like joining a phone conference that may already be in progress. `REQUIRED` (the default) says "join the call if one is already happening, otherwise start one." `REQUIRES_NEW` says "put the current call on hold, start a brand-new separate call, and resume the old call once the new one ends." `SUPPORTS` says "join the call if there's one, otherwise just talk without a call." `NOT_SUPPORTED` says "hang up (suspend) the current call, do the work without any call, then resume it afterward." `MANDATORY` says "there must already be a call in progress, or I refuse to run." `NEVER` says "there must NOT be a call in progress, or I refuse to run."

## The Problem It Solves

### 1. Which transaction manager should handle my transaction?
An application can have several `PlatformTransactionManager` implementations available depending on the database technology in use (`DataSourceTransactionManager` for raw JDBC, `JpaTransactionManager`, `HibernateTransactionManager`, `JtaTransactionManager` for distributed/two-phase-commit transactions across multiple resources). By default, Spring Boot auto-selects one for you (commonly the JPA transaction manager) based on the data source you're using. If you don't want that automatic choice — for example, you want to force JDBC instead of JPA, or force Hibernate — you need a way to explicitly declare which transaction manager `@Transactional` should use.

### 2. Declarative `@Transactional` can hold a database connection open across a slow external call
Consider a method that does: (1) an initial set of DB writes, (2) an external API call to a third-party service, then (3) a final set of DB writes. If the whole method is wrapped in `@Transactional`, the database connection acquired at step 1 stays open for the *entire* duration of the external API call in step 2 — even though the external call has nothing to do with the database. If that external API takes 3-4 seconds and this happens under peak traffic with many concurrent requests, the connection pool gets exhausted holding connections open for calls that are just waiting on a slow third party. This is exactly the kind of dependency chain you can't simply remove (the three steps must happen together), so you need **programmatic** transaction management: to precisely control which parts of the method are inside a transaction and which are not, instead of wrapping the entire method.

### 3. When one `@Transactional` method calls another `@Transactional` method, which transaction "wins"?
If Method A (transactional) calls Method B (also transactional), does Method B's logic become part of Method A's transaction, or does a brand-new transaction get created for Method B? This is exactly what **propagation** controls, and getting it wrong can silently merge unrelated units of work into one transaction (or vice versa) without you realizing it.

## Propagation Decision Flow

*(Full Mermaid source: see [mermaid-diagrams.md](mermaid-diagrams.md))*

```text
Method A (@Transactional) calls Method B (@Transactional)
                    |
                    v
        What propagation is set on Method B?
                    |
   -----------------------------------------------------------------
   |            |            |             |            |          |
REQUIRED   REQUIRES_NEW   SUPPORTS   NOT_SUPPORTED   MANDATORY    NEVER
(default)
   |            |            |             |            |          |
Parent      Parent       Parent        Parent        Parent     Parent
exists?     exists?      exists?       exists?       exists?    exists?
 / \          / \          / \           / \           / \        / \
Yes  No     Yes   No     Yes   No      Yes   No      Yes  No    Yes  No
 |    |      |     |      |     |       |     |       |    |     |    |
Join  New  Suspend New   Join  Run    Suspend Run    Join Throw Throw Run
same  txn  parent, txn  parent no    parent, no      parent exc  exc  no
txn        new txn,           txn    run no    txn                    txn
           resume                    txn,
           parent                    resume
           after                     parent
                                      after
```

## Key Code / Config

### Choosing an explicit transaction manager (instead of Spring Boot's auto-selection)

```java
@Configuration
public class AppConfig {

    // Bean name defaults to the method name -> "userTransactionManager"
    @Bean
    public PlatformTransactionManager userTransactionManager(DataSource dataSource) {
        return new DataSourceTransactionManager(dataSource);
    }
}
```

```java
@Service
public class UserService {

    // Tells Spring to use the bean named "userTransactionManager" instead of auto-selecting one
    @Transactional(transactionManager = "userTransactionManager", propagation = Propagation.REQUIRED)
    public void updateUser(Long userId) {
        // ... business logic
    }
}
```

### Programmatic approach 1 — using `PlatformTransactionManager` directly

```java
@Service
public class UserService {

    private final PlatformTransactionManager transactionManager;

    // Constructor injection instead of @Autowired
    public UserService(PlatformTransactionManager userTransactionManager) {
        this.transactionManager = userTransactionManager;
    }

    public void updateUserProgrammatic(Long userId) {
        TransactionDefinition definition = new DefaultTransactionDefinition() {{
            setName("updateUserTxn");
            setPropagationBehavior(TransactionDefinition.PROPAGATION_REQUIRED);
        }};

        TransactionStatus status = transactionManager.getTransaction(definition);
        try {
            // update DB - initial set of operations
            // external API call
            // update DB - final set of operations
            transactionManager.commit(status);
        } catch (Exception e) {
            transactionManager.rollback(status);
            throw e;
        }
    }
}
```

### Programmatic approach 2 — using `TransactionTemplate` (cleaner wrapper)

```java
@Configuration
public class AppConfig {

    @Bean
    public PlatformTransactionManager userTransactionManager(DataSource dataSource) {
        return new DataSourceTransactionManager(dataSource);
    }

    @Bean
    public TransactionTemplate transactionTemplate(PlatformTransactionManager userTransactionManager) {
        TransactionTemplate template = new TransactionTemplate(userTransactionManager);
        template.setPropagationBehavior(TransactionDefinition.PROPAGATION_REQUIRED);
        template.setName("updateUserTxn");
        return template;
    }
}
```

```java
@Service
public class UserService {

    private final TransactionTemplate transactionTemplate;

    public UserService(TransactionTemplate transactionTemplate) {
        this.transactionTemplate = transactionTemplate;
    }

    public void updateUserProgrammatic(Long userId) {
        transactionTemplate.execute((TransactionCallback<Void>) status -> {
            // this lambda is your business logic - the "do in transaction" call back
            // update DB - initial set of operations
            // external API call
            // update DB - final set of operations
            return null;
        });
        // TransactionTemplate internally does: getTransaction -> run the callback -> commit,
        // and calls rollback automatically if the callback throws
    }
}
```

### Propagation in action — REQUIRED (joins the existing transaction)

```java
@Service
public class MethodOneService {

    @Autowired
    private MethodTwoService methodTwoService;

    @Transactional // default propagation = REQUIRED
    public void methodOne() {
        System.out.println("Active? " + TransactionSynchronizationManager.isActualTransactionActive());
        System.out.println("Txn name: " + TransactionSynchronizationManager.getCurrentTransactionName());
        // ... initial DB operations
        methodTwoService.methodTwo();
        // ... final DB operations
    }
}

@Service
public class MethodTwoService {

    @Transactional(propagation = Propagation.REQUIRED)
    public void methodTwo() {
        // Active = true, Txn name = SAME as methodOne's transaction
        // REQUIRED joins the parent transaction instead of creating a new one
        System.out.println("Active? " + TransactionSynchronizationManager.isActualTransactionActive());
        System.out.println("Txn name: " + TransactionSynchronizationManager.getCurrentTransactionName());
    }
}
```

### Propagation in action — REQUIRES_NEW (suspends the parent, runs independently)

```java
@Service
public class MethodTwoService {

    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public void methodTwo() {
        // Parent transaction (methodOne's) is suspended (NOT aborted) for the duration of this call.
        // Active = true, Txn name = DIFFERENT from methodOne's transaction name.
        // Once this method's own transaction commits or rolls back, the parent transaction resumes.
        System.out.println("Active? " + TransactionSynchronizationManager.isActualTransactionActive());
        System.out.println("Txn name: " + TransactionSynchronizationManager.getCurrentTransactionName());
    }
}
```

### Passing propagation programmatically

```java
// Approach 1 - PlatformTransactionManager + TransactionDefinition
DefaultTransactionDefinition definition = new DefaultTransactionDefinition();
definition.setName("updateUserTxn");
definition.setPropagationBehavior(TransactionDefinition.PROPAGATION_REQUIRED);
TransactionStatus status = transactionManager.getTransaction(definition);

// Approach 2 - TransactionTemplate, set once when building the bean
TransactionTemplate template = new TransactionTemplate(userTransactionManager);
template.setPropagationBehavior(TransactionDefinition.PROPAGATION_REQUIRES_NEW);
template.setName("updateUserTxn");
```

## Important Concepts

- **`TransactionManager`**: The top-level, empty marker interface — no methods.
- **`PlatformTransactionManager`**: The core interface with exactly three methods — `getTransaction`, `commit`, `rollback`. Every concrete transaction manager must implement these.
- **`AbstractPlatformTransactionManager`**: Abstract class providing default implementations of `getTransaction`/`commit`/`rollback`, which concrete managers (`DataSourceTransactionManager`, `JpaTransactionManager`, `HibernateTransactionManager`, `JtaTransactionManager`) extend and override where their underlying technology differs.
- **JDBC vs JPA vs Hibernate vs JTA managers**: JDBC requires manually writing queries. JPA maps entities to tables and auto-generates most CRUD, so you skip writing inserts/selects yourself. Hibernate is a JPA implementation but a distinct framework/transaction manager. JTA (Java Transaction API) is used specifically for **distributed transactions** (two-phase commit) across multiple resources; for a single local database, JDBC/JPA/Hibernate all work. Moving to a NoSQL database requires swapping in a different transaction manager entirely, though the underlying concept (manage the transaction, talk to the DB) stays the same.
- **Declarative transaction management**: Using `@Transactional`. Spring Boot hides the transaction manager selection and the get/commit/rollback plumbing from you.
- **Programmatic transaction management**: Writing the get/commit/rollback logic yourself in code. More flexible (lets you exclude slow, non-DB work like external API calls from the transaction boundary) but more code to maintain.
- **`TransactionTemplate`**: A cleaner wrapper over the raw `getTransaction`/`commit`/`rollback` calls. You call `execute()` with a `TransactionCallback` (a functional interface with a `doInTransaction` method) containing your business logic; the template handles get transaction, running your callback, then commit or rollback.
- **`TransactionInterceptor`**: The AOP interceptor invoked by `@Transactional`. Internally it calls something like "create transaction if necessary," which itself calls `getTransaction` and applies the propagation rules (check `NEVER` → throw, check `NOT_SUPPORTED`/`REQUIRES_NEW` → suspend parent and start new, etc.) before invoking the actual method, then commits or rolls back afterward.
- **Propagation — `REQUIRED`** (default): Join the parent transaction if one exists; otherwise create a new one.
- **Propagation — `REQUIRES_NEW`**: Always run in its own new transaction. If a parent transaction exists, it is suspended (not aborted) while the new transaction runs, and resumed once the new transaction commits or rolls back.
- **Propagation — `SUPPORTS`**: Join the parent transaction if one exists; otherwise run without any transaction at all.
- **Propagation — `NOT_SUPPORTED`**: Always run without a transaction. If a parent transaction exists, it is suspended for the duration of the call and resumed afterward.
- **Propagation — `MANDATORY`**: Requires a parent transaction to already exist; joins it if present, otherwise throws an exception. Never creates a new transaction itself.
- **Propagation — `NEVER`**: Requires that NO parent transaction exists; throws an exception if one is found, otherwise runs without any transaction.
- **Suspend vs abort**: Suspending a parent transaction (in `REQUIRES_NEW` / `NOT_SUPPORTED`) only pauses it — it is not aborted/rolled back. It resumes normally once the nested call finishes.

## Interview Q&A

**Q1: What are the three core methods every `PlatformTransactionManager` implementation must support, and why is `TransactionManager` itself basically useless on its own?**
A: `getTransaction`, `commit`, and `rollback`. `TransactionManager` is an empty marker interface at the top of the hierarchy with no methods — all the real contract lives in `PlatformTransactionManager`, which is why every concrete manager (JDBC, JPA, Hibernate, JTA) implements that interface (directly or via `AbstractPlatformTransactionManager`).

**Q2: Why would you ever need to explicitly configure a `PlatformTransactionManager` bean instead of letting Spring Boot auto-select one?**
A: Spring Boot auto-selects a transaction manager based on your data source (commonly JPA). If you need a specific one instead — e.g., forcing JDBC to write manual queries, or forcing Hibernate instead of the default JPA manager — you declare a `@Bean` of type `PlatformTransactionManager` in an `@Configuration` class and reference it by bean name in `@Transactional(transactionManager = "...")`.

**Q3: Why can wrapping an entire method (that includes a slow external API call) in `@Transactional` cause production issues under load?**
A: The database connection acquired when the transaction starts stays open for the full duration of the method, including the slow external call. Under peak traffic, many concurrent requests holding connections open while waiting on a slow third-party API can exhaust the connection pool. Programmatic transaction management lets you scope the transaction only around the actual DB operations, excluding the external call.

**Q4: If `methodOne()` (propagation `REQUIRED`) calls `methodTwo()` (propagation `REQUIRED`), how many transactions are created, and how do you verify it at runtime?**
A: Just one. `methodTwo()` joins `methodOne()`'s existing transaction instead of creating a new one. You can verify this with `TransactionSynchronizationManager.isActualTransactionActive()` (true in both methods) and `TransactionSynchronizationManager.getCurrentTransactionName()` (same name in both methods).

**Q5: What's the difference between `REQUIRES_NEW` and `NOT_SUPPORTED` when a parent transaction exists?**
A: Both suspend the parent transaction. `REQUIRES_NEW` then creates and runs a brand-new independent transaction for the current method, committing/rolling it back on its own before the parent resumes. `NOT_SUPPORTED` does not create any transaction at all for the current method — it just runs the code without one, then resumes the parent afterward.

**Q6: What happens if a method with propagation `MANDATORY` is called with no active parent transaction, versus a method with propagation `NEVER` called from within an active parent transaction?**
A: Both throw an exception. `MANDATORY` requires a parent transaction to already exist and throws if there isn't one. `NEVER` requires that no parent transaction exists and throws if one is found — they enforce opposite invariants.
