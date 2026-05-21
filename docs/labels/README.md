# SEC ↔ ICIJ bridge labels

Hand-labelled ground truth for the bridges produced by
``scripts/bridge_sec_icij_by_name.py``. Used by Phase 17a's filter
to verify large-cap-issuer drops are correct, and by Phase 17c to
fine-tune a cross-encoder.

## Method

Each row pairs one SEC EDGAR filer with one ICIJ Offshore Leaks
entity that matched it on normalised name. Verdicts:

| Label | Meaning |
|---|---|
| `real` | Strong evidence the two records refer to the same legal entity or related vehicles in the same brand. Should remain a bridge. |
| `false_positive` | Same name purely by coincidence; the two records refer to different entities. Should be dropped. |
| `uncertain` | Could go either way; resolving needs jurisdiction + officer-overlap signal we don't have today. Currently kept as a bridge with a caveat in the report. |

## Why this exists

The exact-name match (the production default) catches ~30 bridges
including substantive offshore-vehicle matches (EE Holdings Ltd,
Apeiron Investment Group, Rhea Marine, Ocean Capital).

Enabling `--use-goldenmatch` raised the count to ~1,500 but
introduced loud false positives — Royal Bank of Canada, Delta Air
Lines, Equitable Holdings — that the fuzzy matcher can't
disambiguate at the matcher level. The disambiguation signal lives
in SEC EDGAR submissions metadata: SIC code, filer category,
US-exchange ticker. Phase 17a wires that in.

This labels file captures the verdict for each fuzzy-bridge
candidate from a recent GoldenMatch-on run so we can measure:

1. How many bridges Phase 17a's filter correctly drops (precision).
2. How many real bridges Phase 17a accidentally drops (recall).
3. The residual ambiguity pile that needs officer-overlap (Phase 17b).

## Caveats

- These labels are preliminary judgments based on name + context, not
  hand-verified against EDGAR filings and ICIJ pages. Treat them as
  triage seed labels for Phase 17c, not as ground truth for a paper.
- `uncertain` is the common case for fuzzy matches and is honest.
  Resolving them needs evidence we don't currently fetch — officer
  rosters, beneficial-owner declarations, jurisdictional address
  lookups.
- The labels DO NOT make any allegation about wrongdoing. A
  `real` label means "these two records refer to the same legal
  entity or related vehicles in the same brand", nothing more.
