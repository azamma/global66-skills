# Unit Test Patterns — Global66

## Core Philosophy

Tests document behavior. The test name must be a full specification of the scenario — if you need
to read the test body to understand what it's testing, the name is wrong. No comments ever.

## Test Class Structure

```java
@ExtendWith(MockitoExtension.class)
@DisplayName("{ClassName} Tests")
class {ClassName}Test {

    @Mock private DependencyOne mockDependencyOne;
    @Mock private DependencyTwo mockDependencyTwo;

    @InjectMocks private {ClassName} subject;

    @Nested
    @DisplayName("{publicMethodName}")
    class {PublicMethodName}Tests {

        @Test
        void Given_<InputOrState>_When_<Action>_Then_<Outcome>() { ... }
    }
}
```

## Naming Convention

**Pattern**: `Given_<InputOrState>_When_<Action>_Then_<Outcome>`

```
// FORBIDDEN
void testCreateUser() { ... }
void test1() { ... }
void shouldReturnUser() { ... }
void caseWhenUserExists() { ... }

// CORRECT
void Given_ValidUserData_When_CreateUser_Then_ReturnsSavedData()
void Given_ExistingEmail_When_CreateUser_Then_ThrowsEmailAlreadyRegisteredException()
void Given_InactiveAccount_When_UpdatePermission_Then_ThrowsAccountNotActiveException()
void Given_ValidUserId_When_GetLastLocation_Then_ReturnsLastLocationRecord()
```

---

## JSON Fixtures

Complex domain objects must be loaded from JSON files, never constructed inline.

### FileUtils — Gold Standard Loader

Use the project's `FileUtils` utility (see `ms-geolocation` as reference):

```java
// com.global.{domain}.util.FileUtils
public final class FileUtils {
    private static final String TEST_DATA_ROOT_PATH = "src/test/resources/";

    private FileUtils() {
        throw new IllegalStateException("Utility class");
    }

    public static <T> T loadObject(String jsonFile, Class<T> clazz) {
        Path path = Paths.get(TEST_DATA_ROOT_PATH.concat(jsonFile));
        try {
            String content = Files.readString(path);
            return ObjectMapperUtils.loadObject(content, clazz);
        } catch (IOException e) {
            throw new RuntimeException(e);
        }
    }
}
```

**Usage in tests — define a private helper per type:**

```java
private LocationData loadLocationData(String fileName) {
    return FileUtils.loadObject("data/domain/data/" + fileName, LocationData.class);
}

private LocationEntity loadLocationEntity() {
    return FileUtils.loadObject("data/domain/entity/LocationEntityData.json", LocationEntity.class);
}
```

### Fixture Path Convention

**Root**: `src/test/resources/data/{layer}/{type}/`

```
src/test/resources/data/
├── domain/
│   ├── data/             # *Data objects (business layer)
│   ├── entity/           # *Entity objects (persistence layer)
│   └── external_request/ # External API responses
├── client/
│   └── dto/              # Client DTO responses
└── presentation/
    └── consumer/         # SQS message DTOs
```

**Naming**: `ClassName-SCENARIO.json` — uppercase snake_case scenario suffix

```
LocationData-VALID_BOGOTA.json
LocationData-NULL_COORDINATES.json
LocationData-NULL_CUSTOMER_ID.json
LocationData-WITH_TRANSACTION.json
LocationData-FAR_DISTANCE.json
HereGeocodeBasicLocationResponse-VALID.json
HereGeocodeBasicLocationResponse-NULL_POSTAL.json
LastLocationDataRecord-NULL_GEOCODING.json
```

---

## Service Test Example

```java
@ExtendWith(MockitoExtension.class)
class GeoCodeServiceImplTest {

    @Mock private HereClient hereClient;
    @InjectMocks private GeoCodeServiceImpl geoCodeServiceImpl;

    @Test
    void Given_ValidResponse_When_GetBasicLocation_Then_ReturnMappedResponse() {
        HereGeocodeBasicLocationResponse mockResponse = FileUtils.loadObject(
            "data/domain/external_request/here/HereGeocodeBasicLocationResponse-VALID.json",
            HereGeocodeBasicLocationResponse.class);

        when(hereClient.geocode("addr", "city", "country")).thenReturn(mockResponse);

        HereGeocodeBasicLocationResponse result =
            geoCodeServiceImpl.getBasicLocation("addr", "city", "country");

        assertNotNull(result);
        assertEquals("7500000", result.postalCode());
        assertEquals(-33.4489, result.latitude());
    }

    @Test
    void Given_NullPostalCodeInResponse_When_GetBasicLocation_Then_ReturnResponseWithSafeDefaults() {
        HereGeocodeBasicLocationResponse mockResponse = FileUtils.loadObject(
            "data/domain/external_request/here/HereGeocodeBasicLocationResponse-NULL_POSTAL.json",
            HereGeocodeBasicLocationResponse.class);

        when(hereClient.geocode("addr", "city", "country")).thenReturn(mockResponse);

        HereGeocodeBasicLocationResponse result =
            geoCodeServiceImpl.getBasicLocation("addr", "city", "country");

        assertNotNull(result.postalCode());
    }
}
```

---

## Parametrized Tests

### @ParameterizedTest with @CsvSource — inline fixture file paths

Use when multiple scenarios differ only in which fixture file is loaded:

```java
@Nested
@DisplayName("Mandatory Field Validation")
class MandatoryFieldValidationTests {

    @ParameterizedTest(
        name = "Given null {0}, when saving, then skips processing without calling dependencies")
    @CsvSource({
        "customerId, data/domain/data/LocationData-NULL_CUSTOMER_ID.json",
        "email,      data/domain/data/LocationData-NULL_EMAIL.json",
        "fingerprint, data/domain/data/LocationData-NULL_FINGERPRINT.json",
        "latitude,   data/domain/data/LocationData-NULL_LATITUDE.json",
        "longitude,  data/domain/data/LocationData-NULL_LONGITUDE.json"
    })
    void Given_NullMandatoryField_When_Save_Then_LogsDebugAndSkipsSave(
            String fieldName, String jsonFilePath) {
        LocationData locationData = FileUtils.loadObject(jsonFilePath, LocationData.class);

        locationService.save(locationData);

        verifyNoInteractions(authServerClient);
        verifyNoInteractions(locationPersistence);
    }
}
```

### @ParameterizedTest with @MethodSource — multi-fixture scenarios

Use when each scenario requires multiple fixture files or needs a descriptive scenario name:

```java
@ParameterizedTest(name = "{0}")
@MethodSource("provideInvalidCoordinatesScenarios")
void Given_InvalidCoordinatesInLocations_When_DetectAndAlert_Then_LogWarningAndReturn(
        String scenarioName, String currentLocationFile, String lastLocationFile) {
    LocationData current = FileUtils.loadObject(
        "data/domain/data/" + currentLocationFile, LocationData.class);
    LastLocationDataRecord last = FileUtils.loadObject(
        "data/domain/data/" + lastLocationFile, LastLocationDataRecord.class);

    when(locationPersistence.findLastLocationWithEventSource(any(), any(), any()))
        .thenReturn(Optional.of(last));

    assertThatCode(() -> haversineFraudService.detectAndAlertOnLocationChange(current))
        .doesNotThrowAnyException();

    verify(haversineFraudSegmentService, never()).sendAlert(any(), any(), anyDouble(), any());
}

static Stream<Arguments> provideInvalidCoordinatesScenarios() {
    return Stream.of(
        Arguments.of("Null coordinates in current location",
            "LocationData-NULL_COORDINATES.json", "LastLocationDataRecord-VALID.json"),
        Arguments.of("Null coordinates in last location",
            "LocationData-VALID_BOGOTA.json", "LastLocationDataRecord-NULL_COORDINATES.json"),
        Arguments.of("Invalid latitude in current location",
            "LocationData-INVALID_LATITUDE.json", "LastLocationDataRecord-VALID.json")
    );
}
```

---

## Persistence Test — ArgumentCaptor

Capture the exact object passed to `save()` and assert its internal state:

```java
@ExtendWith(MockitoExtension.class)
class LocationGeocodingPersistenceImplTest {

    @InjectMocks private LocationGeocodingPersistenceImpl locationGeocodingPersistence;
    @Mock private LocationRepository locationRepository;

    private LocationEntity loadLocationEntity() {
        return FileUtils.loadObject("data/domain/entity/LocationEntityData.json", LocationEntity.class);
    }

    @Test
    void Given_ValidLocationId_When_SaveGeocoding_Then_AssociatesGeocodingAndSavesLocation() {
        LocationEntity locationEntity = loadLocationEntity();

        when(locationRepository.findById(1)).thenReturn(Optional.of(locationEntity));
        when(locationRepository.save(any(LocationEntity.class))).thenReturn(locationEntity);

        locationGeocodingPersistence.saveGeocoding(1, "CO", "Colombia", "Bogotá", "{...}");

        ArgumentCaptor<LocationEntity> captor = ArgumentCaptor.forClass(LocationEntity.class);
        verify(locationRepository).save(captor.capture());

        LocationEntity saved = captor.getValue();
        assertThat(saved.getGeocoding()).isNotNull();
        assertThat(saved.getGeocoding().getCountryCode()).isEqualTo("CO");
        assertThat(saved.getGeocoding().getCity()).isEqualTo("Bogotá");
    }

    @Test
    void Given_NonExistingLocationId_When_SaveGeocoding_Then_DoNotSave() {
        when(locationRepository.findById(1)).thenReturn(Optional.empty());

        locationGeocodingPersistence.saveGeocoding(1, "CO", "Colombia", "Bogotá", "{...}");

        verify(locationRepository, never()).save(any(LocationEntity.class));
    }
}
```

---

## Controller Test Example

```java
@ExtendWith(MockitoExtension.class)
@DisplayName("GeoCodeControllerImpl Tests")
class GeoCodeControllerImplTest {

    @Mock private GeoCodeService mockGeoCodeService;
    @InjectMocks private GeoCodeControllerImpl geoCodeController;

    @Nested
    @DisplayName("basicGeoInfo")
    class BasicGeoInfoTests {

        @Test
        void Given_ValidAddressCityCountry_When_BasicGeoInfo_Then_DelegatesToService() {
            geoCodeController.basicGeoInfo("Av. Providencia 1234", "Santiago", "Chile");
            verify(mockGeoCodeService).getBasicLocation("Av. Providencia 1234", "Santiago", "Chile");
        }
    }
}
```

---

## Coverage Requirements

For each method or class being tested, cover all 4 mandatory case types:

| Type | Description | Example suffix |
|------|-------------|----------------|
| **Happy Path** | Valid input, expected outcome | `Then_ReturnsSavedData` |
| **Negative / Exception** | Invalid input or constraint violation | `Then_ThrowsNotFoundException` |
| **Edge Cases** | Boundaries, nulls, empty collections | `Then_ReturnsEmpty`, `Then_HandlesNullGracefully` |
| **Branch Conditions** | Each new `if`/`else`/`map`/`orElse` | `Then_UpdatesExistingPermission`, `Then_CreatesNewPermission` |

Aim to cover ~80% of modified/new lines.

---

## When Working from a Git Diff

Scope: **only new or modified classes/methods** — never touch unchanged logic.
Action types: `CREATE_FILE` (new test class) or `EXTEND_FILE` (add to existing).
Prohibited: `OVERWRITE_EXISTING_LOGIC` — always append or insert, never replace existing tests.

Workflow:
1. **Parse** the diff — identify new classes, modified methods, new branches (lines starting with `+`)
2. **Check** if a test file already exists for each changed file
   - Exists → add new `@Nested` blocks or `@Test` methods
   - Doesn't exist → create a new test class from scratch
3. **Apply the 4 coverage types** for each modified method
4. **Generate JSON fixtures** for any complex DTOs touched in the diff
5. **Output a summary** in this format:

```
TEST GENERATION SUMMARY
───────────────────────
Files created:   [PaymentServiceImplTest.java]
Files modified:  [DevicePermissionServiceImplTest.java]
Methods added:   [Given_ValidPayment_When_Create_Then_Returns,
                  Given_InsufficientBalance_When_Create_Then_ThrowsException]
Fixtures generated: [PaymentData-VALID.json, PaymentData-INSUFFICIENT_BALANCE.json]
Coverage: createPayment() — 3 branches covered (happy path, exception, edge case null amount)
```

---

## Common Mistakes to Avoid

```java
// BAD: Inline DTO construction
UserData userData = new UserData();
userData.setEmail("test@test.com");
userData.setAge(25);

// GOOD: Load from JSON fixture
UserData userData = FileUtils.loadObject("data/domain/data/UserData-VALID.json", UserData.class);
```

```java
// BAD: Wildcard static imports
import static org.mockito.Mockito.*;
import static org.assertj.core.api.Assertions.*;

// GOOD: Explicit imports
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.assertj.core.api.Assertions.assertThatCode;
```

```java
// BAD: Comments
// Arrange
UserData userData = FileUtils.loadObject("...", UserData.class);
// Act
UserData result = userService.create(userData);
// Assert
assertThat(result).isNotNull();

// GOOD: Self-explanatory code, no comments
UserData userData = FileUtils.loadObject("data/domain/data/UserData-VALID.json", UserData.class);
UserData result = createUserService.createUser(userData);
assertThat(result.getId()).isNotNull();
assertThat(result.getEmail()).isEqualTo(userData.getEmail());
```
