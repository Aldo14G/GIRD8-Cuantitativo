# PROJECT_CONTEXT.md
# Documento maestro de contexto — Pipeline NL 2024-2026
# Lee este archivo PRIMERO antes de cualquier acción en el proyecto.
# Última actualización: sincronizar con pipeline_state.json

---

## PROPÓSITO DE ESTE DOCUMENTO

Este archivo es la **memoria persistente del proyecto**. Cualquier LLM (OpenAI,
Claude, Gemini, Minimax) que tome el control del pipeline debe leerlo completo
antes de ejecutar cualquier acción. Es la única fuente de verdad sobre:
- Qué hace este proyecto
- En qué estado está ahorita
- Qué decisiones se tomaron y por qué
- Qué restricciones son inamovibles

---

## PREGUNTA CENTRAL DE INVESTIGACIÓN

> ¿Qué dependencias gubernamentales de Nuevo León han mejorado o empeorado
> su calidad de datos abiertos entre 2024 y 2026, y qué variables institucionales
> predicen ese cambio?

Esta pregunta NO cambia. Todo lo que hagas debe poder justificarse
como una contribución a responderla.

---

## ARQUITECTURA DEL SISTEMA

### Flujo de datos (Medallion)

```
CKAN API (catalogodatos.nl.gob.mx)
    │
    ▼
[src/extract/01_extract.py]  →  data/raw/   ← snapshots JSON + CSV plano
    │
    ▼
[src/evaluate/02_evaluate.py] →  data/processed/   ← scores de metadata + contenido + LLM
    │
    ▼
[src/longitudinal/03_longitudinal.py] → data/output/  ← deltas temporales + modelo OLS
```

### Tres capas de evaluación por dataset

| Capa | Qué evalúa | Cómo |
|------|-----------|------|
| 1 — Metadata | Campos del portal CKAN | Reglas Python deterministas |
| 2 — Contenido | Archivo CSV real descargado | DataQualityAnalyzer (herencia 2024) |
| 3 — Estándares | Criterios sectoriales + Open Data Index | LLM (provider agnóstico) |

### Pesos de scoring de metadata (NO modificar sin justificación)

```
completitud    25%
actualización  25%
accesibilidad  20%
documentación  20%
apertura       10%
```

### Modelo OLS (Gold)

Variable dependiente: `delta_quality_score` (cambio 2024→2026)

Predictores:
- X1: capacidad institucional (proxy: datasets publicados total)
- X2: frecuencia de actualización (proxy: días entre modificaciones)
- X3: antigüedad de adopción (proxy: fecha primer dataset)
- X4: proporción formato abierto (CSV+JSON / total recursos)
- X5: diversidad temática (grupos únicos / total datasets)

---

## PROVEEDOR LLM ACTIVO

<!-- ACTUALIZAR AQUÍ cuando cambies de proveedor -->
Proveedor actual: openai
Modelo actual:    gpt-4o-mini
Cambiado por:     [nombre o fecha]
Razón del cambio: [tokens agotados / costo / calidad]

### Historial de proveedores usados

| Fecha | Proveedor | Modelo | Módulo | Razón de cambio |
|-------|-----------|--------|--------|-----------------|
| -     | -         | -      | -      | inicio          |

---

## ESTADO ACTUAL DEL PIPELINE

<!-- Sincronizar con pipeline_state.json -->

| Módulo | Estado | Última ejecución | Datasets procesados |
|--------|--------|-----------------|---------------------|
| 01 — Extracción | ⏳ pendiente | — | 0 / 68 |
| 02 — Evaluación | ⏳ pendiente | — | 0 / 68 |
| 03 — Longitudinal | ⏳ pendiente | — | — |

### Datasets con errores conocidos
(Llenar durante ejecución)
- ninguno aún

---

## DECISIONES DE DISEÑO — NO REABRIR

Estas decisiones ya fueron tomadas. No proponer alternativas salvo que
haya una razón técnica crítica:

1. **Medallion data/raw/processed/output** — arquitectura de capas de datos, no cambiar nombres de directorios
2. **Herencia de Ricardo 2024** — `DataQualityAnalyzer` se mantiene, no reescribir desde cero
3. **OpenAI como default** — el proveedor LLM se cambia en config/settings.py o .env, no en el código
4. **Scores en rango [0.0, 1.0]** — escala fija, no cambiar sin migrar datos históricos
5. **Rate limiting de 0.4s** — respetuoso con el portal de NL, no bajar ese valor

---

## RESTRICCIONES OPERATIVAS

- **NUNCA** hardcodear API keys en ningún archivo
- **NUNCA** renombrar archivos de output sin actualizar los consumidores downstream
- **NUNCA** modificar el schema data/raw sin actualizar data/processed
- **SIEMPRE** preservar snapshots históricos — son la base del análisis longitudinal
- **SIEMPRE** actualizar pipeline_state.json después de cada ejecución exitosa

---

## ESTRUCTURA DEL PROYECTO

```
GIRD8-Cuantitativo/
├── src/                      # Código fuente
│   ├── extract/             # Módulo de extracción (Bronze)
│   ├── evaluate/            # Módulo de evaluación (Silver)
│   └── longitudinal/       # Módulo longitudinal (Gold)
├── config/                  # Configuración centralizada
│   ├── settings.py         # Variables de configuración
│   └── .env.example        # Template de variables de entorno
├── data/
│   ├── raw/                # Bronze (snapshots + CSVs)
│   ├── processed/          # Silver (evaluaciones)
│   └── output/            # Gold (modelos + reportes)
├── dashboards/              # Dashboards
│   ├── r/                 # Dashboard R
│   └── web/               # Dashboard Python/Web
├── tests/                   # Suite de pruebas
├── docs/                    # Documentación
│   ├── PROJECT_CONTEXT.md
│   ├── AGENTS.md
│   └── README.md
└── scripts/
    └── run_pipeline.py     # Orquestador
```

---

## GLOSARIO MÍNIMO

- **CKAN**: plataforma del portal de datos abiertos de NL
- **Snapshot**: captura completa del catálogo en una fecha específica
- **Delta**: diferencia de score entre snapshot 2024 y 2026
- **Dependencia**: organización gubernamental publicadora de datasets
- **Medallion Architecture**: patrón de capas (raw → processed → output)

---

## CÓMO RETOMAR EL TRABAJO (instrucciones para el LLM entrante)

1. Leer este archivo completo
2. Leer `config/pipeline_state.json` para conocer el estado exacto
3. Leer `docs/AGENTS.md` para entender las responsabilidades de cada agente
4. Identificar el módulo pendiente o fallido
5. Verificar que la API key del proveedor activo está en el entorno
6. Ejecutar solo el módulo necesario, no el pipeline completo
7. Actualizar `config/pipeline_state.json` al terminar
