# EcoConecta — frontend v2

Gestión comunitaria de residuos para Villas de San Pablo. Rediseño del proyecto original en React 19 + TypeScript + Tailwind CSS 4 + Vite. Iconos Lucide. Las imágenes de referencia se emplearon como guía de composición y color, no como fondos. No modifica el ZIP original.

## Ejecutar en Windows / VS Code

1. Abrir la carpeta `frontend` en VS Code.
2. Instalar Node.js 22 LTS (o una versión compatible con Vite 6) si no está instalado.
3. Abrir una terminal en la carpeta que contiene `package.json` y ejecutar:

```bash
npm ci
npm run dev
```

Abrir la URL que muestre Vite (normalmente `http://localhost:5173`). Para comprobar tipos y compilar: `npm run build`.

Desde la raíz del repositorio, `docker compose up --build` levanta PostgreSQL, la API en `:8000`, el despachador de WhatsApp (`avisos`) y este dev server en `:5173`. La API acepta ese origen por CORS y la URL base se configura con `VITE_API_URL` (por defecto `http://localhost:8000`).

### Autenticación y paneles conectados a FastAPI

- La pantalla de acceso inicia sesión contra `POST /api/auth/login` (teléfono y contraseña) y carga solicitudes (`GET /api/solicitudes`), recolectores compatibles (`GET /api/recolectores`) y reglas activas (`GET /api/reglas-puntos`) según el rol autenticado (`COORD_HUERTEROS`, `COORD_RECICLADORES` o `ADMIN`).
- El acceso rápido de demostración permanece **desactivado por defecto** (`VITE_ENABLE_DEMO_LOGIN=false`); solo debe habilitarse localmente junto con `ENTORNO=development`.
- En **Por programar** aparecen las solicitudes recibidas por WhatsApp Meta o portal con **material, peso estimado, referencia y notas editables**. Al pulsar **Validar y notificar al recolector**, `PATCH /api/solicitudes/{id}/programar` guarda datos revisados, recolector compatible, fecha, hora, historial y avisos en una sola transacción.
- En **Programadas** se muestran por separado la **Programación guardada** y el **Estado del aviso WhatsApp** (`GET /api/solicitudes/{id}/avisos`), permitiendo reintentar solo fallos confirmados (`FALLIDO`) y esperando conciliación cuando un envío está en `CONCILIAR`. El cierre manual de respaldo llama a `POST /api/solicitudes/{id}/cerrar` con acreditación única de EcoPuntos.

Desde la pantalla de acceso, **Ver recorrido por WhatsApp** abre una demostración con datos ficticios. Elige Huerta o Reciclaje. Como **Habitante**, solicita la recolección. Como **Coordinador**, apruébala y programa la visita. En **Recolector**, envía la respuesta simulada con el código y peso. Vuelve a **Habitante** para ver el cierre y consultar el saldo. La demo comparte la solicitud entre vistas y guarda su progreso por separado durante la sesión del navegador.

## Perfiles de demostración

- Coordinador de Huerta: orgánicos, autorización, recolección/entrega directa, donaciones, equipo, mensajes, pesaje, horarios e historial.
- Coordinador de Reciclaje: aprovechables, autorización, asignación, pesaje por material, valor para el reciclador, equipo, mensajes, horarios y registro de recepción física de materiales.
- Administrador: resumen general, filtros, exportación CSV, equipo, reglas de EcoPuntos, tarifas y base de conocimiento.

El selector de perfil es una demostración, NO un inicio de sesión seguro. Los usuarios externos no tienen panel. Los grupos del equipo son etiquetas de organización; la separación real por coordinador/grupo queda para Supabase.

En **Equipo**, los coordinadores consultan los miembros de su actividad. Administración puede agregar, editar, activar y desactivar miembros de ambos equipos.

## Probar el flujo

1. En cualquiera de los dos perfiles, selecciona una tarjeta en **Por programar**. La ficha se muestra junto a la lista en pantallas amplias y debajo en móvil. Puedes filtrar por generador y usar **Buscar y filtrar** para acotar la búsqueda.
2. Revisa la descripción/foto, solicita más información si corresponde, corrige la categoría o autoriza. Se puede rechazar con motivo.
3. Una vez autorizada, selecciona responsable, fecha permitida y franja configurada. Añade una nota. Programa y avisa por WhatsApp (simulado). Para entrega directa se asigna quien recibe.
4. En **Programadas**, la ficha indica que se espera la confirmación del responsable. En la demo puedes simular su mensaje con `LISTO <código> <cantidad>`. Si usas el cierre manual de respaldo, registra la cantidad y el motivo. En Reciclaje, el peso total permite cerrar y calcular EcoPuntos. Completa el desglose en **Recolectadas** para calcular el valor en COP.
5. Consulta los avisos en el seguimiento de cada solicitud. Para simular una solicitud de WhatsApp, usa el recorrido de demostración desde la pantalla de acceso.
6. En **Métricas**, cada coordinador gestiona sus días y franjas y consulta los EcoPuntos por kilo para hogares y unidades productivas. En Reciclaje también se muestran las tarifas vigentes en COP. Administración edita las reglas de puntos y las tarifas de reciclaje en **Reglas de EcoPuntos**. Cada registro final conserva la tarifa aplicada. Los horarios de ejemplo no representan acuerdos definitivos.

En Reciclaje, abre **Registros de materiales** para registrar una recepción independiente. Selecciona un reciclador, registra el peso por material y añade pacas, proveedor o tiquete si corresponde. El historial conserva el peso y las tarifas aplicadas al guardar.

Las modificaciones se guardan en localStorage del navegador. Para reiniciar la demo elimina la clave `ecoconecta-v2-demo` en las herramientas del navegador (Application > Local Storage). No uses datos personales reales en esta versión. Todas las personas, teléfonos y solicitudes iniciales son datos de demostración. Las fotos adjuntas son locales y están limitadas a 1 MB; localStorage tiene una cuota limitada.

## Decisiones de alcance

- En **Administración → Reglas de EcoPuntos** se guardan los valores de demostración por flujo y tipo de generador. La configuración se conserva en el navegador. Los cierres de Huerta y Reciclaje con peso aceptado guardan los EcoPuntos de demostración y la regla aplicada. Consulta el resultado en la ficha de **Recolectadas**. En Reciclaje, el valor en COP para el reciclador se muestra por separado. Cálculo parametrizable sujeto a validación FSD.
- No se implementan tarifas multiusuarios; los $80 COP/kg son un valor inicial editable por material, destinado al reciclador.
- Lunes, miércoles y viernes son días iniciales de ejemplo; las franjas son independientes, editables por categoría y no afectan asignaciones anteriores.
- Los materiales declarados se revisan antes de asignar; la aceptación definitiva se registra tras la clasificación física. No se automatiza la decisión de aceptar residuos.
- Los PNG proporcionados están en `src/assets/`. EcoConecta es la marca principal sobre fondo blanco. Villas de San Pablo y Fundación Santo Domingo aparecen en el acceso y en el pie de los paneles.

## Estructura

```
src/
  components/      Componentes reutilizables y formulario de solicitud
  pages/           Recolecciones, equipo, configuración, mensajes, reportes, capacitación
  services/        Datos de ejemplo y repositorio local
  types.ts         Tipos y utilidades compartidas
  App.tsx          Perfiles, navegación y estado de la aplicación
  index.css        Tailwind y sistema visual responsive
  main.tsx         Punto de entrada
```

## Próxima fase: Supabase + WhatsApp

Ver `INTEGRACION_SUPABASE.md` para el uso de Supabase como base del backend. No contiene credenciales; la URL de la API se configura con `VITE_API_URL`.
