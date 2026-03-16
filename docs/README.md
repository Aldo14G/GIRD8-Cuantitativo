# Evolución de la Calidad de Datos Abiertos en Nuevo León 2024–2026

[![GitHub Repo](https://img.shields.io/badge/GitHub-GIRD8--Cuantitativo-blue)](https://github.com/Aldo14G/GIRD8-Cuantitativo)
[![License: CC-BY-SA-4.0](https://img.shields.io/badge/License-CC--BY--SA--4.0-green)](https://creativecommons.org/licenses/by-sa/4.0/)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-yellow)](https://www.python.org/)

> Versión 2.0 — Integra y extiende `ricalanis/comovamoslabnle1` (2024)

---

[![Open Science](https://img.shields.io/badge/Open-Science-Repo-orange)](https://github.com/Aldo14G/GIRD8-Cuantitativo)

---

## Pregunta Central de Investigación

> ¿Qué dependencias gubernamentales han mejorado o empeorado su calidad de
> datos abiertos entre 2024 y 2026, y qué variables institucionales predicen ese cambio?

---

## Relación con el Proyecto Original (2024)

| Componente | Ricardo 2024 | Este proyecto 2026 |
|---|---|---|
| Evaluación técnica CSV | `technical.py` (DataQualityAnalyzer) | ✅ Heredado + extendido en `src/evaluate/` |
| Estándares sectoriales | `standards.py` (Perplexity API) | ✅ Migrado a OpenAI API |
| Criterios Open Data (10) | `open_data.py` (GPT-4) | ✅ Migrado a LLM configurable |
| Análisis longitudinal | ❌ No existía | ✅ Nuevo en `src/longitudinal/` |
| Modelo predictivo | ❌ No existía | ✅ OLS con 5 variables |
| Metadata del portal | ❌ No existía | ✅ CKAN API en `src/extract/` |

---

## Arquitectura Medallion

```
data/raw    →  data/processed  →  data/output
   │              │                  │
CKAN API      Metadata            Deltas
68 datasets   scores              + Modelo
              Contenido           OLS
              CSV + LLM
```

---

## Estructura del Proyecto

```
GIRD8-Cuantitativo/
│
├── src/                         # Código fuente
│   ├── extract/                # Módulo 1: Extracción Bronze
│   ├── evaluate/               # Módulo 2: Evaluación Silver
│   └── longitudinal/           # Módulo 3: Análisis Gold
│
├── config/                      # Configuración
│   ├── settings.py             # Variables centralizadas
│   └── .env.example            # Template de entorno
│
├── data/                       # Datos
│   ├── raw/                   # Bronze (snapshots + CSVs)
│   ├── processed/             # Silver (evaluaciones)
│   └── output/                # Gold (modelos + reportes)
│
├── dashboards/                  # Dashboards
│   ├── r/                     # Dashboard R
│   └── web/                   # Dashboard Python/Web
│
├── tests/                       # Pruebas (futuro)
├── docs/                        # Documentación
├── scripts/                     # Orquestación
│   └── run_pipeline.py
│
├── pyproject.toml              # Configuración Python
├── requirements.txt            # Dependencias
└── .gitignore
```

---

## Instalación

```bash
# Clonar el repositorio
git clone https://github.com/Aldo14G/GIRD8-Cuantitativo.git
cd GIRD8-Cuantitativo

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate  # Windows

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tu API key de OpenAI
```

---

## Ejecución

```bash
# Pipeline completo
python scripts/run_pipeline.py

# Solo extracción (Bronze)
python -m src.extract

# Solo evaluación (Silver)
python -m src.evaluate

# Solo análisis longitudinal (Gold)
python -m src.longitudinal

# Evaluación con estándares LLM
python -m src.evaluate --with-standards
```

---

## Tres Capas de Evaluación por Dataset

### Capa 1 — Metadata del Portal
| Dimensión | Peso | Qué mide |
|---|---|---|
| Completitud | 25% | Campos obligatorios presentes |
| Actualización | 25% | Frecuencia de actualización histórica |
| Accesibilidad | 20% | Formatos legibles por máquina |
| Documentación | 20% | Calidad de descripción y etiquetado |
| Apertura | 10% | Licencia abierta reconocida |

### Capa 2 — Contenido CSV (herencia de Ricardo)
Evalúa el archivo de datos real:
- completeness
- accuracy
- consistency
- uniqueness

### Capa 3 — Evaluación LLM
Estándares sectoriales aplicables + 10 criterios Open Data Index.
Proveedor configurable via variables de entorno.

---

## Variables Predictoras del Modelo OLS

| Variable | Proxy de |
|---|---|
| X1 Capacidad institucional | Datasets publicados total |
| X2 Frecuencia de actualización | Días entre modificaciones |
| X3 Antigüedad de adopción | Fecha primer dataset |
| X4 Proporción formato abierto | CSV+JSON / total recursos |
| X5 Diversidad temática | Grupos únicos / total datasets |

---

## Dashboards

### Dashboard Web (Python)
```bash
cd dashboards/web
python server.py --data-root ../../data
# Abre http://127.0.0.1:8765
```

### Dashboard R
Abre `dashboards/r/app.R` en RStudio o ejecuta:
```bash
Rscript dashboards/r/app.R
```

---

## Configuración de LLM

El proyecto soporta múltiples proveedores LLM. Configura mediante variables de entorno:

```bash
# OpenAI (default)
export LLM_PROVIDER=openai
export LLM_MODEL=gpt-4o-mini
export OPENAI_API_KEY=sk-...

# Anthropic
export LLM_PROVIDER=anthropic
export LLM_MODEL=claude-3-haiku-20240307
export ANTHROPIC_API_KEY=sk-ant-...

# Gemini
export LLM_PROVIDER=gemini
export LLM_MODEL=gemini-2.0-flash
export GEMINI_API_KEY=...
```

---

## Tecnologías

- **Python 3.11+**: Pipeline principal
- **Pandas/NumPy**: Análisis de datos
- **Statsmodels**: Modelo OLS
- **OpenAI/Anthropic/Gemini**: Evaluación de estándares
- **R + Shiny**: Dashboard alternativo
- **HTML/JS**: Dashboard web

---

## Antecedentes

- `ricalanis/comovamoslabnle1` — Pipeline de evaluación original (2024)
- `gomezmzn/comovamoslabnlv3` — Dashboard de visualización en R (2024)

---

## Licencia

Creative Commons CC BY-SA 4.0

---

## Contribuciones

Este es un proyecto de ciencia abierta. Las contribuciones son bienvenidas:

1. Fork del repositorio
2. Crear una rama feature (`git checkout -b feature/nueva-caracteristica`)
3. Commit con mensajes descriptivos
4. Push y crear Pull Request

---

## Contacto

Para preguntas sobre metodología de investigación, contactar al equipo del proyecto GIRD 8 - Cuantitativo.
