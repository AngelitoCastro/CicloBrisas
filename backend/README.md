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
export DATABASE_URL="$TEST_DATABASE_URL"
export ALLOW_DESTRUCTIVE_DB_TESTS=1
pytest tests -v
```

En Docker, usa una base desechable distinta de la de demostración (las pruebas de persistencia reinician el esquema):

```bash
docker compose exec -T db createdb -U ecoconecta ecoconecta_test
docker compose run --rm backend env \
  DATABASE_URL=postgresql+psycopg://ecoconecta:<clave>@db:5432/ecoconecta_test \
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
- PostgreSQL: migraciones reversibles, semilla idempotente, restricciones SQL y cierre concurrente con una sola acreditación.

## Semilla piloto

`python -m app.seed` carga 10 cuentas ficticias (todos los roles), 4 reglas de puntos y 4 contenidos educativos. Es idempotente: ejecutarla dos veces no duplica registros ni borra puntos acumulados. Los teléfonos y roles están documentados en [API_CONTRATO.md](API_CONTRATO.md). La contraseña se toma de `SEED_DEFAULT_PASSWORD` o de las variables `SEED_PASSWORD_*`; no se guarda en Git.
