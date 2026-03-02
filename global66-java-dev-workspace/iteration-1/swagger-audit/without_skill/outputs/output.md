# Swagger / OpenAPI Audit Report — TransactionController

---

### Resumen de Auditoría

**Status: NON_COMPLIANT**

The submitted code contains multiple critical violations of the Global66 Swagger/OpenAPI standards. No component — controller implementation, interface, or DTO — is compliant.

---

### Cumplimientos

- None identified. No component meets the required standard.

---

### Errores Críticos (bloqueantes)

**[CRITICAL] TransactionControllerImpl.java — @Tag on the implementation class, inside a method.**
Swagger annotations (`@Tag`, `@Operation`) are **forbidden** in the `@RestController` implementation. They must live exclusively on the interface.
Fix: Remove `@Tag` and `@Operation` from `TransactionControllerImpl`. Move them to `TransactionController`.

**[CRITICAL] TransactionControllerImpl.java — @Operation on the implementation method.**
`@Operation(summary = "Get transaction by ID", description = "Returns a transaction")` is placed directly on the method inside the `@RestController` class.
Fix: Remove from implementation. Add to the corresponding method on the interface `TransactionController`.

**[CRITICAL] TransactionController.java (interface) — @Tag missing at class level.**
The interface has no `@Tag` annotation. The `name` and `description` fields are mandatory on the interface.
Fix: Add `@Tag(name = "Transactions", description = "Payment transaction operations")` at the class level of the interface.

**[CRITICAL] TransactionController.java (interface) — @Operation missing on getTransaction method.**
The interface method `getTransaction` has no `@Operation` annotation. `summary` and `description` are mandatory.
Fix: Add `@Operation(summary = "Get transaction by ID", description = "Returns a transaction by its unique identifier")` to the interface method.

**[CRITICAL] TransactionController.java (interface) — @Parameter missing on the txnId parameter.**
Path parameters must be documented with `@Parameter(description, required, example)`.
Fix: Annotate the `txnId` parameter in the interface with `@Parameter(description = "Transaction unique identifier", required = true, example = "TXN-20240101-00123")`.

**[CRITICAL] TransactionController.java (interface) — @ApiResponse entries missing.**
The `@Operation` must include `responses` with at minimum a `200` success case and a `400` bad request case.
Fix: Add `responses = { @ApiResponse(responseCode = "200", description = "Transaction found"), @ApiResponse(responseCode = "400", description = "Invalid transaction ID format") }` inside `@Operation`.

**[CRITICAL] TransactionController.java (interface) — @ErrorResponses missing.**
A GET-by-ID endpoint can produce a NOT_FOUND business error. The `@ErrorResponses` annotation from `com.global.rest.exception` is required to document it.
Fix: Add `@ErrorResponses(values = { @ErrorResponse(reason = ErrorReason.NOT_FOUND, source = ErrorSource.BUSINESS_SERVICE) })` to the interface method.

**[CRITICAL] TransactionResponse.java — No @Schema annotations anywhere.**
The DTO class has no class-level `@Schema` (missing `name`, `description`, `example`) and none of the three fields (`txnId`, `amount`, `status`) have field-level `@Schema` annotations.
Fix: Add `@Schema` at class level with `name`, `description`, and a full JSON `example`. Add field-level `@Schema` on each field with `description`, `example`, and `requiredMode` where applicable.

---

### Advertencias

**[WARNING] TransactionControllerImpl.java — @Slf4j and @RequiredArgsConstructor are missing.**
The implementation class is missing Lombok annotations. `@Slf4j` is required for START/END logging. `@RequiredArgsConstructor` is required for constructor injection of `transactionService`.
Fix: Add `@Slf4j` and `@RequiredArgsConstructor` to the implementation class and declare `transactionService` as a `private final` field.

**[WARNING] TransactionControllerImpl.java — No START/END log statements in getTransaction.**
Logging policy requires `log.info("START - ...")` and `log.info("END - ...")` in every controller method.
Fix: Add START and END log lines following the pattern `log.info("START - [GET] [/payments/iuse/transactions/{txnId}]: txnId={}", txnId)`.

**[WARNING] TransactionController.java (interface) — @SecurityRequirement absent.**
If this endpoint is consumer-facing (B2C) or service-to-service (B2B), `@SecurityRequirement` must be declared on the interface method.
Fix: Add `@SecurityRequirement(name = "authB2C")` or `@SecurityRequirement(name = "authB2B")` as appropriate.

**[WARNING] TransactionResponse.java — Class uses fields (not a record).**
Response DTOs should prefer Java records for immutability. If a class is used instead of a record, it must include Lombok `@Data` or `@Getter`/`@Setter` plus `@NoArgsConstructor`/`@AllArgsConstructor`. Currently no Lombok annotations are present.
Fix: Convert to a record, or add the appropriate Lombok annotations.

---

### Codigo Corregido

#### TransactionController.java (Interface — API contract, all Swagger annotations here)

```java
import com.global.rest.exception.annotation.ErrorResponse;
import com.global.rest.exception.annotation.ErrorResponses;
import com.global.rest.exception.enums.ErrorReason;
import com.global.rest.exception.enums.ErrorSource;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.web.bind.annotation.PathVariable;

@Tag(name = "Transactions", description = "Payment transaction operations")
public interface TransactionController {

    @ErrorResponses(
        values = {
            @ErrorResponse(
                reason = ErrorReason.NOT_FOUND,
                source = ErrorSource.BUSINESS_SERVICE)
        })
    @Operation(
        summary = "Get transaction by ID",
        description = "Returns a payment transaction by its unique identifier",
        responses = {
            @ApiResponse(responseCode = "200", description = "Transaction found successfully"),
            @ApiResponse(responseCode = "400", description = "Invalid transaction ID format")
        })
    @SecurityRequirement(name = "authB2C")
    TransactionResponse getTransaction(
        @Parameter(description = "Transaction unique identifier", required = true, example = "TXN-20240101-00123")
            @PathVariable String txnId);
}
```

#### TransactionControllerImpl.java (Implementation — zero Swagger annotations)

```java
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@Slf4j
@RestController
@RequiredArgsConstructor
@RequestMapping("/payments/iuse/transactions")
public class TransactionControllerImpl implements TransactionController {

    private final TransactionService transactionService;

    @GetMapping("/{txnId}")
    public TransactionResponse getTransaction(@PathVariable String txnId) {
        log.info("START - [GET] [/payments/iuse/transactions/{}]: txnId={}", txnId, txnId);
        TransactionResponse response = transactionService.findById(txnId);
        log.info("END - [GET] [/payments/iuse/transactions/{}]", txnId);
        return response;
    }
}
```

#### TransactionResponse.java (DTO as record with full @Schema documentation)

```java
import io.swagger.v3.oas.annotations.media.Schema;

import java.math.BigDecimal;

@Schema(
    name = "TransactionResponse",
    description = "Response payload for a payment transaction.",
    example = """
        {
          "txnId": "TXN-20240101-00123",
          "amount": 150.00,
          "status": "COMPLETED"
        }
        """)
public record TransactionResponse(

    @Schema(
        description = "Unique identifier of the transaction.",
        requiredMode = Schema.RequiredMode.REQUIRED,
        example = "TXN-20240101-00123")
    String txnId,

    @Schema(
        description = "Monetary amount of the transaction.",
        requiredMode = Schema.RequiredMode.REQUIRED,
        example = "150.00")
    BigDecimal amount,

    @Schema(
        description = "Current status of the transaction (e.g. PENDING, COMPLETED, FAILED).",
        requiredMode = Schema.RequiredMode.REQUIRED,
        example = "COMPLETED")
    String status
) {}
```

---

### Summary of Changes

| Component | Issue | Action |
|---|---|---|
| `TransactionControllerImpl` | `@Tag` and `@Operation` in implementation | Removed both annotations |
| `TransactionControllerImpl` | Missing `@Slf4j`, `@RequiredArgsConstructor` | Added both, added `private final` service field |
| `TransactionControllerImpl` | Missing START/END logs | Added log statements in method |
| `TransactionController` (interface) | Missing `@Tag` at class level | Added `@Tag(name, description)` |
| `TransactionController` (interface) | Missing `@Operation` on method | Added with `summary`, `description`, `responses` |
| `TransactionController` (interface) | Missing `@Parameter` on path variable | Added with `description`, `required`, `example` |
| `TransactionController` (interface) | Missing `@ErrorResponses` | Added `NOT_FOUND / BUSINESS_SERVICE` |
| `TransactionController` (interface) | Missing `@SecurityRequirement` | Added `authB2C` |
| `TransactionResponse` | No `@Schema` annotations anywhere | Added class-level and field-level `@Schema` |
| `TransactionResponse` | Mutable class with no Lombok | Converted to immutable record |
