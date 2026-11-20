---
name: ecoconecta-whatsapp-ia
description: Implementar o revisar la integración de WhatsApp Cloud API y el asistente de IA de EcoConecta, incluyendo webhook, privacidad, notificaciones y cierres desde campo.
---

# WhatsApp e IA de EcoConecta

Leer [la arquitectura propuesta](../../../arquitectura_de_ia_y_flujo_bidireccional_whatsapp.md) y el servicio de solicitudes existente. Confirmar en documentación oficial las versiones de Graph API, modelos disponibles y requisitos de plantillas antes de integrar; no asumir vigentes las versiones de los documentos iniciales.

## Límites operativos

- La IA educa y propone una intención o extracción de campos. No asigna personas, define horarios, autoriza remitentes ni escribe directamente estados o puntos.
- Aceptar las intenciones `DUDA_AMBIENTAL`, `CIERRE_RECOLECCION`, `CONSULTA_ESTADO` y `OTRO` mediante un esquema validado. Usar números y valores nulos reales; el JSON descriptivo del documento no es un esquema listo para producción.
- Antes de cerrar, validar remitente autorizado, código, peso y estado mediante el backend. Invocar el mismo servicio transaccional usado por el panel. Si faltan datos, pedir aclaración sin confirmar un cierre.
- Consultar estados solo para solicitudes del remitente autenticado o perfiles autorizados; no confiar en un código público como autorización.

## Mensajería y privacidad

Implementar tanto el desafío de verificación como la validación de firma del webhook usando el cuerpo original y el secreto correspondiente. Distinguir mensajes entrantes de eventos de entrega. Deduplicar por identificador del proveedor con persistencia y estrategia de reintento para fallos parciales.

Comprobar consentimiento y elegibilidad del envío, ventana de conversación y plantillas cuando corresponda. Registrar por separado operación guardada y entrega de notificación para poder reintentar sin duplicar efectos.

Anonimizar nombres, teléfonos y direcciones antes de consultar al proveedor de IA; los mensajes libres también pueden incluirlos. Evitar que logs y errores expongan esos datos. No comunicar éxito al usuario antes de que el backend confirme la operación. Acordar acceso y conservación del historial.

## Verificación

Comprobar firma inválida, evento duplicado, salida de IA inválida, remitente ajeno, campos ausentes, proveedor caído y reintento después de un fallo parcial. Demostrar que un cierre repetido no duplica puntos. Usar dobles de proveedor para pruebas locales; realizar envíos reales solo dentro del alcance autorizado.
