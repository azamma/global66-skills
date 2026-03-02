# Endpoint Generation: GET /users/{userId}/last-location

## Task
Generate all layers for the endpoint `GET /users/{userId}/last-location` in `ms-geolocation`,
fetching the last location of a user from the `location` table and returning lat, lon, city,
and country code.

## Package Root
`com.global.geolocation`

---

## File List

| Layer | File |
|-------|------|
| Presentation — Interface | `presentation/LocationController.java` |
| Presentation — Impl | `presentation/impl/LocationControllerImpl.java` |
| Presentation — Response DTO | `presentation/dto/LastLocationResponse.java` |
| Presentation — Mapper | `presentation/mapper/LocationPresentationMapper.java` |
| Business — Interface | `business/FindLastLocationService.java` |
| Business — Impl | `business/impl/FindLastLocationServiceImpl.java` |
| Persistence — Interface | `persistence/LocationPersistence.java` |
| Persistence — Impl | `persistence/impl/LocationPersistenceImpl.java` |
| Persistence — Repository | `persistence/repository/LocationRepository.java` |
| Persistence — Entity | `persistence/entity/LocationEntity.java` |
| Persistence — Mapper | `persistence/mapper/LocationMapper.java` |
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
    private Double lat;
    private Double lon;
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
@Comment("Stores geolocation records per user")
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

    @Column(name = "lat", nullable = false)
    @Comment("Latitude coordinate of the location")
    private Double lat;

    @Column(name = "lon", nullable = false)
    @Comment("Longitude coordinate of the location")
    private Double lon;

    @Column(name = "city", nullable = false, length = 100)
    @Comment("City name of the location")
    private String city;

    @Column(name = "country_code", nullable = false, length = 10)
    @Comment("ISO country code of the location")
    private String countryCode;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    @Comment("Timestamp when the location record was created")
    private java.time.LocalDateTime createdAt;
}
```

### `persistence/repository/LocationRepository.java`

```java
package com.global.geolocation.persistence.repository;

import com.global.geolocation.persistence.entity.LocationEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface LocationRepository extends JpaRepository<LocationEntity, Integer> {

    Optional<LocationEntity> findTopByUserIdOrderByCreatedAtDesc(Integer userId);
}
```

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

### `persistence/LocationPersistence.java`

```java
package com.global.geolocation.persistence;

import com.global.geolocation.domain.data.LocationData;

import java.util.Optional;

public interface LocationPersistence {

    Optional<LocationData> findLastByUserId(Integer userId);
}
```

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
        return locationRepository.findTopByUserIdOrderByCreatedAtDesc(userId)
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

    @Schema(description = "Latitude coordinate of the last known location", example = "-33.456789")
    Double lat,

    @Schema(description = "Longitude coordinate of the last known location", example = "-70.648972")
    Double lon,

    @Schema(description = "City name of the last known location", example = "Santiago")
    String city,

    @Schema(description = "ISO 3166-1 alpha-2 country code", example = "CL")
    String countryCode) {}
```

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

    LastLocationResponse toResponse(LocationData data);
}
```

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

@Tag(name = "Location", description = "API for retrieving user geolocation data")
public interface LocationController {

    @ErrorResponses(
        values = {
            @ErrorResponse(reason = ErrorReason.NOT_FOUND,
                           source = ErrorSource.BUSINESS_SERVICE)
        })
    @Operation(
        summary = "Get last known location of a user",
        description = "Returns the most recent latitude, longitude, city, and country code recorded for the given user",
        tags = {"location", "geolocation", "user"},
        responses = {
            @ApiResponse(responseCode = "200", description = "Last location returned successfully"),
            @ApiResponse(responseCode = "404", description = "No location record found for the given user")
        })
    @SecurityRequirement(name = "authB2C")
    LastLocationResponse getLastLocation(
        @Parameter(description = "Unique identifier of the user", required = true, example = "12345")
            @PathVariable Integer userId);
}
```

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

## Architecture Summary

```
LocationControllerImpl
    └── FindLastLocationService
            └── LocationPersistence
                    └── LocationRepository (JPA)
                            └── location table

Data flow (outbound):
LocationEntity → LocationData → LastLocationResponse

Mappers:
  LocationMapper.INSTANCE.toData()              (persistence ↔ domain)
  LocationPresentationMapper.INSTANCE.toResponse()  (domain → response DTO)
```

## Checklist Verification

- [x] No `@Entity` outside `persistence/` package
- [x] No repository injected directly into service (uses `LocationPersistence` port)
- [x] `@Transactional(readOnly = true)` on `findLastLocation` (read-only query — `find*` prefix rule)
- [x] `@Transactional` only in business layer — not in persistence, controller, or client
- [x] All public methods ≤ 10 lines, orchestration only
- [x] No `process/handle/execute/validate/check` method names
- [x] Exception factory method `locationNotFoundException(userId)` — no inline `throw new`
- [x] `fetchLastLocationOrThrow` follows `fetch*` semantic prefix (get or throw NOT_FOUND)
- [x] MapStruct mapper per layer with `INSTANCE` singleton and full `@Mapper(componentModel="default", ...)` config
- [x] Controller is thin: validate input → delegate to service → map response
- [x] `START` and `END` logs in controller with `userId`
- [x] No PII in logs (only non-sensitive `userId`)
- [x] All Swagger annotations on interface only — zero on `LocationControllerImpl`
- [x] `@Tag(name, description)` on controller interface
- [x] `@Operation(summary, description)` on the method
- [x] `@ErrorResponses` with `NOT_FOUND` from `BUSINESS_SERVICE`
- [x] `@SecurityRequirement(name = "authB2C")` on the protected endpoint
- [x] Response record has `@Schema` on each component with `description` + `example`
- [x] `LocationEntity` stays in `persistence/entity/` — never leaks to business or presentation
- [x] `LocationData` is a plain `@Data` class — used as the domain transfer object between layers
- [x] `findLastByUserId` on persistence interface follows `find*` naming (returns `Optional`, never throws)
