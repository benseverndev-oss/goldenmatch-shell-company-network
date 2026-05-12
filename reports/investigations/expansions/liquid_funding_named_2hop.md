# 2-hop expansion: `liquid_funding_named`

Seed entity: `icij:82004676` (`Liquid Funding, Ltd.`)

Walks: seed → persons (officer / intermediary / shareholder / beneficial-owner edges) → other companies those persons are attached to. Surfaces every entity that shares at least one officer-class link with the seed.

> **Hypothesis, not proof.** A shared director is a lead. It does not imply common control, shared beneficial ownership, or wrongdoing. Confirm identity (DOB, address, multiple filings) before drawing conclusions.

## Summary

- 14 person(s) attached to seed.
- 521 *other* company(ies) share at least one of those persons.
- 7 of seed's persons appear elsewhere in ICIJ.

## Seed's officer-class neighbours

| person_uid | name | country | kind |
| --- | --- | --- | --- |
| `icij:80111786` | `Perinchief - Diane` | ? | officer |
| `icij:80113450` | `Poole - Deborah J` | ? | officer |
| `icij:80069756` | `Gillespie - Hugh Edwin` | ? | officer |
| `icij:80067647` | `Fulton - Mary` | ie | officer |
| `icij:80039252` | `Erskine - Alex J` | ? | officer |
| `icij:80096976` | `MacNamara - Liam` | ie | officer |
| `icij:80094304` | `Lipman - Jeffrey M` | us | officer |
| `icij:80063035` | `Epstein - Jeffrey E` | ? | officer |
| `icij:80107655` | `Novelly - Paul Anthony` | us | officer |
| `icij:80087420` | `Klug - Marcus` | ? | officer |
| `icij:80042934` | `Burritt - James R` | us | officer |
| `icij:80088364` | `Krehan - Ernst` | ? | officer |
| `icij:80071114` | `Gores - Fiona Adenike` | ? | officer |
| `icij:80113562` | `Papouras - Christopher` | us | officer |

## Other companies sharing officer-class links

Ranked by number of distinct shared persons (desc). Showing all rows.

| other_company_uid | name | jur | shared_persons | shared_with |
| --- | --- | --- | ---: | --- |
| `icij:82000567` | `SANDGATE LTD.` | bm | 3 | `icij:80039252`, `icij:80071114`, `icij:80113450` |
| `icij:82001793` | `EPI - Ecopetrol Pipelines International Limited` | bm | 3 | `icij:80039252`, `icij:80069756`, `icij:80071114` |
| `icij:82003443` | `Mid Baltic Investments Limited` | bm | 3 | `icij:80039252`, `icij:80069756`, `icij:80113450` |
| `icij:82000344` | `Wellbridge Maritime Limited` | bm | 2 | `icij:80071114`, `icij:80111786` |
| `icij:82000536` | `Mundipharma Laboratories Limited` | bm | 2 | `icij:80039252`, `icij:80071114` |
| `icij:82000538` | `Atlantic Laboratories Limited` | bm | 2 | `icij:80039252`, `icij:80071114` |
| `icij:82000558` | `Earls Court Farm Limited` | bm | 2 | `icij:80039252`, `icij:80071114` |
| `icij:82000584` | `HENLEY GROUP, LTD.` | bm | 2 | `icij:80069756`, `icij:80113450` |
| `icij:82000711` | `Wye Shipping Limited` | bm | 2 | `icij:80071114`, `icij:80111786` |
| `icij:82000729` | `The Research Foundation Ltd.` | bm | 2 | `icij:80039252`, `icij:80071114` |
| `icij:82000800` | `Ebury Investments Limited` | bm | 2 | `icij:80039252`, `icij:80071114` |
| `icij:82000801` | `Great Park Investments Limited` | bm | 2 | `icij:80039252`, `icij:80071114` |
| `icij:82000852` | `Dryden Limited` | bm | 2 | `icij:80039252`, `icij:80071114` |
| `icij:82000935` | `The Aesculapius Foundation Ltd.` | bm | 2 | `icij:80039252`, `icij:80071114` |
| `icij:82000974` | `Worldstar Limited` | bm | 2 | `icij:80039252`, `icij:80113450` |
| `icij:82000983` | `Ely Investment Company Limited` | bm | 2 | `icij:80039252`, `icij:80113450` |
| `icij:82001051` | `NCR Services Ltd.` | bm | 2 | `icij:80039252`, `icij:80071114` |
| `icij:82001154` | `Casterbridge Marine Limited` | bm | 2 | `icij:80071114`, `icij:80111786` |
| `icij:82001185` | `L. P. Clover Limited` | bm | 2 | `icij:80039252`, `icij:80071114` |
| `icij:82001186` | `G. H. Carrell Limited` | bm | 2 | `icij:80039252`, `icij:80071114` |
| `icij:82001189` | `Safinvest Holdings (Bermuda) Limited` | bm | 2 | `icij:80039252`, `icij:80113450` |
| `icij:82001204` | `Mundipharma International Limited` | bm | 2 | `icij:80039252`, `icij:80071114` |
| `icij:82001205` | `B.L. Carrolton Limited` | bm | 2 | `icij:80039252`, `icij:80071114` |
| `icij:82001227` | `J.E.M. Limited` | bm | 2 | `icij:80039252`, `icij:80071114` |
| `icij:82001229` | `Mallard Limited` | bm | 2 | `icij:80039252`, `icij:80071114` |
| `icij:82001267` | `Betal Limited` | bm | 2 | `icij:80039252`, `icij:80071114` |
| `icij:82001323` | `Exe Shipping Limited` | bm | 2 | `icij:80071114`, `icij:80111786` |
| `icij:82001438` | `Aerolab Limited` | bm | 2 | `icij:80039252`, `icij:80071114` |
| `icij:82001471` | `Northdale Limited` | bm | 2 | `icij:80039252`, `icij:80071114` |
| `icij:82001595` | `Kelly Pharmaceuticals Limited` | bm | 2 | `icij:80039252`, `icij:80071114` |
| `icij:82001596` | `Tom Pharmaceuticals Limited` | bm | 2 | `icij:80039252`, `icij:80071114` |
| `icij:82001632` | `Clyde Holdings Limited` | bm | 2 | `icij:80071114`, `icij:80111786` |
| `icij:82001662` | `WINSTAR LIMITED` | bm | 2 | `icij:80039252`, `icij:80113450` |
| `icij:82001781` | `Sapstar Limited` | bm | 2 | `icij:80039252`, `icij:80113450` |
| `icij:82002205` | `Goldstar Limited` | bm | 2 | `icij:80039252`, `icij:80113450` |
| `icij:82002237` | `Bermag Limited` | bm | 2 | `icij:80039252`, `icij:80071114` |
| `icij:82002261` | `Asia Pacific Investment Company Limited` | bm | 2 | `icij:80039252`, `icij:80071114` |
| `icij:82003025` | `The Young's Foundation` | bm | 2 | `icij:80069756`, `icij:80071114` |
| `icij:82003103` | `Mining and Technical Services (Bermuda) Ltd.` | bm | 2 | `icij:80039252`, `icij:80071114` |
| `icij:82003439` | `Anthracite Limited` | bm | 2 | `icij:80069756`, `icij:80113450` |
| `icij:82003474` | `Lend Lease Asian Retail Investment Fund 1 Ltd.` | bm | 2 | `icij:80039252`, `icij:80071114` |
| `icij:82003605` | `Merganser Limited` | bm | 2 | `icij:80039252`, `icij:80071114` |
| `icij:82003606` | `Sheldrake Limited` | bm | 2 | `icij:80039252`, `icij:80071114` |
| `icij:82003631` | `Conway Shipping Co. Ltd.` | bm | 2 | `icij:80071114`, `icij:80111786` |
| `icij:82003632` | `Bernhard Schulte (Bermuda) Limited` | bm | 2 | `icij:80071114`, `icij:80111786` |
| `icij:82003794` | `Space Resource International, Ltd.` | bm | 2 | `icij:80111786`, `icij:80113450` |
| `icij:82004135` | `Mundipharma Research Company Limited` | bm | 2 | `icij:80039252`, `icij:80071114` |
| `icij:82004408` | `Elizabethan Private Trust Company Ltd.` | bm | 2 | `icij:80069756`, `icij:80113450` |
| `icij:82004664` | `Wingate High Net Worth Private Equity Fund Limited` | bm | 2 | `icij:80039252`, `icij:80113450` |
| `icij:82004665` | `Wingate Institutional Private Equity Fund Limited` | bm | 2 | `icij:80039252`, `icij:80113450` |
| `icij:82004737` | `Mundipharma International Holdings Limited` | bm | 2 | `icij:80039252`, `icij:80071114` |
| `icij:82004765` | `Tol Eressea Limited` | bm | 2 | `icij:80071114`, `icij:80113450` |
| `icij:82004788` | `Crestview (Bermuda) Limited` | bm | 2 | `icij:80069756`, `icij:80071114` |
| `icij:82004791` | `LiquidAfrica Holdings Limited` | bm | 2 | `icij:80039252`, `icij:80069756` |
| `icij:82004800` | `Apstar Limited` | bm | 2 | `icij:80039252`, `icij:80113450` |
| `icij:82006584` | `TK International Limited` | bm | 2 | `icij:80039252`, `icij:80071114` |
| `icij:82006585` | `Laysan Limited` | bm | 2 | `icij:80039252`, `icij:80071114` |
| `icij:82007068` | `Mundipharma International Corporation Limited` | bm | 2 | `icij:80039252`, `icij:80071114` |
| `icij:82007185` | `Navigo Shipmanagers Bermuda Ltd.` | bm | 2 | `icij:80071114`, `icij:80111786` |
| `icij:82007271` | `Mackenzie Cundill Investment Management (Bermuda) Ltd.` | bm | 2 | `icij:80039252`, `icij:80071114` |
| `icij:82007309` | `Putnam Green Ltd.` | bm | 2 | `icij:80039252`, `icij:80071114` |
| `icij:82007342` | `Lend Lease Asian Retail Investment Fund 2 Ltd.` | bm | 2 | `icij:80039252`, `icij:80071114` |
| `icij:82007343` | `Lend Lease Asian Retail Investment Fund 3 Ltd.` | bm | 2 | `icij:80039252`, `icij:80071114` |
| `icij:82007344` | `Lend Lease Asian Retail Investment Fund 4 Ltd.` | bm | 2 | `icij:80039252`, `icij:80071114` |
| `icij:82007345` | `Lend Lease Asian Retail Investment Fund 5 Ltd.` | bm | 2 | `icij:80039252`, `icij:80071114` |
| `icij:82007346` | `Lend Lease Asian Retail Investment Fund 6 Ltd.` | bm | 2 | `icij:80039252`, `icij:80071114` |
| `icij:82007932` | `LifeVest Limited` | bm | 2 | `icij:80039252`, `icij:80071114` |
| `icij:82000017` | `TRANSWORLD ENERGY LIMITED` | bm | 1 | `icij:80069756` |
| `icij:82000022` | `Befico Limited` | bm | 1 | `icij:80113450` |
| `icij:82000034` | `DLD (BERMUDA) LIMITED` | bm | 1 | `icij:80039252` |
| `icij:82000041` | `Capge Limited` | bm | 1 | `icij:80111786` |
| `icij:82000060` | `Mason Investments Limited` | bm | 1 | `icij:80069756` |
| `icij:82000083` | `Sea Stars Company Limited` | bm | 1 | `icij:80039252` |
| `icij:82000098` | `Vesta Limited` | bm | 1 | `icij:80071114` |
| `icij:82000116` | `Aluminium Atlantic Company Limited` | bm | 1 | `icij:80069756` |
| `icij:82000119` | `Bermuda Air Conditioning Limited` | bm | 1 | `icij:80111786` |
| `icij:82000120` | `Bermuda Capital Company Limited` | bm | 1 | `icij:80039252` |
| `icij:82000130` | `Godet & Young Limited` | bm | 1 | `icij:80111786` |
| `icij:82000132` | `Eigg Bermuda Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82000145` | `Norwood Limited` | bm | 1 | `icij:80071114` |
| `icij:82000149` | `Roxdene Limited` | bm | 1 | `icij:80111786` |
| `icij:82000152` | `TELLIN (BERMUDA) LIMITED` | bm | 1 | `icij:80039252` |
| `icij:82000160` | `BERRY COMPANY LIMITED` | bm | 1 | `icij:80039252` |
| `icij:82000161` | `CARTER COMPANY LIMITED` | bm | 1 | `icij:80039252` |
| `icij:82000164` | `FAIRCHILD FOUNDATION LIMITED` | bm | 1 | `icij:80039252` |
| `icij:82000177` | `Equus International Management Ltd.` | bm | 1 | `icij:80111786` |
| `icij:82000180` | `Reid Finance Limited` | bm | 1 | `icij:80039252` |
| `icij:82000186` | `HUDSON CENTRAL LIMITED` | bm | 1 | `icij:80039252` |
| `icij:82000188` | `TRANSWORLD OIL LIMITED` | bm | 1 | `icij:80069756` |
| `icij:82000189` | `Appleby Management (Bermuda) Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82000193` | `Resort Photo Services Limited` | bm | 1 | `icij:80071114` |
| `icij:82000197` | `SAFINVEST INTERNATIONAL LIMITED` | bm | 1 | `icij:80039252` |
| `icij:82000213` | `Polar Reefers Ltd.` | bm | 1 | `icij:80111786` |
| `icij:82000220` | `Willis Faber Services Limited` | bm | 1 | `icij:80111786` |
| `icij:82000230` | `Hawthorne Insurance Company Limited` | bm | 1 | `icij:80071114` |
| `icij:82000233` | `EDLOW RESOURCES LIMITED` | bm | 1 | `icij:80039252` |
| `icij:82000246` | `A.I.C. LIMITED` | bm | 1 | `icij:80107655` |
| `icij:82000289` | `ARK INTERNATIONAL LIMITED` | bm | 1 | `icij:80039252` |
| `icij:82000327` | `BB Company  Limited` | bm | 1 | `icij:80039252` |
| `icij:82000345` | `GLENCORE GRAIN LTD.` | bm | 1 | `icij:80071114` |
| `icij:82000392` | `Appleby Corporate Services (BVI) Limited` | vg | 1 | `icij:80039252` |
| `icij:82000462` | `GRANOCO LTD.` | bm | 1 | `icij:80071114` |
| `icij:82000480` | `Bay Investments Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82000481` | `Inlet Investments Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82000503` | `BS&R Group Ltd.` | bm | 1 | `icij:80111786` |
| `icij:82000507` | `Suninvest Limited` | bm | 1 | `icij:80069756` |
| `icij:82000537` | `Triangle Industries Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82000555` | `ORBEX LIMITED` | bm | 1 | `icij:80039252` |
| `icij:82000556` | `Jardine Fleming Management (Bermuda) Limited` | bm | 1 | `icij:80113450` |
| `icij:82000561` | `Premier Overseas Holdings Ltd.` | bm | 1 | `icij:80113450` |
| `icij:82000657` | `Nottingham Trading Co. Ltd.` | bm | 1 | `icij:80111786` |
| `icij:82000660` | `Gotco, Ltd.` | bm | 1 | `icij:80111786` |
| `icij:82000662` | `Old SRPH, Ltd.` | bm | 1 | `icij:80107655` |
| `icij:82000692` | `Fishing and Cruising Ltd.` | bm | 1 | `icij:80111786` |
| `icij:82000696` | `SICO LTD.` | bm | 1 | `icij:80039252` |
| `icij:82000700` | `Pangold Marine Limited` | bm | 1 | `icij:80107655` |
| `icij:82000701` | `Transshipment Holding, Ltd.` | bm | 1 | `icij:80107655` |
| `icij:82000708` | `Consul International Corporation Limited` | bm | 1 | `icij:80071114` |
| `icij:82000730` | `Reynolds International (China) Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82000736` | `JUD B-430 LIMITED` | bm | 1 | `icij:80113450` |
| `icij:82000743` | `FIBRAS LIMITED` | bm | 1 | `icij:80113450` |
| `icij:82000748` | `Gulf International Lubricants, Ltd.` | bm | 1 | `icij:80111786` |
| `icij:82000751` | `Balmuir Holdings Limited` | bm | 1 | `icij:80113450` |
| `icij:82000758` | `WESTERN METAL SALES LIMITED` | bm | 1 | `icij:80111786` |
| `icij:82000772` | `Pointsettia Limited` | bm | 1 | `icij:80069756` |
| `icij:82000773` | `O  R  O Financial Services Limited` | bm | 1 | `icij:80113450` |
| `icij:82000795` | `REL Investment Holdings Limited` | bm | 1 | `icij:80111786` |
| `icij:82000805` | `International Pacific Securities Limited` | bm | 1 | `icij:80111786` |
| `icij:82000833` | `Island Engineering Limited` | bm | 1 | `icij:80111786` |
| `icij:82000842` | `West End Landscaping Limited` | bm | 1 | `icij:80111786` |
| `icij:82000849` | `Employee Assistance Programme of Bermuda` | bm | 1 | `icij:80111786` |
| `icij:82000851` | `McAlpine Brittain Ltd.` | bm | 1 | `icij:80069756` |
| `icij:82000862` | `CREST MANAGEMENT SERVICES, LIMITED` | bm | 1 | `icij:80113450` |
| `icij:82000864` | `The Ferry Reach Company Limited` | bm | 1 | `icij:80111786` |
| `icij:82000866` | `Dawson & Sons Limited` | bm | 1 | `icij:80111786` |
| `icij:82000882` | `EMS Bermuda Limited` | bm | 1 | `icij:80111786` |
| `icij:82000890` | `Grandford Maritime Limited` | bm | 1 | `icij:80111786` |
| `icij:82000939` | `Marine Gas Transport, Ltd.` | bm | 1 | `icij:80111786` |
| `icij:82000995` | `Dovey Shipping Co. Ltd.` | bm | 1 | `icij:80111786` |
| `icij:82001042` | `Tiana Limited` | bm | 1 | `icij:80113450` |
| `icij:82001043` | `Rhymney Shipping Company Limited` | bm | 1 | `icij:80111786` |
| `icij:82001044` | `TRIANGLE INTERNATIONAL REINSURANCE LIMITED` | bm | 1 | `icij:80113450` |
| `icij:82001054` | `Glencore Exploration Ltd.` | bm | 1 | `icij:80071114` |
| `icij:82001067` | `Marway Shipping Limited` | xx | 1 | `icij:80111786` |
| `icij:82001079` | `Voya Investment Management (Bermuda) Holdings Limited` | bm | 1 | `icij:80039252` |
| `icij:82001110` | `Impex Company Ltd.` | bm | 1 | `icij:80111786` |
| `icij:82001152` | `Dusco (Bda) Limited` | bm | 1 | `icij:80113450` |
| `icij:82001184` | `Olivewood Limited` | bm | 1 | `icij:80039252` |
| `icij:82001215` | `Record Fund Management (Bermuda) Limited` | bm | 1 | `icij:80039252` |
| `icij:82001245` | `UPT Global, Ltd.` | bm | 1 | `icij:80071114` |
| `icij:82001285` | `Sea Moss Enterprises Limited` | bm | 1 | `icij:80039252` |
| `icij:82001306` | `Colony Holdings Ltd.` | bm | 1 | `icij:80111786` |
| `icij:82001322` | `Bristol Shipping Limited` | bm | 1 | `icij:80111786` |
| `icij:82001324` | `Severn Shipping Limited` | bm | 1 | `icij:80111786` |
| `icij:82001325` | `Airkool Properties Ltd.` | bm | 1 | `icij:80111786` |
| `icij:82001326` | `Mills Creek Properties Ltd.` | bm | 1 | `icij:80111786` |
| `icij:82001455` | `Capital Development Corporation Limited` | bm | 1 | `icij:80111786` |
| `icij:82001459` | `CARIVEN INVESTMENT LIMITED` | bm | 1 | `icij:80113450` |
| `icij:82001472` | `Chiltern Investments Limited` | bm | 1 | `icij:80111786` |
| `icij:82001486` | `CEF ENTERPRISE CAPITAL (BERMUDA) LIMITED` | bm | 1 | `icij:80039252` |
| `icij:82001501` | `J. B. Limited` | bm | 1 | `icij:80039252` |
| `icij:82001543` | `CEFNA Greater China Investments Company Limited` | bm | 1 | `icij:80039252` |
| `icij:82001570` | `Guinness Peat International Capital Assets Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82001579` | `PEARL HOLDINGS (BERMUDA) LTD.` | bm | 1 | `icij:80039252` |
| `icij:82001613` | `MERSTAL LIMITED` | bm | 1 | `icij:80113450` |
| `icij:82001627` | `W & B Investments, Ltd.` | bm | 1 | `icij:80107655` |
| `icij:82001670` | `Atalantaf Limited` | bm | 1 | `icij:80039252` |
| `icij:82001676` | `Freepoint Towage Company (Bahamas) Ltd.` | bm | 1 | `icij:80107655` |
| `icij:82001697` | `Ebbtide Holdings Limited` | bm | 1 | `icij:80039252` |
| `icij:82001703` | `OIL DRILLING & EXPLORATION (BERMUDA) LIMITED` | bm | 1 | `icij:80111786` |
| `icij:82001714` | `NZ Holdings Limited` | bm | 1 | `icij:80111786` |
| `icij:82001778` | `NORTH AMERICAN LONDON UNDERWRITERS, LIMITED` | bm | 1 | `icij:80039252` |
| `icij:82001893` | `Diamond Link (Bermuda) Ltd.` | bm | 1 | `icij:80111786` |
| `icij:82001934` | `The Lante Jahwe Trust` | bm | 1 | `icij:80039252` |
| `icij:82002012` | `Energy Investment Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82002022` | `Novartis International Pharmaceutical Ltd.` | bm | 1 | `icij:80113450` |
| `icij:82002227` | `Canmar Courage Ltd.` | bm | 1 | `icij:80113450` |
| `icij:82002228` | `Canmar Fortune Ltd.` | bm | 1 | `icij:80113450` |
| `icij:82002276` | `AL TADAMON COMPANY LTD.` | bm | 1 | `icij:80039252` |
| `icij:82002294` | `Renaissance Advisory Services Limited` | bm | 1 | `icij:80039252` |
| `icij:82002311` | `Heritage Capital Limited` | bm | 1 | `icij:80111786` |
| `icij:82002345` | `OMI Marine Services Limited` | bm | 1 | `icij:80111786` |
| `icij:82002399` | `Latin American Coal Marketing Company Ltd.` | bm | 1 | `icij:80071114` |
| `icij:82002432` | `CORONA LTD.` | bm | 1 | `icij:80071114` |
| `icij:82002454` | `Woodbridge Asset Management Ltd.` | bm | 1 | `icij:80113450` |
| `icij:82002461` | `Hexagon Capital Management Ltd.` | bm | 1 | `icij:80113450` |
| `icij:82002472` | `Seagos Tankers Services Limited` | bm | 1 | `icij:80111786` |
| `icij:82002491` | `Asia Pacific Wire & Cable Corporation Limited` | bm | 1 | `icij:80039252` |
| `icij:82002598` | `Andean Chemicals Ltd.` | bm | 1 | `icij:80111786` |
| `icij:82002642` | `TORM Crewing Services Limited` | bm | 1 | `icij:80111786` |
| `icij:82002787` | `Rondeau Reefers Ltd.` | bm | 1 | `icij:80111786` |
| `icij:82002807` | `Renaissance Capital Asset Management Limited` | bm | 1 | `icij:80039252` |
| `icij:82002844` | `SIL Limited` | bm | 1 | `icij:80113450` |
| `icij:82002853` | `DLJ Financial Products Limited` | bm | 1 | `icij:80069756` |
| `icij:82002907` | `Internet Business Capital Corporation Limited` | bm | 1 | `icij:80069756` |
| `icij:82002908` | `Framlington Investment Management (Bermuda) Limited` | bm | 1 | `icij:80113450` |
| `icij:82002913` | `Flashpoint Media Ltd.` | bm | 1 | `icij:80069756` |
| `icij:82002919` | `ClearWater Systems Ltd.` | bm | 1 | `icij:80111786` |
| `icij:82002944` | `Pacific Investments (Asia), Limited` | bm | 1 | `icij:80113450` |
| `icij:82002977` | `Fair Cheer Investment Ltd.` | vg | 1 | `icij:80111786` |
| `icij:82002978` | `Harvest Tech Investment Ltd.` | vg | 1 | `icij:80111786` |
| `icij:82002979` | `Peakle Union Holdings Limited` | vg | 1 | `icij:80111786` |
| `icij:82002980` | `Perfect Score Investment Ltd.` | vg | 1 | `icij:80111786` |
| `icij:82002981` | `Sunny Jade Investment Ltd.` | vg | 1 | `icij:80111786` |
| `icij:82002982` | `Units Key Investment Ltd.` | vg | 1 | `icij:80111786` |
| `icij:82002983` | `Union Express Investment Ltd.` | vg | 1 | `icij:80111786` |
| `icij:82002997` | `SafeGard Medical Limited` | bm | 1 | `icij:80111786` |
| `icij:82003022` | `Net Well International Limited` | vg | 1 | `icij:80111786` |
| `icij:82003023` | `Gowell Investments Company Inc.` | vg | 1 | `icij:80111786` |
| `icij:82003024` | `Carbondale Enterprises Ltd.` | vg | 1 | `icij:80111786` |
| `icij:82003026` | `SolutionInc Bermuda Limited` | bm | 1 | `icij:80111786` |
| `icij:82003057` | `Kowill Investments Inc.` | vg | 1 | `icij:80111786` |
| `icij:82003065` | `Renaissance Securities Trading Limited` | bm | 1 | `icij:80039252` |
| `icij:82003372` | `Atlantic Sales & Marketing Ltd.` | bm | 1 | `icij:80069756` |
| `icij:82003375` | `Truman Enterprises, Inc.` | bm | 1 | `icij:80069756` |
| `icij:82003376` | `The Truman Foundation (Pvt) Limited` | bm | 1 | `icij:80069756` |
| `icij:82003378` | `The Sagitta Aegis Fund Limited` | bm | 1 | `icij:80039252` |
| `icij:82003385` | `Provco Limited` | bm | 1 | `icij:80113450` |
| `icij:82003393` | `ALLMAT (BERMUDA) LIMITED` | bm | 1 | `icij:80069756` |
| `icij:82003397` | `The Sagitta Aegis (US$) Fund Limited` | bm | 1 | `icij:80039252` |
| `icij:82003405` | `Appleby Securities (Bermuda) Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82003431` | `Canmar Honour Ltd.` | bm | 1 | `icij:80113450` |
| `icij:82003432` | `Canmar Pride Ltd.` | bm | 1 | `icij:80113450` |
| `icij:82003437` | `SafeGard Medical Group Limited` | bm | 1 | `icij:80111786` |
| `icij:82003441` | `Comrock Ltd.` | bm | 1 | `icij:80113450` |
| `icij:82003468` | `Bermuda Insulation Ltd.` | bm | 1 | `icij:80111786` |
| `icij:82003469` | `Aviation Healthcare Limited` | bm | 1 | `icij:80113450` |
| `icij:82003484` | `Caymus Financial Limited` | bm | 1 | `icij:80069756` |
| `icij:82003521` | `VMR Trust and Management Limited` | bm | 1 | `icij:80111786` |
| `icij:82003544` | `Trafalgar Trading Limited` | bm | 1 | `icij:80069756` |
| `icij:82003545` | `Mid Ocean World Investments Limited` | bm | 1 | `icij:80039252` |
| `icij:82003565` | `Captive Fixed Income Fund Limited, The` | bm | 1 | `icij:80039252` |
| `icij:82003600` | `Sage Private Trust Company Limited` | bm | 1 | `icij:80069756` |
| `icij:82003614` | `Equipment International Ltd.` | bm | 1 | `icij:80111786` |
| `icij:82003659` | `Garnham & Co. Limited` | bm | 1 | `icij:80111786` |
| `icij:82003707` | `Manulife Century Investments (Bermuda) Limited` | bm | 1 | `icij:80069756` |
| `icij:82003708` | `Daihyaku Manulife Holdings (Bermuda) Limited` | bm | 1 | `icij:80069756` |
| `icij:82003713` | `Jetcam International Holdings Limited` | bm | 1 | `icij:80111786` |
| `icij:82003735` | `Bay Almanzora Limited` | bm | 1 | `icij:80039252` |
| `icij:82003778` | `Glencore Investments Limited` | bm | 1 | `icij:80071114` |
| `icij:82003814` | `Malvern Holdings Limited` | bm | 1 | `icij:80113450` |
| `icij:82003972` | `SEPEP General Partner Limited` | bm | 1 | `icij:80039252` |
| `icij:82004018` | `SEPEP Holdings Limited` | bm | 1 | `icij:80039252` |
| `icij:82004048` | `Atila Venture Partners Ltd.` | bm | 1 | `icij:80113450` |
| `icij:82004085` | `CapVest Group Limited` | bm | 1 | `icij:80071114` |
| `icij:82004118` | `CV Equity Management Limited` | bm | 1 | `icij:80071114` |
| `icij:82004142` | `Triangle Management Limited` | bm | 1 | `icij:80113450` |
| `icij:82004186` | `CITIC Pacific Communications Limited` | bm | 1 | `icij:80111786` |
| `icij:82004223` | `Atila Venture Capital Limited` | bm | 1 | `icij:80113450` |
| `icij:82004274` | `PELHAM Limited` | bm | 1 | `icij:80111786` |
| `icij:82004296` | `Engineering World Media Limited` | bm | 1 | `icij:80111786` |
| `icij:82004348` | `Buckingham Enterprises Limited` | bm | 1 | `icij:80039252` |
| `icij:82004354` | `Hedge Fund Brokerage and Trading Ltd.` | bm | 1 | `icij:80113450` |
| `icij:82004416` | `Glencore Capital Ltd.` | bm | 1 | `icij:80071114` |
| `icij:82004471` | `Stock2Profit Limited` | bm | 1 | `icij:80111786` |
| `icij:82004500` | `Jalva Media, Ltd.` | bm | 1 | `icij:80111786` |
| `icij:82004512` | `Calew Ltd.` | bm | 1 | `icij:80069756` |
| `icij:82004515` | `Thorburn Limited` | bm | 1 | `icij:80069756` |
| `icij:82004518` | `OHCP MGP (Bermuda), Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82004519` | `OHCP Principal Company (Bermuda), Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82004521` | `OHCP SLP (Bermuda), Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82004544` | `VIL Finance Ltd` | bm | 1 | `icij:80111786` |
| `icij:82004580` | `ifgmanagement.com (Bermuda) Limited` | bm | 1 | `icij:80039252` |
| `icij:82004595` | `Securitas Ventures Limited` | bm | 1 | `icij:80113450` |
| `icij:82004617` | `SS Capital International I Limited` | bm | 1 | `icij:80039252` |
| `icij:82004659` | `Syngenta Reinsurance Limited` | bm | 1 | `icij:80113450` |
| `icij:82004661` | `Syngenta Investment Ltd.` | bm | 1 | `icij:80113450` |
| `icij:82004677` | `SPI IMW 1, Ltd.` | bm | 1 | `icij:80113450` |
| `icij:82004678` | `SPI IMW 2, Ltd.` | bm | 1 | `icij:80113450` |
| `icij:82004679` | `Securitas Allied Holdings, Ltd` | bm | 1 | `icij:80113450` |
| `icij:82004680` | `Securitas RCL Limited` | bm | 1 | `icij:80113450` |
| `icij:82004681` | `SLAM HS Investment, Ltd.` | bm | 1 | `icij:80113450` |
| `icij:82004703` | `Invesdex Capital Ltd.` | bm | 1 | `icij:80113450` |
| `icij:82004729` | `NewSat Holdings Limited` | bm | 1 | `icij:80111786` |
| `icij:82004730` | `NewSat-425 Limited` | bm | 1 | `icij:80111786` |
| `icij:82004731` | `NewSat-I Limited` | bm | 1 | `icij:80111786` |
| `icij:82004741` | `Glencore Cerrejon Ltd` | bm | 1 | `icij:80071114` |
| `icij:82004759` | `Wingate (Bermuda) Ltd.` | bm | 1 | `icij:80113450` |
| `icij:82004760` | `Wingate (Bermuda) Funds Ltd.` | bm | 1 | `icij:80113450` |
| `icij:82004811` | `Biogen Idec (Bermuda) Investments Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82004824` | `Resort Imaging Limited` | bm | 1 | `icij:80071114` |
| `icij:82004837` | `Huntrise Global Partners Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82004842` | `Marvell International Ltd.` | bm | 1 | `icij:80069756` |
| `icij:82004880` | `Novartis Bioventures Ltd.` | bm | 1 | `icij:80113450` |
| `icij:82004901` | `Solar Development Capital Ltd.` | bm | 1 | `icij:80111786` |
| `icij:82004912` | `Dressage Ltd.` | vg | 1 | `icij:80069756` |
| `icij:82004918` | `CITIC Pacific Aviation Limited` | bm | 1 | `icij:80111786` |
| `icij:82004920` | `Performance Materials (Bermuda) Ltd.` | bm | 1 | `icij:80069756` |
| `icij:82004936` | `Masco Limited` | bm | 1 | `icij:80069756` |
| `icij:82004939` | `Buena Vista Limited` | bm | 1 | `icij:80039252` |
| `icij:82004940` | `PWB Institutional Value Partners Ltd` | bm | 1 | `icij:80039252` |
| `icij:82005070` | `UFJ Trustee Services Pvt. (Bermuda) Limited` | bm | 1 | `icij:80039252` |
| `icij:82005105` | `AQ Japan Long-Short Fund Ltd.` | bm | 1 | `icij:80113450` |
| `icij:82005165` | `ANAHARI:IO HOLDINGS LTD.` | bm | 1 | `icij:80111786` |
| `icij:82005223` | `Admirals Overseas Fund, Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82005230` | `Novartis Securities Investment Ltd.` | bm | 1 | `icij:80113450` |
| `icij:82005273` | `GMO Offshore Master Portfolios IV Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82005282` | `FK Language Ltd.` | bm | 1 | `icij:80071114` |
| `icij:82005398` | `GMO Emerging Country Debt Portfolio (Offshore) Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82005399` | `Midsummer Partners, Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82005400` | `Midsummer Investments, Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82005447` | `Foxseal Limited` | bm | 1 | `icij:80039252` |
| `icij:82005448` | `Bula Limited` | bm | 1 | `icij:80039252` |
| `icij:82005479` | `St Ledger Limited` | bm | 1 | `icij:80039252` |
| `icij:82005482` | `Anthems Limited` | bm | 1 | `icij:80039252` |
| `icij:82005523` | `GMO Offshore Funds I Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82005598` | `Primicia Fund, Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82005611` | `Acadia Wealth Management Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82005613` | `GMO Offshore Master Portfolios V Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82005646` | `GMO Offshore Master Portfolio VI Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82005650` | `Parkway Parade Partnership Limited` | bm | 1 | `icij:80039252` |
| `icij:82005662` | `Primicia Master Fund, Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82005666` | `Tricor Re Investment Fund Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82005697` | `Carapace Consulting Services Ltd.` | bm | 1 | `icij:80111786` |
| `icij:82005703` | `Power Asset Management Limited` | bm | 1 | `icij:80039252` |
| `icij:82005720` | `GMO Offshore Master Portfolios Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82005732` | `Renaissance Financial Holdings Limited` | bm | 1 | `icij:80039252` |
| `icij:82005812` | `CGT Management Ltd.` | bm | 1 | `icij:80111786` |
| `icij:82005816` | `EGT Management Ltd.` | bm | 1 | `icij:80111786` |
| `icij:82005818` | `Chelsea Properties Ltd.` | bm | 1 | `icij:80111786` |
| `icij:82005822` | `FIA Financial Services Ltd.` | bm | 1 | `icij:80111786` |
| `icij:82005834` | `Bay Holdings Limited` | bm | 1 | `icij:80039252` |
| `icij:82005851` | `Vista Management Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82005883` | `Renaissance Capital International Services Limited` | bm | 1 | `icij:80039252` |
| `icij:82005895` | `Globeleq Generation Holdings Limited` | bm | 1 | `icij:80039252` |
| `icij:82005910` | `GMO Offshore Funds II, Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82005961` | `Nonsuch Holdings, Ltd.` | bm | 1 | `icij:80071114` |
| `icij:82005962` | `SARAZEN LIMITED` | bm | 1 | `icij:80071114` |
| `icij:82005963` | `Prospect Holdings, Ltd.` | bm | 1 | `icij:80071114` |
| `icij:82005964` | `PAGET LIMITED` | bm | 1 | `icij:80071114` |
| `icij:82005968` | `Lionstone IDF Ltd.` | bm | 1 | `icij:80111786` |
| `icij:82005998` | `Capital Generations Company Ltd.` | bm | 1 | `icij:80111786` |
| `icij:82006012` | `Parkcentral Signal Offshore Fund Limited` | bm | 1 | `icij:80039252` |
| `icij:82006013` | `Windward Equity Holdings V, Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82006014` | `Windward Funding V, Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82006043` | `Bay Group Limited` | bm | 1 | `icij:80039252` |
| `icij:82006044` | `The Rio Capital Fund Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82006061` | `Performa Liquid Assets Fund Ltd` | bm | 1 | `icij:80039252` |
| `icij:82006066` | `Performa Reserve Fund Ltd` | bm | 1 | `icij:80039252` |
| `icij:82006067` | `Performa International Convertible Bond Fund Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82006077` | `Bear Stearns International Funding (Bermuda) Limited` | bm | 1 | `icij:80094304` |
| `icij:82006104` | `Quantrarian Asia Hedge Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82006125` | `Biogen Idec (Bermuda) Investments II Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82006153` | `Globeleq Holdings (Tsavo) Limited` | bm | 1 | `icij:80039252` |
| `icij:82006207` | `Prides Capital (Bermuda) Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82006212` | `Globeleq Holdings (Azito) Limited` | bm | 1 | `icij:80039252` |
| `icij:82006230` | `Luminus Energy Partners Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82006235` | `Premium Fund, Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82006249` | `Altius Capital Limited` | bm | 1 | `icij:80039252` |
| `icij:82006258` | `COSL Rig Ltd.` | bm | 1 | `icij:80111786` |
| `icij:82006261` | `Luminus Energy Partners Master Fund, Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82006263` | `Mosvold Shipping Ltd.` | bm | 1 | `icij:80111786` |
| `icij:82006273` | `COSL Craft Ltd.` | bm | 1 | `icij:80111786` |
| `icij:82006274` | `COSL Power Ltd.` | bm | 1 | `icij:80111786` |
| `icij:82006368` | `GMO Alternative Asset SPC Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82006392` | `China Distance Education Holdings Limited` | bm | 1 | `icij:80111786` |
| `icij:82006416` | `Fornax Investments Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82006446` | `Pancurri Investments Limited` | bm | 1 | `icij:80039252` |
| `icij:82006449` | `ChemEnergy Investments Limited` | bm | 1 | `icij:80039252` |
| `icij:82006450` | `ChemEnergy International Limited` | bm | 1 | `icij:80039252` |
| `icij:82006456` | `Altius Combined Strategy Fund Limited` | bm | 1 | `icij:80039252` |
| `icij:82006471` | `Galif Investments Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82006473` | `City Streets Production Co. Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82006608` | `COSL Superior Ltd.` | bm | 1 | `icij:80111786` |
| `icij:82006630` | `Mosvold Management Ltd.` | bm | 1 | `icij:80111786` |
| `icij:82006637` | `SHENGDA (GROUP) HOLDINGS LTD.` | bm | 1 | `icij:80111786` |
| `icij:82006642` | `Guinness Peat CH Limited` | bm | 1 | `icij:80039252` |
| `icij:82006677` | `Cintus Worldwide Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82006683` | `Matos International Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82006702` | `WPS Investments, Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82006752` | `Orbis Investment Management (MIS) Limited` | bm | 1 | `icij:80069756` |
| `icij:82006769` | `Sud Energie Limited` | bm | 1 | `icij:80039252` |
| `icij:82006770` | `Globeleq Holdings (Panama Greenfield) Limited` | bm | 1 | `icij:80039252` |
| `icij:82006789` | `Range Petroleum Ltd.` | bm | 1 | `icij:80111786` |
| `icij:82006820` | `Vietnam Dragon Fund Limited` | bm | 1 | `icij:80039252` |
| `icij:82006882` | `RomReal Ltd.` | bm | 1 | `icij:80111786` |
| `icij:82006894` | `COSL Force Ltd.` | bm | 1 | `icij:80111786` |
| `icij:82006932` | `Syrinx Limited` | bm | 1 | `icij:80039252` |
| `icij:82006952` | `CapVest Group II Limited` | bm | 1 | `icij:80071114` |
| `icij:82006953` | `CV Equity Management II Limited` | bm | 1 | `icij:80071114` |
| `icij:82006968` | `Zanett Opportunity Fund, Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82006977` | `Globeleq Holdings (GECA) Limited` | bm | 1 | `icij:80039252` |
| `icij:82007009` | `COSL Boss Ltd.` | bm | 1 | `icij:80111786` |
| `icij:82007074` | `Globeleq Tanzania Limited` | bm | 1 | `icij:80039252` |
| `icij:82007089` | `COSL Strike Ltd.` | bm | 1 | `icij:80111786` |
| `icij:82007102` | `Rodcroft Global Equity Fund Ltd.` | bm | 1 | `icij:80071114` |
| `icij:82007104` | `COSL Seeker Ltd.` | bm | 1 | `icij:80111786` |
| `icij:82007110` | `GMO Offshore Master Portfolios II Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82007152` | `Rodcroft Fund Management Ltd.` | bm | 1 | `icij:80071114` |
| `icij:82007155` | `Mosvold Partner Ltd.` | bm | 1 | `icij:80111786` |
| `icij:82007167` | `SamSal Limited` | bm | 1 | `icij:80069756` |
| `icij:82007283` | `Trinity Emerging Markets Opportunities Fund Limited` | bm | 1 | `icij:80071114` |
| `icij:82007298` | `Grand Link Investments Holdings Ltd.` | vg | 1 | `icij:80071114` |
| `icij:82007484` | `Pacific Crossing Limited` | bm | 1 | `icij:80111786` |
| `icij:82007485` | `Midsummer Ventures, Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82007589` | `Spire Holding Co. Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82007607` | `Abbott Strategic Opportunities Limited` | bm | 1 | `icij:80111786` |
| `icij:82007635` | `Cronos Ltd.` | bm | 1 | `icij:80111786` |
| `icij:82007650` | `Luminus Capital Partners, Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82007653` | `Renaissance Securities (Cyprus) Limited` | cy | 1 | `icij:80039252` |
| `icij:82007698` | `Luminus Capital Partners Master Fund, Ltd` | bm | 1 | `icij:80039252` |
| `icij:82007918` | `Brookfield Infrastructure Partners Limited` | bm | 1 | `icij:80039252` |
| `icij:82007936` | `Glencore Exploration (DRC) Limited` | bm | 1 | `icij:80039252` |
| `icij:82007938` | `Glencore Exploration (New Ventures) Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82007961` | `Prometheus Equity Holdings III, Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82007962` | `Prometheus Funding III, Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82007978` | `SIF (Bermuda) Investments No 1 Limited` | bm | 1 | `icij:80039252` |
| `icij:82007979` | `SIF (Bermuda) Investments No 2 Limited` | bm | 1 | `icij:80039252` |
| `icij:82008128` | `Arrow Capital Investment Services, Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82008148` | `STEELE'S COMPANY LTD.` | bm | 1 | `icij:80111786` |
| `icij:82008151` | `Glencore Exploration Cameroon Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82008152` | `Glencore Exploration (GE) Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82008179` | `Chamfield Limited` | bm | 1 | `icij:80071114` |
| `icij:82008235` | `Northern Trust Global Fund Services Bermuda, Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82008245` | `Prout Web Solutions Ltd.` | bm | 1 | `icij:80071114` |
| `icij:82008262` | `Brookfield Infrastructure General Partner Limited` | bm | 1 | `icij:80039252` |
| `icij:82008332` | `Appleby Global Group LLC` | im | 1 | `icij:80039252` |
| `icij:82008333` | `Oakdale Holdings Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82008334` | `Burdock Investments Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82008335` | `Atlas Investments Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82008336` | `Wapata Investments Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82008338` | `Glencore Exploration (Bioko) Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82008339` | `Bendelli Holding Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82008341` | `CABASSOLE LIMITED` | bm | 1 | `icij:80039252` |
| `icij:82008342` | `SAINT AMAND LIMITED` | bm | 1 | `icij:80039252` |
| `icij:82008343` | `MONT MIRAIL LIMITED` | bm | 1 | `icij:80039252` |
| `icij:82008345` | `Carestream Holdings (Bermuda) Ltd.` | bm | 1 | `icij:80111786` |
| `icij:82008346` | `Carestream Group Holdings (Bermuda) Ltd.` | bm | 1 | `icij:80111786` |
| `icij:82008362` | `Inkia Energy Limited` | bm | 1 | `icij:80039252` |
| `icij:82008379` | `NFD Agro Ltd.` | bm | 1 | `icij:80111786` |
| `icij:82008386` | `Perella Weinberg Partners Xerion Master` | bm | 1 | `icij:80039252` |
| `icij:82008387` | `Perella Weinberg Partners Xerion Offshore` | bm | 1 | `icij:80039252` |
| `icij:82008396` | `RHS Holdings Incorporated` | vg | 1 | `icij:80039252` |
| `icij:82008431` | `Park Orchard Finance Inc.` | vg | 1 | `icij:80039252` |
| `icij:82008432` | `Saint Exupéry Finance Inc.` | vg | 1 | `icij:80039252` |
| `icij:82008544` | `Fiora Investments Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82008545` | `Cascade Holdings Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82008573` | `AIS Funds Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82008646` | `Glencore Exploration (Chad) Limited` | bm | 1 | `icij:80039252` |
| `icij:82008684` | `Matrix Alternative Investment Strategies Fund II Limited` | bm | 1 | `icij:80071114` |
| `icij:82008686` | `Eclipse Private Equity Fund Services Limited` | bm | 1 | `icij:80039252` |
| `icij:82008709` | `GR Ltd.` | bm | 1 | `icij:80071114` |
| `icij:82008782` | `Lotus Equity Income Fund Limited` | bm | 1 | `icij:80039252` |
| `icij:82008859` | `Fusion Funding Limited` | bm | 1 | `icij:80111786` |
| `icij:82008872` | `Aegean Services Limited` | bm | 1 | `icij:80039252` |
| `icij:82008879` | `Glencore E&P (Colombia) Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82008892` | `Glencore Production (Colombia) Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82008951` | `Quick Investments Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82008952` | `Damila Holding Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82009043` | `Karakoram (Bermuda) Ltd.` | bm | 1 | `icij:80071114` |
| `icij:82009061` | `Midsummer Partners II, Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82009128` | `Perinvest Holdings Limited` | bm | 1 | `icij:80071114` |
| `icij:82009134` | `Ocean Synergy Limited` | bm | 1 | `icij:80111786` |
| `icij:82009230` | `BERMUDA STRIPPING & REFINISHING CO. LTD.` | bm | 1 | `icij:80111786` |
| `icij:82009378` | `Bermuda Alternate Energy Limited` | bm | 1 | `icij:80111786` |
| `icij:82009386` | `Nomura Securities (Bermuda) Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82009437` | `Diversification Fund Limited` | bm | 1 | `icij:80039252` |
| `icij:82009438` | `Institutional Benchmarks Series (Master Feeder) Limited` | bm | 1 | `icij:80039252` |
| `icij:82009479` | `Oceaneer Energy Ltd.` | bm | 1 | `icij:80071114` |
| `icij:82009880` | `Ingenious Global IDF G.P. Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82009969` | `eStats Revolution Master Fund Limited` | bm | 1 | `icij:80039252` |
| `icij:82009970` | `eStats Revolution Offshore Fund Limited` | bm | 1 | `icij:80039252` |
| `icij:82010042` | `CRX Intermodal Bermuda Ltd.` | bm | 1 | `icij:80111786` |
| `icij:82010101` | `Depp Services International Limited` | bm | 1 | `icij:80039252` |
| `icij:82010109` | `Cortesta Holding Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82010110` | `Polino Holding Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82010111` | `Ratalime Limited` | bm | 1 | `icij:80039252` |
| `icij:82010112` | `Glencore Services Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82013405` | `Apex Oil Limited` | bm | 1 | `icij:80107655` |
| `icij:82014280` | `Appleby (Bermuda) Limited` | bm | 1 | `icij:80039252` |
| `icij:82014613` | `Contrarius Group Holdings Limited` | bm | 1 | `icij:80039252` |
| `icij:82014614` | `Contrarius Holdings Limited` | bm | 1 | `icij:80039252` |
| `icij:82014615` | `Contrarius Investment Management (Bermuda) Limited` | bm | 1 | `icij:80039252` |
| `icij:82016162` | `Cronos Containers Program I Ltd.` | bm | 1 | `icij:80111786` |
| `icij:82016195` | `Temaya Limited` | bm | 1 | `icij:80039252` |
| `icij:82019385` | `Globeleq Mesoamerica Energy (Wind) Limited` | bm | 1 | `icij:80039252` |
| `icij:82019449` | `Apamera Limited` | bm | 1 | `icij:80039252` |
| `icij:82019450` | `Nevasca Limited` | bm | 1 | `icij:80039252` |
| `icij:82019596` | `Auger Trading Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82019599` | `Renaissance Capital Investments Limited` | bm | 1 | `icij:80039252` |
| `icij:82020021` | `Transport Infrastructure Fund Limited` | bm | 1 | `icij:80039252` |
| `icij:82020116` | `Lhotse Capital Advisors Limited` | bm | 1 | `icij:80039252` |
| `icij:82020185` | `Sprinter Limited` | bm | 1 | `icij:80039252` |
| `icij:82020186` | `Glencore Exploration & Production (EG) Limited` | bm | 1 | `icij:80039252` |
| `icij:82020245` | `Waterfall Limited` | bm | 1 | `icij:80039252` |
| `icij:82020246` | `Javelin Limited` | bm | 1 | `icij:80039252` |
| `icij:82020247` | `Glencore Exploration (DOB/DOI) Limited` | bm | 1 | `icij:80039252` |
| `icij:82020248` | `Glencore Exploration (DOH) Limited` | bm | 1 | `icij:80039252` |
| `icij:82020249` | `Glencore Exploration (Doseo/Borogop) Limited` | bm | 1 | `icij:80039252` |
| `icij:82020250` | `Cliffs Limited` | bm | 1 | `icij:80039252` |
| `icij:82020412` | `Glencore Exploration & Production (Morocco) Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82020413` | `Drilio Limited` | bm | 1 | `icij:80039252` |
| `icij:82020414` | `Hargos Limited` | bm | 1 | `icij:80039252` |
| `icij:82020485` | `Glencore Exploration (Transportation) Limited` | bm | 1 | `icij:80039252` |
| `icij:82020567` | `SDF III-SideCo Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82020583` | `Maru Sky Limited` | bm | 1 | `icij:80039252` |
| `icij:82020584` | `Livados Limited` | bm | 1 | `icij:80039252` |
| `icij:82020585` | `Surmira Limited` | bm | 1 | `icij:80039252` |
| `icij:82020586` | `Dulino Limited` | bm | 1 | `icij:80039252` |
| `icij:82020739` | `Snowfall Limited` | bm | 1 | `icij:80039252` |
| `icij:82020744` | `Glencore Exploration (Morocco) Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82020941` | `Fluor International C.V.` | bm | 1 | `icij:80039252` |
| `icij:82021303` | `Gonaco Limited` | bm | 1 | `icij:80039252` |
| `icij:82021328` | `Glencore Exploration (Gabon) Limited` | bm | 1 | `icij:80039252` |
| `icij:82021377` | `Exelixis International (Bermuda) Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82022040` | `KANSUKI HOLDINGS (BERMUDA) LIMITED` | bm | 1 | `icij:80039252` |
| `icij:82022264` | `Pachon Project Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82022958` | `New Ocean Diversified Cat Fund Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82022959` | `New Ocean Focus Cat Fund Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82023128` | `GGC Waypoint LP` | ky | 1 | `icij:80113450` |
| `icij:82023130` | `Flamingo Limited` | bm | 1 | `icij:80039252` |
| `icij:82023139` | `Glencore Exploration & Production (Nigeria) Limited` | bm | 1 | `icij:80039252` |
| `icij:82023260` | `New Ocean Market Value Cat Fund Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82023777` | `Alpstar Multi-Strategy Fund, Ltd.` | bm | 1 | `icij:80039252` |
| `icij:82023942` | `Durnford Fund Limited` | ky | 1 | `icij:80113450` |
| `icij:82023944` | `Durnford Masters Fund` | ky | 1 | `icij:80113450` |
| `icij:82024696` | `BAC Transco Ltd.` | bm | 1 | `icij:80111786` |
| `icij:82025266` | `Grampian Investments Limited` | bm | 1 | `icij:80113450` |
| `icij:82025972` | `Berchem Limited` | bm | 1 | `icij:80111786` |
| `icij:82025977` | `Ferro Limited` | bm | 1 | `icij:80111786` |
| `icij:82026542` | `Eurasia Travel Network Limited` | bm | 1 | `icij:80111786` |

## Provenance

- Seed entity_uid: `icij:82004676`
- Edges read from: `D:\show_case\goldenmatch-shell-company-network\data\interim\icij_edges.parquet`
- Generated: `2026-05-12T05:01:58+00:00`
