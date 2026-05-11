# marginal_v1.csv — labelling methodology

This file documents how the `label` and `rationale` columns were filled
in for the `v1_dropped` bucket of `marginal_v1.csv` (100 pairs, IDs
P0001–P0100). The other three buckets (`v2_marginal`, `perfect_sanity`,
`v2_borderline_class`) are still unlabelled at the time of writing.

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

For the 100 v1_dropped pairs:

| label | count |
| --- | ---: |
| no_match | 81 |
| match | 6 |
| unsure | 13 |

Read: v2's threshold raise was correct on at least 81% of these pairs,
and possibly cost recall on at most 19% (the 6 `match` plus the 13
`unsure` if all `unsure` are treated as `match`). The 6 confirmed
`match` cases share a single pattern — identical name + same
jurisdiction with diverging address rows — which suggests a future
iteration should weight name-equality more strongly when the address
columns conflict, rather than averaging them.
