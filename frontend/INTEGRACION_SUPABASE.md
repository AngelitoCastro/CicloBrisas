# Plan de integración (pendiente)

La implementación actual es solamente frontend. `src/services/repository.ts` concentra la persistencia de demostración. En la fase siguiente, instalar `@supabase/supabase-js`, configurar `VITE_SUPABASE_URL` y `VITE_SUPABASE_PUBLISHABLE_KEY`, y reemplazar el acceso local por servicios asíncronos con manejo de errores, caché y control de concurrencia. No colocar claves service_role ni secretos de Meta en el frontend.

## Modelo propuesto

- `profiles`: usuario de Supabase Auth, rol, nombre, grupo asignado, estado.
- `groups`: categoría (orgánico/aprovechable), nombre, coordinador responsable.
- `members`: recolectores/huerteros, grupo, teléfono, disponibilidad.
- `external_users`: habitantes/comercios, teléfono, dirección, piloto; no necesitan un login web.
- `requests`: usuario externo, grupo/categoría, tipo, descripción, evidencia, preferencia, peso estimado, unidad, modalidad, origen, estado, autorización (por y cuándo), asignación, fecha/franja.
- `request_events`: auditoría de transiciones, comentarios, actor y fecha.
- `weighings` / `weighing_items`: peso aceptado por material, tarifa histórica y valor calculado, responsable. `donations`: unidades recibidas y observaciones.
- `schedules` / `schedule_slots`: días y franjas por grupo/categoría.
- `material_rates`: material, valor COP/kg, vigencia.
- `messages`: dirección, contacto, solicitud, estado de entrega, identificador de Meta, contenido.
- `knowledge_entries`: pregunta, respuesta aprobada, vigencia, versión.
- Puntos: posponer esquema de reglas y libro de movimientos hasta decisión comunitaria.

## Seguridad y consistencia

RLS en todas las tablas: administradores con permisos globales, coordinadores únicamente en su propio grupo; recolectores y habitantes sin acceso directo al portal. Las funciones SQL/RPC deben comprobar las transiciones, sobre todo pendiente → autorizada → programada → completada, aplicar transacciones para pesajes/cierre y evitar duplicados. Almacenamiento privado para fotos, URLs firmadas y acceso restringido por grupo. Consentimiento y política de retención de datos personales. El selector de roles y localStorage del prototipo NO sustituyen estas medidas.

## WhatsApp e IA

Webhook de Meta en una función de backend (por ejemplo Edge Function), verificación de firma y deduplicación por identificador del mensaje. Guardar entrada, foto y descripción, sugerir categoría y solicitar datos faltantes. La autorización humana es obligatoria antes de programar. Tras la asignación, generar mensajes a ambos contactos mediante una cola de salida; gestionar plantillas aprobadas y ventana de conversación, reintentos idempotentes y estados entregado/error. No afirmar envío si el proveedor no confirma. La bandeja se actualizará mediante consultas y Realtime según los permisos de cada perfil.

El asistente consulta únicamente información autorizada (horarios, material, estado de solicitud, tarifas internas según permisos), responde con base en conocimiento aprobado y deriva al coordinador cuando no tenga certeza. No inventa puntos ni asignaciones. No enviar datos personales innecesarios al modelo.
