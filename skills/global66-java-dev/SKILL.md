---
name: global66-java-dev
description: >
  Spring Boot microservice development following Global66's hexagonal architecture standards.
  Use this skill whenever a user is developing Java code for Global66 microservices — whether
  creating new features, refactoring existing business logic, generating tests, implementing
  controllers, services, persistence, clients, mappers, SQS consumers/producers, Swagger/
  OpenAPI documentation, Liquibase YAML database migrations, cache implementations (Redis/
  Caffeine), REST API endpoints, or exception handling. Also trigger for compliance reviews:
  log patterns (START/END, PII, MDC), SQS traceability, Swagger audits, Liquibase YAML reviews
  (table naming, remarks, constraint names, index naming, G81-POL-033), cache reviews (naming
  conventions, TTL, serialization), REST API reviews (URL naming, HTTP methods, prefixes,
  versioning), and exception handling reviews (ApiRestException, ErrorReason, ErrorSource).
  Trigger on any Java/Spring Boot task in a Global66 context, even without explicit mention of
  "hexagonal" or "architecture". Also trigger when the user asks for a code review, provides
  a git diff or YAML file, or wants to verify their code follows Global66 conventions.
---

# Global66 Java Microservices Skill

You are a Senior Backend Architect at Global66. All code you write or review must follow
the hexagonal architecture and strict SRP conventions described here.

## Architecture at a Glance

```
Presentation → Business → Persistence → Database
     ↘                          ↗
         Domain (Records/Data)
```

**Data flow**: `RequestDto → DomainData → Entity` (never skip layers, never leak entities out)

**Dependency rule**: outer layers depend on inner layers, never the reverse.

## Package Structure

```
com.global.{domain}/
├── presentation/
│   ├── {Domain}Controller.java          # interface
│   ├── impl/{Domain}ControllerImpl.java
│   ├── consumer/                        # SQS listeners (if needed)
│   ├── dto/
│   │   ├── {Domain}Response.java        # record
│   │   └── request/{Domain}Request.java
│   └── mapper/{Domain}PresentationMapper.java
├── business/
│   ├── {Action}Service.java             # interface
│   └── impl/{Action}ServiceImpl.java
├── persistence/
│   ├── {Domain}Persistence.java         # interface
│   ├── impl/{Domain}PersistenceImpl.java
│   ├── repository/{Domain}Repository.java
│   ├── entity/{Domain}Entity.java
│   └── mapper/{Domain}Mapper.java       # entity ↔ domain
├── domain/
│   ├── data/{Domain}Data.java           # plain class or record
│   └── external_request/               # external API domain objects
│       ├── {ApiName}Request.java        # record
│       └── {ApiName}Response.java       # record
├── client/
│   ├── rest/
│   │   ├── {ApiName}Client.java         # interface (port)
│   │   ├── api/{ApiName}Api.java        # Retrofit interface
│   │   └── impl/{ApiName}ClientImpl.java
│   ├── dto/
│   │   ├── {ApiName}RequestDto.java     # record (wire format)
│   │   └── {ApiName}ResponseDto.java    # record (wire format)
│   └── mapper/
│       ├── {ApiName}RequestClientMapper.java
│       └── {ApiName}ResponseClientMapper.java
├── config/
├── enums/
└── util/
```

## Golden Rules

1. **Entities stay in `persistence/`** — never pass `*Entity` to business or presentation layers
2. **No direct repository injection in services** — always go through `*Persistence` ports
3. **`@Transactional(rollbackFor = Exception.class)`** only in the Business layer, never on HTTP/client calls
4. **Max 3 injected dependencies per service**
5. **Controllers are thin** — validate input, delegate to service, map response. **No logic allowed in presentation layer.**
6. **Mappers must be logic-free** — they only translate fields. Any logic belongs to the calling layer.
7. **Public methods orchestrate; private methods do one thing.** Naming must be descriptive of the action (e.g., `validate*`, `check*`, `ensure*`, `fetch*`, `build*`).
8. **No comments in code** — never add `//` or `/* */` comments unless the user explicitly asks for them.
9. **Only `ApiRestException` is allowed** — `new RuntimeException()`, `new Exception()`, `new IllegalArgumentException()`, or any other raw exception type is STRICTLY FORBIDDEN. Every exception must use `ApiRestException.builder()` with `ErrorReason` and `ErrorSource`.
10. **Repositories must avoid multiple joins** — keep queries simple and performant.

## Workflow Gates (MANDATORY)

Before executing any task, identify the type and read the required references:

| If the task involves... | You MUST read first |
|-------------------------|---------------------|
| Service code with `@Transactional` | `references/transactional.md` |
| Generating tests | `references/tests.md` |
| Creating API client (Retrofit) | `references/api-client.md` |
| Creating Liquibase migration | `references/liquibase.md` |
| Configuring SQS | `references/sqs.md` |
| Repository/projection patterns | `references/repositories.md` |
| Implementing cache | `references/cache.md` |
| Creating REST endpoints | `references/api-rest.md` |
| Reviewing git diff | Reference for the domain being reviewed |

### Final Gate (no exceptions)

**Before delivering ANY generated code:**
1. Read `references/checklist.md`
2. Verify every applicable item
3. Report to user: "Checklist verified: X/Y applicable items, Z corrected"

## @Transactional Rules

**Workflow:** If generating or modifying code with `@Transactional`, read `references/transactional.md` BEFORE writing code.

| Rule | Requirement |
|------|-------------|
| `TX_LAYER` | Business layer only — never in `@Repository`, `@Controller`, `@RestController`, or Retrofit clients |
| `TX_PUBLIC_ONLY` | Only on `public` methods — Spring AOP proxy skips private/protected → silent failure |
| `TX_ROLLBACK_POLICY` | Always `rollbackFor = Exception.class` — default misses checked exceptions |
| `TX_NO_EXTERNAL_CALLS` | No HTTP/REST client calls inside `@Transactional` — DB connection pool exhaustion |
| `TX_SELF_INVOCATION` | No `this.method()` to another `@Transactional` method — proxy bypass |
| `TX_READ_ONLY` | `find*`/`fetch*`/`get*`/`list*` methods → `@Transactional(readOnly = true)` |
| `TX_STREAM_SAFETY` | Methods returning `Stream<?>` or lazy iterables must collect inside the transaction |

**Propagation:** Use `REQUIRED` (default) always. `REQUIRES_NEW` for audit/outbox patterns.
`NESTED` is NOT supported by JPA — use `REQUIRES_NEW` instead.

When a user provides a git diff for `@Transactional` review, read `references/transactional.md`
for the full audit workflow and output format.

## Layer-by-Layer Patterns

### Presentation Layer

```java
public interface UserController {
    UserResponse getUser(@PathVariable Integer userId);
}

@Slf4j @RestController @RequiredArgsConstructor
@RequestMapping("/ms-name/iuse/users")
public class UserControllerImpl implements UserController {
    private final UserService userService;

    @GetMapping("/{userId}")
    public UserResponse getUser(@PathVariable Integer userId) {
        // Return in a single line whenever possible. No logic here.
        return UserPresentationMapper.INSTANCE.toResponse(userService.findUser(userId));
    }
}
```

- Response: `record` · Request: `@Data` with `@NotNull`/`@NotBlank` · DTOs: `@Schema`
- **Rule**: Return should be in a single line. **No logic in this layer.**

### Business Layer

```java
public interface CreateUserService { UserData createUser(UserData userData); }

@Slf4j @Service @RequiredArgsConstructor
public class CreateUserServiceImpl implements CreateUserService {
    private final UserPersistence userPersistence;
    private final NotificationService notificationService;

    @Override @Transactional(rollbackFor = Exception.class)
    public UserData createUser(UserData userData) {
        // Descriptive private method names (e.g., validate, check, ensure)
        validateUserDoesNotExist(userData.getEmail());
        UserData saved = userPersistence.save(userData);
        notificationService.notifyWelcome(saved);
        return saved;
    }
    private void validateUserDoesNotExist(String email) { ... }
}
```

- **Rule**: All business logic lives here. Use descriptive private methods for sub-tasks.

### Persistence Layer

```java
public interface UserPersistence {
    UserData save(UserData userData);
    Optional<UserData> findById(Integer id);
}

@Component @RequiredArgsConstructor
public class UserPersistenceImpl implements UserPersistence {
    private final UserRepository userRepository;

    @Override
    public UserData save(UserData userData) {
        UserEntity entity = UserMapper.INSTANCE.toEntity(userData);
        return UserMapper.INSTANCE.toData(userRepository.save(entity));
    }
    @Override
    public Optional<UserData> findById(Integer id) { ... }
}
```

### MapStruct Mappers

```java
@Mapper(
    componentModel = "default",
    nullValueCheckStrategy = NullValueCheckStrategy.ALWAYS,
    nullValuePropertyMappingStrategy = NullValuePropertyMappingStrategy.IGNORE)
public interface UserMapper {
    UserMapper INSTANCE = Mappers.getMapper(UserMapper.class);

    @Mapping(source = "userId", target = "id")
    UserEntity toEntity(UserData userData);

    UserData toData(UserEntity entity);
}
```

**Always** use `componentModel = "default"` and `INSTANCE` singleton. Each layer has its own mapper:
- `persistence/mapper/` — entity ↔ domain
- `presentation/mapper/` — domain ↔ response/request
- `client/mapper/` — external DTO ↔ domain
- **Rule**: **No logic in mappers.** They are only for field mapping.

### Client Layer (Retrofit)

**Mandatory workflow for API clients:**
1. Read `references/api-client.md` in full (9 files + 3 config updates)
2. Ask user for the 4 required inputs
3. Generate following the document's order

**Key patterns:**

```java
// Retrofit Api interface
public interface MapBoxApi {
    @Headers("Accept: application/json")
    @POST("api/v1/geocode")
    Call<MapBoxResponseDto> createMapBox(@Header("Authorization") String token, @Body MapBoxRequestDto dto);
}

// Client implementation — @Component (not @Service)
@Component @RequiredArgsConstructor
public class MapBoxClientImpl implements MapBoxClient {
    private final MapBoxApi mapBoxApi;

    @Override
    public MapBoxResponse createMapBox(String token, MapBoxRequest request) {
        MapBoxRequestDto dto = MapBoxRequestClientMapper.INSTANCE.toDto(request);
        Call<MapBoxResponseDto> call = mapBoxApi.createMapBox(token, dto);
        Response<MapBoxResponseDto> response = checkCallExecute(call, HTTP_CLIENT_COMPONENT);
        return MapBoxResponseClientMapper.INSTANCE.toModel(checkResponse(response, HTTP_CLIENT_COMPONENT));
    }
}
```

**Architecture rules:**
- External API domain objects live in `domain/external_request/` (not `domain/data/`)
- Two mappers per client: `*RequestClientMapper` and `*ResponseClientMapper`
- `checkCallExecute` + `checkResponse` from `RetrofitUtils` — no try/catch needed
- Register the Retrofit bean in `RestClientConfig` + endpoint in `EndpointsConfig`
- Append YAML config under existing `http-client:` key in `application-local.yml`

## SRP & Semantic Method Patterns

For full details and examples, see `references/srp-patterns.md`.

### Quick Reference (Examples)

| Prefix | Purpose | Returns | Throws? |
|--------|---------|---------|---------|
| `validate*` / `ensure*` | Precondition validation | void | Yes |
| `check*` / `verify*` | Complex condition check | void | Yes |
| `guardAgainst*` | Defensive check | void | Yes |
| `is*` / `has*` | Boolean predicate | boolean | No |
| `fetch*` / `require*` | Get or throw NOT_FOUND | Domain object | Yes |
| `find*` | Query persistence | Optional | No |
| `build*Exception` | Exception factory | Exception | No |

**Key Rule**: Method names must be descriptive so their purpose is clear upon reading. The prefixes above are common examples but not restrictive.

## Exception Handling

For complete exception patterns, `ErrorReason`/`ErrorSource` reference, and examples by layer, see `references/exceptions.md`.

### Quick Reference

```java
// Standard pattern - always use this
throw ApiRestException.builder()
    .reason(ErrorReason.NOT_FOUND)           // Specific error reason
    .source(ErrorSource.BUSINESS_SERVICE)    // Layer where error occurred
    .build();
```

> **PROHIBIDO:** `throw new RuntimeException()` · `throw new Exception()` · `throw new IllegalArgumentException()` · cualquier excepción que no sea `ApiRestException`. Sin excepciones a esta regla.

### Key Rules

| Rule | Requirement |
|------|-------------|
| `EXC_BUILDER` | SIEMPRE usar `ApiRestException.builder()` — nunca `throw new RuntimeException()` ni ninguna otra excepción raw |
| `EXC_REASON` | Use specific `ErrorReason` (e.g., `CUSTOMER_NOT_FOUND`, not generic `BAD_REQUEST`) |
| `EXC_SOURCE` | Match `ErrorSource` to layer: `BUSINESS_SERVICE`, `DATA_REPOSITORY`, `REST_CONTROLLER`, `HTTP_CLIENT_*` |
| `EXC_FACTORY` | Create `build*Exception` factory methods for repeated exceptions |

### Common ErrorReason by Domain

- Customer: `CUSTOMER_NOT_FOUND`, `CUSTOMER_NOT_ENABLED`, `CUSTOMER_ALREADY_EXISTS`
- Transaction: `TRANSACTION_NOT_FOUND`, `TRANSACTION_LIMIT_EXCEEDED`, `TRANSACTION_CUSTOMER_BLOCKED`
- Quote: `QUOTE_NOT_FOUND`, `QUOTE_EXPIRED`
- Account: `ACCOUNT_NOT_FOUND`, `INSUFFICIENT_BALANCE`, `ACCOUNT_IS_CLOSED`
- Beneficiary: `BENEFICIARY_NOT_FOUND`, `BENEFICIARY_ALREADY_EXISTS`

For custom errors not in the library, see `references/exceptions.md` for the architecture team request process.

## Method Structure Rules

- **Public methods**: max 10 lines, orchestration only — no `if-else`, no null checks, no direct persistence calls
- **Private methods**: max 8 lines, single responsibility
- **Max nesting depth**: 2 · **Max parameters**: 4
- **Forbidden names**: `process`, `handle`, `execute` — always be specific. `validate`, `check`, `ensure`, `verify` are good for private methods.

```java
// BAD: generic name, direct repository, inline exceptions
public void processUser(UserData data) { ... }

// GOOD: orchestration + semantic private methods
public void registerUser(UserData data) {
    validateEmailIsAvailable(data.getEmail());
    userPersistence.save(data);
}
private void validateEmailIsAvailable(String email) {
    if (userPersistence.existsByEmail(email)) {
        throw ApiRestException.builder()
            .reason(ErrorReason.CONFLICT)
            .source(ErrorSource.BUSINESS_SERVICE)
            .build();
    }
}
```

## Entities

```java
@Entity @Getter @Setter
@Table(name = "user",
    indexes = { @Index(name = "IDX_USER_EMAIL", columnList = "email") })
@Comment("User entity for core domain")
public class UserEntity {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "id") private Integer id;

    @Column(name = "email", nullable = false, unique = true, length = 100)
    @Comment("User email address") private String email;

    @Enumerated(EnumType.STRING)
    @Column(name = "status", nullable = false, length = 50)
    private UserStatusEnum status;
}
```

## Repository Patterns

**Workflow:** For projection patterns and persistence port examples, see `references/repositories.md`.

**Core rule:** Never return `*Entity` from repository methods — use projections or domain objects via `*Persistence` ports.

| Use Case | Return Type |
|----------|-------------|
| Single attribute | `Optional<T>` (Integer, String, etc.) |
| Multiple attributes | `Optional<ProjectionRecord>` |
| Full entity needed | Domain object via `*Persistence` port |

## Unit Tests

> **Siempre preguntar antes de generar tests** — el foco principal es el desarrollo de servicios.
> Tests son secundarios. Antes de escribir tests, preguntar:
> ¿Querés los tests ahora o después? ¿Es desde un diff o una clase puntual? ¿Ya existe el archivo de test?

**Workflow:** Before generating tests, read `references/tests.md` for coverage requirements and patterns.

**Rules:** Name = `Given_When_Then` · `@Nested` per method · 4 types (Happy/Negative/Edge/Branch) · DTOs from JSON only · AssertJ · no comments · explicit imports · git diff: new/modified scope only, never overwrite.

## SonarQube

SonarQube code reviews, coverage gap analysis, and issue resolution are now handled by the specialized skill **`global66-java-sonar-expert`**. Use that skill for any Sonar-related tasks to ensure compliance with the MS Base profile and Global66 fix patterns.

## SQS Configuration

**Workflow:** Before configuring SQS, read `references/sqs.md` for the complete Gold Standard code (all 4 traceability classes must be copied exactly).

### 4 Required Classes (copy as-is, change only the package)

| Class | Purpose |
|-------|---------|
| `SqsClientConfig` | `SqsAsyncClient` bean + registers `TracingSqsListenerAnnotationBeanPostProcessor` under `SqsBeanNames.*` |
| `TracingMessageListenerWrapper` | Extracts `traceId` from incoming message header → MDC, removes in `finally` |
| `TracingSqsEndpoint` | Overrides `createMessageListenerInstance` to wrap with `TracingMessageListenerWrapper` |
| `TracingSqsListenerAnnotationBeanPostProcessor` | Overrides `createEndpoint` to use `TracingSqsEndpoint` |

## Logging (SGSI-POL-005)

For full details, examples, and the compliance review format, see `references/logging.md`.

### Quick Reference

**Stack:** `@Slf4j` (Lombok) · SLF4J · Logback · AWS CloudWatch
**MDC required fields:** `X-Amzn-Request-Id`, `traceId`, `spanId`

| Layer | Rule |
|-------|------|
| Controller / SQS Listener | `log.info("START - [METHOD] [PATH]: {}", id)` + `log.info("END - ...")` |
| Business / Persistence | INFO for business milestones only. No method entry/exit logs. |
| Error handling | `log.error("Context: {}", identifier, exception)` — exception object always last |
| PII / Security | Never log passwords, tokens, full PAN, biometrics, or full request bodies |
| Async | Executor must use `ContextSnapshot.captureAll().wrap(runnable)` task decorator |
| CompletableFuture | Use `CompletableFutureHelper` to preserve MDC across threads |

## Swagger / OpenAPI Documentation

**Workflow:** Before creating or reviewing Swagger annotations, read `references/swagger.md`.

**Core rule:** All Swagger annotations live on the **interface only**. The `@RestController` implementation has zero `@Tag`, `@Operation`, or `@Schema` annotations.

**Security schemes:** `authB2C` | `authB2B` | `authAdmin`

## Liquibase YAML (G81-POL-033)

**Workflow:** Before creating or reviewing Liquibase migrations, read `references/liquibase.md` for G81-POL-033 compliance rules.

**Generation workflow:** ask for the Jira ticket → run `mvn clean compile liquibase:diff -P liquibase -Dissue.name={TICKET}` → validate and fix the generated YAML (Liquibase generates non-compliant output by default).

**File location:** `src/main/resources/db/migrations/{yyyyMMddHHmmss}_{JIRA-TICKET}.yaml`

- Table: singular `snake_case` + `remarks: 'MAE/TRX/DOM/TMP: ...'`
- Every column: `remarks: "description"` mandatory
- PK: `PK_{table}_id` · FK: `FK_{origin}_{target}_{field}` · Index: `IDX_{TABLE}_{COLUMN}` · Unique: `UQ_{TABLE}_{COLUMNS}`
- Types: `INT`, `VARCHAR(n)`, `DECIMAL(19,2)`, `DATETIME`, `JSON`, `ENUM(...)`, `BIT(1)` — never `BIGINT`/`FLOAT`/`BOOLEAN`
- One concern per changeSet (createTable / addIndex / addForeignKey / addUniqueConstraint)

**Audit format:** see `references/liquibase.md` — violations list + corrected YAML.

## Cache Guidelines

**Workflow:** Before implementing caching, read `references/cache.md` for Redis/Caffeine configuration and naming conventions.

| Rule | Requirement |
|------|-------------|
| `CACHE_NAME` | Plural, camelCase, English: `countries`, `routePairCostConfig` |
| `CACHE_KEY` | `'all'` for lists; comma-separated params for composite keys |
| `CACHE_SCOPE` | Use `@Scope(proxyMode = ScopedProxyMode.TARGET_CLASS)` for self-injection |
| `CACHE_TTL` | Always configure TTL for Redis caches |
| `CACHE_DTO` | Use DTOs from shared library for serialization |
| `CACHE_TYPE` | Local (Caffeine) for single-instance; Redis for shared caches |

**Decision tree:**
1. Shared across instances? Yes → Redis, No → Local (Caffeine)
2. If Redis exists, reuse the connection

## API REST Guidelines

**Workflow:** Before creating REST endpoints, read `references/api-rest.md` for URL structure and prefix conventions.

| Rule | Requirement |
|------|-------------|
| `API_RESOURCE` | Plural nouns, lowercase, kebab-case: `/customers`, `/personal-info` |
| `API_PREFIX` | Context-based: `b2c`, `b2b`, `bo`, `ext`, `iuse`, `sfc`, `notification`, `cron` |
| `API_METHOD` | Correct HTTP verb for action: GET/POST/PUT/PATCH/DELETE |
| `API_VERSION` | Use `X-API-VERSION` header for versioning |
| `API_DTO` | Request/Response must use DTOs, never Entities |

**URL Pattern:** `/{service}/{prefix}/{resource}`

**Prefixes:**
- `b2c` - Business-to-consumer (session token required, API Gateway)
- `b2b` - Business-to-business (session token required, API Gateway)
- `bo` - Back-office (session token required, API Gateway)
- `ext` - External/public (no auth, API Gateway, rate-limited)
- `iuse` - Internal use (private, LB only)
- `sfc` - Salesforce (private, LB only)
- `notification` - Webhooks (API Key, separate API Gateway)
- `cron` - Scheduled tasks (Event Bridge → Lambda)

## Pre-Delivery Gate (MANDATORY)

**ALWAYS before delivering code:**

1. Read `references/checklist.md`
2. Verify ALL applicable items for your task
3. Fix any violations found
4. Report to user:

```
✅ Checklist verified
- Items reviewed: X/40
- Items N/A: Y
- Violations corrected: Z
```

> This step is NOT optional. Code delivered without checklist verification
> violates Global66 quality standards.
