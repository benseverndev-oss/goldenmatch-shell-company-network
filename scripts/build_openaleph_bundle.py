"""Build an OpenAleph / ICIJ Datashare ingest bundle from a validation pack.

The bundle is a zip with this layout::

    cluster_<id>_aleph_bundle.zip
    ├── manifest.json              # bundle metadata (foreign_id, label, languages, countries)
    ├── entities.ftm.json          # FollowTheMoney ndjson (from export_validation_pack_ftm.py)
    ├── README.md                  # human-readable bundle description
    ├── _index.csv                 # file -> source -> entity-refs mapping
    └── documents/
        ├── research_brief.md
        ├── timeline.md
        ├── graph_paths.md
        ├── evidence_ledger.csv
        ├── discovery_delta.csv
        ├── underreported_entities.csv
        ├── hit_scores.csv
        ├── search_results.json
        └── ...                    # all other validation-pack artefacts

The output is consumable by:

- ``alephclient crawldir <bundle_dir>`` — bulk-ingest to a remote Aleph
- OpenAleph's web upload for an investigation
- ICIJ Datashare via its file watcher
- ftm-lakehouse as a frozen archive

Usage::

    uv run python scripts/build_openaleph_bundle.py \\
        --community-id 37 \\
        --person "calvin edward ayre"
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve()
_REPO_ROOT = _HERE.parents[1]
sys.path.insert(0, str(_REPO_ROOT / "src"))

log = logging.getLogger("build_openaleph_bundle")

PROJECT_ROOT = _REPO_ROOT

# Files we always copy from the validation pack into the bundle, when present.
# (key = source filename relative to pack data dir, value = bundle location)
_PACK_FILES: tuple[tuple[str, str], ...] = (
    # From first-stage validation pack
    ("cluster_{cid}_profile.json", "documents/profile.json"),
    ("cluster_{cid}_person_overlap.csv", "documents/person_overlap.csv"),
    ("cluster_{cid}_person_company_roles.csv", "documents/person_company_roles.csv"),
    ("cluster_{cid}_repeated_addresses.csv", "documents/repeated_addresses.csv"),
    ("cluster_{cid}_repeated_officers.csv", "documents/repeated_officers.csv"),
    ("cluster_{cid}_repeated_agents.csv", "documents/repeated_agents.csv"),
    ("cluster_{cid}_company_themes.csv", "documents/company_themes.csv"),
    ("cluster_{cid}_external_search_queries.csv", "documents/external_search_queries.csv"),
    ("cluster_{cid}_graph_paths.md", "documents/validation_graph_paths.md"),
    # From corroboration pack (optional)
    ("cluster_{cid}_external_search_results.json", "documents/search_results.json"),
    ("cluster_{cid}_external_search_results.csv", "documents/search_results.csv"),
    ("cluster_{cid}_external_hit_scores.csv", "documents/hit_scores.csv"),
    ("cluster_{cid}_discovery_delta.csv", "documents/discovery_delta.csv"),
    ("cluster_{cid}_timeline.csv", "documents/timeline.csv"),
    ("cluster_{cid}_evidence_ledger.csv", "documents/evidence_ledger.csv"),
    ("cluster_{cid}_underreported_entities.csv", "documents/underreported_entities.csv"),
)

# Top-level markdown files we copy from the pack root.
_PACK_MD_FILES: tuple[tuple[str, str], ...] = (
    ("cluster_{cid}.md", "documents/validation_workbook.md"),
    ("cluster_{cid}_research_brief.md", "documents/research_brief.md"),
    ("cluster_{cid}_timeline.md", "documents/timeline.md"),
    ("cluster_{cid}_graph_paths.md", "documents/corroborate_graph_paths.md"),
)


# ---------------------------------------------------------------------------
# Manifest + README
# ---------------------------------------------------------------------------


def build_manifest(
    community_id: int,
    person: str,
    profile: dict[str, Any] | None,
    file_count: int,
    entity_count: int,
    archive_summary: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Aleph-compatible bundle metadata. ``foreign_id`` is the stable
    bundle identifier — re-ingestion overwrites by foreign_id."""

    odd = (profile or {}).get("ordinary_vs_unusual", {}) if profile else {}
    queue = (profile or {}).get("queue_row", {}) if profile else {}
    return {
        "foreign_id": f"gm-cluster-{community_id}-bundle",
        "label": (f"GoldenMatch Cluster #{community_id} — {person.title()} — Investigative bundle"),
        "summary": (
            f"Machine-generated investigative packet for community #{community_id}, "
            f"anchored on {person}. Combines GoldenMatch's first-stage validation "
            f"pack (cluster structure, recurring infrastructure, themes) with the "
            f"second-stage corroboration pass (external search, timeline, "
            f"evidence ledger, underreported scoring). Human review required."
        ),
        "languages": ["en"],
        "countries": ["mt"],  # All current clusters are Malta-anchored.
        "generator": "goldenmatch-shell-company-network",
        "generator_url": ("https://github.com/benseverndev-oss/goldenmatch-shell-company-network"),
        "publisher": "GoldenMatch shell-company-network discovery pipeline",
        "stats": {
            "cluster_size": (profile or {}).get("n_members", "?"),
            "priority_score": queue.get("priority_score", "?"),
            "officer_reuse_rate": odd.get("officer_reuse_rate", "?"),
            "address_reuse_rate": odd.get("address_reuse_rate", "?"),
            "n_files_in_bundle": file_count,
            "n_ftm_entities": entity_count,
            "archived_sources": archive_summary or {"attempted": 0, "succeeded": 0, "failed": 0},
        },
        "human_review_required": True,
        "publication_safe_by_default": False,
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def render_readme(community_id: int, person: str, manifest: dict[str, Any]) -> str:
    cid = community_id
    parts: list[str] = []
    parts.append(f"# Cluster {cid} — {person.title()} — Investigative bundle\n\n")
    parts.append(
        "**This is a machine-generated investigative packet. Human review is "
        "required before any claim from this bundle is published.**\n\n"
    )
    parts.append(
        "Nothing in this bundle is an allegation. Same-name does not imply "
        "same-person; recurring infrastructure is a triage signal, not an "
        "indictment.\n\n"
    )
    parts.append("## What's in here\n\n")
    parts.append(
        "| File | What |\n"
        "| --- | --- |\n"
        "| `manifest.json` | Bundle metadata (foreign_id, label, stats) |\n"
        "| `entities.ftm.json` | "
        "FollowTheMoney ndjson — Persons, Companies, Addresses, Directorships, "
        "Ownerships. Drop into OpenAleph, ICIJ Datashare, or ftm-store. |\n"
        "| `_index.csv` | File-by-file index with referenced FTM entity IDs |\n"
        "| `documents/research_brief.md` | One-page narrative summary (the place to start) |\n"
        "| `documents/timeline.md` | Dated events extracted from records + web hits |\n"
        "| `documents/corroborate_graph_paths.md` | Plain-language graph narratives |\n"
        "| `documents/evidence_ledger.csv` | Every claim, sourced and confidence-tagged |\n"
        "| `documents/discovery_delta.csv` | What was publicly known vs. what GoldenMatch added |\n"
        "| `documents/underreported_entities.csv` | High-graph-degree entities with no web presence |\n"
        "| `documents/hit_scores.csv` | External-search results, scored by domain quality |\n"
        "| `documents/search_results.json` | Raw Tavily output (provenance for hit_scores) |\n"
        "| `documents/*.csv` | First-stage validation outputs (overlap, roles, infra, themes) |\n"
        "| `archived_sources/icij/nodes/*.html` | "
        "Captured HTML of each ICIJ Offshore Leaks node page referenced by the "
        "FTM `sourceUrl` field. URLs are not evidence; these captures are. |\n"
        "| `archived_sources/icij/manifest.json` | "
        "Per-URL fetch metadata: sha256, status, retrieval timestamp, "
        "best-effort Wayback Machine backstop URL. |\n"
        "| `investigations/<slug>/evidence_record.yaml` | "
        "Per-entity verdict scaffold from `scripts/probe_mbr_company.py`. "
        "Promote `verdict: pending_review` to `confirmed_same`, "
        "`different_entity`, or `ambiguous` once an investigator has "
        "diffed the OpenCorporates officer roster against the ICIJ context. |\n"
        "| `investigations/<slug>/opencorporates_*.json` | "
        "Raw OpenCorporates API responses (search + detail). Free, "
        "MBR-mirroring, ~12-month lag. |\n"
        "| `investigations/<slug>/wayback_snapshots.json` | "
        "Wayback Machine snapshot URL for the OpenCorporates page. |\n"
        "\n"
    )

    parts.append("## How to ingest\n\n")
    parts.append(
        "**OpenAleph (via alephclient):**\n\n"
        "```bash\n"
        f"# Unzip into a working directory, then crawldir at it.\n"
        f"unzip cluster_{cid}_aleph_bundle.zip -d cluster_{cid}_bundle\n"
        f"alephclient -h https://your-aleph.example/ crawldir \\\n"
        f"    --foreign-id {manifest['foreign_id']} \\\n"
        f"    cluster_{cid}_bundle/\n"
        "```\n\n"
        "**ICIJ Datashare:** drop the unzipped folder under your "
        "Datashare data directory. The FTM file is auto-recognized.\n\n"
        "**ftm-store (CLI):**\n\n"
        "```bash\n"
        "ftm store iter -i entities.ftm.json -o entities.ftm.json\n"
        "```\n\n"
        "**Raw inspection:**\n\n"
        "```bash\n"
        "# Just look at the brief.\n"
        "less documents/research_brief.md\n"
        "```\n\n"
    )

    parts.append("## Stats\n\n")
    s = manifest["stats"]
    parts.append(
        f"- Cluster size: **{s['cluster_size']}** entities\n"
        f"- Priority score: **{s['priority_score']}**\n"
        f"- Officer reuse rate: **{s['officer_reuse_rate']}**\n"
        f"- Address reuse rate: **{s['address_reuse_rate']}**\n"
        f"- FTM entities in bundle: **{s['n_ftm_entities']}**\n"
        f"- Files in bundle: **{s['n_files_in_bundle']}**\n\n"
    )
    parts.append(
        "## Cautious framing\n\n"
        "- Same-name records have not been verified as the same individual.\n"
        "- Recurring infrastructure (shared registered address + officer reuse) "
        "is a common-and-legitimate feature of Malta corporate-services hubs. "
        "It is a triage signal, not an indictment.\n"
        "- Web search uses Tavily, a third-party aggregator. Absence of hits is "
        "not absence of public record.\n"
        "- Theme labels are keyword heuristics. The `evidence_ledger.csv` flags "
        "which claims are publication-safe and which need review.\n"
    )
    return "".join(parts)


def build_file_index(
    bundle_files: list[tuple[Path, str]],
    entity_count: int,
) -> list[dict[str, str]]:
    """A small CSV index that ties each file to its source role + a hint of
    which entity types it touches. Helps the reviewer audit the bundle
    without opening every file."""

    rows: list[dict[str, str]] = []
    for src, bundle_path in bundle_files:
        rows.append(
            {
                "bundle_path": bundle_path,
                "source_path": str(src.relative_to(PROJECT_ROOT))
                if PROJECT_ROOT in src.parents
                else src.name,
                "size_bytes": str(src.stat().st_size) if src.exists() else "0",
                "notes": _describe(bundle_path),
            }
        )
    rows.append(
        {
            "bundle_path": "entities.ftm.json",
            "source_path": "(generated)",
            "size_bytes": "",
            "notes": (
                f"FollowTheMoney ndjson with {entity_count} entities. "
                "Each line is one FTM entity (Person, Company, Address, "
                "Directorship, Ownership). Stable IDs prefixed gm-c<id>-."
            ),
        }
    )
    return rows


def _describe(bundle_path: str) -> str:
    if bundle_path.endswith("research_brief.md"):
        return "One-page narrative summary — start here."
    if bundle_path.endswith("timeline.md") or bundle_path.endswith("timeline.csv"):
        return "Dated events from ICIJ + corroboration search."
    if "graph_paths" in bundle_path:
        return "Graph-path narratives in plain English."
    if "evidence_ledger" in bundle_path:
        return "Every load-bearing claim, with source + publication_safe flag."
    if "discovery_delta" in bundle_path:
        return "Publicly-known facts vs. GoldenMatch-added structural facts."
    if "underreported" in bundle_path:
        return "Cluster members with high graph degree + no public web presence."
    if "hit_scores" in bundle_path:
        return "External-search hits, scored by domain quality + term match."
    if "search_results.json" in bundle_path:
        return "Raw Tavily API responses (provenance for hit_scores)."
    if "person_overlap" in bundle_path:
        return "Anchor-dossier vs cluster-membership overlap."
    if "person_company_roles" in bundle_path:
        return "Per-edge role/date/source from ICIJ for the anchor."
    if "repeated_addresses" in bundle_path:
        return "Address bridges — shared registered offices across cluster."
    if "repeated_officers" in bundle_path:
        return "Officer bridges — people appearing on multiple cluster members."
    if "repeated_agents" in bundle_path:
        return "Intermediary bridges (corporate service providers)."
    if "company_themes" in bundle_path:
        return "Weak keyword-based theme labels per cluster member."
    if "external_search_queries" in bundle_path:
        return "Generated search queries (input to corroboration pass)."
    if bundle_path.endswith("profile.json"):
        return "Pack-level metadata: queue row, cluster scores, member sample."
    if "validation_workbook" in bundle_path:
        return "First-stage human-review workbook."
    return "Supporting artefact."


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------


def _resolve_pack_files(cid: int, pack_dir: Path, data_dir: Path) -> list[tuple[Path, str]]:
    """Return [(source_path, bundle_path), ...] for every pack file that
    actually exists. Missing optional files are skipped silently."""

    out: list[tuple[Path, str]] = []
    for src_tmpl, bundle_path in _PACK_FILES:
        src = data_dir / src_tmpl.format(cid=cid)
        if src.exists():
            out.append((src, bundle_path))
    for src_tmpl, bundle_path in _PACK_MD_FILES:
        src = pack_dir / src_tmpl.format(cid=cid)
        if src.exists():
            out.append((src, bundle_path))
    return out


def _count_ftm_entities(ftm_path: Path) -> int:
    if not ftm_path.exists():
        return 0
    with ftm_path.open(encoding="utf-8") as f:
        return sum(1 for line in f if line.strip())


def build_bundle(
    community_id: int,
    person: str,
    *,
    pack_dir: Path | None = None,
    out_path: Path | None = None,
    repo_root: Path = PROJECT_ROOT,
    archive_sources: bool = True,
    archive_min_interval_s: float = 1.0,
    archive_request_wayback: bool = True,
    investigations_dir: Path | None = None,
) -> Path:
    base = (pack_dir or repo_root / "docs" / "validation").resolve()
    data = base / "data"
    cid = community_id

    ftm_path = data / f"cluster_{cid}_ftm.json"
    if not ftm_path.exists():
        raise SystemExit(
            f"[fatal] {ftm_path} not found. Run scripts/export_validation_pack_ftm.py first."
        )

    profile_path = data / f"cluster_{cid}_profile.json"
    profile = (
        json.loads(profile_path.read_text(encoding="utf-8")) if profile_path.exists() else None
    )

    bundle_files = _resolve_pack_files(cid, base, data)
    entity_count = _count_ftm_entities(ftm_path)

    # Archive ICIJ source pages alongside the bundle so the FTM
    # `sourceUrl` references stay reproducible if ICIJ retires or
    # rebuilds the pages. Output: archived_sources/icij/<node>.html
    # + manifest.json. Skipped if archive_sources=False.
    archived_root: Path | None = None
    archive_summary: dict[str, int] = {"attempted": 0, "succeeded": 0, "failed": 0}
    if archive_sources:
        from shellnet.archive import archive_urls, parse_icij_urls_from_ftm

        urls = parse_icij_urls_from_ftm(ftm_path)
        if urls:
            archived_root = data / f"cluster_{cid}_archived_sources"
            archived_root.mkdir(parents=True, exist_ok=True)
            res = archive_urls(
                urls,
                archived_root,
                min_interval_s=archive_min_interval_s,
                request_wayback_save=archive_request_wayback,
            )
            archive_summary = {
                "attempted": len(res.entries),
                "succeeded": len(res.successes),
                "failed": len(res.failures),
            }

    manifest = build_manifest(
        community_id=cid,
        person=person,
        profile=profile,
        file_count=len(bundle_files) + 1,  # +1 for entities.ftm.json itself
        entity_count=entity_count,
        archive_summary=archive_summary,
    )

    index_rows = build_file_index(bundle_files, entity_count)
    readme = render_readme(cid, person, manifest)

    out = out_path or (data / f"cluster_{cid}_aleph_bundle.zip")
    out.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest, indent=2, sort_keys=True))
        zf.writestr("README.md", readme)
        # FTM file at the top level — Aleph's crawldir picks it up automatically.
        zf.write(ftm_path, "entities.ftm.json")

        # _index.csv
        from io import StringIO

        buf = StringIO()
        w = csv.DictWriter(buf, fieldnames=["bundle_path", "source_path", "size_bytes", "notes"])
        w.writeheader()
        for r in index_rows:
            w.writerow(r)
        zf.writestr("_index.csv", buf.getvalue())

        # Pack files (validation-pack + corroborate-pack artefacts).
        for src, bundle_path in bundle_files:
            zf.write(src, bundle_path)

        # Archived ICIJ source pages — preserve directory structure
        # under archived_sources/ inside the zip.
        if archived_root and archived_root.exists():
            for path in sorted(archived_root.rglob("*")):
                if path.is_file():
                    arc_path = "archived_sources/" + str(path.relative_to(archived_root)).replace(
                        "\\", "/"
                    )
                    zf.write(path, arc_path)

        # Investigation evidence records (Phase 17a follow-ups). One
        # subdirectory per (slug) under data/investigations/, each
        # containing opencorporates_search.json + evidence_record.yaml
        # produced by scripts/probe_mbr_company.py. Surfaces alongside
        # the bundle so the reviewer can promote pending_review verdicts
        # to confirmed / different / ambiguous in-place.
        inv_root = investigations_dir or (repo_root / "data" / "investigations")
        inv_count = 0
        if inv_root.exists():
            for path in sorted(inv_root.rglob("*")):
                if path.is_file():
                    arc_path = "investigations/" + str(path.relative_to(inv_root)).replace(
                        "\\", "/"
                    )
                    zf.write(path, arc_path)
                    inv_count += 1

    log.info(
        "wrote %s (%d pack files, %d FTM entities, %d archived sources, %d investigation artefacts)",
        out,
        len(bundle_files) + 1,
        entity_count,
        archive_summary["succeeded"],
        inv_count,
    )
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description=(
            "Build an OpenAleph / ICIJ Datashare / ftm-store ingest bundle "
            "from a validation pack. Includes the FTM ndjson, all pack CSVs "
            "and markdown, a manifest.json, an index CSV, and a README."
        )
    )
    p.add_argument("--community-id", type=int, required=True)
    p.add_argument("--person", type=str, required=True)
    p.add_argument("--pack-dir", type=Path, default=None)
    p.add_argument("--out", type=Path, default=None)
    p.add_argument(
        "--no-archive-sources",
        action="store_true",
        help=(
            "Skip fetching + bundling ICIJ source-page HTML captures. "
            "Useful for fast local iteration; production bundles should "
            "always include them so the FTM sourceUrl references stay "
            "reproducible if ICIJ retires pages."
        ),
    )
    p.add_argument(
        "--archive-min-interval",
        type=float,
        default=1.0,
        help=("Seconds between ICIJ page fetches. Default 1.0 (1 req/s); polite for a small NGO."),
    )
    p.add_argument(
        "--no-wayback",
        action="store_true",
        help="Skip the best-effort Wayback Machine save request per URL.",
    )
    p.add_argument(
        "--investigations-dir",
        type=Path,
        default=None,
        help=(
            "Optional path to a data/investigations/ root. Every "
            "<slug>/* file is included in the bundle under "
            "investigations/<slug>/* so reviewer-resolved evidence "
            "records ship inside the same zip as the FTM + archived "
            "sources. Default: repo's data/investigations/."
        ),
    )
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    out = build_bundle(
        community_id=args.community_id,
        person=args.person,
        pack_dir=args.pack_dir,
        out_path=args.out,
        archive_sources=not args.no_archive_sources,
        archive_min_interval_s=args.archive_min_interval,
        archive_request_wayback=not args.no_wayback,
        investigations_dir=args.investigations_dir,
    )
    try:
        rel = out.relative_to(PROJECT_ROOT)
        print(f"wrote {rel}")
    except ValueError:
        print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
