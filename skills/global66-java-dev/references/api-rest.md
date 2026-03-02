# Global66 API REST Guidelines

Guidelines for designing and implementing REST APIs in Global66 microservices.

## URL Structure

```
/{service-name}/{prefix}/{resource-path}
```

## Naming Conventions

### Resource Names

| Rule | Convention | Example |
|------|------------|---------|
| Use nouns, not verbs | Resource name only | `/customers` not `/get-customer` |
| Use plural forms | Plural sustantives | `/customers`, `/orders` |
| Lowercase only | RFC 3986 compliance | `/customers` not `/Customers` |
| Kebab-case for multi-word | Hyphen-separated | `/personal-info` not `/personalInfo` |
| No special characters | Alphanumeric and hyphens only | `/customer-info` |
| Hierarchy with forward slash | `/` indicates relationship | `/customers/123/addresses` |

### Examples

```
GET  /customer/b2c/customers              # List all customers
GET  /customer/b2c/customers/123           # Get specific customer
GET  /customer/b2c/customers/123/addresses # Get customer addresses
POST /customer/b2c/customers               # Create customer
PUT  /customer/b2c/customers/123           # Update customer (full)
PATCH /customer/b2c/customers/123          # Update customer (partial)
DELETE /customer/b2c/customers/123         # Delete customer
```

### Anti-patterns

```
# INCORRECT - Don't use:
GET /get-customer              # Verbs in URL
GET /getCustomer               # camelCase
GET /customer/123/fn           # Unclear abbreviations
GET /Customer                  # Uppercase
GET /customers/personal_info   # snake_case
GET /customers/123?action=delete  # Action in query param
```

## HTTP Methods

| Method | Purpose | Idempotent | Request Body | Response Body |
|--------|---------|------------|--------------|---------------|
| `GET` | Retrieve resource(s) | Yes* | No | Yes (resource) |
| `POST` | Create resource | No | Yes (new resource) | Yes (created resource) |
| `PUT` | Full update/replace | Yes | Yes (full resource) | Yes (updated resource) |
| `PATCH` | Partial update | No | Yes (partial fields) | Yes (updated resource) |
| `DELETE` | Remove resource | Yes | No | No (or confirmation) |
| `HEAD` | Check existence | Yes | No | No (headers only) |
| `OPTIONS` | Available methods | Yes | No | No |

\* GET is idempotent only if it doesn't change resource state.

### GET Examples

```
# List resources
GET /customer/b2c/customers
Response: 200 OK
[
  { "id": 12345, "name": "Nicolás", "lastName": "D'Amelio" },
  { "id": 12346, "name": "Jhunior", "lastName": "Cuadros" }
]

# Single resource
GET /customer/b2c/customers/12345
Response: 200 OK
{ "id": 12345, "name": "Nicolás", "lastName": "D'Amelio", "country": "Chile" }
```

### POST Example

```
POST /customer/b2c/customers
Request Body:
{
  "name": "Nicolás",
  "lastName": "D'Amelio",
  "country": "Chile",
  "address": "Santiago"
}
Response: 201 Created
Location: /customer/b2c/customers/12345
{ "id": 12345, "name": "Nicolás", "lastName": "D'Amelio", ... }
```

### PUT Example

```
PUT /customer/b2c/customers/12345
Request Body: (full resource required)
{
  "name": "Nicolás",
  "lastName": "D'Amelio",
  "country": "Venezuela",
  "address": "Caracas"
}
Response: 200 OK
```

### PATCH Example

```
PATCH /customer/b2c/customers/12345
Request Body: (only changed fields)
{
  "country": "Venezuela"
}
Response: 200 OK
```

### DELETE Example

```
DELETE /customer/b2c/customers/12345
Response: 204 No Content
```

## Prefixes (Authentication Context)

| Prefix | Description | Auth Required | Exposed In |
|--------|-------------|---------------|------------|
| `b2c` | Business-to-consumer (person users) | Session token (b2c pool) | API Gateway |
| `b2b` | Business-to-business (company users) | Session token (b2b pool) | API Gateway |
| `bo` | Back-office (admin users) | Session token (back-office pool) | API Gateway |
| `ext` | External/public access | None | API Gateway |
| `iuse` | Internal use (microservice-to-microservice) | None | Private (LB only) |
| `sfc` | Salesforce integration | None | Private (LB only) |
| `notification` | Webhooks/provider callbacks | API Key | Separate API Gateway |
| `cron` | Scheduled tasks | None | Event Bridge → Lambda |

### Prefix Security Rules

**b2c, b2b, bo:**
- Always extract user ID from auth token, never from request body
- Validate the requesting user can only access their own data
- Log security violations

**ext:**
- Never expose sensitive or specific customer data
- Use for: login, registration, forgot password, public rates/routes
- Implement rate limiting

**iuse, sfc:**
- Never exposed in API Gateway
- Accessible only via internal load balancer
- Network-level security (same VPC)

**notification:**
- Dedicated API Gateway with API Key authentication
- Validate webhook signatures when applicable

**cron:**
- Triggered by Event Bridge rules
- Lambda-invoked only
- No external access

## Request/Response Body

### Request Body

- Always use DTOs, never Entities
- Never use ambiguous types (String, Map, Object)
- Include validation annotations

```java
@Data
public class CustomerRequest {
    @NotBlank
    @Size(max = 100)
    private String name;

    @NotBlank
    @Size(max = 100)
    private String lastName;

    @NotNull
    @ValidCountry
    private String country;
}
```

### Response Body

- Always use DTOs or lists of DTOs
- Never use wrapper objects (ApiResponse, etc.)
- Never return Entities

```java
@Data
@Builder
public class CustomerResponse {
    private Long id;
    private String name;
    private String lastName;
    private String country;
    private String address;
}
```

## API Versioning

Use **Custom Header Versioning** with `X-API-VERSION` header.

### Implementation

```java
// Default version (v1)
@GetMapping(value = "/header")
public ResponseEntity<Void> headersV1(
        @RequestHeader(value = "X-API-VERSION", defaultValue = "1") String version) {
    log.info("Start GET request/service-name/v1/header");
    return ResponseEntity.ok().build();
}

// Explicit version (v2)
@GetMapping(value = "/header", headers = "X-API-VERSION=2")
public ResponseEntity<Void> headersV2() {
    log.info("Start GET request/service-name/v2/header");
    return ResponseEntity.ok().build();
}
```

### Versioning Rules

- **When to version:** Breaking changes in request/response contracts
- **Default behavior:** If version not specified or invalid, use v1
- **Maintenance:** Technical Lead responsible for consolidating versions
- **Goal:** Minimize version sprawl; plan for single-version APIs

## Documentation

See `references/swagger.md` for complete Swagger/OpenAPI documentation standards.

Key requirements:
- All annotations on controller interface (not implementation)
- `@Tag` on every controller interface
- `@Operation` on every method
- `@ErrorResponses` for error scenarios
- `@Schema` on DTOs with examples

## Complete Example

```java
@Tag(name = "Customers", description = "Customer management operations")
public interface CustomerController {

    @Operation(summary = "Get all customers", description = "Returns a list of all customers")
    @GetMapping("/customer/b2c/customers")
    List<CustomerResponse> getAllCustomers();

    @Operation(summary = "Get customer by ID", description = "Returns a specific customer")
    @GetMapping("/customer/b2c/customers/{id}")
    CustomerResponse getCustomer(@PathVariable Long id);

    @Operation(summary = "Create customer", description = "Creates a new customer")
    @PostMapping("/customer/b2c/customers")
    ResponseEntity<CustomerResponse> createCustomer(@RequestBody @Valid CustomerRequest request);

    @Operation(summary = "Update customer", description = "Fully updates a customer")
    @PutMapping("/customer/b2c/customers/{id}")
    CustomerResponse updateCustomer(@PathVariable Long id, @RequestBody @Valid CustomerRequest request);

    @Operation(summary = "Patch customer", description = "Partially updates a customer")
    @PatchMapping("/customer/b2c/customers/{id}")
    CustomerResponse patchCustomer(@PathVariable Long id, @RequestBody Map<String, Object> updates);

    @Operation(summary = "Delete customer", description = "Deletes a customer")
    @DeleteMapping("/customer/b2c/customers/{id}")
    ResponseEntity<Void> deleteCustomer(@PathVariable Long id);
}
```

## Common Violations

| Violation | Problem | Correct Approach |
|-----------|---------|------------------|
| Verbs in URL | `/get-customer`, `/create-order` | Use nouns: `/customers`, `/orders` |
| Singular resources | `/customer` for collection | Use plural: `/customers` |
| camelCase in URL | `/personalInfo` | Use kebab-case: `/personal-info` |
| Uppercase letters | `/Customers` | Use lowercase: `/customers` |
| Underscores | `/personal_info` | Use hyphens: `/personal-info` |
| Action in query param | `?action=delete` | Use HTTP method: `DELETE` |
| Entities in request/response | Using JPA entities | Use DTOs only |
| Missing auth validation | Reading user ID from body | Extract from auth token |
| No version header | Breaking changes without version | Use `X-API-VERSION` header |

## Compliance Checklist

- [ ] Resource names are plural nouns in lowercase
- [ ] Multi-word resources use kebab-case (hyphens)
- [ ] HTTP methods used correctly (GET/POST/PUT/PATCH/DELETE)
- [ ] Prefix chosen correctly based on auth context
- [ ] Request/Response use DTOs (not Entities)
- [ ] Versioning implemented with `X-API-VERSION` header
- [ ] Swagger annotations on interface (not implementation)
- [ ] Auth tokens validated for b2c/b2b/bo endpoints
- [ ] User ID extracted from token, not request body
- [ ] iuse/sfc endpoints not exposed in API Gateway
