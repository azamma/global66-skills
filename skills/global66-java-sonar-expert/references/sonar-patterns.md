# SonarQube — Coverage & Issues Guide

---

## Part 1: Coverage Gaps (git diff + Sonar report)

### Workflow

1. **Parse** — identify lines/methods flagged by Sonar and cross-reference with git diff.
   Scope is **only new or modified methods**. Never touch coverage of unrelated code.

2. **Locate test file** — check if `{ClassName}Test.java` already exists.
   - Exists → **extend** it, add `@Nested` class for the new method
   - Missing → **create** it from scratch

3. **Generate fixtures** — for any complex DTO/domain object, create a JSON file:
   - Path: `src/test/resources/{objectName}-{STATE}.json`
   - Examples: `payment-data-VALID.json`, `user-data-NOT_FOUND.json`
   - Load in tests with `ObjectMapperUtils.loadObject(...)` or `objectMapper.readValue(...)`
   - Never construct complex objects inline with setters

4. **Write tests** — one `@Nested` class per public method, covering:
   - Happy path (expected success)
   - Each exception branch (`ensure*`/`verify*` throwing `BusinessException`)
   - Edge cases (null, empty list, Optional.empty())
   - Branch conditions (`is*`/`has*` returning true vs. false)

5. **Validate** — all new/modified lines have test coverage. Target: 100% of new lines.

### Test template

```java
@ExtendWith(MockitoExtension.class)
class PaymentServiceImplTest {

    @Mock private PaymentPersistence paymentPersistence;
    @Mock private UserPersistence userPersistence;

    @InjectMocks private PaymentServiceImpl paymentService;

    @Nested
    class CreatePayment {

        @Test
        void Given_ValidPayment_When_UserExists_Then_ReturnsSavedPayment() {
            // given
            PaymentData input = loadFixture("payment-data-VALID.json", PaymentData.class);
            PaymentData expected = loadFixture("payment-data-SAVED.json", PaymentData.class);
            when(userPersistence.existsById(input.getUserId())).thenReturn(true);
            when(paymentPersistence.save(input)).thenReturn(expected);

            // when
            PaymentData result = paymentService.createPayment(input);

            // then
            assertThat(result).isEqualTo(expected);
            verify(paymentPersistence).save(input);
        }

        @Test
        void Given_UnknownUser_When_CreatePayment_Then_ThrowsUserNotFoundException() {
            PaymentData input = loadFixture("payment-data-VALID.json", PaymentData.class);
            when(userPersistence.existsById(input.getUserId())).thenReturn(false);

            assertThatThrownBy(() -> paymentService.createPayment(input))
                .isInstanceOf(BusinessException.class)
                .extracting("errorCode")
                .isEqualTo(ErrorCode.USER_NOT_FOUND);
        }
    }
}
```

### Coverage output format

```
## Coverage Analysis

**Scope:** 3 new/modified methods from git diff
**Sonar uncovered lines:** 12 lines across 2 files

| Method | Class | Uncovered branches | Action |
|--------|----|----|----|
| createPayment | PaymentServiceImpl | isUserMissing=false, duplicate path | EXTEND existing test |
| findByUserId | PaymentServiceImpl | Optional.empty() branch | EXTEND existing test |
| processRefund | RefundServiceImpl | No test file | CREATE new test class |

**Fixtures created:**
- src/test/resources/payment-data-VALID.json
- src/test/resources/payment-data-SAVED.json
- src/test/resources/refund-data-VALID.json

[Test code follows]
```

---

## Part 2: Issues Resolution

Map Sonar rule codes to the Global66 fix pattern. Always apply the project's existing
conventions rather than generic Java solutions.

### Rule → Global66 Fix Mapping

| Sonar Rule | Issue | Global66 Fix |
|------------|-------|-------------|
| `java:S3776` | Cognitive Complexity > 15 | Extract to `ensure*/verify*/is*/has*/build*Exception` private methods per SRP pattern. The orchestration method should be ≤10 lines. |
| `java:S112` | Generic exception (`RuntimeException`) thrown | Replace with `BusinessException(ErrorCode.XXX, ...)` + extract to `build*Exception` factory method |
| `java:S106` | `System.out.println` | Replace with `@Slf4j` + `log.info/warn/error` following SGSI-POL-005 rules |
| `java:S1192` | Duplicated string literals | Extract to a `static final String` constant or an `enum`. If it's an error message, it belongs in `ErrorCode`. |
| `java:S107` | Too many parameters (>4) | Wrap parameters into a `*Data` domain object or a request DTO. Never introduce Builder unless it's a Lombok `@Builder` on an entity. |
| `java:S5976` | Duplicate test methods | Consolidate with `@ParameterizedTest` + `@MethodSource` or `@CsvSource`. Fixture JSON files can be parameterized by path. |
| `java:S2699` | Test with no assertions | Add AssertJ `assertThat(...)` or `verify(mock).method(...)` — never leave a test empty |
| `java:S2142` | `InterruptedException` swallowed | Add `Thread.currentThread().interrupt()` before re-throwing or logging |
| `java:S2095` | Resource not closed | Wrap in `try-with-resources`. Applies to streams, connections, readers. |
| `java:S1135` | TODO comment | Resolve or replace with a JIRA ticket reference comment: `// TODO [PROJ-123]: description` |
| `java:S1186` | Empty method body | Either implement, add `log.debug(...)`, or throw `UnsupportedOperationException` with a reason |
| `java:S4925` | `@Deprecated` without Javadoc | Add `/** @deprecated Use {@link NewClass} instead. */` |
| `java:S1130` | Redundant `throws` in signature | Remove unchecked exceptions from `throws` declaration |
| `java:S3457` | Printf format string mismatch | Fix argument count/types to match format string |
| `java:S5122` | CORS wildcard (`*`) | Restrict allowed origins to specific domains in `CorsConfiguration` |
| `java:S2077` | SQL injection risk | Replace string concatenation with `@Query` named parameters or `JpaRepository` methods |

### Severity-based priority

- **CRITICAL** (Vulnerabilities + Runtime Bugs): fix before anything else. Never commit with these open.
- **MAJOR** (SRP violations, complexity, duplication): apply the Global66 pattern directly. Don't introduce design patterns (Strategy, Template) unless the team already uses them.
- **MINOR** (naming, style): fix following the project's conventions, not generic Java style guides.

### Global66-specific notes

**Cognitive Complexity (S3776):** The fix is always the SRP semantic method pattern. Extract conditions
to `is*`/`has*`, validations to `ensure*`/`verify*`, and exception construction to `build*Exception`.
This reduces complexity and aligns with the architecture at the same time.

**Too Many Parameters (S107):** Never reach for Builder Pattern. Create a `*Data` domain object
in `domain/data/` and pass that instead. This also enforces the hexagonal layer boundary.

**Generic Exception (S112):** Replace all `throw new RuntimeException("message")` with:
```java
private BusinessException paymentNotFoundException(Integer paymentId) {
    return new BusinessException(ErrorCode.PAYMENT_NOT_FOUND, paymentId.toString());
}
```

**Duplicate Tests (S5976):** Use `@ParameterizedTest` only when the test logic is truly identical
and only the input data changes. Don't force it — three separate `@Test` methods with different
scenarios are better than a forced parameterized test with convoluted setup.

### Issues output format

```
## SonarQube Issues Report

| Severity | Rule | File | Count | Status |
|----------|------|------|-------|--------|
| CRITICAL | java:S112 | PaymentServiceImpl.java | 3 | Fixed |
| MAJOR | java:S3776 | CreatePaymentServiceImpl.java | 1 | Fixed |
| MINOR | java:S1192 | PaymentControllerImpl.java | 2 | Fixed |

**Technical Debt reduction:** 2h 15min
**Maintainability:** C → A

---

### java:S3776 — CreatePaymentServiceImpl.java (MAJOR)

**Problem:** `createPayment` method has cognitive complexity of 18 (threshold: 15)

**Fix:** Extract conditions to private methods following SRP naming
[corrected code block]

---

### java:S112 — PaymentServiceImpl.java (CRITICAL) × 3

**Problem:** `throw new RuntimeException(...)` in 3 methods

**Fix:** Replace with `BusinessException` factory methods
[corrected code block]
```
