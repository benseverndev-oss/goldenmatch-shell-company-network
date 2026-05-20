"""Ad-hoc CLI for the national-registry adapters.

Usage::

    uv run python scripts/lookup_registry.py --registry brreg_norway --id 974760673
    uv run python scripts/lookup_registry.py --registry inpi_france --id 552120222
    uv run python scripts/lookup_registry.py --registry brreg_norway --search "telenor"
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
_REPO_ROOT = _HERE.parents[1]
sys.path.insert(0, str(_REPO_ROOT / "src"))

from shellnet.registries.brreg_norway import BrregNorwayAdapter  # noqa: E402
from shellnet.registries.cro_ireland import CroIrelandAdapter  # noqa: E402
from shellnet.registries.inpi_france import InpiFranceAdapter  # noqa: E402
from shellnet.registries.kvk_netherlands import KvkNetherlandsAdapter  # noqa: E402

_ADAPTERS = {
    "brreg_norway": BrregNorwayAdapter,
    "inpi_france": InpiFranceAdapter,
    "cro_ireland": CroIrelandAdapter,
    "kvk_netherlands": KvkNetherlandsAdapter,
}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--registry", required=True, choices=sorted(_ADAPTERS))
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--id", help="national identifier to look up")
    g.add_argument("--search", help="name-based search query")
    p.add_argument("--limit", type=int, default=10)
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    adapter = _ADAPTERS[args.registry]()
    if args.id:
        hit = adapter.lookup(args.id)
        if hit is None:
            print(json.dumps({"found": False, "identifier": args.id}, indent=2))
            return 1
        print(json.dumps(hit.to_dict(), indent=2, default=str, ensure_ascii=False))
        return 0
    hits = adapter.search(args.search, limit=args.limit)
    print(json.dumps([h.to_dict() for h in hits], indent=2, default=str, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
