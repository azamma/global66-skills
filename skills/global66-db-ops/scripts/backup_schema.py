#!/usr/bin/env python3
"""
Backup an entire schema to CSV files.
Usage: python scripts/backup_schema.py <schema> [--env dev|ci] [--output-dir <dir>]
"""
import argparse
import sys
import os
import csv
from rich.console import Console
from rich.progress import track

# Add the parent directory to sys.path to allow importing from utils
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils.db_connect import db_connection, print_env_banner
from utils.constants import EXCLUDED_TABLES

console = Console()

def get_tables(env: str, schema: str):
    """List all tables in the specified schema."""
    with db_connection(env) as conn:
        cursor = conn.cursor()
        cursor.execute(f"SHOW TABLES FROM `{schema}`")
        tables = [row[0] for row in cursor.fetchall() if row[0] not in EXCLUDED_TABLES]
        return tables

def export_table_to_csv(env: str, schema: str, table_name: str, output_dir: str):
    """Export a single table to CSV."""
    with db_connection(env) as conn:
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM `{schema}`.`{table_name}`")
        
        column_names = [i[0] for i in cursor.description]
        rows = cursor.fetchall()
        
        file_path = os.path.join(output_dir, f"{table_name}.csv")
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f, quoting=csv.QUOTE_NONNUMERIC)
            writer.writerow(column_names)
            writer.writerows(rows)
            
    return len(rows)

def main():
    parser = argparse.ArgumentParser(
        description="Backup an entire schema to CSV files."
    )
    parser.add_argument("schema", help="Schema name to backup")
    parser.add_argument(
        "--env",
        choices=['dev', 'ci'],
        default='dev',
        help="Database environment (default: dev)"
    )
    parser.add_argument(
        "--output-dir",
        help="Directory to save the CSV files (default: backups/<schema>_<env>)"
    )

    args = parser.parse_args()
    print_env_banner(args.env)

    try:
        # 1. Get tables
        tables = get_tables(args.env, args.schema)
        if not tables:
            console.print(f"[yellow]No tables found in {args.schema}.[/yellow]")
            return

        # 2. Setup output directory
        output_dir = args.output_dir or f"backups/{args.schema}_{args.env}"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        console.print(f"🚀 Starting backup of [bold cyan]{args.schema}[/bold cyan] schema...")
        
        # 3. Export each table
        for table in track(tables, description="Exporting tables..."):
            export_table_to_csv(args.env, args.schema, table, output_dir)
            
        console.print(f"\n✅ Backup completed successfully in [bold green]{output_dir}[/bold green]")
        console.print(f"[dim]Total: {len(tables)} tables exported.[/dim]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
