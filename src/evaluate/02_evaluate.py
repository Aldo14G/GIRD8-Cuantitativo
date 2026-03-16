"""
MÓDULO 2 — EVALUACIÓN SILVER
==============================
Proyecto: Evolución de Calidad de Datos Abiertos NL 2024-2026

Integra y extiende el trabajo original de Ricardo Alanis (2024):
    ricalanis/comovamoslabnle1

CAPAS DE EVALUACIÓN:
┌─────────────────────────────────────────────────────────────────┐
│ CAPA A — Metadata Portal (nueva 2026)                           │
│   Evalúa: completitud, documentación, licencia,                │
│   categorización, actualización declarada                       │
├─────────────────────────────────────────────────────────────────┤
│ CAPA B — Contenido CSV (DataQualityAnalyzer de Ricardo 2024)    │
│   Evalúa: completeness, accuracy, consistency, uniqueness       │
├─────────────────────────────────────────────────────────────────┤
│ CAPA C — Estándares Internacionales                             │
│   Proveedor LLM configurable via env vars:                     │
│     LLM_PROVIDER = openai | anthropic | gemini | minimax       │
│     LLM_MODEL    = nombre del modelo                            │
└─────────────────────────────────────────────────────────────────┘

Score final = promedio ponderado de las 3 capas.
Para datasets sin CSV descargado, se usa solo Capa A (penalizado).

CAMBIO DE PROVEEDOR LLM:
    Edita las variables de entorno antes de correr:
    LLM_PROVIDER=anthropic LLM_MODEL=claude-haiku-4-5-20251001 python 02_evaluate.py --with-standards
    LLM_PROVIDER=gemini    LLM_MODEL=gemini-2.0-flash          python 02_evaluate.py --with-standards
    LLM_PROVIDER=openai    LLM_MODEL=gpt-4o-mini               python 02_evaluate.py --with-standards
"""

from __future__ import annotations

import ast
import glob
import json
import os
import re
import shutil
import sys
import time
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd
import requests


# ══════════════════════════════════════════════════════════════════
# CONFIGURACIÓN LLM — provider-agnostic
# Cambia solo las variables de entorno, no el código.
# ══════════════════════════════════════════════════════════════════

# Proveedores soportados y sus modelos default
_LLM_DEFAULTS: dict[str, str] = {
    "openai":    "gpt-4o-mini",
    "anthropic": "claude-haiku-4-5-20251001",
    "gemini":    "gemini-2.0-flash",
    "minimax":   "MiniMax-Text-01",
}

LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai").lower().strip()
LLM_MODEL:    str = os.getenv("LLM_MODEL", _LLM_DEFAULTS.get(LLM_PROVIDER, "gpt-4o-mini"))

_LLM_SYSTEM_PROMPT = (
    "Eres un experto en estándares de datos abiertos gubernamentales de México. "
    "Responde ÚNICAMENTE con JSON válido estricto, sin texto adicional, sin markdown."
)


# ══════════════════════════════════════════════════════════════════
# CAPA LLM — llamada única provider-agnostic
# ══════════════════════════════════════════════════════════════════

def _call_llm(prompt: str, retries: int = 3, retry_delay: float = 5.0) -> str:
    """
    Ejecuta la llamada al LLM según LLM_PROVIDER activo.
    Retorna el texto de respuesta o "" en caso de fallo.
    Reintentos automáticos ante errores de red o rate-limit.
    """
    for attempt in range(1, retries + 1):
        try:
            text = _dispatch_llm(prompt)
            if text:
                return text
        except Exception as exc:
            print(f"    [LLM/{LLM_PROVIDER}] Intento {attempt}/{retries}: {exc}")
            if attempt < retries:
                time.sleep(retry_delay)

    print(f"    [LLM/{LLM_PROVIDER}] FALLO tras {retries} intentos.")
    return ""


def _dispatch_llm(prompt: str) -> str:
    """Enruta la llamada al proveedor configurado."""
    if LLM_PROVIDER == "openai":
        return _call_openai(prompt)
    elif LLM_PROVIDER == "anthropic":
        return _call_anthropic(prompt)
    elif LLM_PROVIDER == "gemini":
        return _call_gemini(prompt)
    elif LLM_PROVIDER == "minimax":
        return _call_minimax(prompt)
    else:
        raise ValueError(
            f"Proveedor '{LLM_PROVIDER}' no soportado. "
            f"Usa: {list(_LLM_DEFAULTS.keys())}"
        )


def _call_openai(prompt: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY no configurada")
    r = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": LLM_MODEL,
            "temperature": 0.2,
            "max_tokens": 1000,
            "messages": [
                {"role": "system", "content": _LLM_SYSTEM_PROMPT},
                {"role": "user",   "content": prompt},
            ],
        },
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def _call_anthropic(prompt: str) -> str:
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY no configurada")
    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        },
        json={
            "model": LLM_MODEL,
            "max_tokens": 1000,
            "system": _LLM_SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["content"][0]["text"]


def _call_gemini(prompt: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        raise EnvironmentError("GEMINI_API_KEY no configurada")
    full_prompt = f"{_LLM_SYSTEM_PROMPT}\n\n{prompt}"
    r = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{LLM_MODEL}:generateContent",
        params={"key": api_key},
        headers={"Content-Type": "application/json"},
        json={"contents": [{"parts": [{"text": full_prompt}]}]},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["candidates"][0]["content"]["parts"][0]["text"]


def _call_minimax(prompt: str) -> str:
    api_key = os.getenv("MINIMAX_API_KEY", "")
    if not api_key:
        raise EnvironmentError("MINIMAX_API_KEY no configurada")
    r = requests.post(
        "https://api.minimax.chat/v1/text/chatcompletion_v2",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": LLM_MODEL,
            "temperature": 0.2,
            "max_tokens": 1000,
            "messages": [
                {"role": "system", "content": _LLM_SYSTEM_PROMPT},
                {"role": "user",   "content": prompt},
            ],
        },
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def _parse_llm_json(text: str) -> dict[str, Any]:
    """Extrae JSON de la respuesta LLM, tolerante a markdown."""
    cleaned = re.sub(r"```(?:json)?|```", "", text).strip()
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        return json.loads(match.group())
    return json.loads(cleaned)


# ══════════════════════════════════════════════════════════════════
# CAPA A — Evaluación de Metadata (nueva 2026)
# ══════════════════════════════════════════════════════════════════

OPEN_LICENSES    = {"cc-by", "cc-zero", "odc-by", "odc-pddl", "cc-by-sa", "odc-odbl"}
OPEN_FORMATS     = {"CSV", ".CSV", "JSON", "XML", "GEOJSON"}
MACHINE_READABLE = {"CSV", ".CSV", "JSON", "XML", "GEOJSON", "XLSX"}


def score_metadata(row: pd.Series, reference_date: datetime) -> dict:
    """
    Evalúa el registro del portal CKAN en 5 dimensiones.
    Retorna scores normalizados 0-1 por dimensión.
    """
    # D1: Completitud del registro
    checks_completitud = [
        bool(str(row.get("title", "")).strip()),
        bool(row.get("has_description")),
        bool(row.get("org_name")),
        int(row.get("num_resources", 0)) > 0,
        int(row.get("num_tags", 0)) >= 2,
        int(row.get("num_groups", 0)) > 0,
        int(row.get("description_length", 0)) > 50,
    ]
    d1_completitud = sum(checks_completitud) / len(checks_completitud)

    # D2: Frecuencia de actualización
    modified = row.get("metadata_modified")
    if pd.isna(modified) or modified is None:
        d2_actualizacion = 0.0
    else:
        if hasattr(modified, "tzinfo") and modified.tzinfo is None:
            modified = modified.replace(tzinfo=timezone.utc)
        days = max((reference_date - modified).days, 0)
        if   days <= 90:   d2_actualizacion = 1.00
        elif days <= 180:  d2_actualizacion = 0.85
        elif days <= 365:  d2_actualizacion = 0.65
        elif days <= 730:  d2_actualizacion = 0.40
        elif days <= 1095: d2_actualizacion = 0.20
        else:              d2_actualizacion = 0.05

    # D3: Accesibilidad de formatos
    formats = row.get("formats", [])
    if not formats:
        d3_accesibilidad = 0.0
    else:
        fmt_scores = []
        for fmt in formats:
            fu = str(fmt).upper()
            if fu in OPEN_FORMATS:              fmt_scores.append(1.0)
            elif fu in MACHINE_READABLE:        fmt_scores.append(0.7)
            elif fu in {"PDF", "DOC", "DOCX"}:  fmt_scores.append(0.2)
            else:                               fmt_scores.append(0.1)
        d3_accesibilidad = float(np.mean(fmt_scores))

    # D4: Calidad de documentación
    desc_len = int(row.get("description_length", 0))
    num_tags = int(row.get("num_tags", 0))
    desc_score = min(np.log1p(desc_len) / np.log1p(500), 1.0)
    if   num_tags == 0:  tag_score = 0.0
    elif num_tags <= 2:  tag_score = 0.4
    elif num_tags <= 8:  tag_score = 1.0
    else:                tag_score = 0.8
    d4_documentacion = desc_score * 0.6 + tag_score * 0.4

    # D5: Apertura legal
    lic = str(row.get("license_id", "")).lower()
    if row.get("isopen") or lic in OPEN_LICENSES:    d5_apertura = 1.0
    elif lic and lic not in {"nan", "none", ""}:     d5_apertura = 0.5
    else:                                            d5_apertura = 0.0

    composite = (
        d1_completitud   * 0.25 +
        d2_actualizacion * 0.25 +
        d3_accesibilidad * 0.20 +
        d4_documentacion * 0.20 +
        d5_apertura      * 0.10
    )

    return {
        "meta_completitud":   round(d1_completitud,   4),
        "meta_actualizacion": round(d2_actualizacion, 4),
        "meta_accesibilidad": round(d3_accesibilidad, 4),
        "meta_documentacion": round(d4_documentacion, 4),
        "meta_apertura":      round(d5_apertura,      4),
        "meta_score":         round(composite,         4),
    }


# ══════════════════════════════════════════════════════════════════
# CAPA B — DataQualityAnalyzer (Ricardo Alanis, 2024)
# Integrado sin modificar la lógica original
# ══════════════════════════════════════════════════════════════════

class DataQualityAnalyzer:
    """
    Clase original de Ricardo Alanis (ricalanis/comovamoslabnle1, 2024).
    Evalúa el CONTENIDO de archivos CSV en 4 dimensiones:
      completeness, accuracy, consistency, uniqueness.

    Integrada sin cambios estructurales para mantener
    compatibilidad con el baseline 2024.
    """

    def __init__(self, file_path: str):
        self.file_path = file_path
        if file_path.endswith(".csv"):
            self.df = self._read_csv_robust(file_path)
        elif file_path.endswith((".xlsx", ".xls")):
            self.df = pd.read_excel(file_path)
        else:
            raise ValueError("Formato no soportado. Use CSV o Excel.")

        self.total_rows    = len(self.df)
        self.total_columns = len(self.df.columns)
        self.columns       = list(self.df.columns)

    @staticmethod
    def _read_csv_robust(file_path: str) -> pd.DataFrame:
        encodings = [None, "utf-8", "utf-8-sig", "latin-1"]
        last_error = None
        for enc in encodings:
            try:
                kwargs = {"encoding": enc} if enc else {}
                return pd.read_csv(file_path, **kwargs)
            except Exception as e:
                last_error = e
        for enc in ["utf-8", "utf-8-sig", "latin-1"]:
            try:
                return pd.read_csv(file_path, encoding=enc, engine="python", on_bad_lines="skip")
            except Exception as e:
                last_error = e
        raise ValueError(f"No se pudo leer CSV de forma robusta: {last_error}")

    def analyze_completeness(self) -> Dict[str, Any]:
        total_cells      = self.total_rows * self.total_columns
        total_null_cells = self.df.isna().sum().sum()
        completeness_ratio = 1 - (total_null_cells / total_cells) if total_cells else 0
        validations = {}
        for col in self.columns:
            unexpected_count   = int(self.df[col].isna().sum())
            unexpected_percent = (unexpected_count / self.total_rows * 100) if self.total_rows else 0
            validations[col]   = {
                "success":            unexpected_count == 0,
                "unexpected_count":   unexpected_count,
                "unexpected_percent": round(unexpected_percent, 3),
            }
        return {
            "metrics": {
                "total_rows":         self.total_rows,
                "total_cells":        total_cells,
                "total_null_cells":   int(total_null_cells),
                "completeness_ratio": round(completeness_ratio, 3),
            },
            "validations": validations,
            "grade": self._calculate_grade(completeness_ratio),
        }

    def analyze_accuracy(self) -> Dict[str, Any]:
        accuracy_score = 1.0
        metrics = {}
        for col in self.columns:
            col_metrics = {
                "data_type":          str(self.df[col].dtype),
                "unique_values_count": int(self.df[col].nunique()),
            }
            if pd.api.types.is_numeric_dtype(self.df[col]):
                col_metrics.update({
                    "min":  float(self.df[col].min()),
                    "max":  float(self.df[col].max()),
                    "mean": round(float(self.df[col].mean()), 3),
                    "std":  round(float(self.df[col].std()), 3),
                })
            metrics[col] = col_metrics
            if self.df[col].dtype == "object":
                if self.df[col].apply(type).nunique() > 1:
                    accuracy_score -= 0.05
        return {
            "metrics": metrics,
            "validations": {
                "data_type_check": {
                    "success":          accuracy_score > 0.95,
                    "unexpected_count": int((1 - accuracy_score) * self.total_rows),
                }
            },
            "grade": self._calculate_grade(accuracy_score),
        }

    def analyze_consistency(self) -> Dict[str, Any]:
        metrics = {}
        consistency_score = 1.0
        for col in self.columns:
            if pd.api.types.is_string_dtype(self.df[col]):
                vc = self.df[col].value_counts()
                metrics[col] = {
                    "unique_values_count":         len(vc),
                    "most_common_value":           vc.index[0] if len(vc) else None,
                    "most_common_value_frequency": int(vc.iloc[0]) if len(vc) else 0,
                }
                unique_ratio = len(vc) / self.total_rows if self.total_rows else 0
                if unique_ratio > 0.9 and "id" not in col.lower():
                    consistency_score -= 0.1
        return {
            "metrics": metrics,
            "validations": {
                "value_set_check": {
                    "success":          consistency_score > 0.9,
                    "unexpected_count": int((1 - consistency_score) * self.total_rows),
                }
            },
            "grade": self._calculate_grade(consistency_score),
        }

    def analyze_uniqueness(self) -> Dict[str, Any]:
        metrics = {}
        for col in self.columns:
            vc         = self.df[col].value_counts()
            duplicates = vc[vc > 1].to_dict()
            metrics[col] = {
                "unique_count":     int(self.df[col].nunique()),
                "duplicate_count":  len(duplicates),
                "duplication_ratio": round(len(duplicates) / self.total_rows, 3)
                                     if self.total_rows else 0,
            }
        max_dup = max((m["duplication_ratio"] for m in metrics.values()), default=0)
        return {
            "metrics": metrics,
            "validations": {
                f"{col}_uniqueness": {
                    "success":            metrics[col]["duplicate_count"] == 0,
                    "unexpected_count":   metrics[col]["duplicate_count"],
                    "unexpected_percent": round(metrics[col]["duplication_ratio"] * 100, 3),
                } for col in self.columns
            },
            "grade": self._calculate_grade(1 - max_dup),
        }

    def _calculate_grade(self, score: float) -> dict:
        score = round(float(score), 3)
        if   score >= 0.95: interp = "Excellent"
        elif score >= 0.90: interp = "Good"
        elif score >= 0.85: interp = "Fair"
        elif score >= 0.80: interp = "Poor"
        else:               interp = "Failed"
        return {"score": score, "interpretation": interp, "threshold_met": score >= 0.85}

    def generate_report(self) -> Dict[str, Any]:
        completeness = self.analyze_completeness()
        accuracy     = self.analyze_accuracy()
        consistency  = self.analyze_consistency()
        uniqueness   = self.analyze_uniqueness()

        cat_scores = {
            "completeness": completeness["grade"]["score"],
            "accuracy":     accuracy["grade"]["score"],
            "consistency":  consistency["grade"]["score"],
            "uniqueness":   uniqueness["grade"]["score"],
        }
        overall = round(float(np.mean(list(cat_scores.values()))), 3)

        return {
            "metadata": {
                "filename":         self.file_path,
                "timestamp":        datetime.now().isoformat(),
                "total_rows":       self.total_rows,
                "total_columns":    self.total_columns,
                "columns":          self.columns,
                "analysis_version": "2.0-2026",
            },
            "quality_checks": {
                "completeness": completeness,
                "accuracy":     accuracy,
                "consistency":  consistency,
                "uniqueness":   uniqueness,
            },
            "overall_quality": {
                "score":           overall,
                "grade":           self._calculate_grade(overall)["interpretation"],
                "category_scores": cat_scores,
            },
        }


def score_content(csv_paths: list) -> dict:
    """
    Wrapper: corre DataQualityAnalyzer sobre todos los CSVs de un dataset
    y agrega los scores. Retorna score promedio de contenido.
    """
    if not csv_paths:
        return {"content_score": None, "content_evaluated": False, "content_files": 0}

    scores = []
    for path in csv_paths:
        path_obj = Path(path)
        if not path_obj.exists():
            print(f"     ⚠ Archivo no encontrado, se omite: {path}")
            continue
        try:
            analyzer = DataQualityAnalyzer(path)
            report   = analyzer.generate_report()
            scores.append(report["overall_quality"]["score"])
        except Exception as e:
            print(f"     ⚠ Error al analizar {path}: {e}")
            quarantine = quarantine_bad_csv(path, str(e))
            if quarantine.get("quarantined"):
                print(f"       → Archivo movido a cuarentena: {quarantine.get('quarantine_path')}")

    if not scores:
        return {"content_score": None, "content_evaluated": False, "content_files": 0}

    return {
        "content_score":     round(float(np.mean(scores)), 4),
        "content_score_min": round(float(np.min(scores)),  4),
        "content_score_max": round(float(np.max(scores)),  4),
        "content_evaluated": True,
        "content_files":     len(scores),
    }


# ══════════════════════════════════════════════════════════════════
# CAPA C — Evaluación de Estándares con LLM (provider-agnostic)
# ══════════════════════════════════════════════════════════════════

def quarantine_bad_csv(file_path: str, reason: str) -> dict:
    base     = Path("data/bronze") / "csv_quarantine"
    log_path = base / "quarantine_log.jsonl"
    try:
        src = Path(file_path)
        if not src.exists():
            return {"quarantined": False, "reason": f"No existe: {file_path}"}

        date_str    = datetime.now().strftime("%Y%m%d")
        dataset_dir = src.parent.name if src.parent else "unknown_dataset"
        dest_dir    = base / date_str / dataset_dir
        dest_dir.mkdir(parents=True, exist_ok=True)

        dest = dest_dir / src.name
        if dest.exists():
            dest = dest_dir / f"{dest.stem}_{datetime.now().strftime('%H%M%S')}{dest.suffix}"

        shutil.move(str(src), str(dest))
        base.mkdir(parents=True, exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "timestamp":      datetime.now().isoformat(),
                "original_path":  str(src),
                "quarantine_path": str(dest),
                "reason":         reason,
            }, ensure_ascii=False) + "\n")

        return {"quarantined": True, "quarantine_path": str(dest)}
    except Exception as e:
        return {"quarantined": False, "reason": str(e)}


def score_standards_llm(
    dataset_title: str,
    dataset_description: str,
    csv_columns: list[str],   # ← columnas reales del CSV (no tags)
    category: str,
) -> dict:
    """
    Evalúa el dataset contra estándares internacionales sectoriales.

    Usa el proveedor LLM activo (LLM_PROVIDER env var).
    Mismo prompt independientemente del proveedor — respuesta JSON idéntica.

    FIX vs versión anterior:
    - Usa csv_columns (columnas reales del CSV), no tags del dataset
    - Provider-agnostic: funciona con OpenAI, Claude, Gemini, Minimax
    - Retry automático con backoff
    - Nombre de función no asume proveedor
    """
    prompt = f"""Eres un experto en estándares de datos abiertos gubernamentales.
Evalúa el siguiente dataset del Gobierno de Nuevo León, México.

Título: {dataset_title}
Categoría: {category}
Descripción: {dataset_description[:500] if dataset_description else 'No disponible'}
Columnas disponibles en el CSV: {', '.join(csv_columns[:30]) if csv_columns else 'No disponible'}

Tareas:
1. Identifica 3 estándares internacionales de datos específicos para este dominio temático
   (no estándares genéricos — usa estándares como GTFS para transporte,
   OCDS para contrataciones, IATI para ayuda, HL7/FHIR para salud, etc.)
2. Evalúa el cumplimiento del dataset con cada estándar basándote en las columnas disponibles
3. Asigna un score de cumplimiento: green (>70%), yellow (40-70%), red (<40%)

Responde ÚNICAMENTE con este JSON:
{{
  "standards": [
    {{"name": "...", "compliance": "green|yellow|red", "score": 0.0, "url": "...", "missing_fields": []}},
    {{"name": "...", "compliance": "green|yellow|red", "score": 0.0, "url": "...", "missing_fields": []}},
    {{"name": "...", "compliance": "green|yellow|red", "score": 0.0, "url": "...", "missing_fields": []}}
  ],
  "domain_alignment_score": 0.0
}}"""

    raw = _call_llm(prompt)
    if not raw:
        return {
            "standards_evaluated": False,
            "standards": [],
            "standards_score": None,
            "llm_provider": LLM_PROVIDER,
            "llm_model": LLM_MODEL,
            "error": f"LLM ({LLM_PROVIDER}/{LLM_MODEL}) no retornó respuesta",
        }

    try:
        result = _parse_llm_json(raw)
        # Validar que los scores están en rango [0, 1]
        for std in result.get("standards", []):
            std["score"] = max(0.0, min(1.0, float(std.get("score", 0))))
        alignment = max(0.0, min(1.0, float(result.get("domain_alignment_score", 0))))

        return {
            "standards_evaluated": True,
            "standards":           result.get("standards", []),
            "standards_score":     round(alignment, 4),
            "llm_provider":        LLM_PROVIDER,
            "llm_model":           LLM_MODEL,
        }
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        return {
            "standards_evaluated": False,
            "standards":           [],
            "standards_score":     None,
            "llm_provider":        LLM_PROVIDER,
            "llm_model":           LLM_MODEL,
            "error":               f"Parse error: {e} | raw={raw[:200]}",
        }


def _extract_csv_columns(row: pd.Series) -> list[str]:
    """
    Extrae columnas reales del primer CSV descargado del dataset.
    Fallback a lista vacía (nunca usa tags como proxy de columnas).
    """
    csv_paths = row.get("csv_paths", [])
    if isinstance(csv_paths, str):
        try:
            csv_paths = ast.literal_eval(csv_paths)
        except Exception:
            csv_paths = []

    for path in csv_paths:
        p = Path(path)
        if p.exists():
            try:
                df_sample = pd.read_csv(p, nrows=0)
                return list(df_sample.columns)
            except Exception:
                continue

    return []  # nunca retorna tags — columnas vacías es honest


# ══════════════════════════════════════════════════════════════════
# EVALUADOR INTEGRADO
# ══════════════════════════════════════════════════════════════════

def evaluate_dataset(
    row: pd.Series,
    reference_date: datetime,
    evaluate_standards: bool = False,
) -> dict:
    """Evaluación completa de un dataset en las 3 capas."""
    # Capa A: Metadata
    meta_scores = score_metadata(row, reference_date)

    # Capa B: Contenido CSV
    csv_paths = row.get("csv_paths", [])
    if isinstance(csv_paths, str):
        try:
            csv_paths = ast.literal_eval(csv_paths)
        except Exception:
            csv_paths = []
    content_scores = score_content(csv_paths)

    # Capa C: Estándares LLM (provider-agnostic, opcional)
    standards_scores: dict = {"standards_evaluated": False, "standards_score": None}
    if evaluate_standards:
        csv_columns = _extract_csv_columns(row)  # ← columnas reales, no tags
        standards_scores = score_standards_llm(
            dataset_title       = str(row.get("title", "")),
            dataset_description = str(row.get("notes", row.get("description", ""))),
            csv_columns         = csv_columns,
            category            = str((row.get("groups") or [""])[0]),
        )

    # Score compuesto final
    scores_to_combine = [meta_scores["meta_score"]]
    if content_scores.get("content_evaluated"):
        scores_to_combine.append(content_scores["content_score"])
    if standards_scores.get("standards_evaluated") and standards_scores.get("standards_score") is not None:
        scores_to_combine.append(standards_scores["standards_score"])

    final_score = round(float(np.mean(scores_to_combine)), 4)

    if   final_score >= 0.80: grade = "A"
    elif final_score >= 0.65: grade = "B"
    elif final_score >= 0.50: grade = "C"
    elif final_score >= 0.35: grade = "D"
    else:                     grade = "F"

    return {
        **meta_scores,
        **content_scores,
        **{k: v for k, v in standards_scores.items()
           if k in ("standards_evaluated", "standards_score", "llm_provider", "llm_model")},
        "score_final":      final_score,
        "grade":            grade,
        "layers_evaluated": len(scores_to_combine),
    }


def evaluate_catalog(
    df: pd.DataFrame,
    reference_date: datetime,
    evaluate_standards: bool = False,
) -> pd.DataFrame:
    """Evalúa todos los datasets. Retorna DataFrame con scores añadidos."""
    print(f"🔍 Evaluando {len(df)} datasets | proveedor LLM: {LLM_PROVIDER}/{LLM_MODEL}")
    results = []
    for i, (_, row) in enumerate(df.iterrows()):
        result = evaluate_dataset(row, reference_date, evaluate_standards)
        results.append(result)
        if (i + 1) % 10 == 0:
            print(f"   {i+1}/{len(df)} evaluados...")

    eval_df = pd.DataFrame(results)
    return pd.concat([df.reset_index(drop=True), eval_df], axis=1)


def aggregate_by_organization(eval_df: pd.DataFrame) -> pd.DataFrame:
    """Agrega scores a nivel de dependencia."""
    agg = eval_df.groupby("org_title").agg(
        n_datasets          = ("id", "count"),
        meta_score_mean     = ("meta_score", "mean"),
        meta_score_std      = ("meta_score", "std"),
        content_score_mean  = ("content_score", lambda x: x.dropna().mean() if x.notna().any() else None),
        score_final_mean    = ("score_final", "mean"),
        score_final_std     = ("score_final", "std"),
        pct_with_csv        = ("content_evaluated", "mean"),
        grade_A             = ("grade", lambda x: (x == "A").sum()),
        grade_B             = ("grade", lambda x: (x == "B").sum()),
        grade_C             = ("grade", lambda x: (x == "C").sum()),
        grade_D             = ("grade", lambda x: (x == "D").sum()),
        grade_F             = ("grade", lambda x: (x == "F").sum()),
        last_update         = ("metadata_modified", "max"),
    ).reset_index()

    agg["org_grade"] = pd.cut(
        agg["score_final_mean"],
        bins   = [0, 0.35, 0.50, 0.65, 0.80, 1.01],
        labels = ["F", "D", "C", "B", "A"],
        right  = True,
    )
    return agg.sort_values("score_final_mean", ascending=False).reset_index(drop=True)


# ── Main ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    parser = argparse.ArgumentParser(description="Evaluación Silver — NL 2024-2026")
    parser.add_argument(
        "--with-standards",
        action="store_true",
        help=f"Activa evaluación de estándares via LLM (proveedor: {LLM_PROVIDER}/{LLM_MODEL})",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("  EVALUACIÓN SILVER — DATOS ABIERTOS NL")
    print(f"  LLM proveedor: {LLM_PROVIDER} / {LLM_MODEL}")
    print("=" * 60 + "\n")

    BRONZE_DIR = Path("data/raw")
    SILVER_DIR = Path("data/processed")
    SILVER_DIR.mkdir(parents=True, exist_ok=True)

    # Cargar Bronze más reciente
    files = sorted(glob.glob(str(BRONZE_DIR / "catalog_flat_*.csv")))
    if not files:
        print("❌ Ejecuta primero 01_extract.py")
        sys.exit(1)

    df = pd.read_csv(files[-1])

    for col in ["formats", "groups", "tags", "csv_paths"]:
        if col in df.columns:
            df[col] = df[col].apply(
                lambda x: ast.literal_eval(x)
                if isinstance(x, str) and x.startswith("[") else []
            )

    for col in ["metadata_created", "metadata_modified"]:
        df[col] = pd.to_datetime(df[col], errors="coerce", utc=True)

    ref_t1  = datetime.now(timezone.utc)
    eval_df = evaluate_catalog(df, reference_date=ref_t1, evaluate_standards=args.with_standards)

    date_str = datetime.now().strftime("%Y%m%d")
    eval_df.to_csv(SILVER_DIR / f"evaluated_datasets_{date_str}.csv", index=False)
    aggregate_by_organization(eval_df).to_csv(
        SILVER_DIR / f"evaluated_organizations_{date_str}.csv", index=False
    )

    print(f"\n💾 Silver guardado en data/silver/")

    org_df = aggregate_by_organization(eval_df)
    print("\n📊 RANKING DE DEPENDENCIAS:")
    print(org_df[[
        "org_title", "n_datasets", "meta_score_mean",
        "content_score_mean", "score_final_mean", "org_grade"
    ]].to_string(index=False))