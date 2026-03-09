#!/usr/bin/env python3
"""
Backup a single table to a CSV file.
Usage: python scripts/backup_table.py <schema> <table> [--env dev|ci] [--output-dir <dir>]
"""
import argparse
import sys
import os
import csv
from rich.console import Console

# Add the parent directory to sys.path to allow importing from utils
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils.db_connect import db_connection, print_env_banner

console = Console()

def export_table_to_csv(env: str, schema: str, table_name: str, output_dir: str):
    """Export a single table to CSV."""
    with db_connection(env) as conn:
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM `{schema}`.`{table_name}`")
        
        column_names = [i[0] for i in cursor.description]
        rows = cursor.fetchall()
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        file_path = os.path.join(output_dir, f"{table_name}.csv")
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f, quoting=csv.QUOTE_NONNUMERIC)
            writer.writerow(column_names)
            writer.writerows(rows)
            
        return len(rows), file_path

def main():
    parser = argparse.ArgumentParser(
        description="Backup a single table to a CSV file."
    )
    parser.add_argument("schema", help="Schema name")
    parser.add_argument("table", help="Table name")
    parser.add_argument(
        "--env",
        choices=['dev', 'ci'],
        default='dev',
        help="Database environment (default: dev)"
    )
    parser.add_argument(
        "--output-dir",
        help="Directory to save the CSV file (default: backups/<schema>_<env>)"
    )

    args = parser.parse_args()
    print_env_banner(args.env)

    try:
        # Setup output directory
        output_dir = args.output_dir or f"backups/{args.schema}_{args.env}"
        
        console.print(f"🚀 Starting backup of [bold cyan]{args.schema}.{args.table}[/bold cyan]...")
        
        row_count, file_path = export_table_to_csv(args.env, args.schema, args.table, output_dir)
            
        console.print(f"\n✅ Backup of [bold green]{args.table}[/bold green] completed successfully!")
        console.print(f"📄 Saved to: [bold green]{file_path}[/bold green]")
        console.print(f"[dim]Total: {row_count} rows exported.[/dim]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
