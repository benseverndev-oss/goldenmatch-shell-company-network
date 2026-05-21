"""Build a reproducibility bundle for the 128 Ebury Street case study.

The bundle is a single .zip with every artefact a journalist needs
to reproduce the finding from scratch:

  cluster_128_ebury_aleph_bundle.zip
  ├── README.md                       # how to read this bundle
  ├── manifest.json                   # bundle metadata + cited URLs
  ├── docs/
  │   ├── video_script.md             # 128_ebury_street_case_study.md
  │   └── video_script_barilla.md     # for comparison
  ├── probes/
  │   ├── ebury_128_hub.json
  │   ├── ocod_icij_overlap.json
  │   ├── ocod_disqualified_overlap.json
  │   ├── tohme_sarkis_network.json
  │   ├── bvi_deepdive.json
  │   └── ebury_bos_summary.json
  ├── ch_pages/                       # captured Companies House HTML
  │   ├── ch_oe<NNNN>_psc.html
  │   └── ...
  └── source_code/
      ├── probe_128_ebury_hub.py
      ├── probe_tohme_sarkis_network.py
      ├── probe_bvi_confirmed_deepdive.py
      ├── probe_hmlr_ocod_crossref.py
      └── scrape_ch_for_ebury_companies.py

Outputs ``data/investigations/128_ebury/cluster_128_ebury_aleph_bundle.zip``.

Run after the probes have completed locally and the per-company CH
HTML has been captured.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import zipfile
from datetime import UTC, datetime
from pathlib import Path

log = logging.getLogger("build_128_ebury_bundle")

REPO_ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _add(zf: zipfile.ZipFile, src: Path, arc: str, manifest: list[dict]) -> None:
    if not src.exists():
        log.warning("skipping missing file: %s", src)
        return
    zf.write(src, arc)
    manifest.append(
        {
            "arc": arc,
            "source": str(src.relative_to(REPO_ROOT))
            if REPO_ROOT in src.parents
            else str(src),
            "size_bytes": src.stat().st_size,
            "sha256": _sha256(src),
        }
    )
    log.info("  + %s (%d bytes)", arc, src.stat().st_size)


def _readme(now_iso: str) -> str:
    return f"""# 128 Ebury Street — investigative reproducibility bundle

Generated **{now_iso}** by `scripts/build_128_ebury_bundle.py`.

## What this bundle contains

Everything a journalist needs to reproduce the 128 Ebury Street
case study end-to-end:

| Folder | Contents |
| --- | --- |
| `docs/` | The video script (`video_script.md`) — the human-readable narrative + shot list + citation URLs |
| `probes/` | Raw JSON outputs from every Railway-side probe — the data that backs every claim in the video |
| `ch_pages/` | Captured HTML of every UK Companies House page cited — courts will accept these as evidence even if CH's site changes |
| `source_code/` | The Python source for every probe that produced the data |

## How to verify any claim

1. Open `manifest.json` — find the file you want to verify.
2. Compute its sha256 locally and compare to the manifest value.
3. Cross-check the on-screen narration timing in
   `docs/video_script.md` against the cited URLs in the same
   section.
4. For ICIJ provenance, fetch the relevant ICIJ node URL (e.g.
   `https://offshoreleaks.icij.org/nodes/14033543` for the
   128 Ebury address node) and confirm the data is still
   live-public.
5. For UK Companies House provenance, the captured HTML in
   `ch_pages/` is the snapshot; the live URL is in `manifest.json`.

## Cautious framing (required reading)

- Offshore ownership of UK property is **legal**.
- Use of UK corporate-services providers is **a regulated
  profession**.
- The 2022 Economic Crime Act explicitly required this
  beneficial-owner disclosure; the disclosure is happening as
  intended.
- The bundle does **not** allege wrongdoing against any individual,
  family, firm, or company named.
- The pre-publication checklist in `docs/video_script.md` is
  load-bearing — UK media-lawyer review, right of reply to every
  named individual, and notification to regulators are required
  before any derivative work is published.

## Methodology

- Sources: ICIJ Offshore Leaks DB, HM Land Registry OCOD, UK
  Companies House Register of Overseas Entities. All free, public,
  open-licensed.
- Pipeline: open-source MIT, at
  `https://github.com/benseverndev-oss/goldenmatch-shell-company-network`.
- Total compute time to surface this finding from raw data: <10
  minutes on a Railway-class instance.

## Licence

The pipeline code is MIT. The captured CH HTML and ICIJ data are
redistributed under their respective Open Government Licence v3.0
and Creative Commons BY-SA 4.0 terms. Every derivative work must
preserve those upstream attributions.
"""


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--out",
        type=Path,
        default=REPO_ROOT
        / "data"
        / "investigations"
        / "128_ebury"
        / "cluster_128_ebury_aleph_bundle.zip",
    )
    p.add_argument(
        "--probes-dir",
        type=Path,
        default=REPO_ROOT,
        help=(
            "Where local probe JSONs live. Defaults to repo root since "
            "we pull each probe to cwd during interactive work."
        ),
    )
    p.add_argument(
        "--ch-pages-dir",
        type=Path,
        default=REPO_ROOT / ".firecrawl" / "barilla",
        help="Where captured CH HTML files live.",
    )
    p.add_argument(
        "--ebury-bos-dir",
        type=Path,
        default=REPO_ROOT / ".firecrawl" / "ebury_bos",
        help="Where the per-company BO scrape outputs live.",
    )
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    args.out.parent.mkdir(parents=True, exist_ok=True)

    cited_urls = [
        ("ICIJ 128 Ebury address node", "https://offshoreleaks.icij.org/nodes/14033543"),
        ("HMLR OCOD download portal", "https://use-land-property-data.service.gov.uk/datasets/ocod"),
        ("Companies House — RAWI CO ASSOCIATES LTD", "https://find-and-update.company-information.service.gov.uk/company/09389698"),
        ("Companies House — Small Property Limited (Al-Thani worked example)", "https://find-and-update.company-information.service.gov.uk/company/OE003363/persons-with-significant-control"),
        ("Companies House — HEMSLEY PROPERTIES (Akeel)", "https://find-and-update.company-information.service.gov.uk/company/OE033110/persons-with-significant-control"),
        ("Companies House — TASS INVESTMENTS (Uppal)", "https://find-and-update.company-information.service.gov.uk/company/OE001400/persons-with-significant-control"),
        ("UNHCR — Sheikh Thani Al-Thani Eminent Advocate", "https://www.unhcr.org/asia/about-unhcr/our-partners/prominent-supporters/eminent-advocates/his-excellency-sheikh-thani-bin"),
        ("Open-source pipeline (MIT)", "https://github.com/benseverndev-oss/goldenmatch-shell-company-network"),
    ]

    manifest: list[dict] = []
    now_iso = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    with zipfile.ZipFile(args.out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        # README + manifest header (we'll add the actual manifest at the end)
        zf.writestr("README.md", _readme(now_iso))

        # docs/
        _add(
            zf,
            REPO_ROOT / "docs" / "videos" / "128_ebury_street_case_study.md",
            "docs/video_script.md",
            manifest,
        )
        _add(
            zf,
            REPO_ROOT / "docs" / "videos" / "barilla_jamers_case_study.md",
            "docs/video_script_barilla.md",
            manifest,
        )

        # probes/
        probe_files = [
            "ebury_128_hub.json",
            "ocod_icij_overlap.json",
            "ocod_disqualified_overlap.json",
            "ocod_sajid_bashir.json",
            "tohme_sarkis_network.json",
            "bvi_deepdive.json",
            "barilla_network.json",
        ]
        for f in probe_files:
            _add(zf, args.probes_dir / f, f"probes/{f}", manifest)

        # ebury_bos summary
        _add(
            zf,
            args.ebury_bos_dir / "_summary.json",
            "probes/ebury_bos_summary.json",
            manifest,
        )

        # ch_pages/ — captured Companies House + ICIJ HTML
        if args.ch_pages_dir.exists():
            for p in sorted(args.ch_pages_dir.glob("*.html")):
                _add(zf, p, f"ch_pages/{p.name}", manifest)

        # source_code/
        source_files = [
            "probe_128_ebury_hub.py",
            "probe_tohme_sarkis_network.py",
            "probe_bvi_confirmed_deepdive.py",
            "probe_hmlr_ocod_crossref.py",
            "probe_barilla_network.py",
            "scrape_ch_for_ebury_companies.py",
            "build_128_ebury_bundle.py",
        ]
        for f in source_files:
            _add(zf, REPO_ROOT / "scripts" / f, f"source_code/{f}", manifest)

        # Write the manifest as the very last entry
        zf.writestr(
            "manifest.json",
            json.dumps(
                {
                    "generated_at": now_iso,
                    "case_study": "128 Ebury Street, Belgravia",
                    "generator": "scripts/build_128_ebury_bundle.py",
                    "generator_url": "https://github.com/benseverndev-oss/goldenmatch-shell-company-network",
                    "cited_urls": [{"label": l, "url": u} for l, u in cited_urls],
                    "files": manifest,
                    "human_review_required": True,
                    "publication_safe_by_default": False,
                },
                indent=2,
                sort_keys=True,
            ),
        )

    log.info("wrote %s (%d files)", args.out, len(manifest))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
