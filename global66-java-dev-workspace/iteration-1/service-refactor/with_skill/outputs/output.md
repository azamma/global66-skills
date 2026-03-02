# Service Refactor — Global66 Guidelines

## Anti-Patterns Found in Original Code

| # | Violation | Rule |
|---|-----------|------|
| 1 | `PaymentRepository` and `UserRepository` injected directly into the service | Golden Rule #2: never inject repositories in services — always use `*Persistence` ports |
| 2 | Method named `processPayment` | Forbidden name: `process` — always be specific |
| 3 | `RuntimeException` thrown inline three times | No `RuntimeException` — use `BusinessException(ErrorCode.XXX, ...)` factory methods |
| 4 | All validation, fetching, mapping, and persistence inline in the public method | Public methods must orchestrate only; private methods do one thing |
| 5 | `PaymentEntity` constructed with setters inside the service | Entities must never leave or be built in the business layer; mapping belongs in `persistence/mapper/` via MapStruct |
| 6 | Missing `@Transactional(rollbackFor = Exception.class)` | Every write operation in the business layer requires this annotation |
| 7 | Missing `@Slf4j` | Services with business milestones must log them |
| 8 | Result object (`PaymentData`) constructed with setters inside the service | Mapping to/from domain objects belongs in the mapper, not inline in service methods |
| 9 | No `@Override` + transactional on `processPayment` | Required on every interface implementation in the business layer |
| 10 | 4 injected dependencies (2 repositories instead of 2 persistence ports) | Max 3 injected dependencies per service; direct repos violate the port rule |

---

## Refactored Code

The refactor introduces the full hexagonal slice needed to support `processPayment` correctly.
Each file is placed in its canonical package.

---

### `business/PaymentService.java` — interface

```java
package com.global.payment.business;

import com.global.payment.domain.data.PaymentData;

public interface PaymentService {
    PaymentData registerPayment(PaymentData payment);
}
```

> Renamed from `processPayment` to `registerPayment` — "process" is a forbidden generic verb.
> The interface lives in `business/`, not in a sub-package.

---

### `business/impl/PaymentServiceImpl.java` — implementation

```java
package com.global.payment.business.impl;

import com.global.payment.business.PaymentService;
import com.global.payment.domain.data.PaymentData;
import com.global.payment.persistence.PaymentPersistence;
import com.global.payment.persistence.UserPersistence;
import com.global.rest.exception.BusinessException;
import com.global.rest.exception.ErrorCode;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Slf4j
@Service
@RequiredArgsConstructor
public class PaymentServiceImpl implements PaymentService {

    private final PaymentPersistence paymentPersistence;
    private final UserPersistence userPersistence;

    @Override
    @Transactional(rollbackFor = Exception.class)
    public PaymentData registerPayment(PaymentData payment) {
        UserData user = fetchUserOrThrow(payment.getUserId());
        ensureSufficientBalance(user, payment.getAmount());
        guardAgainstDuplicateTransaction(payment.getTransactionId());
        PaymentData saved = paymentPersistence.save(payment);
        log.info("Payment registered successfully: transactionId={}", saved.getTransactionId());
        return saved;
    }

    // -------------------------------------------------------------------------
    // Fetch helpers
    // -------------------------------------------------------------------------

    private UserData fetchUserOrThrow(Integer userId) {
        return userPersistence.findById(userId)
                .orElseThrow(() -> userNotFoundException(userId));
    }

    // -------------------------------------------------------------------------
    // Precondition guards
    // -------------------------------------------------------------------------

    private void ensureSufficientBalance(UserData user, java.math.BigDecimal amount) {
        if (isBalanceInsufficient(user.getBalance(), amount)) {
            throw insufficientBalanceException(user.getId());
        }
    }

    private void guardAgainstDuplicateTransaction(String transactionId) {
        if (paymentPersistence.existsByTransactionId(transactionId)) {
            throw duplicateTransactionException(transactionId);
        }
    }

    // -------------------------------------------------------------------------
    // Boolean predicates
    // -------------------------------------------------------------------------

    private boolean isBalanceInsufficient(java.math.BigDecimal balance, java.math.BigDecimal amount) {
        return balance.compareTo(amount) < 0;
    }

    // -------------------------------------------------------------------------
    // Exception factories
    // -------------------------------------------------------------------------

    private BusinessException userNotFoundException(Integer userId) {
        return new BusinessException(ErrorCode.USER_NOT_FOUND, userId.toString());
    }

    private BusinessException insufficientBalanceException(Integer userId) {
        return new BusinessException(ErrorCode.INSUFFICIENT_BALANCE, userId.toString());
    }

    private BusinessException duplicateTransactionException(String transactionId) {
        return new BusinessException(ErrorCode.DUPLICATE_TRANSACTION, transactionId);
    }
}
```

---

### `persistence/UserPersistence.java` — port interface

```java
package com.global.payment.persistence;

import com.global.payment.domain.data.UserData;

import java.util.Optional;

public interface UserPersistence {
    Optional<UserData> findById(Integer userId);
}
```

---

### `persistence/impl/UserPersistenceImpl.java` — port implementation

```java
package com.global.payment.persistence.impl;

import com.global.payment.domain.data.UserData;
import com.global.payment.persistence.UserPersistence;
import com.global.payment.persistence.mapper.UserMapper;
import com.global.payment.persistence.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Component;

import java.util.Optional;

@Component
@RequiredArgsConstructor
public class UserPersistenceImpl implements UserPersistence {

    private final UserRepository userRepository;

    @Override
    public Optional<UserData> findById(Integer userId) {
        return userRepository.findById(userId)
                .map(UserMapper.INSTANCE::toData);
    }
}
```

---

### `persistence/PaymentPersistence.java` — port interface

```java
package com.global.payment.persistence;

import com.global.payment.domain.data.PaymentData;

public interface PaymentPersistence {
    PaymentData save(PaymentData payment);
    boolean existsByTransactionId(String transactionId);
}
```

---

### `persistence/impl/PaymentPersistenceImpl.java` — port implementation

```java
package com.global.payment.persistence.impl;

import com.global.payment.domain.data.PaymentData;
import com.global.payment.persistence.PaymentPersistence;
import com.global.payment.persistence.mapper.PaymentMapper;
import com.global.payment.persistence.repository.PaymentRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Component;

@Component
@RequiredArgsConstructor
public class PaymentPersistenceImpl implements PaymentPersistence {

    private final PaymentRepository paymentRepository;

    @Override
    public PaymentData save(PaymentData payment) {
        return PaymentMapper.INSTANCE.toData(
                paymentRepository.save(PaymentMapper.INSTANCE.toEntity(payment)));
    }

    @Override
    public boolean existsByTransactionId(String transactionId) {
        return paymentRepository.existsByTransactionId(transactionId);
    }
}
```

---

### `persistence/mapper/PaymentMapper.java` — MapStruct mapper

```java
package com.global.payment.persistence.mapper;

import com.global.payment.domain.data.PaymentData;
import com.global.payment.persistence.entity.PaymentEntity;
import org.mapstruct.Mapper;
import org.mapstruct.Mapping;
import org.mapstruct.NullValueCheckStrategy;
import org.mapstruct.NullValuePropertyMappingStrategy;
import org.mapstruct.factory.Mappers;

@Mapper(
        componentModel = "default",
        nullValueCheckStrategy = NullValueCheckStrategy.ALWAYS,
        nullValuePropertyMappingStrategy = NullValuePropertyMappingStrategy.IGNORE)
public interface PaymentMapper {

    PaymentMapper INSTANCE = Mappers.getMapper(PaymentMapper.class);

    @Mapping(target = "status", constant = "PENDING")
    PaymentEntity toEntity(PaymentData payment);

    PaymentData toData(PaymentEntity entity);
}
```

> The `status = "PENDING"` default is set in the mapper via `@Mapping(target = "status", constant = "PENDING")`,
> keeping the business layer free of persistence-level concerns.

---

### `persistence/mapper/UserMapper.java` — MapStruct mapper

```java
package com.global.payment.persistence.mapper;

import com.global.payment.domain.data.UserData;
import com.global.payment.persistence.entity.UserEntity;
import org.mapstruct.Mapper;
import org.mapstruct.NullValueCheckStrategy;
import org.mapstruct.NullValuePropertyMappingStrategy;
import org.mapstruct.factory.Mappers;

@Mapper(
        componentModel = "default",
        nullValueCheckStrategy = NullValueCheckStrategy.ALWAYS,
        nullValuePropertyMappingStrategy = NullValuePropertyMappingStrategy.IGNORE)
public interface UserMapper {

    UserMapper INSTANCE = Mappers.getMapper(UserMapper.class);

    UserData toData(UserEntity entity);

    UserEntity toEntity(UserData userData);
}
```

---

### `domain/data/UserData.java` — domain object

```java
package com.global.payment.domain.data;

import lombok.Data;

import java.math.BigDecimal;

@Data
public class UserData {
    private Integer id;
    private BigDecimal balance;
}
```

---

### `domain/data/PaymentData.java` — domain object

```java
package com.global.payment.domain.data;

import lombok.Data;

import java.math.BigDecimal;

@Data
public class PaymentData {
    private Integer id;
    private Integer userId;
    private BigDecimal amount;
    private String transactionId;
    private String status;
}
```

---

## Summary of Changes

| Area | Before | After |
|------|--------|-------|
| Method name | `processPayment` | `registerPayment` |
| Repositories in service | `PaymentRepository`, `UserRepository` injected directly | `PaymentPersistence`, `UserPersistence` ports injected |
| Validation logic | Inline `if` blocks inside public method | `ensureSufficientBalance`, `guardAgainstDuplicateTransaction` private methods |
| User fetch | `Optional.isPresent()` + `get()` inline | `fetchUserOrThrow` private method using `.orElseThrow()` |
| Exception construction | `throw new RuntimeException("...")` × 3 | Exception factory methods: `userNotFoundException`, `insufficientBalanceException`, `duplicateTransactionException` |
| Exception type | `RuntimeException` | `BusinessException(ErrorCode.XXX, ...)` |
| Entity construction | Inline setters in business layer | MapStruct `PaymentMapper.INSTANCE.toEntity(payment)` in persistence layer |
| Result mapping | Inline setters in business layer | MapStruct `PaymentMapper.INSTANCE.toData(entity)` in persistence layer |
| `status = "PENDING"` | Hard-coded setter in business layer | `@Mapping(target = "status", constant = "PENDING")` in mapper |
| `@Transactional` | Missing | `@Transactional(rollbackFor = Exception.class)` on public write method |
| Logging | None | `log.info("Payment registered successfully: transactionId={}", ...)` — business milestone only |
| Nesting depth | 2–3 levels inline | Max 1 in public method, max 1 in each private method |
