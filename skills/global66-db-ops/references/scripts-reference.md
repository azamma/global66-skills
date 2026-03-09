# Database Operations Scripts Reference

Guía completa de los scripts Python para interactuar con bases de datos MySQL de Global66.

## Setup

### Requisitos
- Python 3.7+
- `mysql-connector-python`: `pip install mysql-connector-python`
- `python-dotenv`: `pip install python-dotenv`
- `rich`: `pip install rich`

### Instalación Local

Copia estos scripts a tu carpeta local:

```bash
mkdir -p ./scripts/utils

# Crear archivo .env con credenciales
cat > .env << 'EOF'
DB_DEV_HOST=db-dev-wr.global66.com
DB_DEV_USER=tu_usuario
DB_DEV_PASSWORD=tu_password
DB_DEV_DATABASE=subscription

DB_CI_HOST=db-ci-wr.global66.com
DB_CI_USER=tu_usuario_ci
DB_CI_PASSWORD=tu_password_ci
DB_CI_DATABASE=subscription
EOF

# Proteger archivo .env
chmod 600 .env
```

---

## Utilities

### `utils/constants.py`

Constantes compartidas por todos los scripts.

```python
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
```

**Ubicación**: `./scripts/utils/constants.py`

---

### `utils/db_connect.py`

Utilidad de conexión a bases de datos con manejo de credenciales y context manager.

```python
#!/usr/bin/env python3
"""
Database connection utility for MySQL environments.
Provides environment-based configuration and context manager pattern.
"""
import os
import sys
from contextlib import contextmanager
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error

# Load environment variables from .env file
load_dotenv()

# Environment configurations
ENVIRONMENTS = {
    'dev': {
        'host': os.getenv('DB_DEV_HOST', 'db-dev-wr.global66.com'),
        'port': int(os.getenv('DB_DEV_PORT', 3306)),
        'user': os.getenv('DB_DEV_USER'),
        'password': os.getenv('DB_DEV_PASSWORD'),
        'database': os.getenv('DB_DEV_DATABASE', 'subscription'),
    },
    'ci': {
        'host': os.getenv('DB_CI_HOST', 'db-ci-wr.global66.com'),
        'port': int(os.getenv('DB_CI_PORT', 3306)),
        'user': os.getenv('DB_CI_USER'),
        'password': os.getenv('DB_CI_PASSWORD'),
        'database': os.getenv('DB_CI_DATABASE', 'subscription'),
    }
}


def validate_config(env: str, config: dict) -> None:
    """Validate that all required configuration values are present."""
    required = ['host', 'user', 'password']
    missing = [k for k in required if not config.get(k)]
    if missing:
        raise ValueError(
            f"Missing required configuration for '{env}' environment: {', '.join(missing)}.\n"
            f"Please set DB_{env.upper()}_* environment variables or add them to .env file."
        )


def get_connection(env: str = 'dev'):
    """
    Create a MySQL connection for the specified environment.

    Args:
        env: Environment name ('dev' or 'ci')

    Returns:
        mysql.connector.connection.MySQLConnection

    Raises:
        ValueError: If environment is unknown or configuration is incomplete
        ConnectionError: If connection fails
    """
    if env not in ENVIRONMENTS:
        raise ValueError(f"Unknown environment: '{env}'. Available: {', '.join(ENVIRONMENTS.keys())}")

    config = ENVIRONMENTS[env].copy()
    validate_config(env, config)

    try:
        conn = mysql.connector.connect(**config)
        return conn
    except Error as e:
        raise ConnectionError(f"Failed to connect to {env} environment: {e}")


@contextmanager
def db_connection(env: str = 'dev'):
    """
    Context manager for database connections.

    Usage:
        with db_connection('dev') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
    """
    conn = None
    try:
        conn = get_connection(env)
        yield conn
    finally:
        if conn and conn.is_connected():
            conn.close()


def list_available_environments():
    """Return list of available environment names."""
    return list(ENVIRONMENTS.keys())


def print_env_banner(env: str):
    """Print a safety banner to indicate which environment is being used."""
    from rich.console import Console
    from rich.panel import Panel

    console = Console()
    color = "yellow" if env == 'dev' else "red"
    banner_text = f"CONNECTED TO: [bold]{env.upper()}[/bold] ENVIRONMENT\nHost: {ENVIRONMENTS[env]['host']}"

    console.print(Panel(banner_text, style=f"bold {color}", expand=False))
```

**Ubicación**: `./scripts/utils/db_connect.py`

---

## Scripts Principales

### `list_schemas.py`

Lista todos los esquemas/bases de datos disponibles.

```python
#!/usr/bin/env python3
"""
List all available database schemas.
Usage: python list_schemas.py [--env dev|ci]
"""
import argparse
import sys
import os
from rich.console import Console
from rich.table import Table
from rich import box

# Add the parent directory to sys.path to allow importing from utils
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils.db_connect import db_connection, print_env_banner
from utils.constants import EXCLUDED_SCHEMAS

console = Console()


def list_schemas(env: str):
    """List all databases the user has access to."""
    with db_connection(env) as conn:
        cursor = conn.cursor()
        cursor.execute("SHOW DATABASES")
        schemas = [row[0] for row in cursor.fetchall() if row[0] not in EXCLUDED_SCHEMAS]
        return schemas


def display_schemas(schemas: list, env: str):
    """Display schemas in a Rich table."""
    table = Table(
        title=f"Database Schemas ({env} environment)",
        box=box.MINIMAL_DOUBLE_HEAD,
        header_style="bold cyan"
    )
    table.add_column("#", justify="right", style="dim", width=4)
    table.add_column("Schema Name", style="green")

    for i, schema in enumerate(schemas, 1):
        table.add_row(str(i), schema)

    console.print(table)
    console.print(f"\n[dim]Total: {len(schemas)} schema(s)[/dim]")


def main():
    parser = argparse.ArgumentParser(
        description="List all available database schemas."
    )
    parser.add_argument(
        "--env",
        choices=['dev', 'ci'],
        default='dev',
        help="Database environment to connect to (default: dev)"
    )

    args = parser.parse_args()
    print_env_banner(args.env)

    try:
        schemas = list_schemas(args.env)
        display_schemas(schemas, args.env)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
```

**Ubicación**: `./scripts/list_schemas.py`

**Uso**:
```bash
python3 ./scripts/list_schemas.py --env dev
```

---

### `list_tables.py`

Lista todas las tablas en un esquema específico.

```python
#!/usr/bin/env python3
"""
List all tables within a specified schema.
Usage: python list_tables.py [--env dev|ci] <schema_name>
"""
import argparse
import sys
import os
from rich.console import Console
from rich.table import Table
from rich import box

# Add the parent directory to sys.path to allow importing from utils
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils.db_connect import db_connection, print_env_banner
from utils.constants import EXCLUDED_TABLES

console = Console()

def list_tables(env: str, schema: str):
    """List all tables in the specified schema."""
    with db_connection(env) as conn:
        cursor = conn.cursor()
        # Use SHOW TABLES FROM to avoid changing database context
        cursor.execute(f"SHOW TABLES FROM `{schema}`")
        tables = [row[0] for row in cursor.fetchall() if row[0] not in EXCLUDED_TABLES]
        return tables

def display_tables(tables: list, schema: str, env: str):
    """Display tables in a Rich table."""
    table = Table(
        title=f"Tables in '{schema}' Schema ({env} environment)",
        box=box.MINIMAL_DOUBLE_HEAD,
        header_style="bold cyan"
    )
    table.add_column("#", justify="right", style="dim", width=4)
    table.add_column("Table Name", style="green")

    for i, tbl in enumerate(tables, 1):
        table.add_row(str(i), tbl)

    console.print(table)
    console.print(f"\n[dim]Total: {len(tables)} table(s)[/dim]")

def main():
    parser = argparse.ArgumentParser(
        description="List all tables within a specified schema."
    )
    parser.add_argument(
        "schema",
        help="Name of the schema/database to list tables from"
    )
    parser.add_argument(
        "--env",
        choices=['dev', 'ci'],
        default='dev',
        help="Database environment to connect to (default: dev)"
    )

    args = parser.parse_args()
    print_env_banner(args.env)

    try:
        tables = list_tables(args.env, args.schema)
        display_tables(tables, args.schema, args.env)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
```

**Ubicación**: `./scripts/list_tables.py`

**Uso**:
```bash
python3 ./scripts/list_tables.py subscription --env dev
```

---

### `describe_table.py`

Describe la estructura de una tabla (columnas, tipos, claves, índices).

```python
#!/usr/bin/env python3
"""
Describe a table's structure (columns, types, keys, indices).
Usage: python scripts/describe_table.py <schema> <table> [--env dev|ci]
"""
import argparse
import sys
import os
from rich.console import Console
from rich.table import Table
from rich import box

# Add the parent directory to sys.path to allow importing from utils
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils.db_connect import db_connection, print_env_banner

console = Console()

def describe_columns(env: str, schema: str, table_name: str):
    """Fetch column details for a table."""
    with db_connection(env) as conn:
        cursor = conn.cursor()
        cursor.execute(f"SHOW COLUMNS FROM `{schema}`.`{table_name}`")
        columns = cursor.fetchall()
        # Column descriptions from SHOW COLUMNS: Field, Type, Null, Key, Default, Extra
        return columns

def describe_indices(env: str, schema: str, table_name: str):
    """Fetch index details for a table."""
    with db_connection(env) as conn:
        cursor = conn.cursor()
        cursor.execute(f"SHOW INDEX FROM `{schema}`.`{table_name}`")
        indices = cursor.fetchall()
        # Column descriptions from SHOW INDEX: Table, Non_unique, Key_name, Seq_in_index, Column_name, Collation, Cardinality, Sub_part, Packed, Null, Index_type, Comment, Index_comment, Visible, Expression
        return indices

def display_columns(columns: list, table_name: str, schema: str):
    """Display column details in a Rich table."""
    table = Table(
        title=f"Columns in '{schema}.{table_name}'",
        box=box.MINIMAL_DOUBLE_HEAD,
        header_style="bold cyan"
    )
    table.add_column("Field", style="green")
    table.add_column("Type", style="yellow")
    table.add_column("Null", style="dim")
    table.add_column("Key", style="red")
    table.add_column("Default", style="dim")
    table.add_column("Extra", style="blue")

    for col in columns:
        table.add_row(*[str(val) if val is not None else "NULL" for val in col])

    console.print(table)

def display_indices(indices: list):
    """Display index details in a Rich table."""
    if not indices:
        console.print("\n[yellow]No indices found.[/yellow]")
        return

    table = Table(
        title="Table Indices",
        box=box.MINIMAL_DOUBLE_HEAD,
        header_style="bold magenta"
    )
    table.add_column("Key Name", style="green")
    table.add_column("Unique", style="yellow")
    table.add_column("Seq", style="dim")
    table.add_column("Column", style="cyan")
    table.add_column("Type", style="blue")
    table.add_column("Visible", style="dim")

    for idx in indices:
        # Index info mapped: Key_name (2), Non_unique (1), Seq_in_index (3), Column_name (4), Index_type (10), Visible (13)
        unique = "Yes" if idx[1] == 0 else "No"
        table.add_row(
            str(idx[2]),
            unique,
            str(idx[3]),
            str(idx[4]),
            str(idx[10]),
            str(idx[13])
        )

    console.print(table)

def main():
    parser = argparse.ArgumentParser(
        description="Describe a table's structure (columns, types, keys, indices)."
    )
    parser.add_argument("schema", help="Schema name")
    parser.add_argument("table", help="Table name")
    parser.add_argument(
        "--env",
        choices=['dev', 'ci'],
        default='dev',
        help="Database environment (default: dev)"
    )

    args = parser.parse_args()
    print_env_banner(args.env)

    try:
        console.print(f"🔍 Describing [bold cyan]{args.schema}.{args.table}[/bold cyan]...")

        columns = describe_columns(args.env, args.schema, args.table)
        display_columns(columns, args.table, args.schema)

        indices = describe_indices(args.env, args.schema, args.table)
        display_indices(indices)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
```

**Ubicación**: `./scripts/describe_table.py`

**Uso**:
```bash
python3 ./scripts/describe_table.py subscription users --env dev
```

---

### `query_table.py`

Consulta datos de una tabla con límites seguros y opción de exportar a CSV.

```python
#!/usr/bin/env python3
"""
Query data from a table with limits and optional export to CSV.
Usage: python scripts/query_table.py <schema> <table> [--limit 10] [--export] [--env dev|ci]
"""
import argparse
import sys
import os
import csv
from rich.console import Console
from rich.table import Table
from rich import box

# Add the parent directory to sys.path to allow importing from utils
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils.db_connect import db_connection, print_env_banner

console = Console()

def query_table(env: str, schema: str, table_name: str, limit: int):
    """Fetch recent records from a table."""
    with db_connection(env) as conn:
        cursor = conn.cursor()

        # We assume the schema exists as per earlier validation steps
        # Use backticks for safety
        query = f"SELECT * FROM `{schema}`.`{table_name}` LIMIT %s"
        cursor.execute(query, (limit,))

        column_names = [i[0] for i in cursor.description]
        rows = cursor.fetchall()

        return column_names, rows

def display_results(columns: list, rows: list, table_name: str, env: str):
    """Display query results in a Rich table."""
    table = Table(
        title=f"Recent records from '{table_name}' ({env} environment)",
        box=box.MINIMAL_DOUBLE_HEAD,
        header_style="bold cyan"
    )

    for col in columns:
        table.add_column(col, style="green")

    for row in rows:
        table.add_row(*[str(val) for val in row])

    console.print(table)
    console.print(f"\n[dim]Showing {len(rows)} record(s)[/dim]")

def export_results(columns: list, rows: list, table_name: str):
    """Export results to a CSV file."""
    output_dir = "exports"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    file_path = os.path.join(output_dir, f"{table_name}_recent.csv")
    with open(file_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, quoting=csv.QUOTE_NONNUMERIC)
        writer.writerow(columns)
        writer.writerows(rows)

    console.print(f"\n✅ Results exported to [bold green]{file_path}[/bold green]")

def main():
    parser = argparse.ArgumentParser(
        description="Query recent records from a database table."
    )
    parser.add_argument("schema", help="Schema name")
    parser.add_argument("table", help="Table name")
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Number of records to fetch (default: 10)"
    )
    parser.add_argument(
        "--export",
        action="store_true",
        help="Export results to CSV in exports/ directory"
    )
    parser.add_argument(
        "--env",
        choices=['dev', 'ci'],
        default='dev',
        help="Database environment (default: dev)"
    )

    args = parser.parse_args()
    print_env_banner(args.env)

    try:
        columns, rows = query_table(args.env, args.schema, args.table, args.limit)
        if not rows:
            console.print(f"[yellow]No records found in {args.schema}.{args.table}[/yellow]")
            return

        display_results(columns, rows, args.table, args.env)

        if args.export:
            export_results(columns, rows, args.table)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
```

**Ubicación**: `./scripts/query_table.py`

**Uso**:
```bash
# Query con límite (default 10)
python3 ./scripts/query_table.py subscription users --env dev

# Query con límite personalizado
python3 ./scripts/query_table.py subscription users --limit 50 --env dev

# Query con exportación a CSV
python3 ./scripts/query_table.py subscription users --limit 100 --export --env dev
```

---

### `search_metadata.py`

Busca tablas o columnas por patrón en todos los esquemas.

```python
#!/usr/bin/env python3
"""
Search for tables or columns across all schemas using metadata.
Usage: python scripts/search_metadata.py <pattern> [--type table|column] [--env dev|ci]
"""
import argparse
import sys
import os
from rich.console import Console
from rich.table import Table
from rich import box

# Add the parent directory to sys.path to allow importing from utils
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils.db_connect import db_connection, print_env_banner
from utils.constants import EXCLUDED_SCHEMAS

console = Console()

def search_tables(env: str, pattern: str):
    """Search for tables matching the pattern across all schemas."""
    with db_connection(env) as conn:
        cursor = conn.cursor()
        placeholders = ', '.join(['%s'] * len(EXCLUDED_SCHEMAS))
        query = f"""
            SELECT TABLE_SCHEMA, TABLE_NAME, TABLE_TYPE, TABLE_ROWS
            FROM information_schema.TABLES
            WHERE TABLE_NAME LIKE %s
            AND TABLE_SCHEMA NOT IN ({placeholders})
            ORDER BY TABLE_SCHEMA, TABLE_NAME
        """
        cursor.execute(query, (f"%{pattern}%", *EXCLUDED_SCHEMAS))
        return cursor.fetchall()

def search_columns(env: str, pattern: str):
    """Search for columns matching the pattern across all tables and schemas."""
    with db_connection(env) as conn:
        cursor = conn.cursor()
        placeholders = ', '.join(['%s'] * len(EXCLUDED_SCHEMAS))
        query = f"""
            SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME, DATA_TYPE
            FROM information_schema.COLUMNS
            WHERE COLUMN_NAME LIKE %s
            AND TABLE_SCHEMA NOT IN ({placeholders})
            ORDER BY TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME
        """
        cursor.execute(query, (f"%{pattern}%", *EXCLUDED_SCHEMAS))
        return cursor.fetchall()

def display_table_results(results: list, pattern: str, env: str):
    """Display table search results."""
    if not results:
        console.print(f"[yellow]No tables found matching '[bold]{pattern}[/bold]'.[/yellow]")
        return

    table = Table(
        title=f"Table Search Results for '{pattern}' ({env})",
        box=box.MINIMAL_DOUBLE_HEAD,
        header_style="bold cyan"
    )
    table.add_column("Schema", style="green")
    table.add_column("Table Name", style="yellow")
    table.add_column("Type", style="dim")
    table.add_column("Approx Rows", justify="right", style="blue")

    for row in results:
        table.add_row(str(row[0]), str(row[1]), str(row[2]), str(row[3]))

    console.print(table)
    console.print(f"\n[dim]Total: {len(results)} tables(s)[/dim]")

def display_column_results(results: list, pattern: str, env: str):
    """Display column search results."""
    if not results:
        console.print(f"[yellow]No columns found matching '[bold]{pattern}[/bold]'.[/yellow]")
        return

    table = Table(
        title=f"Column Search Results for '{pattern}' ({env})",
        box=box.MINIMAL_DOUBLE_HEAD,
        header_style="bold magenta"
    )
    table.add_column("Schema", style="green")
    table.add_column("Table", style="yellow")
    table.add_column("Column Name", style="cyan")
    table.add_column("Data Type", style="blue")

    for row in results:
        table.add_row(str(row[0]), str(row[1]), str(row[2]), str(row[3]))

    console.print(table)
    console.print(f"\n[dim]Total: {len(results)} column(s)[/dim]")

def main():
    parser = argparse.ArgumentParser(
        description="Search for tables or columns across all schemas."
    )
    parser.add_argument("pattern", help="Search pattern (LIKE style, e.g., 'user' matches '%user%')")
    parser.add_argument(
        "--type",
        choices=['table', 'column'],
        default='table',
        help="What to search for (default: table)"
    )
    parser.add_argument(
        "--env",
        choices=['dev', 'ci'],
        default='dev',
        help="Database environment (default: dev)"
    )

    args = parser.parse_args()
    print_env_banner(args.env)

    try:
        console.print(f"🔍 Searching for [bold cyan]{args.type}[/bold cyan] matching '[bold]{args.pattern}[/bold]'...")

        if args.type == 'table':
            results = search_tables(args.env, args.pattern)
            display_table_results(results, args.pattern, args.env)
        else:
            results = search_columns(args.env, args.pattern)
            display_column_results(results, args.pattern, args.env)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
```

**Ubicación**: `./scripts/search_metadata.py`

**Uso**:
```bash
# Buscar tablas por patrón
python3 ./scripts/search_metadata.py "customer" --type table --env dev

# Buscar columnas por patrón
python3 ./scripts/search_metadata.py "status" --type column --env dev
```

---

## Ejemplo de Estructura Local

```
your-repo/
├── .env                      # Credenciales (en .gitignore)
├── scripts/
│   ├── __init__.py
│   ├── list_schemas.py
│   ├── list_tables.py
│   ├── describe_table.py
│   ├── query_table.py
│   ├── search_metadata.py
│   └── utils/
│       ├── __init__.py
│       ├── db_connect.py
│       └── constants.py
└── exports/                  # CSV exportados (en .gitignore)
    └── table_name.csv
```

---

## Troubleshooting

Ver `troubleshooting.md` para errores comunes y soluciones.

