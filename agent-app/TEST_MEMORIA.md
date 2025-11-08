# Test de Memoria Conversacional - Manuelita Assistant

## Objetivo
Verificar que el asistente recuerda información personal del usuario durante la conversación.

## Cambios Implementados

### 1. **Router Mejorado** (`agent.py` líneas 167-191)
El router ahora detecta preguntas personales/contextuales con patrones:
- "mi nombre"
- "te dije"
- "recuerda/recuerdas"
- "quién soy"
- "cómo me llamo"
- "me presenté"
- "soy [nombre]"
- "me llamo"
- "hola, me llamo"
- "mencioné"

Cuando detecta estas preguntas, usa el tool `"memory"` en lugar de RAG/Structured.

### 2. **Prompt Actualizado** (`agent.py` líneas 274-346)
El prompt ahora incluye:
- Instrucción explícita de recordar información personal (línea 280)
- Fallback específico para información personal (línea 308)
- Checklist que verifica memoria del usuario (línea 346)

### 3. **Manejo de Tool "Memory"** (`agent.py` líneas 237-248)
Cuando el router detecta pregunta personal:
- Solo usa memoria conversacional (sin RAG)
- Fuente: "memoria_conversacional"
- Contexto documental vacío (para que se enfoque en el historial)

## Secuencia de Prueba

### Test 1: Presentación y Recuerdo Básico

**Turno 1:**
```
Usuario: Hola, me llamo Esteban
```

**Comportamiento esperado:**
- Router detecta "me llamo" → Tool: `memory`
- Bot responde saludando por nombre
- Se guarda en memoria conversacional

**Turno 2:**
```
Usuario: ¿Te dije mi nombre?
```

**Comportamiento esperado:**
- Router detecta "te dije" + "mi nombre" → Tool: `memory`
- Bot consulta historial
- Responde: "Sí, Esteban, me comentaste que te llamas Esteban" (o similar)

### Test 2: Pregunta sobre Manuelita + Recuerdo Personal

**Turno 1:**
```
Usuario: Me llamo Esteban y trabajo en análisis de datos
```

**Turno 2:**
```
Usuario: ¿Qué productos ofrece Manuelita?
```
(Respuesta normal de RAG)

**Turno 3:**
```
Usuario: ¿Recuerdas mi nombre y profesión?
```

**Comportamiento esperado:**
- Router → Tool: `memory`
- Bot responde: "Claro, Esteban. Eres analista de datos..." (o similar)

### Test 3: Contexto de Conversación Previa

**Turno 1:**
```
Usuario: ¿Cuántas sedes tiene Manuelita?
```
(Respuesta RAG)

**Turno 2:**
```
Usuario: ¿Y en qué países?
```

**Comportamiento esperado:**
- Router puede usar RAG pero con memoria
- Bot entiende "Y" se refiere a las sedes mencionadas

## Verificación de Funcionamiento

### En Admin → Herramientas del Core
Verifica:
1. **Estado de Conversaciones Activas**: muestra conversaciones y turnos
2. **Memoria**: Max tokens y turnos configurados correctamente

### Logs del Sistema
Buscar en la consola:
```
INFO: Turno X añadido. Tokens: Y/20000
INFO: Cambiado a conversación 'Conversación 1'
```

### Estructura de Memoria
Cada turno guarda:
- `user_question`: pregunta del usuario
- `bot_response`: respuesta del bot
- `rag_context`: contexto RAG (si aplica)
- `sources`: fuentes utilizadas
- `tool_used`: "rag", "structured" o "memory"
- `timestamp`: momento de la interacción

## Solución de Problemas

### Si NO recuerda el nombre:

1. **Verificar que el router detecta la pregunta:**
   - Logs: buscar "Tool: memory"
   
2. **Verificar que hay contexto de memoria:**
   - En `app.py` línea 503: `memory_ctx = current_conv_memory.get_conversation_context()`
   - Debe contener los turnos previos

3. **Verificar prompt del LLM:**
   - El historial se inyecta en línea 331 de `agent.py`
   - Si está vacío, mostrará "(Primera interacción: no hay historial válido)"

### Si solo funciona a veces:

- Verifica que `use_memory=False` en `app.py` línea 104 pero se pasa `memory_context` manualmente
- La memoria se guarda en `current_conv_memory` (línea 508-514 de `app.py`)

## Parámetros Relevantes

**Configurables en Admin:**
- **Max Tokens Memoria**: 20000 por defecto (línea 283-329 `app.py`)
- **Max Turnos Memoria**: 50 por defecto

**No configurables:**
- Token estimation: ~4 caracteres = 1 token
- FIFO: turnos antiguos se eliminan automáticamente

## Referencias

- `memory.py`: Sistema de memoria conversacional FIFO
- `agent.py`: Router, prompt y generación de respuesta
- `app.py`: Integración con Streamlit y gestión de conversaciones
