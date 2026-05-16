"""Thin runner for Max Harlow's Node.js scrapers.

These scrapers (e.g. ``scrape-disqualified-directors``,
``scrape-members-financial-interests``) are not on npm; we clone them
into the Railway image at build time under ``/opt/scrapers/<name>``
and run them with ``node``. Each writes its output CSV (and any cache
state) to the current working directory, so the runner creates a
per-invocation workdir under ``data/raw/scrapers/<name>/`` and chdirs
there before execution.

Why a per-invocation workdir: the MFI scraper writes a ``cache/`` of
per-URL SHA1s; preserving it across runs avoids re-hitting Parliament.

Per the conventions in CLAUDE.md, all heavy fetching happens on
Railway and outputs land under ``/data``.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from pathlib import Path

from shellnet.paths import RAW_DIR

log = logging.getLogger(__name__)


class ScraperError(RuntimeError):
    pass


def _resolve_install_dir(name: str) -> Path:
    """Locate the cloned scraper directory.

    ``SHELLNET_SCRAPERS_DIR`` overrides the default ``/opt/scrapers``
    so the wrappers can be exercised locally outside the Railway image.
    """
    base = Path(os.environ.get("SHELLNET_SCRAPERS_DIR", "/opt/scrapers"))
    install = base / name
    if not install.exists():
        raise ScraperError(
            f"scraper {name!r} not installed at {install}. "
            "On Railway this is provisioned by the Dockerfile; locally, "
            "set SHELLNET_SCRAPERS_DIR to a directory containing a "
            "git clone + `npm install`."
        )
    return install


def run(
    name: str,
    *,
    entry_script: str,
    output_csv_name: str,
    workdir: Path | None = None,
    timeout: float | None = None,
) -> Path:
    """Run a Node scraper and return the absolute path of its output CSV.

    ``entry_script`` is the .js file relative to the install dir.
    ``output_csv_name`` is the CSV filename the scraper writes to CWD.
    """
    install = _resolve_install_dir(name)
    entry = install / entry_script
    if not entry.exists():
        raise ScraperError(f"entry script missing: {entry}")

    work = workdir or (RAW_DIR / "scrapers" / name)
    work.mkdir(parents=True, exist_ok=True)

    node = shutil.which("node")
    if not node:
        raise ScraperError("`node` not on PATH — install Node 20+ or use the Railway image.")

    cmd = [node, str(entry)]
    log.info("scraper %s: cwd=%s cmd=%s", name, work, " ".join(cmd))
    proc = subprocess.run(cmd, cwd=work, timeout=timeout)
    if proc.returncode != 0:
        raise ScraperError(f"scraper {name} exited {proc.returncode}")

    out = work / output_csv_name
    if not out.exists():
        raise ScraperError(f"scraper {name} did not produce {out}")
    return out
