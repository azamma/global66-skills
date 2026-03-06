# Global66 Exception Handling Guidelines

Guidelines for throwing and handling exceptions in Global66 microservices using the `com.global.rest.exception` library.

## Overview

All exceptions must be thrown using the `ApiRestException` builder pattern with standardized `ErrorReason` and `ErrorSource` enums from the shared library.

## Basic Exception Pattern

```java
import com.global.rest.exception.ApiRestException;
import com.global.rest.exception.enums.ErrorReason;
import com.global.rest.exception.enums.ErrorSource;

// Standard exception throwing
throw ApiRestException.builder()
    .reason(ErrorReason.NOT_FOUND)
    .source(ErrorSource.BUSINESS_SERVICE)
    .build();
```

## Available ErrorSource Values

| Source | Description | Use Case |
|--------|-------------|----------|
| `BUSINESS_SERVICE` | Business service has failed | Business logic failures, validations |
| `DATA_REPOSITORY` | Data repository has failed | Database operations, JPA errors |
| `REST_CONTROLLER` | REST controller has failed | Request validation, mapping errors |
| `ADAPTER_COMPONENT` | Component's adapter has failed | External service adapters |
| `ADAPTER_JUMIO` | Jumio's adapter has failed | Jumio integration errors |
| `ADAPTER_TRUORA` | Truora's adapter has failed | Truora integration errors |
| `UTILS` | The utility has failed | Utility class errors |
| `HELPER_COMPONENT` | The component's helper has failed | Helper method errors |
| `HTTP_CLIENT_COMPONENT` | Component's HTTP client has failed | Generic HTTP client errors |
| `HTTP_CLIENT_JUMIO` | Jumio's HTTP client has failed | Jumio HTTP errors |
| `HTTP_CLIENT_TRUORA` | Truora's HTTP client has failed | Truora HTTP errors |
| `HTTP_CLIENT_IBAN` | Iban's HTTP client has failed | IBAN HTTP errors |
| `COGNITO_SERVICE` | Cognito service has failed | AWS Cognito errors |
| `ITERABLE_SERVICE` | Iterable service has failed | Iterable integration errors |
| `UNKNOWN_SOURCE` | Unknown error source | Fallback for uncategorized errors |

## Common ErrorReason Values

### 4xx Client Errors

| Reason | HTTP Status | Use Case |
|--------|-------------|----------|
| `BAD_REQUEST` | 400 | Invalid request format |
| `UNAUTHORIZED` | 401 | Authentication required/failed |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `CONFLICT` | 409 | Resource conflict |
| `GONE` | 410 | Resource no longer available |
| `UNPROCESSABLE_ENTITY` | 422 | Semantic validation errors |
| `TOO_MANY_REQUESTS` | 429 | Rate limit exceeded |

### 5xx Server Errors

| Reason | HTTP Status | Use Case |
|--------|-------------|----------|
| `INTERNAL_SERVER_ERROR` | 500 | Unexpected server error |
| `SERVICE_UNAVAILABLE` | 503 | Service temporarily unavailable |
| `GATEWAY_TIMEOUT` | 504 | Upstream timeout |

### Domain-Specific Errors

| Reason | Use Case |
|--------|----------|
| `CUSTOMER_NOT_FOUND` | Customer entity not found |
| `TRANSACTION_NOT_FOUND` | Transaction entity not found |
| `TRANSACTION_CUSTOMER_BLOCKED` | Customer blocked for transactions |
| `TRANSACTION_LIMIT_EXCEEDED` | Transaction limit reached |
| `INSUFFICIENT_BALANCE` | Account balance insufficient |
| `ACCOUNT_NOT_FOUND` | Account entity not found |
| `BENEFICIARY_NOT_FOUND` | Beneficiary not found |
| `PROMOTION_NOT_FOUND` | Promotion not found |
| `PROMOTION_EXPIRED` | Promotion no longer valid |
| `QUOTE_NOT_FOUND` | Quote not found |
| `QUOTE_EXPIRED` | Quote no longer valid |

## Examples by Layer

### Business Layer

```java
@Service
@RequiredArgsConstructor
public class CustomerServiceImpl implements CustomerService {

    @Override
    public CustomerData getCustomerById(Long id) {
        return customerRepository.findById(id)
            .map(customerMapper::toData)
            .orElseThrow(() -> ApiRestException.builder()
                .reason(ErrorReason.CUSTOMER_NOT_FOUND)
                .source(ErrorSource.BUSINESS_SERVICE)
                .build());
    }

    @Override
    public void ensureCustomerIsActive(Long customerId) {
        CustomerEntity customer = customerRepository.findById(customerId)
            .orElseThrow(() -> ApiRestException.builder()
                .reason(ErrorReason.CUSTOMER_NOT_FOUND)
                .source(ErrorSource.BUSINESS_SERVICE)
                .build());

        if (!customer.isActive()) {
            throw ApiRestException.builder()
                .reason(ErrorReason.CUSTOMER_NOT_ENABLED)
                .source(ErrorSource.BUSINESS_SERVICE)
                .build();
        }
    }

    @Override
    public void ensureTransactionLimitNotExceeded(Long customerId, BigDecimal amount) {
        if (isLimitExceeded(customerId, amount)) {
            throw ApiRestException.builder()
                .reason(ErrorReason.TRANSACTION_LIMIT_EXCEEDED)
                .source(ErrorSource.BUSINESS_SERVICE)
                .build();
        }
    }
}
```

### Persistence Layer

```java
@Repository
@RequiredArgsConstructor
public class CustomerPersistenceImpl implements CustomerPersistence {

    private final CustomerRepository customerRepository;

    @Override
    public CustomerEntity save(CustomerEntity entity) {
        try {
            return customerRepository.save(entity);
        } catch (DataIntegrityViolationException e) {
            throw ApiRestException.builder()
                .reason(ErrorReason.CONFLICT)
                .source(ErrorSource.DATA_REPOSITORY)
                .build();
        }
    }
}
```

### Controller Layer

```java
@Slf4j
@RestController
@RequiredArgsConstructor
public class CustomerControllerImpl implements CustomerController {

    private final CustomerService customerService;

    @Override
    public ResponseEntity<CustomerResponse> getCustomer(Long id) {
        log.info("[START] getCustomer - id: {}", id);

        if (id == null || id <= 0) {
            throw ApiRestException.builder()
                .reason(ErrorReason.BAD_REQUEST)
                .source(ErrorSource.REST_CONTROLLER)
                .build();
        }

        CustomerData customerData = customerService.getCustomerById(id);
        CustomerResponse response = customerMapper.toResponse(customerData);

        log.info("[END] getCustomer - id: {}", id);
        return ResponseEntity.ok(response);
    }
}
```

### API Client Layer

```java
@Component
@RequiredArgsConstructor
@Slf4j
public class JumioClientImpl implements JumioClient {

    @Override
    public JumioResponse verifyIdentity(JumioRequest request) {
        Response<JumioResponse> response = jumioApi.verifyIdentity(request).execute();

        if (!response.isSuccessful()) {
            throw ApiRestException.builder()
                .reason(ErrorReason.HTTP_COMMUNICATION_FAILURE)
                .source(ErrorSource.HTTP_CLIENT_JUMIO)
                .build();
        }

        return response.body();
    }
}
```

## Factory Methods (Alternative Pattern)

When the same exception is thrown in multiple places, create a factory method:

```java
@Slf4j
@Service
@RequiredArgsConstructor
public class CustomerServiceImpl implements CustomerService {

    // Factory method for common exception
    private ApiRestException buildCustomerNotFoundException(Long customerId) {
        return ApiRestException.builder()
            .reason(ErrorReason.CUSTOMER_NOT_FOUND)
            .source(ErrorSource.BUSINESS_SERVICE)
            .build();
    }

    @Override
    public CustomerData getCustomer(Long id) {
        return customerRepository.findById(id)
            .map(customerMapper::toData)
            .orElseThrow(() -> buildCustomerNotFoundException(id));
    }

    @Override
    public void updateCustomer(Long id, CustomerData data) {
        CustomerEntity customer = customerRepository.findById(id)
            .orElseThrow(() -> buildCustomerNotFoundException(id));
        // ... update logic
    }
}
```

## Swagger Integration

Document exceptions using `@ErrorResponses` annotation:

```java
public interface CustomerController {

    @ErrorResponses(values = {
        @ErrorResponse(reason = ErrorReason.NOT_FOUND, source = ErrorSource.BUSINESS_SERVICE),
        @ErrorResponse(reason = ErrorReason.FORBIDDEN, source = ErrorSource.REST_CONTROLLER)
    })
    @GetMapping("/customer/b2c/customers/{id}")
    ResponseEntity<CustomerResponse> getCustomer(@PathVariable Long id);
}
```

## Creating Custom Errors

When you need domain-specific errors not available in the library:

### Step 1: Use TODO Comments with Generic Errors

**DO NOT create local enums** in your microservice. All errors must come from the shared library. Use generic errors with TODO comments:

```java
// TODO: SUBSCRIPTION_BENEFIT_ALREADY_EXISTS (CONFLICT)
throw ApiRestException.builder()
    .reason(ErrorReason.CONFLICT)  // Generic - replace once library is updated
    .source(ErrorSource.BUSINESS_SERVICE)
    .build();

// TODO: SUBSCRIPTION_BUSINESS_NOT_FOUND (NOT_FOUND)
throw ApiRestException.builder()
    .reason(ErrorReason.NOT_FOUND)
    .source(ErrorSource.BUSINESS_SERVICE)
    .build();
```

### Step 2: Request New ErrorReason to Architecture Team

Create a ticket/request to the architecture team with the following information:

#### ErrorReason Naming Convention

Format: `{DOMAIN}_{ENTITY}_{CONDITION}`

| Pattern | Example |
|---------|---------|
| `{DOMAIN}_{ENTITY}_ALREADY_EXISTS` | `SUBSCRIPTION_BENEFIT_ALREADY_EXISTS` |
| `{DOMAIN}_{ENTITY}_BUSINESS_{CONDITION}` | `SUBSCRIPTION_BENEFIT_BUSINESS_ALREADY_EXISTS` |
| `{DOMAIN}_{ENTITY}_NOT_ACTIVE` | `SUBSCRIPTION_AVAILABLE_ACCOUNT_REMUNERATION_NOT_ACTIVE` |
| `{DOMAIN}_{ENTITY}_NOT_FOUND` | `SUBSCRIPTION_BUSINESS_NOT_FOUND` |
| `{DOMAIN}_{ENTITY}_NOT_{ROLE}` | `SUBSCRIPTION_BUSINESS_NOT_PARTNER` |
| `{DOMAIN}_{ENTITY}_{CONTEXT}_NOT_FOUND` | `SUBSCRIPTION_PLAN_COUNTRY_NOT_FOUND` |

**Naming Rules:**
- Always use **UPPER_SNAKE_CASE**
- Start with the **domain prefix** (e.g., `SUBSCRIPTION_`, `TRANSACTION_`, `CUSTOMER_`)
- Include the **entity name** (e.g., `BENEFIT`, `BUSINESS`, `PLAN`)
- End with the **condition** (e.g., `ALREADY_EXISTS`, `NOT_FOUND`, `NOT_ACTIVE`)
- Be specific and descriptive - avoid generic terms like `INVALID` or `ERROR`

#### Required Information for Architecture Team

For each new `ErrorReason`, provide:

1. **ErrorReason name** (following naming convention above)
2. **HTTP Status Code** (e.g., 400, 404, 409, 422)
3. **Error Code** (numeric format, e.g., `060405`)
4. **Description** for the `ErrorCode` enum (detailed format)

**Description Format for ErrorCode:**

```
Error response when [specific condition in clear, descriptive language].
```

**Examples:**

| ErrorReason | HTTP Status | Error Code | Description for ErrorCode enum |
|-------------|-------------|------------|-------------------------------|
| `SUBSCRIPTION_BENEFIT_ALREADY_EXISTS` | 409 | 060405 | Error response when the subscription benefit already exists for the given customer. |
| `SUBSCRIPTION_BUSINESS_NOT_FOUND` | 404 | 060406 | Error response when the requested business is not found in the subscription context. |
| `SUBSCRIPTION_PLAN_COUNTRY_NOT_FOUND` | 404 | 060407 | Error response when the requested plan configuration for the given country is not found or is inactive. |
| `SUBSCRIPTION_PLAN_DOWNGRADE_NOT_ALLOWED` | 422 | 060408 | Error response when the customer attempts to subscribe to a plan with a tier level equal or lower than the current active plan. |

**Complete Example Request to Architecture:**

```
Subject: Request for new ErrorReason and ErrorCode - Subscription Domain

Hi Architecture Team,

I need the following new error codes added to the shared exception library:

1. ErrorReason: SUBSCRIPTION_BENEFIT_ALREADY_EXISTS
   - HTTP Status: 409 CONFLICT
   - Error Code: 060405
   - Description: Error response when the subscription benefit already exists for the given customer.

2. ErrorReason: SUBSCRIPTION_BUSINESS_NOT_FOUND
   - HTTP Status: 404 NOT_FOUND
   - Error Code: 060406
   - Description: Error response when the requested business is not found in the subscription context.

3. ErrorReason: SUBSCRIPTION_BUSINESS_NOT_PARTNER
   - HTTP Status: 422 UNPROCESSABLE_ENTITY
   - Error Code: 060407
   - Description: Error response when the business is not registered as a partner in the subscription system.

These are needed for the subscription validation flows in the ms-subscription microservice.

Thanks!
```

### Step 3: Request New ErrorSource (if needed)

If none of the existing `ErrorSource` values fit your use case, request a new one:

**ErrorSource Naming Convention:**

Format: `{LAYER}_{COMPONENT}` or `ADAPTER_{EXTERNAL_SYSTEM}` or `HTTP_CLIENT_{SYSTEM}`

| Pattern | Examples |
|---------|----------|
| `ADAPTER_{EXTERNAL_SYSTEM}` | `ADAPTER_STRIPE`, `ADAPTER_PAYPAL` |
| `HTTP_CLIENT_{SYSTEM}` | `HTTP_CLIENT_STRIPE`, `HTTP_CLIENT_PAYPAL` |
| `{LAYER}_{COMPONENT}` | `BUSINESS_VALIDATOR`, `PERSISTENCE_CACHE` |

**Existing ErrorSource values** (use these first):
- `BUSINESS_SERVICE`, `DATA_REPOSITORY`, `REST_CONTROLLER`
- `ADAPTER_COMPONENT`, `ADAPTER_JUMIO`, `ADAPTER_TRUORA`
- `HTTP_CLIENT_COMPONENT`, `HTTP_CLIENT_JUMIO`, `HTTP_CLIENT_TRUORA`, `HTTP_CLIENT_IBAN`
- `COGNITO_SERVICE`, `ITERABLE_SERVICE`
- `UTILS`, `HELPER_COMPONENT`

### Step 4: Update Code After Library Release

Once the architecture team adds the errors to the shared library:

1. Update your `pom.xml` (or `build.gradle`) to the new library version
2. Replace generic error with specific `ErrorReason.XXX`
3. Remove the TODO comment
4. Update `ErrorSource` if a new specific one was created

**Before:**
```java
// TODO: SUBSCRIPTION_BENEFIT_ALREADY_EXISTS (CONFLICT)
throw ApiRestException.builder()
    .reason(ErrorReason.CONFLICT)
    .source(ErrorSource.BUSINESS_SERVICE)
    .build();
```

**After:**
```java
throw ApiRestException.builder()
    .reason(ErrorReason.SUBSCRIPTION_BENEFIT_ALREADY_EXISTS)
    .source(ErrorSource.BUSINESS_SERVICE)
    .build();
```

## Common Violations

| Violation | Problem | Correct Approach |
|-----------|---------|------------------|
| Inline `throw new RuntimeException()` | No standardized error info | Use `ApiRestException.builder()` |
| Inline `throw new Exception()` | Generic exception type | Use specific `ErrorReason` |
| `BusinessException(ErrorCode.XXX)` | Deprecated pattern | Use `ApiRestException` with `ErrorReason` |
| Wrong `ErrorSource` | Incorrect error categorization | Use source matching the layer |
| No `ErrorSource` | Missing error context | Always include `.source(...)` |
| Generic error for specific case | Poor error granularity | Use domain-specific `ErrorReason` |

## Compliance Checklist

- [ ] Exceptions use `ApiRestException.builder()` pattern
- [ ] `ErrorReason` is specific to the error condition
- [ ] `ErrorSource` matches the layer where error occurs
- [ ] Factory methods used for repeated exceptions
- [ ] Swagger `@ErrorResponses` documents possible errors
- [ ] Custom errors requested to architecture team for library inclusion
- [ ] No inline `throw new RuntimeException()` or `throw new Exception()`
- [ ] Persistence layer uses `DATA_REPOSITORY` source
- [ ] Business layer uses `BUSINESS_SERVICE` source
- [ ] Controller layer uses `REST_CONTROLLER` source
- [ ] HTTP clients use `HTTP_CLIENT_*` sources

## ErrorReason/ErrorSource Request Checklist

When requesting new errors from architecture team:

- [ ] ErrorReason follows `{DOMAIN}_{ENTITY}_{CONDITION}` format
- [ ] ErrorReason is in UPPER_SNAKE_CASE
- [ ] HTTP status code is specified (400, 404, 409, 422, 500, etc.)
- [ ] Numeric error code is provided (e.g., 060405)
- [ ] Description follows format: "Error response when [condition]."
- [ ] Description is clear and descriptive
- [ ] ErrorSource matches existing values or follows naming convention
- [ ] TODO comments in code reference the exact ErrorReason name needed
