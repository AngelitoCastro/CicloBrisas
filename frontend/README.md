# EcoConecta — frontend v2

Gestión comunitaria de residuos para Brisas de San Pablo. Rediseño del proyecto original en React 19 + TypeScript + Tailwind CSS 4 + Vite. Iconos Lucide. Las imágenes de referencia se emplearon como guía de composición y color, no como fondos. No modifica el ZIP original.

## Ejecutar en Windows / VS Code

1. Abrir la carpeta `frontend` en VS Code.
2. Instalar Node.js 22 LTS (o una versión compatible con Vite 6) si no está instalado.
3. Abrir una terminal en la carpeta que contiene `package.json` y ejecutar:

```bash
npm ci
npm run dev
```

Abrir la URL que muestre Vite (normalmente `http://localhost:5173`). Para comprobar tipos y compilar: `npm run build`.

## Perfiles de demostración

- Coordinador de Huerta: orgánicos, autorización, recolección/entrega directa, donaciones, equipo, mensajes, pesaje, horarios e historial.
- Coordinador de Reciclaje: aprovechables, autorización, asignación, pesaje por material, valor para el reciclador, equipo, mensajes, horarios y registro de recepción física de materiales.
- Administrador: resumen general, filtros, exportación CSV, equipo, horarios, tarifas, base de conocimiento y mensajes.

El selector de perfil es una demostración, NO un inicio de sesión seguro. Los usuarios externos no tienen panel. Los grupos del equipo son etiquetas de organización; la separación real por coordinador/grupo queda para Supabase.

## Probar el flujo

1. Selecciona un coordinador y abre una solicitud recibida. En Huerta, usa la tabla y sus filtros de estado, generador y fecha.
2. Revisa la descripción/foto, solicita más información si corresponde, corrige la categoría o autoriza. Se puede rechazar con motivo.
3. Una vez autorizada, selecciona responsable, fecha permitida y franja configurada. Añade una nota. Programa y avisa por WhatsApp (simulado). Para entrega directa se asigna quien recibe.
4. En una solicitud programada, elige **Registrar cierre** y registra el peso realmente aceptado por material o unidades de donación. Anota lo rechazado. Finaliza. El cálculo de reciclaje se acredita como valor para el reciclador, no para el habitante.
5. Consulta historial, mensajes y reportes. Puedes simular entradas a partir de un formulario (no procesa mensajes reales ni clasifica por IA).
6. En Configuración cambia los días y franjas, y las tarifas de reciclaje. Cada registro final conserva su tarifa aplicada. Los horarios de ejemplo no representan acuerdos definitivos.

En Reciclaje, abre **Registros de materiales** para registrar una recepción independiente. Selecciona un reciclador, registra el peso por material y añade pacas, proveedor o tiquete si corresponde. El historial conserva el peso y las tarifas aplicadas al guardar.

Las modificaciones se guardan en localStorage del navegador. Para reiniciar la demo elimina la clave `ecoconecta-v2-demo` en las herramientas del navegador (Application > Local Storage). No uses datos personales reales en esta versión. Todas las personas, teléfonos y solicitudes iniciales son datos de demostración. Las fotos adjuntas son locales y están limitadas a 1 MB; localStorage tiene una cuota limitada.

## Decisiones de alcance

- En la demostración, los cierres orgánicos con peso aceptado registran 10 EcoPuntos base más 5 por kg. Los reportes y el CSV incluyen el resultado guardado. Cálculo parametrizable sujeto a validación FSD.
- No se implementan tarifas multiusuarios; los $80 COP/kg son un valor inicial editable por material, destinado al reciclador.
- Lunes, miércoles y viernes son días iniciales de ejemplo; las franjas son independientes, editables por categoría y no afectan asignaciones anteriores.
- Los materiales declarados se revisan antes de asignar; la aceptación definitiva se registra tras la clasificación física. No se automatiza la decisión de aceptar residuos.
- Se conserva «Brisas de San Pablo» de las notas; la referencia visual indica «Villas de San Pablo». Confirmar nombre oficial antes del despliegue.
- Para incorporar la marca oficial, colocar `logo-ecoconecta.svg` o `logo-ecoconecta.png` en `src/assets/`. El prototipo muestra el nombre EcoConecta cuando falta el archivo.

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

Ver `INTEGRACION_SUPABASE.md` para la arquitectura prevista. No contiene credenciales ni conexión activa, y no ejecuta migraciones.
