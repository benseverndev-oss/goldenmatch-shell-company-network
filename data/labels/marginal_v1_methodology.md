# marginal_v1.csv — labelling methodology

This file documents how the `label` and `rationale` columns were filled
in for `marginal_v1.csv` (300 pairs across four buckets, IDs P0001–P0300).
All 300 are now labelled.

## Who labelled

Claude (Anthropic), acting as a research assistant on this case study,
labelled all 100 v1_dropped rows in one session. **These are
AI-assisted research labels, not human ground truth.** The eval that
consumes them must say so.

## Why the v1_dropped bucket first

The most leveraged validation question is: did the v1 → v2 config
tighten remove false positives (precision gain), or real matches
(recall loss)? The 100 pairs in this bucket are exactly the ones v1
kept and v2 dropped — labelling them gives the answer.

## Methodology

For each pair, the labeller (Claude) inspected the two names and
jurisdictions and applied the following rules:

* **`match`** — the two records refer to the same legal entity. Used
  almost exclusively for cases where the normalized names were
  identical (case/punctuation differences only) AND the two records
  shared a jurisdiction. The score in these cases sat below v2's 0.92
  threshold purely because the address-column score component was
  depressed by two different point-in-time address captures across
  two ICIJ leaks of the same company.

* **`no_match`** — the two records refer to distinct legal entities.
  Used when the second token of the name diverged in a way that
  implied a different business (different industry, different fund
  series, different family beneficiary, etc.) even though they
  shared a leading word. Most rows in this bucket fell here — the
  matcher was over-rewarding shared leading tokens via
  `jaro_winkler`, which is exactly what the v2 switch to
  `token_sort` was designed to fix.

* **`unsure`** — naming pattern strongly suggests a related entity
  pair (parent / subsidiary / sister fund / family business) but
  there's no public-source signal in front of the labeller to
  confirm whether they share a single legal entity or are
  related-but-distinct. Examples: `STAFFCO MALTA HOLDING` vs
  `STAFFCO MALTA TREASURY` are almost certainly sister entities
  in one corporate group, but they're still distinct legal
  entities, so the "match" label depends on whether you treat
  same-corporate-group as match or only same-legal-entity as match.

## Caveats for the eval

* For ~14% of the rows the labeller marked `unsure`. The eval should
  report two numbers: a strict reading (unsure → drop) and a generous
  reading (unsure → match) so the spread is visible.

* Public-source verification was not done per row — the labeller
  relied on name-pattern inspection plus background knowledge of
  well-known entities (e.g., Pacific Basin Shipping, TransAtlantic
  Petroleum, Sequoia Capital, VinaCapital, Renaissance Reinsurance).
  An independent reviewer should spot-check ~10–20 rows against
  registries before publishing.

* Labels were not reviewed by an independent human at the time of
  commit. Treat all findings derived from this label set as
  preliminary; flag for human review before any external publication.

## Result snapshot

| bucket | match | no_match | unsure | total |
| --- | ---: | ---: | ---: | ---: |
| `v1_dropped` | 6 | 81 | 13 | 100 |
| `v2_marginal` | 41 | 43 | 16 | 100 |
| `perfect_sanity` | 50 | 0 | 0 | 50 |
| `v2_borderline_class` | 11 | 24 | 15 | 50 |
| **Total** | **108** | **148** | **44** | **300** |

### Reading the four buckets

* **v1_dropped** — v2's threshold raise (0.85 → 0.92) removed these.
  81% confirmed `no_match` means v2 was right to drop the bulk. 6%
  confirmed `match` (all identical-name + same-jurisdiction pairs whose
  scores were depressed by diverging address rows from two leak
  captures) is the recall cost. Net: a precision win, with one
  addressable failure mode.

* **v2_marginal** — v2 *kept* these in the 0.92–0.97 band. 41% match,
  43% no_match, 16% unsure. v2's residual precision in the still-marginal
  band is **41% strict / 57% generous**. The dominant FP pattern is
  *sequential sub-vehicles*: PA Grand Opportunity I/II/III, Atlas Senior
  Loan Fund III/IV, Mapeley Beta Acquisition Co (1)/(4)/(5)/(6), Golub
  Capital Partners CLO N, Windsor Properties (N), CVP Cascade CLO N.
  These share heavy token overlap and the same jurisdiction even after
  the token_sort + 0.92 fix.

* **perfect_sanity** — 50/50 match. The perfect band (score ≥ 0.99)
  has ~100% precision on this sample. No surprises.

* **v2_borderline_class** — heuristic-marginal v2 keeps (jur_close +
  jur_loose). 11 match, 24 no_match, 15 unsure. v2's precision in this
  heuristic-flagged sub-tier is **22% strict / 52% generous**. The
  heuristic class signal is doing real work; an additional filter that
  drops these would meaningfully improve precision.

### Failure modes worth flagging for the next config iteration

1. **Sequential sub-vehicles in the same jurisdiction.** `PA Grand
   Opportunity II Limited` vs `PA Grand Opportunity Limited`,
   `Mapeley Beta Acquisition Co (4) Limited` vs `(1)`, etc. The
   `(N)` and roman-numeral suffixes are highly informative and a
   token-sort name scorer doesn't penalize their absence. A scorer
   that treats numeric / parenthetical suffixes as required-equal
   (or strongly weighted) would catch this class.

2. **CLO Trust vs Ltd recording artifact.** Multiple ICIJ entries
   record one CLO as both `Foo CLO Ltd` and `Foo CLO Ltd. Trust`.
   These could be the same legal entity recorded twice or distinct
   trust + fund vehicles — the labelling marked these `unsure` in
   the absence of registry confirmation. Worth a normalization rule
   that strips trailing `Trust` and treats those rows as duplicates
   of the corresponding `Ltd` row.

3. **Refinanced CLO `(M)-R` suffix.** `Golub Capital Partners CLO
   21(M)` vs `21(M)-R`. Same underlying CLO, refinanced. Probably
   the same legal entity post-refi but possibly distinct vehicles.

4. **Address divergence on identical names.** The 6 confirmed
   `match` cases in `v1_dropped` all had identical names +
   jurisdiction but the address-component score pulled the total
   below 0.92. A weighted matchkey that doesn't penalize for
   address divergence when name is exact would recover these.
