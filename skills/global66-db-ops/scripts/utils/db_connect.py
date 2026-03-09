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
