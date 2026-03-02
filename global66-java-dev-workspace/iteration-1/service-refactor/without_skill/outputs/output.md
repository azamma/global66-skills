# Refactored PaymentServiceImpl

## Issues Identified in Original Code

1. **Generic RuntimeException** — loses semantic meaning, hard to handle upstream.
2. **God method** — `processPayment` does user validation, balance check, duplicate check, entity mapping, and persistence all in one method (SRP violation).
3. **Manual entity/DTO mapping** — inline `new PaymentEntity()` and `new PaymentData()` construction with manual field setters scattered in business logic.
4. **Magic string literal** — `"PENDING"` hardcoded without a type-safe enum.
5. **`Optional` anti-pattern** — calling `.isPresent()` + `.get()` instead of using `.orElseThrow()`.
6. **No separation of validation concerns** — all guard clauses live inside the service method, making it impossible to reuse or test them independently.

---

## Refactored Code

### 1. PaymentStatus enum

```java
public enum PaymentStatus {
    PENDING,
    COMPLETED,
    FAILED
}
```

---

### 2. Domain exceptions (one class per business rule)

```java
public class UserNotFoundException extends RuntimeException {
    public UserNotFoundException(Long userId) {
        super("User not found: " + userId);
    }
}

public class InsufficientBalanceException extends RuntimeException {
    public InsufficientBalanceException() {
        super("Insufficient balance for the requested payment amount");
    }
}

public class DuplicateTransactionException extends RuntimeException {
    public DuplicateTransactionException(String transactionId) {
        super("Transaction already exists: " + transactionId);
    }
}
```

---

### 3. PaymentValidator (Single Responsibility — validation only)

```java
@Component
@RequiredArgsConstructor
public class PaymentValidator {

    private final UserRepository userRepository;
    private final PaymentRepository paymentRepository;

    public UserEntity ensureUserExists(Long userId) {
        return userRepository.findById(userId)
                .orElseThrow(() -> new UserNotFoundException(userId));
    }

    public void verifyUserHasSufficientBalance(UserEntity user, BigDecimal amount) {
        if (user.getBalance().compareTo(amount) < 0) {
            throw new InsufficientBalanceException();
        }
    }

    public void verifyTransactionIsNotDuplicate(String transactionId) {
        if (paymentRepository.existsByTransactionId(transactionId)) {
            throw new DuplicateTransactionException(transactionId);
        }
    }
}
```

---

### 4. PaymentMapper (Single Responsibility — mapping only)

```java
@Component
public class PaymentMapper {

    public PaymentEntity toEntity(PaymentData payment) {
        PaymentEntity entity = new PaymentEntity();
        entity.setUserId(payment.getUserId());
        entity.setAmount(payment.getAmount());
        entity.setTransactionId(payment.getTransactionId());
        entity.setStatus(PaymentStatus.PENDING.name());
        return entity;
    }

    public PaymentData toData(PaymentEntity entity) {
        PaymentData result = new PaymentData();
        result.setId(entity.getId());
        result.setStatus(entity.getStatus());
        return result;
    }
}
```

---

### 5. Refactored PaymentServiceImpl

```java
@Slf4j
@Service
@RequiredArgsConstructor
public class PaymentServiceImpl implements PaymentService {

    private final PaymentRepository paymentRepository;
    private final PaymentValidator paymentValidator;
    private final PaymentMapper paymentMapper;

    @Override
    public PaymentData processPayment(PaymentData payment) {
        UserEntity user = paymentValidator.ensureUserExists(payment.getUserId());
        paymentValidator.verifyUserHasSufficientBalance(user, payment.getAmount());
        paymentValidator.verifyTransactionIsNotDuplicate(payment.getTransactionId());

        PaymentEntity entity = paymentMapper.toEntity(payment);
        PaymentEntity saved = paymentRepository.save(entity);

        return paymentMapper.toData(saved);
    }
}
```

---

## Summary of Changes

| Problem | Fix Applied |
|---|---|
| Generic `RuntimeException` | Three typed domain exceptions: `UserNotFoundException`, `InsufficientBalanceException`, `DuplicateTransactionException` |
| God method (SRP violation) | Validation extracted to `PaymentValidator`; mapping extracted to `PaymentMapper` |
| Manual entity/DTO construction inside service | Moved to `PaymentMapper`, keeping the service free of mapping concerns |
| Magic string `"PENDING"` | Replaced with `PaymentStatus.PENDING.name()` backed by a type-safe enum |
| `Optional.isPresent()` + `.get()` anti-pattern | Replaced with `.orElseThrow()` |
| `UserRepository` injected into service | Moved to `PaymentValidator`; service now has no direct dependency on `UserRepository` |

## SOLID Principles Applied

- **S — Single Responsibility**: `PaymentServiceImpl` orchestrates only; `PaymentValidator` validates only; `PaymentMapper` maps only.
- **O — Open/Closed**: New validation rules can be added to `PaymentValidator` without touching the service.
- **L — Liskov Substitution**: `PaymentServiceImpl` correctly implements the `PaymentService` contract without strengthening preconditions.
- **I — Interface Segregation**: Each collaborator (`PaymentValidator`, `PaymentMapper`) exposes only the methods the service needs.
- **D — Dependency Inversion**: `PaymentServiceImpl` depends on abstractions (`PaymentService` interface) and injected collaborators, not on concrete infrastructure details.
