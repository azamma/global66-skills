# Log Compliance Review Report

**Reviewed by:** Senior Java Developer
**Policy:** SGSI-POL-005 — Global66 Logging Guidelines
**Date:** 2026-03-02

---

## COMPLIANCE SUMMARY

```
Compliant:   false
Violations:  4
Risk Level:  HIGH
```

---

## VIOLATIONS

---

### [1] CRITICAL · SECURITY · PaymentControllerImpl.java

**Code:**
```java
log.info("Processing payment for user: email={}, cardNumber={}, amount={}",
    request.getEmail(), request.getCardNumber(), request.getAmount());
```

**Issue:** Two distinct PII/sensitive data violations in one log statement:

1. **Full card number (PAN) logged** — logging `cardNumber` in plain text is a direct violation of SGSI-POL-005 and PCI-DSS requirements. Full PANs must never appear in logs. Only the last four digits are permitted, and only via the configured `MaskingPatternLayout`.
2. **Full email address logged** — emailing addresses are PII. In financial operation flows, full email addresses must not be logged. A masked form (e.g., `us***@g***`) must be used instead.

**Fix:**
```java
log.info("START - [POST] [/payments]: userId={}, lastFourDigits={}, amount={}",
    paymentData.getUserId(), maskLastFour(request.getCardNumber()), request.getAmount());
```

> Note: The method must also be restructured to include the mandatory START/END pattern described in violation [2] below.

---

### [2] CRITICAL · FORMAT · PaymentControllerImpl.java

**Code:**
```java
public PaymentResponse createPayment(@RequestBody PaymentRequest request) {
    log.info("Processing payment for user: email={}, cardNumber={}, amount={}",
        ...);
    return PaymentPresentationMapper.INSTANCE.toResponse(
        createPaymentService.create(PaymentPresentationMapper.INSTANCE.toData(request)));
}
```

**Issue:** The controller method is missing the mandatory **START** and **END** log pattern required for all HTTP controller entry points. There is a single log line in the middle of the method body, but:
- It does not follow the `START - [METHOD] [PATH]: ...` format.
- There is no `END - [METHOD] [PATH]` log before returning.

Per SGSI-POL-005, every public HTTP controller method must open with a START log and close with an END log to enable request tracing in CloudWatch.

**Fix:**
```java
@PostMapping
public PaymentResponse createPayment(@RequestBody PaymentRequest request) {
    log.info("START - [POST] [/payments]: amount={}", request.getAmount());
    PaymentResponse response = PaymentPresentationMapper.INSTANCE.toResponse(
        createPaymentService.create(PaymentPresentationMapper.INSTANCE.toData(request)));
    log.info("END - [POST] [/payments]");
    return response;
}
```

---

### [3] WARNING · NOISE · CreatePaymentServiceImpl.java

**Code:**
```java
log.info("Entering createPayment service method");
// ...
log.info("Payment saved successfully");
```

**Issues:**

1. `"Entering createPayment service method"` — Method entry logs in the service layer are explicitly forbidden as noise under SGSI-POL-005. This log fires on every request regardless of outcome and carries no business value. **Must be removed.**

2. `"Payment saved successfully"` — This line is borderline. Logging that a payment was persisted can be a legitimate business milestone, but the message lacks any identifying context (e.g., `paymentId`, `userId`, `transactionId`). Without a correlating identifier, this log is useless for incident diagnosis.

**Fix:**
```java
@Override
@Transactional(rollbackFor = Exception.class)
public PaymentData create(PaymentData paymentData) {
    ensureUserHasSufficientBalance(paymentData);
    PaymentData saved = paymentPersistence.save(paymentData);
    log.info("Payment created successfully: paymentId={}, userId={}", saved.getId(), paymentData.getUserId());
    return saved;
}
```

---

### [4] CRITICAL · ARCHITECTURE · AsyncConfig.java

**Code:**
```java
@Bean
public TaskExecutor paymentExecutor() {
    ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
    executor.setCorePoolSize(5);
    executor.setMaxPoolSize(20);
    executor.initialize();
    return executor;
}
```

**Issue:** The `ThreadPoolTaskExecutor` is configured **without a `TaskDecorator`**. When tasks run on a thread pool, Spring's MDC context (which carries `traceId`, `spanId`, and `X-Amzn-Request-Id`) is not automatically propagated to worker threads. This means all async log statements will have empty or incorrect trace identifiers in CloudWatch, making it impossible to correlate async operations back to the originating HTTP request.

Per SGSI-POL-005, all `ThreadPoolTaskExecutor` beans must set a task decorator using `ContextSnapshot.captureAll().wrap(runnable)`.

**Fix:**
```java
@Bean
public TaskExecutor paymentExecutor() {
    ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
    executor.setCorePoolSize(5);
    executor.setMaxPoolSize(20);
    // REQUIRED: propagate MDC (traceId, spanId, X-Amzn-Request-Id) to async threads
    executor.setTaskDecorator(runnable ->
        ContextSnapshot.captureAll().wrap(runnable));
    executor.initialize();
    return executor;
}
```

---

## FULL CORRECTED CODE

### PaymentControllerImpl.java

```java
@PostMapping
public PaymentResponse createPayment(@RequestBody PaymentRequest request) {
    log.info("START - [POST] [/payments]: amount={}", request.getAmount());
    PaymentResponse response = PaymentPresentationMapper.INSTANCE.toResponse(
        createPaymentService.create(PaymentPresentationMapper.INSTANCE.toData(request)));
    log.info("END - [POST] [/payments]");
    return response;
}
```

**Changes applied:**
- Replaced the PII-leaking log with a compliant START log that includes only the payment amount (non-PII business context).
- Added the mandatory END log before the return statement.
- Removed `email` and `cardNumber` from the log entirely.

---

### CreatePaymentServiceImpl.java

```java
@Override
@Transactional(rollbackFor = Exception.class)
public PaymentData create(PaymentData paymentData) {
    ensureUserHasSufficientBalance(paymentData);
    PaymentData saved = paymentPersistence.save(paymentData);
    log.info("Payment created successfully: paymentId={}, userId={}", saved.getId(), paymentData.getUserId());
    return saved;
}
```

**Changes applied:**
- Removed the forbidden method entry log (`"Entering createPayment service method"`).
- Replaced the contextless `"Payment saved successfully"` with a business milestone log that includes identifying fields (`paymentId`, `userId`).

---

### AsyncConfig.java

```java
@Bean
public TaskExecutor paymentExecutor() {
    ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
    executor.setCorePoolSize(5);
    executor.setMaxPoolSize(20);
    executor.setTaskDecorator(runnable ->
        ContextSnapshot.captureAll().wrap(runnable));
    executor.initialize();
    return executor;
}
```

**Changes applied:**
- Added `setTaskDecorator` with `ContextSnapshot.captureAll().wrap(runnable)` to ensure MDC context propagates to all async threads spawned by this executor.

---

## QUICK COMPLIANCE CHECKLIST

| Rule | PaymentControllerImpl | CreatePaymentServiceImpl | AsyncConfig |
|---|---|---|---|
| Controller START/END logs present | FAIL | N/A | N/A |
| No PII in logs (email, card number) | FAIL | PASS | N/A |
| No method entry/exit noise in service | N/A | FAIL | N/A |
| Business milestone logs have identifying context | N/A | FAIL | N/A |
| `log.error()` includes exception as last arg | N/A | N/A | N/A |
| Async executor has MDC TaskDecorator | N/A | N/A | FAIL |

---

## SUMMARY TABLE

| # | Severity | Category | File | Description |
|---|---|---|---|---|
| 1 | CRITICAL | SECURITY | PaymentControllerImpl.java | Full card number (PAN) and email logged in plain text |
| 2 | CRITICAL | FORMAT | PaymentControllerImpl.java | Missing mandatory START/END log pattern in HTTP controller |
| 3 | WARNING | NOISE | CreatePaymentServiceImpl.java | Method entry log forbidden in service layer; business log lacks identifying context |
| 4 | CRITICAL | ARCHITECTURE | AsyncConfig.java | ThreadPoolTaskExecutor missing MDC TaskDecorator — trace correlation broken in CloudWatch |

**This diff must not be merged until violations [1], [2], and [4] are resolved. Violation [3] must also be addressed before merge.**
