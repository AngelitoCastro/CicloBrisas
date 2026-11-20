---
name: ecoconecta-backend
description: Implementar o revisar FastAPI, PostgreSQL, permisos, solicitudes y puntos de EcoConecta. Usar al trabajar en las reglas RN-01 a RN-08 o los contratos de API del proyecto.
---

# Backend de EcoConecta

Leer [el plan y esquema propuesto](../../../plan_de_desarrollo_reglas_y_base_de_datos.md) y el código existente antes de cambiar contratos. El repositorio comenzó como documentación; comprobar qué está implementado. El SQL del plan es una propuesta, no una migración ejecutada.

## Invariantes del dominio

- Enrutar `ORGANICO` a Huerteros y `RECICLABLE` a Recicladores. Comprobar permisos y compatibilidad de roles en el servidor.
- Solo un coordinador humano autorizado programa: exigir coordinador, recolector compatible, fecha y hora. Acordar transiciones válidas para los seis estados documentados; no inferir que toda transición está permitida.
- Registrar actor, estado anterior, estado nuevo y fecha en el historial al cambiar estado.
- Cerrar y acreditar puntos en una misma transacción. Proteger contra cierres simultáneos o repetidos; leer la regla configurable aplicable y conservar evidencia del cálculo utilizado.
- Validar pesos y parámetros numéricos. No acreditar puntos antes de `RECOLECTADA`.
- Filtrar teléfono y dirección según propietario y perfiles autorizados. No confiar en que la interfaz o la IA hayan validado la operación.
- Precisar el comportamiento de `es_piloto` con el contrato acordado; el campo por sí solo no restringe acceso.

## Forma de trabajar y verificar

Definir ejemplos de petición, respuesta y error para los consumidores de la API. Mantener el servicio de cierre compartido entre panel y WhatsApp, sin duplicar la lógica de puntos. Coordinar cambios de dependencias y modelos con el compañero de integración.

Al modificar operaciones críticas, verificar permisos entre flujos, programación incompleta, historial, peso inválido y cierre repetido o concurrente. Usar PostgreSQL para comprobar comportamientos que dependan de transacciones y restricciones. Informar qué se ejecutó y qué sigue pendiente.
