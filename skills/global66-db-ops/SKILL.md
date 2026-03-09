---
name: global66-db-ops
description: >
  Herramientas para interactuar con bases de datos MySQL de Global66 (CI/DEV). Permite explorar esquemas, listar tablas, ver estructuras y consultar datos de forma segura utilizando scripts Python.

  Úsalo cuando el usuario necesite:
  - "Dame los últimos registros de la tabla X"
  - "Necesito validar la estructura de la tabla Y después de un cambio Liquibase"
  - "Busca todas las tablas que contengan 'user' en su nombre"
  - "Audita qué cambios se hicieron en la tabla Z"
  - "Exporta datos de la tabla W a CSV"

  También úsalo proactivamente cuando el usuario esté debuggeando problemas de persistencia (excepciones de base de datos, datos faltantes, migraciones fallidas) o validando cambios de esquema.
---

# Global66 Database Operations Skill

Esta skill proporciona un flujo de trabajo estándar para interactuar con las bases de datos de Global66 (entornos CI/DEV), integrando la obtención de credenciales desde el Config Server y la exploración de datos mediante scripts especializados.

## 📍 Scripts Python

Los scripts Python están documentados completamente en `references/scripts-reference.md`.

Para usar los scripts:

1. **Lee `references/scripts-reference.md`** — contiene el código completo de todos los scripts
2. **Copia los scripts a tu repo local:**
   ```bash
   mkdir -p ./scripts/utils
   # Copia el código de scripts-reference.md a estos archivos
   ```
3. **Configura credenciales en `.env`** (ver instrucciones en scripts-reference.md)
4. **Ejecuta desde tu repo:**
   ```bash
   python3 ./scripts/list_schemas.py --env dev
   ```

**IMPORTANTE**:
- ❌ NO uses rutas globales como `/root/.claude/skills/...`
- ❌ NO expongas credenciales en prompts
- ✅ Usa `.env` file para credenciales
- ✅ Copia los scripts a tu carpeta local

## Cuándo usar esta skill

Claude debería usar esta skill cuando:
- El usuario pregunta explícitamente por datos: *"Dame los últimos 20 registros de subscription"*
- El usuario valida cambios de DB: *"Revisa la estructura actual de la tabla customers después del cambio"*
- El usuario busca en metadatos: *"Qué tablas tienen una columna 'status'?"*
- El usuario exporta datos: *"Necesito los datos de la tabla products en CSV"*
- El usuario debuggea: *"¿Por qué esta excepción de ForeignKey? Revisa la tabla users"*

## Protocolo de Operación: Research → Explore → Query

Sigue **estrictamente** este orden de 4 pasos:

### 1️⃣ Obtención de Credenciales (Si no las tienes)

Si el usuario no proporciona credenciales explícitamente:
- Consulta el Config Server según el entorno (`ci` o `dev`):
  ```bash
  curl -s https://lb-{env}.global66.com/config/subscription/{env} | grep -E "datasource|flash-token"
  ```
- Extrae: `username`, `password`, `url` (JDBC), y `host` (desde la URL)
- Configura las variables de entorno para los scripts:
  ```bash
  export DB_{ENV}_HOST=...
  export DB_{ENV}_USER=...
  export DB_{ENV}_PASSWORD=...
  export DB_{ENV}_DATABASE=subscription
  ```

**Importante**: Nunca hardcodees credenciales en el script; úsalas solo como vars de entorno temporales.

### 2️⃣ Exploración de Esquema (Si es desconocido)

Si el usuario no menciona el schema:
- **Guía al usuario** a usar `list_schemas.py` (ver `references/scripts-reference.md`)
- Una vez identificado el schema, guía a usar `list_tables.py`

Si el usuario ya mencionó el schema (ej: "subscription"), salta a paso 3.

### 3️⃣ Análisis de Estructura

Antes de consultar datos:
- **Guía al usuario** a usar `describe_table.py` para ver estructura
- Esto mostrará columnas, tipos, claves primarias e índices
- Si hay relaciones con otras tablas, sugiere describir también esas

### 4️⃣ Consulta de Datos

**Guía al usuario** a usar `query_table.py`:
- Con límite (default 10)
- Con `--limit` personalizado (máx. 1000)
- Con `--export` para CSV

Todos los scripts están documentados en `references/scripts-reference.md` con ejemplos de uso.

## Ejemplos de uso

**Ejemplo 1: Usuario dice "Dame los últimos 20 registros de la tabla users en dev"**

→ Paso 1: Obtener credenciales (si no las tiene)
→ Paso 2: Schema ya conocido → subscription
→ Paso 3: Guiar a usar `describe_table.py subscription users --env dev`
→ Paso 4: Guiar a usar `query_table.py subscription users --limit 20 --env dev`

(Ver `references/scripts-reference.md` para código completo)

**Ejemplo 2: Usuario dice "Busca todas las tablas que tengan 'customer' en su nombre"**

→ Paso 1: Obtener credenciales
→ Paso 2: Guiar a usar `list_schemas.py --env dev` si no conoce esquemas
→ Paso 3: Guiar a usar `search_metadata.py "customer" --type table --env dev`
→ Paso 4: Para cada tabla encontrada, guiar a usar `describe_table.py`

(Ver `references/scripts-reference.md` para código completo)

**Ejemplo 3: Usuario dice "Valida la estructura de la tabla payments después del cambio"**

→ Paso 1: Obtener credenciales
→ Paso 2: Schema conocido → subscription
→ Paso 3: Guiar a usar `describe_table.py subscription payments --env dev`
→ Paso 4: Comparar con esquema esperado o mostrar al usuario

(Ver `references/scripts-reference.md` para código completo)

## Scripts Disponibles

| Script | Ubicación | Uso | Ejemplo |
|--------|-----------|-----|---------|
| `list_schemas.py` | `/root/.claude/skills/global66-db-ops/scripts/` | Listar todos los esquemas | `python3 /root/.claude/skills/global66-db-ops/scripts/list_schemas.py --env dev` |
| `list_tables.py` | `/root/.claude/skills/global66-db-ops/scripts/` | Listar tablas de un schema | `python3 /root/.claude/skills/global66-db-ops/scripts/list_tables.py subscription --env dev` |
| `describe_table.py` | `/root/.claude/skills/global66-db-ops/scripts/` | Ver estructura (columnas, índices, claves) | `python3 /root/.claude/skills/global66-db-ops/scripts/describe_table.py subscription users --env dev` |
| `query_table.py` | `/root/.claude/skills/global66-db-ops/scripts/` | Consultar datos con límite | `python3 /root/.claude/skills/global66-db-ops/scripts/query_table.py subscription users --limit 20 --env dev` |
| `search_metadata.py` | `/root/.claude/skills/global66-db-ops/scripts/` | Buscar tablas/columnas por patrón | `python3 /root/.claude/skills/global66-db-ops/scripts/search_metadata.py "customer" --env dev` |
| `backup_table.py` | `/root/.claude/skills/global66-db-ops/scripts/` | Respaldar tabla a archivo SQL | `python3 /root/.claude/skills/global66-db-ops/scripts/backup_table.py subscription users --env dev` |
| `backup_schema.py` | `/root/.claude/skills/global66-db-ops/scripts/` | Respaldar todo un schema | `python3 /root/.claude/skills/global66-db-ops/scripts/backup_schema.py subscription --env dev` |

## Reglas de Seguridad y Estándares

**Credenciales:**
- ❌ NUNCA hardcodees contraseñas en scripts o comandos
- ✅ Usa siempre variables de entorno: `DB_{ENV}_HOST`, `DB_{ENV}_USER`, etc.
- ✅ Cargan desde `.env` file o terminal (temporal)
- ✅ Limpialas después de usar: `unset DB_*`

**Consultas:**
- ✅ Siempre usa `--limit` (default 10, máx 1000)
- ✅ Usa backticks para escapar nombres: `` `schema`.`table` ``
- ✅ Para consultas grandes, exporta a CSV con `--export`

**Entornos:**
- ✅ Sé **explícito**: `--env dev` o `--env ci`
- ❌ Nunca asumas el entorno
- ✅ Usa colores del banner para confirmación visual (amarillo=dev, rojo=ci)

**Liquibase:**
- Las tablas `DATABASECHANGELOG` y `DATABASECHANGELOGLOCK` están excluidas de listados por defecto
- Pueden consultarse si necesitas auditar migraciones: `query_table.py subscription DATABASECHANGELOG`

## Integración con Flujos de Desarrollo

### Validación de cambios Liquibase

Cuando trabajas con migraciones:
```bash
# 1. Genera YAML
mvn clean compile liquibase:diff -P liquibase -Dissue.name=JIRA-123

# 2. Valida estructura con esta skill
python3 scripts/describe_table.py subscription users --env dev

# 3. Compara el YAML generado con la estructura actual
```

### Debugging de problemas de persistencia

Si ves excepciones tipo `ForeignKeyException` o datos faltantes:
1. Identifica la tabla problemática
2. Usa `describe_table.py` para ver claves foráneas y restricciones
3. Usa `query_table.py` para auditar los datos actuales
4. Busca en `DATABASECHANGELOG` para ver qué cambios se aplicaron

## Errores Comunes

Si algo no funciona, consulta `references/troubleshooting.md` para:
- Errores de conexión (credenciales, host inválido)
- Tabla no encontrada (búsqueda por patrón)
- Performance lenta (limits y índices)
- Problemas de seguridad (PII en CSV, credenciales en historial)
- Integración con Liquibase (validación de cambios)

## Checklist de Seguridad

Antes de cualquier operación:
- ✅ ¿Credenciales en variables de entorno, NO hardcodeadas?
- ✅ ¿Environment correcto (dev/ci)?
- ✅ ¿Usando --limit para evitar saturación?
- ✅ ¿Los datos que exporto contienen PII?
- ✅ ¿Voy a borrar el CSV después de usar?
