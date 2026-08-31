# Data Isolation Strategies

## The Three Approaches (SAP BTP Pattern Applied to PostgreSQL + Spring)

SAP BTP documents three data separation strategies for multitenancy. Here's how each maps to AWS RDS (PostgreSQL) with Spring Boot/Hibernate.

---

## Strategy Comparison Matrix

| Criteria | Discriminator Column | Schema per Tenant | DB Instance per Tenant |
|----------|---------------------|-------------------|----------------------|
| **Isolation** | Low | High | Highest |
| **Cost** | Lowest | Low-Medium | Highest |
| **Complexity** | Low | Medium | High |
| **Tenant count** | Unlimited | 100s–1000s | 10s–100s |
| **Compliance** | Risky | Usually sufficient | Required (HIPAA/PCI) |
| **Backup granularity** | Full DB only | Per-schema dump | Per-instance |
| **Migration effort** | Single migration | Per-tenant migration | Per-instance migration |
| **SAP BTP equivalent** | Discriminator column | HDI Container (recommended) | HANA Instance separation |
| **Recommended for** | Internal tools, prototypes | Most SaaS products | Finance, Healthcare |

**Default recommendation: Schema per Tenant** — same as SAP's recommendation for HDI Containers.

---

## Strategy 1: Discriminator Column (Row-Level Isolation)

### How It Works

All tenants share the same tables. Every table has a `tenant_id` column.

```sql
CREATE TABLE orders (
    id          BIGSERIAL PRIMARY KEY,
    tenant_id   VARCHAR(100) NOT NULL,   -- ← discriminator
    order_no    VARCHAR(50),
    total       DECIMAL(10,2),
    created_at  TIMESTAMP
);

CREATE INDEX idx_orders_tenant ON orders(tenant_id);
```

### Hibernate @Filter Approach

```java
@Entity
@Table(name = "orders")
@FilterDef(
    name = "tenantFilter",
    parameters = @ParamDef(name = "tenantId", type = String.class)
)
@Filter(name = "tenantFilter", condition = "tenant_id = :tenantId")
public class Order {

    @Id @GeneratedValue
    private Long id;

    @Column(name = "tenant_id", nullable = false, updatable = false)
    private String tenantId;

    private String orderNo;
    private BigDecimal total;
}
```

Enable the filter in a Spring interceptor:

```java
@Component
public class HibernateTenantFilterAspect {

    @PersistenceContext
    private EntityManager entityManager;

    @Before("execution(* com.saas.repository.*.*(..))")
    public void enableTenantFilter() {
        Session session = entityManager.unwrap(Session.class);
        session.enableFilter("tenantFilter")
            .setParameter("tenantId", TenantContextHolder.getTenantId());
    }
}
```

### PostgreSQL Row-Level Security (More Robust)

```sql
-- Enable RLS on orders table
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;

-- Policy: app_user can only see rows matching their tenant
CREATE POLICY tenant_isolation ON orders
    FOR ALL
    TO app_user
    USING (tenant_id = current_setting('app.current_tenant'));

-- Spring sets this at the start of each request/transaction
```

```java
@Component
public class RlsTenantAspect {

    @PersistenceContext
    private EntityManager em;

    @Before("@within(org.springframework.stereotype.Repository)")
    public void setTenantContext() {
        em.createNativeQuery(
            "SET LOCAL app.current_tenant = '" +
            TenantContextHolder.getTenantId() + "'")
          .executeUpdate();
    }
}
```

**Risk:** If developer forgets the WHERE clause or filter is disabled, cross-tenant data leak occurs. RLS is safer (enforced at DB level).

---

## Strategy 2: Schema per Tenant (Recommended)

### How It Works

Each tenant gets their own schema in the shared RDS instance.

```
RDS PostgreSQL Instance
├── schema: platform        (shared — tenants table, billing)
├── schema: tenant_acmecorp (Acme Corp's tables)
├── schema: tenant_globex   (Globex's tables)
└── schema: tenant_initech  (Initech's tables)

Each tenant schema contains:
  orders, products, customers, invoices, ...
  (identical DDL, separate data)
```

### Dynamic DataSource Routing — Spring AbstractRoutingDataSource

```java
@Component
public class TenantRoutingDataSource extends AbstractRoutingDataSource {

    @Override
    protected Object determineCurrentLookupKey() {
        // Returns the schema name from thread-local
        // AbstractRoutingDataSource uses this to pick the right DataSource
        return TenantContextHolder.getSchemaName();
    }
}
```

### PostgreSQL Schema Switching (Preferred over multiple DataSources)

Rather than separate JDBC connections per tenant, set `search_path` on the connection:

```java
@Configuration
public class DataSourceConfig {

    @Bean
    @Primary
    public DataSource dataSource(DataSourceProperties props) {
        // Single connection pool, but we switch schema per request
        HikariDataSource ds = props.initializeDataSourceBuilder()
            .type(HikariDataSource.class)
            .build();
        ds.setMaximumPoolSize(50);
        return ds;
    }

    @Bean
    public JdbcTemplate jdbcTemplate(DataSource dataSource) {
        return new JdbcTemplate(dataSource);
    }
}
```

```java
@Component
public class SchemaRoutingInterceptor implements HandlerInterceptor {

    private final JdbcTemplate jdbcTemplate;

    @Override
    public boolean preHandle(HttpServletRequest request,
                             HttpServletResponse response, Object handler) {
        String schemaName = TenantContextHolder.getSchemaName();
        if (schemaName != null) {
            // Set search_path for this connection/transaction
            jdbcTemplate.execute("SET search_path TO " + schemaName + ", public");
        }
        return true;
    }

    @Override
    public void afterCompletion(HttpServletRequest request,
                                HttpServletResponse response, Object handler,
                                Exception ex) {
        // Reset search_path (important with connection pools)
        jdbcTemplate.execute("SET search_path TO public");
        TenantContextHolder.clear();
    }
}
```

### Flyway Migrations Per Schema

```java
@Service
public class TenantMigrationService {

    private final DataSource dataSource;

    public void migrateSchema(String schemaName) {
        Flyway.configure()
            .dataSource(dataSource)
            .schemas(schemaName)
            .locations("classpath:db/migration/tenant")
            .baselineOnMigrate(true)
            .load()
            .migrate();
    }

    // Call this when deploying a new version to migrate ALL tenants
    public void migrateAllTenants() {
        tenantRepository.findAllActive().forEach(tenant ->
            migrateSchema(tenant.getSchemaName()));
    }
}
```

```
src/main/resources/
└── db/migration/
    ├── platform/           ← shared schema migrations
    │   └── V1__create_tenants.sql
    └── tenant/             ← tenant schema migrations (run per tenant)
        ├── V1__initial_schema.sql
        ├── V2__add_indexes.sql
        └── V3__add_audit_columns.sql
```

### Entity Configuration for Schema Isolation

Entities do NOT need `@Table(schema=...)` — the `search_path` handles routing:

```java
@Entity
@Table(name = "orders")  // no schema — resolved via search_path
public class Order {
    @Id @GeneratedValue
    private Long id;

    // No tenant_id column needed — schemas are already isolated
    private String orderNo;
    private BigDecimal total;
}
```

---

## Strategy 3: Database Instance per Tenant (Premium Tier)

### When to Use

- Tenant contract requires complete data isolation (HIPAA, PCI-DSS, FINRA)
- Tenant requires custom backup schedules or point-in-time recovery
- Tenant has very high throughput that would cause noisy-neighbor issues

### Implementation

```java
@Service
public class DedicatedRdsProvisioner {

    private final RdsClient rdsClient;
    private final SecretsManagerClient secretsManager;

    public TenantDbInfo provisionDedicatedDb(String tenantId) {
        // Create RDS instance for this tenant
        String instanceId = "saas-tenant-" + tenantId;

        rdsClient.createDBInstance(CreateDbInstanceRequest.builder()
            .dbInstanceIdentifier(instanceId)
            .dbInstanceClass("db.t3.medium")
            .engine("postgres")
            .engineVersion("15.3")
            .masterUsername("admin")
            .masterUserPassword(generateSecurePassword())
            .dbName("tenant_db")
            .multiAZ(true)
            .storageEncrypted(true)
            .tags(Tag.builder().key("tenantId").value(tenantId).build())
            .build());

        // Store connection details in Secrets Manager
        String secretArn = secretsManager.createSecret(CreateSecretRequest.builder()
            .name("saas/tenant/" + tenantId + "/db")
            .secretString(buildDbSecretJson(instanceId, tenantId))
            .build()).arn();

        return TenantDbInfo.builder()
            .instanceId(instanceId)
            .secretArn(secretArn)
            .build();
    }
}
```

Dynamic DataSource creation per tenant:

```java
@Component
public class DynamicDataSourceManager {

    private final Map<String, DataSource> dataSources = new ConcurrentHashMap<>();
    private final SecretsManagerClient secretsManager;

    public DataSource getDataSource(String tenantId) {
        return dataSources.computeIfAbsent(tenantId, this::createDataSource);
    }

    private DataSource createDataSource(String tenantId) {
        DbSecret secret = fetchSecret("saas/tenant/" + tenantId + "/db");

        HikariConfig config = new HikariConfig();
        config.setJdbcUrl(secret.getJdbcUrl());
        config.setUsername(secret.getUsername());
        config.setPassword(secret.getPassword());
        config.setMaximumPoolSize(10);  // smaller pool per tenant
        config.setConnectionTimeout(5000);

        return new HikariDataSource(config);
    }
}
```

---

## Recommended Strategy for Each SaaS Tier

```
FREE tier tenants     → Discriminator column (cheapest, shared everything)
PRO tier tenants      → Schema per tenant (good isolation, manageable cost)
ENTERPRISE tenants    → DB instance per tenant (full isolation)
```

This tiered approach lets a single platform support all customer segments efficiently.

---

## RDS Proxy — Connection Pooling Across Tenants

With schema-per-tenant, many tenants sharing one RDS instance can exhaust connections. **RDS Proxy** solves this:

```
Multiple ECS tasks × Multiple tenants × HikariCP pools
    = Potentially thousands of DB connections

Solution: RDS Proxy
    - Pools and multiplexes connections at the proxy layer
    - ECS tasks connect to proxy endpoint (not RDS directly)
    - Proxy maintains efficient connection pool to actual RDS
    - Supports IAM authentication (no password rotation needed)
```

```yaml
spring:
  datasource:
    url: jdbc:postgresql://saas-proxy.proxy-xyz.us-east-1.rds.amazonaws.com:5432/saasdb
    # IAM auth token instead of password:
    hikari:
      connection-init-sql: "SET search_path TO public"
```
