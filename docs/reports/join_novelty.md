# Newly surfaced cross-source joins

_Generated 2026-05-16 19:32 UTC by `scripts/render_join_novelty_report.py` from a Railway-side
build of `scripts/build_join_novelty_report.py`. See
[`docs/prior_art_comparison.md`](../prior_art_comparison.md) for what makes
these "newly surfaced" versus what ICIJ Offshore Leaks DB / OCCRP Aleph
already surface._

## Summary

| Kind | Rows | Distinct anchors | With evasion signal | With UK-disq overlap |
|---|---:|---:|---:|---:|
| ICIJ + OS + GLEIF company triples | 16 | 4 LEIs | 0 | 0 |
| DOB-confirmed OS↔UK_PSC pairs | 200 | 137 sanctioned IDs | 38 | 0 |

**Evasion signal** = `n_datasets == 1` on the sanctions overlay AND
`us_ofac_sdn` is absent — the regional-list-but-not-OFAC pattern the
overlay was designed to surface.

## 1. Company triples (ICIJ + OpenSanctions + GLEIF)

Same legal entity referenced by all three datasets. Invisible to any
single dataset's UI — ICIJ's Offshore Leaks DB doesn't show GLEIF LEIs;
OpenSanctions doesn't surface ICIJ leak provenance; GLEIF doesn't
flag sanctions status.

| ICIJ name | OS name | GLEIF name | LEI | Jurisdiction | OS list count |
|---|---|---|---|---|---|
| Altitude X2 Ltd. | Altitude X3 LTD | ALTITUDE X2 LTD. | `2138006Z57H3EJHYY303` | bm | 4 |
| VASSILIADES & CO. (MALTA) LIMITED | VASSILIADES & CO. MALTA LIMITED | VASSILIADES & CO. (MALTA) LIMITED | `213800IMQFB4XIUD2580` | mt | 5 |
| Altitude 42 Limited | Altitude X3 LTD | ALTITUDE X2 LTD. | `2138006Z57H3EJHYY303` | bm | 4 |
| Altitude X3 Ltd. | Altitude X3 LTD | ALTITUDE X2 LTD. | `2138006Z57H3EJHYY303` | bm | 4 |
| Altitude X4 Ltd. | Altitude X3 LTD | ALTITUDE X2 LTD. | `2138006Z57H3EJHYY303` | bm | 4 |
| Altitude X1 Ltd. | Altitude X3 LTD | ALTITUDE X2 LTD. | `2138006Z57H3EJHYY303` | bm | 4 |
| Altitude 15 Ltd. | Altitude X3 LTD | ALTITUDE X2 LTD. | `2138006Z57H3EJHYY303` | bm | 4 |
| Altitude 60 Ltd. | Altitude X3 LTD | ALTITUDE X2 LTD. | `2138006Z57H3EJHYY303` | bm | 4 |
| Altitude 51 Ltd. | Altitude X3 LTD | ALTITUDE X2 LTD. | `2138006Z57H3EJHYY303` | bm | 4 |
| Altitude 50 Ltd. | Altitude X3 LTD | ALTITUDE X2 LTD. | `2138006Z57H3EJHYY303` | bm | 4 |
| Altitude 45 Ltd. | Altitude X3 LTD | ALTITUDE X2 LTD. | `2138006Z57H3EJHYY303` | bm | 4 |
| Altitude 41 Ltd. | Altitude X3 LTD | ALTITUDE X2 LTD. | `2138006Z57H3EJHYY303` | bm | 4 |
| Altitude 35 Ltd. | Altitude X3 LTD | ALTITUDE X2 LTD. | `2138006Z57H3EJHYY303` | bm | 4 |
| Hong Kong Jinzhao Resources Limited | HONG KONG INTERTRADE COMPANY | Hong Kong Linear Growth Limited | `300300HHTAWFTXYVVI58` | hk | 9 |
| MERCHANT CHARTER LIMITED | Merchant Supreme Co., Ltd. | MERCHANTILE ASSET LIMITED | `52990053RSLBKN4VFX85` | vg | 4 |
| Altitude Air Services Limited | Altitude X3 LTD | ALTITUDE X2 LTD. | `2138006Z57H3EJHYY303` | bm | 4 |


### Jurisdiction distribution

| Jurisdiction | Triples |
|---|---:|
| bm | 13 |
| hk | 1 |
| vg | 1 |
| mt | 1 |


## 2. DOB-confirmed sanctioned officer pairs (OS sanctions ↔ UK PSC)

Sanctioned persons whose name + date-of-birth-year match a UK PSC officer
record. Filtered to the **evasion signal** subset (sanctioned by at least
one government list but absent from OFAC SDN) — top 50 shown,
parquet has the full 38 rows.

| UK PSC officer | OS sanctioned name | DOB | Country | Sanction lists | Name score |
|---|---|---|---|---|---|
| Pavel Maslovsky | Pavel Maslovsky | 1956-12 | ru | ua_nsdc_sanctions | 1.000 |
| Pavel Maslovsky | Pavel Maslovsky | 1956-12 | ru | ua_nsdc_sanctions | 1.000 |
| Pavel Maslovsky | Pavel Maslovsky | 1956-12 | ru | ua_nsdc_sanctions | 1.000 |
| Victor Pichugov | Viktor Pichugov | 1958-05 | cy | ua_nsdc_sanctions | 0.977 |
| Leonid Boguslavskiy | Leonid Boguslavsky | 1951-06 | ru | ua_nsdc_sanctions | 0.962 |
| Elena Kostikova | Elena Strokova | 1976-03 | ru | ua_nsdc_sanctions | 0.950 |
| Konstantin Ulanov | Konstantinov Nikolai | 1985-08 | ru | ua_nsdc_sanctions | 0.946 |
| Konstantin Ulanov | Konstantinov Nikolai | 1985-08 | ru | ua_nsdc_sanctions | 0.946 |
| Vladimir Poliakov | Vladimir Pozdnyakov | 1946-05 | ru | ua_nsdc_sanctions | 0.939 |
| Elena Korneeva | Elena SMIRNOVA | 1981-10 | ru | gb_fcdo_sanctions | 0.927 |
| Mikhail Sarkisiants | Mikhail Serdyuk | 1976-03 | ru | ua_nsdc_sanctions | 0.904 |
| Olga Gruzdeva | Gruzdeva Olga | 1974-06 | ru | ua_nsdc_sanctions | 0.900 |
| Igor Iakovlev | Iakovlev Igor | 1965-10 | ru | ua_nsdc_sanctions | 0.900 |
| Igor Fedorov | Fedorov Igor | 1966-01 | ru | ua_nsdc_sanctions | 0.900 |
| Mr Konstantinos Antoniou | Antoniou Konstantinos | 1961-04 | cy | ua_nsdc_sanctions | 0.883 |
| Mr. Konstantinos Antoniou | Antoniou Konstantinos | 1961-04 | cy | ua_nsdc_sanctions | 0.883 |
| Mr Konstantinos Antoniou | Antoniou Konstantinos | 1961-04 | cy | ua_nsdc_sanctions | 0.883 |
| Mr Konstantinos Antoniou | Antoniou Konstantinos | 1961-04 | cy | ua_nsdc_sanctions | 0.883 |
| Mr Konstantinos Antoniou | Antoniou Konstantinos | 1961-04 | cy | ua_nsdc_sanctions | 0.883 |
| Mr Pavel Astafurov | Astafurov Pavel | 1987-09 | ru | ua_nsdc_sanctions | 0.877 |
| Mr Pavel Fedorov | Fedorov Pavel | 1984-02 | ru | ua_nsdc_sanctions | 0.874 |
| Ms. Ekaterina Ronami | Ronami Ekaterina | 1988-08 | ru | ua_nsdc_sanctions | 0.860 |
| Mrs Ekaterina Nosik | Ronami Ekaterina | 1988-04 | ru | ua_nsdc_sanctions | 0.852 |
| Mr Konstantin Dobrynin | Konstantin Dobrynin | 1976-11 | ru | ua_nsdc_sanctions | 0.851 |
| Mr Leonid Boguslavsky | Leonid Boguslavsky | 1951-06 | ru | ua_nsdc_sanctions | 0.850 |
| Mr Leonid Boguslavsky | Leonid Boguslavsky | 1951-06 | ru | ua_nsdc_sanctions | 0.850 |
| Mr Leonid Boguslavsky | Leonid Boguslavsky | 1951-06 | ru | ua_nsdc_sanctions | 0.850 |
| Maxim Novichkov | Maxim / Maksim Volkov | 1975-10 | ru | ua_nsdc_sanctions | 0.847 |
| Mr Valeriy Markelov | Markelov Valerii | 1965-10 | ru | ua_nsdc_sanctions | 0.843 |
| Mr Petr Kondrashev | Pyotr Kondrashev | 1949-07 | ru | ua_nsdc_sanctions | 0.841 |
| Iurii Andreev | Andreev Vitalii | 1985-08 | ru | ua_nsdc_sanctions | 0.841 |
| Iurii Andreev | Andreev Vitalii | 1985-08 | ru | ua_nsdc_sanctions | 0.841 |
| Mr. Aleksei Kudinov | Klimov Aleksei | 1979-01 | ru | ua_nsdc_sanctions | 0.840 |
| Mr Aleksei Chua | Maruev Aleksei | 1977-11 | ru | ua_nsdc_sanctions | 0.840 |
| Iuliia Volkova | Vetrova Iuliia | 1984-08 | ru | ua_nsdc_sanctions | 0.840 |
| Mr Aleksei Zhukov | Maruev Aleksei | 1977-10 | ru | ua_nsdc_sanctions | 0.839 |
| Chrysostomos Sofokleous | Sophocleous Chrysostomos | 1969-09 | cy | ua_nsdc_sanctions | 0.838 |
| Maxim Miroshkin | Maxim / Maksim Volkov | 1975-09 | ru | ua_nsdc_sanctions | 0.838 |


## Caveats

- Person matches use **year-only** DOB equality (most UK PSC DOB values
  are month+year). Full date-equal would be stronger but loses recall.
- Name matching uses string similarity; transliteration variants of
  Russian/Ukrainian names produce both real matches (Maslovsky ≡
  Маслоўскі) and false positives (different surnames sharing a
  first name + DOB year). Manual review of the top 50 is recommended
  before any investigative use.
- "Evasion signal" is a *prior* not a verdict — an entity on UA-NSDC
  but not OFAC may be a legitimate Ukrainian-specific listing rather
  than a US compliance gap.
- The 16-triple count for companies is small because GLEIF coverage is
  thinnest among the three sources; the joinable subset is what GLEIF
  carries.

## Reproduce

```bash
# Railway side (produces the two output files on the /data volume):
just job-run build_join_novelty_report
just job-fetch processed/join_novelty.parquet data/processed/
just job-fetch processed/join_novelty_summary.json data/processed/

# Local side (renders this markdown):
uv run python scripts/render_join_novelty_report.py \
    --parquet data/processed/join_novelty.parquet \
    --summary data/processed/join_novelty_summary.json \
    --out docs/reports/join_novelty.md
```

Or trigger the GH Actions workflow `render-novelty-report.yml` which
does both steps and opens a PR with the regenerated report.
