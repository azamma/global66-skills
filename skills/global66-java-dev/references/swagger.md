# Swagger / OpenAPI Guidelines — Global66

Stack: SpringDoc OpenAPI `springdoc-openapi-starter-webmvc-ui` v2.2.0 · `io.swagger.v3.oas.annotations`

---

## Dependencies & Configuration

**pom.xml** (managed via `global66-mysql-starter-parent` — verify version property exists):
```xml
<dependency>
    <groupId>org.springdoc</groupId>
    <artifactId>springdoc-openapi-starter-webmvc-ui</artifactId>
    <version>${springdoc-openapi-ui.version}</version>  <!-- target: 2.2.0 -->
</dependency>
```

**application.yml** (mandatory structure):
```yaml
springdoc:
  api-docs:
    path: /{serviceName}/api-docs
  swagger-ui:
    path: /{serviceName}/swagger-ui.html
  override-with-generic-response: false
```

**Required custom components** (from `com.global.rest.exception` internal library):
- `SwaggerConfig` — base OpenAPI configuration bean
- `CustomProcessor` — scans and registers `@ErrorResponses` into the spec
- `annotation/ErrorResponses` + `annotation/ErrorResponse` — custom error annotation

---

## Controller Pattern: Interface = Contract, Impl = Logic

All Swagger annotations live **exclusively on the interface**. The `@RestController`
implementation must have zero `@Operation`, `@Tag`, or `@Schema` annotations — those
belong to the API contract definition, not the logic.

```
presentation/
├── GeoCodeController.java          ← ALL Swagger annotations here
└── impl/
    └── GeoCodeControllerImpl.java  ← NO Swagger annotations, only Spring MVC
```

**Naming convention:**
- Interface: `{Domain}Controller` — defines the API contract
- Implementation: `{Domain}ControllerImpl` — implements business delegation only

> **Note:** Some teams use `{Domain}Api` (interface) and `{Domain}ApiController` (impl).
> Either convention is acceptable, but it must be consistent within a microservice.

---

## Interface — Full Example

```java
@Tag(name = "GeoCode", description = "API for managing Here-Geocode")
public interface GeoCodeController {

    @ErrorResponses(
        values = {
            @ErrorResponse(reason = ErrorReason.CONFLICT,
                           source = ErrorSource.HTTP_CLIENT_COMPONENT)
        })
    @Operation(
        summary = "Return basic geolocation info",
        description = "Uses a specific address, city and country to return basic location info",
        tags = {"geocode", "location", "postalCode", "latitude", "longitude"},
        responses = {
            @ApiResponse(responseCode = "200", description = "Geocode returned successfully"),
            @ApiResponse(responseCode = "400", description = "Bad request or empty parameter")
        })
    GeoCodeBasicLocationResponse basicGeoInfo(
        @Parameter(description = "Street address", required = true, example = "Av. Providencia 1234")
            String address,
        @Parameter(description = "City of the address", required = true, example = "Santiago")
            String city,
        @Parameter(description = "Country of the city", required = true, example = "Chile")
            String country);
}
```

**Key rules:**
- `@Tag` at class level: `name` + `description` mandatory
- `@Operation` at method level: `summary` + `description` mandatory; `tags` optional
- `@ErrorResponses` with `@ErrorResponse(reason, source)` for business/client errors
- `@Parameter` per individual parameter: `description` + `required` + `example`
- For request body DTOs with multiple fields: use `@RequestBody @Valid` — no `@ParameterObject`
- For query parameters with a DTO: use `@ParameterObject` on the DTO argument

---

## Implementation — What NOT to do

```java
// CORRECT: zero Swagger annotations, only Spring MVC + logic
@Slf4j
@RestController
@RequiredArgsConstructor
@RequestMapping("/geolocation/iuse/geocode")
public class GeoCodeControllerImpl implements GeoCodeController {

    private final GeoCodeService geoCodeService;

    @GetMapping("/basic-location-info")
    public GeoCodeBasicLocationResponse basicGeoInfo(
            @RequestParam("address") @NotBlank String address,
            @RequestParam("city") @NotBlank String city,
            @RequestParam("country") @NotBlank String country) {
        log.info("START - [GET] [/geolocation/iuse/geocode/basic-location-info]: address={}", address);
        GeoCodeBasicLocationResponse response = GeoCodeBasicLocationPresentationMapper.INSTANCE
            .toGeoCodeBasicLocationResponse(geoCodeService.getBasicLocation(address, city, country));
        log.info("END - [GET] [/geolocation/iuse/geocode/basic-location-info]");
        return response;
    }
}
```

```java
// WRONG: Swagger annotations in the implementation
@RestController
public class GeoCodeControllerImpl implements GeoCodeController {

    @Operation(summary = "...")  // ← FORBIDDEN in implementation
    @Tag(name = "...")           // ← FORBIDDEN in implementation
    public GeoCodeBasicLocationResponse basicGeoInfo(...) { ... }
}
```

---

## @ErrorResponses — Custom Error Annotation

Uses the internal library `com.global.rest.exception`:

```java
import com.global.rest.exception.annotation.ErrorResponse;
import com.global.rest.exception.annotation.ErrorResponses;
import com.global.rest.exception.enums.ErrorReason;
import com.global.rest.exception.enums.ErrorSource;

@ErrorResponses(
    values = {
        @ErrorResponse(reason = ErrorReason.CONFLICT,
                       source = ErrorSource.HTTP_CLIENT_COMPONENT),
        @ErrorResponse(reason = ErrorReason.NOT_FOUND,
                       source = ErrorSource.BUSINESS_SERVICE),
        @ErrorResponse(reason = ErrorReason.UNPROCESSABLE_ENTITY,
                       source = ErrorSource.ADAPTER_JUMIO)
    })
```

**Common `ErrorSource` values:**
- `ErrorSource.BUSINESS_SERVICE` — internal business rule violation
- `ErrorSource.HTTP_CLIENT_COMPONENT` — external HTTP/REST client error
- `ErrorSource.ADAPTER_JUMIO`, `ErrorSource.ADAPTER_*` — specific external adapter failures

---

## @SecurityRequirement — Authentication Schemes

Only add when the endpoint is protected. Use the scheme matching the consumer type:

```java
import io.swagger.v3.oas.annotations.security.SecurityRequirement;

// B2C (end user / customer-facing)
@SecurityRequirement(name = "authB2C")

// B2B (internal service-to-service)
@SecurityRequirement(name = "authB2B")

// Admin panel / backoffice
@SecurityRequirement(name = "authAdmin")
```

---

## @Server — Only for APIGW-exposed endpoints

Only add `@Server` when the endpoint is exposed through API Gateway or you need to override
the base URL. Do NOT add `@Server` to every endpoint.

```java
import io.swagger.v3.oas.annotations.servers.Server;

@Server(url = "https://dev-api.global66.com", description = "Dev - Public APIGW")
@Server(url = "https://lb-dev-private.global66.com", description = "Dev - Internal LB")
@Server(url = "http://localhost:8105/", description = "Local")
```

**Valid URLs:** `http://localhost:8105/` · `https://lb-dev-private.global66.com` · `https://dev-api.global66.com`

---

## DTOs — Request Classes

```java
@Data
@Schema(
    name = "UserPermissionRequestDto",
    description = "Request payload for creating or updating a user's geolocation permission.",
    example = """
        {
          "permission_status": "GRANTED",
          "permission_type": "LOCATION",
          "device_info": { "device": "Samsung Galaxy S22", "fingerprint": "ab1234cd" }
        }
        """)
public class UserPermissionRequestDto {

    @NotNull
    @JsonProperty("permission_status")
    @Schema(
        description = "Status of the permission granted by the user.",
        requiredMode = Schema.RequiredMode.REQUIRED,
        example = "GRANTED")
    private PermissionStatusEnum permissionStatus;

    @NotNull
    @JsonProperty("permission_type")
    @Schema(
        description = "Type of permission being recorded.",
        requiredMode = Schema.RequiredMode.REQUIRED,
        example = "LOCATION")
    private PermissionTypeEnum permissionType;
}
```

## DTOs — Response Records

```java
public record GeoCodeBasicLocationResponse(
    @Schema(description = "Response source: API or DEFAULT fallback", example = "API")
        HereGeocodeResponseSource responseSource,
    @Schema(description = "Full formatted address", example = "Str. 1 #2, Santiago, Chile")
        String fullAddress,
    @Schema(description = "Latitude coordinate", example = "7.666283")
        double latitude,
    @Schema(description = "Longitude coordinate", example = "-99.247894")
        double longitude) {}
```

**Rules for DTOs:**
- Class-level `@Schema`: `name` + `description` + `example` (full JSON string)
- Field-level `@Schema`: `description` + `example` + `requiredMode` (for required fields)
- Use `Schema.RequiredMode.REQUIRED` instead of deprecated `required = true`
- Response records: annotate each component parameter

---

## Swagger Audit Report Format

When reviewing a controller or DTO for Swagger compliance, output:

```
### Resumen de Auditoría
Status: COMPLIANT | PARTIAL | NON_COMPLIANT

### Cumplimientos
- @Tag presente con name y description
- @Operation en todos los métodos con summary y description
- @Schema con ejemplos en todos los campos del DTO

### Errores Críticos (bloqueantes)
- [CRITICAL] GeoCodeControllerImpl.java:15 — @Operation en la implementación.
  Fix: Mover @Operation a la interfaz GeoCodeController.java

- [CRITICAL] UserRequest.java — @Schema sin campo 'example'.
  Fix: Agregar example = "valor real" al @Schema de cada campo

### Advertencias
- [WARNING] PaymentController.java:8 — @SecurityRequirement ausente en endpoint protegido.
  Fix: Agregar @SecurityRequirement(name = "authB2C") en la interfaz

### Código Corregido
[snippet corregido de la interfaz]
```

---

## Quick Compliance Checklist

- [ ] Dependency `springdoc-openapi-starter-webmvc-ui` en `pom.xml`
- [ ] `springdoc.api-docs.path` = `/{serviceName}/api-docs`
- [ ] `springdoc.swagger-ui.path` = `/{serviceName}/swagger-ui.html`
- [ ] `override-with-generic-response: false`
- [ ] Interfaz de controller tiene `@Tag(name, description)`
- [ ] Cada método del interfaz tiene `@Operation(summary, description)`
- [ ] Métodos con errores de negocio tienen `@ErrorResponses`
- [ ] Implementación `@RestController` no tiene `@Tag`, `@Operation`, ni `@Schema`
- [ ] Request DTOs: `@Schema` a nivel clase (con `name`, `description`, `example`) y en cada campo
- [ ] Response records: `@Schema` en cada componente con `description` y `example`
- [ ] Endpoints protegidos tienen `@SecurityRequirement(name = "authB2C|authB2B|authAdmin")`
- [ ] `@Server` solo si el endpoint se expone en APIGW
