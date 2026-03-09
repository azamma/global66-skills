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
