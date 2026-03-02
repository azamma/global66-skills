# Swagger Audit Report — TransactionController

---

## Resumen de Auditoría

**Status: NON_COMPLIANT**

Se encontraron 9 violaciones: 5 críticas y 4 advertencias.
El código requiere refactorización completa antes de ser aceptado.

---

## Cumplimientos

Ninguno. El código auditado no cumple ninguna regla de Swagger de Global66 en su estado actual.

---

## Errores Críticos (bloqueantes)

**[CRITICAL-1] `TransactionControllerImpl.java` — `@Tag` en la implementación.**

`@Tag(name = "Transactions", description = "Payment transaction operations")` está declarado
sobre el método `getTransaction` dentro de `TransactionControllerImpl`. Las anotaciones Swagger
no deben existir en ninguna clase anotada con `@RestController`. Deben vivir exclusivamente en
la interfaz.

Fix: Eliminar `@Tag` de `TransactionControllerImpl` y moverlo al nivel de clase en `TransactionController`.

---

**[CRITICAL-2] `TransactionControllerImpl.java` — `@Operation` en la implementación.**

`@Operation(summary = "Get transaction by ID", description = "Returns a transaction")` está
declarado dentro de `TransactionControllerImpl`. Igual que `@Tag`, `@Operation` es una
anotación de contrato de API y pertenece únicamente a la interfaz.

Fix: Eliminar `@Operation` de `TransactionControllerImpl` y moverlo al método correspondiente
en `TransactionController`.

---

**[CRITICAL-3] `TransactionController.java` (interfaz) — `@Tag` ausente a nivel de clase.**

La interfaz `TransactionController` no tiene la anotación `@Tag(name, description)` a nivel de
clase. Esta anotación es obligatoria en toda interfaz de controller para que el endpoint aparezca
correctamente agrupado en la UI de Swagger.

Fix: Agregar `@Tag(name = "Transactions", description = "Payment transaction operations")` sobre
la declaración `public interface TransactionController`.

---

**[CRITICAL-4] `TransactionController.java` (interfaz) — `@Operation` ausente en el método.**

El método `getTransaction` en la interfaz no tiene `@Operation`. Tanto `summary` como
`description` son obligatorios para documentar el comportamiento del endpoint.

Fix: Agregar `@Operation(summary = "Get transaction by ID", description = "Returns the transaction detail for the given ID")` sobre `getTransaction` en la interfaz.

---

**[CRITICAL-5] `TransactionController.java` (interfaz) — `@Parameter` ausente para `txnId`.**

El parámetro `txnId` en la firma del método de la interfaz no tiene `@Parameter(description, required, example)`. Sin esta anotación, Swagger no mostrará descripción ni ejemplo para el path variable.

Fix: Agregar `@Parameter(description = "Unique transaction identifier", required = true, example = "TXN-2024-001")` antes del argumento `txnId` en la interfaz.

---

## Advertencias

**[WARNING-1] `TransactionController.java` (interfaz) — `@ErrorResponses` ausente.**

Un endpoint de consulta por ID normalmente puede lanzar un error de negocio `NOT_FOUND` cuando
la transacción no existe. Falta la anotación `@ErrorResponses` con los errores esperados.

Fix: Agregar `@ErrorResponses(values = { @ErrorResponse(reason = ErrorReason.NOT_FOUND, source = ErrorSource.BUSINESS_SERVICE) })` sobre el método en la interfaz.

---

**[WARNING-2] `TransactionController.java` (interfaz) — `@SecurityRequirement` ausente.**

Un endpoint de transacciones de pagos es un recurso protegido. Falta declarar el esquema de
autenticación requerido.

Fix: Agregar `@SecurityRequirement(name = "authB2C")` sobre el método en la interfaz (o
`authB2B` si es consumido por otro servicio interno).

---

**[WARNING-3] `TransactionResponse.java` — `@Schema` ausente a nivel de clase.**

El DTO `TransactionResponse` no tiene `@Schema(name, description, example)` a nivel de clase.
Sin esta anotación, Swagger no mostrará descripción ni ejemplo del objeto en la documentación.

Fix: Agregar `@Schema(name = "TransactionResponse", description = "Transaction detail response", example = "{\"txnId\": \"TXN-2024-001\", \"amount\": 15000.00, \"status\": \"COMPLETED\"}")` sobre la clase.

---

**[WARNING-4] `TransactionResponse.java` — `@Schema` ausente en todos los campos.**

Los campos `txnId`, `amount` y `status` no tienen `@Schema(description, example)`. Swagger
mostrará los campos sin contexto semántico.

Fix: Agregar `@Schema` individual con `description` y `example` en cada campo del DTO.

---

## Codigo Corregido

### `TransactionController.java` (interfaz — contrato completo)

```java
import com.global.rest.exception.annotation.ErrorResponse;
import com.global.rest.exception.annotation.ErrorResponses;
import com.global.rest.exception.enums.ErrorReason;
import com.global.rest.exception.enums.ErrorSource;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.web.bind.annotation.PathVariable;

@Tag(name = "Transactions", description = "Payment transaction operations")
public interface TransactionController {

    @ErrorResponses(
        values = {
            @ErrorResponse(reason = ErrorReason.NOT_FOUND, source = ErrorSource.BUSINESS_SERVICE)
        })
    @Operation(
        summary = "Get transaction by ID",
        description = "Returns the transaction detail for the given ID")
    @SecurityRequirement(name = "authB2C")
    TransactionResponse getTransaction(
        @Parameter(description = "Unique transaction identifier", required = true, example = "TXN-2024-001")
            @PathVariable String txnId);
}
```

---

### `TransactionControllerImpl.java` (implementacion — sin anotaciones Swagger)

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
        TransactionResponse response = TransactionPresentationMapper.INSTANCE.toResponse(
            transactionService.findById(txnId));
        log.info("END - [GET] [/payments/iuse/transactions/{}]", txnId);
        return response;
    }
}
```

---

### `TransactionResponse.java` (DTO con Schema completo)

```java
import io.swagger.v3.oas.annotations.media.Schema;
import java.math.BigDecimal;

@Schema(
    name = "TransactionResponse",
    description = "Transaction detail response",
    example = """
        {
          "txnId": "TXN-2024-001",
          "amount": 15000.00,
          "status": "COMPLETED"
        }
        """)
public class TransactionResponse {

    @Schema(description = "Unique transaction identifier", example = "TXN-2024-001")
    private String txnId;

    @Schema(description = "Transaction amount in the operation currency", example = "15000.00")
    private BigDecimal amount;

    @Schema(description = "Current status of the transaction", example = "COMPLETED")
    private String status;
}
```

---

## Tabla Resumen de Violaciones

| # | Archivo | Regla Violada | Severidad |
|---|---------|---------------|-----------|
| 1 | `TransactionControllerImpl.java` | `@Tag` en la implementacion | CRITICAL |
| 2 | `TransactionControllerImpl.java` | `@Operation` en la implementacion | CRITICAL |
| 3 | `TransactionController.java` | `@Tag` ausente a nivel de clase en la interfaz | CRITICAL |
| 4 | `TransactionController.java` | `@Operation` ausente en el metodo de la interfaz | CRITICAL |
| 5 | `TransactionController.java` | `@Parameter` ausente para `txnId` en la interfaz | CRITICAL |
| 6 | `TransactionController.java` | `@ErrorResponses` ausente | WARNING |
| 7 | `TransactionController.java` | `@SecurityRequirement` ausente | WARNING |
| 8 | `TransactionResponse.java` | `@Schema` ausente a nivel de clase | WARNING |
| 9 | `TransactionResponse.java` | `@Schema` ausente en los campos `txnId`, `amount`, `status` | WARNING |

---

## Notas Adicionales

1. **Logging agregado en la implementacion**: La implementacion original no tenia logs START/END.
   Se agregaron siguiendo SGSI-POL-005 como parte de la correccion integral.

2. **`@PathVariable` en la interfaz**: El metodo original en la interfaz no tenia `@PathVariable`
   en el parametro `txnId`. Spring MVC requiere que las anotaciones de binding esten presentes
   en la interfaz o en la implementacion; se recomienda declararlas en ambos lugares para
   claridad del contrato.

3. **`TransactionResponse` como record**: El skill recomienda usar `record` para DTOs de respuesta
   inmutables. Si se migra a `record`, la anotacion `@Schema` se coloca en cada componente del
   constructor canonico, no con `@Schema` a nivel de campo.

   ```java
   public record TransactionResponse(
       @Schema(description = "Unique transaction identifier", example = "TXN-2024-001")
           String txnId,
       @Schema(description = "Transaction amount in the operation currency", example = "15000.00")
           BigDecimal amount,
       @Schema(description = "Current status of the transaction", example = "COMPLETED")
           String status) {}
   ```
