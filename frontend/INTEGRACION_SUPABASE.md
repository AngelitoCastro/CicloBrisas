# Integración de Supabase

La base de datos del proyecto es PostgreSQL alojado en Supabase. El backend FastAPI sigue siendo el dueño de la autenticación JWT, los permisos por rol, las reglas de puntos, las transiciones, el historial y la privacidad de los datos. Se conecta con SQLAlchemy 2 y psycopg 3 mediante `DATABASE_URL`, usando el pooler compartido de Supabase en modo sesión (puerto `5432`).

## Esquema y migraciones

El esquema de referencia vive en Alembic:

- `usuarios`
- `reglas_puntos`
- `solicitudes`
- `historial_estados`
- `mensajes_whatsapp`
- `contenidos_educativos`

Los nombres en inglés del plan inicial (`profiles`, `requests`, `weighings`, etc.) quedan reemplazados por ese esquema. Para alinear una base remota:

```bash
cd backend
python -m alembic current
python -m alembic upgrade head
python -m app.seed
```

Si la base ya contiene tablas creadas fuera de Alembic, no se deben borrar: se compara `alembic current` con el esquema real y se prepara una revisión de reconciliación.

## Frontend

El frontend v2 continúa siendo un prototipo con persistencia en `localStorage`. La integración prevista es consumir la API del backend con `VITE_API_URL`, no hablar directamente con PostgREST mientras FastAPI sea la autoridad de reglas y permisos.

Nunca colocar claves `service_role` ni secretos en el navegador. Si en el futuro se expone Supabase al frontend, habilitar RLS en todas las tablas del esquema `public`, conceder permisos solo a los roles necesarios y verificar las políticas con el equipo.

## WhatsApp e IA

El webhook entrante está en el backend en `POST /api/webhooks/whatsapp`, valida `X-Twilio-Signature`, deduplica por `MessageSid` y usa Twilio para los mensajes salientes. La clasificación de intenciones, visión y transcripción usa OpenAI o Azure OpenAI según `IA_PROVEEDOR`. Esta implementación no usa Meta ni Edge Functions.

La autorización, asignación y programación siguen siendo decisiones humanas. El asistente solo propone intención y campos; no asigna recolectores, horarios ni puntos.

## Verificación

Antes de dar por terminada la integración se debe comprobar:

1. Conexión a Supabase con `SELECT 1` y `alembic current`.
2. Migraciones aplicadas sin borrar esquemas existentes.
3. Semilla cargada sin duplicar usuarios ni reglas.
4. Pruebas HTTP y de webhook en verde.
5. Pruebas destructivas aisladas en una base desechable mediante `TEST_DATABASE_URL` y `ALLOW_DESTRUCTIVE_DB_TESTS=1`.
