# Distribución de tareas y ramas — EcoConecta

Equipo de cuatro personas. Los responsables se identifican por su posición en la distribución acordada hasta registrar sus nombres. Las listas representan trabajo pendiente, no funcionalidades ya implementadas.

## Responsables y ramas

| Responsable | Frente | Rama |
| --- | --- | --- |
| Tú | Backend, PostgreSQL e integración general | [equipo/backend](https://github.com/AngelitoCastro/CicloBrisas/tree/equipo/backend) |
| Compañero 1 | Portal comunitario y componentes visuales compartidos | [equipo/portal-comunitario](https://github.com/AngelitoCastro/CicloBrisas/tree/equipo/portal-comunitario) |
| Compañero 2 | Paneles de coordinadores | [equipo/paneles-coordinadores](https://github.com/AngelitoCastro/CicloBrisas/tree/equipo/paneles-coordinadores) |
| Compañero 3 | WhatsApp e inteligencia artificial | [equipo/whatsapp-ia](https://github.com/AngelitoCastro/CicloBrisas/tree/equipo/whatsapp-ia) |

Todas las ramas parten del mismo commit de `main` con esta distribución. Cada persona trabaja en su rama y propone integrar los cambios mediante un pull request hacia `main`.

## Tú — Backend, base de datos e integración

- [ ] Preparar FastAPI, PostgreSQL, configuración de entorno y arranque con Docker.
- [ ] Implementar modelos, datos semilla y autenticación con permisos por rol.
- [ ] Implementar creación y consulta de solicitudes, separación de flujos, asignación y programación.
- [ ] Validar encargado, fecha y hora antes de programar; registrar coordinador y recolector.
- [ ] Registrar historial de cada transición y proteger los datos personales por rol y propiedad.
- [ ] Implementar cierre transaccional y puntos configurables, evitando acreditaciones duplicadas.
- [ ] Publicar contratos de API y coordinar integración y despliegue del MVP.

**Entrega verificable:** una solicitud recorre `RECIBIDA → PROGRAMADA → RECOLECTADA`, conserva su historial y acredita puntos una sola vez. Los permisos impiden operaciones y consultas no autorizadas.

**Área propuesta:** `backend/`, configuración raíz de Docker y contratos de API.

## Compañero 1 — Portal comunitario

- [ ] Crear la base del frontend y los componentes compartidos con los colores y tipografías documentados.
- [ ] Construir educación ambiental y formulario para hogares y unidades productivas.
- [ ] Mostrar solicitud activa, estado, encargado, día y hora de recolección.
- [ ] Mostrar puntos y aclaración de que su cálculo es parametrizable y sujeto a validación FSD.
- [ ] Incorporar carga, errores, estados vacíos y presentación móvil accesible.
- [ ] Conectar las vistas con la API y verificar el recorrido de un habitante y un negocio.

**Entrega verificable:** un hogar o negocio registra una solicitud y consulta su programación y puntos. Los estados usan icono, texto y color.

**Área propuesta:** portal comunitario, estilos y componentes compartidos dentro de `frontend/`. Acordar las rutas exactas antes de iniciar.

## Compañero 2 — Paneles de coordinadores

- [ ] Construir tarjetas para el coordinador de Recicladores.
- [ ] Construir tabla y filtros para el coordinador de Huerteros.
- [ ] Incorporar selección de recolector, día y hora y acción de programar y notificar.
- [ ] Permitir cierre manual con peso y mostrar historial y resultado de puntos.
- [ ] Mostrar todos los estados acordados y mensajes de validación claros.
- [ ] Conectar los paneles con la API y verificar el aislamiento entre flujos y roles.

**Entrega verificable:** cada coordinador ve su flujo y programa una recolección; la aplicación rechaza programaciones sin encargado, día u hora. El cierre manual permite probar el MVP mientras se integra WhatsApp.

**Área propuesta:** vistas de coordinadores dentro de `frontend/`. Reutilizar los componentes del compañero 1.

## Compañero 3 — WhatsApp e IA

- [ ] Configurar WhatsApp Cloud API y probar envío y recepción desde el inicio.
- [ ] Implementar verificación y validación de autenticidad del webhook.
- [ ] Notificar asignación al recolector y programación al solicitante.
- [ ] Definir y validar la salida estructurada de IA para dudas, cierre, consulta de estado y otros mensajes.
- [ ] Anonimizar mensajes antes de consultar al proveedor de IA.
- [ ] Validar el remitente y deduplicar mensajes; usar el servicio de cierre del backend para actualizar solicitudes y puntos.
- [ ] Probar errores de proveedor y evitar confirmar una operación que no se haya guardado.

**Entrega verificable:** una programación genera notificaciones y un recolector autorizado puede confirmar el cierre por WhatsApp. Repetir el mismo mensaje no vuelve a acreditar puntos. La IA no asigna recolectores ni define horarios.

**Área propuesta:** módulos de WhatsApp e IA dentro de `backend/`. Coordinar con el responsable del backend; los modelos, permisos, estados y puntos tienen una única implementación compartida.

## Acuerdos iniciales — 30 minutos juntos

- [ ] Definir rutas y campos de los endpoints de solicitud, programación, cierre y consulta de puntos.
- [ ] Acordar roles, estados, transiciones y ejemplos JSON para avanzar con datos simulados.
- [ ] Elegir la estructura concreta de frontend y backend y delimitar archivos compartidos.
- [ ] El compañero 1 prepara el esqueleto del frontend y el responsable del backend prepara el suyo; integrar pronto esos cambios a `main` y actualizar las otras ramas.
- [ ] Asignar la edición de dependencias: compañero 1 en frontend y responsable del backend en backend. El compañero 3 comunica las dependencias que necesite.

## Orden de entrega

1. **Bases:** API mínima y datos semilla; interfaz con datos simulados; envío y recepción de WhatsApp.
2. **Integración:** crear solicitud → asignar y programar → notificar → cerrar → acreditar puntos.
3. **Demostración conjunta:** una unidad productiva solicita orgánicos y un hogar solicita reciclables; comprobar programación, historial, permisos y puntos.

Priorizar ese recorrido. Dejar analítica avanzada, optimización de rutas y gestión detallada de compostaje para después del MVP.

## Cómo usar la rama de cada persona

Clonar una vez y seleccionar la rama asignada; este ejemplo corresponde al compañero 1:

```bash
git clone https://github.com/AngelitoCastro/CicloBrisas.git
cd CicloBrisas
git fetch origin
git switch --track origin/equipo/portal-comunitario
```

Si ya tienes el repositorio, omite los primeros dos comandos. Para las otras personas, sustituye `equipo/portal-comunitario` por la rama de la tabla. Si la rama local ya existe, usa `git switch equipo/portal-comunitario`.

Guardar cambios en la rama asignada:

```bash
git status
git add ruta/del/archivo
git commit -m "Describe el cambio realizado"
git push
```

Sustituir `ruta/del/archivo` por los archivos que correspondan. Revisar los cambios antes de incluirlos y no subir credenciales ni datos personales reales.

Para incorporar cambios de `main`, con los cambios propios previamente guardados:

```bash
git fetch origin
git merge origin/main
```

Abrir un pull request desde la rama asignada hacia `main`, describiendo qué funciona y cómo se verificó. Integrar cambios pequeños con frecuencia para detectar conflictos pronto.

**Permisos:** crear ramas no otorga acceso de escritura. Para hacer push, cada compañero necesita estar agregado como colaborador del repositorio y haber aceptado la invitación. Los nombres de usuario de GitHub no se han proporcionado y esta distribución no modifica permisos.
