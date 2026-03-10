# Repository Patterns — Global66

Guidelines for JPA repository methods following hexagonal architecture principles.

---

## Core Rule: Never Return Entities

When creating repository methods, **never return the full Entity**. Choose the appropriate return type based on use case:

| Use Case | Return Type | Example |
|----------|-------------|---------|
| Single attribute | `Optional<T>` | `Optional<Integer> findUserIdByEmail(String email)` |
| Multiple attributes | Projection record | `Optional<UserInfoData> findUserInfoById(Integer id)` |
| Full entity needed | Domain object via Persistence | `Optional<UserData> findById(Integer id)` |

**Why:** Returning entities couples the query result to the persistence layer, bypassing the hexagonal architecture. Projections are lightweight, immutable, and follow SRP.

---

## Projection Records

For queries returning multiple fields but not the full entity, define a record in the same repository file or as a top-level class:

```java
public interface UserRepository extends JpaRepository<UserEntity, Integer> {

    // Single attribute - Optional<T>
    @Query("SELECT u.id FROM UserEntity u WHERE u.email = :email")
    Optional<Integer> findUserIdByEmail(String email);

    // Multiple attributes - Projection record
    @Query("SELECT new com.global.user.persistence.repository.UserRepository.UserInfoData(u.id, u.email, u.status) FROM UserEntity u WHERE u.id = :id")
    Optional<UserInfoData> findUserInfoById(Integer id);

    // Record projection - defined inside repository or separately
    record UserInfoData(Integer id, String email, UserStatusEnum status) {}
}
```

### Alternative: Interface-based Projections

```java
// Interface projection (Spring Data generates implementation)
public interface UserSummary {
    Integer getId();
    String getEmail();
    UserStatusEnum getStatus();
}

public interface UserRepository extends JpaRepository<UserEntity, Integer> {
    Optional<UserSummary> findUserSummaryById(Integer id);
}
```

---

## Rules Reference

| Rule | Requirement |
|------|-------------|
| `REPO_NO_ENTITY_RETURN` | Never return `Entity` from repository methods — always use projections or domain objects |
| `REPO_SINGLE_ATTR` | Single attribute queries → return `Optional<T>` (Integer, String, Boolean, etc.) |
| `REPO_MULTI_ATTR` | Multiple attributes → return `Optional<RecordProjection>` with descriptive name |
| `REPO_RECORD_NAMING` | Projection records named `{Entity}{Purpose}Data` or `{Purpose}Data` (e.g., `UserSummaryData`, `UserInfoData`) |
| `REPO_LIST_PROJECTION` | List queries can return `List<Projection>` — still no entities |
| `REPO_NO_MANY_JOINS` | Avoid complex queries with multiple joins. Keep them efficient. |

---

## Persistence Port Pattern

The repository is never injected directly into services. Use a `*Persistence` port:

```java
// Port interface
public interface UserPersistence {
    Optional<UserData> findById(Integer id);
    UserData save(UserData userData);
    boolean existsByEmail(String email);
}

// Implementation
@Component
@RequiredArgsConstructor
public class UserPersistenceImpl implements UserPersistence {
    private final UserRepository userRepository;

    @Override
    public Optional<UserData> findById(Integer id) {
        return userRepository.findById(id)
            .map(UserMapper.INSTANCE::toData);
    }

    @Override
    public UserData save(UserData userData) {
        UserEntity entity = UserMapper.INSTANCE.toEntity(userData);
        return UserMapper.INSTANCE.toData(userRepository.save(entity));
    }

    @Override
    public boolean existsByEmail(String email) {
        return userRepository.existsByEmail(email);
    }
}
```

**Key points:**
- `*Persistence` port returns domain objects (`*Data`), never entities
- Mapping happens inside the persistence implementation
- Services inject `*Persistence`, not `*Repository`

---

## Query Method Naming

Spring Data JPA method naming conventions:

| Pattern | Generated Query |
|---------|-----------------|
| `findById(id)` | `WHERE id = ?` |
| `findByEmailAndStatus(email, status)` | `WHERE email = ? AND status = ?` |
| `existsByEmail(email)` | `SELECT EXISTS(... WHERE email = ?)` |
| `countByStatus(status)` | `SELECT COUNT(*) WHERE status = ?` |
| `deleteByIdAndStatus(id, status)` | `DELETE WHERE id = ? AND status = ?` |

For complex queries, use `@Query` with JPQL or native SQL.

---

## Compliance Checklist

- [ ] Repository methods never return `*Entity` types
- [ ] Single attribute queries return `Optional<T>`
- [ ] Multi-attribute queries use projection records
- [ ] Projection records follow naming convention `{Entity}{Purpose}Data`
- [ ] Services inject `*Persistence` ports, not repositories
- [ ] Complex queries with joins are reviewed for performance
- [ ] `@Query` annotations use JPQL unless native SQL is required
