"""Export a validation pack to FollowTheMoney entities.

Reads the artefacts produced by ``scripts/build_validation_pack.py``
(and, when present, ``scripts/corroborate_validation_pack.py``) and
emits a single ndjson stream of FollowTheMoney entities — the canonical
data model used by ICIJ Datashare, OpenAleph, OpenSanctions, and other
investigative-journalism tooling.

Reads (from ``docs/validation/`` by default)::

    cluster_<id>_profile.json
    cluster_<id>_person_overlap.csv
    cluster_<id>_person_company_roles.csv
    cluster_<id>_repeated_addresses.csv
    cluster_<id>_repeated_officers.csv
    cluster_<id>_repeated_agents.csv

Writes::

    docs/validation/data/cluster_<id>_ftm.json   (ndjson, one entity per line)

The same file can be ``ftm dump-aleph`` / ``alephclient crawldir`` / loaded
into ftm-store. Every entity carries publisher provenance pointing at the
GoldenMatch pipeline + this repo, and a ``sourceUrl`` pointing at the
ICIJ Offshore Leaks page when the entity has an ICIJ uid.

Usage::

    uv run python scripts/export_validation_pack_ftm.py \\
        --community-id 37 \\
        --person "calvin edward ayre"
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve()
_REPO_ROOT = _HERE.parents[1]
sys.path.insert(0, str(_REPO_ROOT / "src"))

from shellnet.normalize import normalize_company_name  # noqa: E402

# NOTE: we emit FollowTheMoney ndjson directly rather than importing the
# ``followthemoney`` library. The library transitively requires PyICU
# which needs the ICU C++ libs at build time (painful on Windows). The
# FTM JSON format is well-specified and stable, and our consumers
# (OpenAleph, ftm-store, alephclient) all validate against the schema on
# ingest, so emitting raw dicts that match the schema is equivalent for
# our purposes.
#
# Schema reference: https://followthemoney.tech/explorer/
# JSON shape: {"id": str, "schema": str, "properties": {prop: [values]}}

log = logging.getLogger("export_validation_pack_ftm")

PROJECT_ROOT = _REPO_ROOT
PUBLISHER = "GoldenMatch shell-company-network discovery pipeline"
PUBLISHER_URL = "https://github.com/benseverndev-oss/goldenmatch-shell-company-network"


# ---------------------------------------------------------------------------
# Identifier conventions
# ---------------------------------------------------------------------------
#
# Every FTM entity needs a stable ID. We prefix with the cluster so the same
# legal entity surfacing in two different validation packs gets two distinct
# FTM rows — keeps clusters reproducibly separable in downstream tools. We
# still set `sameAs` cross-references where the underlying ICIJ uid is the
# same, so Aleph's resolver can merge them later.


def _eid_person(cid: int, uid: str) -> str:
    return f"gm-c{cid}-p-{_slug(uid)}"


def _eid_company(cid: int, uid_or_name: str) -> str:
    return f"gm-c{cid}-co-{_slug(uid_or_name)}"


def _eid_address(cid: int, addr: str) -> str:
    return f"gm-c{cid}-addr-{_slug(addr)}"


def _eid_directorship(cid: int, person_uid: str, company_uid: str, role: str) -> str:
    return f"gm-c{cid}-dir-{_slug(person_uid)}-{_slug(company_uid)}-{_slug(role)}"


def _eid_ownership(cid: int, owner_uid: str, asset_uid: str) -> str:
    return f"gm-c{cid}-own-{_slug(owner_uid)}-{_slug(asset_uid)}"


_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slug(s: str) -> str:
    if not s:
        return "x"
    out = _SLUG_RE.sub("-", s.lower()).strip("-")
    return out[:80] or "x"


def _icij_source_url(uid: str | None) -> str:
    if not uid or not uid.startswith("icij:"):
        return ""
    return f"https://offshoreleaks.icij.org/nodes/{uid.split(':', 1)[1]}"


# ---------------------------------------------------------------------------
# Loader
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


# ---------------------------------------------------------------------------
# Entity construction
# ---------------------------------------------------------------------------


# Known FTM schemas + the properties we actually use. Keeping this whitelist
# lets us reject typos at construction time without importing the lib.
_FTM_SCHEMAS = {
    "Person",
    "LegalEntity",
    "Company",
    "Address",
    "Directorship",
    "Ownership",
    "Membership",
}


class _Entity:
    """Minimal FTM-shaped entity. Mirrors EntityProxy.to_dict() output."""

    __slots__ = ("id", "schema", "properties")

    def __init__(self, schema: str, eid: str) -> None:
        if schema not in _FTM_SCHEMAS:
            raise ValueError(f"unsupported FTM schema in this exporter: {schema}")
        self.id = eid
        self.schema = schema
        self.properties: dict[str, list[str]] = {}

    def add(self, prop: str, value: str | None) -> None:
        if value is None or value == "":
            return
        v = str(value)
        bucket = self.properties.setdefault(prop, [])
        if v not in bucket:
            bucket.append(v)

    def to_dict(self) -> dict[str, Any]:
        # Stable property ordering for deterministic output.
        return {
            "id": self.id,
            "schema": self.schema,
            "properties": {k: list(self.properties[k]) for k in sorted(self.properties)},
        }


def _make_entity(schema_name: str, eid: str, source_url: str | None = None) -> _Entity:
    """Return an empty FTM entity with publisher provenance set."""

    e = _Entity(schema_name, eid)
    e.add("publisher", PUBLISHER)
    e.add("publisherUrl", PUBLISHER_URL)
    if source_url:
        e.add("sourceUrl", source_url)
    return e


def _country_from_jurisdiction(juris: str | None) -> str:
    if not juris:
        return ""
    j = juris.strip().lower()
    if len(j) == 2:
        return j
    return ""


def build_entities(  # noqa: PLR0915 — single linear pipeline; splitting hurts traceability
    community_id: int,
    person: str,
    profile: dict[str, Any],
    roles: list[dict[str, str]],
    addresses: list[dict[str, str]],
    officers: list[dict[str, str]],
    agents: list[dict[str, str]],
) -> list[dict[str, Any]]:
    """Return a list of FTM-entity dicts (ready for ndjson emit)."""

    cid = community_id
    entities: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    def _push(entity) -> None:
        d = entity.to_dict()
        if d["id"] in seen_ids:
            return
        seen_ids.add(d["id"])
        entities.append(d)

    # Defined early so address-loop + role-loop + ownership-loop all share it.
    member_lookup: dict[str, dict[str, Any]] = {}

    def _ensure_company(uid: str, name: str = "") -> str:
        """Emit a Company entity for a uid that may not be in members_sample.

        Returns the entity id. Idempotent; safe to call repeatedly. Used
        because profile.members_sample caps at 50 entries — clusters with
        >50 members will have role/officer edges pointing at uids we
        otherwise wouldn't see.
        """
        co_id = _eid_company(cid, uid)
        if co_id in seen_ids:
            return co_id
        # Try to look up a friendlier name from previously-emitted member rows.
        if not name and uid in member_lookup:
            name = member_lookup[uid].get("name") or uid
        co = _make_entity("Company", co_id, _icij_source_url(uid))
        co.add("name", name or uid)
        co.add("idNumber", uid)
        co.add(
            "notes",
            f"Cluster #{cid} member referenced by role/officer edge "
            "(not in the first-50 members_sample summary).",
        )
        _push(co)
        return co_id

    # ---- The anchor person (the human anchor of the investigation) ----
    person_uids = profile.get("person_uids") or []
    if not person_uids:
        # Synthesize a placeholder uid from the name.
        person_uids = [f"name:{person}"]
    anchor_id = _eid_person(cid, person_uids[0])
    anchor = _make_entity("Person", anchor_id, _icij_source_url(person_uids[0]))
    anchor.add("name", person.title())
    for uid in person_uids:
        anchor.add("idNumber", uid)
        url = _icij_source_url(uid)
        if url:
            anchor.add("sourceUrl", url)
    anchor.add(
        "notes",
        f"Anchor person for GoldenMatch validation pack of community #{cid}. "
        "Same-name records have not been verified as the same individual.",
    )
    _push(anchor)

    # ---- Cluster member companies (from profile.members_sample) ----
    member_lookup: dict[str, dict[str, Any]] = {}
    for m in profile.get("members_sample") or []:
        uid = m.get("uid") or ""
        name = m.get("name") or uid
        if not uid:
            continue
        # Skip person-typed uids (officers/intermediaries that appear in the
        # cluster as members) — they're handled below.
        member_lookup[uid] = m
        eid = _eid_company(cid, uid)
        co = _make_entity("Company", eid, _icij_source_url(uid))
        co.add("name", name)
        if m.get("jurisdiction"):
            country = _country_from_jurisdiction(m["jurisdiction"])
            if country:
                co.add("jurisdiction", country)
                co.add("country", country)
        co.add("idNumber", uid)
        if m.get("seed"):
            co.add(
                "notes",
                f"Seed node for community #{cid}; surfaced by the dossier-anchored "
                "2-hop graph walk.",
            )
        _push(co)

    # ---- Shared addresses + Address entities + Membership edges ----
    address_id_by_text: dict[str, str] = {}
    for a in addresses:
        addr_text = a.get("address") or ""
        if not addr_text:
            continue
        addr_id = _eid_address(cid, addr_text)
        address_id_by_text[addr_text] = addr_id
        addr_e = _make_entity("Address", addr_id)
        addr_e.add("full", addr_text)
        if "MALTA" in addr_text.upper():
            addr_e.add("country", "mt")
        addr_e.add(
            "notes",
            f"Recurring registered address linking "
            f"{a.get('n_linked_companies', '?')} companies in community #{cid}.",
        )
        _push(addr_e)

        # Edge: every linked company → registeredAt → this address.
        linked = (a.get("linked_companies") or "").split(";")
        for company_name in linked:
            company_name = company_name.strip()
            if not company_name:
                continue
            # Resolve company name back to uid via member_lookup.
            uid = _name_to_uid(company_name, member_lookup)
            if not uid:
                continue
            co_id = _ensure_company(uid, company_name)
            # Update the company entity to carry the address text in-line too
            # (Aleph displays this even without a separate Address resolver).
            for ent in entities:
                if ent["id"] == co_id:
                    ent.setdefault("properties", {}).setdefault("address", []).append(addr_text)
                    ent["properties"]["address"] = sorted(set(ent["properties"]["address"]))
                    break

    # ---- Person entities for officers / intermediaries ----
    officer_ids: dict[str, str] = {}
    for o in officers:
        name = o.get("officer_name") or ""
        if not name:
            continue
        # Heuristic: if the name matches a company-suffixed pattern, skip — it's
        # actually a corporate shareholder (handled as Ownership separately).
        if any(
            tok in name.lower().split()
            for tok in ("ltd", "limited", "ltd.", "plc", "limitada", "llc")
        ):
            continue
        pid = _eid_person(cid, f"officer:{name}")
        officer_ids[name] = pid
        if pid in seen_ids:
            continue
        p = _make_entity("Person", pid)
        p.add("name", name.title())
        p.add(
            "notes",
            f"Recurring officer in community #{cid}: appears on "
            f"{o.get('n_linked_companies', '?')} cluster companies with roles "
            f"{o.get('roles', '')}.",
        )
        _push(p)

    for a in agents:
        name = a.get("intermediary_name") or ""
        if not name:
            continue
        pid = _eid_person(cid, f"intermediary:{name}")
        if pid in seen_ids:
            continue
        p = _make_entity("LegalEntity", pid)
        p.add("name", name.title())
        p.add(
            "notes",
            f"Recurring intermediary in community #{cid}: appears on "
            f"{a.get('n_linked_companies', '?')} cluster companies.",
        )
        _push(p)

    # ---- Directorship edges (the rich role data lives here) ----
    # Anchor → company edges from roles CSV.
    for r in roles:
        company_name = r.get("company_name") or ""
        company_uid = r.get("company_record_id") or ""
        role = r.get("role") or "unknown"
        if not company_uid:
            company_uid = _name_to_uid(company_name, member_lookup) or company_name
        co_id = _ensure_company(company_uid, company_name)
        dir_id = _eid_directorship(cid, person_uids[0], company_uid, role)
        d = _make_entity("Directorship", dir_id)
        d.add("director", anchor_id)
        d.add("organization", co_id)
        d.add("role", role)
        if r.get("start_date"):
            d.add("startDate", r["start_date"])
        if r.get("end_date"):
            d.add("endDate", r["end_date"])
        if r.get("leak"):
            d.add("sourceUrl", _icij_source_url(r.get("person_record_id")))
            d.add(
                "notes",
                f"From {r['leak']}. {r.get('notes', '')}",
            )
        # If the role string says "shareholder", also emit an Ownership.
        if "shareholder" in role.lower():
            own_id = _eid_ownership(cid, person_uids[0], company_uid)
            own = _make_entity("Ownership", own_id)
            own.add("owner", anchor_id)
            own.add("asset", co_id)
            own.add("role", role)
            if r.get("leak"):
                own.add("notes", f"From {r['leak']}")
            _push(own)
        _push(d)

    # Repeated officer → company directorships (one Directorship per officer
    # per linked company, role = officer's combined-role string).
    for o in officers:
        name = o.get("officer_name") or ""
        if name not in officer_ids:
            continue
        person_id = officer_ids[name]
        role_str = o.get("roles") or "officer"
        linked = (o.get("linked_companies") or "").split(";")
        for company_name in linked:
            company_name = company_name.strip()
            if not company_name:
                continue
            uid = _name_to_uid(company_name, member_lookup)
            if not uid:
                continue
            co_id = _ensure_company(uid, company_name)
            dir_id = _eid_directorship(cid, f"officer:{name}", uid, role_str[:40])
            d = _make_entity("Directorship", dir_id)
            d.add("director", person_id)
            d.add("organization", co_id)
            d.add("role", role_str)
            d.add(
                "notes",
                f"Recurring officer across {o.get('n_linked_companies', '?')} "
                f"community-#{cid} companies (source: {o.get('source_label', '')}).",
            )
            _push(d)

    return entities


def _name_to_uid(company_name: str, member_lookup: dict[str, dict[str, Any]]) -> str:
    """Best-effort lookup: match by raw name or normalized form."""
    if not company_name:
        return ""
    target = normalize_company_name(company_name)
    for uid, m in member_lookup.items():
        if m.get("name") == company_name:
            return uid
        if normalize_company_name(m.get("name") or "") == target:
            return uid
    return ""


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def export(
    community_id: int,
    person: str,
    *,
    pack_dir: Path | None = None,
    out_path: Path | None = None,
    repo_root: Path = PROJECT_ROOT,
) -> Path:
    base = (pack_dir or repo_root / "docs" / "validation").resolve()
    data = base / "data"
    cid = community_id

    profile = _read_json(data / f"cluster_{cid}_profile.json")
    if profile is None:
        raise SystemExit(
            f"[fatal] cluster_{cid}_profile.json not found at {data}. "
            "Run scripts/build_validation_pack.py first."
        )

    roles = _read_csv(data / f"cluster_{cid}_person_company_roles.csv")
    addresses = _read_csv(data / f"cluster_{cid}_repeated_addresses.csv")
    officers = _read_csv(data / f"cluster_{cid}_repeated_officers.csv")
    agents = _read_csv(data / f"cluster_{cid}_repeated_agents.csv")

    entities = build_entities(
        community_id=cid,
        person=person,
        profile=profile,
        roles=roles,
        addresses=addresses,
        officers=officers,
        agents=agents,
    )

    out = out_path or (data / f"cluster_{cid}_ftm.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for e in entities:
            f.write(json.dumps(e, sort_keys=True, default=str) + "\n")

    # Summary tally for sanity-checking the export.
    by_schema: dict[str, int] = defaultdict(int)
    for e in entities:
        by_schema[e["schema"]] += 1
    log.info("wrote %d FTM entities to %s", len(entities), out)
    for s, n in sorted(by_schema.items()):
        log.info("  %s: %d", s, n)

    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description=(
            "Export a validation pack to FollowTheMoney ndjson. The output is "
            "OpenAleph / ICIJ Datashare / ftm-store compatible."
        )
    )
    p.add_argument("--community-id", type=int, required=True)
    p.add_argument("--person", type=str, required=True)
    p.add_argument(
        "--pack-dir",
        type=Path,
        default=None,
        help="override docs/validation/",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=None,
        help="override output path (default: <pack-dir>/data/cluster_<id>_ftm.json)",
    )
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    out = export(
        community_id=args.community_id,
        person=args.person,
        pack_dir=args.pack_dir,
        out_path=args.out,
    )
    try:
        rel = out.relative_to(PROJECT_ROOT)
        print(f"wrote {rel}")
    except ValueError:
        print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
