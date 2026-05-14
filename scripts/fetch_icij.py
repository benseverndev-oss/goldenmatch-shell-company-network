"""Optional helper to fetch the ICIJ Offshore Leaks bundle.

ICIJ distributes the bundle as a ZIP via their public download page at
https://offshoreleaks.icij.org/pages/database. The direct URL has rotated
across releases; we keep it parameterised rather than hardcoded so this
script doesn't silently break.

Usage:
    # Pass the URL you got from the download page:
    uv run python scripts/fetch_icij.py \
        --url https://offshoreleaks.icij.org/path/to/all-offshoreleaks-data.zip \
        --sha256 <hex>

    # Or, with a URL pinned in your env:
    ICIJ_BUNDLE_URL=... uv run python scripts/fetch_icij.py --sha256 <hex>

Why we require ``--sha256``:

ICIJ's bundle is investigative data. We want a tripwire so a man-in-the-middle
or a silently re-uploaded bundle is caught at fetch time, before it
contaminates downstream analysis. Get the checksum from the ICIJ release
notes (or compute it from a known-good local copy) and pass it in.

This script never auto-runs; the README ingestion instructions still tell
users to download manually. It exists so that *if* you want a one-liner
fetch, it's reproducible and verified.
"""

from __future__ import annotations

import hashlib
import logging
import os
import zipfile
from pathlib import Path

import httpx
import typer

from shellnet.paths import ICIJ_RAW, ensure_dirs

app = typer.Typer(add_completion=False, no_args_is_help=False)
USER_AGENT = "shellnet/0.1 (+https://github.com/) GoldenMatch case study"


def _sha256_file(path: Path, chunk: int = 1 << 16) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


@app.command()
def main(
    url: str = typer.Option(
        None,
        "--url",
        help="Direct URL to the ICIJ bundle ZIP. Falls back to $ICIJ_BUNDLE_URL.",
    ),
    sha256: str = typer.Option(
        ...,
        "--sha256",
        help="Expected SHA-256 of the downloaded ZIP (lowercase hex).",
    ),
    dest: Path = typer.Option(ICIJ_RAW, help="Where to unzip the bundle."),
    keep_zip: bool = typer.Option(False, "--keep-zip", help="Keep the ZIP after extraction."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Emit DEBUG-level logs."),
) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    ensure_dirs()
    dest.mkdir(parents=True, exist_ok=True)
    src_url = url or os.environ.get("ICIJ_BUNDLE_URL")
    if not src_url:
        typer.echo(
            "No ICIJ URL provided. Visit https://offshoreleaks.icij.org/pages/database, "
            "grab the bundle link, and pass it as --url (or export ICIJ_BUNDLE_URL)."
        )
        raise typer.Exit(code=2)

    zip_path = dest / "icij_bundle.zip"
    typer.echo(f"Downloading {src_url} → {zip_path}")
    with httpx.stream(
        "GET",
        src_url,
        headers={"User-Agent": USER_AGENT},
        timeout=300.0,
        follow_redirects=True,
    ) as r:
        r.raise_for_status()
        with zip_path.open("wb") as fh:
            for chunk in r.iter_bytes(1 << 16):
                fh.write(chunk)

    actual = _sha256_file(zip_path)
    if actual.lower() != sha256.lower():
        zip_path.unlink(missing_ok=True)
        typer.echo(
            f"Checksum mismatch.\n  expected: {sha256}\n  got:      {actual}\n"
            "Refusing to extract a bundle that didn't match its expected hash."
        )
        raise typer.Exit(code=3)
    typer.echo(f"Checksum OK ({actual[:12]}…). Extracting…")

    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(dest)
    typer.echo(f"Extracted into {dest}")

    if not keep_zip:
        zip_path.unlink(missing_ok=True)

    csvs = sorted(p.name for p in dest.glob("*.csv"))
    typer.echo(f"CSVs available: {csvs or '(none — check the bundle layout)'}")


if __name__ == "__main__":
    app()
