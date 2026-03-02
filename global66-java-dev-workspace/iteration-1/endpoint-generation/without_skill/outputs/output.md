# Endpoint Generation — GET /users/{userId}/last-location

**Task:** Create a GET endpoint `/users/{userId}/last-location` in `ms-geolocation` that returns the last known location of a user (lat, lon, city, country code) from the `location` table.

---

## File Index

| Layer | File |
|---|---|
| Presentation — Interface | `LocationController.java` |
| Presentation — Implementation | `impl/LocationControllerImpl.java` |
| Presentation — Response DTO | `dto/LastLocationResponse.java` |
| Presentation — Mapper | `mapper/LocationPresentationMapper.java` |
| Business — Interface | `FindLastLocationService.java` |
| Business — Implementation | `impl/FindLastLocationServiceImpl.java` |
| Persistence — Interface | `LocationPersistence.java` |
| Persistence — Implementation | `impl/LocationPersistenceImpl.java` |
| Persistence — Repository | `repository/LocationRepository.java` |
| Persistence — Entity | `entity/LocationEntity.java` |
| Persistence — Mapper | `mapper/LocationMapper.java` |
| Domain — Data | `domain/data/LocationData.java` |

---

## 1. Domain Layer

### `domain/data/LocationData.java`

```java
package com.global.geolocation.domain.data;

import lombok.Data;

@Data
public class LocationData {
    private Integer id;
    private Integer userId;
    private Double latitude;
    private Double longitude;
    private String city;
    private String countryCode;
}
```

---

## 2. Persistence Layer

### `persistence/entity/LocationEntity.java`

```java
package com.global.geolocation.persistence.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import lombok.Getter;
import lombok.Setter;
import org.hibernate.annotations.Comment;

@Entity
@Table(name = "location")
@Comment("Stores the last known geolocation recorded per user")
@Getter
@Setter
public class LocationEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "id")
    private Integer id;

    @Column(name = "user_id", nullable = false)
    @Comment("Identifier of the user who owns this location record")
    private Integer userId;

    @Column(name = "latitude", nullable = false)
    @Comment("Latitude coordinate of the recorded location")
    private Double latitude;

    @Column(name = "longitude", nullable = false)
    @Comment("Longitude coordinate of the recorded location")
    private Double longitude;

    @Column(name = "city", nullable = false, length = 100)
    @Comment("City name derived from the coordinates")
    private String city;

    @Column(name = "country_code", nullable = false, length = 10)
    @Comment("ISO country code derived from the coordinates")
    private String countryCode;
}
```

---

### `persistence/repository/LocationRepository.java`

```java
package com.global.geolocation.persistence.repository;

import com.global.geolocation.persistence.entity.LocationEntity;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface LocationRepository extends JpaRepository<LocationEntity, Integer> {

    Optional<LocationEntity> findTopByUserIdOrderByIdDesc(Integer userId);
}
```

---

### `persistence/mapper/LocationMapper.java`

```java
package com.global.geolocation.persistence.mapper;

import com.global.geolocation.domain.data.LocationData;
import com.global.geolocation.persistence.entity.LocationEntity;
import org.mapstruct.Mapper;
import org.mapstruct.NullValueCheckStrategy;
import org.mapstruct.NullValuePropertyMappingStrategy;
import org.mapstruct.factory.Mappers;

@Mapper(
    componentModel = "default",
    nullValueCheckStrategy = NullValueCheckStrategy.ALWAYS,
    nullValuePropertyMappingStrategy = NullValuePropertyMappingStrategy.IGNORE)
public interface LocationMapper {

    LocationMapper INSTANCE = Mappers.getMapper(LocationMapper.class);

    LocationData toData(LocationEntity entity);

    LocationEntity toEntity(LocationData data);
}
```

---

### `persistence/LocationPersistence.java`

```java
package com.global.geolocation.persistence;

import com.global.geolocation.domain.data.LocationData;

import java.util.Optional;

public interface LocationPersistence {

    Optional<LocationData> findLastByUserId(Integer userId);
}
```

---

### `persistence/impl/LocationPersistenceImpl.java`

```java
package com.global.geolocation.persistence.impl;

import com.global.geolocation.domain.data.LocationData;
import com.global.geolocation.persistence.LocationPersistence;
import com.global.geolocation.persistence.mapper.LocationMapper;
import com.global.geolocation.persistence.repository.LocationRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Component;

import java.util.Optional;

@Component
@RequiredArgsConstructor
public class LocationPersistenceImpl implements LocationPersistence {

    private final LocationRepository locationRepository;

    @Override
    public Optional<LocationData> findLastByUserId(Integer userId) {
        return locationRepository.findTopByUserIdOrderByIdDesc(userId)
            .map(LocationMapper.INSTANCE::toData);
    }
}
```

---

## 3. Business Layer

### `business/FindLastLocationService.java`

```java
package com.global.geolocation.business;

import com.global.geolocation.domain.data.LocationData;

public interface FindLastLocationService {

    LocationData findLastLocation(Integer userId);
}
```

---

### `business/impl/FindLastLocationServiceImpl.java`

```java
package com.global.geolocation.business.impl;

import com.global.geolocation.business.FindLastLocationService;
import com.global.geolocation.domain.data.LocationData;
import com.global.geolocation.persistence.LocationPersistence;
import com.global.rest.exception.BusinessException;
import com.global.rest.exception.enums.ErrorCode;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Slf4j
@Service
@RequiredArgsConstructor
public class FindLastLocationServiceImpl implements FindLastLocationService {

    private final LocationPersistence locationPersistence;

    @Override
    @Transactional(readOnly = true)
    public LocationData findLastLocation(Integer userId) {
        return fetchLastLocationOrThrow(userId);
    }

    private LocationData fetchLastLocationOrThrow(Integer userId) {
        return locationPersistence.findLastByUserId(userId)
            .orElseThrow(() -> locationNotFoundException(userId));
    }

    private BusinessException locationNotFoundException(Integer userId) {
        return new BusinessException(ErrorCode.NOT_FOUND, userId.toString());
    }
}
```

---

## 4. Presentation Layer

### `presentation/dto/LastLocationResponse.java`

```java
package com.global.geolocation.presentation.dto;

import io.swagger.v3.oas.annotations.media.Schema;

public record LastLocationResponse(
    @Schema(description = "Latitude coordinate of the user's last location", example = "-33.456789")
        Double latitude,
    @Schema(description = "Longitude coordinate of the user's last location", example = "-70.648532")
        Double longitude,
    @Schema(description = "City name of the user's last location", example = "Santiago")
        String city,
    @Schema(description = "ISO country code of the user's last location", example = "CL")
        String countryCode) {}
```

---

### `presentation/mapper/LocationPresentationMapper.java`

```java
package com.global.geolocation.presentation.mapper;

import com.global.geolocation.domain.data.LocationData;
import com.global.geolocation.presentation.dto.LastLocationResponse;
import org.mapstruct.Mapper;
import org.mapstruct.NullValueCheckStrategy;
import org.mapstruct.NullValuePropertyMappingStrategy;
import org.mapstruct.factory.Mappers;

@Mapper(
    componentModel = "default",
    nullValueCheckStrategy = NullValueCheckStrategy.ALWAYS,
    nullValuePropertyMappingStrategy = NullValuePropertyMappingStrategy.IGNORE)
public interface LocationPresentationMapper {

    LocationPresentationMapper INSTANCE = Mappers.getMapper(LocationPresentationMapper.class);

    LastLocationResponse toResponse(LocationData locationData);
}
```

---

### `presentation/LocationController.java`

```java
package com.global.geolocation.presentation;

import com.global.geolocation.presentation.dto.LastLocationResponse;
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

@Tag(name = "Location", description = "API for managing user geolocation data")
public interface LocationController {

    @ErrorResponses(
        values = {
            @ErrorResponse(reason = ErrorReason.NOT_FOUND,
                           source = ErrorSource.BUSINESS_SERVICE)
        })
    @Operation(
        summary = "Get last known location of a user",
        description = "Returns the most recent latitude, longitude, city and country code recorded for a given user",
        tags = {"location", "geolocation", "user"},
        responses = {
            @ApiResponse(responseCode = "200", description = "Last location returned successfully"),
            @ApiResponse(responseCode = "404", description = "No location found for the given userId")
        })
    @SecurityRequirement(name = "authB2C")
    LastLocationResponse getLastLocation(
        @Parameter(description = "Unique identifier of the user", required = true, example = "12345")
            @PathVariable Integer userId);
}
```

---

### `presentation/impl/LocationControllerImpl.java`

```java
package com.global.geolocation.presentation.impl;

import com.global.geolocation.business.FindLastLocationService;
import com.global.geolocation.presentation.LocationController;
import com.global.geolocation.presentation.dto.LastLocationResponse;
import com.global.geolocation.presentation.mapper.LocationPresentationMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@Slf4j
@RestController
@RequiredArgsConstructor
@RequestMapping("/ms-geolocation/iuse/users")
public class LocationControllerImpl implements LocationController {

    private final FindLastLocationService findLastLocationService;

    @Override
    @GetMapping("/{userId}/last-location")
    public LastLocationResponse getLastLocation(@PathVariable Integer userId) {
        log.info("START - [GET] [/ms-geolocation/iuse/users/{}/last-location]: userId={}", userId, userId);
        LastLocationResponse response = LocationPresentationMapper.INSTANCE.toResponse(
            findLastLocationService.findLastLocation(userId));
        log.info("END - [GET] [/ms-geolocation/iuse/users/{}/last-location]", userId);
        return response;
    }
}
```

---

## Architecture Decision Notes

1. **`FindLastLocationService`** — named after the action (`Find`) to respect SRP naming. A single interface per use case avoids fat service classes.
2. **`@Transactional(readOnly = true)`** — this is a pure query with no writes. `readOnly = true` enables DB-level optimizations and satisfies `TX_READ_ONLY` rule.
3. **`fetchLastLocationOrThrow`** — private method following the `fetch*` semantic prefix: gets or throws NOT_FOUND. Exception is always constructed via a factory method (`locationNotFoundException`), never inline.
4. **`LocationPersistence.findLastByUserId`** — returns `Optional`. The service layer is responsible for deciding whether absence is an error; the persistence port never throws NOT_FOUND.
5. **`findTopByUserIdOrderByIdDesc`** — selects the most recently inserted row for the user. No `@Query` annotation needed; Spring Data derives the query from the method name.
6. **`@Transactional` only in business layer** — `LocationPersistenceImpl` has no `@Transactional`. The transaction is opened by the service and the JPA call participates in it via default `REQUIRED` propagation.
7. **Swagger annotations on interface only** — `LocationControllerImpl` has zero `@Operation`, `@Tag`, or `@Schema` annotations.
8. **`INSTANCE` singleton** in both mappers — follows the mandatory MapStruct `componentModel = "default"` + `INSTANCE` convention.
9. **Max 3 injected dependencies** — every class has exactly 1 injected dependency, well within the limit.
10. **No `process`/`handle`/`execute`/`validate`/`check` names** — all method names use semantic prefixes (`findLastLocation`, `fetchLastLocationOrThrow`, `locationNotFoundException`).
