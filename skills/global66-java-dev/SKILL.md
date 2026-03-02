---
name: global66-java-dev
description: >
  Spring Boot microservice development following Global66's hexagonal architecture standards.
  Use this skill whenever a user is developing Java code for Global66 microservices — whether
  creating new features, refactoring existing business logic, generating tests, implementing
  controllers, services, persistence, clients, mappers, SQS consumers/producers, Swagger/
  OpenAPI documentation, or Liquibase YAML database migrations. Also trigger for compliance
  reviews: log patterns (START/END, PII, MDC), SQS traceability, Swagger audits, and Liquibase
  YAML reviews (table naming, remarks, constraint names, index naming, G81-POL-033). Trigger
  on any Java/Spring Boot task in a Global66 context, even without explicit mention of
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
5. **Controllers are thin** — validate input, delegate to service, map response. No logic.
6. **Public methods orchestrate; private methods do one thing**

## @Transactional Rules

For full rules, examples, and audit output format (git diff reviews), see `references/transactional.md`.

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
// Interface
public interface UserController {
    UserResponse getUser(@PathVariable Integer userId);
}

// Implementation
@Slf4j
@RestController
@RequiredArgsConstructor
@RequestMapping("/ms-name/iuse/users")
public class UserControllerImpl implements UserController {
    private final UserService userService;

    @GetMapping("/{userId}")
    public UserResponse getUser(@PathVariable Integer userId) {
        return UserPresentationMapper.INSTANCE.toResponse(
            userService.findUser(userId));
    }
}
```

- Response DTOs: prefer `record` for immutable responses
- Request DTOs: `@Data` class with `@NotNull`/`@NotBlank` + `@JsonProperty`
- Always use `@Schema` (OpenAPI) on DTOs for documentation

### Business Layer

```java
// Interface
public interface CreateUserService {
    UserData createUser(UserData userData);
}

// Implementation
@Slf4j
@Service
@RequiredArgsConstructor
public class CreateUserServiceImpl implements CreateUserService {
    private final UserPersistence userPersistence;
    private final NotificationService notificationService;

    @Override
    @Transactional(rollbackFor = Exception.class)
    public UserData createUser(UserData userData) {
        ensureUserDoesNotExist(userData.getEmail());
        UserData saved = userPersistence.save(userData);
        notificationService.notifyWelcome(saved);
        return saved;
    }

    private void ensureUserDoesNotExist(String email) {
        if (userPersistence.existsByEmail(email)) {
            throw userAlreadyExistsException(email);
        }
    }

    private RuntimeException userAlreadyExistsException(String email) {
        return new BusinessException(ErrorCode.USER_ALREADY_EXISTS, email);
    }
}
```

### Persistence Layer

```java
// Interface
public interface UserPersistence {
    UserData save(UserData userData);
    Optional<UserData> findById(Integer id);
    boolean existsByEmail(String email);
}

// Implementation
@Component
@RequiredArgsConstructor
public class UserPersistenceImpl implements UserPersistence {
    private final UserRepository userRepository;

    @Override
    public UserData save(UserData userData) {
        UserEntity entity = UserMapper.INSTANCE.toEntity(userData);
        return UserMapper.INSTANCE.toData(userRepository.save(entity));
    }

    @Override
    public Optional<UserData> findById(Integer id) {
        return userRepository.findById(id).map(UserMapper.INSTANCE::toData);
    }
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

### Client Layer (Retrofit)

For the complete file-by-file generation guide (all 9 files + 3 config updates), see
`references/api-client.md`. Ask the user for 4 inputs and infer the rest.

**Key patterns:**

```java
// Retrofit Api interface (client/rest/api/)
public interface MapBoxApi {
    @Headers("Accept: application/json")
    @POST("api/v1/geocode")
    Call<MapBoxResponseDto> createMapBox(
        @Header("Authorization") String token,
        @Body MapBoxRequestDto mapBoxRequestDto);
}

// Client implementation (client/rest/impl/) — @Component, not @Service
@Component
@RequiredArgsConstructor
public class MapBoxClientImpl implements MapBoxClient {
    private final MapBoxApi mapBoxApi;

    @Override
    public MapBoxResponse createMapBox(String token, MapBoxRequest mapBoxRequest) {
        MapBoxRequestDto dto = MapBoxRequestClientMapper.INSTANCE.toDto(mapBoxRequest);
        Call<MapBoxResponseDto> call = mapBoxApi.createMapBox(token, dto);
        Response<MapBoxResponseDto> response = checkCallExecute(call, HTTP_CLIENT_COMPONENT);
        MapBoxResponseDto responseDto = checkResponse(response, HTTP_CLIENT_COMPONENT);
        return MapBoxResponseClientMapper.INSTANCE.toModel(responseDto);
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

### Quick Reference

| Prefix | Purpose | Returns | Throws? |
|--------|---------|---------|---------|
| `ensure*` | Precondition validation | void | Yes |
| `verify*` | Complex condition check | void | Yes |
| `guardAgainst*` | Defensive check | void | Yes |
| `is*` / `has*` | Boolean predicate | boolean | No |
| `fetch*` / `require*` | Get or throw NOT_FOUND | Domain object | Yes |
| `find*` | Query persistence | Optional | No |
| `build*Exception` | Exception factory | Exception | No |

### Method Structure Rules

- **Public methods**: max 10 lines, orchestration only — no `if-else`, no null checks, no direct persistence calls
- **Private methods**: max 8 lines, single responsibility
- **Max nesting depth**: 2 · **Max parameters**: 4
- **Forbidden names**: `process`, `handle`, `execute`, `validate`, `check` — always be specific

```java
// BAD: everything inline, generic name, direct repository, inline exceptions
public void processUser(UserData data) { ... }

// GOOD: public method orchestrates, private methods do one thing
public void registerUser(UserData data) {
    ensureEmailIsAvailable(data.getEmail());
    ensureUserIsAdult(data.getAge());
    userPersistence.save(data);
}
private void ensureEmailIsAvailable(String email) {
    if (userPersistence.existsByEmail(email)) throw emailAlreadyRegisteredException(email);
}
private boolean isUnderage(int age) { return age < 18; }
private RuntimeException emailAlreadyRegisteredException(String email) {
    return new BusinessException(ErrorCode.EMAIL_ALREADY_REGISTERED, email);
}
```

## Entities

```java
@Entity
@Table(name = "user",
    indexes = { @Index(name = "IDX_USER_EMAIL", columnList = "email") })
@Comment("User entity for core domain")
@Getter @Setter
public class UserEntity {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "id") private Integer id;

    @Column(name = "email", nullable = false, unique = true, length = 100)
    @Comment("User email address") private String email;

    @Enumerated(EnumType.STRING)
    @Column(name = "status", nullable = false, length = 50)
    private UserStatusEnum status;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false)
    private LocalDateTime createdAt;
}
```

## Unit Tests

> **Siempre preguntar antes de generar tests** — el foco principal es el desarrollo de servicios.
> Tests son secundarios. Antes de escribir tests, preguntar:
> ¿Querés los tests ahora o después? ¿Es desde un diff o una clase puntual? ¿Ya existe el archivo de test?

For full testing guide, coverage requirements, and examples, see `references/tests.md`.

**Rules:** Name = `Given_When_Then` · `@Nested` per method · 4 types (Happy/Negative/Edge/Branch) · DTOs from JSON only · AssertJ · no comments · explicit imports · git diff: new/modified scope only, never overwrite.

## SonarQube

For the full coverage workflow (git diff + Sonar report) and the Sonar rule → Global66 fix mapping, see `references/sonar.md`.

**Coverage gaps** (user provides git diff + Sonar uncovered lines):
- Scope: only new/modified methods from the diff
- Extend existing test class if it exists; create new one if not
- Complex DTOs always from JSON fixtures in `src/test/resources/`
- Target: 100% of new lines covered

**Issues resolution** (user provides Sonar report):
- Prioritize CRITICAL (vulnerabilities, bugs) → MAJOR (complexity, duplication) → MINOR (style)
- `java:S3776` Cognitive Complexity → extract to `ensure*/verify*/is*/has*` private methods (SRP pattern)
- `java:S112` Generic exception → `BusinessException(ErrorCode.XXX, ...)` factory method
- `java:S107` Too many parameters → wrap in `*Data` domain object, never Builder Pattern
- `java:S106` System.out → `@Slf4j` + `log.*` following SGSI-POL-005

## SQS Configuration

For the complete Gold Standard code (SqsClientConfig, TracingMessageListenerWrapper, TracingSqsEndpoint, TracingSqsListenerAnnotationBeanPostProcessor, MdcTaskDecorator) and all rules, see `references/sqs.md`.

### 4 Required Classes (copy as-is, change only the package)

| Class | Purpose |
|-------|---------|
| `SqsClientConfig` | `SqsAsyncClient` bean + registers `TracingSqsListenerAnnotationBeanPostProcessor` under `SqsBeanNames.*` |
| `TracingMessageListenerWrapper` | Extracts `traceId` from incoming message header → MDC, removes in `finally` |
| `TracingSqsEndpoint` | Overrides `createMessageListenerInstance` to wrap with `TracingMessageListenerWrapper` |
| `TracingSqsListenerAnnotationBeanPostProcessor` | Overrides `createEndpoint` to use `TracingSqsEndpoint` |

### Consumer Pattern

```java
@Slf4j @Component @RequiredArgsConstructor
public class OrderQueueListenerImpl implements OrderQueueListener {
    private final OrderService orderService;

    @Override
    @SqsListener(value = "${com.global.{domain}.queue.sqs.order.url}")
    public void receiveMessage(String message) {
        log.info("START - [receiveMessage] [SQS]: {}", message);
        try {
            OrderMessageDto dto = ObjectMapperUtils.loadObject(message, OrderMessageDto.class);
            orderService.process(OrderMessageMapper.INSTANCE.toData(dto));
        } catch (Exception e) {
            log.error("Failed to process order message from SQS: {}", message, e);
        }
        log.info("END - [receiveMessage] [SQS]");
    }
}
```

### Producer Pattern (with traceId propagation)

```java
// Standard queue
sqsTemplate.send(to -> to
    .queue(queueUrl)
    .payload(mapper.toMessage(data))
    .header("traceId", MDC.get("traceId")));

// FIFO queue — also requires messageGroupId and messageDeduplicationId
sqsTemplate.send(to -> to
    .queue(queueUrl)
    .payload(mapper.toMessage(data))
    .header("traceId", MDC.get("traceId"))
    .header(SqsHeaders.MessageSystemAttributes.SQS_MESSAGE_GROUP_ID_HEADER, data.getGroupId())
    .header(SqsHeaders.MessageSystemAttributes.SQS_MESSAGE_DEDUPLICATION_ID_HEADER,
        data.getTransactionId()));
```

### Queue Naming Convention

```
{ms}-{action}-{env}           # Standard:  geolocation-events-dev
{ms}-{action}-{env}.fifo      # FIFO:      transaction-geolocation-dev.fifo
{ms}-{action}-{env}-dlq       # DLQ:      transaction-geolocation-dev-dlq
```

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

```java
// Controller (correct)
@GetMapping("/{userId}")
public UserResponse getUser(@PathVariable Integer userId) {
    log.info("START - [GET] [/users/{}]: userId={}", userId, userId);
    UserResponse response = UserPresentationMapper.INSTANCE.toResponse(
        userService.findUser(userId));
    log.info("END - [GET] [/users/{}]", userId);
    return response;
}

// Service (correct — business milestone only, no entry/exit)
public UserData createUser(UserData userData) {
    ensureEmailIsAvailable(userData.getEmail());
    UserData saved = userPersistence.save(userData);
    log.info("User registered successfully: userId={}", saved.getId());
    return saved;
}

// Error (correct)
} catch (Exception e) {
    log.error("Failed to process SQS message: transactionId={}", transactionId, e);
}
```

### Log Compliance Review (git diff)

When a user provides a `git diff` for log review, read `references/logging.md` for the
full compliance check and output format. Analyze all lines starting with `+`, classify
each violation by category (`SECURITY | FORMAT | ARCHITECTURE | NOISE`) and severity
(`CRITICAL | WARNING`), and provide corrected code for each.

## Swagger / OpenAPI Documentation

For complete examples and audit report format, see `references/swagger.md`.

**Core rule:** All Swagger annotations live on the **interface only**. The `@RestController`
implementation has zero `@Tag`, `@Operation`, or `@Schema` annotations.

### Interface annotations (mandatory)

```java
@Tag(name = "Payment", description = "Payment processing operations")
public interface PaymentController {

    @ErrorResponses(values = {
        @ErrorResponse(reason = ErrorReason.NOT_FOUND, source = ErrorSource.BUSINESS_SERVICE),
        @ErrorResponse(reason = ErrorReason.CONFLICT,  source = ErrorSource.HTTP_CLIENT_COMPONENT)
    })
    @Operation(summary = "Process a payment",
               description = "Validates and persists a new payment transaction")
    @SecurityRequirement(name = "authB2C")
    PaymentResponse createPayment(
        @Parameter(description = "Authenticated user email", required = true,
                   example = "user@global66.com")
            @RequestHeader("Claim-Email") String email,
        @RequestBody @Valid PaymentRequest request);
}
```

### DTO annotations

```java
// Request class
@Data
@Schema(name = "PaymentRequest", description = "Payload for creating a payment",
        example = "{\"amount\": 1000, \"currency\": \"CLP\"}")
public class PaymentRequest {
    @Schema(description = "Amount to transfer", requiredMode = Schema.RequiredMode.REQUIRED,
            example = "1000")
    private BigDecimal amount;
}

// Response record
public record PaymentResponse(
    @Schema(description = "Generated transaction ID", example = "TXN-2024-001") String txnId,
    @Schema(description = "Final transaction status", example = "COMPLETED") String status) {}
```

### application.yml (required)
```yaml
springdoc:
  api-docs:
    path: /{serviceName}/api-docs
  swagger-ui:
    path: /{serviceName}/swagger-ui.html
  override-with-generic-response: false
```

### Security schemes: `authB2C` | `authB2B` | `authAdmin`
Add `@Server` only for endpoints exposed on API Gateway.

## Liquibase YAML (G81-POL-033)

For full rules, Gold Standard examples, and audit format, see `references/liquibase.md`.

**File location:** `src/main/resources/db/migrations/{yyyyMMddHHmmss}_{JIRA-TICKET}.yaml`

- Table: singular `snake_case` + `remarks: 'MAE/TRX/DOM/TMP: ...'`
- Every column: `remarks: "description"` mandatory
- PK: `PK_{table}_id` · FK: `FK_{origin}_{target}_{field}` · Index: `IDX_{TABLE}_{COLUMN}` · Unique: `UQ_{TABLE}_{COLUMNS}`
- Types: `INT`, `VARCHAR(n)`, `DECIMAL(19,2)`, `DATETIME`, `JSON`, `ENUM(...)`, `BIT(1)` — never `BIGINT`/`FLOAT`/`BOOLEAN`
- One concern per changeSet (createTable / addIndex / addForeignKey / addUniqueConstraint)

**Audit format:** see `references/liquibase.md` — violations list + corrected YAML.

## Checklist Before Finishing Code

- [ ] No `@Entity` outside `persistence/` package
- [ ] No repository injected directly into a service (use `*Persistence` port)
- [ ] `@Transactional` only in business layer — never in persistence, controller, or client layers
- [ ] `@Transactional` only on `public` methods (proxy bypass on private/protected)
- [ ] Always `rollbackFor = Exception.class` on write operations
- [ ] `readOnly = true` on `find*`/`fetch*`/`get*`/`list*` methods
- [ ] No HTTP/external API calls inside a `@Transactional` block
- [ ] No `this.method()` calls to another `@Transactional` method in the same bean
- [ ] Methods returning `Stream<?>` collect inside the transaction before returning
- [ ] All public methods: ≤10 lines, orchestration only
- [ ] No `process/handle/execute/validate/check` as method names
- [ ] Boolean conditions extracted to `is*`/`has*` methods
- [ ] No inline `throw new` — use factory methods
- [ ] MapStruct mapper per layer, with `INSTANCE` singleton and full `@Mapper(componentModel="default", ...)` config
- [ ] API clients: `@Component` (not `@Service`) on `*ClientImpl`
- [ ] API clients: domain objects in `domain/external_request/`, not `domain/data/`
- [ ] API clients: two separate mappers (`*RequestClientMapper`, `*ResponseClientMapper`)
- [ ] API clients: `checkCallExecute` + `checkResponse` from `RetrofitUtils`, no try/catch in impl
- [ ] API clients: `RestClientConfig` + `EndpointsConfig` + `application-local.yml` updated
- [ ] Tests use Given_When_Then naming and JSON fixtures
- [ ] Controllers/listeners have START + END logs with relevant IDs
- [ ] No PII, passwords, tokens, or full request bodies in logs
- [ ] `log.error()` always includes exception object as last argument
- [ ] Async executors use `ContextSnapshot` task decorator for MDC propagation
- [ ] SQS: 4 traceability classes present (`SqsClientConfig`, `TracingMessageListenerWrapper`, `TracingSqsEndpoint`, `TracingSqsListenerAnnotationBeanPostProcessor`)
- [ ] SQS consumers: catch `Exception` broadly to avoid retry storms
- [ ] SQS producers: include `traceId` header from MDC
- [ ] FIFO: `messageGroupId` + `messageDeduplicationId` set on every send
- [ ] DLQ configured in AWS for each queue
- [ ] Liquibase: file named `{yyyyMMddHHmmss}_{JIRA-TICKET}.yaml`
- [ ] Tables: singular snake_case + `remarks` with MAE/TRX/DOM/TMP classification
- [ ] All columns have `remarks`, PK/FK/UQ/IDX names follow G81-POL-033 convention
- [ ] One concern per changeSet (no bundled createTable + indexes + FKs)
- [ ] Swagger: all annotations on interface, zero on implementation
- [ ] `@Tag(name, description)` on every controller interface
- [ ] `@Operation(summary, description)` on every method
- [ ] `@ErrorResponses` for methods that can throw business/client errors
- [ ] `@SecurityRequirement` on protected endpoints
- [ ] Request DTOs: `@Schema` at class level (name + description + example) and each field
- [ ] Response records: `@Schema` on each component with description + example
- [ ] No `RuntimeException` thrown directly — always `BusinessException(ErrorCode.XXX, ...)`
- [ ] No cognitive complexity > 15 — extract to private methods with semantic naming
- [ ] Tests: only new/modified methods from git diff, never overwrite existing tests
- [ ] Tests: complex DTOs loaded from JSON fixtures, never constructed inline with setters
