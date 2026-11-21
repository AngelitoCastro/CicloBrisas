# Contrato de API — EcoConecta (MVP)

Documento de integración para el portal comunitario, los paneles de coordinación y el webhook de WhatsApp. La fuente ejecutable está en `backend/app/main.py`; Swagger queda disponible en `/docs` y el esquema OpenAPI en `/openapi.json`.

## 1. Base y autenticación

- URL local: `http://localhost:8000`
- Prefijo funcional: `/api`
- Formato: JSON UTF-8.
- Autenticación: `Authorization: Bearer <access_token>` (JWT HS256, PyJWT).
- Contraseñas: hash bcrypt; nunca se devuelven ni se registran.
- Vigencia del token: `ACCESS_TOKEN_EXPIRE_MINUTES` (60 minutos por defecto).
- Zona horaria de negocio: `America/Bogota` (UTC-5 fijo). Las fechas se envían como `YYYY-MM-DD`; las horas como `HH:MM` o `HH:MM:SS`.
- Los valores `NUMERIC` se devuelven como números JSON con dos decimales.

### POST `/api/auth/login`

```json
{
  "telefono": "+573000000108",
  "password": "clave-de-demostracion"
}
```

Respuesta `200`:

```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "expira_en_segundos": 3600,
  "usuario": {
    "id": "0b0d9d6e-6a2f-4f1e-9f7a-1d2e3f4a5b6c",
    "nombre": "Hogar Piloto Familia Demo",
    "telefono": "+573000000108",
    "rol": "HOGAR",
    "direccion": "Carrera Ficticia 12 # 102-15 (Piloto)",
    "sector_manzana": "Manzana B - Piloto FSD",
    "es_piloto": true,
    "puntos_acumulados": 0.0,
    "activo": true,
    "creado_en": "2026-11-20T15:00:00+00:00"
  }
}
```

Errores: `401 NO_AUTENTICADO` (teléfono o contraseña incorrectos; mensaje genérico para no enumerar cuentas), `403 USUARIO_INACTIVO`.

### GET `/api/auth/me`

Devuelve el mismo objeto `usuario`, incluidos los puntos acumulados. Requiere token.

## 2. Forma estable de errores

Todas las rutas propias responden con:

```json
{
  "detail": {
    "codigo": "ESTADO_INVALIDO",
    "mensaje": "Solo se puede cerrar una solicitud PROGRAMADA; estado actual: RECIBIDA."
  }
}
```

Los errores de validación agregan `errores`:

```json
{
  "detail": {
    "codigo": "VALIDACION",
    "mensaje": "La petición contiene datos inválidos.",
    "errores": [
      {"campo": "fecha_programada", "mensaje": "Field required", "tipo": "missing"}
    ]
  }
}
```

Para errores HTTP no funcionales (por ejemplo ruta inexistente) se usa `codigo: "ERROR_HTTP"`. Un error inesperado responde `500 ERROR_INTERNO` sin detalles internos.

Códigos relevantes:

| Código | HTTP | Significado |
| --- | --- | --- |
| `NO_AUTENTICADO` | 401 | Falta token o credenciales incorrectas. |
| `TOKEN_EXPIRADO` / `TOKEN_INVALIDO` | 401 | Vuelve a iniciar sesión. |
| `USUARIO_INACTIVO` | 403 | Cuenta desactivada. |
| `ROL_NO_AUTORIZADO` | 403 | El rol no puede ejecutar la operación. |
| `FLUJO_NO_AUTORIZADO` | 403 | Coordinador de un flujo intenta operar el otro. |
| `NO_ENCONTRADO` | 404 | Recurso inexistente o no visible (privacidad). |
| `VALIDACION` | 422 | Cuerpo/parámetros inválidos. |
| `RECOLECTOR_INCOMPATIBLE` | 422 | El flujo exige HUERTERO o RECICLADOR. |
| `RECOLECTOR_INACTIVO` / `RECOLECTOR_INVALIDO` | 422 | Recolector no utilizable. |
| `FECHA_PROGRAMADA_INVALIDA` | 422 | Fecha en el pasado. |
| `HORA_PROGRAMADA_INVALIDA` | 422 | Hora ya pasada para hoy. |
| `ESTADO_INVALIDO` | 409 | Transición no permitida para el estado actual. |
| `SOLICITUD_YA_CERRADA` | 409 | Cierre repetido; no se acreditaron puntos de nuevo. |
| `REGLA_PUNTOS_NO_DISPONIBLE` | 409 | No hay regla activa para el flujo/tipo de generador. |
| `CIERRE_CONCURRENTE` | 409 | No se pudo completar por concurrencia; reintentar. |
| `CONFLICTO_DATOS` | 409 | Restricción de base de datos. |
| `USUARIO_NO_APLICA_PILOTO` | 422 | Solo aplica a HOGAR y UNIDAD_PRODUCTIVA. |
| `REGLA_ACTIVA_DUPLICADA` | 409 | Ya existe una regla activa para el par. |
| `SIN_CAMBIOS` | 422 | PATCH sin campos efectivos. |

## 3. Solicitudes

### Objeto `SolicitudPublica`

```json
{
  "id": 1,
  "codigo_publico": "ECO-2026-000001",
  "flujo": "ORGANICO",
  "subtipo_material": "Cáscaras y restos de vegetales",
  "cantidad_estimada_kg": 12.5,
  "cantidad_real_kg": 10.0,
  "disponibilidad_usuario": "Lunes a viernes de 8:00 a.m. a 11:00 a.m.",
  "observaciones": "Dejar el balde en la portería.",
  "estado": "PROGRAMADA",
  "solicitante": {
    "id": "0b0d9d6e-...",
    "nombre": "Unidad Productiva Piloto Mercado Verde",
    "rol": "UNIDAD_PRODUCTIVA",
    "telefono": "+573000000107",
    "direccion": "Calle Ficticia 101 # 10-20 (Piloto)",
    "sector_manzana": "Manzana A - Piloto FSD"
  },
  "coordinador": {
    "id": "e5b6...",
    "nombre": "Coordinación Colectivo Huerteros",
    "rol": "COORD_HUERTEROS"
  },
  "recolector": {
    "id": "f7c8...",
    "nombre": "Huertero Campo Uno",
    "rol": "HUERTERO"
  },
  "fecha_programada": "2026-11-21",
  "hora_programada": "09:30",
  "puntos_otorgados": 0.0,
  "regla_puntos_id": null,
  "creado_en": "2026-11-20T15:00:00+00:00",
  "actualizado_en": "2026-11-20T15:10:00+00:00"
}
```

Los campos de contacto se devuelven como `null` si el observador no está autorizado (RN-07). La API igualmente bloquea el acceso completo a solicitudes ajenas.

### POST `/api/solicitudes` — alta

Roles: `HOGAR`, `UNIDAD_PRODUCTIVA`.

```json
{
  "flujo": "ORGANICO",
  "subtipo_material": "Cáscaras y restos de vegetales",
  "cantidad_estimada_kg": 12.5,
  "disponibilidad_usuario": "Lunes a viernes de 8:00 a.m. a 11:00 a.m.",
  "observaciones": "Dejar el balde en la portería."
}
```

`flujo` es obligatorio: `ORGANICO` enruta a `COORD_HUERTEROS` y `RECICLABLE` a `COORD_RECICLADORES` (RN-01). La respuesta es `201` con estado `RECIBIDA`, código público generado y el primer registro del historial. No se acepta `solicitante_id` desde el cliente: se toma del token.

### GET `/api/solicitudes` — listado

Query params:

- `flujo`: `ORGANICO` o `RECICLABLE` (opcional).
- `estado`: uno de los seis estados (opcional).
- `limit`: 1..100, por defecto 50.
- `offset`: desde 0.

Respuesta:

```json
{"items": [], "total": 0, "limit": 50, "offset": 0}
```

Alcance por rol:

| Rol | Ve |
| --- | --- |
| HOGAR / UNIDAD_PRODUCTIVA | Solo sus solicitudes. |
| COORD_HUERTEROS | Solo flujo `ORGANICO`; pedir `flujo=RECICLABLE` responde 403. |
| COORD_RECICLADORES | Solo flujo `RECICLABLE`. |
| HUERTERO / RECICLADOR | Solo solicitudes asignadas a su cuenta. |
| ADMIN | Todas; puede filtrar por flujo y estado. |

### GET `/api/solicitudes/{id}` y `.../historial`

Mismo alcance que el listado. El historial se ordena cronológicamente y devuelve:

```json
[
  {
    "id": 1,
    "estado_anterior": null,
    "estado_nuevo": "RECIBIDA",
    "actor": {"id": "...", "nombre": "...", "rol": "UNIDAD_PRODUCTIVA"},
    "nota_operativa": "Solicitud creada para el flujo ORGANICO.",
    "fecha_cambio": "2026-11-20T15:00:00+00:00"
  }
]
```

### POST `/api/solicitudes/{id}/revisar`

Solo el coordinador del flujo. Pasa `RECIBIDA → EN_REVISION`.

```json
{"nota_operativa": "Revisada por coordinación"}
```

### POST `/api/solicitudes/{id}/asignar`

Solo el coordinador del flujo. Pasa `RECIBIDA` o `EN_REVISION → ASIGNADA` y registra coordinador y recolector (RN-03).

```json
{"recolector_id": "f7c8...", "nota_operativa": "Asignada a ruta A"}
```

El recolector debe existir, estar activo y tener rol `HUERTERO` para orgánicos o `RECICLADOR` para reciclables; de lo contrario responde `422 RECOLECTOR_INCOMPATIBLE`.

### PATCH `/api/solicitudes/{id}/programar`

Solo el coordinador del flujo. Es la única vía a `PROGRAMADA` (RN-02). Admite `RECIBIDA`, `EN_REVISION`, `ASIGNADA` o una `PROGRAMADA` previa (reprogramación).

```json
{
  "recolector_id": "f7c8...",
  "fecha_programada": "2026-11-21",
  "hora_programada": "09:30",
  "nota_operativa": "Ruta de la mañana"
}
```

Reglas de validación:

- Los tres campos son obligatorios.
- `fecha_programada` no puede ser anterior a hoy en Bogotá.
- Si es hoy, la hora debe ser futura.
- El recolector debe ser compatible con el flujo y estar activo.
- Se registran `coordinador_id`, `recolector_id`, fecha, hora e historial.

### POST `/api/solicitudes/{id}/cerrar`

Cierre transaccional con peso real y puntos (RN-05/RN-06). Puede hacerlo el coordinador del flujo, el recolector asignado o un administrador. La solicitud debe estar `PROGRAMADA`.

```json
{
  "cantidad_real_kg": 10.0,
  "nota_operativa": "Recolección confirmada en campo"
}
```

Respuesta `200` (extiende `SolicitudPublica`):

```json
{
  "id": 1,
  "estado": "RECOLECTADA",
  "cantidad_real_kg": 10.0,
  "puntos_otorgados": 75.0,
  "regla_puntos_id": 2,
  "calculo_puntos": {
    "regla_puntos_id": 2,
    "flujo": "ORGANICO",
    "tipo_generador": "UNIDAD_PRODUCTIVA",
    "puntos_base_solicitud": 15.0,
    "puntos_por_kg": 6.0,
    "cantidad_real_kg": 10.0,
    "puntos_otorgados": 75.0,
    "formula": "15.00 base + 10.00 kg × 6.00 puntos/kg = 75.00 EcoPuntos",
    "nota_fsd": "Cálculo parametrizable sujeto a validación FSD."
  }
}
```

Comportamiento transaccional:

1. Bloquea la fila de la solicitud (`SELECT ... FOR UPDATE`).
2. Bloquea la fila del solicitante y la regla activa.
3. Verifica estado `PROGRAMADA`; si ya está `RECOLECTADA`, responde `409 SOLICITUD_YA_CERRADA` sin volver a acreditar.
4. Calcula `puntos = puntos_base_solicitud + puntos_por_kg × cantidad_real_kg` con redondeo a dos decimales (`ROUND_HALF_UP`).
5. Actualiza la solicitud, incrementa `usuarios.puntos_acumulados`, guarda `regla_puntos_id` y agrega el historial con la fórmula aplicada.
6. Confirma todo en un solo `COMMIT`; cualquier fallo hace rollback.

Dos cierres concurrentes: PostgreSQL serializa por la fila; el segundo recibe `SOLICITUD_YA_CERRADA`. Los puntos se acreditan exactamente una vez. La nota del historial conserva la regla, base, valor por kg y total usados, aunque la regla se edite después.

Errores: `403 CIERRE_NO_AUTORIZADO`, `409 ESTADO_INVALIDO`, `409 REGLA_PUNTOS_NO_DISPONIBLE`, `422 CANTIDAD_INVALIDA` (si se llama al servicio directamente), `409 CONFLICTO_DATOS`.

### POST `/api/solicitudes/{id}/cancelar`

```json
{"motivo": "Cambio de planes del hogar"}
```

- El propietario solo puede cancelar en `RECIBIDA` o `EN_REVISION`.
- El coordinador del flujo o un administrador puede cancelar antes de `RECOLECTADA`.
- No se acreditan puntos. Siempre queda registro en historial.

## 4. Estados y transiciones

| Estado | Significado |
| --- | --- |
| `RECIBIDA` | Alta confirmada; pendiente de gestión del coordinador. |
| `EN_REVISION` | Coordinador tomó la solicitud para revisión humana. |
| `ASIGNADA` | Recolector compatible asignado, sin fecha/hora aún. |
| `PROGRAMADA` | Fecha, hora y recolector confirmados. |
| `RECOLECTADA` | Cierre confirmado; puntos acreditados una vez. |
| `CANCELADA` | Cerrada sin recolección ni puntos. |

Transiciones implementadas:

```text
RECIBIDA ──revisar──> EN_REVISION ──asignar──> ASIGNADA ──programar──> PROGRAMADA
    │                    │                        │                        │
    ├──asignar───────────┤                        │                        ├──programar (reprogramar)
    ├──programar─────────┼────────────────────────┘                        └──cerrar──> RECOLECTADA
    └──cancelar──────────┴──cancelar──────────────────────────────────────> CANCELADA
```

`RECOLECTADA` y `CANCELADA` son terminales en esta API.

## 5. Privacidad (RN-07)

| Observador | Ve solicitud | Teléfono/dirección del solicitante |
| --- | --- | --- |
| Propietario | La propia | Sí (sus datos) |
| Coordinador del flujo | Todas las de su flujo | Sí (dato operativo) |
| Recolector asignado | Solo las asignadas | Sí (dato operativo) |
| Administrador | Todas | Sí |
| Otro hogar/unidad | No (404) | No |
| Coordinador del otro flujo | No (404) | No |
| Recolector no asignado | No (404) | No |

El serializador `ContactoSolicitante` devuelve `telefono`, `direccion` y `sector_manzana` como `null` para observadores no autorizados. Aun así, las rutas bloquean el acceso completo; el `null` es una segunda barrera. No se registran cuerpos de petición ni datos personales en logs. Los errores de integridad no exponen SQL ni valores.

`es_piloto` (RN-08) es una **etiqueta** de población piloto FSD. No restringe acceso ni funcionalidades por sí sola.

## 6. Administración

Todas las rutas `/api/admin/*` exigen rol `ADMIN`. El administrador puede consultar todas las solicitudes, cerrarlas o cancelarlas como respaldo operativo, pero **no revisa, programa ni asigna**: esa decisión sigue reservada al coordinador humano del flujo (RN-02/RN-03).

### Reglas de puntos

- `GET /api/admin/reglas-puntos?flujo=&tipo_generador=&activa=&limit=&offset=` — incluye reglas históricas inactivas.
- `POST /api/admin/reglas-puntos` — crea una regla. Si `activa=true` y ya existe una activa para el mismo par, la anterior pasa a `activa=false` en la misma transacción; las solicitudes históricas conservan su `regla_puntos_id`.
- `PATCH /api/admin/reglas-puntos/{id}` — actualiza parámetros, descripción o `activa`. Para cambiar `flujo` o `tipo_generador`, crear una regla nueva y desactivar la anterior. No se eliminan reglas.

```json
{
  "flujo": "RECICLABLE",
  "tipo_generador": "HOGAR",
  "puntos_base_solicitud": 10,
  "puntos_por_kg": 8,
  "valor_referencia_kg_cop": 120,
  "descripcion_regla": "Regla piloto de reciclables de hogar.",
  "activa": true
}
```

`GET /api/reglas-puntos` (autenticado, cualquier rol) devuelve solo reglas activas para mostrar la fórmula y la nota “Cálculo parametrizable sujeto a validación FSD”.

### Cuentas y modo piloto

- `GET /api/admin/usuarios?rol=&es_piloto=&activo=&q=&limit=&offset=` — listado administrativo.
- `PATCH /api/admin/usuarios/{id}/piloto` — body `{"es_piloto": true}`. Solo aplica a `HOGAR` y `UNIDAD_PRODUCTIVA`; otro rol responde `422 USUARIO_NO_APLICA_PILOTO`.

## 7. Integración WhatsApp con Twilio

El webhook vive en el mismo backend FastAPI y reutiliza los servicios de `app.services.solicitudes`; no duplica el cálculo de puntos ni cambia estados por su cuenta. Meta Cloud API quedó reemplazada por Twilio WhatsApp.

### Endpoint

- `POST /api/webhooks/whatsapp` — recibe `application/x-www-form-urlencoded`, exige `X-Twilio-Signature` y valida la URL exacta, todos los parámetros y `AccountSid` con `twilio.request_validator.RequestValidator`. La URL a validar se toma de `WEBHOOK_PUBLIC_URL`, se reconstruye con `X-Forwarded-Proto`/`X-Forwarded-Host` detrás de proxy o usa `request.url`. Firma o cuenta inválidas devuelven `403`.
- El endpoint responde siempre TwiML vacío (`<Response/>`) para evitar respuestas automáticas no deseadas. Los callbacks de estado (`MessageStatus`/`SmsStatus`) se ignoran.
- Formatos admitidos: `MessageSid` (dedupe), `From`, `To`, `Body`, `NumMedia`, `MediaUrl0` y `MediaContentType0`. El número se normaliza quitando el prefijo `whatsapp:` y aplicando formato internacional colombiano cuando aplica.
- No existe el desafío GET de Meta; en Twilio la verificación es la firma de cada petición.

### Flujo admitido

- Texto, foto o nota de voz: el proveedor configurado (`IA_PROVEEDOR=openai|azure`) propone una intención y campos; el backend valida y ejecuta.
- `SOLICITUD_RECOLECCION`: si el flujo es inferible, se crea con `crear_solicitud()` en estado `RECIBIDA`, guardando la preferencia del vecino en `disponibilidad_usuario`. La IA nunca asigna recolector ni fecha/hora. Si falta el flujo, el bot pregunta y guarda el borrador en `MensajeWhatsapp.borrador_json` hasta la respuesta.
- `CIERRE_RECOLECCION`: la IA extrae código y peso; `cerrar_solicitud_por_codigo()` valida remitente, permisos, estado y peso en la misma transacción que acredita puntos. Un cierre repetido no duplica acreditación.
- `CONSULTA_ESTADO`: se resuelve solo la última solicitud activa del teléfono autenticado, sin confiar en un código público como autorización.
- `DUDA_AMBIENTAL` y `OTRO`: respuesta educativa breve sin cambios de estado.
- Número no registrado: el bot pide nombre y dirección; con esa respuesta crea un `Usuario` `HOGAR`, `es_piloto=true`, contraseña aleatoria y teléfono normalizado a formato internacional.

### Mensajería, IA y configuración

- Las respuestas salientes usan `twilio.rest.Client.messages.create` con `from_=TWILIO_WHATSAPP_NUMBER` y `to=whatsapp:<teléfono>`. Si `TWILIO_CONTENT_SID` está configurado se envía ese Content SID con `content_variables={"1": texto}`; si no, texto libre dentro de la ventana de conversación de 24 h.
- Los eventos post-commit `solicitud_programada` y `solicitud_cerrada` se publican desde `app.services.solicitudes` y `app.whatsapp.notificaciones` envía un mensaje al solicitante con recolector, día y hora o con peso y puntos. Asignar sin programar no notifica.
- Los archivos se descargan desde `MediaUrl0` con Basic Auth de Twilio y solo desde `api.twilio.com`. Las imágenes se redimensionan y pierden EXIF; los audios se transcriben con el proveedor de IA configurado. No se conserva el archivo original.
- `wa_message_id` continúa siendo la columna de dedupe y ahora almacena el `MessageSid` de Twilio; no se requirió migración.
- Variables: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_NUMBER`, `TWILIO_CONTENT_SID`, `WEBHOOK_PUBLIC_URL`, `IA_PROVEEDOR` (`openai` por defecto o `azure`), `OPENAI_API_KEY`, `OPENAI_MODEL` (default `gpt-4o-mini`), `OPENAI_TRANSCRIPTION_MODEL` (default `gpt-transcribe`), `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_CHAT_DEPLOYMENT`, `AZURE_OPENAI_AUDIO_DEPLOYMENT`, `AZURE_OPENAI_API_VERSION` (default `2024-10-21`) y `AZURE_OPENAI_API_MODE` (`classic` o `v1`).
- El texto se anonimiza antes del prompt (sin nombres, teléfonos ni direcciones exactas) y los errores no exponen secretos ni datos personales.
- Las respuestas de IA se validan con `ClasificacionIA` (`extra="forbid"`); una salida inválida cae a una respuesta aclaratoria y no ejecuta operaciones.

## 8. Cuentas semilla ficticias

La semilla (`python -m app.seed`) carga estas cuentas de demostración. Todas usan la contraseña definida en `SEED_DEFAULT_PASSWORD` o en la variable específica por rol. No son datos personales reales.

| Rol | Teléfono | Uso |
| --- | --- | --- |
| `ADMIN` | `+573000000100` | Reglas de puntos y modo piloto. |
| `COORD_HUERTEROS` | `+573000000101` | Bandeja y programación orgánica. |
| `HUERTERO` | `+573000000102`, `+573000000103` | Recolección orgánica. |
| `COORD_RECICLADORES` | `+573000000104` | Bandeja y programación reciclable. |
| `RECICLADOR` | `+573000000105`, `+573000000106` | Recolección reciclable. |
| `UNIDAD_PRODUCTIVA` | `+573000000107` | Generador piloto de orgánicos. |
| `HOGAR` | `+573000000108` | Hogar piloto. |
| `HOGAR` | `+573000000109` | Hogar de comparación, no piloto. |

Reglas semilla: orgánico hogar `10 + 5/kg`, orgánico unidad productiva `15 + 6/kg`, reciclable hogar `10 + 8/kg`, reciclable unidad productiva `15 + 10/kg`.

## 9. Configuración relevante

```env
SECRET_KEY=<mínimo 32 caracteres, nunca en Git>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
ENTORNO=development
```

Si `SECRET_KEY` falta o es más corta que 32 caracteres, la API no arranca y muestra un error explícito. Los orígenes CORS deben incluir la URL del frontend desplegado.

## 10. Verificación ejecutada

- `pytest tests` con SQLite aislado: autenticación, permisos, flujo completo, puntos, historial, privacidad, admin y contrato OpenAPI.
- `pytest tests` con PostgreSQL 16 y `TEST_DATABASE_URL`: migraciones de persistencia, semilla idempotente, restricciones SQL y cierre concurrente real (una sola acreditación).
- Prueba de humo con `docker compose`: migración, semilla, login, alta orgánica, programación, cierre con 10 kg → 75 puntos, doble cierre bloqueado, historial y cambio de piloto.
