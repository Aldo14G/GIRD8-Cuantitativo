from __future__ import annotations

import argparse
import ast
import csv
import json
import re
from dataclasses import dataclass
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


DATE_PATTERN = re.compile(r"(20\d{6})")

DATASET_NUMERIC_COLS = {
    "num_resources",
    "description_length",
    "num_tags",
    "num_groups",
    "csv_downloaded_count",
    "csv_total_kb",
    "meta_completitud",
    "meta_actualizacion",
    "meta_accesibilidad",
    "meta_documentacion",
    "meta_apertura",
    "meta_score",
    "content_score",
    "content_score_min",
    "content_score_max",
    "content_files",
    "standards_score",
    "score_final",
    "layers_evaluated",
}

DATASET_BOOL_COLS = {
    "has_description",
    "has_license",
    "isopen",
    "has_csv",
    "has_json",
    "is_como_vamos",
    "content_evaluated",
    "standards_evaluated",
}

DATASET_LIST_COLS = {"formats", "groups", "tags", "csv_paths"}

ORG_NUMERIC_COLS = {
    "n_datasets",
    "meta_score_mean",
    "meta_score_std",
    "content_score_mean",
    "score_final_mean",
    "score_final_std",
    "pct_with_csv",
    "grade_A",
    "grade_B",
    "grade_C",
    "grade_D",
    "grade_F",
}

DELTA_NUMERIC_COLS = {
    "n_datasets_t0",
    "meta_score_mean_t0",
    "meta_score_std_t0",
    "content_score_mean_t0",
    "score_final_mean_t0",
    "score_final_std_t0",
    "pct_with_csv_t0",
    "grade_A_t0",
    "grade_B_t0",
    "grade_C_t0",
    "grade_D_t0",
    "grade_F_t0",
    "n_datasets_t1",
    "meta_score_mean_t1",
    "meta_score_std_t1",
    "content_score_mean_t1",
    "score_final_mean_t1",
    "score_final_std_t1",
    "pct_with_csv_t1",
    "grade_A_t1",
    "grade_B_t1",
    "grade_C_t1",
    "grade_D_t1",
    "grade_F_t1",
    "delta_meta_score_mean",
    "delta_score_final_mean",
    "delta_n_datasets",
}


def extract_snapshot_date(path: Path | str) -> str | None:
    name = Path(path).name
    match = DATE_PATTERN.search(name)
    return match.group(1) if match else None


def pick_latest(paths: list[Path]) -> Path | None:
    if not paths:
        return None
    return max(paths, key=lambda p: p.stat().st_mtime)


def parse_cell(value: str, key: str, numeric_cols: set[str], bool_cols: set[str], list_cols: set[str]):
    if value is None:
        return None

    text = value.strip()
    if text == "":
        return None

    if key in bool_cols:
        if text in {"True", "true", "1"}:
            return True
        if text in {"False", "false", "0"}:
            return False

    if key in numeric_cols:
        try:
            if text.isdigit() or (text.startswith("-") and text[1:].isdigit()):
                return int(text)
            return float(text)
        except ValueError:
            return None

    if key in list_cols and text.startswith("[") and text.endswith("]"):
        try:
            parsed = ast.literal_eval(text)
            if isinstance(parsed, list):
                return parsed
            return []
        except (SyntaxError, ValueError):
            return []

    return text


def read_csv_records(
    path: Path,
    numeric_cols: set[str],
    bool_cols: set[str] | None = None,
    list_cols: set[str] | None = None,
) -> list[dict]:
    bool_cols = bool_cols or set()
    list_cols = list_cols or set()

    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            with path.open("r", encoding=encoding, newline="") as handle:
                reader = csv.DictReader(handle)
                rows = []
                for row in reader:
                    parsed = {
                        key: parse_cell(val, key, numeric_cols, bool_cols, list_cols)
                        for key, val in row.items()
                    }
                    rows.append(parsed)
                return rows
        except UnicodeDecodeError:
            continue
    return []


@dataclass
class DataStore:
    data_root: Path

    @property
    def silver_dir(self) -> Path:
        return self.data_root / "silver"

    @property
    def gold_dir(self) -> Path:
        return self.data_root / "gold"

    def _files(self, pattern: str, base_dir: Path) -> list[Path]:
        if not base_dir.exists():
            return []
        return sorted(base_dir.glob(pattern))

    def snapshot_index(self) -> dict:
        datasets = self._files("evaluated_datasets_*.csv", self.silver_dir)
        organizations = self._files("evaluated_organizations_*.csv", self.silver_dir)
        delta = self._files("delta_dependencias_*.csv", self.gold_dir)
        report = self._files("report_longitudinal_*.json", self.gold_dir)

        dates = sorted(
            {
                *(d for d in (extract_snapshot_date(p) for p in datasets) if d),
                *(d for d in (extract_snapshot_date(p) for p in organizations) if d),
                *(d for d in (extract_snapshot_date(p) for p in delta) if d),
                *(d for d in (extract_snapshot_date(p) for p in report) if d),
            },
            reverse=True,
        )

        def has_for_date(items: list[Path], date: str) -> bool:
            return any(extract_snapshot_date(p) == date for p in items)

        rows = [
            {
                "snapshot_date": date,
                "has_datasets": has_for_date(datasets, date),
                "has_organizations": has_for_date(organizations, date),
                "has_delta": has_for_date(delta, date),
                "has_report": has_for_date(report, date),
            }
            for date in dates
        ]

        return {
            "snapshots": rows,
            "default_snapshot": rows[0]["snapshot_date"] if rows else None,
        }

    def _pick_for_date(self, files: list[Path], snapshot_date: str | None) -> Path | None:
        if not files:
            return None
        if snapshot_date:
            dated = [p for p in files if extract_snapshot_date(p) == snapshot_date]
            if dated:
                return pick_latest(dated)
        return pick_latest(files)

    def load_bundle(self, snapshot_date: str | None = None) -> dict:
        datasets_path = self._pick_for_date(
            self._files("evaluated_datasets_*.csv", self.silver_dir), snapshot_date
        )
        organizations_path = self._pick_for_date(
            self._files("evaluated_organizations_*.csv", self.silver_dir), snapshot_date
        )
        delta_path = self._pick_for_date(
            self._files("delta_dependencias_*.csv", self.gold_dir), snapshot_date
        )
        report_path = self._pick_for_date(
            self._files("report_longitudinal_*.json", self.gold_dir), snapshot_date
        )

        datasets = (
            read_csv_records(datasets_path, DATASET_NUMERIC_COLS, DATASET_BOOL_COLS, DATASET_LIST_COLS)
            if datasets_path
            else []
        )
        organizations = (
            read_csv_records(organizations_path, ORG_NUMERIC_COLS)
            if organizations_path
            else []
        )
        delta = read_csv_records(delta_path, DELTA_NUMERIC_COLS) if delta_path else []

        report = {}
        if report_path:
            try:
                report = json.loads(report_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                report = {}

        resolved_snapshot = (
            extract_snapshot_date(datasets_path)
            or extract_snapshot_date(organizations_path)
            or extract_snapshot_date(delta_path)
            or extract_snapshot_date(report_path)
        )

        return {
            "requested_snapshot": snapshot_date,
            "resolved_snapshot": resolved_snapshot,
            "datasets": datasets,
            "organizations": organizations,
            "delta": delta,
            "report": report,
            "paths": {
                "datasets": str(datasets_path) if datasets_path else None,
                "organizations": str(organizations_path) if organizations_path else None,
                "delta": str(delta_path) if delta_path else None,
                "report": str(report_path) if report_path else None,
            },
        }

    def compare_snapshots(self, snapshot_a: str, snapshot_b: str) -> dict:
        bundle_a = self.load_bundle(snapshot_a)
        bundle_b = self.load_bundle(snapshot_b)

        org_a = {
            row["org_title"]: row.get("score_final_mean")
            for row in bundle_a["organizations"]
            if row.get("org_title")
        }
        org_b = {
            row["org_title"]: row.get("score_final_mean")
            for row in bundle_b["organizations"]
            if row.get("org_title")
        }

        all_orgs = sorted(set(org_a) | set(org_b))
        results = []
        for org in all_orgs:
            a = org_a.get(org)
            b = org_b.get(org)
            if a is None or b is None:
                continue
            results.append(
                {
                    "org_title": org,
                    "score_a": a,
                    "score_b": b,
                    "delta_b_minus_a": b - a,
                }
            )

        results.sort(key=lambda item: item["delta_b_minus_a"])
        return {
            "snapshot_a": snapshot_a,
            "snapshot_b": snapshot_b,
            "rows": results,
        }


class DashboardHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, static_dir: Path, store: DataStore, **kwargs):
        self.static_dir = static_dir
        self.store = store
        super().__init__(*args, directory=str(static_dir), **kwargs)

    def _json_response(self, payload: dict, status: int = HTTPStatus.OK) -> None:
        content = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path == "/api/health":
            self._json_response({"ok": True})
            return

        if path == "/api/snapshots":
            self._json_response(self.store.snapshot_index())
            return

        if path == "/api/data":
            snapshot = query.get("snapshot", [None])[0]
            payload = self.store.load_bundle(snapshot_date=snapshot)
            self._json_response(payload)
            return

        if path == "/api/compare":
            snapshot_a = query.get("snapshot_a", [None])[0]
            snapshot_b = query.get("snapshot_b", [None])[0]
            if not snapshot_a or not snapshot_b:
                self._json_response(
                    {"error": "snapshot_a y snapshot_b son obligatorios"},
                    status=HTTPStatus.BAD_REQUEST,
                )
                return
            payload = self.store.compare_snapshots(snapshot_a, snapshot_b)
            self._json_response(payload)
            return

        if path in {"/", "/index", "/index/", "/landing", "/landing/"}:
            self.path = "/index.html"
        elif path in {"/dashboard", "/dashboard/"}:
            self.path = "/dashboard.html"

        return super().do_GET()


def build_handler(static_dir: Path, store: DataStore):
    def factory(*args, **kwargs):
        return DashboardHandler(*args, static_dir=static_dir, store=store, **kwargs)

    return factory


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve HTML dashboard v2026 on localhost")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface")
    parser.add_argument("--port", type=int, default=8765, help="Port number")
    parser.add_argument(
        "--data-root",
        default=str((Path(__file__).resolve().parents[2] / "Data" / "files" / "data")),
        help="Path to pipeline data root (contains silver/ and gold/)",
    )
    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parent
    static_dir = base_dir / "static"
    data_root = Path(args.data_root)
    store = DataStore(data_root=data_root)

    if not static_dir.exists():
        raise SystemExit(f"Static directory not found: {static_dir}")
    if not data_root.exists():
        raise SystemExit(f"Data root not found: {data_root}")

    server = ThreadingHTTPServer((args.host, args.port), build_handler(static_dir, store))
    url = f"http://{args.host}:{args.port}"
    print(f"Dashboard server running at {url}")
    print(f"Using data root: {data_root}")
    print("Press Ctrl+C to stop.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
