"""Build a machine-generated validation pack for one (community, person) pair.

This is **evidence collection scaffolding** for a human investigator, not a
finding. Nothing here asserts wrongdoing or same-person identity. Every
generated conclusion is cautious ("candidate", "lead", "requires
validation"); the final verdict in the output workbook is always
``Human review required.``

Usage::

    uv run python scripts/build_validation_pack.py \\
        --community-id 47 \\
        --person "peter kevin perry"

Outputs (all paths relative to project root)::

    docs/validation/cluster_<id>.md
    docs/validation/data/cluster_<id>_profile.json
    docs/validation/data/cluster_<id>_person_overlap.csv
    docs/validation/data/cluster_<id>_person_company_roles.csv
    docs/validation/data/cluster_<id>_repeated_addresses.csv
    docs/validation/data/cluster_<id>_repeated_officers.csv
    docs/validation/data/cluster_<id>_repeated_agents.csv
    docs/validation/data/cluster_<id>_company_themes.csv
    docs/validation/data/cluster_<id>_external_search_queries.csv
    docs/validation/data/cluster_<id>_graph_paths.md

Source tables that may be missing degrade gracefully: an empty CSV (with
headers) is written and a warning is appended to the markdown. The script
only hard-fails if the community or person cannot be found at all.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import polars as pl

# Repo path bootstrap so the script can be run as ``python scripts/...``
# without an editable install in test environments.
_HERE = Path(__file__).resolve()
_REPO_ROOT = _HERE.parents[1]
sys.path.insert(0, str(_REPO_ROOT / "src"))

from shellnet.normalize import normalize_company_name  # noqa: E402

log = logging.getLogger("build_validation_pack")

# ---------------------------------------------------------------------------
# Conventions
# ---------------------------------------------------------------------------

DEFAULT_THRESHOLD = 0.9
PROJECT_ROOT = _REPO_ROOT
REPORTS_DATA = PROJECT_ROOT / "docs" / "reports" / "data"
DOSSIERS_DIR = PROJECT_ROOT / "docs" / "reports" / "dossiers"
INTERIM_DIR = PROJECT_ROOT / "data" / "interim"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
VALIDATION_DIR = PROJECT_ROOT / "docs" / "validation"
VALIDATION_DATA_DIR = VALIDATION_DIR / "data"
TEMPLATE_PATH = VALIDATION_DIR / "template.md"


# CSV header schemas. Keep these in sync with the markdown and with tests.
OVERLAP_HEADERS = [
    "company_name",
    "normalized_company_name",
    "in_community",
    "in_person_dossier",
    "match_type",
    "confidence",
    "source_record_ids",
    "notes",
]
ROLES_HEADERS = [
    "person_name",
    "person_record_id",
    "company_name",
    "company_record_id",
    "relationship_type",
    "role",
    "start_date",
    "end_date",
    "source",
    "leak",
    "confidence",
    "notes",
]
ADDR_HEADERS = ["address", "n_linked_companies", "linked_companies", "source_label", "confidence"]
OFFICER_HEADERS = [
    "officer_name",
    "n_linked_companies",
    "linked_companies",
    "roles",
    "source_label",
    "confidence",
]
AGENT_HEADERS = [
    "intermediary_name",
    "n_linked_companies",
    "linked_companies",
    "source_label",
    "confidence",
]
THEME_HEADERS = [
    "company_name",
    "normalized_company_name",
    "theme",
    "matched_keywords",
    "confidence",
    "needs_manual_review",
]
QUERY_HEADERS = ["target_type", "target_name", "query", "purpose", "priority"]


# Weak theme keyword map. These are heuristics only — every row in the
# resulting CSV is flagged ``needs_manual_review = true``.
THEME_KEYWORDS: dict[str, tuple[str, ...]] = {
    "yachting / charter / vessel": (
        "yacht",
        "yachting",
        "charter",
        "vessel",
        "marine",
        "shipping",
        "nautica",
        "sailing",
        "boat",
    ),
    "investment / holding / capital": (
        "invest",
        "holding",
        "capital",
        "equity",
        "finance",
        "fund",
        "trading",
    ),
    "services / administration": (
        "services",
        "service",
        "admin",
        "management",
        "consulting",
        "corporate",
        "secretarial",
        "fiduciary",
        "trust",
    ),
    "property / real estate": (
        "propert",
        "estate",
        "realty",
        "real estate",
        "land",
        "developments",
        "residence",
    ),
    "gaming": ("gaming", "casino", "betting", "bet", "wager", "poker", "sportsbook"),
    "procurement": ("procurement", "supply", "supplies", "logistics", "sourcing"),
    "media / marketing": ("media", "marketing", "advert", "publish", "broadcast"),
    "tech / digital": ("tech", "digital", "software", "data", "cyber", "ai", "cloud"),
}


# Registry sites to fan out per company for the external-search queue.
EXTERNAL_SEARCH_TARGETS_COMPANY = [
    ("registry filing", "site:registry.mfsa.mt OR site:rocsupport.mfsa.com.mt {name}"),
    ("litigation", '"{name}" (lawsuit OR claim OR litigation OR judgment)'),
    ("insolvency", '"{name}" (insolvency OR liquidation OR bankruptcy OR winding-up)'),
    ("sanctions", '"{name}" (sanction OR OFAC OR EU sanction OR OFSI)'),
    ("procurement", '"{name}" (tender OR contract OR procurement)'),
    ("property", '"{name}" (property OR real estate OR land registry)'),
    ("gaming", '"{name}" (MGA OR "gaming licence" OR gambling)'),
    ("shipping/yacht/charter", '"{name}" (yacht OR charter OR vessel OR IMO)'),
    ("directors/officers", '"{name}" (director OR officer OR shareholder OR UBO)'),
]
EXTERNAL_SEARCH_TARGETS_PERSON = [
    ("registry filings", '"{name}" director OR officer'),
    ("litigation", '"{name}" (lawsuit OR claim OR litigation)'),
    ("sanctions", '"{name}" (sanction OR OFAC OR OFSI)'),
    ("media", '"{name}" -site:linkedin.com -site:facebook.com'),
    ("PEP/UBO", '"{name}" (PEP OR beneficial owner OR UBO)'),
]


# ---------------------------------------------------------------------------
# Loaders. Each returns None or an empty frame when the source is missing.
# Callers then degrade gracefully.
# ---------------------------------------------------------------------------


def _read_optional_parquet(path: Path) -> pl.DataFrame | None:
    if not path.exists():
        log.warning("missing optional parquet: %s", path)
        return None
    try:
        return pl.read_parquet(path)
    except Exception as exc:  # noqa: BLE001
        log.warning("could not read %s: %s", path, exc)
        return None


@dataclass
class PackContext:
    """All loaded source data the builder needs. Anything that's missing
    stays as ``None`` and downstream code handles that case."""

    community_id: int
    person_query: str  # raw user input
    person_norm: str  # lowercase, single-spaced
    threshold: float
    generated_at: str
    members: pl.DataFrame  # confidence_communities filtered
    queue_row: dict[str, Any] | None
    cluster_scored: dict[str, Any] | None
    cluster_anomaly: dict[str, Any] | None
    icij_entities: pl.DataFrame | None
    icij_edges: pl.DataFrame | None
    icij_officers: pl.DataFrame | None
    icij_intermediaries: pl.DataFrame | None
    icij_addresses: pl.DataFrame | None
    icij_persons: pl.DataFrame | None
    confidence_edges: pl.DataFrame | None
    dossier_text: str | None
    dossier_companies: list[dict[str, str]] = field(default_factory=list)
    person_uids: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def normalize_person_query(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())


def load_context(
    community_id: int,
    person: str,
    *,
    threshold: float = DEFAULT_THRESHOLD,
    repo_root: Path = PROJECT_ROOT,
    reports_data_dir: Path | None = None,
    interim_dir: Path | None = None,
    processed_dir: Path | None = None,
    dossiers_dir: Path | None = None,
) -> PackContext:
    """Load every input the builder needs, tolerating missing files.

    Source-data directories can be overridden independently. The Railway
    job-server passes ``/data/...`` paths; locally they default to the
    repo-relative ``data/`` and ``docs/reports/`` layout.
    """

    reports_data = reports_data_dir or (repo_root / "docs" / "reports" / "data")
    interim_dir = interim_dir or (repo_root / "data" / "interim")
    processed_dir = processed_dir or (repo_root / "data" / "processed")
    dossiers_dir = dossiers_dir or (repo_root / "docs" / "reports" / "dossiers")

    communities = _read_optional_parquet(reports_data / "confidence_communities.parquet")
    if communities is None or communities.is_empty():
        raise SystemExit(
            f"[fatal] confidence_communities.parquet not found at {reports_data}. "
            "Cannot resolve community membership."
        )

    members = communities.filter(
        (pl.col("community_id") == community_id) & (pl.col("threshold") == threshold)
    )
    if members.is_empty():
        # fall back to "any threshold" before giving up
        members = communities.filter(pl.col("community_id") == community_id)
        if members.is_empty():
            raise SystemExit(
                f"[fatal] community_id={community_id} not found in confidence_communities."
            )

    warnings: list[str] = []

    queue = _read_optional_parquet(reports_data / "validation_queue.parquet")
    queue_row: dict[str, Any] | None = None
    if queue is not None:
        match = queue.filter(pl.col("community_id") == community_id)
        if not match.is_empty():
            queue_row = match.row(0, named=True)
        else:
            warnings.append(
                f"community_id={community_id} not present in validation_queue.parquet "
                "(cluster may not be in the top-N priority queue)."
            )
    else:
        warnings.append("validation_queue.parquet missing — priority context skipped.")

    scored = _read_optional_parquet(reports_data / "confidence_cluster_scored.parquet")
    scored_row: dict[str, Any] | None = None
    if scored is not None:
        match = scored.filter(pl.col("community_id") == community_id)
        if not match.is_empty():
            scored_row = match.row(0, named=True)

    anomaly = _read_optional_parquet(reports_data / "confidence_community_anomalies.parquet")
    anomaly_row: dict[str, Any] | None = None
    if anomaly is not None:
        match = anomaly.filter(pl.col("community_id") == community_id)
        if not match.is_empty():
            anomaly_row = match.row(0, named=True)

    icij_entities = _read_optional_parquet(interim_dir / "icij_entities.parquet")
    icij_edges = _read_optional_parquet(interim_dir / "icij_edges.parquet")
    icij_officers = _read_optional_parquet(interim_dir / "icij_officers.parquet")
    icij_intermediaries = _read_optional_parquet(interim_dir / "icij_intermediaries.parquet")
    icij_addresses = _read_optional_parquet(interim_dir / "icij_addresses.parquet")
    icij_persons = _read_optional_parquet(processed_dir / "icij_persons.parquet")
    confidence_edges = _read_optional_parquet(reports_data / "confidence_graph_edges.parquet")

    person_norm = normalize_person_query(person)

    # Dossier file: prefer slugified filename.
    dossier_slug = re.sub(r"[^a-z0-9]+", "-", person_norm).strip("-")
    dossier_path = dossiers_dir / f"{dossier_slug}.md"
    dossier_text = None
    if dossier_path.exists():
        dossier_text = dossier_path.read_text(encoding="utf-8")
    else:
        warnings.append(f"dossier file not found at {dossier_path} — using parquet only.")

    dossier_companies = parse_dossier_companies(dossier_text) if dossier_text else []

    # Person UIDs via icij_persons.
    person_uids: list[str] = []
    if icij_persons is not None and not icij_persons.is_empty():
        m = icij_persons.filter(pl.col("normalized_name") == person_norm)
        person_uids = m["entity_uid"].to_list()
    # Fallback: scan officers parquet.
    if not person_uids and icij_officers is not None:
        m = icij_officers.filter(pl.col("normalized_name") == person_norm)
        if not m.is_empty():
            person_uids = [f"icij:{s}" for s in m["source_id"].to_list()]

    if not person_uids and not dossier_companies:
        raise SystemExit(
            f"[fatal] person '{person}' not found in icij_persons, icij_officers, "
            "or dossier file. Cannot proceed."
        )

    return PackContext(
        community_id=community_id,
        person_query=person,
        person_norm=person_norm,
        threshold=threshold,
        generated_at=datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC"),
        members=members,
        queue_row=queue_row,
        cluster_scored=scored_row,
        cluster_anomaly=anomaly_row,
        icij_entities=icij_entities,
        icij_edges=icij_edges,
        icij_officers=icij_officers,
        icij_intermediaries=icij_intermediaries,
        icij_addresses=icij_addresses,
        icij_persons=icij_persons,
        confidence_edges=confidence_edges,
        dossier_text=dossier_text,
        dossier_companies=dossier_companies,
        person_uids=person_uids,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Dossier parsing
# ---------------------------------------------------------------------------

# Matches "- COMPANY NAME (mt) — address: ..." style lines in dossier .md.
_DOSSIER_COMPANY_RE = re.compile(
    r"^\s*-\s+(?P<name>[^—–\-]+?)\s*\((?P<juris>[a-z]{2})\)\s*(?:[—–-])?\s*address:\s*`?(?P<addr>[^`\n]*)`?",
    re.MULTILINE,
)


def parse_dossier_companies(text: str) -> list[dict[str, str]]:
    """Pull linked-company rows out of a person dossier markdown."""

    out: list[dict[str, str]] = []
    for m in _DOSSIER_COMPANY_RE.finditer(text):
        name = m.group("name").strip()
        out.append(
            {
                "name": name,
                "normalized_name": normalize_company_name(name),
                "jurisdiction": m.group("juris"),
                "address": m.group("addr").strip(),
            }
        )
    return out


# ---------------------------------------------------------------------------
# Member resolution: uid → (name, juris, address)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MemberEntity:
    uid: str
    name: str
    normalized_name: str
    jurisdiction: str | None
    address: str | None
    source_id: str
    is_seed: bool


def resolve_members(ctx: PackContext) -> list[MemberEntity]:
    """Join cluster member uids with icij_entities / icij_officers / icij_intermediaries
    to recover a (name, jurisdiction) for each."""

    uid_list = ctx.members["node_uid"].to_list()
    seed_lookup = dict(
        zip(
            ctx.members["node_uid"].to_list(),
            ctx.members["is_seed"].to_list(),
            strict=True,
        )
    )
    source_ids = [u.split(":", 1)[1] for u in uid_list if ":" in u]

    name_lookup: dict[str, tuple[str, str | None, str | None]] = {}
    if ctx.icij_entities is not None:
        rows = ctx.icij_entities.filter(pl.col("source_id").is_in(source_ids)).select(
            ["source_id", "name", "jurisdiction", "normalized_address"]
        )
        for r in rows.iter_rows(named=True):
            name_lookup[f"icij:{r['source_id']}"] = (
                r["name"],
                r["jurisdiction"],
                r["normalized_address"],
            )
    # Officers/intermediaries — uids that don't resolve to companies might be persons.
    if ctx.icij_officers is not None:
        rows = ctx.icij_officers.filter(pl.col("source_id").is_in(source_ids)).select(
            ["source_id", "name", "country"]
        )
        for r in rows.iter_rows(named=True):
            name_lookup.setdefault(f"icij:{r['source_id']}", (r["name"], r["country"], None))
    if ctx.icij_intermediaries is not None:
        rows = ctx.icij_intermediaries.filter(pl.col("source_id").is_in(source_ids)).select(
            ["source_id", "name", "country"]
        )
        for r in rows.iter_rows(named=True):
            name_lookup.setdefault(f"icij:{r['source_id']}", (r["name"], r["country"], None))

    out: list[MemberEntity] = []
    for uid in uid_list:
        name, juris, addr = name_lookup.get(uid, (uid, None, None))
        out.append(
            MemberEntity(
                uid=uid,
                name=name,
                normalized_name=normalize_company_name(name),
                jurisdiction=juris,
                address=addr,
                source_id=uid.split(":", 1)[1] if ":" in uid else uid,
                is_seed=bool(seed_lookup.get(uid, False)),
            )
        )
    return out


# ---------------------------------------------------------------------------
# Overlap, roles, repeated infra
# ---------------------------------------------------------------------------


def compute_overlap(
    ctx: PackContext, members: list[MemberEntity]
) -> list[dict[str, Any]]:
    """Compute company overlap between dossier and cluster.

    Match priority:
      1. exact normalized-name match (high confidence)
      2. cluster-only or dossier-only entries (so the reviewer sees the full
         population, not just the intersection)

    No fuzzy matching by default — fuzzy hits should only be added with a
    clear ``match_type`` flag and a low confidence score; we leave that hook
    for a future iteration.
    """

    member_by_norm: dict[str, list[MemberEntity]] = defaultdict(list)
    for m in members:
        if m.normalized_name:
            member_by_norm[m.normalized_name].append(m)

    dossier_by_norm: dict[str, list[dict[str, str]]] = defaultdict(list)
    for d in ctx.dossier_companies:
        if d["normalized_name"]:
            dossier_by_norm[d["normalized_name"]].append(d)

    rows: list[dict[str, Any]] = []
    seen: set[str] = set()

    # 1. Intersection (exact normalized match)
    for norm in sorted(set(member_by_norm) & set(dossier_by_norm)):
        seen.add(norm)
        m_hits = member_by_norm[norm]
        d_hits = dossier_by_norm[norm]
        rows.append(
            {
                "company_name": m_hits[0].name,
                "normalized_company_name": norm,
                "in_community": "true",
                "in_person_dossier": "true",
                "match_type": "exact_normalized",
                "confidence": "0.90",
                "source_record_ids": ";".join(sorted({m.uid for m in m_hits}))
                + " | dossier="
                + ";".join(sorted({d["jurisdiction"] for d in d_hits})),
                "notes": (
                    "candidate overlap — verify these uids refer to the same "
                    "underlying legal entity"
                ),
            }
        )

    # 2. Community-only
    for norm in sorted(set(member_by_norm) - set(dossier_by_norm)):
        if norm in seen:
            continue
        m_hits = member_by_norm[norm]
        rows.append(
            {
                "company_name": m_hits[0].name,
                "normalized_company_name": norm,
                "in_community": "true",
                "in_person_dossier": "false",
                "match_type": "community_only",
                "confidence": "1.00",
                "source_record_ids": ";".join(sorted({m.uid for m in m_hits})),
                "notes": "in cluster but not in person dossier",
            }
        )

    # 3. Dossier-only
    for norm in sorted(set(dossier_by_norm) - set(member_by_norm)):
        if norm in seen:
            continue
        d_hits = dossier_by_norm[norm]
        rows.append(
            {
                "company_name": d_hits[0]["name"],
                "normalized_company_name": norm,
                "in_community": "false",
                "in_person_dossier": "true",
                "match_type": "dossier_only",
                "confidence": "1.00",
                "source_record_ids": "dossier:" + d_hits[0]["jurisdiction"],
                "notes": (
                    "in dossier but not in this cluster — could be a different "
                    "Perry, or in a different community"
                ),
            }
        )

    return rows


def compute_person_company_roles(
    ctx: PackContext, members: list[MemberEntity]
) -> list[dict[str, Any]]:
    """Walk icij_edges to find Perry → cluster-member edges with roles."""

    if ctx.icij_edges is None or not ctx.person_uids:
        return []
    member_uids = {m.uid for m in members}
    name_by_uid = {m.uid: m.name for m in members}

    edges = ctx.icij_edges.lazy().filter(
        (pl.col("src_node").is_in(ctx.person_uids) & pl.col("dst_node").is_in(member_uids))
        | (pl.col("dst_node").is_in(ctx.person_uids) & pl.col("src_node").is_in(member_uids))
    ).collect()

    out: list[dict[str, Any]] = []
    for r in edges.iter_rows(named=True):
        if r["src_node"] in ctx.person_uids:
            person_uid, company_uid = r["src_node"], r["dst_node"]
        else:
            person_uid, company_uid = r["dst_node"], r["src_node"]
        out.append(
            {
                "person_name": ctx.person_query,
                "person_record_id": person_uid,
                "company_name": name_by_uid.get(company_uid, company_uid),
                "company_record_id": company_uid,
                "relationship_type": r["kind_raw"] or "unknown",
                "role": r["role"] or "unknown",
                "start_date": r["start_date"] or "",
                "end_date": r["end_date"] or "",
                "source": r["source"] or "icij",
                "leak": r["source_label"] or "",
                "confidence": "0.90",
                "notes": "candidate edge — verify against original ICIJ source record",
            }
        )
    # Deterministic ordering.
    out.sort(key=lambda x: (x["company_record_id"], x["role"]))
    return out


def _repeated_infra(
    ctx: PackContext, members: list[MemberEntity]
) -> tuple[list[dict], list[dict], list[dict]]:
    """Return (addresses, officers, intermediaries) lists of dicts. Each row
    is one repeated infra entity linked to >=2 cluster members."""

    member_uids = {m.uid for m in members}
    name_by_uid = {m.uid: m.name for m in members}

    addresses_out: list[dict[str, Any]] = []
    officers_out: list[dict[str, Any]] = []
    agents_out: list[dict[str, Any]] = []

    if ctx.icij_edges is None:
        return addresses_out, officers_out, agents_out

    # ------- registered addresses -------
    addr_edges = ctx.icij_edges.lazy().filter(
        (pl.col("kind_raw") == "registered_address")
        & (pl.col("src_node").is_in(member_uids) | pl.col("dst_node").is_in(member_uids))
    ).collect()

    addr_to_companies: dict[str, set[str]] = defaultdict(set)
    addr_to_source: dict[str, str] = {}
    for r in addr_edges.iter_rows(named=True):
        # one endpoint is a member company, the other is an address node.
        if r["src_node"] in member_uids:
            company, addr_uid = r["src_node"], r["dst_node"]
        else:
            company, addr_uid = r["dst_node"], r["src_node"]
        addr_to_companies[addr_uid].add(company)
        addr_to_source[addr_uid] = r["source_label"] or ""

    # Resolve address text.
    addr_text: dict[str, str] = {}
    if ctx.icij_addresses is not None and addr_to_companies:
        ids = [u.split(":", 1)[1] for u in addr_to_companies]
        text_rows = ctx.icij_addresses.filter(pl.col("source_id").is_in(ids)).select(
            ["source_id", "raw_text", "normalized_text"]
        )
        for r in text_rows.iter_rows(named=True):
            addr_text[f"icij:{r['source_id']}"] = (
                r["raw_text"] or r["normalized_text"] or f"icij:{r['source_id']}"
            )

    for addr_uid, companies in addr_to_companies.items():
        if len(companies) < 2:
            continue
        addresses_out.append(
            {
                "address": addr_text.get(addr_uid, addr_uid),
                "n_linked_companies": str(len(companies)),
                "linked_companies": ";".join(
                    sorted(name_by_uid.get(c, c) for c in companies)
                ),
                "source_label": addr_to_source.get(addr_uid, ""),
                "confidence": "0.85",
            }
        )

    # ------- officers (officer_of edges) -------
    off_edges = ctx.icij_edges.lazy().filter(
        (pl.col("kind_raw") == "officer_of")
        & (pl.col("dst_node").is_in(member_uids))
    ).collect()
    officer_to_companies: dict[str, set[str]] = defaultdict(set)
    officer_roles: dict[str, set[str]] = defaultdict(set)
    officer_source: dict[str, str] = {}
    for r in off_edges.iter_rows(named=True):
        officer_uid = r["src_node"]
        company_uid = r["dst_node"]
        officer_to_companies[officer_uid].add(company_uid)
        if r["role"]:
            officer_roles[officer_uid].add(r["role"])
        officer_source[officer_uid] = r["source_label"] or ""

    officer_names: dict[str, str] = {}
    if ctx.icij_officers is not None and officer_to_companies:
        ids = [u.split(":", 1)[1] for u in officer_to_companies]
        nm = ctx.icij_officers.filter(pl.col("source_id").is_in(ids)).select(
            ["source_id", "name"]
        )
        for r in nm.iter_rows(named=True):
            officer_names[f"icij:{r['source_id']}"] = r["name"]

    for off_uid, companies in officer_to_companies.items():
        if len(companies) < 2:
            continue
        officers_out.append(
            {
                "officer_name": officer_names.get(off_uid, off_uid),
                "n_linked_companies": str(len(companies)),
                "linked_companies": ";".join(
                    sorted(name_by_uid.get(c, c) for c in companies)
                ),
                "roles": ";".join(sorted(officer_roles.get(off_uid, set()))),
                "source_label": officer_source.get(off_uid, ""),
                "confidence": "0.85",
            }
        )

    # ------- intermediaries (intermediary_of edges) -------
    int_edges = ctx.icij_edges.lazy().filter(
        (pl.col("kind_raw") == "intermediary_of")
        & (pl.col("dst_node").is_in(member_uids))
    ).collect()
    int_to_companies: dict[str, set[str]] = defaultdict(set)
    int_source: dict[str, str] = {}
    for r in int_edges.iter_rows(named=True):
        int_to_companies[r["src_node"]].add(r["dst_node"])
        int_source[r["src_node"]] = r["source_label"] or ""

    int_names: dict[str, str] = {}
    if ctx.icij_intermediaries is not None and int_to_companies:
        ids = [u.split(":", 1)[1] for u in int_to_companies]
        nm = ctx.icij_intermediaries.filter(pl.col("source_id").is_in(ids)).select(
            ["source_id", "name"]
        )
        for r in nm.iter_rows(named=True):
            int_names[f"icij:{r['source_id']}"] = r["name"]

    for uid, companies in int_to_companies.items():
        if len(companies) < 2:
            continue
        agents_out.append(
            {
                "intermediary_name": int_names.get(uid, uid),
                "n_linked_companies": str(len(companies)),
                "linked_companies": ";".join(
                    sorted(name_by_uid.get(c, c) for c in companies)
                ),
                "source_label": int_source.get(uid, ""),
                "confidence": "0.85",
            }
        )

    addresses_out.sort(key=lambda r: (-int(r["n_linked_companies"]), r["address"]))
    officers_out.sort(key=lambda r: (-int(r["n_linked_companies"]), r["officer_name"]))
    agents_out.sort(key=lambda r: (-int(r["n_linked_companies"]), r["intermediary_name"]))
    return addresses_out, officers_out, agents_out


# ---------------------------------------------------------------------------
# Themes + search queries
# ---------------------------------------------------------------------------


def classify_themes(members: list[MemberEntity]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for m in members:
        name_lc = (m.name or "").lower()
        matched: list[tuple[str, list[str]]] = []
        for theme, keywords in THEME_KEYWORDS.items():
            hits = [k for k in keywords if k in name_lc]
            if hits:
                matched.append((theme, hits))
        if matched:
            theme, hits = matched[0]
            rows.append(
                {
                    "company_name": m.name,
                    "normalized_company_name": m.normalized_name,
                    "theme": theme,
                    "matched_keywords": ";".join(hits),
                    "confidence": "0.30",
                    "needs_manual_review": "true",
                }
            )
        else:
            rows.append(
                {
                    "company_name": m.name,
                    "normalized_company_name": m.normalized_name,
                    "theme": "unknown",
                    "matched_keywords": "",
                    "confidence": "0.00",
                    "needs_manual_review": "true",
                }
            )
    rows.sort(key=lambda r: (r["theme"], r["company_name"]))
    return rows


def build_search_queries(
    ctx: PackContext, members: list[MemberEntity], overlap_rows: list[dict]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    overlap_names = {r["company_name"] for r in overlap_rows if r["in_person_dossier"] == "true"}

    # High-priority: dossier-overlap companies first.
    for m in members:
        priority = "high" if m.name in overlap_names else "medium"
        for purpose, template in EXTERNAL_SEARCH_TARGETS_COMPANY:
            rows.append(
                {
                    "target_type": "company",
                    "target_name": m.name,
                    "query": template.format(name=m.name),
                    "purpose": purpose,
                    "priority": priority,
                }
            )

    # Person queries.
    for purpose, template in EXTERNAL_SEARCH_TARGETS_PERSON:
        rows.append(
            {
                "target_type": "person",
                "target_name": ctx.person_query,
                "query": template.format(name=ctx.person_query),
                "purpose": purpose,
                "priority": "high",
            }
        )

    rows.sort(
        key=lambda r: (
            {"high": 0, "medium": 1, "low": 2}.get(r["priority"], 9),
            r["target_type"],
            r["target_name"],
            r["purpose"],
        )
    )
    return rows


# ---------------------------------------------------------------------------
# Graph paths
# ---------------------------------------------------------------------------


def build_graph_paths_md(
    ctx: PackContext,
    members: list[MemberEntity],
    roles: list[dict[str, Any]],
    repeated_addresses: list[dict[str, Any]],
    repeated_officers: list[dict[str, Any]],
    repeated_agents: list[dict[str, Any]],
) -> str:
    parts: list[str] = []
    parts.append(f"# Graph paths — cluster {ctx.community_id} / {ctx.person_query}\n")
    parts.append(f"_Generated {ctx.generated_at}. Machine-extracted — verify each edge._\n")

    parts.append("\n## Direct person → company edges\n")
    if not roles:
        parts.append("_(none found in icij_edges)_\n")
    else:
        parts.append(
            "| person uid | → | company | role | leak |\n"
            "| --- | --- | --- | --- | --- |\n"
        )
        for r in roles:
            parts.append(
                f"| `{r['person_record_id']}` | → | {r['company_name']} | "
                f"{r['role']} | {r['leak']} |\n"
            )

    parts.append("\n## Top intermediary bridges (>=2 cluster members)\n")
    if not repeated_agents:
        parts.append("_(no recurring intermediaries found)_\n")
    else:
        for a in repeated_agents[:15]:
            parts.append(
                f"- **{a['intermediary_name']}** — {a['n_linked_companies']} companies: "
                f"{a['linked_companies']}\n"
            )

    parts.append("\n## Top officer bridges (>=2 cluster members)\n")
    if not repeated_officers:
        parts.append("_(no recurring officers found)_\n")
    else:
        for o in repeated_officers[:15]:
            parts.append(
                f"- **{o['officer_name']}** ({o['roles']}) — "
                f"{o['n_linked_companies']} companies: {o['linked_companies']}\n"
            )

    parts.append("\n## Top address bridges (>=2 cluster members)\n")
    if not repeated_addresses:
        parts.append("_(no recurring addresses found)_\n")
    else:
        for a in repeated_addresses[:15]:
            parts.append(
                f"- **{a['address']}** — {a['n_linked_companies']} companies: "
                f"{a['linked_companies']}\n"
            )

    # Confidence-weighted internal edges (sample)
    parts.append("\n## Internal cluster edges — top 25 by credibility\n")
    if ctx.confidence_edges is None:
        parts.append("_(confidence_graph_edges.parquet not available)_\n")
    else:
        member_uids = {m.uid for m in members}
        ce = ctx.confidence_edges.filter(
            pl.col("src_node").is_in(member_uids) & pl.col("dst_node").is_in(member_uids)
        ).sort("credibility", descending=True).head(25)
        name_by_uid = {m.uid: m.name for m in members}
        parts.append("| src | → | dst | kind | source | credibility |\n")
        parts.append("| --- | --- | --- | --- | --- | ---: |\n")
        for r in ce.iter_rows(named=True):
            parts.append(
                f"| {name_by_uid.get(r['src_node'], r['src_node'])} | → | "
                f"{name_by_uid.get(r['dst_node'], r['dst_node'])} | "
                f"{r['kind_raw']} | {r['source_label']} | {r['credibility']:.3f} |\n"
            )

    return "".join(parts)


# ---------------------------------------------------------------------------
# Same-person evidence matrix
# ---------------------------------------------------------------------------


def same_person_evidence(ctx: PackContext) -> dict[str, list[str]]:
    """Heuristic, cautious matrix. Final verdict is always 'Human review required'."""

    supporting: list[str] = []
    contradictory: list[str] = []
    missing: list[str] = []

    if len(ctx.person_uids) > 1:
        supporting.append(
            f"{len(ctx.person_uids)} ICIJ uids share normalized name "
            f"`{ctx.person_norm}` ({', '.join(ctx.person_uids)})."
        )
    else:
        missing.append("only one or zero ICIJ uids — cannot test same-person consistency.")

    # Country/jurisdiction consistency across persons rows.
    if ctx.icij_persons is not None and ctx.person_uids:
        rows = ctx.icij_persons.filter(pl.col("entity_uid").is_in(ctx.person_uids))
        countries = sorted({c for c in rows["country"].to_list() if c})
        if len(countries) == 1:
            supporting.append(f"All ICIJ rows report the same country: {countries[0]}.")
        elif len(countries) > 1:
            contradictory.append(f"ICIJ rows disagree on country: {countries}.")
        else:
            missing.append("country field missing in ICIJ persons rows.")

    # DOB / address comparison would go here. Not available in current parquets.
    missing.append("date-of-birth not available in icij_persons; cannot compare DOB.")
    missing.append(
        "no canonical home-address field for persons; cannot compare residential address."
    )

    if ctx.dossier_text and "no web mentions" in ctx.dossier_text.lower():
        missing.append("dossier reports 0 web mentions — no third-party corroboration online.")

    return {
        "supporting": supporting,
        "contradictory": contradictory,
        "missing": missing,
    }


# ---------------------------------------------------------------------------
# Ordinary-vs-unusual indicators
# ---------------------------------------------------------------------------


def ordinary_vs_unusual(
    ctx: PackContext,
    members: list[MemberEntity],
    repeated_addresses: list[dict],
    repeated_officers: list[dict],
    repeated_agents: list[dict],
    themes: list[dict],
) -> dict[str, Any]:
    n = len(members) or 1
    # reuse rate = fraction of cluster members touched by a repeated entity.
    members_touched_addr: set[str] = set()
    for r in repeated_addresses:
        members_touched_addr.update(r["linked_companies"].split(";"))
    members_touched_off: set[str] = set()
    for r in repeated_officers:
        members_touched_off.update(r["linked_companies"].split(";"))
    members_touched_int: set[str] = set()
    for r in repeated_agents:
        members_touched_int.update(r["linked_companies"].split(";"))

    theme_counter = Counter(r["theme"] for r in themes)
    top_theme, top_count = theme_counter.most_common(1)[0] if themes else ("n/a", 0)

    return {
        "cluster_size": n,
        "officer_reuse_rate": round(len(members_touched_off) / n, 3),
        "address_reuse_rate": round(len(members_touched_addr) / n, 3),
        "intermediary_reuse_rate": round(len(members_touched_int) / n, 3),
        "top_theme": top_theme,
        "top_theme_share": round(top_count / n, 3) if themes else 0.0,
        "underreportedness": (
            ctx.queue_row.get("underreportedness") if ctx.queue_row else None
        ),
        "contradiction_density": (
            ctx.cluster_scored.get("contradiction_density") if ctx.cluster_scored else None
        ),
        "isolation": ctx.cluster_anomaly.get("isolation") if ctx.cluster_anomaly else None,
        "anomaly_score": (
            ctx.cluster_anomaly.get("anomaly_score") if ctx.cluster_anomaly else None
        ),
        "n_repeated_addresses": len(repeated_addresses),
        "n_repeated_officers": len(repeated_officers),
        "n_repeated_intermediaries": len(repeated_agents),
    }


# ---------------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------------


def _write_csv(path: Path, headers: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        for r in rows:
            w.writerow({h: r.get(h, "") for h in headers})


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8"
    )


def _md_table(headers: list[str], rows: list[list[str]]) -> str:
    if not rows:
        return "_(no rows)_\n"
    out = ["| " + " | ".join(headers) + " |\n"]
    out.append("| " + " | ".join("---" for _ in headers) + " |\n")
    for r in rows:
        out.append("| " + " | ".join(str(c) for c in r) + " |\n")
    return "".join(out)


def render_markdown(  # noqa: PLR0913 — single template renderer; splitting hurts readability
    ctx: PackContext,
    members: list[MemberEntity],
    overlap: list[dict],
    roles: list[dict],
    repeated_addresses: list[dict],
    repeated_officers: list[dict],
    repeated_agents: list[dict],
    themes: list[dict],
    queries: list[dict],
    spe: dict[str, list[str]],
    odd: dict[str, Any],
) -> str:
    parts: list[str] = []
    parts.append(f"# Cluster {ctx.community_id} Validation Pack\n\n")
    parts.append(
        "## Status\nMachine-generated. **Human review required.** Not an "
        "accusation or finding of wrongdoing.\n\n"
    )

    parts.append("## Investigation target\n")
    parts.append(f"- Community ID: **{ctx.community_id}**\n")
    parts.append(f"- Human anchor: **{ctx.person_query}**\n")
    parts.append(f"- Generated at: {ctx.generated_at}\n")
    parts.append("- Script: `scripts/build_validation_pack.py`\n")
    parts.append(f"- Threshold: {ctx.threshold}\n\n")

    if ctx.warnings:
        parts.append("### Data gaps / warnings\n")
        for w in ctx.warnings:
            parts.append(f"- ⚠️ {w}\n")
        parts.append("\n")

    parts.append("## Machine-generated triage summary\n")
    q = ctx.queue_row or {}
    s = ctx.cluster_scored or {}
    a = ctx.cluster_anomaly or {}
    triage_rows = [
        ["Priority score", f"{q.get('priority_score', 'n/a')}"],
        ["Cluster size", str(len(members))],
        ["Cluster confidence", f"{s.get('cluster_confidence', 'n/a')}"],
        ["Mean edge credibility", f"{s.get('mean_edge_credibility', 'n/a')}"],
        ["Contradiction density", f"{s.get('contradiction_density', 'n/a')}"],
        ["Anomaly score", f"{a.get('anomaly_score', 'n/a')}"],
        ["Isolation", f"{a.get('isolation', 'n/a')}"],
        ["Seed nodes", f"{a.get('n_seeds', 'n/a')}"],
        ["Underreportedness", f"{q.get('underreportedness', 'n/a')}"],
        ["Attestation density", f"{q.get('attestation_density', 'n/a')}"],
    ]
    parts.append(_md_table(["Metric", "Value"], triage_rows))
    parts.append("\n")

    parts.append("## Why this cluster ranked highly\n")
    if q:
        parts.append(
            f"The composite priority formula produced **{q.get('priority_score')}**, "
            f"weighted on:\n\n"
            f"- structurally strange (anomaly): {q.get('anomaly_score')}\n"
            f"- high-confidence: {q.get('cluster_confidence')}\n"
            f"- highly connected: {q.get('connectedness')}\n"
            f"- underreported: {q.get('underreportedness')}\n\n"
            "See `docs/reports/validation_queue.md` for the full ranking context.\n\n"
        )
    else:
        parts.append("_Cluster not present in validation_queue.parquet._\n\n")

    parts.append("## Community sample members (first 20)\n")
    sample_rows = [[m.name, m.uid, m.jurisdiction or "", "seed" if m.is_seed else ""]
                   for m in members[:20]]
    parts.append(_md_table(["Name", "uid", "Jurisdiction", "Seed?"], sample_rows))
    parts.append(f"\n_Total cluster size: {len(members)}_\n\n")

    parts.append(f"## {ctx.person_query} dossier summary\n")
    if ctx.dossier_text:
        # Pull the header block for context.
        head_lines = []
        for line in ctx.dossier_text.splitlines()[:5]:
            head_lines.append(line)
        parts.append("```\n" + "\n".join(head_lines) + "\n```\n")
        parts.append(
            f"- Dossier linked companies (parsed): **{len(ctx.dossier_companies)}**\n"
            f"- ICIJ uids resolved to this name: **{len(ctx.person_uids)}**: "
            f"{', '.join(ctx.person_uids) if ctx.person_uids else '_(none)_'}\n\n"
        )
    else:
        parts.append("_(no dossier file)_\n\n")

    parts.append("## Company overlap table\n")
    overlap_rows = [
        [r["company_name"], r["normalized_company_name"], r["in_community"],
         r["in_person_dossier"], r["match_type"], r["confidence"]]
        for r in overlap[:50]
    ]
    parts.append(
        _md_table(
            ["Company", "Normalized", "In cluster?", "In dossier?", "Match type", "Conf"],
            overlap_rows,
        )
    )
    overlap_hits = sum(1 for r in overlap if r["match_type"] == "exact_normalized")
    parts.append(
        f"\n_Exact normalized-name overlap: **{overlap_hits}** companies. "
        "Full CSV: `data/cluster_{cid}_person_overlap.csv`._\n\n".format(cid=ctx.community_id)
    )

    parts.append("## Person-company role evidence\n")
    role_rows = [
        [r["company_name"], r["relationship_type"], r["role"], r["leak"]] for r in roles[:30]
    ]
    parts.append(
        _md_table(["Company", "Relationship", "Role", "Leak"], role_rows)
    )
    parts.append(
        f"\n_{len(roles)} edges total. Full CSV: "
        f"`data/cluster_{ctx.community_id}_person_company_roles.csv`._\n\n"
    )

    parts.append("## Recurring infrastructure\n### Addresses\n")
    parts.append(
        _md_table(
            ["Address", "N linked", "Source"],
            [[r["address"], r["n_linked_companies"], r["source_label"]]
             for r in repeated_addresses[:10]],
        )
    )
    parts.append("\n### Officers / directors\n")
    parts.append(
        _md_table(
            ["Officer", "N linked", "Roles"],
            [[r["officer_name"], r["n_linked_companies"], r["roles"]]
             for r in repeated_officers[:10]],
        )
    )
    parts.append("\n### Agents / intermediaries\n")
    parts.append(
        _md_table(
            ["Intermediary", "N linked", "Source"],
            [[r["intermediary_name"], r["n_linked_companies"], r["source_label"]]
             for r in repeated_agents[:10]],
        )
    )
    parts.append(
        "\n### Secretaries / service providers\n"
        "_(officer rows with role containing 'secretary' or 'service' surfaced "
        "in the officers table above; not separated in the source data.)_\n\n"
    )

    parts.append("## Company theme classification\n")
    theme_counter = Counter(r["theme"] for r in themes)
    theme_rows = [[t, str(n)] for t, n in theme_counter.most_common()]
    parts.append(_md_table(["Theme", "Count"], theme_rows))
    parts.append(
        "\n_These are **weak labels** — keyword-based heuristics, every row "
        "is flagged needs_manual_review = true._\n\n"
    )

    parts.append("## Graph paths\n")
    parts.append(
        f"See `data/cluster_{ctx.community_id}_graph_paths.md` for the full "
        "extracted-paths report.\n\n"
    )

    parts.append("## External search queue\n")
    parts.append(
        f"`data/cluster_{ctx.community_id}_external_search_queries.csv` "
        f"contains **{len(queries)}** queries.\n"
        "No external search has been run automatically (no safe abstraction "
        "wired). The reviewer should execute these queries by hand against the "
        "appropriate registries / search engines, or pass "
        "`--run-external-search` if/when an in-repo abstraction is added.\n\n"
    )

    parts.append("## Same-person evidence matrix\n")
    parts.append(
        "> **Are the Peter Kevin Perry records the same person?**\n\n"
        "**Final verdict: Human review required.** Below is candidate evidence "
        "only — do not treat as a determination.\n\n"
    )
    parts.append("**Supporting evidence:**\n")
    for line in spe["supporting"] or ["_(none)_"]:
        parts.append(f"- {line}\n")
    parts.append("\n**Contradictory evidence:**\n")
    for line in spe["contradictory"] or ["_(none)_"]:
        parts.append(f"- {line}\n")
    parts.append("\n**Missing evidence:**\n")
    for line in spe["missing"] or ["_(none)_"]:
        parts.append(f"- {line}\n")
    parts.append("\n")

    parts.append("## Ordinary vs unusual analysis\n")
    parts.append(
        _md_table(
            ["Indicator", "Value", "Interpretation"],
            [
                ["Cluster size", str(odd["cluster_size"]), ""],
                ["Officer reuse rate", str(odd["officer_reuse_rate"]),
                 "high reuse = corporate-services hub"],
                ["Address reuse rate", str(odd["address_reuse_rate"]),
                 "high reuse = shared registered office"],
                ["Intermediary reuse rate", str(odd["intermediary_reuse_rate"]),
                 "high reuse = shared agent"],
                ["Top theme", odd["top_theme"], f"share={odd['top_theme_share']}"],
                ["Anomaly score", str(odd["anomaly_score"]), ""],
                ["Isolation", str(odd["isolation"]), "1.0 = no cross-cluster bridges"],
                ["Underreportedness", str(odd["underreportedness"]),
                 "1.0 = no name overlap with formal registries"],
                ["Contradiction density", str(odd["contradiction_density"]), ""],
                ["# repeated addresses", str(odd["n_repeated_addresses"]), ""],
                ["# repeated officers", str(odd["n_repeated_officers"]), ""],
                ["# repeated intermediaries", str(odd["n_repeated_intermediaries"]), ""],
            ],
        )
    )
    parts.append(
        "\n> **TODO:** percentile ranks against a cluster baseline have not "
        "been computed (no per-cluster baseline parquet present). Raw values "
        "only above.\n\n"
    )

    parts.append("## Contradictory or missing evidence\n")
    parts.append(
        "- ICIJ records do not include date-of-birth for persons; same-person "
        "claims cannot be tested on DOB.\n"
        "- No web-corroboration is wired (dossier records 0 hits as of "
        "2026-05-16).\n"
        "- Address fields on most cluster member entity rows are null; "
        "address-bridge analysis depends on `registered_address` edges.\n\n"
    )

    parts.append(
        "## Human review checklist\n"
        "- [ ] Confirm whether the Peter Kevin Perry records refer to the "
        "same person\n"
        "- [ ] Verify each overlapping company in source records\n"
        "- [ ] Verify roles and dates\n"
        "- [ ] Check external registry records (MFSA, Companies House, etc.)\n"
        "- [ ] Check litigation / insolvency / sanctions / procurement / "
        "property / gaming / yacht records\n"
        "- [ ] Determine whether this is ordinary corporate-services plumbing "
        "or unusual network structure\n"
        "- [ ] Draft cautious narrative if evidence supports it\n\n"
    )

    parts.append("## Preliminary human verdict\nPending.\n\n")
    parts.append(
        "## Publication risk notes\n"
        "- No allegations should be made without independent corroboration.\n"
        "- Same-name does not imply same-person.\n"
        "- Corporate-services hubs in Malta legitimately serve hundreds of "
        "unrelated clients; recurring infrastructure is a starting point, not "
        "an indictment.\n"
        "- Preserve provenance (source_label, leak name, uid) for every claim "
        "carried into any published narrative.\n"
    )
    return "".join(parts)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_pack(
    community_id: int,
    person: str,
    *,
    threshold: float = DEFAULT_THRESHOLD,
    repo_root: Path = PROJECT_ROOT,
    out_dir: Path | None = None,
    run_external_search: bool = False,
    reports_data_dir: Path | None = None,
    interim_dir: Path | None = None,
    processed_dir: Path | None = None,
    dossiers_dir: Path | None = None,
) -> dict[str, Path]:
    """Build the validation pack. Returns a dict of {kind: path_written}.

    Idempotent and deterministic given the same source parquets.
    """

    ctx = load_context(
        community_id,
        person,
        threshold=threshold,
        repo_root=repo_root,
        reports_data_dir=reports_data_dir,
        interim_dir=interim_dir,
        processed_dir=processed_dir,
        dossiers_dir=dossiers_dir,
    )
    members = resolve_members(ctx)

    overlap = compute_overlap(ctx, members)
    roles = compute_person_company_roles(ctx, members)
    repeated_addresses, repeated_officers, repeated_agents = _repeated_infra(ctx, members)
    themes = classify_themes(members)
    queries = build_search_queries(ctx, members, overlap)
    spe = same_person_evidence(ctx)
    odd = ordinary_vs_unusual(
        ctx, members, repeated_addresses, repeated_officers, repeated_agents, themes
    )

    if run_external_search:
        ctx.warnings.append(
            "--run-external-search passed, but no in-repo search abstraction "
            "is wired; queries written to CSV for manual execution."
        )

    base = (out_dir or repo_root / "docs" / "validation").resolve()
    data_dir = base / "data"
    paths = {
        "markdown": base / f"cluster_{community_id}.md",
        "profile_json": data_dir / f"cluster_{community_id}_profile.json",
        "overlap_csv": data_dir / f"cluster_{community_id}_person_overlap.csv",
        "roles_csv": data_dir / f"cluster_{community_id}_person_company_roles.csv",
        "addresses_csv": data_dir / f"cluster_{community_id}_repeated_addresses.csv",
        "officers_csv": data_dir / f"cluster_{community_id}_repeated_officers.csv",
        "agents_csv": data_dir / f"cluster_{community_id}_repeated_agents.csv",
        "themes_csv": data_dir / f"cluster_{community_id}_company_themes.csv",
        "queries_csv": data_dir / f"cluster_{community_id}_external_search_queries.csv",
        "graph_paths_md": data_dir / f"cluster_{community_id}_graph_paths.md",
    }

    _write_csv(paths["overlap_csv"], OVERLAP_HEADERS, overlap)
    _write_csv(paths["roles_csv"], ROLES_HEADERS, roles)
    _write_csv(paths["addresses_csv"], ADDR_HEADERS, repeated_addresses)
    _write_csv(paths["officers_csv"], OFFICER_HEADERS, repeated_officers)
    _write_csv(paths["agents_csv"], AGENT_HEADERS, repeated_agents)
    _write_csv(paths["themes_csv"], THEME_HEADERS, themes)
    _write_csv(paths["queries_csv"], QUERY_HEADERS, queries)

    paths["graph_paths_md"].parent.mkdir(parents=True, exist_ok=True)
    paths["graph_paths_md"].write_text(
        build_graph_paths_md(
            ctx, members, roles, repeated_addresses, repeated_officers, repeated_agents
        ),
        encoding="utf-8",
    )

    profile = {
        "community_id": community_id,
        "person": person,
        "person_normalized": ctx.person_norm,
        "generated_at": ctx.generated_at,
        "threshold": threshold,
        "person_uids": ctx.person_uids,
        "n_members": len(members),
        "queue_row": ctx.queue_row,
        "cluster_scored": ctx.cluster_scored,
        "cluster_anomaly": ctx.cluster_anomaly,
        "ordinary_vs_unusual": odd,
        "same_person_evidence": spe,
        "warnings": ctx.warnings,
        "members_sample": [
            {"uid": m.uid, "name": m.name, "jurisdiction": m.jurisdiction, "seed": m.is_seed}
            for m in members[:50]
        ],
    }
    _write_json(paths["profile_json"], profile)

    paths["markdown"].parent.mkdir(parents=True, exist_ok=True)
    paths["markdown"].write_text(
        render_markdown(
            ctx, members, overlap, roles, repeated_addresses, repeated_officers,
            repeated_agents, themes, queries, spe, odd,
        ),
        encoding="utf-8",
    )

    return paths


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Build a validation evidence pack for a (community, person) pair.",
    )
    p.add_argument("--community-id", type=int, required=True)
    p.add_argument("--person", type=str, required=True)
    p.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_THRESHOLD,
        help="confidence_communities threshold to use (default 0.9)",
    )
    p.add_argument(
        "--run-external-search",
        action="store_true",
        help=(
            "If a safe in-repo search abstraction exists, run the generated "
            "queries through it. Currently a no-op (no abstraction wired) — "
            "queries are still written to CSV."
        ),
    )
    p.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="override the output directory (default: docs/validation/)",
    )
    p.add_argument(
        "--reports-data-dir",
        type=Path,
        default=None,
        help="directory holding confidence_* and validation_queue parquets "
        "(default: docs/reports/data/). On Railway pass /data/processed/.",
    )
    p.add_argument(
        "--interim-dir",
        type=Path,
        default=None,
        help="directory holding icij_* interim parquets (default: data/interim/). "
        "On Railway pass /data/interim/.",
    )
    p.add_argument(
        "--processed-dir",
        type=Path,
        default=None,
        help="directory holding icij_persons.parquet (default: data/processed/). "
        "On Railway pass /data/processed/.",
    )
    p.add_argument(
        "--dossiers-dir",
        type=Path,
        default=None,
        help="directory holding person dossier markdown files "
        "(default: docs/reports/dossiers/).",
    )
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    paths = build_pack(
        community_id=args.community_id,
        person=args.person,
        threshold=args.threshold,
        out_dir=args.out_dir,
        run_external_search=args.run_external_search,
        reports_data_dir=args.reports_data_dir,
        interim_dir=args.interim_dir,
        processed_dir=args.processed_dir,
        dossiers_dir=args.dossiers_dir,
    )

    print("Generated:")
    for kind, path in paths.items():
        print(f"  {kind:18s} {path.relative_to(PROJECT_ROOT) if path.is_absolute() and PROJECT_ROOT in path.parents else path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
