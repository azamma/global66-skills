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
