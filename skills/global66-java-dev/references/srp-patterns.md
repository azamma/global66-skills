# SRP & Semantic Method Patterns

In Global66 microservices, we follow a strict SRP (Single Responsibility Principle) pattern.
Public methods in the business layer should be orchestration-only, while private methods
perform specific actions.

## Core Rule: Descriptive Naming

Method names must clearly state what they do. While specific prefixes are common (ensure, validate, check, fetch), they are **examples**. Use whatever prefix or name makes the code's intent obvious to the reader.

## Common Semantic Prefixes (Examples)

### 1. Precondition Validation (void)
Used to check if an operation can proceed. Throws `ApiRestException` if invalid.
- Examples: `validateEmailIsAvailable`, `ensureUserIsActive`, `checkSufficientBalance`.

### 2. Complex Condition Check (void)
Used for logic that requires multiple steps or data sources.
- Examples: `verifyTransactionRisk`, `checkLimitCompliance`.

### 3. Defensive Guard (void)
Used at the start of a method to prevent processing invalid states.
- Examples: `guardAgainstNullInput`, `stopIfAlreadyProcessed`.

### 4. Boolean Predicates (boolean)
Simple questions about state. Never throw exceptions.
- Examples: `isEligibleForPromo`, `hasPendingOrders`, `canUpdateStatus`.

### 5. Mandatory Retrieval (Domain Object)
Get an object or throw `NOT_FOUND`.
- Examples: `fetchUser`, `requireAccount`, `getMandatoryConfig`.

### 6. Query Retrieval (Optional)
Safe retrieval that might not find anything.
- Examples: `findOptionalConfig`, `getRecentTransaction`.

### 7. Exception Factory (Exception)
Centralize exception construction.
- Examples: `buildUserNotFoundException`, `createConflictException`.

## What to Avoid

- **Generic names**: `processUser`, `handleRequest`, `executeAction`, `validateData`.
- **Logic in public methods**: If-else blocks, null checks, and repository calls belong in private methods or the persistence layer.
- **Ambiguous names**: `checkData` (Does it return a boolean? Does it throw an exception? Be specific).

## Example Implementation

```java
@Override
@Transactional(rollbackFor = Exception.class)
public UserData registerUser(UserData userData) {
    // Intent is clear: we validate, then save, then notify.
    validateEmailIsAvailable(userData.getEmail());
    UserData saved = userPersistence.save(userData);
    sendWelcomeNotification(saved);
    return saved;
}

private void validateEmailIsAvailable(String email) {
    if (userPersistence.existsByEmail(email)) {
        throw ApiRestException.builder()
            .reason(ErrorReason.CONFLICT)
            .source(ErrorSource.BUSINESS_SERVICE)
            .build();
    }
}
```
