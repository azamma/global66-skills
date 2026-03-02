# Global66 Cache Guidelines

Guidelines for implementing caching with Redis and Caffeine in Global66 microservices.

## Quick Decision Tree

1. Does the cache need to be shared across multiple instances/services?
   - Yes → Use Redis
   - No → Use local cache (Caffeine)
2. What type of information will be cached?
3. Does the information change frequently?
4. How often is the data queried? How many queries are needed to obtain it?

**Exception:** If Redis already exists in the microservice, use that connection even if the cache is not shared.

## Package Structure

```
com.global.{domain}/
├── cache/
│   └── {Domain}CacheService.java          # Interface
├── cache/impl/
│   └── {Domain}CacheServiceImpl.java    # Implementation with @Scope
```

## Cache Service Implementation

```java
@Slf4j
@Component
@RequiredArgsConstructor
@Scope(proxyMode = ScopedProxyMode.TARGET_CLASS)
public class DestinyBankCacheServiceImpl implements DestinyBankCacheService {
    private final DestinyBankRepository destinyBankRepository;
    private final DestinyBankCacheService self;  // Self-injection for cache

    @Override
    @Cacheable(value = "destinyBank", key = "'all'")
    public List<DestinyBankCache> getAll() {
        return destinyBankRepository.findAllCache();
    }

    @Override
    public List<DestinyBankCache> getAllByRouteId(List<Integer> routeIds) {
        return self.getAll().stream()
            .filter(bank -> routeIds.contains(bank.getRouteId()))
            .toList();
    }

    @Override
    @CacheEvict(value = "destinyBank", allEntries = true)
    public void evictAll() {
        log.info("Evict all entries for destinyBank cache");
    }

    @Override
    public void evictForKeys(List<String> keys) {
        keys.forEach(self::evictKey);
    }

    @Override
    @CacheEvict(value = "destinyBank", key = "#key")
    public void evictKey(String key) {
        log.info("Evict key {} in destinyBank cache", key);
    }
}
```

**Note:** `@Scope(proxyMode = ScopedProxyMode.TARGET_CLASS)` is required for self-injection to avoid circular dependencies when calling cached methods from within the same class.

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Cache name | Plural, camelCase, English | `countries`, `routePairCostConfig` |
| Key (no params) | `'all'` for lists | `key = "'all'"` |
| Key (with params) | Parameter names separated by commas | `key = "{ #routePairId, #paymentTypeId }"` |
| Key (lite/full) | Use colon separator for complex entities | `key = "'all:lite'"`, `key = "'all:full'"` |

## Annotations

### @Cacheable

```java
// Simple cache - no parameters
@Cacheable(value = "countries")
public List<CountryResponse> getAllEnabled() { ... }

// With explicit key
@Cacheable(value = "countries", key = "'all'")
public List<CountryResponse> getAllEnabled() { ... }

// With multiple parameters
@Cacheable(value = "routePairCostConfig", key = "{ #routePairId, #paymentTypeId }")
public RoutePairCostConfigCache getByRoutePairIdAndPaymentTypeId(
        Integer routePairId, Integer paymentTypeId) { ... }

// With unless condition
@Cacheable(
    cacheManager = "cacheManagerRedis",
    value = "routePairFee",
    key = "{ #routePairId, #feeTypeId, #clientTypeId }",
    unless = "#result == null"
)
public RoutePairFeeCache getByRoutePairIdAndFeeTypeIdAndClientTypeId(...) { ... }
```

### @CachePut

```java
// Update cache after method execution
@CachePut(value = "countries")
@Scheduled(timeUnit = TimeUnit.SECONDS, fixedDelayString = "60")
public List<CountryResponse> putAllCountriesEnabled() {
    log.info("Starting to put cache 'countries-enabled'");
    return getAllEnabledCache();
}
```

**Note:** Methods with `@Scheduled` cannot have parameters.

### @CacheEvict

```java
// Evict all entries
@CacheEvict(value = "countries", allEntries = true)
public void evictAll() {
    log.info("Evict all entries for countries cache");
}

// Evict specific key
@CacheEvict(value = "countries", key = "#key")
public void evictSingleCacheValue(String key) {
    log.info("Evict key {} in routePairCostConfig cache", key);
}
```

## Local Cache (Caffeine)

### Dependencies

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-cache</artifactId>
</dependency>
<dependency>
    <groupId>com.github.ben-manes.caffeine</groupId>
    <artifactId>caffeine</artifactId>
</dependency>
```

### YAML Configuration

```yaml
spring:
  cache:
    type: caffeine
    caffeine:
      spec: expireAfterWrite=1h,recordStats=true
```

### Java Configuration

```java
@Bean
public Caffeine caffeineConfig() {
    return Caffeine.newBuilder()
        .initialCapacity(10)
        .maximumSize(100)  // Max 100 to avoid memory issues
        .expireAfterAccess(Duration.ofMinutes(10))
        .expireAfterWrite(Duration.ofHours(1))
        .refreshAfterWrite(Duration.ofHours(1))
        .recordStats();
}

@Bean
public CacheManager cacheManager(Caffeine caffeine) {
    CaffeineCacheManager caffeineCacheManager = new CaffeineCacheManager();
    caffeineCacheManager.setCaffeine(caffeine);
    return caffeineCacheManager;
}
```

### Caffeine Spec Options

| Option | Description |
|--------|-------------|
| `initialCapacity` | Initial capacity (default: 0) |
| `maximumSize` | Max entries to keep (recommended: ≤100) |
| `expireAfterAccess` | Expire after last access |
| `expireAfterWrite` | Expire after creation/update |
| `refreshAfterWrite` | Async refresh after write |
| `recordStats` | Enable statistics |

## Redis Cache

### Dependencies

```xml
<dependency>
    <groupId>redis.clients</groupId>
    <artifactId>jedis</artifactId>
</dependency>
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-data-redis</artifactId>
</dependency>
```

### YAML Configuration

```yaml
spring:
  redis:
    host: ${REDIS_HOST}
    port: 6379
    database: 2
    jedis:
      pool:
        max-active: 500
        max-idle: 100
        min-idle: 10
        max-wait: 2
```

### RedisConfig (Jedis)

```java
@Configuration
public class RedisConfig {
    @Value("${spring.redis.host}")
    private String redisHost;

    @Value("${spring.redis.port}")
    private int redisPort;

    @Value("${spring.redis.database}")
    private int database;

    @Value("${spring.redis.jedis.pool.max-active}")
    private int maxActive;

    @Value("${spring.redis.jedis.pool.max-idle}")
    private int maxIdle;

    @Value("${spring.redis.jedis.pool.min-idle}")
    private int minIdle;

    @Value("${spring.redis.jedis.pool.max-wait}")
    private int maxWait;

    JedisPoolConfig getJedisPoolConfig() {
        JedisPoolConfig jedisPoolConfig = new JedisPoolConfig();
        jedisPoolConfig.setMaxTotal(maxActive);
        jedisPoolConfig.setMaxIdle(maxIdle);
        jedisPoolConfig.setMinIdle(minIdle);
        jedisPoolConfig.setMaxWait(Duration.ofSeconds(maxWait));
        return jedisPoolConfig;
    }

    @Bean
    RedisConnectionFactory redisConnectionFactory() {
        RedisStandaloneConfiguration redisStandaloneConfiguration =
            new RedisStandaloneConfiguration();
        redisStandaloneConfiguration.setHostName(redisHost);
        redisStandaloneConfiguration.setPort(redisPort);
        redisStandaloneConfiguration.setDatabase(database);

        JedisClientConfiguration jedisClientConfiguration =
            JedisClientConfiguration.builder()
                .usePooling()
                .poolConfig(getJedisPoolConfig())
                .build();

        return new JedisConnectionFactory(
            redisStandaloneConfiguration,
            jedisClientConfiguration
        );
    }
}
```

### Serialization (Full Type Info)

Required for proper deserialization when reading from cache:

```java
@Configuration
@EnableCaching
public class RedisCacheConfig {
    @Bean
    public RedisCacheConfiguration cacheConfiguration() {
        ObjectMapper objectMapper = new ObjectMapper();
        objectMapper
            .setSerializationInclusion(JsonInclude.Include.NON_NULL)
            .setDateFormat(new StdDateFormat())
            .disable(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES)
            .disable(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS)
            .registerModule(new JavaTimeModule())
            .activateDefaultTyping(
                objectMapper.getPolymorphicTypeValidator(),
                ObjectMapper.DefaultTyping.EVERYTHING
            );

        return RedisCacheConfiguration.defaultCacheConfig()
            .disableCachingNullValues()
            .serializeValuesWith(
                RedisSerializationContext.SerializationPair.fromSerializer(
                    new GenericJackson2JsonRedisSerializer(objectMapper)
                )
            );
    }

    @Bean
    public CacheManager cacheManager(
            RedisConnectionFactory redisConnectionFactory) {
        return RedisCacheManager.builder(redisConnectionFactory)
            .cacheDefaults(cacheConfiguration())
            .build();
    }
}
```

### TTL Configuration

```java
@Bean
public CacheManager cacheManager(
        RedisConnectionFactory redisConnectionFactory) {
    return RedisCacheManager.builder(redisConnectionFactory)
        .cacheDefaults(cacheConfiguration())
        .withCacheConfiguration(
            "deviceCustomer",
            cacheConfiguration().entryTtl(Duration.ofSeconds(60))
        )
        .build();
}
```

**Note:** `@CachePut` resets the TTL when updating a cache entry.

### Multiple CacheManagers

```java
@Configuration
public class RedisConfig {
    @Bean("redisConnectionFactoryQuote")
    @Primary
    RedisConnectionFactory redisConnectionFactoryQuote() { ... }

    @Bean("redisConnectionFactoryRoute")
    RedisConnectionFactory redisConnectionFactoryRoute() { ... }
}

@Configuration
public class RedisCacheConfig {
    @Primary
    @Bean("cacheManagerQuote")
    public CacheManager cacheManagerQuote(
            @Qualifier("redisConnectionFactoryQuote")
            RedisConnectionFactory factory) {
        return RedisCacheManager.builder(factory)
            .cacheDefaults(RedisCacheConfiguration.defaultCacheConfig())
            .build();
    }

    @Bean("cacheManagerRoute")
    public CacheManager cacheManagerRoute(
            @Qualifier("redisConnectionFactoryRoute")
            RedisConnectionFactory factory) {
        return RedisCacheManager.builder(factory)
            .cacheDefaults(RedisCacheConfiguration.defaultCacheConfig())
            .build();
    }
}
```

Usage:
```java
@Cacheable(cacheManager = "cacheManagerRoute", value = "countries")
public List<CountryDto> getAll() { ... }
```

## Library Comparison

| Library | Pros | Cons | Use Case |
|---------|------|------|----------|
| **Jedis** | Simple, direct API, good docs | Not thread-safe, blocking I/O | Small/medium apps, simplicity priority |
| **Lettuce** | Reactive, thread-safe, high perf | Complex API, steep learning curve | High concurrency, WebFlux |
| **Redisson** | Distributed data structures, JCache | Memory overhead, complex API | Distributed systems, advanced patterns |

**Global66 Standard:** Use Jedis for simplicity and direct Redis command mapping.

## Accessing Cache Without @Cacheable

When you need to read without updating:

```java
@Component
public class CountryCacheService {
    @Autowired
    @Qualifier("cacheManagerRoute")
    private CacheManager cacheManagerRoute;

    public List<CountryDto> getAll(String key) {
        Cache cache = cacheManagerRoute.getCache("countries-enabled");
        Cache.ValueWrapper valueWrapper = cache.get(key);
        return (valueWrapper != null)
            ? (List<CountryDto>) valueWrapper.get()
            : null;
    }
}
```

## Cache DTO Library

Global66 maintains a shared library `arch-cache-dto` for cache DTOs to ensure consistent serialization across services.

**Important:**
- New attributes added to DTOs not in cached objects → set to `null`
- Removed attributes → new structure respected
- Always maintain backward compatibility
- Any modifications require architecture team approval via formal request

## Common Violations

| Violation | Problem | Correct Approach |
|-----------|---------|------------------|
| Cache name in singular | `value = "country"` | Use plural: `value = "countries"` |
| Key without quotes | `key = "all"` | Quote string keys: `key = "'all'"` |
| Missing @Scope | Self-invocation skips cache | Add `@Scope(proxyMode = ScopedProxyMode.TARGET_CLASS)` |
| No TTL on Redis | Cache never expires | Configure `entryTtl()` in CacheManager |
| Cache in wrong layer | Entities leaking | Cache service in `cache/` package, use domain objects |

## Compliance Checklist

- [ ] Cache name is plural, camelCase, English
- [ ] String keys use single quotes: `'all'`, `'enabled'`
- [ ] Composite keys use comma-separated parameters
- [ ] Cache service has `@Scope(proxyMode = ScopedProxyMode.TARGET_CLASS)`
- [ ] TTL configured for Redis caches
- [ ] DTOs from shared library used for serialization
- [ ] Cache eviction implemented when data changes
- [ ] Proper serialization with type info for Redis
