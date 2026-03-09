"""
Centralized constants for the database discovery scripts.
"""

# Schemas to exclude from all discovery operations
EXCLUDED_SCHEMAS = (
    'information_schema',
    'mysql',
    'performance_schema',
    'sys'
)

# Table names to exclude (e.g., Liquibase utility tables)
EXCLUDED_TABLES = (
    'DATABASECHANGELOG',
    'DATABASECHANGELOGLOCK'
)
