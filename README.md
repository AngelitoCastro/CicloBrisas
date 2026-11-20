# EcoConecta — Villas de San Pablo

Documentación del MVP comunitario para coordinar la recolección de residuos orgánicos y reciclables en Villas de San Pablo, Barranquilla.

**Estado del repositorio:** contiene especificaciones y un plan de desarrollo. Todavía no incluye la aplicación, archivos Docker, plantilla `.env.example` ni datos semilla. Las reglas y los comandos de ejecución descritos en los documentos son objetivos de implementación; no acreditan funcionalidades construidas o probadas.

## Documentos del equipo

| Documento | Contenido y uso |
| --- | --- |
| [Presentación y alcance del MVP](readme_oficial_ecoconecta_villas_de_san_pablo.md) | Propósito, actores, arquitectura, stack propuesto, reglas RN-01 a RN-08 y escenario de demostración. Leer primero. |
| [Plan de desarrollo, reglas y base de datos](plan_de_desarrollo_reglas_y_base_de_datos.md) | Cronograma por frentes, esquema SQL propuesto y lista de verificación de reglas operativas. |
| [Guía de interfaz e identidad visual](gu_a_de_implementaci_n_ui_e_identidad_visual.md) | Colores, tipografías, accesibilidad y especificaciones de las tres vistas principales. |
| [Arquitectura de IA y WhatsApp](arquitectura_de_ia_y_flujo_bidireccional_whatsapp.md) | Notificaciones, webhook, clasificación de intenciones y propuesta de prompt del asistente. |

## Análisis de la documentación

Los cuatro documentos coinciden en separar los flujos orgánico y reciclable, reservar la asignación y programación a coordinadores humanos, usar WhatsApp para el trabajo en campo y acreditar puntos después de confirmar la recolección. La interfaz diferencia el portal comunitario y los dos paneles de coordinación.

Antes de implementar, el equipo debe resolver estos puntos:

1. **Requisitos de referencia:** los textos citan un reto oficial, sus secciones 8 y 9 y un manual de marca que no están incluidos en este repositorio. La autorización del stack y el cumplimiento de esas fuentes quedan pendientes de contrastar.
2. **Estados de solicitudes:** el esquema SQL contempla `RECIBIDA`, `EN_REVISION`, `ASIGNADA`, `PROGRAMADA`, `RECOLECTADA` y `CANCELADA`; la guía visual describe solo cuatro. Definir transiciones permitidas, permisos y presentación de todos los estados.
3. **Contrato de IA:** el flujo de entrada enumera tres intenciones y el prompt añade `OTRO`. El ejemplo de salida mezcla descripciones con tipos; hace falta un esquema validable con enumeraciones, números y valores `null` reales. Configurar un prompt no equivale a entrenar un modelo.
4. **Privacidad:** los mensajes libres pueden contener nombres, teléfonos o direcciones. Definir cómo anonimizar antes de consultar la IA, así como acceso y conservación del historial de mensajes.
5. **Cierre y puntos:** especificar autenticación del webhook, deduplicación de mensajes y cierre transaccional para evitar acreditar puntos dos veces. Validar peso, remitente autorizado y estado previo en el backend, sin delegar esas decisiones a la IA.
6. **Integraciones y versiones:** confirmar modelos disponibles, versión de Graph API, requisitos de plantillas de WhatsApp y versión de Tailwind antes de implementar. Las referencias de los documentos no se han verificado contra los proveedores.
7. **Piloto y reglas de puntos:** precisar si `es_piloto` solo etiqueta cuentas o restringe acceso; definir qué regla activa aplica a cada combinación de flujo y generador y conservar la regla usada en cada cierre.

## Acceso para compañeros

Los documentos pueden leerse desde este índice en GitHub o descargarse clonando el repositorio:

```bash
git clone https://github.com/AngelitoCastro/CicloBrisas.git
cd CicloBrisas
```

El repositorio es público al momento de publicar esta documentación. Para aportar cambios directamente se requieren permisos de colaboración; también se pueden proponer cambios mediante un fork y un pull request. No incluir credenciales ni datos personales reales en los archivos.
