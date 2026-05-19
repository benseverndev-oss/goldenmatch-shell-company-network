"""Rank clusters by where an investigator should look next.

    uv run python scripts/rank_by_attention.py

Reads the investigative-value ranking parquet produced by
``scripts/rank_by_investigative_value.py``, optionally joins the
defensibility ranking parquet from ``scripts/rank_clusters.py``, and
writes:

  * ``cluster_attention_ranking.md`` — the full leaderboard with the
    six attention components and a next-action hint per cluster.
  * ``cluster_attention_ranking.parquet`` — the same as a parquet for
    downstream tooling.
  * ``cluster_next_actions.md`` — a diversity-filtered top-N "what to
    investigate next" queue (one cluster per ``kind_tag`` until the
    cap is reached).

If the investigative-value parquet isn't present, this script can be
pointed at a saved one via ``--investigative-parquet``.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

import polars as pl
import typer
from dotenv import load_dotenv

from shellnet.investigations.attention import (
    rank_by_attention,
    render_attention_ranking_markdown,
    render_next_actions_markdown,
    select_diverse_queue,
)

load_dotenv()

app = typer.Typer(add_completion=False, no_args_is_help=False)
log = logging.getLogger(__name__)


def _read_required_parquet(path: Path, what: str) -> pl.DataFrame:
    if not path.exists():
        raise typer.BadParameter(
            f"{what} parquet not found at {path}. Run scripts/rank_by_investigative_value.py first."
        )
    return pl.read_parquet(path)


def _read_optional_parquet(path: Path | None) -> pl.DataFrame | None:
    if path is None or not path.exists():
        return None
    try:
        return pl.read_parquet(path)
    except Exception as exc:  # noqa: BLE001
        log.warning("could not read %s: %s", path, exc)
        return None


@app.command()
def main(
    investigative_parquet: Path = typer.Option(
        Path("/data/reports/generated/cluster_investigative_ranking.parquet"),
        "--investigative-parquet",
        help="Output of scripts/rank_by_investigative_value.py.",
    ),
    rank_parquet: Path = typer.Option(
        Path("/data/reports/generated/cluster_ranking.parquet"),
        "--rank-parquet",
        help="Optional defensibility ranking parquet (joined in if present).",
    ),
    out_md: Path = typer.Option(
        Path("/data/reports/generated/cluster_attention_ranking.md"),
        "--out-md",
        help="Where to write the attention leaderboard Markdown.",
    ),
    queue_md: Path = typer.Option(
        Path("/data/reports/generated/cluster_next_actions.md"),
        "--queue-md",
        help="Where to write the diversity-filtered next-actions queue.",
    ),
    top_n: int = typer.Option(50, "--top-n", help="Rows in the leaderboard."),
    queue_size: int = typer.Option(10, "--queue-size", help="Rows in the next-actions queue."),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    investigative_df = _read_required_parquet(investigative_parquet, "investigative-value ranking")
    defensibility_df = _read_optional_parquet(rank_parquet)
    log.info(
        "loaded investigative_df rows=%d; defensibility=%s",
        investigative_df.height,
        "yes" if defensibility_df is not None else "missing",
    )

    ranking = rank_by_attention(investigative_df, defensibility_df=defensibility_df)
    log.info(
        "scored %d cluster(s); top attention=%.2f",
        ranking.height,
        ranking["attention_score"].max() if ranking.height else 0.0,
    )

    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(
        render_attention_ranking_markdown(ranking, top_n=top_n, generated_at=datetime.now(UTC)),
        encoding="utf-8",
    )
    log.info("wrote %s", out_md)
    ranking.write_parquet(out_md.with_suffix(".parquet"))
    log.info("wrote %s", out_md.with_suffix(".parquet"))

    queue = select_diverse_queue(ranking, top_n=queue_size)
    queue_md.parent.mkdir(parents=True, exist_ok=True)
    queue_md.write_text(
        render_next_actions_markdown(queue, generated_at=datetime.now(UTC)),
        encoding="utf-8",
    )
    log.info("wrote %s (queue size %d)", queue_md, queue.height)
    print(str(out_md))


if __name__ == "__main__":
    app()
