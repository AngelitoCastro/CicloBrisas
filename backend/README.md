# Backend de EcoConecta — API, persistencia e infraestructura

API FastAPI del MVP de EcoConecta (Villas de San Pablo): autenticación JWT, permisos por rol y propiedad, solicitudes orgánicas/reciclables, programación humana, historial auditable, cierre transaccional con puntos parametrizables y administración de reglas y cuentas piloto. Persistencia con PostgreSQL, SQLAlchemy 2, psycopg 3, Alembic y datos semilla.

El contrato de peticiones, respuestas, errores y uso compartido con WhatsApp está en [API_CONTRATO.md](API_CONTRATO.md). Swagger se sirve en `http://localhost:8000/docs`.

## Contrato compartido

- `app/db.py`: expone `Base`, `engine`, `SessionLocal`, `get_database_url()` y `get_db()` para sesiones síncronas SQLAlchemy 2 con `psycopg` 3.
- `app/models.py`: expone `Usuario`, `ReglaPuntos`, `Solicitud`, `HistorialEstado` (además de `MensajeWhatsapp` y `ContenidoEducativo`), con `Usuario.password_hash` (`str`, bcrypt) y `Solicitud.regla_puntos_id` (FK nullable a `reglas_puntos.id`).
- `app/main.py`: aplicación `app.main:app`; routers en `app/routers/`, servicios de dominio en `app/services/`.
- Directorio de ejecución: `backend/`; imports `app.*`.

## Arranque local con Docker

1. Crear `.env` en la raíz del repositorio a partir de `.env.example` y definir al menos `POSTGRES_PASSWORD`, `SECRET_KEY` (mínimo 32 caracteres) y `SEED_DEFAULT_PASSWORD`:

```bash
cp .env.example .env
```

2. Levantar PostgreSQL y la API:

```bash
docker compose up --build -d
```

3. Aplicar la migración y cargar la semilla repetible:

```bash
docker compose run --rm backend alembic upgrade head
docker compose run --rm backend python -m app.seed
# También compatible con:
docker compose run --rm backend python app/seed.py
```

4. Comprobar la API:

```bash
curl http://localhost:8000/health
# Documentación interactiva:
# http://localhost:8000/docs
```

La API no arranca si `SECRET_KEY` falta o tiene menos de 32 caracteres. No subas `.env` ni secretos al repositorio.

## Supabase como base de datos

La API no cambia de framework: Supabase provee PostgreSQL. Define `DATABASE_URL` en la raíz `.env` con la cadena del **pooler compartido** de Supabase en modo sesión (puerto `5432`). `app/db.py` normaliza `postgres://` o `postgresql://` a `postgresql+psycopg://`; codifica los caracteres especiales del password en la URL.

```bash
cd backend
python -m alembic current
python -m alembic upgrade head
python -m app.seed
```

Si la base remota ya tiene tablas creadas fuera de Alembic, no ejecutes `downgrade`: compara `alembic current` con el esquema real y prepara una revisión de reconciliación. Las pruebas destructivas exigen `TEST_DATABASE_URL` y `ALLOW_DESTRUCTIVE_DB_TESTS=1`; nunca usan `DATABASE_URL`.

## Endpoints principales

| Método y ruta | Uso |
| --- | --- |
| `POST /api/auth/login` | Login por teléfono y contraseña; devuelve JWT. |
| `GET /api/auth/me` | Cuenta autenticada y puntos acumulados. |
| `POST /api/solicitudes` | Alta de hogar o unidad productiva (RN-01). |
| `GET /api/solicitudes` | Listado filtrado y aislado por rol/propiedad. |
| `GET /api/solicitudes/{id}` / `.../historial` | Detalle e historial auditable (RN-04, RN-07). |
| `POST /api/solicitudes/{id}/revisar` | `RECIBIDA → EN_REVISION`. |
| `POST /api/solicitudes/{id}/asignar` | Asigna recolector compatible (RN-03). |
| `PATCH /api/solicitudes/{id}/programar` | Día, hora y recolector (RN-02). |
| `POST /api/solicitudes/{id}/cerrar` | Cierre con peso y puntos en una transacción (RN-05/RN-06). |
| `POST /api/solicitudes/{id}/cancelar` | Cancelación sin puntos. |
| `GET /api/reglas-puntos` | Reglas activas visibles para usuarios autenticados. |
| `GET/POST/PATCH /api/admin/reglas-puntos` | Administración de reglas (solo ADMIN). |
| `GET /api/admin/usuarios` | Listado administrativo de cuentas. |
| `PATCH /api/admin/usuarios/{id}/piloto` | Etiqueta piloto FSD (RN-08, solo ADMIN). |
| `POST /api/webhooks/whatsapp` | Mensajes entrantes firmados por Twilio WhatsApp. |

Detalle completo, ejemplos JSON, matriz de permisos, transiciones y errores: [API_CONTRATO.md](API_CONTRATO.md).

## Comportamiento crítico

- **RN-01:** `ORGANICO` se atiende en la bandeja de `COORD_HUERTEROS`; `RECICLABLE` en la de `COORD_RECICLADORES`.
- **RN-02/RN-03:** solo el coordinador humano del flujo programa; se exigen fecha, hora y recolector compatible, y se registran coordinador y recolector.
- **RN-04:** cada transición inserta una fila en `historial_estados` con actor, estados y fecha.
- **RN-05/RN-06:** los puntos solo se acreditan al cerrar una solicitud `PROGRAMADA`; se lee la regla activa por flujo/tipo de generador y se guarda `regla_puntos_id` y la fórmula en el historial. La fila de la solicitud, del solicitante y de la regla se bloquean; dos cierres concurrentes acreditan una sola vez.
- **RN-07:** teléfono y dirección solo se devuelven al propietario, coordinador del flujo, recolector asignado o administrador. Las rutas además bloquean solicitudes ajenas con 404.
- **RN-08:** `es_piloto` es una etiqueta de población piloto; no restringe el acceso.

## Pruebas

Pruebas HTTP con SQLite aislado (no requieren PostgreSQL):

```bash
cd backend
pytest tests -v
```

Pruebas de persistencia y concurrencia contra PostgreSQL 16 desechable:

```bash
# Base de datos de prueba, nunca una base con datos reales
export TEST_DATABASE_URL=postgresql+psycopg://ecoconecta:clave@localhost:5432/ecoconecta_test
export ALLOW_DESTRUCTIVE_DB_TESTS=1
pytest tests -v
```

`DATABASE_URL` no se sobrescribe: puede apuntar a la base de la aplicación (incluido Supabase) y las pruebas destructivas no la tocarán.

En Docker, usa una base desechable distinta de la de demostración (las pruebas de persistencia reinician el esquema):

```bash
docker compose exec -T db createdb -U ecoconecta ecoconecta_test
docker compose run --rm backend env \
  TEST_DATABASE_URL=postgresql+psycopg://ecoconecta:<clave>@db:5432/ecoconecta_test \
  ALLOW_DESTRUCTIVE_DB_TESTS=1 \
  pytest tests -v
```

Nunca apuntes `DATABASE_URL` de las pruebas a una base con datos reales o de demostración.

Cobertura verificada en esta entrega:

- Login correcto/incorrecto, cuenta inactiva, token expirado/inválido/ausente y hash bcrypt.
- Alta y enrutamiento por flujo, aislamiento entre coordinadores, propiedad y recolector asignado.
- Programación incompleta, fecha pasada, recolector incompatible, reprogramación y transiciones.
- Cierre con fórmula parametrizable, historial, actualización de puntos, doble cierre y cierre sin regla activa.
- Administración de reglas (reemplazo de la activa), validaciones y modo piloto.
- Privacidad del serializador y contrato OpenAPI.
- WhatsApp con Twilio: firma y cuenta, payloads form, estados ignorados, texto/foto/audio, registro de número nuevo, flujo ambiguo, dedupe, notificación al programar y cierre idempotente con proveedores simulados.
- IA: chat, visión y transcripción con dobles de `httpx`, en modo OpenAI y Azure OpenAI (endpoint clásico por deployment y endpoint v1).
- PostgreSQL: migraciones reversibles, semilla idempotente, restricciones SQL y cierre concurrente con una sola acreditación.

## Conexión de Twilio y proveedor de IA

1. Completar `.env` con `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_NUMBER` y, si se usan plantillas, `TWILIO_CONTENT_SID`.
2. En Twilio Console, configurar el webhook entrante del remitente de WhatsApp con `POST https://<host>/api/webhooks/whatsapp`. La URL debe ser HTTPS y pública; la firma se valida contra la URL exacta y todos los parámetros del formulario.
3. Definir `WEBHOOK_PUBLIC_URL` con esa misma URL si el backend corre detrás de proxy o túnel y `request.url` no coincide con la URL pública. Si se deja vacía, se reconstruye con `X-Forwarded-Proto`/`X-Forwarded-Host`.
4. Si se usa el sandbox, enviar el código `join <palabra>` al número sandbox antes de probar con un teléfono personal.
5. IA por defecto: dejar `IA_PROVEEDOR=openai` y completar `OPENAI_API_KEY`. `OPENAI_MODEL=gpt-4o-mini` atiende texto e imágenes; `OPENAI_TRANSCRIPTION_MODEL=gpt-transcribe` atiende notas de voz.
6. Azure OpenAI: poner `IA_PROVEEDOR=azure` y completar `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_CHAT_DEPLOYMENT` y `AZURE_OPENAI_AUDIO_DEPLOYMENT`. El deployment es el nombre elegido al desplegar el modelo, no `gpt-4o-mini`.
7. Modo Azure: con `AZURE_OPENAI_API_MODE=classic` se llama a `/openai/deployments/<deployment>/chat/completions?api-version=<versión>`; con `v1` o un endpoint terminado en `/openai/v1` se llama a `/openai/v1/chat/completions` y el deployment viaja en `model`. La autenticación usa la cabecera `api-key` y la versión por defecto es `2024-10-21`.
8. Reiniciar el backend para que `obtener_config()` lea las nuevas variables. No se requiere migración: el dedupe reutiliza `wa_message_id` con el `MessageSid` de Twilio.

Fuentes oficiales consultadas: [chat completions clásico](https://learn.microsoft.com/en-us/azure/ai-services/openai/reference) y [API v1 de Foundry Models](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/latest).

## Semilla piloto

`python -m app.seed` carga 10 cuentas ficticias (todos los roles), 4 reglas de puntos y 4 contenidos educativos. Es idempotente: ejecutarla dos veces no duplica registros ni borra puntos acumulados. Los teléfonos y roles están documentados en [API_CONTRATO.md](API_CONTRATO.md). La contraseña se toma de `SEED_DEFAULT_PASSWORD` o de las variables `SEED_PASSWORD_*`; no se guarda en Git.

### Avisos de programación y cierre

Aplicar `alembic upgrade head` antes de arrancar esta versión de la API. Ejecutar el servicio Compose `avisos` junto con `backend`, o iniciar `python -m app.whatsapp.despacho` como proceso persistente desde `backend/` con el mismo entorno que la API. Cada fila de `avisos_whatsapp` corresponde a una transición y un destinatario. El historial anterior permanece en `mensajes_whatsapp`.

Configurar `WEBHOOK_PUBLIC_URL` con la URL HTTPS completa del webhook entrante, terminada en `/api/webhooks/whatsapp`. El proxy debe enrutar también `POST /api/webhooks/whatsapp/estado/{intento}`. El worker pasa esa URL a Twilio por mensaje. Las cuatro variables opcionales `TWILIO_CONTENT_SID_PROGRAMADA_RECOLECTOR`, `TWILIO_CONTENT_SID_PROGRAMADA_SOLICITANTE`, `TWILIO_CONTENT_SID_RECOLECTADA_RECOLECTOR` y `TWILIO_CONTENT_SID_RECOLECTADA_SOLICITANTE` seleccionan plantillas aprobadas con una variable de texto (1). Sin ellas se usa la plantilla genérica configurada con una variable, o texto libre en una conversación habilitada. Configurar y verificar las plantillas antes del piloto.

En el detalle del coordinador, «Seguimiento y avisos» consulta `GET /api/solicitudes/{id}/avisos`. «Reintentar aviso» llama a `POST /api/solicitudes/{id}/avisos/{aviso_id}/reintentar`. Un fallo definitivo admite un reintento individual mientras la transición siga vigente. ENVIADO corresponde al envío por el proveedor, ENTREGADO y LEIDO a callbacks firmados. CONCILIAR indica que el proceso reclamó el aviso y aún se desconoce el resultado. Consultar los registros de Twilio antes de cualquier intervención manual; los callbacks firmados pueden completar ese estado. Vigilar el número de PENDIENTE, CONCILIAR y FALLIDO y revisar el código de Twilio de los fallos nuevos.

Para el piloto, usar dos números de prueba autorizados y un remitente de WhatsApp habilitado. Programar, verificar ambos avisos, responder `LISTO ECO-AAAA-NNNNNN 8` desde el recolector y revisar las dos confirmaciones y la única acreditación. Repetir con un destinatario de prueba no habilitado para comprobar el fallo aislado y el reintento tras corregir su configuración.
