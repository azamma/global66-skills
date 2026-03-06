# Retrofit API Client — Generation Guide

When creating a new external API client, you can use the **automated generator script** or generate files manually. The script generates the boilerplate; you customize the Request/Response DTOs and endpoint details.

---

## Automated Generation (Recommended)

### Prerequisites

Ensure the project has the required structure:
```
src/main/java/com/global/{domain}/
├── client/
├── config/RestClientConfig.java
├── config/endpoints/EndpointsConfig.java
└── domain/external_request/
```

### Step 1: Gather Information from User

Before running the generator, collect these 4 required inputs:

| Input | Description | Example |
|-------|-------------|---------|
| `ApiName` | PascalCase service name | `MapBox`, `HereGeocoder`, `PaymentGateway` |
| `endpointPath` | Relative API path | `api/v1/geocode`, `v2/payments` |
| `baseUrl` | Base URL for local env | `https://api.mapbox.com/`, `https://payments.example.com` |
| `serviceIdentifier` | kebab-case YAML key | `mapbox-api`, `payment-gateway` |

**Optional but recommended:**
- Does the API require credentials? (apiKey, token, etc.)
- CURL example (for inferring HTTP method, headers, request/response structure)
- Sample request/response JSON

### Step 2: Run the Generator

```bash
# From the Java project root
python /mnt/c/repos/retrofit-client-generator/generate.py
```

The script will:
1. Detect the base package by finding the `client/` directory
2. Generate all 9 boilerplate files (see below)
3. Add configuration to `RestClientConfig.java`, `EndpointsConfig.java`, and `application-local.yml`

### Step 3: Customize Generated Files

The script creates placeholder files. You must customize:

#### 3.1 DTOs (`client/dto/`)

Fill in the actual fields based on the API spec or CURL:

```java
// MapBoxRequestDto.java
public record MapBoxRequestDto(
    @JsonProperty("query") String query,
    @JsonProperty("limit") Integer limit,
    @JsonProperty("country") String country
) {}

// MapBoxResponseDto.java
public record MapBoxResponseDto(
    @JsonProperty("features") List<FeatureDto> features,
    @JsonProperty("attribution") String attribution
) {
    public record FeatureDto(
        @JsonProperty("id") String id,
        @JsonProperty("place_name") String placeName,
        @JsonProperty("center") List<Double> center
    ) {}
}
```

#### 3.2 Domain Objects (`domain/external_request/`)

Create the internal domain representation:

```java
// MapBoxRequest.java
public record MapBoxRequest(String query, Integer limit, String countryCode) {}

// MapBoxResponse.java
public record MapBoxResponse(
    List<GeolocationFeature> features,
    String attribution
) {}
```

#### 3.3 Update Retrofit API Interface

Adjust HTTP method, path, headers, and parameters based on the actual API:

```java
// Before (generated):
public interface MapBoxApi {
    @Headers("Accept: application/json")
    @POST("api/v1/geocode")
    Call<MapBoxResponseDto> createMapBox(...);
}

// After (customized):
public interface MapBoxApi {
    @GET("geocoding/v5/mapbox.places/{query}.json")
    Call<MapBoxResponseDto> geocode(
        @Path("query") String query,
        @Query("access_token") String token,
        @Query("limit") Integer limit,
        @Query("country") String country
    );
}
```

**Common adjustments:**
- Change `@POST` to `@GET`, `@PUT`, `@PATCH`, or `@DELETE`
- Add `@Path` variables for URL segments
- Add `@Query` parameters
- Add `@Header` for dynamic headers
- Add static headers with `@Headers("X-API-Key: ...")`

#### 3.4 Update Client Implementation

Adjust the client method to match the API interface:

```java
@Component @RequiredArgsConstructor
public class MapBoxClientImpl implements MapBoxClient {
    private final MapBoxApi mapBoxApi;

    @Override
    public MapBoxResponse geocode(MapBoxRequest request, String token) {
        MapBoxRequestDto dto = MapBoxRequestClientMapper.INSTANCE.toDto(request);

        Call<MapBoxResponseDto> call = mapBoxApi.geocode(
            dto.query(),
            token,
            dto.limit(),
            dto.country()
        );
        Response<MapBoxResponseDto> response = checkCallExecute(call, HTTP_CLIENT_COMPONENT);

        return MapBoxResponseClientMapper.INSTANCE.toModel(
            checkResponse(response, HTTP_CLIENT_COMPONENT)
        );
    }
}
```

#### 3.5 Update Mappers

Add field mappings if needed:

```java
@Mapper(componentModel = "default", ...)
public interface MapBoxRequestClientMapper {
    MapBoxRequestClientMapper INSTANCE = Mappers.getMapper(MapBoxRequestClientMapper.class);

    @Mapping(source = "countryCode", target = "country")  // different field names
    MapBoxRequestDto toDto(MapBoxRequest request);
}
```

### Step 4: Validation Checklist

- [ ] DTOs match the actual API request/response structure
- [ ] HTTP method (`@GET`/`@POST`/`@PUT`/`@PATCH`/`@DELETE`) is correct
- [ ] Path variables (`@Path`) match URL segments
- [ ] Query parameters (`@Query`) match API spec
- [ ] Headers (`@Header`, `@Headers`) are correct
- [ ] Mappers convert all fields correctly
- [ ] Client implementation method signature matches the API
- [ ] `application-local.yml` has correct `base-url`
- [ ] Add credentials to `credentials` section in YAML if needed

---

## Manual Generation (Alternative)

If you cannot use the script, generate these 9 files manually:

### Files to Generate

#### 1. DTOs (`client/dto/`)

```java
// [ApiName]RequestDto.java
package [basePackage].client.dto;

public record [ApiName]RequestDto(/* fields */) {}

// [ApiName]ResponseDto.java
package [basePackage].client.dto;

public record [ApiName]ResponseDto(/* fields */) {}
```

#### 2. Domain objects (`domain/external_request/`)

```java
// [ApiName]Request.java
package [basePackage].domain.external_request;

public record [ApiName]Request(/* fields */) {}

// [ApiName]Response.java
package [basePackage].domain.external_request;

public record [ApiName]Response(/* fields */) {}
```

#### 3. Mappers (`client/mapper/`)

```java
// [ApiName]RequestClientMapper.java
@Mapper(
    componentModel = "default",
    nullValueCheckStrategy = NullValueCheckStrategy.ALWAYS,
    nullValuePropertyMappingStrategy = NullValuePropertyMappingStrategy.IGNORE)
public interface [ApiName]RequestClientMapper {
    [ApiName]RequestClientMapper INSTANCE = Mappers.getMapper([ApiName]RequestClientMapper.class);
    [ApiName]RequestDto toDto([ApiName]Request request);
}

// [ApiName]ResponseClientMapper.java
@Mapper(
    componentModel = "default",
    nullValueCheckStrategy = NullValueCheckStrategy.ALWAYS,
    nullValuePropertyMappingStrategy = NullValuePropertyMappingStrategy.IGNORE)
public interface [ApiName]ResponseClientMapper {
    [ApiName]ResponseClientMapper INSTANCE = Mappers.getMapper([ApiName]ResponseClientMapper.class);
    [ApiName]Response toModel([ApiName]ResponseDto dto);
}
```

#### 4. Client interface (`client/rest/`)

```java
public interface [ApiName]Client {
    [ApiName]Response methodName([ApiName]Request request, String token);
}
```

#### 5. Retrofit API interface (`client/rest/api/`)

```java
public interface [ApiName]Api {
    @Headers("Accept: application/json")
    @POST("endpoint/path")
    Call<[ApiName]ResponseDto> methodName(
        @Header("Authorization") String token,
        @Body [ApiName]RequestDto dto);
}
```

#### 6. Client implementation (`client/rest/impl/`)

```java
@Component @RequiredArgsConstructor
public class [ApiName]ClientImpl implements [ApiName]Client {
    private final [ApiName]Api apiNameApi;

    @Override
    public [ApiName]Response methodName([ApiName]Request request, String token) {
        [ApiName]RequestDto dto = [ApiName]RequestClientMapper.INSTANCE.toDto(request);
        Call<[ApiName]ResponseDto> call = apiNameApi.methodName(token, dto);
        Response<[ApiName]ResponseDto> response = checkCallExecute(call, HTTP_CLIENT_COMPONENT);
        return [ApiName]ResponseClientMapper.INSTANCE.toModel(checkResponse(response, HTTP_CLIENT_COMPONENT));
    }
}
```

### Configuration Updates

#### 7. `RestClientConfig.java` — add bean

```java
@Bean
public [ApiName]Api [apiName]Api() {
    return getRetrofitConfig(endpointsConfig.[apiName]Endpoint())
        .addConverterFactory(JacksonConverterFactory.create(getObjectMapper(new ObjectMapper())))
        .build()
        .create([ApiName]Api.class);
}
```

#### 8. `EndpointsConfig.java` — add endpoint bean

```java
@Bean
@ConfigurationProperties(prefix = "http-client.[serviceIdentifier]")
public Endpoint [apiName]Endpoint() {
    return new Endpoint();
}
```

#### 9. `application-local.yml` — add config

```yaml
http-client:
  [serviceIdentifier]:
    baseUrl: https://api.example.com/
    loggingLevel: BODY
    readTimeout: 30
    connectTimeout: 30
```

---

## Key Patterns

### Architecture Rules

| Rule | Requirement |
|------|-------------|
| `CLIENT_COMPONENT` | Use `@Component` (not `@Service`) — this is infrastructure |
| `CLIENT_EXTERNAL_DOMAIN` | External API domain objects live in `domain/external_request/` |
| `CLIENT_TWO_MAPPERS` | Two mappers: `*RequestClientMapper` and `*ResponseClientMapper` |
| `CLIENT_RETROFIT_UTILS` | Use `checkCallExecute` + `checkResponse` — no try/catch needed |
| `CLIENT_CONFIG` | Register bean in `RestClientConfig` + `EndpointsConfig` + YAML |

### Retrofit Annotations Reference

| Annotation | Purpose | Example |
|------------|---------|---------|
| `@GET` | HTTP GET request | `@GET("users/{id}")` |
| `@POST` | HTTP POST request | `@POST("api/v1/payments")` |
| `@PUT` | HTTP PUT request | `@PUT("users/{id}")` |
| `@PATCH` | HTTP PATCH request | `@PATCH("users/{id}")` |
| `@DELETE` | HTTP DELETE request | `@DELETE("users/{id}")` |
| `@Path` | URL path variable | `@Path("id") String userId` |
| `@Query` | Query parameter | `@Query("page") Integer page` |
| `@Header` | Dynamic header | `@Header("Authorization") String token` |
| `@Headers` | Static headers | `@Headers("Accept: application/json")` |
| `@Body` | Request body | `@Body PaymentRequestDto request` |

### Complete File Checklist

- [ ] `client/dto/[ApiName]RequestDto.java` — record with JSON field names
- [ ] `client/dto/[ApiName]ResponseDto.java` — record with JSON field names
- [ ] `domain/external_request/[ApiName]Request.java` — internal domain record
- [ ] `domain/external_request/[ApiName]Response.java` — internal domain record
- [ ] `client/mapper/[ApiName]RequestClientMapper.java` — INSTANCE + @Mapper
- [ ] `client/mapper/[ApiName]ResponseClientMapper.java` — INSTANCE + @Mapper
- [ ] `client/rest/[ApiName]Client.java` — interface (port)
- [ ] `client/rest/api/[ApiName]Api.java` — Retrofit interface with correct HTTP method
- [ ] `client/rest/impl/[ApiName]ClientImpl.java` — @Component, implements interface
- [ ] `config/RestClientConfig.java` — bean method added
- [ ] `config/endpoints/EndpointsConfig.java` — endpoint bean added
- [ ] `application-local.yml` — config block under `http-client:`
