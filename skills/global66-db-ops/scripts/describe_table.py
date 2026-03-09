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
