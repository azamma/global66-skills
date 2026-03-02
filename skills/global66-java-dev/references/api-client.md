# Retrofit API Client — Generation Guide

When creating a new external API client, generate all the following files in order.
Ask the user for these 4 inputs (infer everything else):

| Input | Example |
|-------|---------|
| `ApiName` (PascalCase) | `MapBox`, `HereGeocoder` |
| `endpointPath` (relative URL) | `api/v1/geocode` |
| `baseUrl` (local env) | `https://api.mapbox.com/` |
| `serviceIdentifier` (kebab-case) | `mapbox-api` |

From those inputs, derive:
- `apiName` = camelCase of `ApiName` (e.g. `mapBox`)
- `basePackage` = find the package containing a `client/` directory in the project
- `configPrefix` = `http-client.[serviceIdentifier]`

---

## Files to Generate

### 1. DTOs (`client/dto/`)

```java
// [ApiName]RequestDto.java
package [basePackage].client.dto;

public record [ApiName]RequestDto(/* TODO: Add fields */) {}

// [ApiName]ResponseDto.java
package [basePackage].client.dto;

public record [ApiName]ResponseDto(/* TODO: Add fields */) {}
```

### 2. Domain objects (`domain/external_request/`)

External API domain objects live in `external_request/`, not in `data/`.
They are the domain representation of external API calls — decoupled from the DTO wire format.

```java
// [ApiName]Request.java
package [basePackage].domain.external_request;

public record [ApiName]Request(/* TODO: Add fields */) {}

// [ApiName]Response.java
package [basePackage].domain.external_request;

public record [ApiName]Response(/* TODO: Add fields */) {}
```

### 3. Mappers (`client/mapper/`)

Two separate mappers: one for request, one for response.
Use the full `@Mapper` config consistent with all other mappers in the project.

```java
// [ApiName]RequestClientMapper.java
package [basePackage].client.mapper;

import [basePackage].client.dto.[ApiName]RequestDto;
import [basePackage].domain.external_request.[ApiName]Request;
import org.mapstruct.Mapper;
import org.mapstruct.NullValueCheckStrategy;
import org.mapstruct.NullValuePropertyMappingStrategy;
import org.mapstruct.factory.Mappers;

@Mapper(
    componentModel = "default",
    nullValueCheckStrategy = NullValueCheckStrategy.ALWAYS,
    nullValuePropertyMappingStrategy = NullValuePropertyMappingStrategy.IGNORE)
public interface [ApiName]RequestClientMapper {
    [ApiName]RequestClientMapper INSTANCE = Mappers.getMapper([ApiName]RequestClientMapper.class);

    [ApiName]RequestDto toDto([ApiName]Request [apiName]Request);
}

// [ApiName]ResponseClientMapper.java
package [basePackage].client.mapper;

import [basePackage].client.dto.[ApiName]ResponseDto;
import [basePackage].domain.external_request.[ApiName]Response;
import org.mapstruct.Mapper;
import org.mapstruct.NullValueCheckStrategy;
import org.mapstruct.NullValuePropertyMappingStrategy;
import org.mapstruct.factory.Mappers;

@Mapper(
    componentModel = "default",
    nullValueCheckStrategy = NullValueCheckStrategy.ALWAYS,
    nullValuePropertyMappingStrategy = NullValuePropertyMappingStrategy.IGNORE)
public interface [ApiName]ResponseClientMapper {
    [ApiName]ResponseClientMapper INSTANCE = Mappers.getMapper([ApiName]ResponseClientMapper.class);

    [ApiName]Response toModel([ApiName]ResponseDto [apiName]ResponseDto);
}
```

### 4. Client interface (`client/rest/`)

The interface is the port. Business layer only knows this interface, not the impl or the Retrofit Api.

```java
// [ApiName]Client.java
package [basePackage].client.rest;

import [basePackage].domain.external_request.[ApiName]Request;
import [basePackage].domain.external_request.[ApiName]Response;

public interface [ApiName]Client {
    [ApiName]Response create[ApiName](String token, [ApiName]Request [apiName]Request);
}
```

### 5. Retrofit API interface (`client/rest/api/`)

```java
// [ApiName]Api.java
package [basePackage].client.rest.api;

import [basePackage].client.dto.[ApiName]RequestDto;
import [basePackage].client.dto.[ApiName]ResponseDto;
import retrofit2.Call;
import retrofit2.http.Body;
import retrofit2.http.Header;
import retrofit2.http.Headers;
import retrofit2.http.POST;

public interface [ApiName]Api {

    @Headers("Accept: application/json")
    @POST("[endpointPath]")
    Call<[ApiName]ResponseDto> create[ApiName](
        @Header("Authorization") String token,
        @Body [ApiName]RequestDto [apiName]RequestDto);
}
```

Adjust `@GET`/`@POST`/`@PUT` and path annotations to match the actual endpoint.
For query params use `@Query`, for path segments use `@Path`.

### 6. Client implementation (`client/rest/impl/`)

```java
// [ApiName]ClientImpl.java
package [basePackage].client.rest.impl;

import static com.global.rest.exception.enums.ErrorSource.HTTP_CLIENT_COMPONENT;
import static com.global.rest.exception.utils.RetrofitUtils.checkCallExecute;
import static com.global.rest.exception.utils.RetrofitUtils.checkResponse;

import [basePackage].client.dto.[ApiName]RequestDto;
import [basePackage].client.dto.[ApiName]ResponseDto;
import [basePackage].client.mapper.[ApiName]RequestClientMapper;
import [basePackage].client.mapper.[ApiName]ResponseClientMapper;
import [basePackage].client.rest.[ApiName]Client;
import [basePackage].client.rest.api.[ApiName]Api;
import [basePackage].domain.external_request.[ApiName]Request;
import [basePackage].domain.external_request.[ApiName]Response;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Component;
import retrofit2.Call;
import retrofit2.Response;

@Component
@RequiredArgsConstructor
public class [ApiName]ClientImpl implements [ApiName]Client {

    private final [ApiName]Api [apiName]Api;

    @Override
    public [ApiName]Response create[ApiName](String token, [ApiName]Request [apiName]Request) {
        [ApiName]RequestDto [apiName]RequestDto =
            [ApiName]RequestClientMapper.INSTANCE.toDto([apiName]Request);

        Call<[ApiName]ResponseDto> call =
            [apiName]Api.create[ApiName](token, [apiName]RequestDto);
        Response<[ApiName]ResponseDto> response = checkCallExecute(call, HTTP_CLIENT_COMPONENT);
        [ApiName]ResponseDto [apiName]ResponseDto = checkResponse(response, HTTP_CLIENT_COMPONENT);

        return [ApiName]ResponseClientMapper.INSTANCE.toModel([apiName]ResponseDto);
    }
}
```

Note: `@Component` (not `@Service`) because this is infrastructure, not business logic.
`checkCallExecute` handles `IOException`; `checkResponse` handles non-2xx HTTP responses.
Both throw `BusinessException` with `HTTP_CLIENT_COMPONENT` source — no try/catch needed here.

---

## Configuration Files to Update

### 7. `RestClientConfig.java` — add new bean

Add a `@Bean` method for the Retrofit Api interface. The `getRetrofitConfig` and `endpointsConfig`
helpers are already present in the class; just add the new bean:

```java
@Bean
public [ApiName]Api [apiName]Api() {
    return getRetrofitConfig(endpointsConfig.[apiName]Endpoint())
        .addConverterFactory(JacksonConverterFactory.create(getObjectMapper(new ObjectMapper())))
        .build()
        .create([ApiName]Api.class);
}
```

Also add the import: `import [basePackage].client.rest.api.[ApiName]Api;`

### 8. `EndpointsConfig.java` — add new `@ConfigurationProperties` bean

```java
@Bean
@ConfigurationProperties(prefix = "http-client.[serviceIdentifier]")
public Endpoint [apiName]Endpoint() {
    return new Endpoint();
}
```

The `Endpoint` class is a shared POJO (already in the project) that holds `baseUrl`, `loggingLevel`,
`readTimeout`, and `connectTimeout`.

### 9. `application-local.yml` — append under `http-client`

Find the existing `http-client:` key and add the new service block underneath — do NOT create
a duplicate `http-client:` root key:

```yaml
http-client:
  # ... existing entries ...
  [serviceIdentifier]:
    baseUrl: [baseUrl]
    loggingLevel: BODY
    readTimeout: 30
    connectTimeout: 30
```

---

## Complete File Checklist

After generation, verify:

- [ ] `client/dto/[ApiName]RequestDto.java` — record
- [ ] `client/dto/[ApiName]ResponseDto.java` — record
- [ ] `domain/external_request/[ApiName]Request.java` — record
- [ ] `domain/external_request/[ApiName]Response.java` — record
- [ ] `client/mapper/[ApiName]RequestClientMapper.java` — INSTANCE + full @Mapper config
- [ ] `client/mapper/[ApiName]ResponseClientMapper.java` — INSTANCE + full @Mapper config
- [ ] `client/rest/[ApiName]Client.java` — interface (port)
- [ ] `client/rest/api/[ApiName]Api.java` — Retrofit interface
- [ ] `client/rest/impl/[ApiName]ClientImpl.java` — @Component, not @Service
- [ ] `config/RestClientConfig.java` updated — new `[apiName]Api()` bean
- [ ] `config/endpoints/EndpointsConfig.java` updated — new `[apiName]Endpoint()` bean
- [ ] `application-local.yml` updated — block appended under existing `http-client:` key
