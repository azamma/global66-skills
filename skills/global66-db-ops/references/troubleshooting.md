# Database Operations Troubleshooting

Guía de errores comunes y cómo resolverlos.

## Errores de Conexión

### "Missing required configuration: host, user, password"

**Síntoma**: Scripts fallan con este error cuando se ejecutan.

**Causa**: Variables de entorno no están configuradas.

**Solución**:
```bash
# Verifica que las variables estén establecidas
env | grep DB_

# Si faltan, configúralas manualmente
export DB_DEV_HOST=db-dev-wr.global66.com
export DB_DEV_USER=tu_usuario
export DB_DEV_PASSWORD=tu_password
export DB_DEV_DATABASE=subscription

# O crea un archivo .env
cat > .env << EOF
DB_DEV_HOST=db-dev-wr.global66.com
DB_DEV_USER=tu_usuario
DB_DEV_PASSWORD=tu_password
DB_DEV_DATABASE=subscription
EOF
```

### "Failed to connect to dev environment: Access denied for user"

**Síntoma**: Usuario/contraseña rechazados.

**Causa**: Credenciales inválidas o token expirado.

**Solución**:
1. Verifica credenciales en Config Server: `curl https://lb-dev.global66.com/config/subscription/dev`
2. Actualiza las variables de entorno con credenciales nuevas
3. Prueba conexión: `python3 scripts/list_schemas.py --env dev`

### "Failed to connect to dev environment: Unknown database host"

**Síntoma**: No encuentra el host.

**Causa**: Host incorrecto o sin acceso de red.

**Solución**:
1. Verifica el host en Config Server
2. Intenta ping: `ping db-dev-wr.global66.com`
3. Si no responde, contacta a DevOps

## Errores de Script

### "Unknown database: subscription"

**Síntoma**: La tabla no existe en el schema esperado.

**Causa**: El schema por defecto no es `subscription`, o la tabla realmente no existe.

**Solución**:
```bash
# Primero lista todos los schemas
python3 scripts/list_schemas.py --env dev

# Luego lista tablas del schema correcto
python3 scripts/list_tables.py payments --env dev  # Ejemplo: "payments" es otro schema

# Describe la tabla en el schema correcto
python3 scripts/describe_table.py payments transactions --env dev
```

### "Table '....' doesn't exist"

**Síntoma**: La tabla que buscas no existe.

**Causa**: Tabla eliminada, nombre erróneo, o en otro schema.

**Solución**:
```bash
# Busca por patrón
python3 scripts/search_metadata.py "transact" --env dev

# O lista todas las tablas del schema
python3 scripts/list_tables.py subscription --env dev
```

### "Syntax error near ..."

**Síntoma**: Error SQL en describe o query.

**Causa**: Nombres de tabla/columna con caracteres especiales mal escapados.

**Solución**: Los scripts usan backticks automáticamente (`` ` ``), pero si ves este error:
1. Verifica el nombre exacto de la tabla
2. Si tiene espacios o caracteres especiales, los backticks deberían manejarlos
3. Reporta el error con el nombre exacto de la tabla

## Problemas de Seguridad

### Credenciales guardadas en historial de bash

**Síntoma**: Las credenciales se ven en `history` o en comandos mostrados.

**Causa**: Las variables de entorno se imprimieron en pantalla o logs.

**Solución**:
```bash
# Limpia las variables
unset DB_DEV_HOST DB_DEV_USER DB_DEV_PASSWORD DB_DEV_DATABASE DB_CI_HOST DB_CI_USER DB_CI_PASSWORD DB_CI_DATABASE

# O usa un archivo .env y no lo versionés (añade a .gitignore)
echo ".env" >> .gitignore

# Para limpiar historial si es crítico
history -c  # Borra historial de la sesión actual
```

### "Exported CSV contiene datos sensibles"

**Síntoma**: El archivo CSV exportado tiene información personal (emails, teléfonos).

**Causa**: La tabla contiene PII (Personally Identifiable Information).

**Solución**:
1. **Nunca compartas el CSV con terceros sin autorización**
2. Si necesitas datos desensibilizados, crea una consulta SQL personalizada que hashe o oculte PII
3. Borra el archivo CSV después de usar: `rm exports/transactions_recent.csv`
4. Considera si realmente necesitas exportar o si puedes responder la pregunta con `describe_table`

## Problemas de Performance

### "Query takes too long" o "Connection timeout"

**Síntoma**: `query_table.py` cuelga o tarda mucho.

**Causa**: Tablas muy grandes, o query sin índice.

**Solución**:
```bash
# Reduce el limit
python3 scripts/query_table.py subscription transactions --limit 5 --env dev

# Primero describe para ver índices
python3 scripts/describe_table.py subscription transactions --env dev

# Si la tabla es muy grande, considera:
# - Usar --limit 1 solo para ver estructura
# - Buscar por rango de fecha si existe columna created_at
# - Consultar directamente con SQL personalizado (si necesitas)
```

### "Export to CSV is very slow"

**Síntoma**: El --export tarda mucho tiempo.

**Causa**: Escribiendo archivo grande a disco.

**Solución**:
```bash
# Reduce el limit
python3 scripts/query_table.py subscription large_table --limit 100 --export --env dev

# O executa sin export primero, visualmente verifica, luego exporta si necesita
```

## Problemas de Liquidbase Integration

### "YAML change es inválido según describe_table"

**Síntoma**: Ejecutaste un YAML de Liquibase pero describe_table muestra algo diferente.

**Causa**: El YAML no se aplicó correctamente, o hay error de tipo de dato.

**Solución**:
```bash
# 1. Describe la tabla actual
python3 scripts/describe_table.py subscription users --env dev

# 2. Compara con lo que esperabas en el YAML
# 3. Si hay diferencias, revisa:
#    - DATABASECHANGELOG para ver si el changeset se ejecutó
python3 scripts/query_table.py subscription DATABASECHANGELOG \
  --limit 20 --env dev

# 4. Si el changeset está en DATABASECHANGELOG pero describe no refleja los cambios:
#    - Puede haber error silencioso o rollback parcial
#    - Contacta a DevOps
```

### "Can't run Liquibase diff, how do I validate?"

**Síntoma**: Quieres validar que tu YAML es correcto antes de aplicarlo.

**Causa**: No tienes el ambiente de Maven configurado.

**Solución**:
1. Describe la tabla ANTES del cambio: `describe_table.py subscription users --env dev`
2. Anota las columnas y tipos actuales
3. En tu YAML, especifica los cambios esperados
4. Una vez aplicado, vuelve a hacer `describe_table` y verifica que coincida
5. Revisa DATABASECHANGELOG para confirmar ejecución

## Problemas de Ambiente

### "¿Estoy en dev o ci?"

**Síntoma**: No estás seguro cuál environment usar.

**Causa**: Falta de claridad en la solicitud del usuario.

**Solución**:
- **dev**: Para testing, debugging, entorno de desarrollo
- **ci**: Para staging/pre-producción (⚠️ más datos reales)
- **NUNCA**: Conectes a producción vía estos scripts

**Siempre pregunta** si no está claro:
```
"¿Debería conectarme a 'dev' o 'ci'?
 - 'dev' es para testing (menos datos)
 - 'ci' es para staging (datos más reales)

¿Cuál necesitas?"
```

---

## Checklist de Seguridad Antes de Exportar

1. ✅ ¿Estoy en el environment correcto? (dev/ci)
2. ✅ ¿Necesito realmente exportar o puedo responder con describe?
3. ✅ ¿Los datos contienen PII (emails, teléfonos, SSN)?
4. ✅ ¿Tengo autorización para ver estos datos?
5. ✅ ¿Voy a compartir el CSV? Si sí, ¿con quién y con qué autorización?
6. ✅ Después de terminar, ¿voy a borrar el CSV? (`rm exports/...`)
7. ✅ ¿Configuré las variables de entorno de forma segura? (no hardcodeadas)

