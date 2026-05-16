"""Thin wrapper around Max Harlow's ``reconcile`` CLI.

https://github.com/maxharlow/reconcile

``reconcile`` is a Node.js CLI for fan-out enrichment of CSV files
against online services. We use it as a subprocess from Railway jobs
to enrich ranked shortlists (NOT the full corpus — most reconcilers
are rate-limited and Equasis is hard-capped at ~500 lookups/day).

This wrapper exists so each per-source script (``reconcile_equasis``,
``reconcile_ru_companies``, ``reconcile_sec_filings``) can share the
same subprocess plumbing without re-implementing argument quoting or
error handling.

Install on Railway: see Dockerfile (Node 20 + ``npm install -g reconcile``).

Locally, you can run ``npx reconcile ...`` instead of the global install
— set ``RECONCILE_CMD=npx reconcile`` to force that.
"""

from __future__ import annotations

import logging
import os
import shlex
import shutil
import subprocess
from pathlib import Path

log = logging.getLogger(__name__)


class ReconcileError(RuntimeError):
    pass


def _resolve_cmd() -> list[str]:
    override = os.environ.get("RECONCILE_CMD")
    if override:
        return shlex.split(override)
    found = shutil.which("reconcile")
    if not found:
        raise ReconcileError(
            "`reconcile` CLI not on PATH. Install with `npm install -g reconcile` "
            "or set RECONCILE_CMD=`npx reconcile`."
        )
    return [found]


def _format_params(params: dict[str, str]) -> str:
    """Format a params dict as reconcile's YAML-ish `-p` string.

    reconcile's syntax is ``key1: value1; key2: value2``. Values may not
    contain unescaped semicolons or newlines.
    """
    for k, v in params.items():
        if ";" in v or "\n" in v:
            raise ReconcileError(f"param {k!r} value cannot contain ';' or newline")
    return "; ".join(f"{k}: {v}" for k, v in params.items())


def run(
    reconciler: str,
    input_csv: Path,
    output_csv: Path,
    params: dict[str, str],
    *,
    retries: int = 5,
    cache_dir: Path | None = None,
    timeout: float | None = None,
) -> Path:
    """Run a reconcile command, writing stdout to ``output_csv``.

    ``params`` is the ``-p`` payload (keys depend on the reconciler;
    see https://github.com/maxharlow/reconcile for each one).
    """
    if not input_csv.exists():
        raise FileNotFoundError(f"input csv missing: {input_csv}")
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    cmd = _resolve_cmd() + [
        reconciler,
        str(input_csv),
        "-p",
        _format_params(params),
        "-r",
        str(retries),
    ]
    if cache_dir is not None:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cmd += ["-c", str(cache_dir)]

    log.info("reconcile: %s", " ".join(shlex.quote(c) for c in cmd))
    with output_csv.open("wb") as fh:
        proc = subprocess.run(
            cmd,
            stdout=fh,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
    if proc.returncode != 0:
        err = proc.stderr.decode("utf-8", errors="replace")
        raise ReconcileError(f"reconcile {reconciler} exited {proc.returncode}: {err}")
    return output_csv
