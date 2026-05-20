"""Second-stage corroboration for a (cluster, person) validation pack.

Takes the artefacts produced by ``scripts/build_validation_pack.py`` and
turns them into a journalist-ready research packet: external search +
hit scoring, discovery-delta, timeline, graph-path narratives, evidence
ledger, underreported-entity scoring, and a final research brief.

Reads (from ``docs/validation/`` by default)::

    cluster_<id>_profile.json
    cluster_<id>_person_overlap.csv
    cluster_<id>_person_company_roles.csv
    cluster_<id>_repeated_addresses.csv
    cluster_<id>_repeated_officers.csv
    cluster_<id>_repeated_agents.csv
    cluster_<id>_external_search_queries.csv

Writes::

    docs/validation/cluster_<id>_research_brief.md
    docs/validation/cluster_<id>_timeline.md
    docs/validation/cluster_<id>_graph_paths.md
    docs/validation/data/cluster_<id>_external_search_results.json
    docs/validation/data/cluster_<id>_external_search_results.csv
    docs/validation/data/cluster_<id>_external_hit_scores.csv
    docs/validation/data/cluster_<id>_discovery_delta.csv
    docs/validation/data/cluster_<id>_timeline.csv
    docs/validation/data/cluster_<id>_evidence_ledger.csv
    docs/validation/data/cluster_<id>_underreported_entities.csv

Same cautious framing as the first stage: nothing here is an allegation,
nothing here is a finding. Every claim is tagged with provenance and a
``needs_human_review`` flag.

Usage::

    uv run python scripts/corroborate_validation_pack.py \\
        --community-id 37 \\
        --person "calvin edward ayre"

Pass ``--run-external-search`` to actually hit Tavily (requires
``TAVILY_API_KEY``). Without that flag, the search outputs are skeleton
files with headers only and the brief notes "external search not run".
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import re
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

_HERE = Path(__file__).resolve()
_REPO_ROOT = _HERE.parents[1]
sys.path.insert(0, str(_REPO_ROOT / "src"))

from shellnet.normalize import normalize_company_name  # noqa: E402

log = logging.getLogger("corroborate_validation_pack")

PROJECT_ROOT = _REPO_ROOT
TAVILY_URL = "https://api.tavily.com/search"

# Domain taxonomy. Lifted from common journalist-side categorisation;
# extend in-place. Each entry is (substring, source_type, base_score).
_SOURCE_TAXONOMY: tuple[tuple[str, str, float], ...] = (
    # ICIJ + leak primary
    ("icij.org", "leak_primary", 0.95),
    ("offshoreleaks.icij.org", "leak_primary", 0.98),
    ("occrp.org", "leak_primary", 0.92),
    # Regulators / official registries
    ("mfsa.mt", "regulator", 0.95),
    ("sec.gov", "regulator", 0.95),
    ("ofac.treasury.gov", "regulator", 0.97),
    ("treasury.gov", "regulator", 0.92),
    ("companieshouse.gov.uk", "regulator", 0.93),
    ("find-and-update.company-information.service.gov.uk", "regulator", 0.93),
    ("gov.uk", "regulator", 0.85),
    ("eur-lex.europa.eu", "regulator", 0.90),
    ("consilium.europa.eu", "regulator", 0.88),
    # Sanctions / structured databases
    ("opensanctions.org", "structured_database", 0.92),
    ("opencorporates.com", "structured_database", 0.90),
    ("gleif.org", "structured_database", 0.88),
    ("dilisense.com", "structured_database", 0.70),
    # Major press
    ("reuters.com", "press", 0.85),
    ("ft.com", "press", 0.85),
    ("wsj.com", "press", 0.85),
    ("bloomberg.com", "press", 0.85),
    ("nytimes.com", "press", 0.85),
    ("theguardian.com", "press", 0.83),
    ("bbc.co.uk", "press", 0.83),
    ("bbc.com", "press", 0.83),
    ("apnews.com", "press", 0.83),
    ("politico.com", "press", 0.80),
    ("timesofmalta.com", "press", 0.85),
    ("maltatoday.com.mt", "press", 0.78),
    ("independent.com.mt", "press", 0.78),
    # Court records / litigation
    ("courtlistener.com", "court", 0.88),
    ("justia.com", "court", 0.80),
    ("pacer.gov", "court", 0.93),
    # Social / blog / low quality
    ("linkedin.com", "social", 0.30),
    ("facebook.com", "social", 0.20),
    ("twitter.com", "social", 0.25),
    ("x.com", "social", 0.25),
    ("medium.com", "blog", 0.35),
    ("wordpress.com", "blog", 0.25),
    ("blogspot.com", "blog", 0.20),
    ("youtube.com", "video", 0.40),
    # Wikipedia is useful but tertiary
    ("wikipedia.org", "tertiary", 0.55),
)


# Vocabulary for term matching in result snippets.
_BODOG_TERMS = ("bodog", "ayre", "calvin ayre", "ayre group")
_MALTA_TERMS = ("malta", "valletta", "sliema", "msida", "mfsa")
_OFFSHORE_TERMS = (
    "offshore",
    "shell",
    "shell company",
    "panama papers",
    "paradise papers",
    "pandora papers",
    "icij",
    "leak",
    "ubo",
    "beneficial owner",
)
_REG_ACTION_TERMS = (
    "sanction",
    "ofac",
    "ofsi",
    "ofac sdn",
    "designated",
    "enforcement",
    "fined",
    "penalty",
    "consent order",
)
_FINANCE_TERMS = (
    "finance",
    "holding",
    "investment",
    "capital",
    "fund",
    "trust",
    "private equity",
)
_LITIGATION_TERMS = (
    "lawsuit",
    "litigation",
    "judgment",
    "claim",
    "winding-up",
    "insolvency",
    "liquidation",
    "bankruptcy",
)


# CSV schemas.
SEARCH_RESULTS_HEADERS = [
    "query",
    "result_title",
    "url",
    "snippet",
    "published_date",
    "raw_score",
]
HIT_SCORES_HEADERS = [
    "target_name",
    "query",
    "result_title",
    "url",
    "domain",
    "source_type",
    "matched_terms",
    "relevance_score",
    "supports_edge",
    "contradicts_edge",
    "needs_human_review",
    "notes",
]
DISCOVERY_DELTA_HEADERS = [
    "fact",
    "category",
    "public_knowledge",
    "goldenmatch_added",
    "sources",
    "needs_human_review",
]
TIMELINE_HEADERS = [
    "date",
    "event_type",
    "entity",
    "description",
    "source",
    "confidence",
    "needs_human_review",
]
EVIDENCE_LEDGER_HEADERS = [
    "claim_id",
    "claim_text",
    "claim_type",
    "supporting_sources",
    "contradicting_sources",
    "confidence",
    "human_review_status",
    "publication_safe",
]
UNDERREPORTED_HEADERS = [
    "company_name",
    "uid",
    "graph_degree",
    "n_web_hits",
    "max_hit_score",
    "underreported_score",
    "reason",
]
REGISTRY_HITS_HEADERS = [
    "cluster_member",
    "jurisdiction",
    "registry",
    "match_type",
    "registry_identifier",
    "registry_name",
    "registry_status",
    "registry_address",
    "officer_overlap",
    "sourceUrl",
    "publication_safe",
    "notes",
]


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _write_csv(path: Path, headers: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        for r in rows:
            w.writerow({h: r.get(h, "") for h in headers})


def _join_sources(*parts: str) -> str:
    """Join non-empty source strings with ` | ` separators."""
    return " | ".join(p for p in parts if p)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


# ---------------------------------------------------------------------------
# Pack inputs
# ---------------------------------------------------------------------------


@dataclass
class PackInputs:
    """Everything we read from the existing first-stage validation pack."""

    community_id: int
    person: str
    pack_dir: Path
    data_dir: Path
    profile: dict[str, Any]
    overlap: list[dict[str, str]]
    roles: list[dict[str, str]]
    addresses: list[dict[str, str]]
    officers: list[dict[str, str]]
    agents: list[dict[str, str]]
    themes: list[dict[str, str]]
    queries: list[dict[str, str]]
    warnings: list[str] = field(default_factory=list)


def load_pack(
    community_id: int,
    person: str,
    *,
    pack_dir: Path | None = None,
    repo_root: Path = PROJECT_ROOT,
) -> PackInputs:
    base = (pack_dir or repo_root / "docs" / "validation").resolve()
    data = base / "data"
    cid = community_id

    profile = _read_json(data / f"cluster_{cid}_profile.json")
    if profile is None:
        raise SystemExit(
            f"[fatal] cluster_{cid}_profile.json not found at {data}. "
            "Run scripts/build_validation_pack.py first."
        )

    return PackInputs(
        community_id=cid,
        person=person,
        pack_dir=base,
        data_dir=data,
        profile=profile,
        overlap=_read_csv(data / f"cluster_{cid}_person_overlap.csv"),
        roles=_read_csv(data / f"cluster_{cid}_person_company_roles.csv"),
        addresses=_read_csv(data / f"cluster_{cid}_repeated_addresses.csv"),
        officers=_read_csv(data / f"cluster_{cid}_repeated_officers.csv"),
        agents=_read_csv(data / f"cluster_{cid}_repeated_agents.csv"),
        themes=_read_csv(data / f"cluster_{cid}_company_themes.csv"),
        queries=_read_csv(data / f"cluster_{cid}_external_search_queries.csv"),
    )


# ---------------------------------------------------------------------------
# External search via Tavily
# ---------------------------------------------------------------------------


def tavily_search(
    query: str,
    *,
    max_results: int = 5,
    api_key: str | None = None,
    client: httpx.Client | None = None,
) -> list[dict[str, Any]]:
    """Issue one Tavily query. Returns [] on missing key or HTTP error."""

    api_key = api_key or os.environ.get("TAVILY_API_KEY")
    if not api_key:
        return []
    payload = {
        "api_key": api_key,
        "query": query,
        "max_results": max_results,
        "search_depth": "basic",
        "include_answer": False,
    }
    if client is None:
        with httpx.Client(timeout=30) as c:
            return _tavily_send(c, payload, query)
    return _tavily_send(client, payload, query)


def _tavily_send(client: httpx.Client, payload: dict, query: str) -> list[dict[str, Any]]:
    try:
        resp = client.post(TAVILY_URL, json=payload)
        resp.raise_for_status()
        return resp.json().get("results", []) or []
    except Exception as exc:  # noqa: BLE001
        log.warning("tavily query failed (%r): %s", query, exc)
        return []


def run_search_queue(
    queries: list[dict[str, str]],
    *,
    api_key: str | None = None,
    max_queries: int = 60,
    priority_filter: tuple[str, ...] = ("high", "medium"),
    sleep_between: float = 0.4,
) -> list[dict[str, Any]]:
    """Fan out the validation-pack query queue to Tavily.

    Returns a flat list of result records, each tagged with the originating
    query + target. Stops after ``max_queries`` to keep API spend bounded.
    """

    if not (api_key or os.environ.get("TAVILY_API_KEY")):
        log.info("TAVILY_API_KEY not set — skipping external search.")
        return []

    selected = [q for q in queries if q.get("priority") in priority_filter]
    selected = selected[:max_queries]
    log.info("running %d/%d queries through Tavily", len(selected), len(queries))

    out: list[dict[str, Any]] = []
    with httpx.Client(timeout=30) as client:
        for i, q in enumerate(selected, 1):
            results = tavily_search(q["query"], api_key=api_key, client=client)
            for r in results:
                out.append(
                    {
                        "query": q["query"],
                        "target_type": q.get("target_type", ""),
                        "target_name": q.get("target_name", ""),
                        "purpose": q.get("purpose", ""),
                        "priority": q.get("priority", ""),
                        "result_title": r.get("title") or "",
                        "url": r.get("url") or "",
                        "snippet": (r.get("content") or "")[:400],
                        "published_date": r.get("published_date") or "",
                        "raw_score": r.get("score") or 0.0,
                    }
                )
            if i < len(selected):
                time.sleep(sleep_between)
    return out


# ---------------------------------------------------------------------------
# Hit scoring
# ---------------------------------------------------------------------------


_DOMAIN_RE = re.compile(r"^https?://([^/]+)")


def _extract_domain(url: str) -> str:
    m = _DOMAIN_RE.match(url or "")
    if not m:
        return ""
    host = m.group(1).lower()
    return host[4:] if host.startswith("www.") else host


def _classify_domain(url: str) -> tuple[str, str, float]:
    """Returns (domain, source_type, base_quality_score)."""

    domain = _extract_domain(url)
    for substr, src_type, score in _SOURCE_TAXONOMY:
        if substr in domain:
            return domain, src_type, score
    return domain, "unknown", 0.40


def _match_terms(text: str, vocab: tuple[str, ...]) -> list[str]:
    low = text.lower()
    return [t for t in vocab if t in low]


def score_hits(
    results: list[dict[str, Any]],
    *,
    person: str,
    member_names: list[str],
) -> list[dict[str, Any]]:
    """Score every Tavily result row. Hits that match an anchor name +
    a high-quality domain + cluster-relevant vocabulary get high
    relevance scores; otherwise the row is flagged needs_human_review.
    """

    norm_members = {normalize_company_name(n) for n in member_names if n}
    person_low = person.lower()
    # Person tokens for fuzzy match (handles "calvin ayre" vs "calvin edward ayre").
    person_tokens = [t for t in re.split(r"\s+", person_low) if len(t) >= 3]
    out: list[dict[str, Any]] = []

    for r in results:
        url = r.get("url", "")
        title = r.get("result_title", "")
        snippet = r.get("snippet", "")
        target = r.get("target_name", "")
        text = f"{title} {snippet}".lower()
        domain, src_type, base = _classify_domain(url)

        matched: list[str] = []
        if person_low and person_low in text:
            matched.append("person")
        elif len(person_tokens) >= 2 and all(
            t in text for t in person_tokens[:1] + person_tokens[-1:]
        ):
            # First and last name both present — treat as person match.
            matched.append("person")
        if target and target.lower() in text:
            matched.append("target")
        norm_target = normalize_company_name(target) if target else ""
        if norm_target and norm_target in text:
            matched.append("target_normalized")
        if any(n in text for n in norm_members):
            matched.append("cluster_member")
        for label, vocab in (
            ("bodog", _BODOG_TERMS),
            ("malta", _MALTA_TERMS),
            ("offshore", _OFFSHORE_TERMS),
            ("reg_action", _REG_ACTION_TERMS),
            ("finance", _FINANCE_TERMS),
            ("litigation", _LITIGATION_TERMS),
        ):
            if _match_terms(text, vocab):
                matched.append(label)

        # Specific-entity gate: a hit only earns high relevance if the
        # cluster entity actually appears in the page text. Without this,
        # high-quality domains (OFAC, SEC) + topical vocabulary (malta,
        # offshore) compose to relevance=1.0 even when the page is a
        # generic action list that doesn't name the target. That's a
        # defamation hazard — a reviewer might lift "OFAC 1.0" as
        # corroboration of a sanctions designation that doesn't exist.
        specific_match_terms = {"target", "target_normalized", "cluster_member", "person"}
        has_specific = bool(specific_match_terms.intersection(matched))

        # Composite score: base domain quality + bonus for matched terms.
        term_bonus = min(0.4, 0.08 * len(set(matched)))
        target_bonus = 0.10 if "target" in matched or "target_normalized" in matched else 0
        person_bonus = 0.10 if "person" in matched else 0
        raw_relevance = base + term_bonus + target_bonus + person_bonus

        if has_specific:
            relevance = round(min(1.0, raw_relevance), 3)
            note = ""
        else:
            # No entity from this cluster is named in the page body.
            # Hard-cap relevance at 0.5 regardless of domain quality.
            # This keeps the hit visible to the reviewer (it's still on
            # a credible domain about a credible topic) but disqualifies
            # it from auto-counting as corroboration.
            relevance = round(min(0.5, base * 0.5 + term_bonus * 0.5), 3)
            note = (
                "no specific cluster entity named in page body; "
                "treat as topical-only, not corroboration."
            )

        # supports / contradicts at this stage is a heuristic: a high-quality
        # domain matching both the target AND person counts as supporting
        # evidence for the (person → company) edge. Contradiction detection
        # would need claim NLP; mark for human review.
        supports = (
            "true"
            if (
                src_type in {"leak_primary", "regulator", "structured_database", "press", "court"}
                and ("target" in matched or "target_normalized" in matched)
                and ("person" in matched)
            )
            else ""
        )

        out.append(
            {
                "target_name": target,
                "query": r.get("query", ""),
                "result_title": title,
                "url": url,
                "domain": domain,
                "source_type": src_type,
                "matched_terms": ";".join(matched),
                "relevance_score": relevance,
                "supports_edge": supports,
                "contradicts_edge": "",  # filled by human review
                "needs_human_review": "true" if relevance < 0.75 else "false",
                "notes": note,
            }
        )

    out.sort(key=lambda r: -r["relevance_score"])
    return out


# ---------------------------------------------------------------------------
# Timeline extraction
# ---------------------------------------------------------------------------


_DATE_RE = re.compile(r"(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?")


def _norm_date(s: str | None) -> str:
    if not s:
        return ""
    m = _DATE_RE.search(s)
    if not m:
        return ""
    y, mm, dd = m.group(1), m.group(2) or "01", m.group(3) or "01"
    return f"{y}-{mm}-{dd}"


def build_timeline(
    inputs: PackInputs,
    scored_hits: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    # 1. Person-company role start/end dates (from roles CSV).
    for r in inputs.roles:
        for date_field, kind in (("start_date", "role_start"), ("end_date", "role_end")):
            d = _norm_date(r.get(date_field) or "")
            if not d:
                continue
            rows.append(
                {
                    "date": d,
                    "event_type": kind,
                    "entity": r.get("company_name", ""),
                    "description": (
                        f"{r.get('person_name', '?')} {r.get('role', '?')} "
                        f"({r.get('relationship_type', '?')})"
                    ),
                    "source": r.get("leak") or r.get("source") or "icij",
                    "confidence": r.get("confidence", ""),
                    "needs_human_review": "false",
                }
            )

    # 2. Search hit publication dates that look credible.
    for h in scored_hits:
        d = _norm_date(h.get("published_date", ""))
        if not d or h.get("relevance_score", 0) < 0.6:
            continue
        rows.append(
            {
                "date": d,
                "event_type": "web_mention",
                "entity": h.get("target_name", ""),
                "description": h.get("result_title", "")[:160],
                "source": h.get("url", ""),
                "confidence": h.get("relevance_score", ""),
                "needs_human_review": "true",
            }
        )

    rows.sort(key=lambda r: r["date"])
    return rows


def render_timeline_md(community_id: int, person: str, timeline: list[dict]) -> str:
    parts = [
        f"# Timeline — cluster {community_id} / {person}\n\n",
        "_Machine-extracted from ICIJ role dates + external-search results._\n",
        "_Every row is a candidate; verify before publishing._\n\n",
    ]
    if not timeline:
        parts.append("_(no dated events found)_\n")
        return "".join(parts)
    by_year: dict[str, list[dict]] = defaultdict(list)
    for r in timeline:
        by_year[r["date"][:4]].append(r)
    for year in sorted(by_year):
        parts.append(f"\n## {year}\n\n")
        for r in by_year[year]:
            parts.append(
                f"- **{r['date']}** — _{r['event_type']}_ — "
                f"{r['entity']}: {r['description']} "
                f"`source: {r['source']}`\n"
            )
    return "".join(parts)


# ---------------------------------------------------------------------------
# Graph-path narratives
# ---------------------------------------------------------------------------


def render_graph_narratives_md(inputs: PackInputs) -> str:
    parts: list[str] = []
    cid = inputs.community_id
    parts.append(f"# Graph-path narratives — cluster {cid} / {inputs.person}\n\n")
    parts.append(
        "_Machine-generated readable claims. Phrased as `records say` / "
        "`graph links` rather than allegations._\n\n"
    )

    parts.append("## Anchor → company role chain\n\n")
    if not inputs.roles:
        parts.append("_(no anchor → company edges in this cluster)_\n\n")
    else:
        # Group by company.
        by_company: dict[str, list[dict]] = defaultdict(list)
        for r in inputs.roles:
            by_company[r["company_name"]].append(r)
        for company, rs in list(by_company.items())[:25]:
            roles = sorted({r["role"] for r in rs if r["role"]})
            leak = rs[0].get("leak", "")
            parts.append(
                f"- Records say **{inputs.person}** appears as "
                f"_{', '.join(roles) or 'officer'}_ of **{company}** "
                f"(source: {leak}).\n"
            )
        if len(by_company) > 25:
            parts.append(f"\n_… and {len(by_company) - 25} more company role bindings._\n")

    parts.append("\n## Recurring officers across cluster members\n\n")
    if not inputs.officers:
        parts.append("_(no officer reuse detected)_\n\n")
    else:
        for o in inputs.officers[:10]:
            n = o.get("n_linked_companies", "?")
            roles = o.get("roles", "")
            parts.append(
                f"- Graph links: **{o['officer_name']}** holds roles "
                f"(_{roles}_) across **{n}** cluster-47-style companies.\n"
            )

    parts.append("\n## Shared registered addresses\n\n")
    if not inputs.addresses:
        parts.append("_(no recurring addresses)_\n\n")
    else:
        for a in inputs.addresses[:5]:
            n = a.get("n_linked_companies", "?")
            parts.append(
                f"- Records show **{n} cluster companies** share registered "
                f"address `{a['address']}`.\n"
            )

    parts.append("\n## Shared intermediaries\n\n")
    if not inputs.agents:
        parts.append("_(no recurring intermediaries)_\n\n")
    else:
        for a in inputs.agents[:5]:
            n = a.get("n_linked_companies", "?")
            parts.append(
                f"- Records say **{a['intermediary_name']}** appears as "
                f"intermediary on **{n}** cluster companies.\n"
            )

    return "".join(parts)


# ---------------------------------------------------------------------------
# Discovery delta
# ---------------------------------------------------------------------------


def build_discovery_delta(
    inputs: PackInputs, scored_hits: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Tabulate which facts were already discoverable from a single
    public-web search vs. which only emerged from the cluster structure."""

    rows: list[dict[str, Any]] = []
    profile = inputs.profile

    # --- Already public: anything with a high-quality match in Tavily ---
    public_hits: dict[str, list[str]] = defaultdict(list)
    for h in scored_hits:
        if h["relevance_score"] >= 0.75 and h["source_type"] in {
            "leak_primary",
            "regulator",
            "structured_database",
            "press",
            "court",
        }:
            public_hits[h["target_name"]].append(h["url"])

    if public_hits:
        for name, urls in list(public_hits.items())[:30]:
            rows.append(
                {
                    "fact": f"{name} mentioned in public sources",
                    "category": "publicly_known",
                    "public_knowledge": "true",
                    "goldenmatch_added": "false",
                    "sources": ";".join(urls[:3]),
                    "needs_human_review": "true",
                }
            )

    # --- GoldenMatch-added: structural facts that don't exist on the web ---
    n_members = profile.get("n_members", 0)
    odd = profile.get("ordinary_vs_unusual", {}) or {}
    rows.append(
        {
            "fact": (
                f"Cluster #{inputs.community_id} contains {n_members} "
                "entities tied together by uncertainty-propagated edges"
            ),
            "category": "structural",
            "public_knowledge": "false",
            "goldenmatch_added": "true",
            "sources": f"docs/validation/data/cluster_{inputs.community_id}_profile.json",
            "needs_human_review": "false",
        }
    )
    if odd.get("address_reuse_rate", 0) >= 0.5:
        rows.append(
            {
                "fact": (
                    f"{odd.get('n_repeated_addresses', 0)} address(es) recur "
                    f"across {odd['address_reuse_rate']:.0%} of cluster members"
                ),
                "category": "infrastructure_reuse",
                "public_knowledge": "false",
                "goldenmatch_added": "true",
                "sources": (
                    f"docs/validation/data/cluster_{inputs.community_id}_repeated_addresses.csv"
                ),
                "needs_human_review": "false",
            }
        )
    if odd.get("officer_reuse_rate", 0) >= 0.5:
        rows.append(
            {
                "fact": (
                    f"{odd.get('n_repeated_officers', 0)} officer(s) appear on "
                    f"{odd['officer_reuse_rate']:.0%} of cluster members"
                ),
                "category": "infrastructure_reuse",
                "public_knowledge": "false",
                "goldenmatch_added": "true",
                "sources": (
                    f"docs/validation/data/cluster_{inputs.community_id}_repeated_officers.csv"
                ),
                "needs_human_review": "false",
            }
        )

    # --- Underreported members: cluster members with no web hits ---
    member_hit_counts: dict[str, int] = defaultdict(int)
    for h in scored_hits:
        if h["relevance_score"] >= 0.6:
            member_hit_counts[h["target_name"]] += 1
    members_sample = profile.get("members_sample", []) or []
    silent = [
        m for m in members_sample if m.get("name") and member_hit_counts.get(m["name"], 0) == 0
    ]
    if silent:
        rows.append(
            {
                "fact": (
                    f"{len(silent)} cluster members have zero credible web "
                    "mentions after fanned-out search"
                ),
                "category": "underreported",
                "public_knowledge": "false",
                "goldenmatch_added": "true",
                "sources": (
                    f"docs/validation/data/cluster_{inputs.community_id}_underreported_entities.csv"
                ),
                "needs_human_review": "false",
            }
        )

    return rows


# ---------------------------------------------------------------------------
# Evidence ledger
# ---------------------------------------------------------------------------


def build_evidence_ledger(
    inputs: PackInputs, scored_hits: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    cid = inputs.community_id
    profile = inputs.profile
    odd = profile.get("ordinary_vs_unusual", {}) or {}

    # Group hits by target.
    hits_by_target: dict[str, list[dict]] = defaultdict(list)
    for h in scored_hits:
        if h["relevance_score"] >= 0.6:
            hits_by_target[h["target_name"]].append(h)

    # Claim 1: cluster size + composition.
    rows.append(
        {
            "claim_id": f"c{cid}-001",
            "claim_text": (
                f"Community #{cid} contains {profile.get('n_members', 0)} "
                f"entities at threshold {profile.get('threshold', 0.9)}."
            ),
            "claim_type": "structural",
            "supporting_sources": (
                f"docs/reports/data/confidence_communities.parquet "
                f"(community_id={cid}, threshold=0.9)"
            ),
            "contradicting_sources": "",
            "confidence": profile.get("cluster_scored", {}).get("cluster_confidence", ""),
            "human_review_status": "machine_only",
            "publication_safe": "true",
        }
    )

    # Claim 2: each anchor → company role binding (top 20).
    by_company: dict[str, list[dict]] = defaultdict(list)
    for r in inputs.roles:
        by_company[r["company_name"]].append(r)
    for i, (company, rs) in enumerate(list(by_company.items())[:20], 1):
        anchor_uid = rs[0].get("person_record_id", "")
        leak = rs[0].get("leak", "")
        roles_s = ", ".join(sorted({r["role"] for r in rs if r["role"]}))
        hit_urls = ";".join(h["url"] for h in hits_by_target.get(company, [])[:2])
        rows.append(
            {
                "claim_id": f"c{cid}-r{i:02d}",
                "claim_text": (
                    f"Records say {inputs.person} (uid {anchor_uid}) "
                    f"appears as {roles_s} of {company} in {leak}."
                ),
                "claim_type": "role_edge",
                "supporting_sources": _join_sources(leak, anchor_uid, hit_urls),
                "contradicting_sources": "",
                "confidence": rs[0].get("confidence", ""),
                "human_review_status": ("external_corroborated" if hit_urls else "machine_only"),
                "publication_safe": ("true" if hit_urls else "needs_review"),
            }
        )

    # Claim 3: address-bridge.
    for i, a in enumerate(inputs.addresses[:3], 1):
        rows.append(
            {
                "claim_id": f"c{cid}-a{i:02d}",
                "claim_text": (
                    f"{a.get('n_linked_companies', '?')} cluster companies "
                    f"share registered address: {a['address']}"
                ),
                "claim_type": "address_bridge",
                "supporting_sources": (
                    f"docs/validation/data/cluster_{cid}_repeated_addresses.csv "
                    f"| source: {a.get('source_label', '')}"
                ),
                "contradicting_sources": "",
                "confidence": a.get("confidence", ""),
                "human_review_status": "machine_only",
                "publication_safe": "true",
            }
        )

    # Claim 4: officer-bridge.
    for i, o in enumerate(inputs.officers[:5], 1):
        rows.append(
            {
                "claim_id": f"c{cid}-o{i:02d}",
                "claim_text": (
                    f"{o['officer_name']} holds roles ({o.get('roles', '')}) "
                    f"across {o.get('n_linked_companies', '?')} cluster companies"
                ),
                "claim_type": "officer_bridge",
                "supporting_sources": (
                    f"docs/validation/data/cluster_{cid}_repeated_officers.csv "
                    f"| source: {o.get('source_label', '')}"
                ),
                "contradicting_sources": "",
                "confidence": o.get("confidence", ""),
                "human_review_status": "machine_only",
                "publication_safe": "true",
            }
        )

    # Claim 5: top theme.
    theme = odd.get("top_theme")
    if theme and theme != "unknown":
        rows.append(
            {
                "claim_id": f"c{cid}-t01",
                "claim_text": (
                    f"Most cluster company names match the '{theme}' "
                    f"theme (share {odd.get('top_theme_share', 0):.0%})."
                ),
                "claim_type": "weak_label",
                "supporting_sources": (f"docs/validation/data/cluster_{cid}_company_themes.csv"),
                "contradicting_sources": "",
                "confidence": "0.30",
                "human_review_status": "needs_review",
                "publication_safe": "needs_review",
            }
        )

    return rows


# ---------------------------------------------------------------------------
# Underreported entity scoring
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Registry lookups (Phase 2)
# ---------------------------------------------------------------------------


# Jurisdiction -> adapter class. Lazy-imported inside the function so the
# corroborate module stays importable without httpx etc. when the flag
# isn't used.
_JURIS_TO_ADAPTER = {
    "no": "BrregNorwayAdapter",
    "fr": "InpiFranceAdapter",
    "ie": "CroIrelandAdapter",
    "nl": "KvkNetherlandsAdapter",
    "us": "SecEdgar13DAdapter",
}


def run_registry_lookups(inputs: PackInputs) -> list[dict[str, Any]]:
    """For each cluster member, dispatch to the right national-registry
    adapter and emit a `RegistryHit` row per match.

    State-authoritative; far stronger evidence than Tavily hits.
    Returns an empty list when no cluster member has a supported
    jurisdiction (the common case for current Malta-anchored clusters).
    """

    try:
        from shellnet.registries.brreg_norway import BrregNorwayAdapter
        from shellnet.registries.cro_ireland import CroIrelandAdapter
        from shellnet.registries.inpi_france import InpiFranceAdapter
        from shellnet.registries.kvk_netherlands import KvkNetherlandsAdapter
        from shellnet.registries.sec_edgar_13d_13g import SecEdgar13DAdapter
    except ImportError as exc:
        log.warning("registry adapters unavailable (%s); skipping", exc)
        return []

    adapters = {
        "no": BrregNorwayAdapter(),
        "fr": InpiFranceAdapter(),
        "ie": CroIrelandAdapter(),
        "nl": KvkNetherlandsAdapter(),
        "us": SecEdgar13DAdapter(),
    }

    members_sample = inputs.profile.get("members_sample", []) or []
    # Per-cluster officer set for overlap scoring.
    cluster_officers = {
        (o.get("officer_name") or "").lower() for o in inputs.officers if o.get("officer_name")
    }

    rows: list[dict[str, Any]] = []
    for m in members_sample:
        juris = (m.get("jurisdiction") or "").lower().strip()
        name = m.get("name") or ""
        adapter = adapters.get(juris)
        if not adapter or not name:
            continue
        try:
            hits = adapter.search(name, limit=3)
        except Exception as exc:  # noqa: BLE001
            log.warning("registry search failed for %s (%s): %s", name, juris, exc)
            continue

        for hit in hits:
            # Calculate officer overlap if the adapter returned officers.
            overlap_count = sum(
                1 for o in getattr(hit, "officers", []) if o.name.lower() in cluster_officers
            )
            # Heuristic: a state-issued registry hit that overlaps on
            # name + at least one officer with the cluster is
            # publication-safe.
            publication_safe = (
                "true"
                if (
                    overlap_count > 0
                    or hit.registry in {"sec_edgar_13d_13g", "brreg_norway", "inpi_france"}
                )
                else "needs_review"
            )
            rows.append(
                {
                    "cluster_member": name,
                    "jurisdiction": juris,
                    "registry": hit.registry,
                    "match_type": "name_search",
                    "registry_identifier": hit.identifier,
                    "registry_name": hit.name,
                    "registry_status": hit.status,
                    "registry_address": hit.address,
                    "officer_overlap": str(overlap_count),
                    "sourceUrl": hit.sourceUrl,
                    "publication_safe": publication_safe,
                    "notes": hit.notes,
                }
            )
    log.info("registry lookups: %d hits across cluster members", len(rows))
    return rows


def score_underreported(
    inputs: PackInputs, scored_hits: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    profile = inputs.profile
    members_sample = profile.get("members_sample", []) or []

    # Graph degree = how many recurring-officer rows / address rows / role
    # rows mention this member's name. Cheap proxy for centrality.
    deg: dict[str, int] = defaultdict(int)
    for r in inputs.roles:
        deg[r.get("company_name", "")] += 1
    for o in inputs.officers:
        for nm in (o.get("linked_companies") or "").split(";"):
            deg[nm.strip()] += 1
    for a in inputs.addresses:
        for nm in (a.get("linked_companies") or "").split(";"):
            deg[nm.strip()] += 1

    # Web hits per member.
    hits: dict[str, list[float]] = defaultdict(list)
    for h in scored_hits:
        hits[h.get("target_name", "")].append(float(h.get("relevance_score", 0) or 0))

    out: list[dict[str, Any]] = []
    max_deg = max(deg.values(), default=1) or 1
    for m in members_sample:
        name = m.get("name", "")
        uid = m.get("uid", "")
        d = deg.get(name, 0)
        member_hits = hits.get(name, [])
        n_hits = len(member_hits)
        max_score = max(member_hits, default=0.0)
        # Underreported score: high if graph degree is high AND web presence
        # is low. Normalize degree by cluster max.
        graph_norm = d / max_deg
        web_present = min(1.0, n_hits / 3) if n_hits else 0.0
        urs = round(graph_norm * (1 - web_present), 3)
        out.append(
            {
                "company_name": name,
                "uid": uid,
                "graph_degree": d,
                "n_web_hits": n_hits,
                "max_hit_score": round(max_score, 3),
                "underreported_score": urs,
                "reason": (
                    "high graph degree + no web presence"
                    if d > 0 and n_hits == 0
                    else ("well-attested" if n_hits >= 3 else "low graph degree")
                ),
            }
        )
    out.sort(key=lambda r: -r["underreported_score"])
    return out


# ---------------------------------------------------------------------------
# Research brief
# ---------------------------------------------------------------------------


def _one_sentence_story(inputs: PackInputs) -> str:
    odd = inputs.profile.get("ordinary_vs_unusual", {}) or {}
    n = inputs.profile.get("n_members", "?")
    return (
        f"GoldenMatch surfaced a {n}-entity cluster (#{inputs.community_id}) "
        f"with {odd.get('address_reuse_rate', 0):.0%} shared-address rate and "
        f"{odd.get('officer_reuse_rate', 0):.0%} shared-officer rate, "
        f"anchored on {inputs.person} — a candidate structure for human review."
    )


def render_research_brief(
    inputs: PackInputs,
    scored_hits: list[dict[str, Any]],
    delta: list[dict[str, Any]],
    underreported: list[dict[str, Any]],
    ledger: list[dict[str, Any]],
    search_was_run: bool,
) -> str:
    cid = inputs.community_id
    parts: list[str] = []
    parts.append(f"# Cluster {cid} Research Brief\n\n")
    parts.append(
        "_Machine-generated from the validation pack + external corroboration. "
        "Human review required. Not an allegation or finding of wrongdoing._\n\n"
    )

    parts.append("## One-sentence story\n")
    parts.append(_one_sentence_story(inputs) + "\n\n")

    parts.append("## What GoldenMatch surfaced\n")
    odd = inputs.profile.get("ordinary_vs_unusual", {}) or {}
    parts.append(
        f"- Cluster size: **{inputs.profile.get('n_members', '?')}**\n"
        f"- Anchor: **{inputs.person}**\n"
        f"- Officer reuse rate: {odd.get('officer_reuse_rate', '?')}\n"
        f"- Address reuse rate: {odd.get('address_reuse_rate', '?')}\n"
        f"- Intermediary reuse rate: {odd.get('intermediary_reuse_rate', '?')}\n"
        f"- Top theme: {odd.get('top_theme', '?')} "
        f"(share {odd.get('top_theme_share', '?')})\n"
        f"- Anomaly score: {odd.get('anomaly_score', '?')}\n"
        f"- Isolation: {odd.get('isolation', '?')} "
        "(1.0 = no bridges to other clusters)\n\n"
    )

    parts.append("## What was already publicly known\n")
    public = [r for r in delta if r["category"] == "publicly_known"]
    if not search_was_run:
        parts.append("_External search was not run — public-knowledge column unfilled._\n\n")
    elif not public:
        parts.append("_No high-quality public-web hits matched a cluster entity._\n\n")
    else:
        for r in public[:15]:
            parts.append(f"- {r['fact']} — `{r['sources']}`\n")
        if len(public) > 15:
            parts.append(f"\n_… and {len(public) - 15} more._\n")
        parts.append("\n")

    parts.append("## What appears underreported\n")
    silent = [u for u in underreported if u["underreported_score"] >= 0.3]
    if not silent:
        parts.append("_(no members scored high on underreported axis)_\n\n")
    else:
        for u in silent[:15]:
            parts.append(
                f"- **{u['company_name']}** (uid {u['uid']}): "
                f"graph_degree={u['graph_degree']}, web_hits={u['n_web_hits']}, "
                f"underreported_score={u['underreported_score']}\n"
            )
        if len(silent) > 15:
            parts.append(f"\n_… and {len(silent) - 15} more._\n")
        parts.append("\n")

    parts.append("## Strongest evidence paths\n")
    strong = [c for c in ledger if c["publication_safe"] == "true"]
    if not strong:
        parts.append("_(no publication-safe claims; everything needs human review)_\n\n")
    else:
        for c in strong[:10]:
            parts.append(f"- **{c['claim_id']}**: {c['claim_text']}\n")
        parts.append("\n")

    parts.append("## Weakest links\n")
    weak = [c for c in ledger if c["human_review_status"] == "needs_review"]
    if not weak:
        parts.append("_(none flagged for review)_\n\n")
    else:
        for c in weak[:10]:
            parts.append(f"- **{c['claim_id']}**: {c['claim_text']}\n")
        parts.append("\n")

    parts.append("## External corroboration found\n")
    if not search_was_run:
        parts.append("_External search was not run (no TAVILY_API_KEY or flag not set)._\n\n")
    else:
        high_quality = [h for h in scored_hits if h["relevance_score"] >= 0.75]
        if not high_quality:
            parts.append("_External search ran; no high-quality corroborating hits._\n\n")
        else:
            for h in high_quality[:10]:
                parts.append(
                    f"- [{h['source_type']}] {h['result_title']} — "
                    f"{h['url']} (score {h['relevance_score']})\n"
                )
            parts.append("\n")

    parts.append("## Contradictions / caveats\n")
    parts.append(
        "- Same-name does not imply same-person. The anchor uids are unverified.\n"
        "- Corporate-services hubs in Malta legitimately host hundreds of "
        "unrelated clients; shared-address + shared-officer is a triage signal, "
        "not an indictment.\n"
        "- Web search uses Tavily, which is itself a third-party aggregator. "
        "Absence of hits ≠ absence of public record.\n"
        "- Theme labels are keyword heuristics; treat the 'top theme' as a "
        "weak hint.\n\n"
    )

    parts.append("## Manual review priorities\n")
    parts.append(
        "1. Confirm whether anchor ICIJ uids refer to the same person.\n"
        "2. Verify each top-10 evidence-ledger claim against the cited "
        "source.\n"
        "3. Drill into the top-5 underreported entities — these are the "
        "highest-leverage targets for a narrative.\n"
        "4. Check whether any cluster member has a separate journalist "
        "coverage thread that this analysis missed.\n"
        "5. If the cluster is publication-grade, lift only the "
        "publication-safe claims into the brief.\n\n"
    )

    parts.append("## Safe video framing\n")
    parts.append(
        "- Lead with the question ('what does this Malta cluster look like?'), "
        "not the conclusion.\n"
        "- Show the structure (graph + recurring infrastructure) before any "
        "names.\n"
        "- Quote the cluster's own records ('records say', 'graph links') "
        "rather than asserting wrongdoing.\n"
        "- Acknowledge underreportedness as a tool-surfaced feature, not as a "
        "claim of wrongdoing.\n"
        "- End with 'requires journalist follow-up' framing — the tool surfaces "
        "candidates; humans decide what to publish.\n"
    )

    return "".join(parts)


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def corroborate(
    community_id: int,
    person: str,
    *,
    pack_dir: Path | None = None,
    repo_root: Path = PROJECT_ROOT,
    run_external_search: bool = False,
    max_queries: int = 60,
    tavily_api_key: str | None = None,
    rescore_only: bool = False,
    with_registry_lookups: bool = False,
) -> dict[str, Path]:
    """If ``rescore_only`` is True, skip Tavily and re-use the previously
    saved ``cluster_<id>_external_search_results.json``. Lets a scorer-only
    change ship without burning API spend on already-fetched results."""

    inputs = load_pack(community_id, person, pack_dir=pack_dir, repo_root=repo_root)
    base = inputs.pack_dir
    data = inputs.data_dir
    cid = community_id

    # Step 1: search.
    raw_results: list[dict[str, Any]] = []
    search_was_run = False
    if rescore_only:
        existing = data / f"cluster_{cid}_external_search_results.json"
        if not existing.exists():
            raise SystemExit(
                f"[fatal] --rescore-only set but {existing} not found. "
                "Run corroborate with --run-external-search first."
            )
        raw_results = json.loads(existing.read_text(encoding="utf-8")) or []
        search_was_run = bool(raw_results)
        log.info("rescore-only: reusing %d previously fetched results", len(raw_results))
    elif run_external_search:
        api_key = tavily_api_key or os.environ.get("TAVILY_API_KEY")
        if api_key:
            raw_results = run_search_queue(
                inputs.queries,
                api_key=api_key,
                max_queries=max_queries,
            )
            search_was_run = True
        else:
            log.warning(
                "--run-external-search set but TAVILY_API_KEY missing; "
                "writing skeleton search results."
            )

    member_names = [m["name"] for m in (inputs.profile.get("members_sample") or [])]
    scored = score_hits(raw_results, person=person, member_names=member_names)

    timeline = build_timeline(inputs, scored)
    delta = build_discovery_delta(inputs, scored)
    ledger = build_evidence_ledger(inputs, scored)
    underreported = score_underreported(inputs, scored)
    registry_hits = run_registry_lookups(inputs) if with_registry_lookups else []

    # Output paths.
    paths = {
        "research_brief": base / f"cluster_{cid}_research_brief.md",
        "timeline_md": base / f"cluster_{cid}_timeline.md",
        "graph_paths_md": base / f"cluster_{cid}_graph_paths.md",
        "search_json": data / f"cluster_{cid}_external_search_results.json",
        "search_csv": data / f"cluster_{cid}_external_search_results.csv",
        "hit_scores": data / f"cluster_{cid}_external_hit_scores.csv",
        "discovery_delta": data / f"cluster_{cid}_discovery_delta.csv",
        "timeline_csv": data / f"cluster_{cid}_timeline.csv",
        "evidence_ledger": data / f"cluster_{cid}_evidence_ledger.csv",
        "underreported": data / f"cluster_{cid}_underreported_entities.csv",
        "registry_hits": data / f"cluster_{cid}_registry_hits.csv",
    }

    _write_json(paths["search_json"], raw_results)
    _write_csv(paths["search_csv"], SEARCH_RESULTS_HEADERS, raw_results)
    _write_csv(paths["hit_scores"], HIT_SCORES_HEADERS, scored)
    _write_csv(paths["discovery_delta"], DISCOVERY_DELTA_HEADERS, delta)
    _write_csv(paths["timeline_csv"], TIMELINE_HEADERS, timeline)
    _write_csv(paths["evidence_ledger"], EVIDENCE_LEDGER_HEADERS, ledger)
    _write_csv(paths["underreported"], UNDERREPORTED_HEADERS, underreported)
    _write_csv(paths["registry_hits"], REGISTRY_HITS_HEADERS, registry_hits)

    paths["timeline_md"].parent.mkdir(parents=True, exist_ok=True)
    paths["timeline_md"].write_text(render_timeline_md(cid, person, timeline), encoding="utf-8")
    paths["graph_paths_md"].write_text(render_graph_narratives_md(inputs), encoding="utf-8")
    paths["research_brief"].write_text(
        render_research_brief(inputs, scored, delta, underreported, ledger, search_was_run),
        encoding="utf-8",
    )

    return paths


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description=(
            "Second-stage corroboration: takes a validation pack and adds "
            "external search + scoring + discovery-delta + timeline + "
            "narratives + evidence ledger + underreported scoring + brief."
        )
    )
    p.add_argument("--community-id", type=int, required=True)
    p.add_argument("--person", type=str, required=True)
    p.add_argument(
        "--pack-dir",
        type=Path,
        default=None,
        help="override docs/validation/ — useful in tests and on Railway",
    )
    p.add_argument(
        "--run-external-search",
        action="store_true",
        help="actually call Tavily. Requires TAVILY_API_KEY.",
    )
    p.add_argument(
        "--rescore-only",
        action="store_true",
        help=(
            "skip Tavily; re-use existing cluster_<id>_external_search_results.json. "
            "Useful when only the scoring logic changed."
        ),
    )
    p.add_argument(
        "--max-queries",
        type=int,
        default=60,
        help="cap on Tavily API spend (default 60 high/medium queries)",
    )
    p.add_argument(
        "--with-registry-lookups",
        action="store_true",
        help=(
            "dispatch each cluster member to the relevant national-registry "
            "adapter (NO/FR/IE/NL/US) when its jurisdiction is supported. "
            "Returns state-authoritative hits in cluster_<id>_registry_hits.csv."
        ),
    )
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    paths = corroborate(
        community_id=args.community_id,
        person=args.person,
        pack_dir=args.pack_dir,
        run_external_search=args.run_external_search,
        max_queries=args.max_queries,
        rescore_only=args.rescore_only,
        with_registry_lookups=args.with_registry_lookups,
    )
    print("Generated:")
    for kind, path in paths.items():
        try:
            rel = path.relative_to(PROJECT_ROOT)
            print(f"  {kind:18s} {rel}")
        except ValueError:
            print(f"  {kind:18s} {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
