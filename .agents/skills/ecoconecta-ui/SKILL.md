---
name: ecoconecta-ui
description: Construir o revisar el portal comunitario y los paneles de coordinadores de EcoConecta en React o Next.js con Tailwind, identidad visual y accesibilidad móvil.
---

# Interfaces de EcoConecta

Leer [la guía visual](../../../gu_a_de_implementaci_n_ui_e_identidad_visual.md) y los contratos de API existentes. Conservar el framework y versiones que el equipo haya elegido; verificar la versión de Tailwind antes de copiar su configuración.

## Portal y paneles

- Portal: educación, solicitud, seguimiento de encargado/día/hora y puntos. Diseñar primero para móvil.
- Recicladores: tarjetas grandes para solicitudes reciclables y acción clara de asignar/programar. Mantener controles de acción de al menos 56 px según el plan.
- Huerteros: tabla operativa con filtros y cierre con peso. Permitir uso en tablet y móvil sin perder acciones.
- Compartir componentes, tokens y cliente de API entre los dos frentes. El compañero 1 mantiene la base del frontend; coordinar archivos compartidos antes de modificarlos.

## Reglas visuales y de datos

Usar los colores y tipografías de la guía. Los archivos de logo y el manual original no están incluidos inicialmente: no inventar un logo oficial; usar un título de texto hasta recibir el recurso.

Mostrar estados con icono, texto y color, incluyendo estados que faltan en la guía visual cuando estén en el contrato. Comprobar contraste, etiquetas de formularios, foco visible y navegación por teclado.

Mostrar carga, errores y estados vacíos. Al guardar, reflejar la respuesta del servidor; distinguir una programación guardada de una notificación fallida. No presentar datos simulados como confirmaciones reales. La API decide permisos, transiciones y puntos; las validaciones de interfaz ayudan al usuario.

Los puntos llevan la aclaración «Cálculo parametrizable sujeto a validación FSD». No mostrar teléfono ni dirección a perfiles no autorizados.

## Verificación

Probar el recorrido del perfil modificado, errores de API y presentación móvil. Verificar que programar exige encargado, día y hora; comprobar visualmente icono/texto/color, legibilidad y controles. Si no hay API, aislar los datos simulados y describir qué falta integrar.
