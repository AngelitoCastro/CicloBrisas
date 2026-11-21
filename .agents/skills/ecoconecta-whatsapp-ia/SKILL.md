---
name: ecoconecta-whatsapp-ia
description: Implementar o revisar la integración de WhatsApp con Twilio y el asistente OpenAI de EcoConecta, incluyendo webhook, privacidad, notificaciones y cierres desde campo.
---

# WhatsApp e IA de EcoConecta

Leer [la arquitectura propuesta](../../../arquitectura_de_ia_y_flujo_bidireccional_whatsapp.md) y el servicio de solicitudes existente. La implementación usa Twilio WhatsApp y OpenAI: confirmar en documentación oficial la validación de `X-Twilio-Signature`, los modelos disponibles y los requisitos de Content SID antes de integrar; no asumir vigentes las decisiones de los documentos iniciales.

## Límites operativos

- La IA educa y propone una intención o extracción de campos. No asigna personas, define horarios, autoriza remitentes ni escribe directamente estados o puntos.
- Aceptar las intenciones `DUDA_AMBIENTAL`, `CIERRE_RECOLECCION`, `CONSULTA_ESTADO` y `OTRO` mediante un esquema validado. Usar números y valores nulos reales; el JSON descriptivo del documento no es un esquema listo para producción.
- Antes de cerrar, validar remitente autorizado, código, peso y estado mediante el backend. Invocar el mismo servicio transaccional usado por el panel. Si faltan datos, pedir aclaración sin confirmar un cierre.
- Consultar estados solo para solicitudes del remitente autenticado o perfiles autorizados; no confiar en un código público como autorización.

## Mensajería y privacidad

Validar `X-Twilio-Signature` contra la URL exacta y todos los parámetros del formulario con `RequestValidator`, y comprobar `AccountSid`. Usar `WEBHOOK_PUBLIC_URL` o reconstruir la URL pública con `X-Forwarded-Proto`/`X-Forwarded-Host` detrás de proxy; no fiarse de `request.url` en túneles. No existe desafío GET de Meta. Distinguir mensajes entrantes de callbacks de estado. Deduplicar por `MessageSid` con persistencia y estrategia de reintento para fallos parciales.

Comprobar consentimiento y elegibilidad del envío, ventana de conversación y Content SID cuando corresponda. Registrar por separado operación guardada y entrega de notificación para poder reintentar sin duplicar efectos.

Anonimizar nombres, teléfonos y direcciones antes de consultar al proveedor de IA; los mensajes libres también pueden incluirlos. Evitar que logs y errores expongan esos datos. No comunicar éxito al usuario antes de que el backend confirme la operación. Acordar acceso y conservación del historial.

## Verificación

Comprobar firma inválida, evento duplicado, salida de IA inválida, remitente ajeno, campos ausentes, proveedor caído y reintento después de un fallo parcial. Demostrar que un cierre repetido no duplica puntos. Usar dobles de proveedor para pruebas locales; realizar envíos reales solo dentro del alcance autorizado.
