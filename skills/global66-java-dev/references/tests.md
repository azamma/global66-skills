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

## JSON Fixtures

Complex domain objects must be loaded from JSON files, never constructed inline.

**Path**: `src/test/resources/{layer}/{domain}/{ClassName}-{STATE}.json`

**Naming**:
- `UserData-VALID.json`
- `UserData-SAVED.json`
- `DevicePermissionData-INACTIVE.json`
- `LocationData-WITHOUT_GEOCODING.json`

**Helper method (define once in test or base class)**:
```java
private <T> T loadJson(String path, Class<T> type) {
    try {
        String json = new String(
            Objects.requireNonNull(
                getClass().getClassLoader().getResourceAsStream(path)
            ).readAllBytes()
        );
        return ObjectMapperUtils.loadObject(json, type);
    } catch (IOException e) {
        throw new RuntimeException("Failed to load test fixture: " + path, e);
    }
}
```

---

## Service Test Example

```java
@ExtendWith(MockitoExtension.class)
@DisplayName("LocationGeocodingServiceImpl Tests")
class LocationGeocodingServiceImplTest {

    @Mock private LocationGeocodingPersistence mockLocationGeocodingPersistence;
    @InjectMocks private LocationGeocodingServiceImpl locationGeocodingService;

    @Nested
    @DisplayName("saveGeocodingResult")
    class SaveGeocodingResultTests {

        @Test
        void Given_ValidGeocodingData_When_SaveGeocodingResult_Then_DelegatesToPersistence() {
            Integer locationId = 12345;
            String countryCode = "CO";
            String countryName = "Colombia";
            String city = "Bogotá";
            BigDataCloudReverseGeocodingResponse response =
                loadJson("geocoding/BigDataCloudReverseGeocodingResponse-VALID.json",
                    BigDataCloudReverseGeocodingResponse.class);
            String expectedJson = ObjectMapperUtils.toString(response);

            locationGeocodingService.saveGeocodingResult(
                locationId, countryCode, countryName, city, response);

            verify(mockLocationGeocodingPersistence)
                .saveGeocoding(locationId, countryCode, countryName, city, expectedJson);
        }

        @Test
        void Given_NullResponse_When_SaveGeocodingResult_Then_PersistenceCalledWithNullJson() {
            locationGeocodingService.saveGeocodingResult(1, "CL", "Chile", "Santiago", null);
            verify(mockLocationGeocodingPersistence)
                .saveGeocoding(1, "CL", "Chile", "Santiago", null);
        }
    }
}
```

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

## Persistence Test Example

```java
@ExtendWith(MockitoExtension.class)
@DisplayName("UserPersistenceImpl Tests")
class UserPersistenceImplTest {

    @Mock private UserRepository mockUserRepository;
    @InjectMocks private UserPersistenceImpl userPersistence;

    @Nested
    @DisplayName("findById")
    class FindByIdTests {

        @Test
        void Given_ExistingUserId_When_FindById_Then_ReturnsMappedData() {
            Integer userId = 1;
            UserEntity entity = loadJson("user/UserEntity-ACTIVE.json", UserEntity.class);
            when(mockUserRepository.findById(userId)).thenReturn(Optional.of(entity));

            Optional<UserData> result = userPersistence.findById(userId);

            assertThat(result).isPresent();
            assertThat(result.get().getId()).isEqualTo(userId);
        }

        @Test
        void Given_NonExistentUserId_When_FindById_Then_ReturnsEmpty() {
            when(mockUserRepository.findById(999)).thenReturn(Optional.empty());

            Optional<UserData> result = userPersistence.findById(999);

            assertThat(result).isEmpty();
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
UserData userData = loadJson("user/UserData-VALID.json", UserData.class);
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
```

```java
// BAD: Comments
// Arrange
UserData userData = loadJson("...", UserData.class);
// Act
UserData result = userService.create(userData);
// Assert
assertThat(result).isNotNull();

// GOOD: Self-explanatory code, no comments
UserData userData = loadJson("user/UserData-VALID.json", UserData.class);
UserData result = createUserService.createUser(userData);
assertThat(result.getId()).isNotNull();
assertThat(result.getEmail()).isEqualTo(userData.getEmail());
```
