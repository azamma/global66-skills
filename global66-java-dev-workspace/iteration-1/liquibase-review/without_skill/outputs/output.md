# LIQUIBASE YAML COMPLIANCE REPORT
─────────────────────────────────
**Policy**: G81-POL-033
**Status**: NON_COMPLIANT
**Total Violations**: 14 (9 CRITICAL, 5 WARNING)

---

## VIOLATIONS
──────────────

### [1] CRITICAL · METADATA · changeSet id: `12345`
**Issue**: ChangeSet ID must follow the `{timestamp}-{sequential}` format (e.g., `1766002045101-1`). A plain integer like `12345` is a generic auto-generated ID that does not guarantee uniqueness across migrations and cannot be correlated to a deployment timestamp.
**Fix**: Use `id: 20260302120000-1` (timestamp of migration creation + sequential suffix).

---

### [2] CRITICAL · METADATA · author: `root`
**Issue**: Author must be in `firstname.lastname` format (e.g., `john.doe` or `john.doe (generated)`). Using `root` is not traceable to a real developer.
**Fix**: `author: firstname.lastname`

---

### [3] CRITICAL · NAMING · tableName: `Customers`
**Issue**: Table names must be **singular** and in **snake_case** with no CamelCase or plural forms. `Customers` violates both rules.
**Fix**: `tableName: customer`

---

### [4] CRITICAL · DOCUMENTATION · table: `Customers` — missing `remarks`
**Issue**: Every table must have a `remarks` field with a classification prefix: `MAE:`, `TRX:`, `DOM:`, or `TMP:`. This field is mandatory per G81-POL-033.
**Fix**: `remarks: 'DOM: Customer entity with personal and contact data'`

---

### [5] CRITICAL · DOCUMENTATION · column: `id` — missing `remarks`
**Issue**: Every column must have a `remarks` field with an English description. The `id` column has none.
**Fix**: `remarks: Primary key identifier`

---

### [6] CRITICAL · NAMING · column: `id` — missing `primaryKeyName`
**Issue**: The primary key constraint must include an explicit `primaryKeyName` following the pattern `PK_{table}_{field}`.
**Fix**: Add `primaryKeyName: PK_customer_id` inside the constraints block.

---

### [7] CRITICAL · DATA TYPE · column: `id` — type is `BIGINT`
**Issue**: Per the allowed data types table, primary keys must use `INT` (not `BIGINT`). `BIGINT` is not listed as an acceptable PK type under G81-POL-033.
**Fix**: `type: INT`

---

### [8] CRITICAL · NAMING · column: `customerName`
**Issue**: Column names must be in **snake_case**. `customerName` is camelCase.
**Fix**: `name: customer_name`

---

### [9] CRITICAL · DOCUMENTATION · columns `customerName` and `email` — missing `remarks`
**Issue**: Both columns are missing mandatory `remarks` descriptions.
**Fix**:
- `customerName`: `remarks: Full name of the customer`
- `email`: `remarks: Customer contact email address`

---

### [10] WARNING · NAMING · indexName: `idx1`
**Issue**: Index names must follow the pattern `IDX_{table}_{column}` in UPPER_SNAKE_CASE. `idx1` is a generic, non-descriptive name.
**Fix**: `indexName: IDX_CUSTOMER_CUSTOMER_NAME`

---

### [11] WARNING · NAMING · constraintName: `FK_1`
**Issue**: Foreign key constraint names must follow the pattern `FK_{origin}_{target}_{field}` in UPPER_SNAKE_CASE. `FK_1` is generic.
**Fix**: `constraintName: FK_CUSTOMER_ACCOUNT_ACCOUNT_ID`

---

### [12] WARNING · STRUCTURE · single changeSet bundles `createTable` + `createIndex` + `addForeignKeyConstraint`
**Issue**: Each changeSet must contain **one concern only**. Bundling table creation, index creation, and FK constraints into a single changeSet violates the granularity rule. If any one operation fails, the entire changeSet rolls back and Liquibase cannot apply partial corrections.
**Fix**: Split into three separate changeSets (sequential IDs: `-1`, `-2`, `-3`).

---

### [13] WARNING · DATA TYPE · column: `customerName` — type `varchar(255)` (lowercase)
**Issue**: Data types must use consistent uppercase notation: `VARCHAR(255)`, not `varchar(255)`.
**Fix**: `type: VARCHAR(255)`

---

### [14] WARNING · AUDIT COLUMNS · table `customer` — missing `created_at`
**Issue**: Master (`MAE:`) and transactional (`TRX:`) tables must include a `created_at DATETIME NOT NULL` audit column to track record creation time.
**Fix**: Add `created_at` column of type `DATETIME` with `nullable: false`.

---

## QUICK CHECKLIST SUMMARY

| Rule | Status |
|------|--------|
| File name: `{yyyyMMddHHmmss}_{JIRA-TICKET}.yaml` | NOT EVALUATED (name not provided) |
| Master changelog uses `includeAll`, untouched | NOT EVALUATED |
| Table name: singular, snake_case | FAIL — `Customers` |
| Table `remarks` with MAE/TRX/DOM/TMP classification | FAIL — missing |
| Every column has `remarks` | FAIL — all 3 columns missing |
| Primary key has `primaryKeyName: PK_{table}_id` | FAIL — missing |
| Foreign key: `constraintName: FK_{origin}_{target}_{field}` | FAIL — `FK_1` |
| Index: `indexName: IDX_{table}_{column}` | FAIL — `idx1` |
| Data types: `INT`, `VARCHAR(n)`, `DATETIME`, etc. | FAIL — `BIGINT`, lowercase `varchar` |
| Audit column `created_at DATETIME NOT NULL` | FAIL — missing |
| One concern per changeSet | FAIL — 3 concerns bundled |
| ChangeSet ID: `{timestamp}-{n}` format | FAIL — `12345` |
| Author: `firstname.lastname` | FAIL — `root` |

---

## CORRECTED YAML
─────────────────

```yaml
databaseChangeLog:

  # ChangeSet 1 — Create table: customer
  - changeSet:
      id: 20260302120000-1
      author: firstname.lastname
      changes:
        - createTable:
            tableName: customer
            remarks: 'DOM: Customer entity with personal and contact data'
            columns:
              - column:
                  name: id
                  type: INT
                  autoIncrement: true
                  remarks: Primary key identifier
                  constraints:
                    nullable: false
                    primaryKey: true
                    primaryKeyName: PK_customer_id
              - column:
                  name: customer_name
                  type: VARCHAR(255)
                  remarks: Full name of the customer
              - column:
                  name: email
                  type: VARCHAR(255)
                  remarks: Customer contact email address
                  constraints:
                    nullable: false
              - column:
                  name: account_id
                  type: INT
                  remarks: Foreign key reference to the associated account
                  constraints:
                    nullable: false
              - column:
                  name: created_at
                  type: DATETIME
                  remarks: Timestamp when the customer record was created
                  constraints:
                    nullable: false

  # ChangeSet 2 — Create index on customer_name
  - changeSet:
      id: 20260302120000-2
      author: firstname.lastname
      changes:
        - createIndex:
            indexName: IDX_CUSTOMER_CUSTOMER_NAME
            tableName: customer
            columns:
              - column:
                  name: customer_name

  # ChangeSet 3 — Add foreign key: customer.account_id -> account.id
  - changeSet:
      id: 20260302120000-3
      author: firstname.lastname
      changes:
        - addForeignKeyConstraint:
            baseColumnNames: account_id
            baseTableName: customer
            constraintName: FK_CUSTOMER_ACCOUNT_ACCOUNT_ID
            referencedColumnNames: id
            referencedTableName: account
            deferrable: false
            initiallyDeferred: false
            validate: true
```

---

## KEY CHANGES EXPLAINED

| # | Original | Corrected | Rule |
|---|----------|-----------|------|
| 1 | `id: 12345` | `id: 20260302120000-1` | ChangeSet ID must be `{timestamp}-{n}` |
| 2 | `author: root` | `author: firstname.lastname` | Author must be real developer identity |
| 3 | `tableName: Customers` | `tableName: customer` | Singular snake_case table names |
| 4 | No table `remarks` | `remarks: 'DOM: ...'` | Table classification is mandatory |
| 5 | `type: BIGINT` on PK | `type: INT` | PK must be `INT` |
| 6 | No `primaryKeyName` | `primaryKeyName: PK_customer_id` | Explicit PK naming required |
| 7 | `name: customerName` | `name: customer_name` | Column names must be snake_case |
| 8 | No column `remarks` | remarks on all columns | Every column needs a description |
| 9 | `type: varchar(255)` | `type: VARCHAR(255)` | Uppercase data type notation |
| 10 | `indexName: idx1` | `indexName: IDX_CUSTOMER_CUSTOMER_NAME` | `IDX_{table}_{column}` pattern |
| 11 | `constraintName: FK_1` | `constraintName: FK_CUSTOMER_ACCOUNT_ACCOUNT_ID` | `FK_{origin}_{target}_{field}` pattern |
| 12 | 3 concerns in 1 changeSet | 3 separate changeSets | One concern per changeSet |
| 13 | No `created_at` column | `created_at DATETIME NOT NULL` added | Audit column required on DOM/MAE/TRX tables |
| 14 | `tableName: Accounts` in FK | `referencedTableName: account` | Referenced table also needs snake_case singular |
