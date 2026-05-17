# Temporal patterns — incorporation / dissolution dynamics

_Generated 2026-05-17 19:03 UTC from `processed/temporal_*.parquet`. The dossier
pipeline is structural and static; this report covers the time
dimension._

## Why this report exists

ICIJ leaks carry `incorporation_date` for 814,344 entities
(814,344 total). 96.8% have it; 42% also carry a
`dissolution_date`. That's enough to surface three temporal signatures
the static-graph reports can't see.

## 1. Resurrection pattern

> An entity dissolves, then a new entity is incorporated at the same
> normalized address within a 730-day window. The shell-network's
> "we got named in a leak, dissolve and reincorporate" move.

| Metric | Value |
|---|---:|
| Resurrection pairs found | **34,260** |
| Median gap (dissolve → re-incorporate) | 312 days |
| Top-N written | 500 |

### Tightest resurrections (smallest gap)

| Old entity | Dissolved | New entity | Re-incorporated | Gap (days) | Jurisdiction |
|---|---|---|---|---:|---|
| SEFFARD OVERSEAS, S.A. | 1986-02-27 | APADANA S.A. | 1986-02-28 | 1 | — → — |
| ALTONA FASHION CORPORATION | 1990-01-04 | NUBEC INVESTMENTS CORP. | 1990-01-05 | 1 | — → — |
| LYRA ENTERPRISES LLC | 2009-10-01 | CONSTANCE OVERSEAS LLC | 2009-10-02 | 1 | — → — |
| FORTEX SERVICES LLC | 2009-10-01 | CONSTANCE OVERSEAS LLC | 2009-10-02 | 1 | — → — |
| ASRI Holding B.V. | 2011-06-29 | ASRI Services Inc. | 2011-06-30 | 1 | — → — |
| OPEN CONCORDS INVESTMENTS INC. | 2012-07-15 | CANA GROUP LIMITED | 2012-07-16 | 1 | — → — |
| TENCLEM S.A. | 1982-03-10 | KEG INTERNATIONAL SERVICES INC. | 1982-03-11 | 1 | — → — |
| SALVA CORPORATION | 1985-02-28 | SUNSET GROUP INCORPORATED | 1985-03-01 | 1 | — → — |
| DUNKELD INVESTMENTS LIMITED | 1996-04-30 | ASHLAWN FINANCE LIMITED | 1996-05-01 | 1 | vg → vg |
| VALLIANT TRADING LIMITED | 1996-07-02 | ELDERBERRY WORLDWIDE S.A. | 1996-07-03 | 1 | — → vg |


## 2. Burst incorporations

> ≥5 entities incorporated at the same normalized address
> within a 30-day window. Coordinated registration waves —
> formation-agent batches, scheme launches, or sanctions-driven flight.

| Metric | Value |
|---|---:|
| Address×window bursts found | **1,189** |
| Largest single burst | 5 entities |
| Top-N written | 500 |

### Densest bursts (smallest span for 5 entities)

| Address | Span (days) | Jurisdiction | Sample window |
|---|---:|---|---|
| `2 millewee l 7257 walferdange luxembourg city luxembourg` | 0 | vg | 2012-01-16 → 2012-01-16 |
| `91 2 2nd floor wireless road lumpini pathumwan bangkok thailand 10330` | 0 | vg | 2010-10-21 → 2010-10-21 |
| `alfaserve consultants limited 6 neoptolemos street p o box 28530 2080 nicosia cy` | 0 | — | 2003-06-25 → 2003-06-25 |
| `alpha consulting limited suite 1 second floor sound vision house francis rachel ` | 0 | vg | 2012-01-18 → 2012-01-18 |
| `american corporate services inc 2076 16th avenue suite a san francisco ca 94116 ` | 0 | — | 2000-04-06 → 2000-04-06 |
| `amond smith schipok str 9 26 bldg 1 entrance 3 office 1 moscow 115054 russia sen` | 0 | — | 2004-05-19 → 2004-05-19 |
| `amtrade securities corp c o egs holding a s yildiz posta caddesi dedeman ticaret` | 0 | vg | 2000-01-04 → 2000-01-04 |
| `andreas s petrou law office 2 romanou street tlais tower 6th floor nicosia 1070 ` | 0 | — | 2001-02-23 → 2001-02-23 |
| `apex trust company limited p o box 129 2nd floor commercial house commercial str` | 0 | — | 1988-05-10 → 1988-05-10 |
| `apolloni advisor via vittorio veneto 146 00187 roma italia` | 0 | — | 2011-06-30 → 2011-06-30 |


## 3. Long-lived anchors

> Entities incorporated > 15 years ago, still active (no
> dissolution date), at addresses also hosting many recently-incorporated
> shells. Old anchor entities for shell-rotation patterns.

| Metric | Value |
|---|---:|
| Long-lived anchors found | **0** |
| Top-N written | 0 |

### Top anchors by recent-activity at shared address

| Anchor entity | Address | Jurisdiction | Incorporated | Recent at addr |
|---|---|---|---|---:|


## What this report does NOT prove

1. **Address normalization is imperfect.** Two slightly-different
   address strings can refer to the same physical location; burst /
   resurrection counts are lower bounds.
2. **No officer-level temporal join.** A more powerful "resurrection"
   would require the SAME officer or beneficial owner to appear in
   the new entity. Currently we only key on address.
3. **No cross-leak normalization.** Panama Papers and Pandora Papers
   may record the same physical office with different ICIJ-internal
   address IDs. Both patterns would be stronger if address dedup were
   global.
4. **Recent-activity threshold is hard-coded** (>=2020 incorporations
   for the long-lived-anchor count). Move the threshold and the
   ranking shifts.

## Reproduce

```bash
just job-run build_temporal_patterns
for p in processed/temporal_resurrections.parquet \
         processed/temporal_bursts.parquet \
         processed/temporal_long_lived.parquet \
         processed/temporal_patterns_summary.json; do
    just job-fetch "$p" docs/reports/data/
done

uv run python scripts/render_temporal_patterns.py \
    --resurrections docs/reports/data/temporal_resurrections.parquet \
    --bursts docs/reports/data/temporal_bursts.parquet \
    --anchors docs/reports/data/temporal_long_lived.parquet \
    --summary docs/reports/data/temporal_patterns_summary.json \
    --out docs/reports/temporal_patterns.md
```

Or trigger `.github/workflows/build-temporal-patterns.yml`.
