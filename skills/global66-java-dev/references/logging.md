# Logging Guidelines — Global66 (SGSI-POL-005)

Stack: Java 17 · Spring Boot 3.1.1 · SLF4J · Logback · AWS CloudWatch · `@Slf4j`

MDC must always contain: `X-Amzn-Request-Id`, `traceId`, `spanId`.

---

## Layer-by-Layer Rules

### Controllers & SQS Listeners — START/END logs required

Every public entry point (HTTP controller method, SQS listener) must log START and END.

**HTTP Controllers:**
```java
// START pattern: method + path + relevant IDs (never full body)
log.info("START - [GET] [/users/{}/last-location]: userId={}", userId);

// END pattern: method + path only
log.info("END - [GET] [/users/{}/last-location]");
```

**SQS Listeners:**
```java
log.info("START - [receiveMessage] [SQS]: {}", message);
// ... processing ...
log.info("END - [receiveMessage] [SQS]");
```

**What to include in START:** IDs, keys, discriminating parameters — never full request body, never PII.

### Business & Persistence Layers — Business milestones only

```java
// INFO: Only significant business events (state changes, external calls initiated)
log.info("Initiating geocoding for locationId={}, countryCode={}", locationId, countryCode);
log.info("Device permission updated for userId={}, fingerprint={}", userId, fingerprint);

// DEBUG: Internal calculations, intermediate values (never in production by default)
log.debug("Calculated transfer fee: amount={}, fee={}", amount, fee);

// FORBIDDEN: method entry/exit noise in service or persistence layer
log.info("Entering registerDevicePermission");   // BAD — noise
log.info("Exiting registerDevicePermission");    // BAD — noise
log.info("Calling persistence layer");           // BAD — noise
```

**Rule of thumb:** If the log would appear on every request regardless of what happened, it's noise. Only log when something meaningful changed or when it helps diagnose a specific business problem.

### Error Handling — Always include the exception object

```java
// CORRECT: contextual message + identifier + exception as last argument
log.error("Failed to process SQS message: transactionId={}", transactionId, e);
log.error("External geocoding API call failed: locationId={}", locationId, e);

// WRONG: swallowing stacktrace
log.error("Something failed");                     // no context, no stacktrace
log.error("Error: {}", e.getMessage());            // only message, loses stacktrace
log.error("Failed processing", e.getMessage(), e); // message duplicated incorrectly
```

**Level guide:**
- `ERROR`: unhandled or flow-breaking exceptions (the operation cannot continue)
- `WARN`: recoverable issues, degraded behavior, retries
- `INFO`: business milestones
- `DEBUG`: diagnostic data for development

---

## Security & PII — Forbidden in logs

Never log any of the following:
- Passwords, PINs, security tokens, JWT contents
- Full card numbers (PAN) — last digit only visible via `MaskingPatternLayout`
- Biometric data
- Full email addresses in bulk flows (use partial: `us***@g***`)
- Complete request/response bodies from financial operations

```java
// BAD
log.info("Processing payment for user {} with card {}", userId, cardNumber);
log.info("Login attempt: email={}, password={}", email, password);

// GOOD
log.info("Processing payment: userId={}, lastFourDigits={}", userId, lastFour);
log.info("Login attempt: email={}", maskEmail(email));
```

**`MaskingPatternLayout`** must be configured in `logback.xml` to automatically mask PAN numbers
(only last digit visible) and JWT tokens before writing to any appender.

---

## Async Context Propagation — MDC must survive thread hops

When using async executors, MDC context is lost by default. Two required patterns:

### ThreadPoolTaskExecutor (MDC propagation via ContextSnapshot)
```java
// In AsyncConfig or your executor @Bean
@Bean
public TaskExecutor asyncExecutor() {
    ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
    executor.setCorePoolSize(5);
    executor.setMaxPoolSize(20);
    // REQUIRED: propagate MDC to async threads
    executor.setTaskDecorator(runnable ->
        ContextSnapshot.captureAll().wrap(runnable));
    executor.initialize();
    return executor;
}
```

### CompletableFuture (use CompletableFutureHelper)
```java
// BAD: MDC context lost in the async thread
CompletableFuture.runAsync(() -> doSomething(), executor);

// GOOD: MDC preserved via helper
CompletableFutureHelper.runAsync(() -> doSomething(), executor);
```

**Why it matters:** Without context propagation, CloudWatch traces break — you can't correlate
async logs with the originating request's `traceId` and `X-Amzn-Request-Id`.

---

## Log Compliance Review (from git diff)

When the user provides a `git diff`, review all lines starting with `+` for logging violations.
Output a structured compliance report:

```
COMPLIANCE SUMMARY
──────────────────
Compliant: false
Violations: 3
Risk Level: HIGH

VIOLATIONS
──────────
[1] CRITICAL · SECURITY · UserServiceImpl.java:47
    Code: log.info("User login: email={}, password={}", email, password)
    Issue: Password logged in plain text — violates SGSI-POL-005
    Fix:   log.info("User login: email={}", maskEmail(email))

[2] WARNING · NOISE · PaymentServiceImpl.java:23
    Code: log.info("Entering processPayment method")
    Issue: Method entry/exit logs in service layer are forbidden noise
    Fix:   Remove this line entirely

[3] CRITICAL · FORMAT · OrderController.java:31
    Code: log.error("Failed: " + e.getMessage())
    Issue: Exception object not passed as last argument — stacktrace lost in CloudWatch
    Fix:   log.error("Failed to process order: orderId={}", orderId, e)
```

**Issue categories:** `SECURITY` | `FORMAT` | `ARCHITECTURE` | `NOISE`
**Severity:** `CRITICAL` (must fix before merge) | `WARNING` (should fix)

---

## Quick Compliance Checklist

When generating new code or reviewing existing code:

- [ ] Controller methods have `log.info("START - [METHOD] [PATH]: {}")` and `log.info("END - [METHOD] [PATH]")`
- [ ] SQS listeners have `log.info("START - [receiveMessage] [SQS]: {}")` and `log.info("END - ...")`
- [ ] No full request/response bodies in logs
- [ ] No PII, passwords, tokens, or full card numbers logged
- [ ] Service/persistence layer: only business milestone logs, no method entry/exit
- [ ] `log.error()` always has the exception object as last argument
- [ ] Async executors use `ContextSnapshot.captureAll().wrap(runnable)` task decorator
- [ ] `CompletableFuture` uses `CompletableFutureHelper` to preserve MDC
- [ ] All services use `@Slf4j` (Lombok annotation, not manual logger declaration)
