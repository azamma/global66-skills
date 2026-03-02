# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a **Claude Code skills repository** for Global66 Java microservices development. It contains skill definitions, reference documentation, and evaluation test cases to ensure Claude Code generates code following Global66's hexagonal architecture standards.

## Repository Structure

```
/mnt/c/repos/global66-skills/
├── skills/global66-java-dev/           # Main skill definition
│   ├── SKILL.md                        # ~590 lines - core skill with architecture rules
│   ├── evals/evals.json                # 7 evaluation test cases (IDs 1-7)
│   └── references/                     # 12 specialized reference documents
│       ├── srp-patterns.md             # Semantic naming (ensure*, fetch*, guard*)
│       ├── transactional.md            # @Transactional rules + audit workflow
│       ├── logging.md                  # SGSI-POL-005 logging compliance
│       ├── sqs.md                      # SQS config + 4 traceability classes
│       ├── swagger.md                  # OpenAPI/Swagger guidelines
│       ├── liquibase.md                # G81-POL-033 DB migration rules
│       ├── api-client.md               # Retrofit client generation (9 files)
│       ├── tests.md                    # Unit test patterns (Given_When_Then)
│       ├── sonar.md                    # SonarQube coverage gaps + issues
│       ├── checklist.md                # Pre-submission 40+ item checklist
│       ├── cache.md                    # Redis/Caffeine caching guidelines
│       ├── api-rest.md                 # REST API naming and structure
│       └── exceptions.md               # ApiRestException, ErrorReason, ErrorSource
├── global66-java-dev-workspace/        # Evaluation workspaces
│   └── iteration-1/                    # A/B test results (7 scenarios)
│       ├── endpoint-generation/        # Eval 1: Create endpoint (with vs without skill)
│       ├── service-refactor/           # Eval 2: Refactor legacy service
│       ├── unit-tests/                 # Eval 3: Generate tests
│       ├── log-compliance/             # Eval 4: Audit logs from diff
│       ├── sqs-config/                 # Eval 5: SQS FIFO configuration
│       ├── swagger-audit/              # Eval 6: Swagger compliance review
│       └── liquibase-review/           # Eval 7: YAML migration review
└── global66-java-workspace/            # Legacy workspace (ignore)
```

## Key Architecture Patterns

### Hexagonal Package Structure
```
com.global.{domain}/
├── presentation/          # Controllers (interfaces), DTOs, mappers
├── business/            # Services (interfaces + impl), @Transactional here only
├── persistence/         # Repositories, Entities, *Persistence ports
├── domain/              # *Data objects, external_request/ for API clients
├── client/              # Retrofit REST clients (9-file pattern)
├── config/              # Spring configuration
└── enums/, util/        # Shared enums and utilities
```

### Critical Rules (from SKILL.md)

**Layer Isolation:**
- Entities (`*Entity`) stay in `persistence/` only — never leak to business/presentation
- Services inject `*Persistence` ports, never repositories directly
- Controllers are thin: validate input → delegate → map response

**@Transactional (Business Layer Only):**
- Only on `public` methods (private/protected bypasses proxy)
- Always `rollbackFor = Exception.class` for write operations
- `readOnly = true` for `find*`/`fetch*`/`get*`/`list*` methods
- No HTTP calls inside `@Transactional` blocks
- No `this.method()` calls to another `@Transactional` method

**MapStruct Mappers:**
- Always `componentModel = "default"` with `INSTANCE` singleton
- Per layer: `persistence/mapper/`, `presentation/mapper/`, `client/mapper/`

**SRP & Naming:**
- `ensure*` - precondition validation, throws
- `verify*` - complex multi-step validation
- `guardAgainst*` - defensive checks
- `is*`/`has*` - boolean predicates
- `fetch*`/`require*` - get or throw NOT_FOUND
- `build*Exception` - exception factories

## Reference Microservice

The `ms-geolocation` microservice at `/mnt/c/repos/ms-geolocation/` serves as the **Gold Standard** for all patterns. Key files to study:

- `LocationEntity.java` - JPA entity with `@Comment`, proper indexes
- `LocationMapper.java` - MapStruct with deep path mapping
- `HereClientImpl.java` - Retrofit client implementation
- `SqsClientConfig.java` - SQS traceability configuration
- `TracingMessageListenerWrapper.java` - MDC/traceId extraction
- `GeoCodeController.java` - Swagger annotations on interface

## Commands

This repository has no build system (no Maven/Gradle). It's documentation-only.

**File Operations:**
```bash
# Search for patterns across skills
grep -r "ensureUser" skills/

# Compare eval outputs
ls global66-java-dev-workspace/iteration-1/*/with_skill/
ls global66-java-dev-workspace/iteration-1/*/without_skill/
```

## Evaluation Workflow

When running evals, follow this pattern:

1. **Read the skill** first: `skills/global66-java-dev/SKILL.md`
2. **Read relevant references** from `references/*.md`
3. **Generate code** following all rules
4. **Store outputs** in `global66-java-dev-workspace/iteration-{N}/{scenario}/with_skill/`
5. **Run baseline** without reading skill for comparison
6. **Compare** outputs to measure skill effectiveness

### Evaluation Scenarios

| ID | Scenario | Key Rules Tested |
|----|----------|------------------|
| 1 | Endpoint generation | Hexagonal layers, MapStruct, @Transactional |
| 2 | Service refactor | SRP naming, exception factories, persistence ports |
| 3 | Unit tests | Given_When_Then, JSON fixtures, @Nested |
| 4 | Log compliance | SGSI-POL-005, PII detection, MDC async |
| 5 | SQS config | 4 traceability classes, FIFO patterns |
| 6 | Swagger audit | Interface annotations, @ErrorResponses |
| 7 | Liquibase review | G81-POL-033, naming conventions |

## Skill Development Guidelines

When modifying the skill:

1. **Update SKILL.md** frontmatter description if trigger conditions change
2. **Add reference docs** for new domains (already has 9)
3. **Update evals.json** to add new test cases
4. **Run evaluations** to verify skill effectiveness

### Reference Document Template

Each reference doc should include:
- Policy/rule summary
- Gold Standard code examples (from ms-geolocation)
- Common violations with before/after
- Compliance review format (for git diff audits)

## Claude Code Configuration

The `.claude/settings.local.json` contains permissions for this repository. The skill is automatically available when working in this directory.

## Memory

Long-term context is stored in `/root/.claude/projects/-mnt-c-repos-global66-skills/memory/MEMORY.md`.
