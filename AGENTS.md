# Instrucciones para agentes — EcoConecta

Este repositorio comenzó con especificaciones del MVP; comprobar los archivos existentes antes de asumir que hay una aplicación, servicios Docker o pruebas disponibles. Consultar `README.md` y `TAREAS_EQUIPO.md` para alcance y responsables.

## Skills del proyecto

Las skills están versionadas en `.agents/skills/`. Leer el `SKILL.md` que corresponda antes de trabajar en ese frente; cargar varios solo si la tarea cruza sus responsabilidades. Se pueden solicitar explícitamente por nombre, por ejemplo `$ecoconecta-backend`.

| Trabajo solicitado | Skill que se debe leer |
| --- | --- |
| FastAPI, PostgreSQL, permisos, estados, puntos y contratos de API | `.agents/skills/ecoconecta-backend/SKILL.md` |
| Portal, componentes compartidos y paneles de coordinación | `.agents/skills/ecoconecta-ui/SKILL.md` |
| Webhook, notificaciones, clasificación de IA y cierre por WhatsApp | `.agents/skills/ecoconecta-whatsapp-ia/SKILL.md` |
| Pruebas del recorrido completo y diagnóstico entre servicios | `.agents/skills/ecoconecta-integracion/SKILL.md` |

Para otros agentes que no descubran `.agents/skills`, abrir esos mismos archivos como instrucciones. No requieren plugins de pago ni paquetes adicionales por sí mismas; la aplicación sí requerirá sus dependencias y credenciales cuando se implemente.

## Coordinación del equipo

- Trabajar en la rama asignada; consultar las correspondencias en `TAREAS_EQUIPO.md`. No cambiar automáticamente de rama por el nombre de una skill.
- Reservar `main` como base de integración y proponer cambios de implementación mediante pull requests. Las tareas de mantenimiento o publicación expresamente solicitadas por el usuario siguen su autorización.
- El compañero 1 coordina dependencias y base de frontend; el responsable del backend coordina dependencias, modelos y contratos de backend. Compartir cambios necesarios antes de editar esos archivos entre frentes.
- Las skills no autorizan por sí solas publicar, desplegar, enviar mensajes ni cambiar permisos.
- Usar documentación oficial para confirmar APIs y versiones al implementar. Las fuentes externas del reto y el manual de marca todavía deben contrastarse.

Mantener las decisiones operativas bajo control humano, proteger datos personales y acreditar puntos únicamente tras un cierre confirmado. Detalles y verificaciones específicas se encuentran en las skills correspondientes.
