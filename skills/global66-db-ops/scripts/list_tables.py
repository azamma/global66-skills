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
