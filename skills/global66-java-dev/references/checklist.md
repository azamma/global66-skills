# Pre-Entrega Checklist

Usar esta lista antes de finalizar cualquier código para Global66.

## Arquitectura
- [ ] No `@Entity` outside `persistence/` package
- [ ] No repository injected directly into a service (use `*Persistence` port)
- [ ] Methods returning `Stream<?>` collect inside the transaction before returning
- [ ] All public methods: ≤10 lines, orchestration only
- [ ] Private methods: ≤8 lines, single responsibility
- [ ] Max nesting depth: 2, max parameters: 4
- [ ] Boolean conditions extracted to `is*`/`has*` methods

## @Transactional
- [ ] `@Transactional` only in business layer — never in persistence, controller, or client layers
- [ ] `@Transactional` only on `public` methods (proxy bypass on private/protected)
- [ ] Always `rollbackFor = Exception.class` on write operations
- [ ] `readOnly = true` on `find*`/`fetch*`/`get*`/`list*` methods
- [ ] No HTTP/external API calls inside a `@Transactional` block
- [ ] No `this.method()` calls to another `@Transactional` method in the same bean

## SRP & Naming
- [ ] No `process/handle/execute/validate/check` as method names
- [ ] No cognitive complexity > 15 — extract to private methods with semantic naming

## Exception Handling
- [ ] No inline `throw new RuntimeException()` or `throw new Exception()`
- [ ] Always use `ApiRestException.builder().reason(ErrorReason.XXX).source(ErrorSource.XXX).build()`
- [ ] `ErrorReason` is specific to the error condition (e.g., `CUSTOMER_NOT_FOUND`)
- [ ] `ErrorSource` matches the layer: `BUSINESS_SERVICE`, `DATA_REPOSITORY`, `REST_CONTROLLER`, `HTTP_CLIENT_*`
- [ ] Factory methods `build*Exception()` for repeated exceptions
- [ ] NO local enums created for custom errors
- [ ] Use `// TODO: ERROR_CODE (HTTP_STATUS)` comment when specific ErrorReason doesn't exist

## MapStruct
- [ ] MapStruct mapper per layer, with `INSTANCE` singleton
- [ ] Full `@Mapper(componentModel="default", ...)` config with null value strategies

## API Clients
- [ ] API clients: `@Component` (not `@Service`) on `*ClientImpl`
- [ ] API clients: domain objects in `domain/external_request/`, not `domain/data/`
- [ ] API clients: two separate mappers (`*RequestClientMapper`, `*ResponseClientMapper`)
- [ ] API clients: `checkCallExecute` + `checkResponse` from `RetrofitUtils`, no try/catch in impl
- [ ] API clients: `RestClientConfig` + `EndpointsConfig` + `application-local.yml` updated

## Testing
- [ ] Tests use Given_When_Then naming and JSON fixtures
- [ ] Tests: only new/modified methods from git diff, never overwrite existing tests
- [ ] Tests: complex DTOs loaded from JSON fixtures, never constructed inline with setters

## Logging
- [ ] Controllers/listeners have START + END logs with relevant IDs
- [ ] No PII, passwords, tokens, or full request bodies in logs
- [ ] `log.error()` always includes exception object as last argument
- [ ] Async executors use `ContextSnapshot` task decorator for MDC propagation

## SQS
- [ ] SQS: 4 traceability classes present (`SqsClientConfig`, `TracingMessageListenerWrapper`, `TracingSqsEndpoint`, `TracingSqsListenerAnnotationBeanPostProcessor`)
- [ ] SQS consumers: catch `Exception` broadly to avoid retry storms
- [ ] SQS producers: include `traceId` header from MDC
- [ ] FIFO: `messageGroupId` + `messageDeduplicationId` set on every send
- [ ] DLQ configured in AWS for each queue

## Liquibase
- [ ] Liquibase: file named `{yyyyMMddHHmmss}_{JIRA-TICKET}.yaml`
- [ ] Tables: singular snake_case + `remarks` with MAE/TRX/DOM/TMP classification
- [ ] All columns have `remarks`, PK/FK/UQ/IDX names follow G81-POL-033 convention
- [ ] One concern per changeSet (no bundled createTable + indexes + FKs)

## Swagger
- [ ] Swagger: all annotations on interface, zero on implementation
- [ ] `@Tag(name, description)` on every controller interface
- [ ] `@Operation(summary, description)` on every method
- [ ] `@ErrorResponses` for methods that can throw business/client errors
- [ ] `@SecurityRequirement` on protected endpoints
- [ ] Request DTOs: `@Schema` at class level (name + description + example) and each field
- [ ] Response records: `@Schema` on each component with description + example

## Cache
- [ ] Cache name: plural, camelCase, English (`countries`, `routePairCostConfig`)
- [ ] String keys use single quotes: `key = "'all'"`, `key = "'enabled'"`
- [ ] Composite keys: comma-separated parameters: `key = "{ #id, #type }"`
- [ ] Cache service has `@Scope(proxyMode = ScopedProxyMode.TARGET_CLASS)` for self-injection
- [ ] TTL configured for Redis caches in CacheManager or per-cache configuration
- [ ] DTOs from shared library used for serialization (avoid LinkedHashMap casting issues)
- [ ] Proper serialization with type info: `activateDefaultTyping(..., DefaultTyping.EVERYTHING)`
- [ ] Cache eviction implemented when data changes (create/update/delete operations)
- [ ] Cache type decision documented: Redis for shared, Caffeine for local-only

## API REST
- [ ] Resource names: plural nouns, lowercase (`/customers`, `/orders`)
- [ ] Multi-word resources: kebab-case (`/personal-info` not `/personalInfo`)
- [ ] No verbs in URLs: use `/customers` not `/get-customer`
- [ ] HTTP methods used correctly: GET/POST/PUT/PATCH/DELETE
- [ ] Prefix chosen correctly: b2c/b2b/bo/ext/iuse/sfc/notification/cron
- [ ] User ID extracted from auth token for b2c/b2b/bo (not from request body)
- [ ] Request/Response use DTOs, never Entities or ambiguous types
- [ ] Versioning with `X-API-VERSION` header for breaking changes
- [ ] iuse/sfc endpoints NOT exposed in API Gateway
- [ ] ext endpoints rate-limited and without sensitive data

## Cache
- [ ] Cache name is plural, camelCase, English (e.g., `countries`, `routePairCostConfig`)
- [ ] String keys use single quotes: `key = "'all'"`, `key = "'enabled'"`
- [ ] Composite keys use comma-separated params: `key = "{ #routePairId, #paymentTypeId }"`
- [ ] Cache service has `@Scope(proxyMode = ScopedProxyMode.TARGET_CLASS)` for self-injection
- [ ] Cache service uses self-injection (`private final {Domain}CacheService self`) to call cached methods internally
- [ ] TTL configured for Redis caches in CacheManager bean
- [ ] DTOs from shared library (`arch-cache-dto`) used for serialization
- [ ] Full type info serialization enabled: `.activateDefaultTyping(...)` in RedisCacheConfig
- [ ] Local cache (Caffeine) for single-instance; Redis for shared caches
- [ ] Cache eviction implemented when data changes (create/update/delete operations)
