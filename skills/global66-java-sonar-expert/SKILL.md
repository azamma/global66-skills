---
name: global66-java-sonar-expert
description: SonarQube review and fix automation for Global66 Java microservices. Use when evaluating code coverage, resolving Sonar issues (rules java:S*), or analyzing reports based on the MS Base profile (sonar_rules.xml). Applies Global66 patterns (SRP, BusinessException, Logging) for compliance.
---

# SonarQube Review & Fix Skill

This skill automates the process of identifying, analyzing, and fixing SonarQube findings in Global66 microservices, focusing on **Issues** and **Code Coverage**.

## Core Workflows

### 1. Issue Analysis & Resolution
- **Rule Verification**: Cross-reference the Sonar rule (e.g., `java:S3776`) with `assets/sonar_rules.xml` to verify its priority and parameters (e.g., max cognitive complexity).
- **Global66 Mapping**: Use `references/sonar-patterns.md` to find the specific Global66 fix pattern for the rule.
- **Fix Implementation**: Prioritize CRITICAL/MAJOR issues. Apply SRP naming for complexity, `BusinessException` for generic errors, and Slf4j for logging compliance.

### 2. Coverage Gap Detection
- **Git Diff Scope**: Only analyze coverage for **new or modified methods** (diff-based coverage).
- **Gap Identification**: Identify lines not covered by tests in the Sonar report or via manual analysis of the code compared to its tests.
- **Test Generation**: Create or extend JUnit 5 tests following the hexagonal architecture:
  - Mock external layers (Persistence, Clients).
  - Use JSON fixtures for complex DTOs (stored in `src/test/resources/`).
  - Target 100% coverage of new/modified logic.

### 3. Sonar Report Analysis
- Parse XML/JSON Sonar reports or use git diff to simulate a report.
- Produce a summary table of findings:
  | Severity | Rule | File | Status | Action |
  |----------|------|------|--------|--------|

## Reference Materials
- **Rules Profile**: `assets/sonar_rules.xml` (The "MS Base" profile with rule keys and priorities).
- **Fix Patterns**: `references/sonar-patterns.md` (Detailed mapping of Sonar rules to Global66 architectural patterns).

## Implementation Guidelines
- **Cognitive Complexity (S3776)**: Always extract logic into private methods with semantic names (`ensure*`, `verify*`, `is*`, `has*`).
- **Generic Exceptions (S112)**: Convert to `BusinessException` with `ErrorCode`.
- **Test Fixtures**: Never build objects with setters; load them from JSON resources.
- **Logging (S106)**: Ensure logs follow the START/END pattern and do not expose PII.
