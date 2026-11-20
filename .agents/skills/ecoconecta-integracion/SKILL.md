---
name: ecoconecta-integracion
description: Verificar la integración del MVP de EcoConecta y preparar su demostración entre portal, coordinadores, API, PostgreSQL y WhatsApp. Usar para pruebas integrales o fallos entre frentes.
---

# Integración del MVP de EcoConecta

Leer [la distribución del equipo](../../../TAREAS_EQUIPO.md) y el escenario de demostración del [documento de alcance](../../../readme_oficial_ecoconecta_villas_de_san_pablo.md). Identificar servicios y comandos reales del repositorio; no anunciar una aplicación desplegada o ejecutable basándose solo en los documentos iniciales.

## Recorrido que debe funcionar

1. Una unidad productiva solicita orgánicos y aparece solo en el flujo autorizado de Huerteros.
2. Un coordinador registra encargado, fecha y hora; la programación persiste y se muestra al solicitante.
3. Se notifica al solicitante y al recolector; distinguir registro del envío, aceptación del proveedor y entrega cuando haya evidencia.
4. El recolector autorizado confirma por WhatsApp o se usa el cierre manual del panel. Se guardan peso, historial y puntos una sola vez.
5. Un hogar solicita reciclables y aparece en el flujo de Recicladores; verificar su asignación y programación.

Seguir cada operación desde interfaz o webhook hasta API, persistencia y respuesta. Verificar acceso entre roles y repetir el cierre. Incluir un fallo de notificación: la solicitud debe conservar un estado operativo coherente y permitir recuperación sin duplicar puntos.

## Resultado de la verificación

Indicar pasos ejecutados, resultado observado y evidencia disponible sin datos personales. Separar pruebas con datos simulados, proveedores sustituidos y conexiones reales. Si falta un servicio o credencial, completar lo comprobable y registrar exactamente la parte no validada; no inventar resultados.

Priorizar el recorrido del MVP sobre analítica, optimización de rutas y compostaje avanzado. Esta skill no otorga autorización para desplegar, enviar mensajes reales, modificar permisos o fusionar ramas fuera del alcance solicitado.
