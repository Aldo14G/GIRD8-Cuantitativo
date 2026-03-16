"""
MÓDULO 1 — EXTRACCIÓN BRONZE
==============================
Proyecto: Evolución de Calidad de Datos Abiertos NL 2024-2026

Qué hace:
  1. Extrae metadata completo de todos los datasets via CKAN API
  2. Descarga los archivos CSV reales de cada dataset
  3. Guarda snapshots timestamped para comparación longitudinal

Arquitectura:
  data/raw/
    catalog_snapshot_YYYYMMDD.json  ← metadata completo
    catalog_flat_YYYYMMDD.csv       ← metadata aplanado
    csv_files/                      ← archivos CSV por dataset
"""
import json
import time
import argparse
import sys
from datetime import datetime
from pathlib import Path

import requests
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from config.settings import (
    CKAN_API_BASE,
    DATA_RAW,
    RATE_LIMIT_SECONDS,
    HEADERS,
)


def get_all_packages() -> list[str]:
    r = requests.get(f"{CKAN_API_BASE}/package_list", headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()["result"]


def get_package_detail(name: str) -> dict:
    r = requests.get(
        f"{CKAN_API_BASE}/package_show",
        params={"id": name},
        headers=HEADERS,
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["result"]


def get_organizations() -> list[dict]:
    r = requests.get(
        f"{CKAN_API_BASE}/organization_list",
        params={"all_fields": True, "include_dataset_count": True},
        headers=HEADERS,
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["result"]


def download_csv(resource: dict, dest_dir: Path) -> dict:
    url = resource.get("url", "")
    fmt = resource.get("format", "").upper()
    res_id = resource.get("id", "unknown")

    if fmt not in ["CSV", ".CSV"]:
        return {"downloaded": False, "reason": f"format={fmt}"}

    try:
        r = requests.get(url, headers=HEADERS, timeout=60, stream=True)
        r.raise_for_status()

        filename = dest_dir / f"{res_id}.csv"
        with open(filename, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

        size_kb = filename.stat().st_size / 1024

        return {
            "downloaded": True,
            "path": str(filename),
            "size_kb": round(size_kb, 2),
            "url": url,
        }

    except Exception as e:
        return {"downloaded": False, "reason": str(e), "url": url}


def extract_full_catalog(download_csvs: bool = True, max_datasets: int | None = None) -> list[dict]:
    print("📦 Obteniendo lista de datasets...")
    packages = get_all_packages()
    if max_datasets:
        packages = packages[:max_datasets]
    print(f"   → {len(packages)} datasets encontrados\n")

    csv_dir = DATA_RAW / "csv_files"
    csv_dir.mkdir(parents=True, exist_ok=True)

    catalog = []

    for i, pkg_name in enumerate(packages):
        try:
            pkg = get_package_detail(pkg_name)

            if download_csvs:
                pkg_dir = csv_dir / pkg_name
                pkg_dir.mkdir(exist_ok=True)
                download_results = []
                for resource in pkg.get("resources", []):
                    result = download_csv(resource, pkg_dir)
                    download_results.append(
                        {
                            "resource_id": resource.get("id"),
                            "resource_name": resource.get("name"),
                            **result,
                        }
                    )
                pkg["_download_results"] = download_results

            catalog.append(pkg)
            n_csv = sum(
                1
                for r in pkg.get("resources", [])
                if r.get("format", "").upper() in ["CSV", ".CSV"]
            )
            print(f"  [{i+1:>3}/{len(packages)}] ✓ {pkg_name} ({n_csv} CSV)")
            time.sleep(RATE_LIMIT_SECONDS)

        except Exception as e:
            print(f"  [{i+1:>3}/{len(packages)}] ✗ ERROR: {pkg_name} — {e}")

    return catalog


def flatten_to_dataframe(catalog: list[dict]) -> pd.DataFrame:
    rows = []
    for pkg in catalog:
        resources = pkg.get("resources", [])
        dl_results = pkg.get("_download_results", [])
        csv_downloaded = [r for r in dl_results if r.get("downloaded")]

        row = {
            "id": pkg.get("id"),
            "name": pkg.get("name"),
            "title": pkg.get("title"),
            "org_name": (pkg.get("organization") or {}).get("name"),
            "org_title": (pkg.get("organization") or {}).get("title"),
            "metadata_created": pkg.get("metadata_created"),
            "metadata_modified": pkg.get("metadata_modified"),
            "num_resources": len(resources),
            "has_description": bool((pkg.get("notes") or "").strip()),
            "description_length": len(pkg.get("notes") or ""),
            "num_tags": len(pkg.get("tags", [])),
            "license_id": pkg.get("license_id"),
            "has_license": bool(pkg.get("license_id")),
            "isopen": pkg.get("isopen", False),
            "formats": [r.get("format", "").upper() for r in resources],
            "has_csv": any(
                r.get("format", "").upper() in ["CSV", ".CSV"] for r in resources
            ),
            "has_json": any(r.get("format", "").upper() == "JSON" for r in resources),
            "groups": [g.get("name") for g in pkg.get("groups", [])],
            "num_groups": len(pkg.get("groups", [])),
            "tags": [t.get("name") for t in pkg.get("tags", [])],
            "is_como_vamos": any(
                "como vamos" in t.get("name", "").lower()
                for t in pkg.get("tags", [])
            ),
            "csv_downloaded_count": len(csv_downloaded),
            "csv_paths": [r["path"] for r in csv_downloaded],
            "csv_total_kb": sum(r.get("size_kb", 0) for r in csv_downloaded),
        }
        rows.append(row)

    df = pd.DataFrame(rows)
    for col in ["metadata_created", "metadata_modified"]:
        df[col] = pd.to_datetime(df[col], errors="coerce", utc=True)

    return df


def _ensure_utf8_stdout() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extraccion Bronze CKAN + CSV")
    parser.add_argument(
        "--no-download-csv",
        action="store_true",
        help="Solo extrae metadata CKAN sin descargar archivos CSV",
    )
    parser.add_argument(
        "--max-datasets",
        type=int,
        default=None,
        help="Limitar número de datasets a procesar",
    )
    return parser.parse_args()


def main():
    _ensure_utf8_stdout()
    args = _parse_args()

    from config.settings import CKAN_BASE_URL

    DATE_STR = datetime.now().strftime("%Y%m%d")

    print("=" * 60)
    print("  EXTRACCIÓN BRONZE — DATOS ABIERTOS NL")
    print(f"  Fecha: {DATE_STR}")
    print("=" * 60 + "\n")

    download_csvs = not args.no_download_csv
    print(f"Modo descarga CSV: {'ON' if download_csvs else 'OFF'}")

    catalog = extract_full_catalog(download_csvs=download_csvs, max_datasets=args.max_datasets)

    snap_path = DATA_RAW / f"catalog_snapshot_{DATE_STR}.json"
    with open(snap_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "snapshot_date": DATE_STR,
                "extraction_timestamp": datetime.now().isoformat(),
                "source": CKAN_BASE_URL,
                "total_datasets": len(catalog),
                "datasets": catalog,
            },
            f,
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    print(f"\n💾 Snapshot JSON: {snap_path}")

    df = flatten_to_dataframe(catalog)
    csv_path = DATA_RAW / f"catalog_flat_{DATE_STR}.csv"
    df.to_csv(csv_path, index=False, encoding="utf-8")
    print(f"💾 CSV plano:     {csv_path}")

    print(f"\n📊 RESUMEN:")
    print(f"   Datasets:              {len(df)}")
    print(f"   Dependencias únicas:   {df['org_name'].nunique()}")
    print(f"   Con CSV descargado:    {(df['csv_downloaded_count'] > 0).sum()}")
    print(f"   Sin CSV:               {(df['csv_downloaded_count'] == 0).sum()}")
    print(f"   Volumen total:         {df['csv_total_kb'].sum():.1f} KB")


if __name__ == "__main__":
    main()
