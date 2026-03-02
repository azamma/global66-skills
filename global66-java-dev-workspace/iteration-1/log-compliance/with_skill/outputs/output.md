COMPLIANCE SUMMARY
──────────────────
Compliant: false
Violations: 4
Risk Level: HIGH

VIOLATIONS
──────────

[1] CRITICAL · SECURITY · PaymentControllerImpl.java
    Code: log.info("Processing payment for user: email={}, cardNumber={}, amount={}",
              request.getEmail(), request.getCardNumber(), request.getAmount())
    Issue: Full email address and full card number (PAN) are being logged. This violates
           SGSI-POL-005 — PII and financial data must never appear in plain text in logs.
           Full card numbers are strictly forbidden; only last four digits are permitted
           via MaskingPatternLayout. Full email addresses must be masked in bulk/financial flows.
    Fix:   log.info("START - [POST] [/payments]: lastFourDigits={}, amount={}",
               maskLastFour(request.getCardNumber()), request.getAmount())

[2] CRITICAL · FORMAT · PaymentControllerImpl.java
    Code: log.info("Processing payment for user: email={}, cardNumber={}, amount={}", ...)
    Issue: Controller entry point is missing the mandatory START/END log pattern required
           by SGSI-POL-005. Every public HTTP controller method must open with
           log.info("START - [METHOD] [/path]: {}", id) and close with
           log.info("END - [METHOD] [/path]") bracketing the business call.
           Neither the required START format nor any END log is present.
    Fix:   Add START log before the service call and END log before returning the response:
               log.info("START - [POST] [/payments]: amount={}", request.getAmount());
               PaymentResponse response = PaymentPresentationMapper.INSTANCE.toResponse(
                   createPaymentService.create(PaymentPresentationMapper.INSTANCE.toData(request)));
               log.info("END - [POST] [/payments]");
               return response;

[3] WARNING · NOISE · CreatePaymentServiceImpl.java
    Code: log.info("Entering createPayment service method")
    Issue: Method entry/exit logs in the business layer are explicitly forbidden noise
           under SGSI-POL-005. The rule states: "If the log would appear on every request
           regardless of what happened, it's noise." Service layer logs must represent
           meaningful business milestones only (state changes, significant events).
           "Entering createPayment service method" carries no diagnostic value.
    Fix:   Remove this line entirely.

[4] CRITICAL · ARCHITECTURE · AsyncConfig.java
    Code: ThreadPoolTaskExecutor created without a task decorator — executor.initialize()
          called directly with no call to executor.setTaskDecorator(...)
    Issue: Without the ContextSnapshot task decorator, MDC context (X-Amzn-Request-Id,
           traceId, spanId) is silently dropped when work is dispatched to async threads.
           This breaks CloudWatch trace correlation for all async operations using this
           executor. SGSI-POL-005 requires that all async executors propagate MDC via
           ContextSnapshot.captureAll().wrap(runnable).
    Fix:   executor.setTaskDecorator(runnable ->
               ContextSnapshot.captureAll().wrap(runnable));
           Add this line before executor.initialize().

CORRECTED CODE
──────────────

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

### CreatePaymentServiceImpl.java

```java
@Override
@Transactional(rollbackFor = Exception.class)
public PaymentData create(PaymentData paymentData) {
    ensureUserHasSufficientBalance(paymentData);
    PaymentData saved = paymentPersistence.save(paymentData);
    log.info("Payment saved successfully");
    return saved;
}
```

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

VIOLATION SUMMARY TABLE
───────────────────────
| # | Severity | Category     | File                          | Rule                                      |
|---|----------|--------------|-------------------------------|-------------------------------------------|
| 1 | CRITICAL | SECURITY     | PaymentControllerImpl.java    | PAN and email logged in plain text        |
| 2 | CRITICAL | FORMAT       | PaymentControllerImpl.java    | Missing START/END log pattern             |
| 3 | WARNING  | NOISE        | CreatePaymentServiceImpl.java | Method entry log forbidden in service     |
| 4 | CRITICAL | ARCHITECTURE | AsyncConfig.java              | Missing ContextSnapshot task decorator    |

ACTION REQUIRED
───────────────
Violations [1], [2], and [4] are CRITICAL and must be resolved before merging.
Violation [3] is a WARNING and should be resolved in the same PR.
