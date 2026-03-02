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
- [ ] No inline `throw new` — use factory methods (`build*Exception`)
- [ ] No `RuntimeException` thrown directly — always `BusinessException(ErrorCode.XXX, ...)`
- [ ] No cognitive complexity > 15 — extract to private methods with semantic naming

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
