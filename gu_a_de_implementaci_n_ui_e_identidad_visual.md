# Guía de Implementación UI e Identidad Visual — EcoConecta

Basado en el **Manual de Identidad Visual EcoConecta Villas de San Pablo**, este documento estandariza los colores, tipografías y componentes para garantizar coherencia entre la vista móvil comunitaria y los paneles de coordinadores.

---

## 1. Tokens de Diseño CSS (Corregidos)

Copiar este bloque en `globals.css` o `index.css`:

```css
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Poppins:wght@600;700&display=swap');

:root {
  --eco-forest: #063B2E;      /* Principal: barra superior, encabezados y textos destacados */
  --eco-green: #168A2E;       /* Acciones principales, botones positivos, estados activos */
  --eco-leaf: #65A90A;        /* Acentos naturales, etiquetas ambientales */
  --eco-teal: #0A9B70;        /* Conexión, enlaces y datos secundarios */
  --eco-yellow: #F6C400;      /* Puntos, logros, llamados de atención */
  --eco-orange: #F28C00;      /* Acento secundario para insignias (mariposa) */
  --eco-charcoal: #202522;    /* Texto principal sobre fondos claros */
  --eco-background: #F2F5F2;  /* Fondo general de pantallas */
  --eco-white: #FFFFFF;       /* Fondos de tarjetas y descanso visual */

  --font-heading: 'Poppins', 'Arial', sans-serif;
  --font-body: 'Inter', 'Arial', sans-serif;
}

body {
  background-color: var(--eco-background);
  color: var(--eco-charcoal);
  font-family: var(--font-body);
}

h1, h2, h3 {
  font-family: var(--font-heading);
  color: var(--eco-forest);
}
```

### Configuración para `tailwind.config.js`

```javascript
module.exports = {
  theme: {
    extend: {
      colors: {
        eco: {
          forest: '#063B2E',
          green: '#168A2E',
          leaf: '#65A90A',
          teal: '#0A9B70',
          yellow: '#F6C400',
          orange: '#F28C00',
          charcoal: '#202522',
          bg: '#F2F5F2',
        },
      },
      fontFamily: {
        heading: ['Poppins', 'Arial', 'sans-serif'],
        body: ['Inter', 'Arial', 'sans-serif'],
      },
    },
  },
};
```

---

## 2. Reglas Obligatorias de Marca y Accesibilidad

1. **Logotipo oficial:**
   * Usar el archivo gráfico original (`logo-ecoconecta.png` / `.svg`) sobre fondo blanco o muy claro (`#FFFFFF` o `#F2F5F2`).
   * Ancho mínimo recomendado en web/móvil: `220 px` (o versión reducida autorizada en barras móviles estrechas, sin deformar ni recolorear).
2. **Proporción cromática:**
   * ~40% verdes (`#063B2E`, `#168A2E`), ~30% blanco/neutros (`#FFFFFF`, `#F2F5F2`), ~20% acentos verdes (`#65A90A`, `#0A9B70`), y máximo 10% amarillo/naranja (`#F6C400`, `#F28C00`).
3. **Estados siempre multimodales (No depender solo del color):**
   * Toda insignia de estado debe mostrar **Icono + Texto claro + Color**:
     * `RECIBIDA`: Reloj + *"Recibida"* (Gris/Carbón)
     * `ASIGNADA`: Usuario + *"Asignada"* (Verde Turquesa `#0A9B70`)
     * `PROGRAMADA`: Calendario + *"Programada"* (Amarillo Solar `#F6C400` con texto `#063B2E`)
     * `RECOLECTADA`: Check doble + *"Recolectada"* (Verde Eco `#168A2E` con texto blanco)
4. **Lenguaje cercano y verbos de acción:**
   * Usar palabras claras para la comunidad: **Solicitar, Clasificar, Programar, Recoger, Confirmar, Reconocer**. Evitar tecnicismos en pantallas comunitarias.

---

## 3. Especificación de las 3 Vistas de Interfaz

### Vista 1: Portal Comunitario (Habitantes y Unidades Productivas)
* **Barra superior:** Fondo Verde Bosque (`#063B2E`), saludo al vecino y badge de puntos en Amarillo Solar (`#F6C400`).
* **Bloque principal:** Dos botones gigantes de acción inmediata:
  1. **"Solicitar Recolección"** (Verde Eco `#168A2E`, texto blanco).
  2. **"¿Cómo separar?"** (Fondo blanco, borde Verde Bosque `#063B2E`).
* **Tarjeta de Solicitud Activa:** Muestra código (`ECO-2026-001`), estado con icono, y cuando está programada resalta en un recuadro claro: **Nombre del recolector, día y hora acordados**.

### Vista 2: Panel Coordinador de Recicladores (Ultra-Intuitivo)
* Diseñado para operación rápida con una mano en celular o tablet.
* **Sin tablas densas:** Lista de tarjetas grandes de solicitudes `RECICLABLE` pendientes.
* **Flujo de 2 toques dentro de cada tarjeta:**
  1. Selector visual con foto/nombre del **Reciclador** + selector rápido de **Día y Hora**.
  2. Botón ancho (`height: 56px`) en Verde Eco (`#168A2E`): **"Asignar y Enviar a WhatsApp"**. Al tocarlo, guarda la programación y dispara automáticamente el mensaje al WhatsApp del reciclador y del vecino.

### Vista 3: Panel Coordinador de Huerteros (Gestión Completa)
* Aprovecha la mayor familiaridad tecnológica del equipo de huerta.
* **Filtros superiores:** Por estado (`Recibida`, `Programada`, `Recolectada`), por tipo de generador (`Unidad Productiva` —ruta diaria— vs. `Hogar` —día de por medio—) y por fecha.
* **Tabla operativa + Modal de Cierre:** Permite asignar huertero, programar horario, enviar notificación por WhatsApp y registrar el peso recolectado (kg) para acreditar puntos al usuario.