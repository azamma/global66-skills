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

1. **DO NOT create local enums** in your microservice. All errors must come from the shared library.

2. **Use generic errors with TODO comments** indicating the specific error needed:

```java
// TODO: REWARD_INSUFFICIENT_POINTS (BAD_REQUEST)
throw ApiRestException.builder()
    .reason(ErrorReason.BAD_REQUEST)  // Generic - replace once library is updated
    .source(ErrorSource.BUSINESS_SERVICE)
    .build();

// TODO: REWARD_ALREADY_CLAIMED (CONFLICT)
throw ApiRestException.builder()
    .reason(ErrorReason.CONFLICT)  // Generic - replace once library is updated
    .source(ErrorSource.BUSINESS_SERVICE)
    .build();
```

3. **Request architecture team** to add them to the shared library:
   - Create a ticket/request to the architecture team
   - Provide the new `ErrorReason` code name and suggested HTTP status
   - Include the TODO comment with the exact code you need
   - Once added to library, replace the generic error with the specific one

4. **Update code after library release**:
   - Replace generic error with specific `ErrorReason.XXX`
   - Remove the TODO comment
   - Example: `ErrorReason.BAD_REQUEST` → `ErrorReason.REWARD_INSUFFICIENT_POINTS`

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
