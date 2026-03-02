# @Transactional — Rules & Audit Guide

## Layer Rule (non-negotiable)

`@Transactional` belongs **exclusively in the Business layer** (`business/` / `*ServiceImpl`).

| Layer | Allowed? |
|-------|----------|
| `@Service` / `*ServiceImpl` | ✅ Yes |
| `@Component` / `*PersistenceImpl` | ❌ No |
| `@Repository` | ❌ No — JPA manages its own transactions |
| `@RestController` / `*ControllerImpl` | ❌ No |
| `*ClientImpl` (Retrofit) | ❌ No |
| Interface methods | ❌ No — Spring AOP applies to concrete classes |

If `@Transactional` appears in a prohibited layer, **fail the audit immediately**.

---

## Validation Rules

### TX_PUBLIC_ONLY — Method must be `public`
Spring creates a proxy that wraps the bean. If the annotated method is `private` or `protected`,
the proxy cannot intercept it — the transaction is **silently ignored**.

```java
// VIOLATION: private method
@Transactional(rollbackFor = Exception.class)
private void saveInternal() { ... }

// FIX: make it public, or call it from a public @Transactional method
@Transactional(rollbackFor = Exception.class)
public void save() { ... }
```

### TX_ROLLBACK_POLICY — Always `rollbackFor = Exception.class`
Spring's default only rolls back for `RuntimeException` and `Error`. Checked exceptions
(e.g. `IOException`, custom checked exceptions) will **commit the transaction** unless explicitly configured.

```java
// VIOLATION: default rollback policy
@Transactional
public void processPayment(PaymentData data) { ... }

// FIX: explicit rollback for all exceptions
@Transactional(rollbackFor = Exception.class)
public void processPayment(PaymentData data) { ... }
```

Exception: `@Transactional(readOnly = true)` on finder methods is fine without `rollbackFor`
because read-only transactions don't modify state.

### TX_NO_EXTERNAL_CALLS — No HTTP/REST client calls inside `@Transactional`
An active transaction holds a database connection from the pool. An external HTTP call can
take seconds (or fail). During that time the DB connection is blocked, leading to **connection
pool exhaustion** under load.

```java
// VIOLATION: HTTP client call inside transaction
@Transactional(rollbackFor = Exception.class)
public PaymentData createPayment(PaymentData data) {
    PaymentData saved = paymentPersistence.save(data);
    externalPaymentClient.notifyBank(saved); // ← DB connection held during HTTP call
    return saved;
}

// FIX: orchestrate at a higher level without @Transactional
public PaymentData createPayment(PaymentData data) {
    PaymentData saved = savePaymentTransactionally(data);    // @Transactional
    externalPaymentClient.notifyBank(saved);                  // outside transaction
    return saved;
}

@Transactional(rollbackFor = Exception.class)
public PaymentData savePaymentTransactionally(PaymentData data) {
    return paymentPersistence.save(data);
}
```

### TX_SELF_INVOCATION — No internal calls to `@Transactional` methods in the same bean
Spring's `@Transactional` works through a proxy. Calling `this.method()` or just `method()`
from within the same class bypasses the proxy entirely — the transaction annotation is **ignored**.

```java
// VIOLATION: self-invocation
@Service
public class PaymentServiceImpl {

    @Transactional(rollbackFor = Exception.class)
    public void createPayment(PaymentData data) {
        validateAndSave(data);        // ← calls same class, proxy bypassed
    }

    @Transactional(rollbackFor = Exception.class)
    private void validateAndSave(PaymentData data) { ... }  // never executes in a transaction
}

// FIX: extract to a separate Spring bean, or restructure so only the entry method is @Transactional
```

### TX_READ_ONLY — Finder methods must use `readOnly = true`
`@Transactional(readOnly = true)` tells Hibernate to skip dirty-checking (no flush before
queries). This is a meaningful performance optimization for read-heavy services.

```java
// VIOLATION: missing readOnly on a finder
@Transactional(rollbackFor = Exception.class)
public Optional<PaymentData> findById(Integer id) {
    return paymentPersistence.findById(id);
}

// FIX
@Transactional(readOnly = true)
public Optional<PaymentData> findById(Integer id) {
    return paymentPersistence.findById(id);
}
```

Naming signal: methods starting with `find*`, `fetch*`, `get*`, `list*`, `search*` are candidates
for `readOnly = true`.

### TX_STREAM_SAFETY — `Stream<?>` return closes transaction before data is consumed
When a method annotated with `@Transactional` returns a `Stream<Entity>` or a lazy JPA collection,
the transaction (and the DB cursor) closes at the method boundary. The caller then iterates the
stream **after** the transaction is gone — causing `LazyInitializationException`.

```java
// VIOLATION
@Transactional
public Stream<PaymentData> streamPayments() {
    return paymentRepository.streamAll().map(mapper::toData);
}

// FIX option 1: collect to a List before returning (closes stream inside transaction)
@Transactional(readOnly = true)
public List<PaymentData> findAllPayments() {
    return paymentRepository.streamAll()
        .map(mapper::toData)
        .collect(Collectors.toList());
}

// FIX option 2: use a @Transactional(propagation = Propagation.REQUIRED) on the caller too
```

---

## Propagation Guidance

Use the default `Propagation.REQUIRED` in almost all cases. Exceptions:

| Propagation | When to use |
|-------------|-------------|
| `REQUIRED` (default) | Standard write operations |
| `REQUIRES_NEW` | Audit logging, outbox patterns — must commit independently |
| `NOT_SUPPORTED` | Explicit opt-out (rarely needed) |
| `NEVER` | Assert that no transaction is active (test utilities) |

**NESTED is NOT supported by JPA/Hibernate.** If you need isolation, use `REQUIRES_NEW`.

---

## Audit Workflow (git diff)

When a user provides a git diff for `@Transactional` review:

1. **Parse** — identify all modified/added methods with `@Transactional` and their classes
2. **Layer check** — is the annotation on a prohibited layer? → immediate CRITICAL
3. **Proxy check** — is the method `public`? any `this.method()` self-invocations?
4. **Safety check** — any HTTP client calls inside the block? `rollbackFor` present? returning `Stream`?
5. **readOnly check** — does the method name suggest a read-only operation without `readOnly = true`?
6. **Report** — list violations with severity, fix, and architectural score

---

## Output Format

```
## @Transactional Audit

| Rule | Method | Severity | Violation |
|------|--------|----------|-----------|
| TX_ROLLBACK_POLICY | createPayment | CRITICAL | Missing rollbackFor = Exception.class |
| TX_NO_EXTERNAL_CALLS | createPayment | CRITICAL | externalClient.notifyBank() called inside transaction |
| TX_READ_ONLY | findById | WARNING | readOnly = true missing on finder method |

**Architectural score: 45/100**

### CRITICAL — createPayment

**Violation:** HTTP client call inside transaction + missing rollbackFor
**Fix:**
\`\`\`java
// Split into two methods:
public PaymentData createPayment(PaymentData data) {
    PaymentData saved = savePaymentTransactionally(data);
    externalClient.notifyBank(saved);
    return saved;
}

@Transactional(rollbackFor = Exception.class)
public PaymentData savePaymentTransactionally(PaymentData data) {
    return paymentPersistence.save(data);
}
\`\`\`
**Note:** Holding a DB connection open during an HTTP call is how you kill your connection pool
at 2am on a Friday.
```

Score guide:
- **90–100**: All rules followed, readOnly optimized
- **70–89**: Minor warnings (readOnly missing, etc.)
- **40–69**: At least one CRITICAL violation
- **0–39**: Multiple CRITICALs or prohibited layer usage
