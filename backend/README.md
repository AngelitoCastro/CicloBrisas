# Backend de EcoConecta — Persistencia e Infraestructura

Capa de persistencia (PostgreSQL + SQLAlchemy 2 + psycopg 3 + Alembic), datos semilla piloto y composición Docker para el MVP de EcoConecta (Villas de San Pablo).

## Contrato compartido

- `backend/app/db.py`: expone `Base`, `engine`, `SessionLocal`, `get_database_url()` y `get_db()` para sesiones síncronas SQLAlchemy 2 con `psycopg` 3.
- `backend/app/models.py`: expone `Usuario`, `ReglaPuntos`, `Solicitud`, `HistorialEstado` (además de `MensajeWhatsapp` y `ContenidoEducativo`), con `Usuario.password_hash` (`str`, bcrypt) y `Solicitud.regla_puntos_id` (`FK` nullable a `reglas_puntos.id`).
- Directorio de ejecución: `backend/`, imports `app.*` y punto de entrada API `app.main:app` (implementado por el frente de API).

## Arranque local con Docker

1. Crear `.env` en la raíz del repositorio a partir de `.env.example` y definir al menos `POSTGRES_PASSWORD`, `SECRET_KEY` y `SEED_DEFAULT_PASSWORD`:

```bash
cp .env.example .env
```

2. Levantar PostgreSQL (o la composición completa una vez integrado `app/main.py`):

```bash
docker compose up -d db
# Con app/main.py integrado:
docker compose up --build -d
```

3. Ejecutar migraciones Alembic y cargar la semilla repetible (puedes ejecutarla dos veces sin duplicar registros):

```bash
docker compose run --rm backend alembic upgrade head
docker compose run --rm backend python -m app.seed
# También compatible con:
docker compose run --rm backend python app/seed.py
```

## Pruebas de persistencia (migraciones y semilla doble)

Las pruebas verifican reversibilidad de migraciones (`downgrade base` → `upgrade head`), carga repetida de semilla sin duplicados y restricciones SQL (`RN-02`, `RN-03`, `RN-05`, índice único parcial de reglas activas):

```bash
docker compose run --rm backend pytest tests/test_persistence.py -v
```

Si ejecutas fuera de Docker desde `backend/` con un entorno virtual que tenga `requirements.txt` instalado y PostgreSQL accesible en `DATABASE_URL`:

```bash
cd backend
alembic upgrade head
SEED_DEFAULT_PASSWORD=<clave-local> python -m app.seed
SEED_DEFAULT_PASSWORD=<clave-local> python -m app.seed
pytest tests/test_persistence.py -v
```
