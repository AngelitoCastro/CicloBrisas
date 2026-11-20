# Plan de Desarrollo, Arquitectura de Datos y Reglas Operativas

Este documento guía la ejecución técnica del equipo durante las jornadas del **20 y 21 de noviembre de 2026**, integrando los hallazgos de campo, la charla previa y el documento oficial del reto.

---

## 1. Alineación con la Operación Real (Charla Previa)

1. **Paneles exclusivos para Coordinadores:**
   * No se construyen dashboards complejos para recolectores ni para habitantes.
   * **Coordinador de Recicladores (Baja fricción):** Interfaz tipo tarjetas con botones grandes (`min-height: 56px`). Selecciona el reciclador de su cuadrilla, define día/hora y presiona **"Asignar y Enviar WhatsApp"**.
   * **Coordinador de Huerteros (Perfil técnico):** Tabla operativa con filtros por tipo de generador (Unidad Productiva vs. Hogar), estado, volumen y gestión de compostaje.
2. **Usuarios Externos (Habitantes y Unidades Productivas):**
   * Interfaz móvil directa: *Aprender a separar*, *Solicitar recolección*, *Ver programación (quién viene y cuándo)* y *Consultar puntos adaptables*.
3. **Flujo Bidireccional con WhatsApp e IA:**
   * **Salida:** El aplicativo envía plantillas/mensajes vía WhatsApp Cloud API al asignar y programar.
   * **Entrada:** Un webhook recibe mensajes de WhatsApp hacia el aplicativo. La IA responde dudas de separación de residuos a habitantes e interpreta confirmaciones de recolección enviadas por los recolectores desde campo.

---

## 2. Cronograma de Ejecución por Frentes (20 y 21 de Noviembre)

### Viernes 20 de Noviembre (Hasta las 5:00 p.m.) — Construcción Core
| Bloque Horario | Frente 1: Backend & PostgreSQL | Frente 2: WhatsApp API + IA | Frente 3: Frontend (React/Next + Tailwind) |
| :--- | :--- | :--- | :--- |
| **9:45 a.m. – 12:00 p.m.** | Configurar `docker-compose.yml`, crear esquema PostgreSQL, modelos SQLAlchemy, autenticación por rol y enrutamiento **RN-01**. | Configurar app en Meta Developers (WhatsApp Cloud API), levantar túnel HTTPS para webhook y probar envío/recepción básica. | Configurar proyecto con tokens CSS oficiales (`#063B2E`, `#168A2E`, `#F6C400`), logo intacto y vista móvil del **Habitante** (educación + solicitud). |
| **12:00 p.m. – 2:30 p.m.** | Implementar endpoints de asignación/programación (**RN-02**, **RN-03**), motor de **puntos adaptables** (**RN-05**, **RN-06**) y filtro de privacidad (**RN-07**). | Implementar *System Prompt* de IA (OpenAI/Claude) para responder dudas ambientales y parsear mensajes de cierre de recolección enviados al webhook. | Construir los **dos paneles de coordinadores**: vista ultra-intuitiva de tarjetas para Recicladores y vista tabular/analítica para Huerteros. |
| **2:30 p.m. – 5:00 p.m.** | Cargar script `seed.py` con los actores del **Escenario de Demostración** y desplegar backend + BD en nube. | Conectar eventos del backend con notificaciones WhatsApp (asignación al recolector y confirmación de horario al usuario). | Conectar frontend a la API en nube, validar responsividad en móvil/tablet y verificar que todos los estados tengan icono + texto + color. |

### Sábado 21 de Noviembre (8:00 a.m. – 12:00 m.) — Estabilización y Sustentación
* **8:00 a.m. – 10:00 a.m.:** Pruebas integrales de las reglas **RN-01 a RN-08**, validación de seguridad (ninguna clave en GitHub), captura de diagrama de arquitectura y modelo ER.
* **10:00 a.m. – 12:00 m.:** Ensayo cronometrado (máximo 4 minutos) del **Escenario Mínimo de Demostración** en vivo.

---

## 3. Esquema de Base de Datos (PostgreSQL)

```sql
-- Extensiones
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Usuarios y Actores (Habitantes, Unidades Productivas, Coordinadores, Recolectores, Admin)
CREATE TABLE usuarios (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nombre VARCHAR(120) NOT NULL,
    telefono VARCHAR(25) UNIQUE NOT NULL,
    rol VARCHAR(30) NOT NULL CHECK (rol IN (
        'HOGAR',
        'UNIDAD_PRODUCTIVA',
        'COORD_HUERTEROS',
        'HUERTERO',
        'COORD_RECICLADORES',
        'RECICLADOR',
        'ADMIN'
    )),
    direccion VARCHAR(200),
    sector_manzana VARCHAR(100),
    es_piloto BOOLEAN DEFAULT TRUE, -- RN-08: Control de población piloto FSD
    puntos_acumulados NUMERIC(10, 2) DEFAULT 0,
    activo BOOLEAN DEFAULT TRUE,
    creado_en TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Reglas de Puntos Adaptables (RN-06: Parametrizables y sujetas a validación FSD)
CREATE TABLE reglas_puntos (
    id SERIAL PRIMARY KEY,
    flujo VARCHAR(20) NOT NULL CHECK (flujo IN ('ORGANICO', 'RECICLABLE')),
    tipo_generador VARCHAR(30) NOT NULL CHECK (tipo_generador IN ('HOGAR', 'UNIDAD_PRODUCTIVA')),
    puntos_base_solicitud NUMERIC(10, 2) DEFAULT 10,
    puntos_por_kg NUMERIC(10, 2) DEFAULT 5,
    valor_referencia_kg_cop NUMERIC(10, 2) DEFAULT 80, -- Parámetro editable por Admin
    descripcion_regla TEXT,
    activa BOOLEAN DEFAULT TRUE,
    actualizado_en TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Solicitudes de Recolección (RN-01, RN-02, RN-03, RN-04)
CREATE TABLE solicitudes (
    id SERIAL PRIMARY KEY,
    codigo_publico VARCHAR(20) UNIQUE NOT NULL, -- Ej: ECO-2026-001
    solicitante_id UUID NOT NULL REFERENCES usuarios(id),
    flujo VARCHAR(20) NOT NULL CHECK (flujo IN ('ORGANICO', 'RECICLABLE')), -- RN-01
    subtipo_material VARCHAR(100), -- Ej: Cáscaras/vegetales, Cartón/PET, Donación baldes
    cantidad_estimada_kg NUMERIC(8, 2),
    cantidad_real_kg NUMERIC(8, 2),
    disponibilidad_usuario VARCHAR(120) NOT NULL,
    observaciones TEXT,
    estado VARCHAR(25) NOT NULL DEFAULT 'RECIBIDA' CHECK (estado IN (
        'RECIBIDA',
        'EN_REVISION',
        'ASIGNADA',
        'PROGRAMADA',
        'RECOLECTADA',
        'CANCELADA'
    )),
    coordinador_id UUID REFERENCES usuarios(id), -- RN-03
    recolector_id UUID REFERENCES usuarios(id),  -- RN-03
    fecha_programada DATE,                       -- RN-02
    hora_programada TIME,                        -- RN-02
    puntos_otorgados NUMERIC(10, 2) DEFAULT 0,   -- RN-05
    creado_en TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    actualizado_en TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. Historial de Trazabilidad (RN-04)
CREATE TABLE historial_estados (
    id SERIAL PRIMARY KEY,
    solicitud_id INTEGER NOT NULL REFERENCES solicitudes(id) ON DELETE CASCADE,
    estado_anterior VARCHAR(25),
    estado_nuevo VARCHAR(25) NOT NULL,
    cambiado_por UUID REFERENCES usuarios(id),
    nota_operativa TEXT,
    fecha_cambio TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 5. Registro de Mensajes WhatsApp e IA
CREATE TABLE mensajes_whatsapp (
    id SERIAL PRIMARY KEY,
    solicitud_id INTEGER REFERENCES solicitudes(id),
    telefono_remitente VARCHAR(25) NOT NULL,
    direccion VARCHAR(15) NOT NULL CHECK (direccion IN ('ENTRANTE', 'SALIENTE')),
    contenido TEXT NOT NULL,
    intencion_ia VARCHAR(50), -- Ej: DUDA_AMBIENTAL, CIERRE_RECOLECCION, CONSULTA_ESTADO
    procesado_por_ia BOOLEAN DEFAULT FALSE,
    creado_en TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 6. Contenidos de Educación Ambiental (Sección 5.2)
CREATE TABLE contenidos_educativos (
    id SERIAL PRIMARY KEY,
    titulo VARCHAR(150) NOT NULL,
    categoria VARCHAR(30) NOT NULL CHECK (categoria IN ('ORGANICO', 'RECICLABLE', 'HUERTA', 'RUTAS')),
    resumen TEXT NOT NULL,
    que_si_va TEXT,
    que_no_va TEXT,
    orden INTEGER DEFAULT 1,
    publicado BOOLEAN DEFAULT TRUE
);
```

---

## 4. Checklist de Cumplimiento de Reglas (RN-01 a RN-08)

* [ ] **RN-01:** El endpoint `POST /api/solicitudes` asigna automáticamente el flujo `ORGANICO` a la bandeja de `COORD_HUERTEROS` y `RECICLABLE` a la bandeja de `COORD_RECICLADORES`.
* [ ] **RN-02:** El endpoint `PATCH /api/solicitudes/{id}/programar` valida que `fecha_programada`, `hora_programada` y `recolector_id` no sean nulos antes de cambiar el estado a `PROGRAMADA`.
* [ ] **RN-03:** Toda solicitud asignada registra tanto `coordinador_id` como `recolector_id`.
* [ ] **RN-04:** Cada transición de estado inserta automáticamente una fila en `historial_estados`.
* [ ] **RN-05 & RN-06:** El cálculo de `puntos_otorgados` ocurre únicamente en el endpoint de cierre (`RECOLECTADA`), leyendo la tabla `reglas_puntos` editable por el Administrador y mostrando una nota visual: *"Cálculo parametrizable sujeto a validación FSD"*.
* [ ] **RN-07:** Los serializadores Pydantic (`SolicitudPublicaResponse`) ocultan `telefono` y `direccion` exacta a usuarios externos no propietarios de la solicitud.
* [ ] **RN-08:** El panel de Administrador incluye un interruptor para activar/desactivar el modo piloto (`es_piloto`) en hogares y unidades productivas.