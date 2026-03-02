LIQUIBASE YAML COMPLIANCE REPORT
─────────────────────────────────
Status: NON_COMPLIANT

VIOLATIONS
──────────

[1] CRITICAL · NAMING · changeSet id: 12345
    Issue: ChangeSet ID must follow the format {timestamp}-{sequential} (e.g., 1766002045101-1),
           not a plain integer. Auto-generated numeric IDs are not allowed.
    Fix:   id: 20240101120000-1

[2] CRITICAL · NAMING · changeSet author: root
    Issue: Author must follow the pattern {firstname.lastname} or
           {firstname.lastname} (generated) — never a generic system user like "root".
    Fix:   author: firstname.lastname

[3] CRITICAL · NAMING · table: Customers
    Issue: Table name must be singular and snake_case. "Customers" is plural and PascalCase.
    Fix:   tableName: customer

[4] CRITICAL · DOCUMENTATION · table: Customers (→ customer)
    Issue: Missing 'remarks' field with MAE/TRX/DOM/TMP classification at table level.
           Every table requires a remarks explaining its purpose and type.
    Fix:   remarks: 'DOM: Customer entity for core business domain'

[5] CRITICAL · DATA_TYPE · column: id
    Issue: Type BIGINT is not allowed. Primary keys must use INT.
    Fix:   type: INT

[6] CRITICAL · NAMING · column: id — primaryKey constraint
    Issue: Primary key constraint is missing the required primaryKeyName.
           Must follow pattern PK_{table}_{field}.
    Fix:   Add primaryKeyName: PK_customer_id

[7] CRITICAL · CONSTRAINT · column: id
    Issue: Auto-increment PK column is missing nullable: false constraint.
           G81-POL-033 requires nullable: false on PKs.
    Fix:   Add constraints.nullable: false

[8] CRITICAL · DOCUMENTATION · column: id
    Issue: Missing 'remarks' field. Every column requires a descriptive remarks.
    Fix:   remarks: Primary key identifier

[9] CRITICAL · NAMING · column: customerName
    Issue: Column name must be snake_case. "customerName" is camelCase.
    Fix:   name: customer_name

[10] CRITICAL · DATA_TYPE · column: customerName (→ customer_name)
     Issue: Type varchar(255) uses lowercase. All types must be uppercase.
     Fix:   type: VARCHAR(255)

[11] CRITICAL · DOCUMENTATION · column: customerName (→ customer_name)
     Issue: Missing 'remarks' field on column.
     Fix:   remarks: Full name of the customer

[12] CRITICAL · DATA_TYPE · column: email
     Issue: Type varchar(255) uses lowercase. All types must be uppercase.
     Fix:   type: VARCHAR(255)

[13] CRITICAL · DOCUMENTATION · column: email
     Issue: Missing 'remarks' field on column.
     Fix:   remarks: Customer email address

[14] CRITICAL · DOCUMENTATION · table: customer — audit columns
     Issue: Table is missing required audit column 'created_at DATETIME NOT NULL'.
            Master and domain tables must include created_at.
     Fix:   Add column created_at with type: DATETIME and constraints.nullable: false

[15] CRITICAL · NAMING · index: idx1
     Issue: Index name is non-descriptive and does not follow the IDX_{TABLE}_{COLUMN} pattern.
     Fix:   indexName: IDX_CUSTOMER_CUSTOMER_NAME

[16] CRITICAL · NAMING · table reference in createIndex: Customers
     Issue: Index references the old plural/PascalCase table name. Must be corrected to match
            the renamed table.
     Fix:   tableName: customer

[17] CRITICAL · NAMING · foreignKey constraintName: FK_1
     Issue: Foreign key constraint name must follow FK_{origin}_{target}_{field} pattern
            in UPPER_SNAKE_CASE. "FK_1" is a non-descriptive auto-generated name.
     Fix:   constraintName: FK_CUSTOMER_ACCOUNT_ACCOUNT_ID

[18] CRITICAL · NAMING · foreignKey baseTableName: Customers
     Issue: Table name reference is plural/PascalCase. Must reference the corrected table name.
     Fix:   baseTableName: customer

[19] WARNING · STRUCTURE · changeSet 12345 groups createTable + createIndex + addForeignKeyConstraint
     Issue: All three operations are bundled in a single changeSet. Each concern must have
            its own changeSet (one createTable, one createIndex, one addForeignKeyConstraint).
     Fix:   Split into three separate changeSets: {timestamp}-1, {timestamp}-2, {timestamp}-3

[20] WARNING · NAMING · foreignKey referencedTableName: Accounts
     Issue: Referenced table name is plural/PascalCase. Should follow the same snake_case
            singular convention. Assuming the target table is correctly named 'account'.
     Fix:   referencedTableName: account

CORRECTED YAML
──────────────

```yaml
databaseChangeLog:

  - changeSet:
      id: 20240101120000-1
      author: firstname.lastname
      changes:
        - createTable:
            tableName: customer
            remarks: 'DOM: Customer entity for core business domain'
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
                  remarks: Customer email address
                  constraints:
                    nullable: false
              - column:
                  name: account_id
                  type: INT
                  remarks: Reference to the associated account
                  constraints:
                    nullable: false
              - column:
                  name: created_at
                  type: DATETIME
                  remarks: Timestamp when the customer record was created
                  constraints:
                    nullable: false

  - changeSet:
      id: 20240101120000-2
      author: firstname.lastname
      changes:
        - createIndex:
            indexName: IDX_CUSTOMER_CUSTOMER_NAME
            tableName: customer
            columns:
              - column:
                  name: customer_name

  - changeSet:
      id: 20240101120000-3
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

SUMMARY
───────
Total violations: 20 (18 CRITICAL, 2 WARNING)

Key issues grouped by category:

  NAMING (9 violations)
    - ChangeSet ID not in {timestamp}-{sequential} format
    - Author is "root" instead of firstname.lastname
    - Table name is plural + PascalCase ("Customers" → "customer")
    - Column name is camelCase ("customerName" → "customer_name")
    - Index name is non-descriptive ("idx1" → "IDX_CUSTOMER_CUSTOMER_NAME")
    - FK constraint name is non-descriptive ("FK_1" → "FK_CUSTOMER_ACCOUNT_ACCOUNT_ID")
    - Table references in index and FK use original invalid name
    - Referenced table name is plural/PascalCase ("Accounts" → "account")

  DATA_TYPE (3 violations)
    - PK column uses BIGINT instead of INT
    - Two varchar columns use lowercase instead of VARCHAR(n)

  DOCUMENTATION (6 violations)
    - Table missing 'remarks' with MAE/TRX/DOM/TMP classification
    - Columns id, customerName, email each missing 'remarks'
    - Table missing required audit column 'created_at DATETIME NOT NULL'

  CONSTRAINT (1 violation)
    - PK column missing nullable: false

  STRUCTURE (1 violation)
    - Single changeSet bundles createTable + createIndex + addForeignKeyConstraint;
      must be split into three separate changeSets
