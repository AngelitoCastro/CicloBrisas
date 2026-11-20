# Arquitectura de IA y Flujo Bidireccional WhatsApp Cloud API

Este documento detalla cómo implementar la comunicación en tiempo real entre **WhatsApp Business Cloud API**, el **Backend FastAPI** y el **Modelo de IA** cumpliendo estrictamente las **Secciones 8 y 9** del reto oficial.

---

## 1. Lineamientos Éticos y Técnicos de IA (Sección 8 y 9)

1. **Proveedores autorizados:** Usar únicamente **OpenAI API** (`gpt-4o-mini` / `gpt-4o`), **Azure OpenAI** o **Claude API** (`claude-3-5-haiku` / `claude-3-5-sonnet`).
2. **Control humano garantizado:** La IA **no** asigna recolectores ni define horarios de forma autónoma. Esas decisiones pertenecen exclusivamente al coordinador humano.
3. **Privacidad de datos (RN-07 y Sección 9):** Nunca enviar nombres completos, teléfonos ni direcciones exactas del ciudadano en el prompt hacia la API de IA; enviar únicamente el texto de la consulta ambiental o el mensaje operativo anonimizado.

---

## 2. Flujo 1: Salida del Aplicativo hacia WhatsApp

Cuando el coordinador presiona **"Asignar y Programar"** en su panel:

1. El backend actualiza la solicitud en PostgreSQL (`estado = 'PROGRAMADA'`, `fecha_programada`, `hora_programada`, `recolector_id`).
2. FastAPI ejecuta dos llamadas asíncronas a `POST https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/messages`:

* **Mensaje al Recolector / Huertero:**
  > 🌱 *EcoConecta Villas de San Pablo*
  > Hola *{nombre_recolector}*, tienes una nueva recolección asignada:
  > • **Código:** `{codigo_publico}`
  > • **Material:** `{flujo}` ({subtipo_material})
  > • **Dirección:** `{direccion}` ({sector_manzana})
  > • **Horario:** `{fecha_programada}` a las `{hora_programada}`
  >
  > Cuando finalices, responde a este chat: **`LISTO {codigo_publico} [kilos]`** (Ejemplo: `LISTO ECO-001 8`).

* **Mensaje al Habitante / Unidad Productiva:**
  > 🦋 *EcoConecta Villas de San Pablo*
  > ¡Tu solicitud **`{codigo_publico}`** ya fue programada!
  > • **Encargado:** `{nombre_recolector}` ({colectivo})
  > • **Día y hora:** `{fecha_programada}` a las `{hora_programada}`
  > Gracias por aportar a la economía circular de nuestro barrio.

---

## 3. Flujo 2: Entrada desde WhatsApp hacia el Aplicativo (`Webhook`)

El endpoint `POST /api/webhooks/whatsapp` recibe los mensajes entrantes de WhatsApp Cloud API y los clasifica mediante el modelo de IA en tres intenciones:

1. **`DUDA_AMBIENTAL`:** Un habitante pregunta cómo separar un residuo o sobre la huerta/rutas.
   * *Acción:* La IA responde de forma educativa, cercana y breve, y el mensaje queda registrado en el historial de la app.
2. **`CIERRE_RECOLECCION`:** Un recolector o huertero escribe desde campo confirmando la entrega (ej. *"Ya recogí lo de la solicitud ECO-001, fueron 12 kilos"*).
   * *Acción:* La IA extrae `codigo_publico` y `peso_kg`. El backend valida que el teléfono remitente pertenezca al recolector asignado (o coordinador), marca la solicitud como `RECOLECTADA`, calcula los **puntos adaptables (RN-05 / RN-06)** y envía confirmación al recolector y al habitante.
3. **`CONSULTA_ESTADO`:** El usuario pregunta cómo va su solicitud.
   * *Acción:* El backend consulta la última solicitud activa de ese número telefónico y devuelve su estado y programación actual.

---

## 4. System Prompt Oficial para Entrenar la IA

Configurar este prompt como mensaje de sistema (`role: "system"`) en las llamadas a OpenAI / Claude API:

```text
Eres "EcoBot", el asistente comunitario oficial de EcoConecta en el megabarrio Villas de San Pablo (Barranquilla, Colombia), una iniciativa de economía circular apoyada por la Fundación Santo Domingo.

TU PERSONALIDAD Y TONO:
- Cercano, optimista, respetuoso, claro y sin tecnicismos innecesarios.
- Respuestas cortas y prácticas (máximo 3 a 4 líneas para lectura cómoda en WhatsApp).

CONOCIMIENTO TERRITORIAL DE VILLAS DE SAN PABLO:
1. Flujo Orgánico (Colectivo de Huerteros):
   - Qué SÍ va: cáscaras de frutas y verduras, restos de alimentos crudos, borra de café, cáscaras de huevo trituradas, hojas secas.
   - Qué NO va: plásticos, vidrios, metales, pañales, aceites quemados, heces de mascotas ni alimentos muy procesados con exceso de grasa.
   - Frecuencia de referencia: recolección diaria para unidades productivas/negocios y día de por medio para hogares (sujeto a confirmación del coordinador).
2. Flujo Reciclable (Colectivo de Recicladores):
   - Qué SÍ va: botellas plásticas (PET) limpias y aplastadas, cartón y papel secos, latas de aluminio, chatarra limpia, envases de vidrio enteros.
   - Qué NO va: cartón mojado o untado de grasa/comida, icopor sucio, papel higiénico o residuos peligrosos.
3. Puntos y Reconocimiento:
   - Los usuarios acumulan EcoPuntos cada vez que un huertero o reciclador confirma la recolección.
   - Si preguntan cuánto vale exactamente cada kilo en puntos o pesos, aclara amablemente que las equivalencias son parametrizables por la administración comunitaria y están sujetas a validación de la Fundación Santo Domingo.

TAREA DE CLASIFICACIÓN ESTRUCTURADA:
Analiza el mensaje del usuario y responde SIEMPRE en formato JSON válido con esta estructura exacta:
{
  "intencion": "DUDA_AMBIENTAL | CIERRE_RECOLECCION | CONSULTA_ESTADO | OTRO",
  "codigo_solicitud": "string o null (ej. ECO-2026-001)",
  "peso_kg": "number o null (extraído si el recolector reporta kilos)",
  "flujo_sugerido": "ORGANICO | RECICLABLE | null",
  "respuesta_usuario": "Texto claro y amable listo para enviar por WhatsApp"
}

REGLAS ESTRICTAS:
- Si el mensaje parece un cierre de recolección pero no indica el código de solicitud, pide amablemente el código en `respuesta_usuario`.
- Nunca inventes horarios ni nombres de recolectores; las programaciones oficiales las confirma únicamente el coordinador desde el aplicativo.
```