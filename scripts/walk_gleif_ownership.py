"""Company-anchored matching: walk the GLEIF L2 ownership graph from
OFAC/EU/UK asset-frozen sanctioned entities and surface their adjacent
not-yet-sanctioned subsidiaries / parents.

This is the Tier-D workflow that makes the GLEIF L2 ingest pay off.
The list-match-against-OS pipeline (the rest of the project) is
person-anchored — given a sanctioned person, find their offshore
officer rows. This script is the company-anchored counterpart: given
a sanctioned entity's LEI, walk the corporate ownership graph and
surface what else the matcher believes is controlled by, or controls,
that entity.

Input parquets:
  - data/interim/opensanctions_entities.parquet  (sanctioned entities)
  - data/interim/gleif_l2_relationships.parquet  (ownership edges)

Output:
  - reports/investigations/gleif_ownership_chains.md
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from pathlib import Path

import polars as pl
import typer

from shellnet.paths import INTERIM_DIR, PROJECT_ROOT

app = typer.Typer(add_completion=False, no_args_is_help=False)
log = logging.getLogger(__name__)

_LEI_RE = re.compile(r"^[A-Z0-9]{20}$")


def _extract_lei(identifiers: list[str] | None) -> str | None:
    if not identifiers:
        return None
    for x in identifiers:
        if x and _LEI_RE.match(x):
            return x
    return None


@app.command()
def main(
    os_parquet: Path = typer.Option(
        INTERIM_DIR / "opensanctions_entities.parquet", "--os-parquet"
    ),
    edges_parquet: Path = typer.Option(
        INTERIM_DIR / "gleif_l2_relationships.parquet", "--edges-parquet"
    ),
    out_path: Path = typer.Option(
        PROJECT_ROOT / "reports" / "investigations" / "gleif_ownership_chains.md",
        "--out",
    ),
    sanctions_datasets: str = typer.Option(
        # Original filter was us_ofac,eu_fsf,gb_hmt — too narrow. OS
        # actually calls the relevant datasets us_ofac_sdn,
        # us_sam_exclusions, gb_fcdo_sanctions, ch_seco_sanctions, etc.
        # The first run misclassified real OFAC-sanctioned entities
        # (the Sovcomflot Cyprus shipping shells under
        # us_sam_exclusions) as "not yet sanctioned" because they
        # weren't on the literal us_ofac dataset substring.
        #
        # Wider net: trust OS's own classification — if it assigned
        # the `sanction` topic AND placed the entity on any
        # internationally-recognised sanctions / freeze list, treat as
        # directly sanctioned.
        "us_ofac,us_sam_exclusions,us_trade_csl,eu_fsf,eu_travel_bans,"
        "eu_journal_sanctions,gb_fcdo_sanctions,ch_seco_sanctions,"
        "ua_nsdc_sanctions,ua_war_sanctions,ca_dfatd_sema_sanctions,"
        "au_dfat_sanctions,jp_mof_sanctions,fr_tresor_gels_avoir,"
        "be_fod_sanctions,mc_fund_freezes,nz_russia_sanctions,"
        "tw_shtc,iq_aml_list,kg_fiu_national",
        "--sanctions-datasets",
        help="Comma-separated substrings of OS dataset names to count as "
        "real asset-freeze sanctions (vs reg.action / sanction.linked).",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    log.info("loading OS entities from %s", os_parquet)
    os_e = pl.read_parquet(os_parquet)
    log.info("OS rows: %d", os_e.height)
    rows = os_e.filter(
        pl.col("entity_schema").is_in(["Company", "Organization", "LegalEntity"])
    )

    keep_datasets = [d.strip() for d in sanctions_datasets.split(",") if d.strip()]

    sanctioned: dict[str, dict] = {}  # lei -> {name, datasets}
    name_by_lei: dict[str, str] = {}
    for r in rows.iter_rows(named=True):
        lei = _extract_lei(r["identifiers"])
        if not lei:
            continue
        name_by_lei.setdefault(lei, r["name"])
        topics = list(r["topics"] or [])
        datasets = list(r["datasets"] or [])
        if "sanction" in topics and any(
            any(kd in ds for kd in keep_datasets) for ds in datasets
        ):
            sanctioned[lei] = {"name": r["name"], "datasets": datasets}
    log.info(
        "%d directly-sanctioned LEIs (topic=sanction AND on %s)",
        len(sanctioned),
        keep_datasets,
    )

    log.info("loading ownership edges from %s", edges_parquet)
    e = pl.read_parquet(edges_parquet).with_columns(
        pl.col("src_lei").str.replace_all("^XI-LEI-", "").alias("src_lei"),
        pl.col("dst_lei").str.replace_all("^XI-LEI-", "").alias("dst_lei"),
    )
    log.info("edges: %d", e.height)

    lei_set = list(sanctioned)
    both = e.filter(
        pl.col("src_lei").is_in(lei_set) & pl.col("dst_lei").is_in(lei_set)
    )
    one_side = e.filter(
        (pl.col("src_lei").is_in(lei_set) & ~pl.col("dst_lei").is_in(lei_set))
        | (~pl.col("src_lei").is_in(lei_set) & pl.col("dst_lei").is_in(lei_set))
    )
    log.info("both-ends-sanctioned: %d", both.height)
    log.info("exactly-one-end-sanctioned: %d", one_side.height)

    by_parent: dict[str, list[str]] = defaultdict(list)
    by_child: dict[str, list[str]] = defaultdict(list)
    for r in one_side.iter_rows(named=True):
        # In GLEIF L2: src is the *controlled* entity, dst is the controller.
        # Edge meaning: src --is controlled by--> dst.
        if r["src_lei"] in sanctioned:
            sanc, neigh = r["src_lei"], r["dst_lei"]
            # neighbor controls sanctioned -> neighbor is a *parent*
            by_parent[sanc].append(neigh)
        else:
            sanc, neigh = r["dst_lei"], r["src_lei"]
            # sanctioned controls neighbor -> neighbor is a *subsidiary*
            by_child[sanc].append(neigh)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append("# GLEIF L2 ownership chains — asset-frozen entities + adjacent")
    lines.append("")
    lines.append(
        f"Generated from OS entities filtered by topic == `sanction` AND "
        f"datasets containing any of {keep_datasets}."
    )
    lines.append("")
    lines.append("> **Hypothesis, not proof.** Each chain is a registry-disclosed corporate ownership link via GLEIF Level 2. The fact that one end is OFAC/EU/UK asset-frozen and the other isn't is a *lead* that warrants human review (and possibly secondary-sanctions designation), not a finding. Names may be common; LEI plus jurisdiction is the discriminator.")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Directly-sanctioned LEIs (topic == `sanction`, on OFAC/EU/UK lists): **{len(sanctioned)}**")
    lines.append(f"- Edges with both ends sanctioned: **{both.height}**")
    lines.append(f"- Edges with exactly one end sanctioned (not-yet-sanctioned neighbour): **{one_side.height}**")
    lines.append("")

    lines.append("## Both-ends-sanctioned chains")
    lines.append("")
    lines.append("Pre-existing intra-sanctioned-network corporate-ownership links. Both endpoints are already on the asset-freeze lists.")
    lines.append("")
    lines.append("| controlled (src) | controller (dst) |")
    lines.append("| --- | --- |")
    for r in both.head(40).iter_rows(named=True):
        s = sanctioned.get(r["src_lei"], {}).get("name", r["src_lei"])[:60]
        d = sanctioned.get(r["dst_lei"], {}).get("name", r["dst_lei"])[:60]
        lines.append(f"| `{r['src_lei'][:20]}` {s} | `{r['dst_lei'][:20]}` {d} |")
    if both.height > 40:
        lines.append(f"| _… {both.height-40} more rows_ | |")
    lines.append("")

    lines.append("## Sanctioned parent → not-yet-sanctioned subsidiaries")
    lines.append("")
    lines.append("Each row is one *children-of* group: a sanctioned entity at the top, followed by GLEIF L2 subsidiaries that are not (yet) on the asset-freeze lists. These are the candidate secondary-sanctions targets.")
    lines.append("")
    for sanc_lei, kids in sorted(by_child.items(), key=lambda kv: -len(kv[1]))[:30]:
        s_name = sanctioned[sanc_lei]["name"][:70]
        lines.append(f"### `{sanc_lei}` {s_name}")
        lines.append("")
        for k in kids[:15]:
            kn = name_by_lei.get(k, "(name not in OS — pull GLEIF entity record for full name)")[:80]
            lines.append(f"- `{k}` {kn}")
        if len(kids) > 15:
            lines.append(f"- _… {len(kids)-15} more_")
        lines.append("")

    lines.append("## Sanctioned subsidiary ← not-yet-sanctioned parent")
    lines.append("")
    lines.append("The reverse direction: a sanctioned entity that is controlled by an entity not on the asset-freeze lists. Less common (sanctions tend to flow downward through ownership) but each row is worth flagging.")
    lines.append("")
    for sanc_lei, parents in sorted(by_parent.items(), key=lambda kv: -len(kv[1]))[:20]:
        s_name = sanctioned[sanc_lei]["name"][:70]
        lines.append(f"### `{sanc_lei}` {s_name}")
        lines.append("")
        for p in parents[:10]:
            pn = name_by_lei.get(p, "(name not in OS — pull GLEIF entity record for full name)")[:80]
            lines.append(f"- `{p}` {pn}")
        if len(parents) > 10:
            lines.append(f"- _… {len(parents)-10} more_")
        lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    log.info("wrote %s (%d sanctioned-LEI seed entities)", out_path, len(sanctioned))
    print(str(out_path))


if __name__ == "__main__":
    app()
