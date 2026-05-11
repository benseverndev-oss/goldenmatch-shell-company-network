# v1 vs v2 list-match — eval against hand-labels

Labels: `data\labels\marginal_v1.csv` (300 pairs across 4 buckets)
v1 run: `f40d7099-44c6-4282-9925-036dc4307951` (20297 matched pairs)
v2 run: `a01cce05-896b-4d19-911c-b3efe7b5f56f` (5630 matched pairs)

**Caveats:** the labelled set was *deliberately* stratified to oversample the marginal score bands. Per-bucket numbers below characterise each band; do not multiply them by total run size to estimate overall precision without using the band-distribution weighting in the final section.

## Per-bucket precision/recall (strict: unsure dropped)

| bucket | run | tp | fp | fn | precision | recall | f1 | unsure-in-run |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| v1_dropped | v1 | 6 | 81 | 0 | 0.069 | 1.000 | 0.129 | 13 |
| v1_dropped | v2 | 0 | 0 | 6 | 0.000 | 0.000 | 0.000 | 0 |
| v2_marginal | v1 | 41 | 43 | 0 | 0.488 | 1.000 | 0.656 | 16 |
| v2_marginal | v2 | 41 | 43 | 0 | 0.488 | 1.000 | 0.656 | 16 |
| perfect_sanity | v1 | 50 | 0 | 0 | 1.000 | 1.000 | 1.000 | 0 |
| perfect_sanity | v2 | 50 | 0 | 0 | 1.000 | 1.000 | 1.000 | 0 |
| v2_borderline_class | v1 | 11 | 23 | 0 | 0.324 | 1.000 | 0.489 | 15 |
| v2_borderline_class | v2 | 11 | 24 | 0 | 0.314 | 1.000 | 0.478 | 15 |

## Per-bucket precision/recall (generous: unsure → match)

| bucket | run | tp | fp | fn | precision | recall | f1 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| v1_dropped | v1 | 19 | 81 | 0 | 0.190 | 1.000 | 0.319 |
| v1_dropped | v2 | 0 | 0 | 19 | 0.000 | 0.000 | 0.000 |
| v2_marginal | v1 | 57 | 43 | 0 | 0.570 | 1.000 | 0.726 |
| v2_marginal | v2 | 57 | 43 | 0 | 0.570 | 1.000 | 0.726 |
| perfect_sanity | v1 | 50 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| perfect_sanity | v2 | 50 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| v2_borderline_class | v1 | 26 | 23 | 0 | 0.531 | 1.000 | 0.693 |
| v2_borderline_class | v2 | 26 | 24 | 0 | 0.520 | 1.000 | 0.684 |

## Headline: v2 precision in the labelled set, by band

Pairs sampled FROM v2 (i.e. v2 kept them). Precision = label-confirmed match / (match + no_match).

| v2 band | label-match | label-no_match | label-unsure | strict-precision | generous-precision |
| --- | ---: | ---: | ---: | ---: | ---: |
| perfect | 58 | 0 | 0 | 1.000 | 1.000 |
| high | 14 | 33 | 10 | 0.298 | 0.421 |
| borderline | 30 | 34 | 21 | 0.469 | 0.600 |

## Estimated v1 overall precision (band-weighted)

Same method as v2 below. v1 kept the entire 0.85+ range, including the 0.85–0.92 band that v2 dropped — that's where v1's precision tanks.

| band | size | sample-precision-strict | sample-precision-generous | est_tp_strict | est_tp_generous |
| --- | ---: | ---: | ---: | ---: | ---: |
| perfect | 5192 | 1.000 | 1.000 | 5192 | 5192 |
| high | 850 | 0.298 | 0.421 | 253 | 358 |
| borderline | 14255 | 0.240 | 0.380 | 3421 | 5423 |
| **total** | **20297** | | | **8866** | **10973** |

**Estimated v1 overall precision: 43.7% strict / 54.1% generous.**

## Estimated v2 overall precision (band-weighted)

Combines the per-band precision from the labelled sample with the band sizes in the published v2 run. **This is an estimate**, not a strict eval — only the labelled subset is verified.

| band | size | sample-precision-strict | sample-precision-generous | est_tp_strict | est_tp_generous |
| --- | ---: | ---: | ---: | ---: | ---: |
| perfect | 5123 | 1.000 | 1.000 | 5123 | 5123 |
| high | 263 | 0.298 | 0.421 | 78 | 111 |
| borderline | 244 | 0.469 | 0.600 | 114 | 146 |
| **total** | **5630** | | | **5316** | **5380** |

**Estimated v2 overall precision: 94.4% strict / 95.6% generous.**

## Headline comparison

| metric | v1 | v2 | delta |
| --- | ---: | ---: | ---: |
| matched pairs | 20,297 | 5,630 | -14,667 |
| est. precision (strict) | 43.7% | 94.4% | +50.7pp |
| est. precision (generous) | 54.1% | 95.6% | +41.5pp |
| est. true positives (strict) | 8866 | 5316 | -3551 |

Read: v2 cut the matched pair count by ~73% with a per-pair precision lift of ~50 percentage points. The estimated TP delta above is conservative — see caveat below.

**Caveat on the v1 estimate.** The 'borderline' band (0.85–0.95) is half-cut-by-v2 (the 0.85–0.92 sub-band, ~14,011 pairs, sampled by `v1_dropped` at 6.9% strict precision) and half-kept-by-v2 (the 0.92–0.95 sub-band, ~244 pairs, sampled by `v2_marginal` + `v2_borderline_class` at ~47% strict precision). The v1-borderline estimate above blends those, which inflates v1's estimated TPs in the cut-by-v2 sub-band. A finer split would push v1's TP count down and *increase* the precision-lift signal — so the headline 'v2 is materially more precise' is conservative.

## v1 → v2 transition: what changed

- 100 v1_dropped pairs sampled. In v1: 100. In v2: 0 (expected 0 — v2's threshold raise removed these).
- Labels: 6 match, 81 no_match, 13 unsure.
- Recall cost in 0.85–0.92 band: at least 6% (strict), at most 19% (generous).

- Total labelled pairs in v1 only: 100; in both: 200; in v2 only: 0.