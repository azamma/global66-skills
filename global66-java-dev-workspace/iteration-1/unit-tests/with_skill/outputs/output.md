# Unit Tests — DevicePermissionServiceImpl

## Test Class

**File:** `src/test/java/com/global/device/business/impl/DevicePermissionServiceImplTest.java`

```java
package com.global.device.business.impl;

import com.global.device.domain.data.DevicePermissionData;
import com.global.device.persistence.DevicePermissionPersistence;
import com.global.device.persistence.UserPersistence;
import com.global.rest.exception.BusinessException;
import com.global.rest.exception.ErrorCode;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.io.IOException;
import java.util.Objects;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
@DisplayName("DevicePermissionServiceImpl Tests")
class DevicePermissionServiceImplTest {

    @Mock private DevicePermissionPersistence mockDevicePermissionPersistence;
    @Mock private UserPersistence mockUserPersistence;

    @InjectMocks private DevicePermissionServiceImpl subject;

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

    @Nested
    @DisplayName("registerDevicePermission")
    class RegisterDevicePermissionTests {

        @Test
        void Given_UserExistsAndNoExistingPermission_When_RegisterDevicePermission_Then_SavesNewPermission() {
            Integer userId = 1;
            DevicePermissionData incoming =
                loadJson("business/device/DevicePermissionData-INCOMING.json", DevicePermissionData.class);
            DevicePermissionData saved =
                loadJson("business/device/DevicePermissionData-SAVED.json", DevicePermissionData.class);

            when(mockUserPersistence.existsById(userId)).thenReturn(true);
            when(mockDevicePermissionPersistence.findByUserIdAndFingerprint(userId, incoming.getFingerprint()))
                .thenReturn(Optional.empty());
            when(mockDevicePermissionPersistence.save(incoming)).thenReturn(saved);

            DevicePermissionData result = subject.registerDevicePermission(userId, incoming);

            assertThat(result).isEqualTo(saved);
            verify(mockDevicePermissionPersistence).save(incoming);
        }

        @Test
        void Given_UserExistsAndPermissionAlreadyExists_When_RegisterDevicePermission_Then_UpdatesExistingPermission() {
            Integer userId = 1;
            DevicePermissionData incoming =
                loadJson("business/device/DevicePermissionData-INCOMING.json", DevicePermissionData.class);
            DevicePermissionData existing =
                loadJson("business/device/DevicePermissionData-EXISTING.json", DevicePermissionData.class);
            DevicePermissionData updated =
                loadJson("business/device/DevicePermissionData-UPDATED.json", DevicePermissionData.class);

            when(mockUserPersistence.existsById(userId)).thenReturn(true);
            when(mockDevicePermissionPersistence.findByUserIdAndFingerprint(userId, incoming.getFingerprint()))
                .thenReturn(Optional.of(existing));
            when(mockDevicePermissionPersistence.save(existing)).thenReturn(updated);

            DevicePermissionData result = subject.registerDevicePermission(userId, incoming);

            assertThat(result).isEqualTo(updated);
            assertThat(existing.getPermissionStatus()).isEqualTo(incoming.getPermissionStatus());
            assertThat(existing.getPermissionType()).isEqualTo(incoming.getPermissionType());
            verify(mockDevicePermissionPersistence).save(existing);
        }

        @Test
        void Given_UserDoesNotExist_When_RegisterDevicePermission_Then_ThrowsUserNotFoundException() {
            Integer userId = 99;
            DevicePermissionData incoming =
                loadJson("business/device/DevicePermissionData-INCOMING.json", DevicePermissionData.class);

            when(mockUserPersistence.existsById(userId)).thenReturn(false);

            assertThatThrownBy(() -> subject.registerDevicePermission(userId, incoming))
                .isInstanceOf(BusinessException.class)
                .satisfies(ex -> {
                    BusinessException businessEx = (BusinessException) ex;
                    assertThat(businessEx.getErrorCode()).isEqualTo(ErrorCode.USER_NOT_FOUND);
                    assertThat(businessEx.getMessage()).contains(userId.toString());
                });

            verifyNoInteractions(mockDevicePermissionPersistence);
        }

        @Test
        void Given_UserExistsAndPermissionAlreadyExists_When_RegisterDevicePermission_Then_MutatesExistingBeforeSaving() {
            Integer userId = 1;
            DevicePermissionData incoming =
                loadJson("business/device/DevicePermissionData-INCOMING.json", DevicePermissionData.class);
            DevicePermissionData existing =
                loadJson("business/device/DevicePermissionData-EXISTING.json", DevicePermissionData.class);

            when(mockUserPersistence.existsById(userId)).thenReturn(true);
            when(mockDevicePermissionPersistence.findByUserIdAndFingerprint(userId, incoming.getFingerprint()))
                .thenReturn(Optional.of(existing));
            when(mockDevicePermissionPersistence.save(existing)).thenReturn(existing);

            subject.registerDevicePermission(userId, incoming);

            verify(mockDevicePermissionPersistence).findByUserIdAndFingerprint(userId, incoming.getFingerprint());
            verify(mockDevicePermissionPersistence).save(existing);
        }
    }
}
```

---

## JSON Fixtures

### `src/test/resources/business/device/DevicePermissionData-INCOMING.json`

```json
{
  "fingerprint": "abc123fingerprint",
  "permissionStatus": "GRANTED",
  "permissionType": "BIOMETRIC"
}
```

### `src/test/resources/business/device/DevicePermissionData-SAVED.json`

```json
{
  "id": 10,
  "userId": 1,
  "fingerprint": "abc123fingerprint",
  "permissionStatus": "GRANTED",
  "permissionType": "BIOMETRIC"
}
```

### `src/test/resources/business/device/DevicePermissionData-EXISTING.json`

```json
{
  "id": 7,
  "userId": 1,
  "fingerprint": "abc123fingerprint",
  "permissionStatus": "DENIED",
  "permissionType": "PIN"
}
```

### `src/test/resources/business/device/DevicePermissionData-UPDATED.json`

```json
{
  "id": 7,
  "userId": 1,
  "fingerprint": "abc123fingerprint",
  "permissionStatus": "GRANTED",
  "permissionType": "BIOMETRIC"
}
```

---

## Test Generation Summary

```
TEST GENERATION SUMMARY
───────────────────────
Files created:   [DevicePermissionServiceImplTest.java]
Files modified:  []
Methods added:   [Given_UserExistsAndNoExistingPermission_When_RegisterDevicePermission_Then_SavesNewPermission,
                  Given_UserExistsAndPermissionAlreadyExists_When_RegisterDevicePermission_Then_UpdatesExistingPermission,
                  Given_UserDoesNotExist_When_RegisterDevicePermission_Then_ThrowsUserNotFoundException,
                  Given_UserExistsAndPermissionAlreadyExists_When_RegisterDevicePermission_Then_MutatesExistingBeforeSaving]
Fixtures generated: [DevicePermissionData-INCOMING.json, DevicePermissionData-SAVED.json,
                     DevicePermissionData-EXISTING.json, DevicePermissionData-UPDATED.json]
Coverage: registerDevicePermission() — 4 branches covered:
  - Happy path: user exists, no prior permission → save new record
  - Branch: user exists, permission already exists → update and save existing
  - Negative: user does not exist → throws BusinessException(USER_NOT_FOUND)
  - Branch detail: verifies existing object is mutated before save is called
```
