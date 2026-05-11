"""Stream the ICIJ Offshore Leaks zip up to the shellnet-job service.

Usage:
    SHELLNET_JOB_URL=https://shellnet-job.up.railway.app \
    SHELLNET_JOB_TOKEN=... \
    uv run python scripts/upload_icij.py "C:/path/to/full-oldb.LATEST.zip"

We use ``httpx`` with a streamed multipart body so we don't load the
whole zip into memory.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import httpx
import typer

app = typer.Typer(add_completion=False, no_args_is_help=True)


@app.command()
def main(
    zip_path: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True),
    url: str = typer.Option(None, "--url", help="Base URL. Falls back to $SHELLNET_JOB_URL."),
    token: str = typer.Option(None, "--token", help="Bearer token. Falls back to $SHELLNET_JOB_TOKEN."),
    timeout: float = typer.Option(1800.0, "--timeout", help="Request timeout in seconds."),
) -> None:
    base = (url or os.environ.get("SHELLNET_JOB_URL", "")).rstrip("/")
    tok = token or os.environ.get("SHELLNET_JOB_TOKEN")
    if not base:
        typer.echo("Set --url or SHELLNET_JOB_URL")
        raise typer.Exit(2)
    if not tok:
        typer.echo("Set --token or SHELLNET_JOB_TOKEN")
        raise typer.Exit(2)

    size = zip_path.stat().st_size
    typer.echo(f"Uploading {zip_path.name} ({size / 1e6:.1f} MB) -> {base}/upload-zip")

    with zip_path.open("rb") as fh:
        files = {"file": (zip_path.name, fh, "application/zip")}
        with httpx.Client(timeout=timeout) as client:
            r = client.post(
                f"{base}/upload-zip",
                files=files,
                headers={"Authorization": f"Bearer {tok}"},
            )
    if r.status_code >= 400:
        typer.echo(f"FAILED [{r.status_code}]: {r.text}", err=True)
        sys.exit(1)
    typer.echo(r.json())


if __name__ == "__main__":
    app()
