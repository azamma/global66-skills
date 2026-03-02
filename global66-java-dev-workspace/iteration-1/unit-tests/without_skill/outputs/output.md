# Unit Tests — DevicePermissionServiceImpl

## Test Class

```java
package com.global.geolocation.business.impl;

import com.global.geolocation.domain.data.DevicePermissionData;
import com.global.geolocation.enums.PermissionStatusEnum;
import com.global.geolocation.enums.PermissionTypeEnum;
import com.global.geolocation.persistence.DevicePermissionPersistence;
import com.global.geolocation.persistence.UserPersistence;
import com.global.rest.exception.BusinessException;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

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
                java.util.Objects.requireNonNull(
                    getClass().getClassLoader().getResourceAsStream(path)
                ).readAllBytes()
            );
            return com.global.utils.ObjectMapperUtils.loadObject(json, type);
        } catch (java.io.IOException e) {
            throw new RuntimeException("Failed to load test fixture: " + path, e);
        }
    }

    @Nested
    @DisplayName("registerDevicePermission")
    class RegisterDevicePermissionTests {

        @Test
        void Given_ExistingUserAndNoExistingFingerprint_When_RegisterDevicePermission_Then_SavesNewPermission() {
            Integer userId = 1;
            DevicePermissionData incoming = loadJson(
                "business/device_permission/DevicePermissionData-VALID.json",
                DevicePermissionData.class);
            DevicePermissionData saved = loadJson(
                "business/device_permission/DevicePermissionData-SAVED.json",
                DevicePermissionData.class);

            when(mockUserPersistence.existsById(userId)).thenReturn(true);
            when(mockDevicePermissionPersistence.findByUserIdAndFingerprint(userId, incoming.getFingerprint()))
                .thenReturn(Optional.empty());
            when(mockDevicePermissionPersistence.save(incoming)).thenReturn(saved);

            DevicePermissionData result = subject.registerDevicePermission(userId, incoming);

            assertThat(result).isEqualTo(saved);
            verify(mockDevicePermissionPersistence).save(incoming);
        }

        @Test
        void Given_ExistingUserAndExistingFingerprint_When_RegisterDevicePermission_Then_UpdatesExistingPermission() {
            Integer userId = 1;
            DevicePermissionData incoming = loadJson(
                "business/device_permission/DevicePermissionData-VALID.json",
                DevicePermissionData.class);
            DevicePermissionData existing = loadJson(
                "business/device_permission/DevicePermissionData-SAVED.json",
                DevicePermissionData.class);
            DevicePermissionData updated = loadJson(
                "business/device_permission/DevicePermissionData-UPDATED.json",
                DevicePermissionData.class);

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
        void Given_NonExistentUserId_When_RegisterDevicePermission_Then_ThrowsBusinessException() {
            Integer userId = 999;
            DevicePermissionData incoming = loadJson(
                "business/device_permission/DevicePermissionData-VALID.json",
                DevicePermissionData.class);

            when(mockUserPersistence.existsById(userId)).thenReturn(false);

            assertThatThrownBy(() -> subject.registerDevicePermission(userId, incoming))
                .isInstanceOf(BusinessException.class);

            verifyNoInteractions(mockDevicePermissionPersistence);
        }

        @Test
        void Given_ExistingUserAndExistingFingerprint_When_RegisterDevicePermission_Then_MutatesExistingWithIncomingStatusAndType() {
            Integer userId = 1;
            DevicePermissionData incoming = loadJson(
                "business/device_permission/DevicePermissionData-VALID.json",
                DevicePermissionData.class);
            DevicePermissionData existing = loadJson(
                "business/device_permission/DevicePermissionData-SAVED.json",
                DevicePermissionData.class);

            when(mockUserPersistence.existsById(userId)).thenReturn(true);
            when(mockDevicePermissionPersistence.findByUserIdAndFingerprint(userId, incoming.getFingerprint()))
                .thenReturn(Optional.of(existing));
            when(mockDevicePermissionPersistence.save(existing)).thenReturn(existing);

            subject.registerDevicePermission(userId, incoming);

            assertThat(existing.getPermissionStatus()).isEqualTo(incoming.getPermissionStatus());
            assertThat(existing.getPermissionType()).isEqualTo(incoming.getPermissionType());
        }
    }
}
```

---

## JSON Fixtures

### `src/test/resources/business/device_permission/DevicePermissionData-VALID.json`

```json
{
  "fingerprint": "abc123fingerprint",
  "permissionStatus": "ACTIVE",
  "permissionType": "BIOMETRIC"
}
```

### `src/test/resources/business/device_permission/DevicePermissionData-SAVED.json`

```json
{
  "id": 10,
  "fingerprint": "abc123fingerprint",
  "permissionStatus": "INACTIVE",
  "permissionType": "PIN"
}
```

### `src/test/resources/business/device_permission/DevicePermissionData-UPDATED.json`

```json
{
  "id": 10,
  "fingerprint": "abc123fingerprint",
  "permissionStatus": "ACTIVE",
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
Methods added:   [
    Given_ExistingUserAndNoExistingFingerprint_When_RegisterDevicePermission_Then_SavesNewPermission,
    Given_ExistingUserAndExistingFingerprint_When_RegisterDevicePermission_Then_UpdatesExistingPermission,
    Given_NonExistentUserId_When_RegisterDevicePermission_Then_ThrowsBusinessException,
    Given_ExistingUserAndExistingFingerprint_When_RegisterDevicePermission_Then_MutatesExistingWithIncomingStatusAndType
]
Fixtures generated: [
    DevicePermissionData-VALID.json,
    DevicePermissionData-SAVED.json,
    DevicePermissionData-UPDATED.json
]
Coverage: registerDevicePermission() — 4 branches covered:
  - Happy path: user exists, fingerprint not found → save new record
  - Branch condition: user exists, fingerprint found → update existing record
  - Negative/exception: user not found → throws BusinessException, no persistence call
  - Branch condition (mutation): verifies that existing record fields are mutated with incoming values before save
```
