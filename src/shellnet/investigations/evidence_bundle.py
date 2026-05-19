"""Source-document bundling — investigative evidence packets per cluster.

For every surfaced lead, automatically assemble a directory with:

* ``source_filings/`` — the raw source-adapter records for each member
  (the original ICIJ / OpenCorporates / GLEIF / OpenSanctions row,
  serialised as JSON so the journalist can quote it verbatim).
* ``edges.csv`` — every cluster-incident edge with provenance
  (``src_node``, ``dst_node``, ``kind_raw``, ``source_label``,
  ``start_date``, ``end_date``, ``role`` if present).
* ``leak_index.md`` — leak labels → edge counts → first/last dates.
* ``registry_links.md`` — external URLs derived from LEI / company
  number / OFAC ids, ready to click during validation.
* ``sanctions_records.json`` — any sanctions list-match anchors
  matched against this cluster.
* ``manifest.md`` — human-readable index of everything in the packet.
* ``bundle.json`` — the same manifest in machine-readable form.

Build is pure-functional; ``write_bundle`` is the I/O step.
"""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import polars as pl

    from shellnet.investigations.cluster_explainer import MemberAttr


@dataclass
class SourceFiling:
    """One raw source record for a cluster member."""

    member_uid: str
    source: str
    source_id: str
    name: str
    record: dict[str, Any]  # the raw row (with `raw` field if present)


@dataclass
class LeakReference:
    leak_label: str
    n_edges: int
    first_date: str | None
    last_date: str | None
    sample_nodes: list[str]


@dataclass
class RegistryLink:
    member_uid: str
    source: str
    label: str
    url: str


@dataclass
class SanctionsRecord:
    target_entity_uid: str
    ref_entity_uid: str
    ref_name: str | None
    ref_lei: str | None
    ref_jurisdiction: str | None
    score: float | None
    band: str | None


@dataclass
class EvidenceBundle:
    cluster_id: int
    members: list[MemberAttr]
    source_filings: list[SourceFiling] = field(default_factory=list)
    edges: list[dict[str, Any]] = field(default_factory=list)
    leak_references: list[LeakReference] = field(default_factory=list)
    registry_links: list[RegistryLink] = field(default_factory=list)
    sanctions_records: list[SanctionsRecord] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Registry URL helpers — small, conservative; only emit URLs we're sure
# resolve. No URLs are guessed past these patterns.
# ---------------------------------------------------------------------------


def _registry_urls_for_member(m: MemberAttr) -> list[RegistryLink]:
    out: list[RegistryLink] = []
    if m.lei:
        out.append(
            RegistryLink(
                member_uid=m.entity_uid,
                source="gleif",
                label=f"GLEIF page for LEI {m.lei}",
                url=f"https://www.gleif.org/lei/{m.lei}",
            )
        )
        out.append(
            RegistryLink(
                member_uid=m.entity_uid,
                source="search.gleif",
                label=f"GLEIF search for {m.lei}",
                url=f"https://search.gleif.org/#/record/{m.lei}",
            )
        )
    if m.company_number and m.jurisdiction:
        # OpenCorporates URL pattern: /companies/<jur>/<company_number>.
        jur = m.jurisdiction.lower()
        out.append(
            RegistryLink(
                member_uid=m.entity_uid,
                source="opencorporates",
                label=f"OpenCorporates: {m.company_number} ({jur})",
                url=f"https://opencorporates.com/companies/{jur}/{m.company_number}",
            )
        )
    # OpenSanctions members: source_id is the OS entity id (passed through).
    if m.source == "opensanctions":
        os_id = m.entity_uid.split(":", 1)[1] if ":" in m.entity_uid else m.entity_uid
        out.append(
            RegistryLink(
                member_uid=m.entity_uid,
                source="opensanctions",
                label=f"OpenSanctions entry {os_id}",
                url=f"https://www.opensanctions.org/entities/{os_id}/",
            )
        )
    return out


# ---------------------------------------------------------------------------
# Bundle assembly
# ---------------------------------------------------------------------------


def _gather_source_filings(
    members: list[MemberAttr],
    source_dfs: dict[str, pl.DataFrame | None],
) -> list[SourceFiling]:
    """``source_dfs`` maps source name → interim parquet (already loaded).
    Records are matched by ``source_id`` (the part of entity_uid after the colon)."""
    out: list[SourceFiling] = []
    for m in members:
        if ":" not in m.entity_uid:
            continue
        src, sid = m.entity_uid.split(":", 1)
        df = source_dfs.get(src)
        if df is None or df.height == 0 or "source_id" not in df.columns:
            continue
        import polars as pl  # runtime

        row_df = df.filter(pl.col("source_id") == sid)
        if row_df.height == 0:
            continue
        row = row_df.row(0, named=True)
        # If the row has a `raw` field (Pydantic-style adapters store one),
        # surface it; otherwise just dump the whole row.
        record = row.get("raw") if "raw" in row else dict(row)
        if not isinstance(record, dict):
            record = dict(row)
        out.append(
            SourceFiling(
                member_uid=m.entity_uid,
                source=src,
                source_id=sid,
                name=m.name,
                record=record,
            )
        )
    return out


def _gather_edges(member_uids: list[str], edges_df: pl.DataFrame | None) -> list[dict[str, Any]]:
    if edges_df is None or edges_df.height == 0:
        return []
    import polars as pl

    sub = edges_df.filter(
        pl.col("src_node").is_in(member_uids) | pl.col("dst_node").is_in(member_uids)
    )
    if sub.height == 0:
        return []
    keep_cols = [
        c
        for c in (
            "src_node",
            "dst_node",
            "kind_raw",
            "source_label",
            "start_date",
            "end_date",
            "role",
        )
        if c in sub.columns
    ]
    out: list[dict[str, Any]] = []
    for r in sub.select(keep_cols).iter_rows(named=True):
        out.append({k: (str(v) if v is not None else None) for k, v in r.items()})
    return out


def _gather_leaks(edges: list[dict[str, Any]]) -> list[LeakReference]:
    by_label: dict[str, dict[str, Any]] = {}
    for e in edges:
        leak = e.get("source_label")
        if not leak:
            continue
        slot = by_label.setdefault(
            leak,
            {"n_edges": 0, "first_date": None, "last_date": None, "sample_nodes": set()},
        )
        slot["n_edges"] += 1
        for k in ("start_date", "end_date"):
            d = e.get(k)
            if d:
                if slot["first_date"] is None or d < slot["first_date"]:
                    slot["first_date"] = d
                if slot["last_date"] is None or d > slot["last_date"]:
                    slot["last_date"] = d
        for n in (e.get("src_node"), e.get("dst_node")):
            if n and len(slot["sample_nodes"]) < 5:
                slot["sample_nodes"].add(n)
    return [
        LeakReference(
            leak_label=leak,
            n_edges=slot["n_edges"],
            first_date=slot["first_date"],
            last_date=slot["last_date"],
            sample_nodes=sorted(slot["sample_nodes"]),
        )
        for leak, slot in sorted(by_label.items())
    ]


def _gather_sanctions(
    sanctions_df: pl.DataFrame | None, member_uids: list[str]
) -> list[SanctionsRecord]:
    if sanctions_df is None or sanctions_df.height == 0:
        return []
    if "target_entity_uid" not in sanctions_df.columns:
        return []
    import polars as pl

    sub = sanctions_df.filter(pl.col("target_entity_uid").is_in(member_uids))
    out: list[SanctionsRecord] = []
    for r in sub.iter_rows(named=True):
        out.append(
            SanctionsRecord(
                target_entity_uid=r.get("target_entity_uid", ""),
                ref_entity_uid=r.get("ref_entity_uid", ""),
                ref_name=r.get("ref_name"),
                ref_lei=r.get("ref_lei"),
                ref_jurisdiction=r.get("ref_jurisdiction"),
                score=float(r["score"]) if r.get("score") is not None else None,
                band=r.get("band"),
            )
        )
    return out


def build_evidence_bundle(
    cluster_id: int,
    members: list[MemberAttr],
    *,
    edges_df: pl.DataFrame | None = None,
    source_dfs: dict[str, pl.DataFrame | None] | None = None,
    sanctions_df: pl.DataFrame | None = None,
) -> EvidenceBundle:
    """Assemble the full packet. All optional inputs degrade silently to
    empty sections."""
    bundle = EvidenceBundle(cluster_id=cluster_id, members=members)
    member_uids = [m.entity_uid for m in members]
    if source_dfs:
        bundle.source_filings = _gather_source_filings(members, source_dfs)
    bundle.edges = _gather_edges(member_uids, edges_df)
    bundle.leak_references = _gather_leaks(bundle.edges)
    for m in members:
        bundle.registry_links.extend(_registry_urls_for_member(m))
    bundle.sanctions_records = _gather_sanctions(sanctions_df, member_uids)
    return bundle


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def _json_default(obj: Any) -> Any:
    """Fallback encoder for date / set / Polars rows etc."""
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    if isinstance(obj, set):
        return sorted(obj)
    return str(obj)


def write_bundle(bundle: EvidenceBundle, out_dir: Path) -> Path:
    """Write the bundle to ``out_dir / cluster_<id> /`` and return the
    directory."""
    target = Path(out_dir) / f"cluster_{bundle.cluster_id}"
    target.mkdir(parents=True, exist_ok=True)

    # source_filings/
    if bundle.source_filings:
        sf_dir = target / "source_filings"
        sf_dir.mkdir(exist_ok=True)
        for f in bundle.source_filings:
            (sf_dir / f"{f.source}_{f.source_id}.json").write_text(
                json.dumps(asdict(f), default=_json_default, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

    # edges.csv
    if bundle.edges:
        edges_path = target / "edges.csv"
        cols = list(bundle.edges[0].keys())
        with edges_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=cols)
            writer.writeheader()
            for row in bundle.edges:
                writer.writerow({c: row.get(c, "") for c in cols})

    # leak_index.md
    if bundle.leak_references:
        leak_lines = ["# Leak index", ""]
        leak_lines.append("| leak | edges | first date | last date | sample nodes |")
        leak_lines.append("| --- | ---: | --- | --- | --- |")
        for lr in bundle.leak_references:
            leak_lines.append(
                f"| {lr.leak_label} | {lr.n_edges} | "
                f"{lr.first_date or ''} | {lr.last_date or ''} | "
                f"{', '.join('`' + n + '`' for n in lr.sample_nodes)} |"
            )
        (target / "leak_index.md").write_text("\n".join(leak_lines), encoding="utf-8")

    # registry_links.md
    if bundle.registry_links:
        rl_lines = ["# Registry links", ""]
        rl_lines.append("| member | source | link |")
        rl_lines.append("| --- | --- | --- |")
        for rl in bundle.registry_links:
            rl_lines.append(f"| `{rl.member_uid}` | {rl.source} | [{rl.label}]({rl.url}) |")
        (target / "registry_links.md").write_text("\n".join(rl_lines), encoding="utf-8")

    # sanctions_records.json
    if bundle.sanctions_records:
        (target / "sanctions_records.json").write_text(
            json.dumps(
                [asdict(s) for s in bundle.sanctions_records],
                default=_json_default,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    # bundle.json (machine-readable index)
    manifest_obj = {
        "cluster_id": bundle.cluster_id,
        "n_members": len(bundle.members),
        "members": [
            {
                "entity_uid": m.entity_uid,
                "source": m.source,
                "name": m.name,
                "jurisdiction": m.jurisdiction,
                "lei": m.lei,
                "company_number": m.company_number,
            }
            for m in bundle.members
        ],
        "n_source_filings": len(bundle.source_filings),
        "n_edges": len(bundle.edges),
        "n_leak_references": len(bundle.leak_references),
        "n_registry_links": len(bundle.registry_links),
        "n_sanctions_records": len(bundle.sanctions_records),
        "leak_labels": [lr.leak_label for lr in bundle.leak_references],
    }
    (target / "bundle.json").write_text(
        json.dumps(manifest_obj, default=_json_default, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # manifest.md (human-readable index)
    mf = [f"# Evidence packet — cluster {bundle.cluster_id}", ""]
    mf.append(
        f"**{len(bundle.members)} member(s)**, **{len(bundle.source_filings)}** source filing(s), "
        f"**{len(bundle.edges)}** incident edge(s), **{len(bundle.leak_references)}** leak(s), "
        f"**{len(bundle.registry_links)}** registry link(s), "
        f"**{len(bundle.sanctions_records)}** sanctions record(s)."
    )
    mf.append("")
    mf.append("## Files")
    mf.append("")
    mf.append("| path | what |")
    mf.append("| --- | --- |")
    if bundle.source_filings:
        mf.append("| `source_filings/` | raw source-adapter records per cluster member |")
    if bundle.edges:
        mf.append("| `edges.csv` | every cluster-incident edge with provenance |")
    if bundle.leak_references:
        mf.append("| `leak_index.md` | leak labels → edge counts → date range |")
    if bundle.registry_links:
        mf.append("| `registry_links.md` | external GLEIF / OpenCorporates / OpenSanctions links |")
    if bundle.sanctions_records:
        mf.append("| `sanctions_records.json` | list-match anchors against this cluster |")
    mf.append("| `bundle.json` | machine-readable manifest |")
    mf.append("")
    mf.append("## Members")
    mf.append("")
    mf.append("| entity_uid | source | name | jurisdiction | lei | company_number |")
    mf.append("| --- | --- | --- | --- | --- | --- |")
    for m in bundle.members:
        mf.append(
            f"| `{m.entity_uid}` | {m.source} | `{m.name}` | {m.jurisdiction or '?'} | "
            f"{m.lei or ''} | {m.company_number or ''} |"
        )
    mf.append("")
    if bundle.leak_references:
        mf.append("## Leaks referenced")
        mf.append("")
        for lr in bundle.leak_references:
            mf.append(
                f"- **{lr.leak_label}** — {lr.n_edges} edge(s)"
                + (f", {lr.first_date} → {lr.last_date}" if lr.first_date else "")
            )
        mf.append("")
    (target / "manifest.md").write_text("\n".join(mf), encoding="utf-8")

    return target
