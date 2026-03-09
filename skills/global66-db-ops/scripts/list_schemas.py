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
