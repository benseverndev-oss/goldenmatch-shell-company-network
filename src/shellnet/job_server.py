"""FastAPI control plane for running the shell-company pipeline on Railway.

The container mounts a persistent volume at ``/data`` and exposes stage
endpoints that the operator triggers from their laptop. State is persisted
to ``/data/state.json`` so a redeploy doesn't lose progress.

Auth is a single bearer token from ``SHELLNET_JOB_TOKEN``. There is no
fine-grained authorization; whoever holds the token can wipe data.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import time
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    Header,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse

from shellnet.paths import (
    DATA_DIR,
    ICIJ_RAW,
    INTERIM_DIR,
    PROCESSED_DIR,
    ensure_dirs,
)

log = logging.getLogger("shellnet.job")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

STATE_PATH = DATA_DIR / "state.json"
LOGS_DIR = DATA_DIR / "logs"
REPORTS_DIR = DATA_DIR / "reports" / "generated"
ZIP_PATH = ICIJ_RAW / "full-oldb.LATEST.zip"

STAGES = ("upload", "unzip", "ingest", "build", "match", "publish")


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _load_state() -> dict[str, Any]:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            log.warning("state.json corrupt; resetting")
    return {"stages": {s: {"status": "pending"} for s in STAGES}}


def _save_state(state: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
    tmp.replace(STATE_PATH)


def _mark(stage: str, **fields: Any) -> dict[str, Any]:
    state = _load_state()
    state["stages"].setdefault(stage, {})
    state["stages"][stage].update(fields)
    state["updated_at"] = _now()
    _save_state(state)
    return state["stages"][stage]


def _require_idle(stage: str) -> None:
    state = _load_state()
    cur = state["stages"].get(stage, {}).get("status")
    if cur == "running":
        raise HTTPException(status.HTTP_409_CONFLICT, f"stage {stage} already running")


def _auth(authorization: str | None = Header(default=None)) -> None:
    expected = os.environ.get("SHELLNET_JOB_TOKEN")
    if not expected:
        raise HTTPException(500, "SHELLNET_JOB_TOKEN not configured on server")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing bearer token")
    if authorization.removeprefix("Bearer ").strip() != expected:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid token")


def _run_subprocess(stage: str, cmd: list[str], cwd: Path | None = None) -> dict[str, Any]:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOGS_DIR / f"{stage}-{int(time.time())}.log"
    started = _now()
    _mark(stage, status="running", started_at=started, log=str(log_path), cmd=cmd)
    log.info("[%s] $ %s", stage, " ".join(cmd))
    try:
        with log_path.open("wb") as fh:
            proc = subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT, cwd=cwd)
        if proc.returncode != 0:
            _mark(
                stage,
                status="failed",
                finished_at=_now(),
                returncode=proc.returncode,
                error=f"exit {proc.returncode}",
            )
            return {"ok": False, "returncode": proc.returncode, "log": str(log_path)}
    except Exception as exc:  # noqa: BLE001
        _mark(stage, status="failed", finished_at=_now(), error=repr(exc))
        return {"ok": False, "error": repr(exc), "log": str(log_path)}
    _mark(stage, status="completed", finished_at=_now(), returncode=0)
    return {"ok": True, "returncode": 0, "log": str(log_path)}


app = FastAPI(title="shellnet-job", version="0.1.0")


@app.on_event("startup")
def _startup() -> None:
    ensure_dirs()
    ICIJ_RAW.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    # state.json persists on the volume across redeploys. Any stage
    # marked `running` at startup means a previous container died
    # mid-script (OOM, manual redeploy, force kill, ...). Flip those
    # to `failed` so /run-script's _require_idle check doesn't lock
    # the stage out forever after a stuck job.
    state = _load_state()
    orphans: list[str] = []
    for stage_name, info in state.get("stages", {}).items():
        if info.get("status") == "running":
            orphans.append(stage_name)
    if orphans:
        for stage_name in orphans:
            state["stages"][stage_name]["status"] = "failed"
            state["stages"][stage_name]["finished_at"] = _now()
            state["stages"][stage_name]["error"] = "container restart killed running script"
        _save_state(state)
        log.warning(
            "startup: reset %d orphaned 'running' stages -> 'failed': %s", len(orphans), orphans
        )
    log.info("shellnet-job ready; data dir = %s", DATA_DIR)


@app.get("/healthz")
def healthz() -> dict[str, Any]:
    return {"ok": True, "data_dir": str(DATA_DIR), "now": _now()}


@app.get("/status", dependencies=[Depends(_auth)])
def get_status() -> dict[str, Any]:
    state = _load_state()
    state["files"] = _file_summary()
    return state


@app.get("/files", dependencies=[Depends(_auth)])
def list_files() -> dict[str, Any]:
    return {"data_dir": str(DATA_DIR), "tree": _file_summary(deep=True)}


@app.get("/download", dependencies=[Depends(_auth)])
def download_file(path: str) -> FileResponse:
    """Stream a file from the data volume. path is relative to DATA_DIR."""
    candidate = (DATA_DIR / path).resolve()
    if not str(candidate).startswith(str(DATA_DIR.resolve())):
        raise HTTPException(400, "path must be inside data_dir")
    if not candidate.exists() or not candidate.is_file():
        raise HTTPException(404, f"not found: {path}")
    return FileResponse(candidate, media_type="application/octet-stream", filename=candidate.name)


def _file_summary(deep: bool = False) -> dict[str, Any]:
    out: dict[str, Any] = {}
    targets = [DATA_DIR / "raw", DATA_DIR / "interim", DATA_DIR / "processed", REPORTS_DIR]
    for t in targets:
        if not t.exists():
            continue
        entries = []
        glob = t.rglob("*") if deep else t.glob("*")
        for p in glob:
            if p.is_file():
                entries.append({"path": str(p.relative_to(DATA_DIR)), "bytes": p.stat().st_size})
        entries.sort(key=lambda e: e["path"])
        out[str(t.relative_to(DATA_DIR))] = entries
    return out


@app.get("/logs/{stage}", dependencies=[Depends(_auth)], response_class=PlainTextResponse)
def get_log(stage: str, tail: int = 500) -> str:
    state = _load_state()
    info = state["stages"].get(stage, {})
    log_path = info.get("log")
    if not log_path or not Path(log_path).exists():
        raise HTTPException(404, f"no log for {stage}")
    text = Path(log_path).read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(text[-tail:])


@app.post("/upload-zip", dependencies=[Depends(_auth)])
async def upload_zip(file: UploadFile) -> dict[str, Any]:
    _require_idle("upload")
    _mark("upload", status="running", started_at=_now(), name=file.filename)
    ICIJ_RAW.mkdir(parents=True, exist_ok=True)
    tmp = ZIP_PATH.with_suffix(".zip.partial")
    bytes_written = 0
    try:
        with tmp.open("wb") as fh:
            while True:
                chunk = await file.read(8 * 1024 * 1024)
                if not chunk:
                    break
                fh.write(chunk)
                bytes_written += len(chunk)
        tmp.replace(ZIP_PATH)
    except Exception as exc:  # noqa: BLE001
        tmp.unlink(missing_ok=True)
        _mark("upload", status="failed", finished_at=_now(), error=repr(exc))
        raise HTTPException(500, repr(exc)) from exc
    _mark(
        "upload",
        status="completed",
        finished_at=_now(),
        bytes=bytes_written,
        path=str(ZIP_PATH),
    )
    return {"ok": True, "bytes": bytes_written, "path": str(ZIP_PATH)}


def _do_unzip() -> None:
    started = _now()
    _mark("unzip", status="running", started_at=started)
    try:
        if not ZIP_PATH.exists():
            raise FileNotFoundError(str(ZIP_PATH))
        with zipfile.ZipFile(ZIP_PATH) as zf:
            zf.extractall(ICIJ_RAW)
        csvs = sorted(p.name for p in ICIJ_RAW.glob("*.csv"))
        _mark("unzip", status="completed", finished_at=_now(), csvs=csvs)
    except Exception as exc:  # noqa: BLE001
        _mark("unzip", status="failed", finished_at=_now(), error=repr(exc))


@app.post("/unzip", dependencies=[Depends(_auth)])
def trigger_unzip(bg: BackgroundTasks) -> dict[str, Any]:
    _require_idle("unzip")
    bg.add_task(_do_unzip)
    return {"ok": True, "queued": "unzip"}


def _do_ingest_icij() -> None:
    from shellnet.sources import icij

    started = _now()
    _mark("ingest_icij", status="running", started_at=started)
    try:
        written = icij.ingest(raw_dir=ICIJ_RAW, out_dir=INTERIM_DIR)
        _mark(
            "ingest_icij",
            status="completed",
            finished_at=_now(),
            written={k: str(v) for k, v in written.items()},
        )
    except Exception as exc:  # noqa: BLE001
        log.exception("ingest icij failed")
        _mark("ingest_icij", status="failed", finished_at=_now(), error=repr(exc))


def _do_ingest_script(stage: str, cmd: list[str]) -> None:
    _run_subprocess(stage, cmd, cwd=Path("/app"))


def _do_ingest_gleif_streaming(input_path: Path) -> None:
    from shellnet.sources import gleif_golden_copy

    stage = "ingest_gleif"
    _mark(stage, status="running", started_at=_now(), input=str(input_path))
    try:
        out = gleif_golden_copy.ingest_streaming(input_path, out_dir=INTERIM_DIR)
        _mark(stage, status="completed", finished_at=_now(), output=str(out))
    except Exception as exc:  # noqa: BLE001
        log.exception("ingest gleif streaming failed")
        _mark(stage, status="failed", finished_at=_now(), error=repr(exc))


@app.post("/ingest", dependencies=[Depends(_auth)])
def trigger_ingest(bg: BackgroundTasks, source: str = "icij") -> dict[str, Any]:
    stage = f"ingest_{source}"
    _require_idle(stage)
    if source == "icij":
        bg.add_task(_do_ingest_icij)
    elif source == "gleif":
        gleif_dir = DATA_DIR / "raw" / "gleif"
        inputs = sorted(
            p
            for p in gleif_dir.glob("*")
            if p.is_file() and p.suffix.lower() in {".json", ".jsonl", ".ndjson"}
        )
        if not inputs:
            raise HTTPException(400, f"no gleif inputs under {gleif_dir}")
        target = inputs[0]
        # Files > 200 MB or that match the Golden Copy filename pattern go
        # through the streaming CDF adapter; everything else hits the original
        # v1-API adapter via the script entry point.
        is_golden_copy = (
            "goldencopy" in target.name.lower() or target.stat().st_size > 200 * 1024 * 1024
        )
        if is_golden_copy:
            bg.add_task(_do_ingest_gleif_streaming, target)
        else:
            bg.add_task(
                _do_ingest_script,
                stage,
                ["python", "scripts/ingest_gleif.py", "--input", str(target)],
            )
    elif source == "opensanctions":
        os_dir = DATA_DIR / "raw" / "opensanctions"
        inputs = sorted(
            p
            for p in os_dir.glob("*")
            if p.is_file() and p.suffix.lower() in {".json", ".jsonl", ".ndjson", ".ftm"}
        )
        if not inputs:
            raise HTTPException(400, f"no opensanctions inputs under {os_dir}")
        bg.add_task(
            _do_ingest_script,
            stage,
            ["python", "scripts/ingest_opensanctions.py", "--input", str(inputs[0])],
        )
    else:
        raise HTTPException(400, "source must be icij|gleif|opensanctions")
    return {"ok": True, "queued": stage, "source": source}


def _do_fetch_url(stage: str, url: str, dest: Path) -> None:
    import httpx

    started = _now()
    _mark(stage, status="running", started_at=started, url=url, dest=str(dest))
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        bytes_total = 0
        with httpx.stream("GET", url, follow_redirects=True, timeout=600.0) as r:
            r.raise_for_status()
            with dest.open("wb") as fh:
                for chunk in r.iter_bytes(1 << 20):
                    fh.write(chunk)
                    bytes_total += len(chunk)
        _mark(stage, status="completed", finished_at=_now(), bytes=bytes_total)
    except Exception as exc:  # noqa: BLE001
        log.exception("fetch_url failed")
        _mark(stage, status="failed", finished_at=_now(), error=repr(exc))


_ALLOWED_SCRIPTS = {
    "shared_addresses": ["scripts/report_shared_addresses.py"],
    "coverage": ["scripts/coverage_report.py"],
    "candidate_pairs": ["scripts/generate_candidate_pairs.py"],
    "derive_labels": ["scripts/derive_seed_labels.py"],
    "eval_labels": ["scripts/eval_against_labels.py"],
    "graph_smoke": ["scripts/build_graph_smoke.py"],
    "filter_company": ["scripts/filter_company_table.py"],
    "filter_company_no_gleif": ["scripts/filter_company_table.py", "--drop-sources", "gleif"],
    "extract_gleif_unified": [
        "scripts/filter_company_table.py",
        "--keep-only-sources",
        "gleif",
        "--out",
        "/data/processed/gleif_unified.parquet",
        "--no-keep-unfiltered",
    ],
    "summarize_match": ["scripts/_summarize_match.py"],
    "review_matches": ["scripts/review_matches.py"],
    "review_matches_v2": [
        "scripts/review_matches.py",
        "--matched-csv",
        "/data/reports/generated/icij_os_vs_gleif_v2_matched.csv",
        "--out-md",
        "/data/reports/generated/icij_os_vs_gleif_v2_review.md",
    ],
    "check_schemas": [
        "scripts/_check_schemas.py",
        "/data/processed/company_entities.parquet",
        "/data/processed/gleif_unified.parquet",
    ],
    "rank_clusters": ["scripts/rank_clusters.py"],
    "inspect_edges": ["scripts/_inspect_edges.py"],
    "provenance_503264": ["scripts/provenance_report.py", "503264"],
    "centrality": ["scripts/compute_centrality.py"],
    "explain_cluster": ["scripts/explain_cluster.py"],
    "explain_top_clusters": [
        "scripts/explain_cluster.py",
        "--top-from-rank",
        "20",
        "--rank-parquet",
        "/data/reports/generated/cluster_ranking.parquet",
        "--centrality-parquet",
        "/data/processed/cluster_centrality.parquet",
        "--out-dir",
        "/data/reports/generated",
    ],
    "bundle_evidence": ["scripts/bundle_evidence.py"],
    "rank_by_attention": ["scripts/rank_by_attention.py"],
    "replay_graph": ["scripts/replay_graph.py"],
    "extract_subclusters": ["scripts/extract_subclusters.py"],
    "rank_by_investigative_value": ["scripts/rank_by_investigative_value.py"],
    "rank_by_investigative_value_with_join": [
        "scripts/rank_by_investigative_value.py",
        "--rank-parquet",
        "/data/reports/generated/cluster_ranking.parquet",
        "--centrality-parquet",
        "/data/processed/cluster_centrality.parquet",
        "--out-md",
        "/data/reports/generated/cluster_investigative_ranking.md",
    ],
    "list_match_os_sanctions_vs_icij": [
        "scripts/list_match_os_sanctions_vs_icij.py",
        "--out-dir",
        "/data/processed",
        "--reports-dir",
        "/data/reports/generated",
    ],
    "ingest_opensanctions_default_filtered": [
        "scripts/ingest_opensanctions.py",
        "--input",
        "/data/raw/opensanctions/default.ftm.json",
        "--schemas",
        "Person,Company,Organization,LegalEntity",
        "--out-dir",
        "/data/interim",
    ],
    "ingest_uk_bods": [
        "scripts/ingest_uk_bods.py",
        "--input",
        "/data/raw/openownership/uk_bods.zip",
        "--out-dir",
        "/data/interim",
    ],
    "ingest_gleif_l2": [
        "scripts/ingest_gleif_l2.py",
        "--input",
        "/data/raw/openownership/gleif_bods.zip",
        "--out-dir",
        "/data/interim",
    ],
    "extract_uk_psc_dob": [
        "scripts/extract_uk_psc_dob.py",
        "--input",
        "/data/raw/openownership/uk_bods.zip",
        "--out",
        "/data/processed/uk_psc_dob.parquet",
    ],
    "enrich_match_with_dob": [
        "scripts/enrich_match_with_dob.py",
        "/data/reports/generated/list_match_os_sanctions_vs_icij_matched.csv",
        "--os-parquet",
        "/data/interim/opensanctions_entities.parquet",
        "--uk-dob",
        "/data/processed/uk_psc_dob.parquet",
        "--out",
        "/data/reports/generated/matched_dob.csv",
    ],
    "score_prior_coverage": [
        "scripts/score_prior_coverage.py",
        "/data/reports/generated/matched_dob.csv",
        "--out",
        "/data/reports/generated/matched_dob_scored.csv",
    ],
    "filter_match_survivors": [
        "scripts/filter_match_survivors.py",
        "/data/reports/generated/matched_dob_scored.csv",
        "--out",
        "/data/reports/generated/investigative_grade_survivors.csv",
    ],
    "inspect_uk_bods_zip": [
        "scripts/_inspect_zip.py",
        "/data/raw/openownership/uk_bods.zip",
    ],
    "inspect_uk_bods_schemas": [
        "scripts/_inspect_bods_schemas.py",
        "/data/raw/openownership/uk_bods.zip",
    ],
    "sanctions_overlay": [
        "scripts/build_sanctions_overlay.py",
        "--os-parquet",
        "/data/interim/opensanctions_entities.parquet",
        "--out",
        "/data/processed/sanctions_overlay.parquet",
    ],
    "sanctions_overlay_external": [
        "scripts/build_sanctions_overlay.py",
        "--os-parquet",
        "/data/interim/opensanctions_entities.parquet",
        "--external",
        "/data/raw/sanctions_reconciliation/records.parquet",
        "--out",
        "/data/processed/sanctions_overlay.parquet",
    ],
    "cross_ref_disqualified": [
        "scripts/cross_ref_disqualified.py",
        "--disqualified",
        "/data/interim/uk_disqualified_directors.parquet",
        "--person-table",
        "/data/processed/person_entities.parquet",
        "--company-table",
        "/data/processed/company_entities.parquet",
        "--out",
        "/data/processed/disqualified_overlaps.parquet",
    ],
    "build_officer_overlap": [
        "scripts/build_officer_overlap.py",
        "--person-table",
        "/data/processed/person_entities.parquet",
        "--out",
        "/data/processed/officer_overlap.parquet",
    ],
    "list_match_icij_vs_uk_psc": [
        "scripts/list_match_icij_vs_uk_psc.py",
        "--person-table",
        "/data/processed/person_entities.parquet",
        "--out-dir",
        "/data/processed",
        "--reports-dir",
        "/data/reports/generated",
    ],
    "build_non_obviousness_score": [
        "scripts/build_non_obviousness_score.py",
        "--dossier-parquet",
        "/data/processed/rare_officer_dossiers.parquet",
        "--person-table",
        "/data/processed/person_entities.parquet",
        "--edges",
        "/data/interim/icij_edges.parquet",
        "--out-parquet",
        "/data/processed/non_obviousness_scores.parquet",
        "--out-summary",
        "/data/processed/non_obviousness_summary.json",
    ],
    "build_latent_clusters": [
        "scripts/build_latent_clusters.py",
        "--edges",
        "/data/interim/icij_edges.parquet",
        "--entities",
        "/data/interim/icij_entities.parquet",
        "--sanctions-overlay",
        "/data/processed/sanctions_overlay.parquet",
        "--out-parquet",
        "/data/processed/latent_clusters.parquet",
        "--out-summary",
        "/data/processed/latent_clusters_summary.json",
    ],
    "build_temporal_patterns": [
        "scripts/build_temporal_patterns.py",
        "--entities",
        "/data/interim/icij_entities.parquet",
        "--out-resurrections",
        "/data/processed/temporal_resurrections.parquet",
        "--out-bursts",
        "/data/processed/temporal_bursts.parquet",
        "--out-anchors",
        "/data/processed/temporal_long_lived.parquet",
        "--out-summary",
        "/data/processed/temporal_patterns_summary.json",
    ],
    # Validation pack is driven via the parameterized /run-validation-pack
    # endpoint instead of an allowlist entry — it takes (community_id, person)
    # at request time so any cluster from the queue can be profiled.
    "build_validation_queue": [
        "scripts/build_validation_queue.py",
        "--cluster-scored",
        "/data/processed/confidence_cluster_scored.parquet",
        "--anomalies",
        "/data/processed/confidence_community_anomalies.parquet",
        "--communities",
        "/data/processed/confidence_communities.parquet",
        "--entities",
        "/data/interim/icij_entities.parquet",
        "--officers",
        "/data/interim/icij_officers.parquet",
        "--os-persons",
        "/data/processed/os_sanctioned_persons.parquet",
        "--gleif",
        "/data/interim/gleif_l2_relationships.parquet",
        "--uk-psc",
        "/data/processed/uk_psc_dob.parquet",
        "--uk-disq",
        "/data/interim/uk_disqualified_directors.parquet",
        "--out-parquet",
        "/data/processed/validation_queue.parquet",
        "--out-summary",
        "/data/processed/validation_queue_summary.json",
        "--top-n",
        "20",
    ],
    "build_validation_queue_top50": [
        "scripts/build_validation_queue.py",
        "--cluster-scored",
        "/data/processed/confidence_cluster_scored.parquet",
        "--anomalies",
        "/data/processed/confidence_community_anomalies.parquet",
        "--communities",
        "/data/processed/confidence_communities.parquet",
        "--entities",
        "/data/interim/icij_entities.parquet",
        "--officers",
        "/data/interim/icij_officers.parquet",
        "--os-persons",
        "/data/processed/os_sanctioned_persons.parquet",
        "--gleif",
        "/data/interim/gleif_l2_relationships.parquet",
        "--uk-psc",
        "/data/processed/uk_psc_dob.parquet",
        "--uk-disq",
        "/data/interim/uk_disqualified_directors.parquet",
        "--out-parquet",
        "/data/processed/validation_queue.parquet",
        "--out-summary",
        "/data/processed/validation_queue_summary.json",
        "--top-n",
        "50",
    ],
    "build_top_candidates_walkthrough": [
        "scripts/build_top_candidates_walkthrough.py",
        "--entities",
        "/data/interim/icij_entities.parquet",
        "--edges",
        "/data/interim/icij_edges.parquet",
        "--structure-summary",
        "/data/processed/structure_benchmark_summary.json",
        "--non-obviousness-summary",
        "/data/processed/non_obviousness_summary.json",
        "--latent-clusters",
        "/data/processed/latent_clusters.parquet",
        "--os-persons",
        "/data/processed/os_sanctioned_persons.parquet",
        "--gleif",
        "/data/interim/gleif_l2_relationships.parquet",
        "--uk-psc",
        "/data/processed/uk_psc_dob.parquet",
        "--uk-disq",
        "/data/interim/uk_disqualified_directors.parquet",
        "--out-summary",
        "/data/processed/top_candidates_walkthrough.json",
    ],
    "build_discovery_advantage": [
        "scripts/build_discovery_advantage.py",
        "--inputs-dir",
        "/data/processed",
        "--out-summary",
        "/data/processed/discovery_advantage_summary.json",
    ],
    "build_structure_benchmark": [
        "scripts/build_structure_benchmark.py",
        "--edges",
        "/data/interim/icij_edges.parquet",
        "--entities",
        "/data/interim/icij_entities.parquet",
        "--out-summary",
        "/data/processed/structure_benchmark_summary.json",
    ],
    "build_confidence_graph": [
        "scripts/build_confidence_graph.py",
        "--edges",
        "/data/interim/icij_edges.parquet",
        "--oo-uk-psc-edges",
        "/data/processed/oo_uk_psc_relationships.parquet",
        "--dossier-parquet",
        "/data/processed/rare_officer_dossiers.parquet",
        "--out-edges",
        "/data/processed/confidence_graph_edges.parquet",
        "--out-communities",
        "/data/processed/confidence_communities.parquet",
        "--out-summary",
        "/data/processed/confidence_graph_summary.json",
    ],
    # Phase 3: cross-jurisdictional name-lineage twin detector. Heavy join
    # across ICIJ entities + the OO UK PSC entities parquet (~13.9M rows).
    "detect_cross_jurisdiction_twins": [
        "scripts/detect_cross_jurisdiction_twins.py",
        "--icij-entities",
        "/data/interim/icij_entities.parquet",
        "--oo-entities",
        "/data/processed/oo_uk_psc_entities.parquet",
        "--out",
        "/data/processed/cross_jurisdiction_twins.parquet",
        # At 5.79M OO rows the abbreviation pre-filter OOMs Railway
        # before any semi-join can shrink the frames. Strict_root alone
        # still catches PROBUTEC-style direct twins, which is the
        # roadmap target.
        "--no-abbrev",
    ],
    # Phase 6: bulk SEC EDGAR 13D/G ingest. Year/quarter are baked in;
    # bump them in a PR when re-running for a different window. Caps the
    # fan-out at 5000 filings so the per-filing SGML fetches stay sane.
    # Phase 10: name-match SEC issuers/filers against ICIJ US entities to
    # emit sec:CIK <-> icij:uid bridge edges. Without this, the SEC
    # corpus sits in a topologically disconnected namespace.
    # Phase 17a — enrich SEC filer CIKs with submissions metadata
    # (SIC code, filer category, US ticker). The bridge job below
    # consumes this parquet to drop large-cap false positives.
    "enrich_sec_filer_metadata": [
        "scripts/enrich_sec_filer_metadata.py",
        "--sec-edges",
        "/data/processed/sec_13dg_edges.parquet",
        "--out",
        "/data/processed/sec_filer_metadata.parquet",
    ],
    "bridge_sec_icij_by_name": [
        "scripts/bridge_sec_icij_by_name.py",
        "--sec-edges",
        "/data/processed/sec_13dg_edges.parquet",
        "--icij-entities",
        "/data/interim/icij_entities.parquet",
        # Phase 17a: load the SEC submissions metadata so we can drop
        # bridge rows where the filer is a Large Accelerated Filer,
        # has a US ticker, or has a blocked SIC code (banks, airlines,
        # insurers, telecoms, utilities).
        "--filer-metadata",
        "/data/processed/sec_filer_metadata.parquet",
        # Phase 15a (GoldenMatch fuzzy) is implemented but disabled.
        # See docs/phase-17-bridge-disambiguation-roadmap.md — the
        # fuzzy scorer can't disambiguate name-coincidence false
        # positives (Royal Bank of Canada, Delta Air Lines, Equitable
        # Holdings) from real offshore-vehicle bridges; it just scores
        # both at 1.0. The disambiguation signal is jurisdiction /
        # SIC code / officer overlap, not name similarity. Leaving the
        # default-off behaviour until Phase 17 adds that gate.
        "--out",
        "/data/processed/sec_icij_bridges.parquet",
    ],
    "ingest_sec_13dg_bulk": [
        "scripts/ingest_sec_13dg_bulk.py",
        # Phase 13: ingest 4 quarters instead of 1. Cap is per-quarter,
        # so max total filings = 4 x 5000 = 20,000. Rate-limited at
        # ~9 req/s, that's ~37 min Railway-side.
        "--year-quarter",
        "2025/1",
        "2025/2",
        "2025/3",
        "2025/4",
        "--out",
        "/data/processed/sec_13dg_edges.parquet",
        "--limit",
        "5000",
        # SEC EDGAR's fair-use policy: UA must be "Name Email" — too many
        # words or a URL inside the UA returns 403.
        "--user-agent",
        "Ben Severn bsevern@mjhlifesciences.com",
    ],
    # Phase 16: emit SEC bridge endpoints as extra seeds. Putting
    # the SEC side of each Phase-10 bridge into hop 0 of the next
    # recluster lets the 3-hop BFS walk SEC-to-SEC beneficial_owner_of
    # edges from each bridge landing site.
    "select_bridge_endpoints": [
        "scripts/select_bridge_endpoints.py",
        "--bridges",
        "/data/processed/sec_icij_bridges.parquet",
        "--out",
        "/data/processed/bridge_endpoint_seeds.parquet",
    ],
    # Phase 11: select top-N anomaly communities' member UIDs from the
    # previous recluster as extra seeds for the next pass.
    "select_anomaly_seeds": [
        "scripts/select_anomaly_seeds.py",
        "--anomalies",
        "/data/processed/confidence_community_anomalies.parquet",
        "--communities",
        "/data/processed/confidence_communities.parquet",
        "--top-n",
        "10",
        "--min-anomaly-score",
        "0.5",
        "--threshold",
        "0.9",
        "--out",
        "/data/processed/anomaly_seed_uids.parquet",
    ],
    # Phase 7: same graph builder, plus Phase-3 twin edges + Phase-6 SEC
    # 13D/G edges unioned into the ICIJ corpus before community detection.
    "build_confidence_graph_expanded": [
        "scripts/build_confidence_graph.py",
        "--edges",
        "/data/interim/icij_edges.parquet",
        "--twin-edges",
        "/data/processed/cross_jurisdiction_twins.parquet",
        "--sec-13dg-edges",
        "/data/processed/sec_13dg_edges.parquet",
        "--sec-icij-bridges",
        "/data/processed/sec_icij_bridges.parquet",
        # Phases 11 + 16: extra-seed parquets. Each gets its own
        # --extra-seeds invocation. Missing files are skipped with a
        # warning so a first-deploy still runs.
        "--extra-seeds",
        "/data/processed/anomaly_seed_uids.parquet",
        "--extra-seeds",
        "/data/processed/bridge_endpoint_seeds.parquet",
        # Phase 12: 3-hop BFS, deep-pruning disabled (min-degree=1) so
        # the degree-1 SEC bridges survive. Backed max-nodes off from
        # 50k to 30k — at 50k the BFS hit a polars perf cliff where
        # is_in(list) on the 3.3M-edge frame with tens of thousands of
        # frontier UIDs took >40 min without finishing. 30k is the
        # sweet spot: 2x the 16k cap that worked, well under the cliff.
        "--hops",
        "3",
        "--min-frontier-degree-deep",
        "1",
        "--max-nodes",
        "30000",
        "--dossier-parquet",
        "/data/processed/rare_officer_dossiers.parquet",
        "--out-edges",
        "/data/processed/confidence_graph_edges.parquet",
        "--out-communities",
        "/data/processed/confidence_communities.parquet",
        "--out-summary",
        "/data/processed/confidence_graph_summary.json",
    ],
    "build_adversarial_benchmark": [
        "scripts/build_adversarial_benchmark.py",
        "--discovery-parquet",
        "/data/processed/discovery_lift.parquet",
        "--out-parquet",
        "/data/processed/adversarial_benchmark.parquet",
        "--out-summary",
        "/data/processed/adversarial_benchmark_summary.json",
    ],
    "build_baseline_comparison": [
        "scripts/build_baseline_comparison.py",
        "--discovery-parquet",
        "/data/processed/discovery_lift.parquet",
        "--person-table",
        "/data/processed/person_entities.parquet",
        "--dossier-parquet",
        "/data/processed/rare_officer_dossiers.parquet",
        "--out-parquet",
        "/data/processed/baseline_comparison.parquet",
        "--out-summary",
        "/data/processed/baseline_comparison_summary.json",
    ],
    "build_calibration_benchmark": [
        "scripts/build_calibration_benchmark.py",
        "--matched-csv",
        "/data/reports/generated/matched_dob_scored.csv",
        "--out-metrics",
        "/data/processed/calibration_metrics.parquet",
        "--out-calibrator",
        "/data/processed/erscore_calibrator.json",
        "--out-summary",
        "/data/processed/calibration_summary.json",
    ],
    "build_discovery_lift": [
        "scripts/build_discovery_lift.py",
        "--person-table",
        "/data/processed/person_entities.parquet",
        "--dossier-parquet",
        "/data/processed/rare_officer_dossiers.parquet",
        "--out-parquet",
        "/data/processed/discovery_lift.parquet",
        "--out-summary",
        "/data/processed/discovery_lift_summary.json",
    ],
    "build_rare_officer_dossiers": [
        "scripts/build_rare_officer_dossiers.py",
        "--officer-overlap",
        "/data/processed/officer_overlap.parquet",
        "--person-table",
        "/data/processed/person_entities.parquet",
        "--icij-edges",
        "/data/interim/icij_edges.parquet",
        "--company-table",
        "/data/processed/company_entities.parquet",
        "--sanctions-overlay",
        "/data/processed/sanctions_overlay.parquet",
        "--out",
        "/data/processed/rare_officer_dossiers.parquet",
    ],
    "build_join_novelty_report": [
        "scripts/build_join_novelty_report.py",
        "--icij-os-vs-gleif",
        "/data/reports/generated/icij_os_vs_gleif_matched.csv",
        "--matched-dob",
        "/data/reports/generated/matched_dob_scored.csv",
        "--overlay",
        "/data/processed/sanctions_overlay.parquet",
        "--disqualified",
        "/data/interim/uk_disqualified_directors.parquet",
        "--icij-psc-matched",
        "/data/reports/generated/list_match_icij_vs_uk_psc_matched.csv",
        "--officer-overlap",
        "/data/processed/officer_overlap.parquet",
        "--disqualified-overlaps",
        "/data/processed/disqualified_overlaps.parquet",
        "--out-parquet",
        "/data/processed/join_novelty.parquet",
        "--out-summary",
        "/data/processed/join_novelty_summary.json",
    ],
    "build_reconcile_shortlists": [
        "scripts/build_reconcile_shortlists.py",
        "--overlay",
        "/data/processed/sanctions_overlay.parquet",
        "--out-dir",
        "/data/reports/generated",
    ],
    "reconcile_equasis": [
        "scripts/reconcile_equasis.py",
        "--input",
        "/data/reports/generated/shortlist_imos.csv",
        "--imo-field",
        "IMO",
        "--out",
        "/data/reports/generated/shortlist_imos_enriched.csv",
    ],
    "reconcile_ru_companies": [
        "scripts/reconcile_ru_companies.py",
        "--input",
        "/data/reports/generated/ru_shortlist.csv",
        "--name-field",
        "CompanyName",
        "--out",
        "/data/reports/generated/ru_shortlist_enriched.csv",
    ],
    "reconcile_sec_filings": [
        "scripts/reconcile_sec_filings.py",
        "--input",
        "/data/reports/generated/us_shortlist.csv",
        "--name-field",
        "name",
        "--filing-type",
        "10-K",
        "--out",
        "/data/reports/generated/us_shortlist_sec.csv",
    ],
    "scrape_uk_disqualified_directors": [
        "scripts/scrape_disqualified_directors.py",
        "--out",
        "/data/raw/scrapers/disqualified-directors/disqualified-directors.csv",
    ],
    "ingest_uk_disqualified_directors": [
        "scripts/ingest_uk_disqualified_directors.py",
        "--input",
        "/data/raw/scrapers/disqualified-directors/disqualified-directors.csv",
        "--out-dir",
        "/data/interim",
    ],
    "scrape_mp_interests": [
        "scripts/scrape_mp_interests.py",
        "--out",
        "/data/raw/scrapers/members-financial-interests/members-financial-interests.csv",
    ],
    "ingest_openownership_uk_psc": [
        "scripts/ingest_openownership_uk_psc.py",
        "--bundle-zip",
        "/data/raw/openownership/uk_psc_v0_4.zip",
        "--out-dir",
        "/data/processed",
    ],
    # Investigative probe for the Apeiron / Angermayer drill-down. The
    # slug + needle args are passed via the workflow_dispatch inputs
    # so the same allowlist entry can serve future per-candidate
    # probes without code changes.
    "probe_psc_apeiron_angermayer": [
        "scripts/probe_psc_for_names.py",
        "--slug",
        "apeiron_angermayer",
        "--needle",
        "apeiron",
        "--needle",
        "angermayer",
        "--needle",
        "jorg werner",
        "--needle",
        "parker.*turner",
        "--needle",
        "gewiet",
    ],
    # Trace the PSCs of Apeiron Investment Group Ltd (Companies House
    # #10339937 = oo:gb-coh-10339937) and its sister variant
    # #12587022. The named-substring probe missed Angermayer; this
    # asks "who DOES PSC declare for these specific companies?"
    "probe_psc_apeiron_ig_uids": [
        "scripts/probe_psc_by_uid.py",
        "--slug",
        "apeiron_ig_uids",
        "--uid",
        "oo:gb-coh-10339937",
        "--uid",
        "oo:gb-coh-12587022",
    ],
    # Resolve corporate-PSC UIDs to names by substring-matching the
    # focal company numbers across the entire entities + persons table
    # (catches synthetic oo:gb-coh-ent-* UIDs that don't appear in the
    # standard entity_uid join).
    "probe_psc_apeiron_corporate": [
        "scripts/probe_psc_corporate_uids.py",
        "--slug",
        "apeiron_corporate",
        "--co-number",
        "10339937",
        "--co-number",
        "12587022",
        "--co-number",
        "00c51843",
    ],
    # Three high-stakes story probes in one run: sanctions overlap with
    # SEC filers, Marinakis-family ICIJ expansion, PEP overlap with SEC.
    "probe_high_stakes_bridges": [
        "scripts/probe_high_stakes_bridges.py",
    ],
    # Cross-reference UK disqualified directors against UK PSC persons
    # (by name+DOB, identity-grade) and ICIJ Paradise Papers officers
    # (name-only, candidate-grade). Two JSONs out.
    "probe_disqualified_overlap": [
        "scripts/probe_disqualified_overlap.py",
    ],
    # Diagnostic: what does the disqualified DOB column actually look
    # like, plus full record for the two ICIJ candidates Sajid Bashir
    # + Santokh Singh.
    "probe_inspect_disq_dob": [
        "scripts/probe_inspect_disq_dob.py",
    ],
    # Deep-dive on the substantive lead: all ICIJ records naming
    # 'Sajid Bashir', plus entities + edges connected to him, so we
    # can see if the Panama Papers Sajid Bashir is the same person
    # as the UK-disqualified one (Huddersfield, DOB 1993-01-26).
    "probe_sajid_bashir_icij": [
        "scripts/probe_sajid_bashir_icij.py",
    ],
    # Look up icij:14090036 — Sajid Bashir's registered-address node in
    # Panama Papers. The address is the only remaining disambiguator
    # we can pull on the ICIJ side (no DOB available there).
    "probe_icij_address_bashir": [
        "scripts/probe_icij_address_lookup.py",
        "--source-id",
        "14090036",
        "--slug",
        "bashir_address",
    ],
    # HM Land Registry OCOD ingest + cross-reference. Requires the
    # operator to have manually downloaded the OCOD CSV from
    # use-land-property-data.service.gov.uk and dropped it at
    # /data/raw/hmlr/OCOD_FULL.csv on the Railway volume.
    # See docs/sources/hmlr_ocod.md for the full flow.
    "ingest_hmlr_ocod": [
        "scripts/ingest_hmlr_ocod.py",
        "--input",
        "/data/raw/hmlr/OCOD_FULL.csv",
        "--out",
        "/data/processed/hmlr_ocod.parquet",
    ],
    "probe_hmlr_ocod_crossref": [
        "scripts/probe_hmlr_ocod_crossref.py",
    ],
    # Case-study deep-dive on the three BVI-jurisdiction-confirmed
    # ICIJ ∩ OCOD bridges (SULGER ASSETS, JAMERS INTERNATIONAL,
    # CARDINAL INVESTMENT SERVICES). Pulls full ICIJ network + UK
    # property history per candidate.
    "probe_bvi_confirmed_deepdive": [
        "scripts/probe_bvi_confirmed_deepdive.py",
    ],
    # Expand the Emanuela Barilla / Maya International Foundation
    # ICIJ network — every entity they control, every co-officer at
    # those entities, every UK property the network owns.
    "probe_barilla_network": [
        "scripts/probe_barilla_network.py",
    ],
    # Address-centred subgraph: every reference to 128 Ebury Street
    # SW1W 9QQ across ICIJ + HMLR OCOD. Surfaces the corporate-
    # services hub that administers multiple Mossack Fonseca-era
    # offshore-property-holding companies.
    "probe_128_ebury_hub": [
        "scripts/probe_128_ebury_hub.py",
    ],
    # Expand the Tohme/Sarkis family ICIJ network — every entity any
    # Tohme/Sarkis-named officer controls, every co-officer, every UK
    # property owned by entities they control.
    "probe_tohme_sarkis_network": [
        "scripts/probe_tohme_sarkis_network.py",
    ],
    # Expand the Gulbenkian-dynasty ICIJ network (Micael Paul Sarkis
    # Gulbenkian + three Malta-incorporated entities surfaced by the
    # Tohme/Sarkis probe).
    "probe_gulbenkian_network": [
        "scripts/probe_gulbenkian_network.py",
    ],
    # Generalise the 128 Ebury hub finding — find every UK address
    # that appears as proprietor_address for >=20 OCOD overseas-
    # company titles. For each, count distinct proprietors, country
    # mix, and ICIJ Panama/Paradise Papers overlap.
    "probe_ocod_address_hubs": [
        "scripts/probe_ocod_address_hubs.py",
    ],
    # Deep-dive on the top-10 hubs in one pass: per hub, every OCOD
    # title + price + date + country mix + postcode hotspots +
    # acquisition timeline + portfolio value + ICIJ matches.
    "probe_hub_deepdive": [
        "scripts/probe_hub_deepdive.py",
    ],
    # Three US-angle probes in one pass:
    # A. US-incorporated proprietors in UK OCOD
    # B. Sanctioned-person → ICIJ officer → OCOD overlap
    # C. SEC 13D/G filer → ICIJ entity (filtered)
    "probe_us_angles": [
        "scripts/probe_us_angles.py",
    ],
    # Ingest NYC ACRIS Master + Parties + Legals into parquet (~10-20
    # min Railway-side). Enables NYC equivalent of UK OCOD analysis.
    "ingest_nyc_acris": [
        "scripts/ingest_nyc_acris.py",
    ],
    # Scrape FinCEN enforcement-actions index into parquet.
    "ingest_fincen_enforcement": [
        "scripts/ingest_fincen_enforcement.py",
    ],
    # NYC ACRIS grantees cross-referenced against ICIJ + OFAC SDN.
    # The NYC equivalent of the UK OCOD x ICIJ x ROE join.
    "probe_nyc_acris_offshore": [
        "scripts/probe_nyc_acris_offshore.py",
    ],
    # Disqualified UK directors x ICIJ officers x OCOD UK property.
    # Surfaces potential s.11 CDDA 1986 breaches (disqualified
    # person involved in offshore company management with UK
    # property holdings). Output is a lead list, not an accusation.
    "probe_disqualified_wrongdoing": [
        "scripts/probe_disqualified_wrongdoing.py",
    ],
    # Pull the full UK CH disqualified-directors register from
    # OpenSanctions (~3-5k entities vs the partial 222-row scrape).
    "ingest_os_gb_coh_disqualified": [
        "scripts/ingest_os_gb_coh_disqualified.py",
    ],
    # Build the ranked verification queue for the disqualified x ICIJ
    # name-matches. Score = 1 / (same-name count on each side).
    "probe_disqualified_verification_queue": [
        "scripts/probe_disqualified_verification_queue.py",
    ],
    # UK Register of Overseas Entities — promote the locally-extracted
    # OE-prefixed CH parquet to the Railway data volume.
    "ingest_uk_ch_overseas_entities": [
        "scripts/ingest_uk_ch_overseas_entities.py",
    ],
    # Anti-join OCOD foreign owners vs UK CH OE registry. Surfaces
    # potentially non-compliant proprietors under ECTEA 2022 s.34.
    "probe_roe_noncompliance": [
        "scripts/probe_roe_noncompliance.py",
    ],
    # Drill into the 5,324 non-compliant proprietors. Cross-link
    # against ICIJ leaks + OpenSanctions, plus geographic + date
    # concentration of the 12,240 non-compliant titles.
    "probe_roe_noncompliance_drill": [
        "scripts/probe_roe_noncompliance_drill.py",
    ],
    # Personalize the non-compliance story: ICIJ officer enrichment
    # (named people behind the entities) + OS sanctions/PEP overlap
    # with topic-filter to avoid OOM on the 2.7 GB consolidated file
    # + auto-detected acquisition-date split (pre/post Aug 2022).
    "probe_roe_noncompliance_personalize": [
        "scripts/probe_roe_noncompliance_personalize.py",
    ],
    # Deepdive on the FENLAND / Fenech (Malta) thread — the largest
    # single non-compliant owner (313 UK titles, named in both Panama
    # and Paradise Papers).
    "probe_fenland_deepdive": [
        "scripts/probe_fenland_deepdive.py",
    ],
    # Per-target deepdive for non-compliant entities of interest.
    # Currently runs for: edokpolo (BVI family cluster) + the three
    # high-confidence OS sanction hits (Embassy Development, Harmony
    # Ridge, Ledra Trustee).
    "probe_named_threads_deepdive": [
        "scripts/probe_named_threads_deepdive.py",
    ],
    # Tightened ROE non-compliance matcher with a fuzzy token-set
    # second pass to drop name-form false positives (Deutsche Bank
    # AG vs Aktiengesellschaft etc.).
    "probe_roe_noncompliance_strict": [
        "scripts/probe_roe_noncompliance_strict.py",
    ],
    # Expand each named-thread case study: full title list,
    # proprietor-address co-tenancy across the non-compliant set,
    # ICIJ officer-edge expansion (what other entities each named
    # individual is tied to in the leak graph).
    "probe_named_threads_expand": [
        "scripts/probe_named_threads_expand.py",
    ],
    # Verify the Ledra-Metalloinvest link surfaced by the named-threads
    # expand: pull full ICIJ records for the Metalloinvest-named BVI
    # entity, plus OS records for Metalloinvest + Usmanov, plus direct
    # ICIJ edges between any Usmanov officer and the BVI entity.
    "probe_metalloinvest_verify": [
        "scripts/probe_metalloinvest_verify.py",
    ],
    # Geographic deepdive on the SE1 non-compliant cluster (690 titles,
    # the largest single outward-postcode cluster). Top proprietors,
    # building-level concentration, sector breakdown, country mix,
    # ICIJ overlap, acquisition-year distribution.
    "probe_se1_deepdive": [
        "scripts/probe_se1_deepdive.py",
    ],
}


def _do_script(stage: str, args: list[str]) -> None:
    _run_subprocess(stage, args, cwd=Path("/app"))


@app.post("/run-script", dependencies=[Depends(_auth)])
def trigger_run_script(bg: BackgroundTasks, name: str) -> dict[str, Any]:
    if name not in _ALLOWED_SCRIPTS:
        raise HTTPException(400, f"name must be one of {sorted(_ALLOWED_SCRIPTS)}")
    stage = f"script_{name}"
    _require_idle(stage)
    bg.add_task(_do_script, stage, ["python", *_ALLOWED_SCRIPTS[name]])
    return {"ok": True, "queued": stage}


# Strict whitelist for the parameterized /run-validation-pack endpoint:
# community_id must be a non-negative int, and person is a name that
# contains only letters / spaces / hyphens / apostrophes / periods.
# This avoids shell injection without depending on the subprocess call
# (we already pass argv as a list, so there's no shell, but defense in
# depth on a public-facing endpoint is cheap).
_PERSON_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z .'\-]{1,80}$")


@app.post("/run-validation-pack", dependencies=[Depends(_auth)])
def trigger_run_validation_pack(
    bg: BackgroundTasks,
    community_id: int,
    person: str,
    threshold: float = 0.9,
) -> dict[str, Any]:
    """Run scripts/build_validation_pack.py for an arbitrary (cluster, person)
    pair.

    Outputs land under ``/data/validation_packs/cluster_<id>/`` on the
    Railway volume; the GitHub workflow downloads them and commits to main.
    """

    if community_id < 0 or community_id > 1_000_000:
        raise HTTPException(400, "community_id out of range")
    if not _PERSON_NAME_RE.match(person):
        raise HTTPException(400, "person must match ^[A-Za-z][A-Za-z .'-]{1,80}$")
    if not (0.0 <= threshold <= 1.0):
        raise HTTPException(400, "threshold must be in [0.0, 1.0]")

    out_dir = f"/data/validation_packs/cluster_{community_id}"
    args = [
        "scripts/build_validation_pack.py",
        "--community-id",
        str(community_id),
        "--person",
        person,
        "--threshold",
        str(threshold),
        "--reports-data-dir",
        "/data/processed",
        "--interim-dir",
        "/data/interim",
        "--processed-dir",
        "/data/processed",
        "--dossiers-dir",
        "/app/docs/reports/dossiers",
        "--out-dir",
        out_dir,
    ]
    stage = f"script_build_validation_pack_cluster_{community_id}"
    _require_idle(stage)
    bg.add_task(_do_script, stage, ["python", *args])
    return {"ok": True, "queued": stage, "out_dir": out_dir}


@app.post("/run-aleph-bundle", dependencies=[Depends(_auth)])
def trigger_run_aleph_bundle(
    bg: BackgroundTasks,
    community_id: int,
    person: str,
) -> dict[str, Any]:
    """Build an OpenAleph ingest bundle (zip) from an existing validation pack.

    Output lands at
    ``/data/validation_packs/cluster_<id>/data/cluster_<id>_aleph_bundle.zip``.
    """

    if community_id < 0 or community_id > 1_000_000:
        raise HTTPException(400, "community_id out of range")
    if not _PERSON_NAME_RE.match(person):
        raise HTTPException(400, "person must match ^[A-Za-z][A-Za-z .'-]{1,80}$")

    pack_dir = f"/data/validation_packs/cluster_{community_id}"
    args = [
        "scripts/build_openaleph_bundle.py",
        "--community-id",
        str(community_id),
        "--person",
        person,
        "--pack-dir",
        pack_dir,
    ]
    stage = f"script_aleph_bundle_cluster_{community_id}"
    _require_idle(stage)
    bg.add_task(_do_script, stage, ["python", *args])
    return {"ok": True, "queued": stage, "pack_dir": pack_dir}


@app.post("/run-ftm-export", dependencies=[Depends(_auth)])
def trigger_run_ftm_export(
    bg: BackgroundTasks,
    community_id: int,
    person: str,
) -> dict[str, Any]:
    """Export an existing validation pack to FollowTheMoney ndjson.

    Output lands at ``/data/validation_packs/cluster_<id>/data/cluster_<id>_ftm.json``.
    """

    if community_id < 0 or community_id > 1_000_000:
        raise HTTPException(400, "community_id out of range")
    if not _PERSON_NAME_RE.match(person):
        raise HTTPException(400, "person must match ^[A-Za-z][A-Za-z .'-]{1,80}$")

    pack_dir = f"/data/validation_packs/cluster_{community_id}"
    args = [
        "scripts/export_validation_pack_ftm.py",
        "--community-id",
        str(community_id),
        "--person",
        person,
        "--pack-dir",
        pack_dir,
    ]
    stage = f"script_ftm_export_cluster_{community_id}"
    _require_idle(stage)
    bg.add_task(_do_script, stage, ["python", *args])
    return {"ok": True, "queued": stage, "pack_dir": pack_dir}


@app.post("/run-corroboration", dependencies=[Depends(_auth)])
def trigger_run_corroboration(
    bg: BackgroundTasks,
    community_id: int,
    person: str,
    run_external_search: bool = True,
    max_queries: int = 60,
) -> dict[str, Any]:
    """Second-stage corroboration for an existing validation pack.

    Reads the pack at ``/data/validation_packs/cluster_<id>/`` and writes
    research brief + timeline + narratives + ledgers back into the same
    directory. External search via Tavily requires ``TAVILY_API_KEY``
    in the Railway env.
    """

    if community_id < 0 or community_id > 1_000_000:
        raise HTTPException(400, "community_id out of range")
    if not _PERSON_NAME_RE.match(person):
        raise HTTPException(400, "person must match ^[A-Za-z][A-Za-z .'-]{1,80}$")
    if max_queries < 0 or max_queries > 500:
        raise HTTPException(400, "max_queries must be in [0, 500]")

    pack_dir = f"/data/validation_packs/cluster_{community_id}"
    args = [
        "scripts/corroborate_validation_pack.py",
        "--community-id",
        str(community_id),
        "--person",
        person,
        "--pack-dir",
        pack_dir,
        "--max-queries",
        str(max_queries),
    ]
    if run_external_search:
        args.append("--run-external-search")
    stage = f"script_corroborate_cluster_{community_id}"
    _require_idle(stage)
    bg.add_task(_do_script, stage, ["python", *args])
    return {"ok": True, "queued": stage, "pack_dir": pack_dir}


def _do_unzip_file(stage: str, path: Path) -> None:
    started = _now()
    _mark(stage, status="running", started_at=started, path=str(path))
    try:
        if not path.exists():
            raise FileNotFoundError(str(path))
        with zipfile.ZipFile(path) as zf:
            zf.extractall(path.parent)
            names = zf.namelist()
        _mark(stage, status="completed", finished_at=_now(), extracted=names[:20], count=len(names))
    except Exception as exc:  # noqa: BLE001
        log.exception("unzip_file failed")
        _mark(stage, status="failed", finished_at=_now(), error=repr(exc))


# Fixed whitelist of upload slots. Each slot is a code-controlled
# destination path; the caller picks a slot by name from this dict
# rather than supplying an arbitrary path. Defends against
# path-injection at the schema layer (no taint flow from user input
# to filesystem path).
_UPLOAD_SLOTS: dict[str, Path] = {
    "hmlr_ocod_zip": DATA_DIR / "raw" / "hmlr" / "OCOD_FULL.zip",
    "hmlr_ocod_csv": DATA_DIR / "raw" / "hmlr" / "OCOD_FULL.csv",
    "hmlr_ccod_zip": DATA_DIR / "raw" / "hmlr" / "CCOD_FULL.zip",
    "hmlr_ccod_csv": DATA_DIR / "raw" / "hmlr" / "CCOD_FULL.csv",
}


@app.post("/upload-file", dependencies=[Depends(_auth)])
async def upload_file(file: UploadFile, slot: str) -> dict[str, Any]:
    """Upload an arbitrary file to a fixed, code-controlled slot.

    ``slot`` is a key into ``_UPLOAD_SLOTS`` — the actual destination
    path is determined by this code, not by user input. Adding a new
    slot requires a code change + redeploy, which is the right
    security model for arbitrary file uploads.
    """
    if slot not in _UPLOAD_SLOTS:
        raise HTTPException(400, f"unknown slot; available: {sorted(_UPLOAD_SLOTS)}")
    full = _UPLOAD_SLOTS[slot]
    full.parent.mkdir(parents=True, exist_ok=True)
    stage = f"upload_{slot}"
    _require_idle(stage)
    _mark(stage, status="running", started_at=_now(), name=file.filename, dest=str(full))
    tmp = full.with_suffix(full.suffix + ".partial")
    bytes_written = 0
    try:
        with tmp.open("wb") as fh:
            while True:
                chunk = await file.read(8 * 1024 * 1024)
                if not chunk:
                    break
                fh.write(chunk)
                bytes_written += len(chunk)
        tmp.replace(full)
    except Exception as exc:  # noqa: BLE001
        tmp.unlink(missing_ok=True)
        _mark(stage, status="failed", finished_at=_now(), error=repr(exc))
        raise HTTPException(500, repr(exc)) from exc
    _mark(stage, status="completed", finished_at=_now(), bytes=bytes_written, path=str(full))
    return {"ok": True, "bytes": bytes_written, "path": str(full)}


@app.post("/unzip-file", dependencies=[Depends(_auth)])
def trigger_unzip_file(bg: BackgroundTasks, path: str) -> dict[str, Any]:
    """Extract a zip file under /data to its parent directory."""
    if path.startswith("/") or ".." in Path(path).parts:
        raise HTTPException(400, "path must be a relative path inside /data")
    full = DATA_DIR / path
    stage = f"unzip_{full.stem}"
    _require_idle(stage)
    bg.add_task(_do_unzip_file, stage, full)
    return {"ok": True, "queued": stage, "path": str(full)}


@app.post("/fetch-url", dependencies=[Depends(_auth)])
def trigger_fetch_url(bg: BackgroundTasks, url: str, dest: str) -> dict[str, Any]:
    """Download a URL into a path under /data. ``dest`` is relative to /data."""
    if dest.startswith("/") or ".." in Path(dest).parts:
        raise HTTPException(400, "dest must be a relative path inside /data")
    full = DATA_DIR / dest
    stage = f"fetch_{Path(dest).stem}"
    _require_idle(stage)
    bg.add_task(_do_fetch_url, stage, url, full)
    return {"ok": True, "queued": stage, "dest": str(full)}


_BUILD_SCRIPTS = {
    "company": "scripts/build_candidate_tables.py",
    "address": "scripts/build_address_table.py",
    "person": "scripts/build_person_table.py",
}


def _do_build(what: str = "company") -> None:
    script = _BUILD_SCRIPTS[what]
    cmd = ["python", script]
    _run_subprocess(f"build_{what}", cmd, cwd=Path("/app"))


@app.post("/build", dependencies=[Depends(_auth)])
def trigger_build(bg: BackgroundTasks, what: str = "company") -> dict[str, Any]:
    if what not in _BUILD_SCRIPTS:
        raise HTTPException(400, "what must be company|address|person")
    _require_idle(f"build_{what}")
    bg.add_task(_do_build, what=what)
    return {"ok": True, "queued": f"build_{what}"}


def _do_match(what: str = "company", auto: bool = False) -> None:
    gm = shutil.which("goldenmatch") or "goldenmatch"
    table = PROCESSED_DIR / f"{what}_entities.parquet"
    run_name = f"{what}_auto" if auto else what
    cmd = [
        gm,
        "dedupe",
        str(table),
        "--output-dir",
        str(REPORTS_DIR),
        "--run-name",
        run_name,
        "--output-clusters",
        "--format",
        "csv",
        "--no-tui",
    ]
    if auto:
        cmd += ["--auto-fix", "--auto-block"]
    else:
        config = Path("/app/configs") / f"goldenmatch_{what}.yml"
        cmd += ["--config", str(config)]
    stage = f"match_{what}_auto" if auto else f"match_{what}"
    _run_subprocess(stage, cmd, cwd=Path("/app"))


@app.post("/match", dependencies=[Depends(_auth)])
def trigger_match(bg: BackgroundTasks, what: str = "company", auto: bool = False) -> dict[str, Any]:
    if what not in {"company", "address", "person"}:
        raise HTTPException(400, "what must be company|address|person")
    stage = f"match_{what}_auto" if auto else f"match_{what}"
    _require_idle(stage)
    bg.add_task(_do_match, what=what, auto=auto)
    return {"ok": True, "queued": stage, "what": what, "auto": auto}


def _do_match_against(target: Path, against: Path, run_name: str) -> None:
    gm = shutil.which("goldenmatch") or "goldenmatch"
    config = Path("/app/configs/goldenmatch_company.yml")
    cmd = [
        gm,
        "match",
        str(target),
        "--against",
        str(against),
        "--config",
        str(config),
        "--output-dir",
        str(REPORTS_DIR),
        "--run-name",
        run_name,
        "--output-matched",
        "--output-scores",
        "--format",
        "csv",
        "--quiet",
    ]
    _run_subprocess(f"match_against_{run_name}", cmd, cwd=Path("/app"))


@app.post("/match-against", dependencies=[Depends(_auth)])
def trigger_match_against(
    bg: BackgroundTasks,
    target: str = "processed/company_entities.parquet",
    against: str = "interim/gleif_entities.parquet",
    run_name: str = "icij_vs_gleif",
) -> dict[str, Any]:
    """Match a target file against a reference file. Paths are relative to /data."""
    for p in (target, against):
        if p.startswith("/") or ".." in Path(p).parts:
            raise HTTPException(400, "paths must be relative inside /data")
    full_t = DATA_DIR / target
    full_a = DATA_DIR / against
    if not full_t.exists():
        raise HTTPException(400, f"target missing: {full_t}")
    if not full_a.exists():
        raise HTTPException(400, f"against missing: {full_a}")
    stage = f"match_against_{run_name}"
    _require_idle(stage)
    bg.add_task(_do_match_against, full_t, full_a, run_name)
    return {"ok": True, "queued": stage, "target": str(full_t), "against": str(full_a)}


def _do_publish(what: str = "company") -> None:
    from shellnet import publish

    started = _now()
    stage = f"publish_{what}"
    _mark(stage, status="running", started_at=started, what=what)
    try:
        summary = publish.publish_run(
            what=what,
            reports_dir=REPORTS_DIR,
            processed_dir=PROCESSED_DIR,
        )
        _mark(stage, status="completed", finished_at=_now(), summary=summary)
    except Exception as exc:  # noqa: BLE001
        log.exception("publish failed")
        _mark(stage, status="failed", finished_at=_now(), error=repr(exc))


@app.post("/publish", dependencies=[Depends(_auth)])
def trigger_publish(bg: BackgroundTasks, what: str = "company") -> dict[str, Any]:
    _require_idle(f"publish_{what}")
    bg.add_task(_do_publish, what=what)
    return {"ok": True, "queued": f"publish_{what}", "what": what}


def _do_publish_list_match(run_name: str) -> None:
    from shellnet import publish

    stage = f"publish_list_{run_name}"
    _mark(stage, status="running", started_at=_now(), run_name=run_name)
    try:
        summary = publish.publish_list_match(run_name=run_name, reports_dir=REPORTS_DIR)
        _mark(stage, status="completed", finished_at=_now(), summary=summary)
    except Exception as exc:  # noqa: BLE001
        log.exception("publish_list_match failed")
        _mark(stage, status="failed", finished_at=_now(), error=repr(exc))


@app.post("/publish-list-match", dependencies=[Depends(_auth)])
def trigger_publish_list_match(
    bg: BackgroundTasks, run_name: str = "icij_os_vs_gleif"
) -> dict[str, Any]:
    stage = f"publish_list_{run_name}"
    _require_idle(stage)
    bg.add_task(_do_publish_list_match, run_name)
    return {"ok": True, "queued": stage, "run_name": run_name}


@app.post("/reset", dependencies=[Depends(_auth)])
def reset_state() -> dict[str, Any]:
    _save_state({"stages": {s: {"status": "pending"} for s in STAGES}})
    return {"ok": True}


@app.delete("/data/raw", dependencies=[Depends(_auth)])
def wipe_raw() -> dict[str, Any]:
    """Nuke /data/raw — useful before re-uploading."""
    if (DATA_DIR / "raw").exists():
        shutil.rmtree(DATA_DIR / "raw")
    (DATA_DIR / "raw").mkdir(parents=True, exist_ok=True)
    return {"ok": True}


# Fallback root so a browser hit doesn't 404.
@app.get("/")
def root() -> JSONResponse:
    return JSONResponse(
        {
            "service": "shellnet-job",
            "endpoints": [
                "GET /healthz",
                "GET /status (auth)",
                "GET /files (auth)",
                "GET /logs/{stage} (auth)",
                "POST /upload-zip (auth, multipart)",
                "POST /unzip (auth)",
                "POST /ingest (auth)",
                "POST /build (auth)",
                "POST /match?what=company (auth)",
                "POST /publish?what=company (auth)",
                "POST /reset (auth)",
                "DELETE /data/raw (auth)",
            ],
        }
    )
