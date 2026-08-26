# Local Development Setup

## The Goal

Every engineer on the team should be able to run **two isolated tenants locally** within 5 minutes
of cloning the repo — with full schema isolation, working auth, and AWS service mocking.

---

## 1. Docker Compose — Full Local Stack

```yaml
# docker-compose.yml

version: '3.9'

services:

  # PostgreSQL with multiple schemas (simulates RDS)
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: saasdb
      POSTGRES_USER: saas_user
      POSTGRES_PASSWORD: saas_pass
    ports:
      - "5432:5432"
    volumes:
      - ./scripts/init-db.sql:/docker-entrypoint-initdb.d/01_init.sql
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "saas_user"]
      interval: 5s
      retries: 10

  # Redis (simulates ElastiCache)
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  # LocalStack — AWS service mocks
  localstack:
    image: localstack/localstack:3.0
    ports:
      - "4566:4566"
    environment:
      SERVICES: s3,sqs,sns,events,secretsmanager,cognito-idp
      DEBUG: 0
      DATA_DIR: /tmp/localstack/data
    volumes:
      - ./scripts/localstack-init.sh:/etc/localstack/init/ready.d/init.sh
      - localstack_data:/tmp/localstack

  # Keycloak — local Cognito replacement
  keycloak:
    image: quay.io/keycloak/keycloak:23.0
    command: start-dev --import-realm
    environment:
      KEYCLOAK_ADMIN: admin
      KEYCLOAK_ADMIN_PASSWORD: admin
    ports:
      - "8180:8080"
    volumes:
      - ./scripts/keycloak-realm.json:/opt/keycloak/data/import/realm.json

  # Spring Cloud Gateway
  gateway:
    build:
      context: ./gateway-service
    ports:
      - "8080:8080"
    environment:
      SPRING_PROFILES_ACTIVE: local
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started

  # Core API
  core-api:
    build:
      context: ./core-api-service
    ports:
      - "8081:8081"
    environment:
      SPRING_PROFILES_ACTIVE: local
      DB_URL: jdbc:postgresql://postgres:5432/saasdb
      DB_USERNAME: saas_user
      DB_PASSWORD: saas_pass
      REDIS_HOST: redis
    depends_on:
      postgres:
        condition: service_healthy

volumes:
  postgres_data:
  localstack_data:
```

---

## 2. Database Init Script — Two Test Tenants

```sql
-- scripts/init-db.sql

-- Platform schema (shared metadata)
CREATE SCHEMA IF NOT EXISTS platform;

CREATE TABLE platform.tenants (
    tenant_id   VARCHAR(100) PRIMARY KEY,
    display_name VARCHAR(200),
    schema_name  VARCHAR(100),
    status       VARCHAR(50) DEFAULT 'ACTIVE',
    plan         VARCHAR(20) DEFAULT 'PRO'
);

-- Create two test tenant schemas
CREATE SCHEMA IF NOT EXISTS tenant_acmecorp;
CREATE SCHEMA IF NOT EXISTS tenant_globex;

-- Register both tenants in platform
INSERT INTO platform.tenants VALUES
    ('acmecorp', 'Acme Corporation', 'tenant_acmecorp', 'ACTIVE', 'PRO'),
    ('globex', 'Globex Corporation', 'tenant_globex', 'ACTIVE', 'ENTERPRISE')
ON CONFLICT DO NOTHING;

-- Grant app user access to all schemas
GRANT USAGE ON SCHEMA platform, tenant_acmecorp, tenant_globex TO saas_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA tenant_acmecorp
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO saas_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA tenant_globex
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO saas_user;
```

---

## 3. LocalStack Init Script — AWS Service Mocking

```bash
#!/bin/bash
# scripts/localstack-init.sh — runs on LocalStack startup

awslocal s3 mb s3://saas-platform-files

awslocal sqs create-queue --queue-name billing-queue
awslocal sqs create-queue --queue-name audit-queue

awslocal events create-event-bus --name saas-platform

awslocal secretsmanager create-secret \
  --name saas/db \
  --secret-string '{"username":"saas_user","password":"saas_pass"}'

awslocal cognito-idp create-user-pool \
  --pool-name saas-local-pool \
  --schema Name=tenantId,AttributeDataType=String,Mutable=false \
            Name=role,AttributeDataType=String,Mutable=true

echo "LocalStack initialized."
```

---

## 4. Spring Boot Local Profile

```yaml
# src/main/resources/application-local.yml

spring:
  datasource:
    url: jdbc:postgresql://localhost:5432/saasdb
    username: saas_user
    password: saas_pass

  security:
    oauth2:
      resourceserver:
        jwt:
          # Keycloak local JWKS — replaces Cognito JWKS
          jwk-set-uri: http://localhost:8180/realms/saas-local/protocol/openid-connect/certs

aws:
  endpoint: http://localhost:4566    # LocalStack endpoint
  region: us-east-1
  access-key: test                   # LocalStack accepts any credentials
  secret-key: test

app:
  tenant-host-pattern: "^([a-z0-9-]+)\\.localhost$"  # acmecorp.localhost:8080
  cognito:
    user-pool-id: local-pool
  s3:
    bucket: saas-platform-files
```

---

## 5. Simulating Two Tenants Locally — /etc/hosts

```
# /etc/hosts — add these entries for local subdomain routing

127.0.0.1  acmecorp.localhost
127.0.0.1  globex.localhost
127.0.0.1  admin.localhost
```

Then:
- `http://acmecorp.localhost:8080/api/orders` → tenant: acmecorp
- `http://globex.localhost:8080/api/orders` → tenant: globex

---

## 6. Keycloak Local Realm — Cognito Replacement

```json
// scripts/keycloak-realm.json
{
  "realm": "saas-local",
  "enabled": true,
  "clients": [{
    "clientId": "saas-web",
    "publicClient": true,
    "redirectUris": ["http://acmecorp.localhost:3000/callback",
                     "http://globex.localhost:3000/callback"]
  }],
  "users": [
    {
      "username": "alice@acmecorp.com",
      "email": "alice@acmecorp.com",
      "enabled": true,
      "credentials": [{"type": "password", "value": "password"}],
      "attributes": {
        "tenantId": ["acmecorp"],
        "role": ["ADMIN"]
      },
      "realmRoles": ["acmecorp-admin"]
    },
    {
      "username": "bob@globex.com",
      "email": "bob@globex.com",
      "enabled": true,
      "credentials": [{"type": "password", "value": "password"}],
      "attributes": {
        "tenantId": ["globex"],
        "role": ["USER"]
      },
      "realmRoles": ["globex-user"]
    }
  ]
}
```

---

## 7. Integration Test Base Class

```java
@SpringBootTest(webEnvironment = RANDOM_PORT)
@ActiveProfiles("test")
@Testcontainers
public abstract class MultitenantIntegrationTest {

    @Container
    static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:15")
        .withInitScript("test-init.sql");

    @Container
    static GenericContainer<?> redis = new GenericContainer<>("redis:7-alpine")
        .withExposedPorts(6379);

    @DynamicPropertySource
    static void configureProperties(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", postgres::getJdbcUrl);
        registry.add("spring.datasource.username", postgres::getUsername);
        registry.add("spring.datasource.password", postgres::getPassword);
        registry.add("spring.redis.host", redis::getHost);
        registry.add("spring.redis.port",
            () -> redis.getMappedPort(6379).toString());
    }

    // Helper: run a block of code as a specific tenant
    protected void withTenant(String tenantId, Runnable action) {
        TenantContextHolder.set(TenantContext.of(tenantId));
        try {
            action.run();
        } finally {
            TenantContextHolder.clear();
        }
    }

    // Helper: make a request as a tenant
    protected WebTestClient clientForTenant(String tenantId) {
        return WebTestClient.bindToServer()
            .baseUrl("http://localhost:" + port)
            .defaultHeader("X-Tenant-ID", tenantId)
            .defaultHeader("Authorization", "Bearer " + getTestToken(tenantId))
            .build();
    }
}
```

---

## 8. Quick Start Command

```bash
# Clone, configure, run in under 5 minutes:

git clone https://github.com/yourorg/saas-platform
cd saas-platform

# Start all dependencies
docker compose up -d postgres redis localstack keycloak

# Wait for healthy (or use: docker compose wait)
sleep 15

# Run Flyway migrations for both test tenants
./mvnw flyway:migrate -Dflyway.schemas=platform,tenant_acmecorp,tenant_globex

# Start the app
./mvnw spring-boot:run -Dspring-boot.run.profiles=local

# Test tenant isolation:
curl -H "X-Tenant-ID: acmecorp" http://acmecorp.localhost:8080/api/orders
curl -H "X-Tenant-ID: globex"   http://globex.localhost:8080/api/orders

# Run isolation tests:
./mvnw test -pl core-api-service -Dtest=TenantIsolationTest
```

---

## 9. Makefile Shortcuts

```makefile
# Makefile

.PHONY: dev test clean

dev:
	docker compose up -d
	./mvnw spring-boot:run -Dspring-boot.run.profiles=local

test:
	./mvnw test -Dspring.profiles.active=test

test-isolation:
	./mvnw test -Dtest=TenantIsolationTest,CrossTenantSecurityTest

migrate-local:
	./mvnw flyway:migrate -Dflyway.schemas=tenant_acmecorp,tenant_globex

clean:
	docker compose down -v
	./mvnw clean
```
