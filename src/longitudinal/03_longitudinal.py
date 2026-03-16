"""
MÓDULO 3 — ANÁLISIS LONGITUDINAL GOLD
=======================================
Proyecto: Evolución de Calidad de Datos Abiertos NL 2024-2026

Pregunta central:
  ¿Qué dependencias han mejorado o empeorado su calidad de datos
  entre 2024 y 2026, y qué variables institucionales predicen ese cambio?

Produce:
  1. Reconstrucción del estado t0 (2024) desde metadata temporal
  2. Cálculo de deltas por dependencia
  3. Clasificación: Mejora / Estancamiento / Deterioro
  4. Modelo OLS con 5 variables predictoras
  5. Reporte Gold completo en JSON + CSV exportable

NOTA: Este módulo NO usa LLM. Todo es estadístico puro.
El proveedor LLM activo en 02_evaluate.py no afecta este módulo.
"""

from __future__ import annotations

import ast
import glob
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

# ── Import de 02_evaluate (sin importlib frágil) ──────────────────────────────
# FIX: Reemplaza el importlib.spec_from_file_location que rompía si
# el directorio de trabajo no era el raíz del proyecto.
sys.path.insert(0, str(Path(__file__).parent))

from evaluate_02 import (  # type: ignore[import]
    evaluate_catalog,
    aggregate_by_organization,
)

# ── Constantes ─────────────────────────────────────────────────────────────────

SILVER_DIR = Path("data/silver")
GOLD_DIR   = Path("data/gold")
GOLD_DIR.mkdir(parents=True, exist_ok=True)

# Datasets existentes antes de esta fecha = corpus t0 (2024)
CUTOFF_T0 = pd.Timestamp("2025-01-01", tz="UTC")
REF_T0    = datetime(2024, 12, 31, tzinfo=timezone.utc)
REF_T1    = datetime.now(timezone.utc)

# Columnas de scoring producidas por 02_evaluate — se eliminan antes de re-evaluar t0
EVAL_OUTPUT_COLS = [
    "meta_completitud", "meta_actualizacion", "meta_accesibilidad",
    "meta_documentacion", "meta_apertura", "meta_score",
    "content_score", "content_score_min", "content_score_max",
    "content_evaluated", "content_files",
    "standards_evaluated", "standards_score", "llm_provider", "llm_model",
    "score_final", "grade", "layers_evaluated",
]

# Variables del modelo OLS
PREDICTORS = [
    "x1_capacidad",
    "x2_frecuencia",
    "x3_antiguedad",
    "x4_formato_abierto",
    "x5_diversidad_tematica",
]
TARGET = "delta_score_final_mean"

PREDICTOR_LABELS = {
    "x1_capacidad":           "Capacidad institucional (n datasets)",
    "x2_frecuencia":          "Frecuencia de actualización",
    "x3_antiguedad":          "Antigüedad de adopción (días)",
    "x4_formato_abierto":     "Proporción formato CSV/JSON",
    "x5_diversidad_tematica": "Diversidad temática (grupos promedio)",
}


# ── Reconstrucción t0 ──────────────────────────────────────────────────────────

def reconstruct_t0(df_t1: pd.DataFrame) -> pd.DataFrame:
    """
    Filtra datasets que existían antes de 2025 (corpus 2024)
    para construir el panel balanceado t0.
    """
    df_t0 = df_t1[df_t1["metadata_created"] <= CUTOFF_T0].copy()

    print(f"  Total datasets t1 (2026):       {len(df_t1)}")
    print(f"  Datasets en corpus t0 (2024):   {len(df_t0)}")
    print(f"  Datasets nuevos 2025-2026:       {len(df_t1) - len(df_t0)}")
    print(f"  Dependencias en t0:              {df_t0['org_name'].nunique()}")

    return df_t0


# ── Cálculo de deltas ──────────────────────────────────────────────────────────

def compute_deltas(org_t0: pd.DataFrame, org_t1: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula cambio en calidad entre t0 y t1 por dependencia.
    Solo incluye dependencias presentes en ambos períodos (panel balanceado).
    """
    merged = org_t0.merge(org_t1, on="org_title", suffixes=("_t0", "_t1"), how="inner")

    for col in ["meta_score_mean", "score_final_mean"]:
        c0, c1 = f"{col}_t0", f"{col}_t1"
        if c0 in merged.columns and c1 in merged.columns:
            merged[f"delta_{col}"] = merged[c1] - merged[c0]

    if "n_datasets_t0" in merged.columns and "n_datasets_t1" in merged.columns:
        merged["delta_n_datasets"] = merged["n_datasets_t1"] - merged["n_datasets_t0"]

    def classify(delta: float) -> str:
        if   delta >  0.10: return "Mejora Significativa"
        elif delta >  0.02: return "Mejora Marginal"
        elif delta >= -0.02: return "Estancamiento"
        elif delta >= -0.10: return "Deterioro Marginal"
        else:               return "Deterioro Significativo"

    merged["clasificacion"] = merged["delta_score_final_mean"].apply(classify)

    return merged.sort_values("delta_score_final_mean", ascending=False).reset_index(drop=True)


# ── Variables predictoras ──────────────────────────────────────────────────────

def build_predictors(df_raw: pd.DataFrame, delta_df: pd.DataFrame) -> pd.DataFrame:
    """
    Construye las 5 variables independientes del modelo OLS.

    X1 — Capacidad institucional:     número de datasets publicados en t1
    X2 — Frecuencia de actualización: inverso de días desde última modificación
    X3 — Antigüedad de adopción:      días desde el primer dataset publicado
    X4 — Proporción formato abierto:  % datasets con CSV/JSON
    X5 — Diversidad temática:         promedio de grupos por dataset
    """
    ref = datetime.now(timezone.utc)

    grouped  = df_raw.groupby("org_title", dropna=True)
    org_vars = grouped.agg(
        x1_capacidad              = ("id",                "count"),
        metadata_modified_max     = ("metadata_modified", "max"),
        metadata_created_min      = ("metadata_created",  "min"),
        x4_formato_abierto        = ("has_csv",           "mean"),
        x5_diversidad_tematica    = ("num_groups",        "mean"),
    ).reset_index()

    org_vars["x2_frecuencia"] = org_vars["metadata_modified_max"].apply(
        lambda v: 1 / (1 + max((ref - v).days, 0)) if pd.notna(v) else 0
    )
    org_vars["x3_antiguedad"] = org_vars["metadata_created_min"].apply(
        lambda v: max((ref - v).days, 0) if pd.notna(v) else 0
    )
    org_vars = org_vars.drop(columns=["metadata_modified_max", "metadata_created_min"])

    return delta_df.merge(org_vars, on="org_title", how="left")


# ── Modelo OLS ─────────────────────────────────────────────────────────────────

def run_ols(model_df: pd.DataFrame) -> dict:
    """
    Regresión OLS.
    Usa statsmodels si disponible (p-values, F-test), fallback a numpy.
    """
    clean = model_df[PREDICTORS + [TARGET, "org_title"]].dropna()

    if len(clean) < 5:
        return {"error": f"Muestra insuficiente: {len(clean)} observaciones (mínimo 5)."}

    X = clean[PREDICTORS].values
    y = clean[TARGET].values

    try:
        import statsmodels.api as sm
        model = sm.OLS(y, sm.add_constant(X)).fit()

        return {
            "method":        "OLS (statsmodels)",
            "n":             len(clean),
            "r_squared":     round(model.rsquared, 4),
            "adj_r_squared": round(model.rsquared_adj, 4),
            "f_pvalue":      round(model.f_pvalue, 4),
            "coefficients":  {
                "intercept": round(model.params[0], 6),
                **{PREDICTOR_LABELS[p]: round(c, 6)
                   for p, c in zip(PREDICTORS, model.params[1:])},
            },
            "pvalues": {
                "intercept": round(model.pvalues[0], 4),
                **{PREDICTOR_LABELS[p]: round(v, 4)
                   for p, v in zip(PREDICTORS, model.pvalues[1:])},
            },
            "significant_at_05": [
                PREDICTOR_LABELS[p]
                for p, v in zip(PREDICTORS, model.pvalues[1:])
                if v < 0.05
            ],
            "interpretation": _interpret_model(
                model.rsquared, model.params[1:], model.pvalues[1:]
            ),
        }

    except ImportError:
        Xc    = np.column_stack([np.ones(len(X)), X])
        coeffs, _, _, _ = np.linalg.lstsq(Xc, y, rcond=None)
        y_hat  = Xc @ coeffs
        ss_res = np.sum((y - y_hat) ** 2)
        ss_tot = np.sum((y - y.mean()) ** 2)
        r2     = 1 - ss_res / ss_tot if ss_tot > 0 else 0

        return {
            "method":       "OLS (numpy — instala statsmodels para p-values)",
            "n":            len(clean),
            "r_squared":    round(r2, 4),
            "coefficients": {
                "intercept": round(coeffs[0], 6),
                **{PREDICTOR_LABELS[p]: round(c, 6)
                   for p, c in zip(PREDICTORS, coeffs[1:])},
            },
        }


def _interpret_model(r2: float, coefs: list, pvals: list) -> str:
    lines = [f"El modelo explica el {r2 * 100:.1f}% de la varianza en el cambio de calidad."]
    sig = [
        (PREDICTOR_LABELS[p], c, v)
        for p, c, v in zip(PREDICTORS, coefs, pvals)
        if v < 0.05
    ]
    if not sig:
        lines.append(
            "Ningún predictor alcanza significancia estadística (p<0.05), "
            "posiblemente por el tamaño limitado de la muestra."
        )
    else:
        for label, coef, pval in sig:
            direction = "positivamente" if coef > 0 else "negativamente"
            lines.append(
                f"'{label}' predice {direction} el cambio (β={coef:+.4f}, p={pval:.3f})."
            )
    return " ".join(lines)


# ── Reporte Gold ───────────────────────────────────────────────────────────────

def generate_report(
    delta_df: pd.DataFrame,
    model: dict,
    df_t0_size: int,
    df_t1_size: int,
) -> dict:
    clasificacion = delta_df["clasificacion"].value_counts().to_dict()
    top_mejora    = delta_df.head(3)[["org_title", "delta_score_final_mean"]].to_dict("records")
    top_deterioro = delta_df.tail(3)[["org_title", "delta_score_final_mean"]].to_dict("records")

    return {
        "metadata": {
            "generado":         datetime.now().isoformat(),
            "proyecto":         "Evolución Calidad Datos Abiertos NL 2024-2026",
            "pregunta_central": (
                "¿Qué dependencias han mejorado o empeorado su calidad de datos "
                "entre 2024 y 2026, y qué variables institucionales predicen ese cambio?"
            ),
            "metodologia": {
                "t0_referencia":    "2024-12-31",
                "t1_referencia":    REF_T1.strftime("%Y-%m-%d"),
                "datasets_t0":      df_t0_size,
                "datasets_t1":      df_t1_size,
                "datasets_nuevos":  df_t1_size - df_t0_size,
                "capas_evaluacion": [
                    "A — Metadata CKAN (completitud, actualización, accesibilidad, documentación, apertura)",
                    "B — Contenido CSV (completeness, accuracy, consistency, uniqueness — DataQualityAnalyzer v2.0)",
                    "C — Estándares internacionales (LLM provider-agnostic — opcional)",
                ],
            },
        },
        "hallazgos": {
            "dependencias_analizadas": len(delta_df),
            "clasificacion":           clasificacion,
            "delta_promedio":          round(float(delta_df["delta_score_final_mean"].mean()), 4),
            "delta_mediana":           round(float(delta_df["delta_score_final_mean"].median()), 4),
            "top_mejora":              top_mejora,
            "top_deterioro":           top_deterioro,
        },
        "modelo_predictivo": model,
        "ranking_dependencias": delta_df[[
            "org_title",
            "score_final_mean_t0",
            "score_final_mean_t1",
            "delta_score_final_mean",
            "n_datasets_t0",
            "n_datasets_t1",
            "delta_n_datasets",
            "clasificacion",
        ]].rename(columns={
            "org_title":              "dependencia",
            "score_final_mean_t0":    "score_2024",
            "score_final_mean_t1":    "score_2026",
            "delta_score_final_mean": "delta",
            "n_datasets_t0":          "n_2024",
            "n_datasets_t1":          "n_2026",
        }).to_dict("records"),
    }


# ── Main ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    print("=" * 60)
    print("  ANÁLISIS LONGITUDINAL GOLD — NL 2024-2026")
    print("  (Sin LLM — estadístico puro)")
    print("=" * 60)

    # Cargar Silver más reciente
    silver_files = sorted(glob.glob(str(SILVER_DIR / "evaluated_datasets_*.csv")))
    if not silver_files:
        print("❌ Ejecuta primero 02_evaluate.py")
        sys.exit(1)

    df_t1_full = pd.read_csv(silver_files[-1])

    for col in ["formats", "groups", "tags", "csv_paths"]:
        if col in df_t1_full.columns:
            df_t1_full[col] = df_t1_full[col].apply(
                lambda x: ast.literal_eval(x) if isinstance(x, str) and x.startswith("[") else []
            )
    for col in ["metadata_created", "metadata_modified"]:
        df_t1_full[col] = pd.to_datetime(df_t1_full[col], errors="coerce", utc=True)

    org_files = sorted(glob.glob(str(SILVER_DIR / "evaluated_organizations_*.csv")))
    org_t1    = pd.read_csv(org_files[-1])

    # Reconstruir y evaluar t0
    print("\n📅 Reconstruyendo corpus t0 (2024)...")
    df_t0 = reconstruct_t0(df_t1_full)

    print("\n🔍 Evaluando estado t0 (sin LLM, sin descarga)...")
    t0_input  = df_t0.drop(columns=[c for c in EVAL_OUTPUT_COLS if c in df_t0.columns])
    df_t0_eval = evaluate_catalog(t0_input, reference_date=REF_T0, evaluate_standards=False)
    org_t0     = aggregate_by_organization(df_t0_eval)

    # Calcular deltas
    print("\n📈 Calculando deltas 2024 → 2026...")
    delta_df = compute_deltas(org_t0, org_t1)
    print(f"   → {len(delta_df)} dependencias en panel balanceado\n")
    for cat, n in delta_df["clasificacion"].value_counts().items():
        print(f"   {cat:<30} {n}")

    # Modelo predictivo
    print("\n🔬 Construyendo modelo OLS...")
    model_df = build_predictors(df_t1_full, delta_df)
    model    = run_ols(model_df)
    print(f"   R²: {model.get('r_squared', 'N/A')}")
    if "interpretation" in model:
        print(f"   → {model['interpretation']}")

    # Reporte Gold
    report   = generate_report(delta_df, model, len(df_t0), len(df_t1_full))
    date_str = datetime.now().strftime("%Y%m%d")

    report_path = GOLD_DIR / f"report_longitudinal_{date_str}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)

    delta_path = GOLD_DIR / f"delta_dependencias_{date_str}.csv"
    delta_df.to_csv(delta_path, index=False)

    print(f"\n💾 Reporte:  {report_path}")
    print(f"💾 Deltas:   {delta_path}")

    print("\n📊 RANKING FINAL DE DEPENDENCIAS:")
    cols_show = [c for c in [
        "org_title", "score_final_mean_t0", "score_final_mean_t1",
        "delta_score_final_mean", "clasificacion"
    ] if c in delta_df.columns]
    print(delta_df[cols_show].to_string(index=False))