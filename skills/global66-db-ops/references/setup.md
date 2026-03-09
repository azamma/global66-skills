# Setup Script Generator

Script Python que genera automáticamente todos los scripts de base de datos desde `scripts-reference.md`.

## Cómo usar

1. Copia el código de abajo a `scripts/setup.py`
2. Ejecuta: `python3 scripts/setup.py`
3. Los scripts se generarán automáticamente en `./scripts/`

## `scripts/setup.py`

```python
#!/usr/bin/env python3
"""
Generate database scripts from references/scripts-reference.md
Extracts Python code blocks and creates individual script files.
"""
import os
import re
from pathlib import Path

def extract_scripts_from_markdown(md_file):
    """Extract Python scripts from Markdown file."""
    with open(md_file, 'r') as f:
        content = f.read()

    # Pattern to match: ### `script_name.py` followed by ```python code block
    pattern = r'### `([^`]+\.py)`\n+```python\n(.*?)\n```'
    matches = re.finditer(pattern, content, re.DOTALL)

    scripts = {}
    for match in matches:
        script_name = match.group(1)
        script_code = match.group(2)
        scripts[script_name] = script_code

    return scripts

def extract_utils_from_markdown(md_file):
    """Extract utility files from Markdown file."""
    with open(md_file, 'r') as f:
        content = f.read()

    # Pattern for utilities section: ## Utilities with ### `utils/name.py`
    utils_pattern = r'## Utilities\n(.*?)(?=## Scripts Principales|$)'
    utils_section = re.search(utils_pattern, content, re.DOTALL)

    if not utils_section:
        return {}

    utils_content = utils_section.group(1)
    pattern = r'### `([^`]+\.py)`\n+```python\n(.*?)\n```'
    matches = re.finditer(pattern, utils_content, re.DOTALL)

    utils = {}
    for match in matches:
        util_name = match.group(1)
        util_code = match.group(2)
        utils[util_name] = util_code

    return utils

def create_scripts(scripts_dict, base_dir='./scripts'):
    """Create script files from dictionary."""
    Path(base_dir).mkdir(exist_ok=True)

    for script_name, script_code in scripts_dict.items():
        script_path = os.path.join(base_dir, script_name)
        os.makedirs(os.path.dirname(script_path), exist_ok=True)

        with open(script_path, 'w') as f:
            f.write(script_code)

        # Make executable
        os.chmod(script_path, 0o755)
        print(f"✅ Created {script_path}")

def create_env_template(base_dir='./scripts'):
    """Create .env template file."""
    env_template = """# Database credentials for Global66
# Copy this to .env and fill in your credentials

DB_DEV_HOST=db-dev-wr.global66.com
DB_DEV_PORT=3306
DB_DEV_USER=your_user
DB_DEV_PASSWORD=your_password
DB_DEV_DATABASE=subscription

DB_CI_HOST=db-ci-wr.global66.com
DB_CI_PORT=3306
DB_CI_USER=your_ci_user
DB_CI_PASSWORD=your_ci_password
DB_CI_DATABASE=subscription
"""

    env_path = os.path.join(base_dir, '.env.example')
    with open(env_path, 'w') as f:
        f.write(env_template)

    os.chmod(env_path, 0o644)
    print(f"✅ Created {env_path}")

def main():
    """Main entry point."""
    print("🔧 Generating database scripts from references/scripts-reference.md...\n")

    # Verify we can find the reference file
    ref_file = 'references/scripts-reference.md'
    if not os.path.exists(ref_file):
        print(f"❌ Error: {ref_file} not found")
        print("   Make sure you're running this script from the repository root")
        return False

    try:
        # Extract utilities
        print("📦 Extracting utilities...")
        utils = extract_utils_from_markdown(ref_file)
        if utils:
            create_scripts(utils)
        else:
            print("   No utilities found")

        # Extract scripts
        print("\n📝 Extracting scripts...")
        scripts = extract_scripts_from_markdown(ref_file)
        if scripts:
            create_scripts(scripts)
        else:
            print("   No scripts found")

        # Create .env template
        print("\n⚙️  Creating environment template...")
        create_env_template()

        # Create __init__.py files
        os.makedirs('./scripts/utils', exist_ok=True)
        Path('./scripts/__init__.py').touch()
        Path('./scripts/utils/__init__.py').touch()
        print("✅ Created __init__.py files")

        print("\n✨ Done! Your scripts are ready.")
        print("\n📋 Next steps:")
        print("   1. Copy .env.example to .env")
        print("   2. Fill in your database credentials in .env")
        print("   3. Run: python3 ./scripts/list_schemas.py --env dev")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
```

## Instrucciones de uso

### 1. Generar scripts automáticamente

```bash
# Desde la raíz de tu repositorio
python3 scripts/setup.py
```

Este comando:
- ✅ Crea carpeta `./scripts/`
- ✅ Extrae todos los scripts de `references/scripts-reference.md`
- ✅ Extrae utilities (`db_connect.py`, `constants.py`)
- ✅ Crea `.env.example` con template de credenciales
- ✅ Genera archivos `__init__.py` necesarios

### 2. Configurar credenciales

```bash
# Copiar template
cp scripts/.env.example .env

# Editar con tus credenciales
nano .env
```

### 3. Usar los scripts

```bash
# Listar esquemas
python3 ./scripts/list_schemas.py --env dev

# Listar tablas
python3 ./scripts/list_tables.py subscription --env dev

# Describir tabla
python3 ./scripts/describe_table.py subscription users --env dev

# Consultar datos
python3 ./scripts/query_table.py subscription users --limit 20 --env dev

# Buscar por patrón
python3 ./scripts/search_metadata.py "customer" --type table --env dev
```

## .gitignore

Asegúrate de agregar esto a tu `.gitignore`:

```gitignore
# Database credentials
.env
.env.local

# Exports
exports/

# Python cache
scripts/__pycache__/
scripts/utils/__pycache__/
*.pyc
```

## Solución de problemas

**"ModuleNotFoundError: No module named 'mysql.connector'"**
```bash
pip install mysql-connector-python
pip install python-dotenv
pip install rich
```

**"FileNotFoundError: references/scripts-reference.md"**
- Asegúrate de ejecutar el script desde la raíz del repositorio
- Verifica que exista el archivo `references/scripts-reference.md`

**"No tienes permiso para escribir en ./scripts/"**
- Verifica permisos: `chmod 755 ./scripts`

