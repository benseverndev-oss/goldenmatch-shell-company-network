"""Export a validation pack to Beneficial Ownership Data Standard (BODS) v0.4.

Sibling of ``scripts/export_validation_pack_ftm.py``. Reads the same
validation-pack artefacts and emits a BODS v0.4 statement stream
(ndjson, one statement per line) — the canonical data model used by
Open Ownership, UK PSC, the EU BORIS register, and the upcoming
EU AMLA single access point.

Reads (from ``docs/validation/`` by default)::

    cluster_<id>_profile.json
    cluster_<id>_person_company_roles.csv
    cluster_<id>_repeated_addresses.csv
    cluster_<id>_repeated_officers.csv

Writes::

    docs/validation/data/cluster_<id>_bods.json   (ndjson; one statement per line)

The BODS statement shape is documented at
https://standard.openownership.org/en/0.4.0/. We emit three statement
types: ``entityStatement`` (Company), ``personStatement`` (Person),
and ``ownershipOrControlStatement`` (the relationship). Every
statement carries ``publicationDetails`` pointing at this pipeline +
the GitHub repo.

Usage::

    uv run python scripts/export_validation_pack_bods.py \\
        --community-id 37 \\
        --person "calvin edward ayre"
"""

from __future__ import annotations

import argparse
import csv
import hashlib
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

log = logging.getLogger("export_validation_pack_bods")

PROJECT_ROOT = _REPO_ROOT
PUBLISHER_NAME = "GoldenMatch shell-company-network discovery pipeline"
PUBLISHER_URL = "https://github.com/benseverndev-oss/goldenmatch-shell-company-network"
BODS_VERSION = "0.4"
LICENSE_URL = "https://creativecommons.org/publicdomain/zero/1.0/"

# Fixed reference date so output is byte-stable across re-runs of the same
# pack. Real consumers re-publish on each refresh; for our pipeline that's
# the build_validation_pack run, not now.
PUBLICATION_DATE = "2026-05-19"


_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slug(s: str) -> str:
    if not s:
        return "x"
    out = _SLUG_RE.sub("-", s.lower()).strip("-")
    return out[:80] or "x"


def _stable_id(prefix: str, *parts: str) -> str:
    """Deterministic BODS statementId. BODS spec recommends a UUID; we use
    a content hash so re-runs produce identical IDs (idempotency)."""

    raw = "|".join(parts)
    h = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]
    return f"openownership-{prefix}-{h}"


def _icij_source_url(uid: str | None) -> str:
    if not uid or not uid.startswith("icij:"):
        return ""
    return f"https://offshoreleaks.icij.org/nodes/{uid.split(':', 1)[1]}"


# ---------------------------------------------------------------------------
# Loaders (identical to the FTM exporter)
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
# Statement construction
# ---------------------------------------------------------------------------


def _publication_details() -> dict[str, Any]:
    return {
        "publicationDate": PUBLICATION_DATE,
        "bodsVersion": BODS_VERSION,
        "license": LICENSE_URL,
        "publisher": {"name": PUBLISHER_NAME, "url": PUBLISHER_URL},
    }


def _entity_statement(
    uid: str, name: str, jurisdiction: str = "", notes: str = ""
) -> dict[str, Any]:
    stmt_id = _stable_id("ent", uid)
    js: dict[str, Any] = {
        "statementId": stmt_id,
        "statementType": "entityStatement",
        "statementDate": PUBLICATION_DATE,
        "entityType": {"type": "registeredEntity"},
        "name": name or uid,
        "identifiers": [
            {
                "id": uid,
                "scheme": "GOLDENMATCH-INTERNAL",
                "schemeName": "GoldenMatch internal entity uid",
            }
        ],
        "publicationDetails": _publication_details(),
    }
    if jurisdiction:
        js["jurisdiction"] = {"code": jurisdiction.upper(), "name": jurisdiction.upper()}
    src_url = _icij_source_url(uid)
    if src_url:
        js["source"] = {"type": ["thirdParty"], "url": src_url}
    if notes:
        js["annotations"] = [{"description": notes, "motivation": "describing"}]
    return js


def _person_statement(uid: str, name: str, notes: str = "") -> dict[str, Any]:
    stmt_id = _stable_id("per", uid)
    js: dict[str, Any] = {
        "statementId": stmt_id,
        "statementType": "personStatement",
        "statementDate": PUBLICATION_DATE,
        "personType": "knownPerson",
        "names": [{"type": "individual", "fullName": name}],
        "identifiers": [
            {
                "id": uid,
                "scheme": "GOLDENMATCH-INTERNAL",
                "schemeName": "GoldenMatch internal person uid",
            }
        ],
        "publicationDetails": _publication_details(),
    }
    src_url = _icij_source_url(uid)
    if src_url:
        js["source"] = {"type": ["thirdParty"], "url": src_url}
    if notes:
        js["annotations"] = [{"description": notes, "motivation": "describing"}]
    return js


def _ooc_statement(
    *,
    subject_uid: str,
    interested_uid: str,
    interested_is_person: bool,
    role: str,
    start_date: str = "",
    end_date: str = "",
    notes: str = "",
) -> dict[str, Any]:
    subj_stmt = _stable_id("ent", subject_uid)
    ip_stmt = _stable_id("per" if interested_is_person else "ent", interested_uid)
    stmt_id = _stable_id("ooc", subject_uid, interested_uid, role)
    # BODS interestType vocabulary mapping (rough).
    role_l = (role or "").lower()
    if "share" in role_l or "owner" in role_l:
        interest_type = "shareholding"
    elif "director" in role_l:
        interest_type = "voting-rights"  # closest BODS term
    elif "secretar" in role_l or "officer" in role_l:
        interest_type = "appointment-of-board"
    else:
        interest_type = "other-influence-or-control"

    interest: dict[str, Any] = {"type": interest_type, "details": role}
    if start_date:
        interest["startDate"] = start_date
    if end_date:
        interest["endDate"] = end_date

    js: dict[str, Any] = {
        "statementId": stmt_id,
        "statementType": "ownershipOrControlStatement",
        "statementDate": PUBLICATION_DATE,
        "subject": {"describedByEntityStatement": subj_stmt},
        "interestedParty": (
            {"describedByPersonStatement": ip_stmt}
            if interested_is_person
            else {"describedByEntityStatement": ip_stmt}
        ),
        "interests": [interest],
        "publicationDetails": _publication_details(),
    }
    if notes:
        js["annotations"] = [{"description": notes, "motivation": "describing"}]
    return js


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


def _name_to_uid(company_name: str, member_lookup: dict[str, dict[str, Any]]) -> str:
    if not company_name:
        return ""
    target = normalize_company_name(company_name)
    for uid, m in member_lookup.items():
        if m.get("name") == company_name:
            return uid
        if normalize_company_name(m.get("name") or "") == target:
            return uid
    return ""


def build_statements(
    community_id: int,
    person: str,
    profile: dict[str, Any],
    roles: list[dict[str, str]],
    addresses: list[dict[str, str]],
    officers: list[dict[str, str]],
) -> list[dict[str, Any]]:
    """Return BODS-shaped statement dicts ready for ndjson emit."""

    statements: list[dict[str, Any]] = []
    seen: set[str] = set()

    def _push(stmt: dict[str, Any]) -> None:
        sid = stmt["statementId"]
        if sid in seen:
            return
        seen.add(sid)
        statements.append(stmt)

    # 1. Anchor person.
    person_uids = profile.get("person_uids") or [f"name:{person}"]
    anchor_uid = person_uids[0]
    _push(
        _person_statement(
            anchor_uid,
            person.title(),
            notes=(
                f"Anchor person for GoldenMatch validation pack of community "
                f"#{community_id}. Same-name records have not been verified as "
                "the same individual."
            ),
        )
    )

    # 2. Cluster member companies.
    member_lookup: dict[str, dict[str, Any]] = {}
    for m in profile.get("members_sample") or []:
        uid = m.get("uid") or ""
        if not uid:
            continue
        member_lookup[uid] = m
        name = m.get("name") or uid
        juris = (m.get("jurisdiction") or "")[:2].lower()
        seed_note = (
            f"Seed node for community #{community_id}; surfaced by the dossier-"
            "anchored 2-hop graph walk."
            if m.get("seed")
            else ""
        )
        _push(_entity_statement(uid, name, jurisdiction=juris, notes=seed_note))

    # 3. Anchor-person role edges.
    for r in roles:
        company_uid = r.get("company_record_id") or _name_to_uid(
            r.get("company_name") or "", member_lookup
        )
        if not company_uid:
            continue
        # Make sure the company is emitted.
        if company_uid not in member_lookup:
            _push(
                _entity_statement(
                    company_uid,
                    r.get("company_name") or company_uid,
                    notes=(
                        f"Cluster #{community_id} member referenced by role edge "
                        "(not in first-50 members_sample)."
                    ),
                )
            )
            member_lookup[company_uid] = {"name": r.get("company_name") or ""}
        _push(
            _ooc_statement(
                subject_uid=company_uid,
                interested_uid=anchor_uid,
                interested_is_person=True,
                role=r.get("role") or "officer",
                start_date=r.get("start_date") or "",
                end_date=r.get("end_date") or "",
                notes=f"From {r.get('leak', 'GoldenMatch')}. {r.get('notes', '')}".strip(),
            )
        )

    # 4. Recurring-officer edges.
    for o in officers:
        name = o.get("officer_name") or ""
        if not name:
            continue
        if any(
            tok in name.lower().split()
            for tok in ("ltd", "limited", "ltd.", "plc", "limitada", "llc")
        ):
            # Corporate "officer" — emit as entity + entity-to-entity OOC.
            is_person = False
            officer_uid = f"officer-ent:{_slug(name)}"
            _push(
                _entity_statement(
                    officer_uid,
                    name,
                    notes=(
                        f"Recurring corporate officer in community #{community_id}: "
                        f"appears on {o.get('n_linked_companies', '?')} cluster companies."
                    ),
                )
            )
        else:
            is_person = True
            officer_uid = f"officer-per:{_slug(name)}"
            _push(
                _person_statement(
                    officer_uid,
                    name.title(),
                    notes=(
                        f"Recurring officer in community #{community_id}: "
                        f"appears on {o.get('n_linked_companies', '?')} cluster companies "
                        f"with roles {o.get('roles', '')}."
                    ),
                )
            )

        role_str = o.get("roles") or "officer"
        for company_name in (o.get("linked_companies") or "").split(";"):
            company_name = company_name.strip()
            if not company_name:
                continue
            uid = _name_to_uid(company_name, member_lookup)
            if not uid:
                continue
            _push(
                _ooc_statement(
                    subject_uid=uid,
                    interested_uid=officer_uid,
                    interested_is_person=is_person,
                    role=role_str,
                    notes=(
                        f"Recurring officer across {o.get('n_linked_companies', '?')} "
                        f"community-#{community_id} companies "
                        f"(source: {o.get('source_label', '')})."
                    ),
                )
            )

    return statements


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

    statements = build_statements(
        community_id=cid,
        person=person,
        profile=profile,
        roles=roles,
        addresses=addresses,
        officers=officers,
    )

    out = out_path or (data / f"cluster_{cid}_bods.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for s in statements:
            f.write(json.dumps(s, sort_keys=True, default=str) + "\n")

    tally: dict[str, int] = defaultdict(int)
    for s in statements:
        tally[s["statementType"]] += 1
    log.info("wrote %d BODS statements to %s", len(statements), out)
    for t, n in sorted(tally.items()):
        log.info("  %s: %d", t, n)
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description=(
            "Export a validation pack to Beneficial Ownership Data Standard v0.4 "
            "ndjson. Compatible with Open Ownership tooling."
        )
    )
    p.add_argument("--community-id", type=int, required=True)
    p.add_argument("--person", type=str, required=True)
    p.add_argument("--pack-dir", type=Path, default=None)
    p.add_argument("--out", type=Path, default=None)
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
