# SRP & Semantic Method Patterns — Global66

## Why This Matters

Every method should have exactly one reason to change. When you name a method well and keep it
small, the code reads like a story: the public method tells you *what* happens, the private
methods tell you *how* each step works.

This is not about following rules mechanically — it's about writing code that a new engineer
can understand at a glance without comments.

## Semantic Prefix Guide

### `ensure*` — Precondition validation
Checks a condition that MUST be true before proceeding. Throws an exception if not.
```java
private void ensureAccountIsActive(AccountData account) {
    if (isAccountInactive(account)) {
        throw accountNotActiveException(account.getId());
    }
}
```

### `verify*` — Complex multi-step validation
Use when the validation involves multiple checks or more complex logic than a single condition.
```java
private void verifyTransferEligibility(TransferData transfer) {
    ensureSufficientBalance(transfer);
    ensureDestinationIsReachable(transfer.getDestinationCountry());
    ensureDailyLimitNotExceeded(transfer);
}
```

### `guardAgainst*` — Defensive check
Protects against unexpected or dangerous states.
```java
private void guardAgainstDuplicateTransaction(String transactionId) {
    if (transactionPersistence.existsByTransactionId(transactionId)) {
        throw duplicateTransactionException(transactionId);
    }
}
```

### `is*` / `has*` — Boolean predicates
Pure query — no side effects, no exceptions. Returns true/false only.
```java
private boolean isAccountReassignment(DevicePermissionData existing, DevicePermissionData incoming) {
    return !existing.getUserId().equals(incoming.getUserId());
}

private boolean hasExceededDailyLimit(BigDecimal amount, BigDecimal dailyUsed) {
    return amount.add(dailyUsed).compareTo(DAILY_LIMIT) > 0;
}
```

### `fetch*` / `require*` — Get or throw NOT_FOUND
Fetches a domain object from persistence. Throws NOT_FOUND exception if absent.
```java
private UserData fetchUserOrThrow(Integer userId) {
    return userPersistence.findById(userId)
        .orElseThrow(() -> userNotFoundException(userId));
}
```

### `find*` — Query that returns Optional
Direct persistence query, returns Optional. Never throws. Used inside `fetch*` or in specific
query flows where absence is a valid outcome.
```java
// In persistence layer
Optional<UserData> findByEmail(String email);
```

### `build*Exception` — Exception factory methods
Creates a specific exception. Keeps throw sites clean and centralizes error construction.
```java
private BusinessException userNotFoundException(Integer userId) {
    return new BusinessException(ErrorCode.USER_NOT_FOUND, userId.toString());
}

private BusinessException accountNotActiveException(Integer accountId) {
    return new BusinessException(ErrorCode.ACCOUNT_NOT_ACTIVE, accountId.toString());
}
```

---

## Public Method Structure (Template Method Pattern)

Public methods should read as an ordered list of steps. Think of them as the table of contents
for the operation:

```
Step 1: Validate preconditions
Step 2: Fetch existing state (for updates)
Step 3: Check if change is significant
Step 4: Persist
Step 5: Notify / emit events
```

```java
// BAD: public method doing everything inline
@Transactional(rollbackFor = Exception.class)
public DevicePermissionData updateDevicePermission(Integer userId, DevicePermissionData incoming) {
    DevicePermissionEntity existing = deviceRepository.findByUserId(userId)
        .orElseThrow(() -> new RuntimeException("Not found"));

    if (!existing.getUserId().equals(incoming.getUserId())) {
        existing.setUserId(incoming.getUserId());
        existing.setStatus(incoming.getStatus());
    } else if (incoming.getPermissionType() != null) {
        existing.setPermissionType(incoming.getPermissionType());
    }
    return DevicePermissionMapper.INSTANCE.toData(deviceRepository.save(existing));
}
```

```java
// GOOD: public method orchestrates, private methods do the work
@Transactional(rollbackFor = Exception.class)
public DevicePermissionData updateDevicePermission(Integer userId, DevicePermissionData incoming) {
    DevicePermissionData existing = fetchPermissionOrThrow(userId);
    if (isAccountReassignment(existing, incoming)) {
        return devicePermissionPersistence.save(mergeReassignment(existing, incoming));
    }
    return devicePermissionPersistence.save(mergePermissionUpdate(existing, incoming));
}

private DevicePermissionData fetchPermissionOrThrow(Integer userId) {
    return devicePermissionPersistence.findByUserId(userId)
        .orElseThrow(() -> permissionNotFoundException(userId));
}

private boolean isAccountReassignment(DevicePermissionData existing, DevicePermissionData incoming) {
    return !existing.getUserId().equals(incoming.getUserId());
}

private DevicePermissionData mergeReassignment(DevicePermissionData existing,
                                                DevicePermissionData incoming) {
    existing.setUserId(incoming.getUserId());
    existing.setStatus(incoming.getStatus());
    return existing;
}

private DevicePermissionData mergePermissionUpdate(DevicePermissionData existing,
                                                    DevicePermissionData incoming) {
    existing.setPermissionType(incoming.getPermissionType());
    return existing;
}

private BusinessException permissionNotFoundException(Integer userId) {
    return new BusinessException(ErrorCode.PERMISSION_NOT_FOUND, userId.toString());
}
```

---

## Anti-Pattern Catalog

### Forbidden: Generic method names
```java
// BAD
private void process(UserData data) { ... }
private void handle(Exception e) { ... }
private void validate(String value) { ... }
private boolean check(AccountData account) { ... }

// GOOD
private void ensureEmailIsUnique(String email) { ... }
private void guardAgainstExpiredSession(SessionData session) { ... }
private boolean isEmailAlreadyRegistered(String email) { ... }
```

### Forbidden: Inline boolean conditions
```java
// BAD
if (!userRepository.findByEmail(email).isPresent()) {
    throw new RuntimeException("User not found");
}

// GOOD
private void ensureUserExistsByEmail(String email) {
    if (isEmailNotRegistered(email)) {
        throw userNotFoundByEmailException(email);
    }
}

private boolean isEmailNotRegistered(String email) {
    return !userPersistence.existsByEmail(email);
}
```

### Forbidden: Inline exception construction
```java
// BAD
throw new BusinessException(ErrorCode.USER_NOT_FOUND, userId.toString());

// GOOD
throw userNotFoundException(userId);

private BusinessException userNotFoundException(Integer userId) {
    return new BusinessException(ErrorCode.USER_NOT_FOUND, userId.toString());
}
```

### Forbidden: Business logic in lambda
```java
// BAD
userPersistence.findById(userId)
    .ifPresent(user -> {
        user.setStatus(UserStatus.ACTIVE);
        if (user.getEmail() != null) {
            notificationService.sendWelcome(user.getEmail());
        }
        userPersistence.save(user);
    });

// GOOD
UserData user = fetchUserOrThrow(userId);
activateUser(user);
notifyUserWelcome(user);
```

---

## SRP Checklist

Before committing a method, ask:
- Does the name describe EXACTLY one action? (no "and"/"or" in the name)
- Would a new team member understand what it does without reading the body?
- Does it have exactly ONE reason to change?
- Is it clearly one of: Validation, Query, Fetch, Orchestration, or Factory?
- Is the nesting depth ≤ 2?
- Are there ≤ 4 parameters?
