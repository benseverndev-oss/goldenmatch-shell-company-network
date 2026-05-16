# Newly surfaced cross-source joins

_Generated 2026-05-16 20:45 UTC by `scripts/render_join_novelty_report.py` from a Railway-side
build of `scripts/build_join_novelty_report.py`. See
[`docs/prior_art_comparison.md`](../prior_art_comparison.md) for what makes
these "newly surfaced" versus what ICIJ Offshore Leaks DB / OCCRP Aleph
already surface._

## Summary

The headline numbers are **distinct anchors** — the underlying entity
or sanctioned-person being surfaced, not the number of rows. Rows are
inflated by duplicate variants of the same entity (e.g. ICIJ filings
under multiple spellings of the same shell company name).

| Kind | Anchors | (Rows) | Notes |
|---|---:|---:|---|
| 1. ICIJ + OS + GLEIF company triples | **4 LEIs** | 16 | 3-source company anchors |
| 2. DOB-confirmed OS↔UK_PSC pairs | **137 sanctioned IDs** | 200 | 38 with evasion signal |
| 3. ICIJ↔UK_PSC direct pairs (filtered) | **111 ICIJ uids** | 166 | same-country, ≥3-token names, score ≥ 0.95 |
| 4. Rare multi-source officer names | 200 names | 200 | max ≤ 2 per source, ≥ 3 tokens |
| 5. UK disqualified-director cross-refs | 7 matches | 7 | ICIJ + GLEIF only (UK PSC dominated by name collisions) |

**Evasion signal** = `n_datasets == 1` on the sanctions overlay AND
`us_ofac_sdn` is absent — the regional-list-but-not-OFAC pattern the
overlay was designed to surface.

## 1. Company triples (ICIJ + OpenSanctions + GLEIF)

Same legal entity referenced by all three datasets. Invisible to any
single dataset's UI — ICIJ's Offshore Leaks DB doesn't show GLEIF LEIs;
OpenSanctions doesn't surface ICIJ leak provenance; GLEIF doesn't
flag sanctions status.

| LEI | GLEIF name | ICIJ name (sample) | ICIJ row count | OS name | Jurisdiction | OS list count |
|---|---|---|---:|---|---|---:|
| `300300HHTAWFTXYVVI58` | Hong Kong Linear Growth Limited | Hong Kong Jinzhao Resources Limited (1 variants) | 1 | HONG KONG INTERTRADE COMPANY | hk | 9 |
| `213800IMQFB4XIUD2580` | VASSILIADES & CO. (MALTA) LIMITED | VASSILIADES & CO. (MALTA) LIMITED (1 variants) | 1 | VASSILIADES & CO. MALTA LIMITED | mt | 5 |
| `52990053RSLBKN4VFX85` | MERCHANTILE ASSET LIMITED | MERCHANT CHARTER LIMITED (1 variants) | 1 | Merchant Supreme Co., Ltd. | vg | 4 |
| `2138006Z57H3EJHYY303` | ALTITUDE X2 LTD. | Altitude X2 Ltd. (13 variants) | 13 | Altitude X3 LTD | bm | 4 |


### Jurisdiction distribution

| Jurisdiction | Triples |
|---|---:|
| bm | 13 |
| vg | 1 |
| mt | 1 |
| hk | 1 |


## 2. DOB-confirmed sanctioned officer pairs (OS sanctions ↔ UK PSC)

Sanctioned persons whose name + date-of-birth-year match a UK PSC officer
record. Filtered to the **evasion signal** subset (sanctioned by at least
one government list but absent from OFAC SDN) — top 30 shown,
parquet has the full 38 rows.

| Sanctioned name (OS) | UK PSC name | DOB | Country | PSC seats | Sanction lists | Name score |
|---|---|---|---|---:|---|---:|
| Antoniou Konstantinos | Mr Konstantinos Antoniou | 1961-04 | cy | 5 | ua_nsdc_sanctions | 0.883 |
| Leonid Boguslavsky | Leonid Boguslavskiy | 1951-06 | ru | 4 | ua_nsdc_sanctions | 0.962 |
| Pavel Maslovsky | Pavel Maslovsky | 1956-12 | ru | 3 | ua_nsdc_sanctions | 1.000 |
| Konstantinov Nikolai | Konstantin Ulanov | 1985-08 | ru | 2 | ua_nsdc_sanctions | 0.946 |
| Ronami Ekaterina | Ms. Ekaterina Ronami | 1988-08 | ru | 2 | ua_nsdc_sanctions | 0.860 |
| Maxim / Maksim Volkov | Maxim Novichkov | 1975-10 | ru | 2 | ua_nsdc_sanctions | 0.847 |
| Andreev Vitalii | Iurii Andreev | 1985-08 | ru | 2 | ua_nsdc_sanctions | 0.841 |
| Maruev Aleksei | Mr Aleksei Chua | 1977-11 | ru | 2 | ua_nsdc_sanctions | 0.840 |
| Viktor Pichugov | Victor Pichugov | 1958-05 | cy | 1 | ua_nsdc_sanctions | 0.977 |
| Elena Strokova | Elena Kostikova | 1976-03 | ru | 1 | ua_nsdc_sanctions | 0.950 |
| Vladimir Pozdnyakov | Vladimir Poliakov | 1946-05 | ru | 1 | ua_nsdc_sanctions | 0.939 |
| Elena SMIRNOVA | Elena Korneeva | 1981-10 | ru | 1 | gb_fcdo_sanctions | 0.927 |
| Mikhail Serdyuk | Mikhail Sarkisiants | 1976-03 | ru | 1 | ua_nsdc_sanctions | 0.904 |
| Fedorov Igor | Igor Fedorov | 1966-01 | ru | 1 | ua_nsdc_sanctions | 0.900 |
| Gruzdeva Olga | Olga Gruzdeva | 1974-06 | ru | 1 | ua_nsdc_sanctions | 0.900 |
| Iakovlev Igor | Igor Iakovlev | 1965-10 | ru | 1 | ua_nsdc_sanctions | 0.900 |
| Astafurov Pavel | Mr Pavel Astafurov | 1987-09 | ru | 1 | ua_nsdc_sanctions | 0.877 |
| Fedorov Pavel | Mr Pavel Fedorov | 1984-02 | ru | 1 | ua_nsdc_sanctions | 0.874 |
| Konstantin Dobrynin | Mr Konstantin Dobrynin | 1976-11 | ru | 1 | ua_nsdc_sanctions | 0.851 |
| Markelov Valerii | Mr Valeriy Markelov | 1965-10 | ru | 1 | ua_nsdc_sanctions | 0.843 |
| Pyotr Kondrashev | Mr Petr Kondrashev | 1949-07 | ru | 1 | ua_nsdc_sanctions | 0.841 |
| Klimov Aleksei | Mr. Aleksei Kudinov | 1979-01 | ru | 1 | ua_nsdc_sanctions | 0.840 |
| Vetrova Iuliia | Iuliia Volkova | 1984-08 | ru | 1 | ua_nsdc_sanctions | 0.840 |
| Sophocleous Chrysostomos | Chrysostomos Sofokleous | 1969-09 | cy | 1 | ua_nsdc_sanctions | 0.838 |


## 3. ICIJ ↔ UK PSC direct pairs (no sanctions pivot)

Same-country, multi-token-name, high-score matches between ICIJ leak
officers and UK PSC foreign-national directors. Independent of
sanctions status — the cleanest "person in 2 unrelated datasets"
primitive. Top 30 shown.

| ICIJ leak name | UK PSC name (sample) | Country | PSC seats | Score |
|---|---|---|---:|---:|
| Mr. Vladimir Shevtsov | Mr Vladimir Shevtsov | ru | 8 | 1.000 |
| Mr. Yury Sneshko | Mr Yury Sneshko | ru | 7 | 1.000 |
| ALI EID KHAMIS THANI ALMHEIRI | Ali Eid Khamis Thani Almheiri | ae | 5 | 1.000 |
| Mr. Avraam Kapiri | Mr Avraam Kapiri | cy | 5 | 1.000 |
| MR ANDREY IVANOV | Mr Andrey Ivanov | ru | 4 | 1.000 |
| MARIE LOUISE ZAMMIT | Marie Louise Zammit | mt | 4 | 1.000 |
| FAISAL ALI HABIB SAJWANI | Faisal Ali Habib Sajwani | ae | 3 | 1.000 |
| MR. ALEXEY POPOV | Mr Alexey Popov | ru | 3 | 1.000 |
| MR. TEDDY SAGI | Mr Teddy Sagi | cy | 3 | 1.000 |
| MR HAGOP BOHDJELIAN | Mr Hagop Bohdjelian | cy | 3 | 1.000 |
| ELIOT JON FARRUGIA | Eliot Jon Farrugia | mt | 2 | 1.000 |
| MR. SERGEY SMIRNOV | Mr Sergey Smirnov | ru | 2 | 1.000 |
| Mr. Alexander Gorbachev | Mr Alexander Gorbachev | ru | 2 | 1.000 |
| SULTAN ALI ISMAIL ALI ALFAHIM | Sultan Ali Ismail Ali Alfahim | ae | 2 | 1.000 |
| MR. SERGEY PRONIN | Mr Sergey Pronin | ru | 2 | 1.000 |
| Mr. Alexander Popov | Mr. Alexander Popov | ru | 2 | 1.000 |
| JEAN PAUL FABRI | Jean Paul Fabri | mt | 2 | 1.000 |
| Mrs. Marina Psyllou | Mrs Marina Psyllou | cy | 2 | 1.000 |
| Mr. Vladimir Kuznetsov | Mr Vladimir Kuznetsov | ru | 2 | 1.000 |
| ELIAS IBRAHIM SALLOUM | Elias Ibrahim Salloum | ae | 2 | 1.000 |
| Mr. Vladimir Dunaev | Mr Vladimir Dunaev | ru | 2 | 1.000 |
| AKHILESH KUMAR TIWARI | Akhilesh Kumar Tiwari | cy | 2 | 1.000 |
| MR. ANDREAS SPYRIDES | Mr Andreas Spyrides | cy | 2 | 1.000 |
| MR. YURIY ZHUKOV | Mr Yuriy Zhukov | ru | 2 | 1.000 |
| Mr. Sergey  KLYCHKOV | Mr. Sergey Klychkov | ru | 2 | 1.000 |
| Mr. Andrey Smirnov | Mr Andrey Smirnov | ru | 2 | 1.000 |
| MR GARO BOHDJELIAN | Mr Garo Bohdjelian | cy | 2 | 1.000 |
| Mr Boris Kreyzerov | Mr Boris Kreyzerov | ru | 2 | 1.000 |
| WENDY PENELOPE CUSCHIERI | Wendy Penelope Cuschieri | mt | 2 | 1.000 |
| Mr. Evgeny Aptekar | Mr Evgeny Aptekar | ru | 2 | 1.000 |


### ICIJ↔UK_PSC country distribution

| Country | Pairs |
|---|---:|
| ru | 91 |
| cy | 30 |
| ae | 27 |
| mt | 18 |


## 4. Rare multi-source officer names

Normalized officer names appearing in 2+ source datasets, with all of:
**max ≤ 2 entities per source** (so not a common-name explosion),
**≥ 3 tokens** (so not just a first + last name collision), **at least
2 distinct sources**. Top 30 shown.

| Officer name | n_sources | total | icij_uid | icij_name | icij_jurisdiction | gleif_uid | lei | gleif_name | icij_gleif_score | os_uid | os_name | os_gleif_score | sanction_list_count | sanction_datasets | evasion_signal_single_list_non_ofac | _d_dob | disq_length | uk_disqualified_match | psc_uid | psc_name | psc_dob | psc_country | os_dob | name_score | dob_match | prior_coverage_n | prior_coverage_mainstream | country | uk_psc | opensanctions | icij | overlap_kind | entity_uid | source | name | disq_person_name | disq_dob | disq_case_number | disq_company_name |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| john o connor | 3 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| james michael green | 3 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 2 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| mr vadim samoylenko | 3 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| muhammad umar khan | 3 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| stephen john wheeler | 3 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| michael john rooney | 3 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| rajesh kumar gupta | 3 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| chen wei hsu | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| alan richard taylor | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| javed ali khan | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| luiz alberto rodrigues | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| ryan john lee | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| david james mason | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| ali raza khan | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| philippe le gall | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| abdul hamid khan | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| michael o sullivan | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| mr robert gaspar | 2 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| calvin edward ayre | 2 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| mr koba kezherashvili | 2 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| ish kumar handa | 2 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| mohammed hani kassab | 2 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| trevor peter ridley | 2 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| michael edward jones | 2 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| erbil mehmet arkin | 2 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| mr richard murad | 2 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| liaquat ali pirani | 2 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| derek john green | 2 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| robert hutchison penman | 2 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| keith roger neville | 2 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |


## 5. UK disqualified-director cross-references

The 222-row UK Insolvency Service struck-off register cross-referenced
against the **full** unified person + company tables. Filtered to ICIJ
+ GLEIF matches (UK PSC matches are dominated by Singh / Smith / Jones
name collisions and provide no signal).

| Source | Matched name | Country | Disqualified director | DoB | Length |
|---|---|---|---|---|---|
| icij | Santokh Singh | in | Santokh Singh | 25/5/1971 | 7 Years Month(s) |
| icij | Sajid Bashir | gb | Sajid Bashir | 26/1/1993 | 9 Years 0 Month(s) |
| icij | BFD LTD. |  | Qazi Shamael Iqbal | 22/10/1993 | 9 Years Month(s) |
| gleif | ES MANUFACTURING LTD | gb | Helen Rosalyn James | 14/11/1955 | 8 Years Month(s) |
| gleif | SATCHI HOLDINGS PLC | gb | Jennifer McQueen | 2/1/1983 | 9 Years 0 Month(s) |
| gleif | BFD CORP |  | Qazi Shamael Iqbal | 22/10/1993 | 9 Years Month(s) |
| gleif | BFD | be | Qazi Shamael Iqbal | 22/10/1993 | 9 Years Month(s) |


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
