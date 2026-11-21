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

## Perfiles del panel

- Coordinador de Huerta: orgánicos, autorización, recolección/entrega directa, donaciones, equipo, mensajes, pesaje, horarios e historial.
- Coordinador de Reciclaje: aprovechables, autorización, asignación, pesaje por material, valor para el reciclador, equipo, mensajes, horarios y registro de recepción física de materiales.
- Administrador: resumen general, filtros, exportación CSV, equipo, reglas de EcoPuntos, tarifas y base de conocimiento.

FastAPI valida las credenciales y aplica los permisos de cada perfil. Los usuarios externos no tienen acceso al panel.

En **Equipo**, los coordinadores consultan los miembros de su actividad. Administración puede agregar, editar, activar y desactivar miembros de ambos equipos.

## Probar el flujo

1. En cualquiera de los dos perfiles, selecciona una tarjeta en **Por programar**. La ficha se muestra junto a la lista en pantallas amplias y debajo en móvil. Puedes filtrar por generador y usar **Buscar y filtrar** para acotar la búsqueda.
2. Revisa y corrige el material, el peso estimado, la referencia y las notas. Puedes marcar la solicitud en revisión o cancelarla con motivo.
3. Selecciona un recolector compatible, fecha y franja. Pulsa **Validar y notificar al recolector**.
4. En **Programadas**, comprueba el estado del aviso. El recolector asignado puede confirmar con `LISTO <código> <peso>`. Para el cierre manual de respaldo, registra el peso y el motivo en la ficha.
5. Consulta el historial y los EcoPuntos acreditados en la solicitud recolectada.
6. En **Métricas**, cada coordinador gestiona sus días y franjas y consulta los EcoPuntos por kilo para hogares y unidades productivas. En Reciclaje también se muestran las tarifas vigentes en COP. Administración edita las reglas de puntos y las tarifas de reciclaje en **Reglas de EcoPuntos**. Cada registro final conserva la tarifa aplicada. Los horarios de ejemplo no representan acuerdos definitivos.

En Reciclaje, abre **Registros de materiales** para registrar una recepción independiente. Selecciona un reciclador, registra el peso por material y añade pacas, proveedor o tiquete si corresponde. El historial conserva el peso y las tarifas aplicadas al guardar.

El navegador guarda los horarios, las tarifas y la base de conocimiento en `ecoconecta-v2-prefs`. Los datos operativos de la API se cargan en memoria para la sesión autenticada. El token se guarda en `sessionStorage` y se elimina al cerrar sesión.

## Decisiones de alcance

- En **Administración → Reglas de EcoPuntos** se guardan en la API los valores por flujo y tipo de generador. Los cierres de Huerta y Reciclaje con peso aceptado guardan los EcoPuntos y la regla aplicada. Consulta el resultado en la ficha de **Recolectadas**. En Reciclaje, el valor en COP para el reciclador se muestra por separado. Cálculo parametrizable sujeto a validación FSD.
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
