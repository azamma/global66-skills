# Global66 Claude Code Skills

Repositorio de skills de Claude Code para el desarrollo de microservicios Java en Global66. Define estándares de arquitectura hexagonal, convenciones de código, y reglas de compliance para mantener calidad y consistencia en todos los proyectos.

## Propósito

Este repositorio contiene:
- **Skill `global66-java-dev`**: Instrucciones detalladas para que Claude Code genere código siguiendo los estándares de Global66
- **7 escenarios de evaluación**: Casos de prueba para validar la efectividad del skill
- **12 documentos de referencia**: Guías especializadas (SRP, @Transactional, SQS, Swagger, Liquibase, API REST, Cache, Exceptions, etc.)

## Uso Rápido

### Usar el skill en un microservicio

```bash
# Navegar al microservicio
cd /mnt/c/repos/ms-geolocation

# Claude Code automáticamente carga el skill global66-java-dev
# cuando detecta código Java en contexto Global66
```

### Ejemplos de prompts que activan el skill

- *"Crea un endpoint GET para buscar usuarios por email"*
- *"Refactoriza este servicio siguiendo los lineamientos de Global66"*
- *"Genera los tests unitarios para esta clase"*
- *"Revisa estos logs de este diff"* (compliance de SGSI-POL-005)
- *"Audita este controller Swagger"*
- *"Revisa este YAML de Liquibase"*

## Estructura del Repositorio

```
global66-skills/
├── skills/
│   └── global66-java-dev/
│       ├── SKILL.md              # ~590 líneas - definición principal del skill
│       ├── evals/
│       │   └── evals.json        # 7 casos de evaluación
│       └── references/           # 12 guías especializadas
│           ├── srp-patterns.md       # SRP y naming semántico
│           ├── transactional.md      # Reglas @Transactional
│           ├── logging.md            # SGSI-POL-005 compliance
│           ├── sqs.md                # SQS + 4 clases de trazabilidad
│           ├── swagger.md            # OpenAPI/Swagger
│           ├── liquibase.md          # G81-POL-033 migraciones DB
│           ├── api-client.md         # Retrofit client generator
│           ├── tests.md              # Patrones de testing
│           ├── sonar.md              # SonarQube coverage + issues
│           ├── checklist.md          # Checklist pre-entrega
│           ├── cache.md              # Caché Redis/Caffeine
│           ├── api-rest.md           # API REST guidelines
│           └── exceptions.md         # ApiRestException, ErrorReason
├── global66-java-dev-workspace/
│   └── iteration-1/            # Resultados de evaluación A/B
│       ├── endpoint-generation/    # Eval 1: Generar endpoint
│       ├── service-refactor/         # Eval 2: Refactorizar servicio
│       ├── unit-tests/               # Eval 3: Generar tests
│       ├── log-compliance/           # Eval 4: Auditar logs
│       ├── sqs-config/               # Eval 5: Configurar SQS FIFO
│       ├── swagger-audit/            # Eval 6: Auditar Swagger
│       └── liquibase-review/         # Eval 7: Revisar YAML
└── README.md                     # Este archivo
```

## Arquitectura Hexagonal (Resumen)

```
Presentation → Business → Persistence → Database
     ↘                          ↗
         Domain (Records/Data)
```

### Estructura de paquetes

```
com.global.{domain}/
├── presentation/          # Controllers (interfaces), DTOs, mappers
├── business/            # Services, @Transactional solo aquí
├── persistence/         # Repositories, Entities, puertos *Persistence
├── domain/              # *Data objects, external_request/ para APIs
├── client/              # Retrofit REST clients
├── config/              # Configuración Spring
└── enums/, util/        # Enums y utilidades compartidos
```

### Reglas críticas

| Regla | Descripción |
|-------|-------------|
| **Entities isolation** | `*Entity` solo en `persistence/`, nunca en business/presentation |
| **Persistence ports** | Services inyectan `*Persistence`, nunca repositories directamente |
| **@Transactional** | Solo en capa Business, `rollbackFor = Exception.class`, `readOnly` para lecturas |
| **Max 3 dependencias** | Máximo 3 campos `@RequiredArgsConstructor` por service |
| **Controllers thin** | Validar input → delegar → mapear response. Sin lógica de negocio |

## Casos de Evaluación

| ID | Escenario | Qué evalúa |
|----|-----------|------------|
| 1 | **Endpoint Generation** | Crear endpoint completo con las 4 capas hexagonales |
| 2 | **Service Refactor** | SRP naming, factorías de excepciones, persistence ports |
| 3 | **Unit Tests** | Patrón Given_When_Then, fixtures JSON, @Nested |
| 4 | **Log Compliance** | SGSI-POL-005, detección de PII, MDC async |
| 5 | **SQS Config** | 4 clases de trazabilidad, patrones FIFO |
| 6 | **Swagger Audit** | Anotaciones en interfaz, @ErrorResponses |
| 7 | **Liquibase Review** | G81-POL-033, nomenclatura, un concern por changeSet |

## Microservicio de Referencia

El proyecto `ms-geolocation` en `/mnt/c/repos/ms-geolocation` es el **Gold Standard**. Archivos clave para estudiar:

- `LocationEntity.java` - Entidad JPA con `@Comment`, índices correctos
- `LocationMapper.java` - MapStruct con deep path mapping
- `HereClientImpl.java` - Implementación de cliente Retrofit
- `SqsClientConfig.java` - Configuración SQS con trazabilidad
- `TracingMessageListenerWrapper.java` - Extracción de MDC/traceId
- `GeoCodeController.java` - Anotaciones Swagger en interfaz

## Documentos de Referencia

### SRP y Naming Semántico (`srp-patterns.md`)

Prefijos obligatorios para métodos:

| Prefijo | Uso | Ejemplo |
|---------|-----|---------|
| `ensure*` | Validación de precondición, lanza excepción | `ensureUserExists(userId)` |
| `verify*` | Validación compleja multi-paso | `verifyTransactionLegality(txn)` |
| `guardAgainst*` | Checks defensivos | `guardAgainstNullInput(data)` |
| `is*` / `has*` | Predicados booleanos | `isActive()`, `hasPermissions()` |
| `fetch*` / `require*` | Obtener o lanzar NOT_FOUND | `fetchUserById(id)` |
| `find*` | Query que retorna `Optional` | `findByEmail(email)` |
| `build*Exception` | Fábricas de excepciones | `buildUserNotFoundException(id)` |

### @Transactional (`transactional.md`)

```java
// ✅ CORRECTO: Business layer, público, rollback explícito
@Override
@Transactional(rollbackFor = Exception.class)
public PaymentData processPayment(PaymentData payment) { }

// ✅ LECTURA: readOnly = true
@Override
@Transactional(readOnly = true)
public List<UserData> findActiveUsers() { }
```

Reglas prohibidas:
- ❌ No en `@Repository`, `@Controller`, clientes Retrofit
- ❌ No métodos private/protected (Spring AOP los ignora)
- ❌ No llamadas HTTP dentro de `@Transactional`
- ❌ No `this.method()` a otro método `@Transactional`

### SQS Traceability (`sqs.md`)

4 clases requeridas en `config/sqs/`:

1. `SqsClientConfig.java` - Bean factory + registro del post-processor
2. `TracingMessageListenerWrapper.java` - Wrapper que extrae traceId
3. `TracingSqsEndpoint.java` - Endpoint que usa el wrapper
4. `TracingSqsListenerAnnotationBeanPostProcessor.java` - Post-processor para envolver listeners

### Liquibase YAML (`liquibase.md`)

Convenciones G81-POL-033:

- Tablas: minúscula singular (`user`, `transaction`)
- Clasificación MAE/TRX/DOM/TMP en remarks
- `primaryKeyName`: `PK_{table}_{column}`
- `indexName`: `IDX_{table}_{columns}`
- `constraintName`: `FK_{table}_{ref_table}_{column}`
- Un concern por changeSet (separar índices, FKs)

### Cache (`cache.md`)

Convenciones para caché con Redis/Caffeine:

- Nombres de caché: plural, camelCase, inglés (`countries`, `routePairCostConfig`)
- Keys sin parámetros: `'all'` para listas
- Keys compuestas: `{ #param1, #param2 }`
- TTL obligatorio para Redis
- Serialización con type info: `activateDefaultTyping(..., DefaultTyping.EVERYTHING)`
- Self-injection: `@Scope(proxyMode = ScopedProxyMode.TARGET_CLASS)`

### API REST (`api-rest.md`)

Convenciones para endpoints REST:

- Recursos: plural, minúscula, kebab-case (`/customers`, `/personal-info`)
- Prefijos: `b2c`, `b2b`, `bo`, `ext`, `iuse`, `sfc`, `notification`, `cron`
- Versionado: header `X-API-VERSION` (default v1)
- User ID de token para b2c/b2b/bo, nunca del body
- iuse/sfc NO expuestos en API Gateway

### Exception Handling (`exceptions.md`)

Manejo de excepciones con `ApiRestException`:

```java
throw ApiRestException.builder()
    .reason(ErrorReason.CUSTOMER_NOT_FOUND)
    .source(ErrorSource.BUSINESS_SERVICE)
    .build();
```

- NO crear enums locales de ErrorReason/ErrorSource
- Usar TODO: `// TODO: CUSTOMER_PLAN_NOT_FOUND (NOT_FOUND)`
- ErrorSource por capa: BUSINESS_SERVICE, DATA_REPOSITORY, REST_CONTROLLER, HTTP_CLIENT_*

## Contribuir

Para modificar el skill:

1. **Actualizar `SKILL.md`**: Si cambian las condiciones de activación
2. **Agregar referencias**: Crear nuevo `.md` en `references/`
3. **Actualizar `evals.json`**: Agregar nuevos casos de prueba
4. **Ejecutar evaluaciones**: Comparar outputs con/sin skill

### Template para nuevas referencias

Cada documento de referencia debe incluir:
- Resumen de política/regla
- Ejemplos Gold Standard (de ms-geolocation)
- Violaciones comunes con before/after
- Formato de salida para revisiones (git diff audits)

---

**Última revisión**: Marzo 2025
**Mantenedor**: Equipo de Arquitectura Global66
**Skill version**: global66-java-dev v1.0
