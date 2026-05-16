# vadim samoylenko

**Sources:** 3 (opensanctions, uk_psc, icij)  •  **Linked companies:** 2  •  **Jurisdictions:** vg  •  **Novelty score:** 0.56

_Normalized name in source data: `mr vadim samoylenko` — honorifics stripped for display._

## Shared-address shell clusters

_Multiple ICIJ-linked companies registered at the same address — the shell-network shape the spec was designed to surface._

- `sergey sobolev graff international partners k s dobroluybova street house 2 building 1 moscow moskva` (vg) — 2 companies: BARNSLEY INTERINVEST LIMITED; MARTLAND PROJECT LIMITED

## Linked entities by source
### icij (2 entities)
- MR. VADIM SAMOYLENKO — `icij:13006329` — country: ru
- MR. VADIM SAMOYLENKO — `icij:13001554` — country: ru

**Linked companies (ICIJ 2-hop walk):**
- MARTLAND PROJECT LIMITED (vg) — address: `sergey sobolev graff international partners k s dobroluybova street house 2 buil`
- BARNSLEY INTERINVEST LIMITED (vg) — address: `sergey sobolev graff international partners k s dobroluybova street house 2 buil`

### opensanctions (1 entity)
- Mr Vadim Samoylenko — `opensanctions:gb-coh-psc-OC428060-drumcnpjiu6cpmlkd4at96rmbw8` — country: ru
  _(stub only — no person→company relations parquet for opensanctions in v1)_

### uk_psc (1 entity)
- Mr Vadim Samoylenko — `uk_psc:966ec9e7-a0c6-0309-d7bd-eac348eb337d` — country: ru
  _(stub only — no person→company relations parquet for uk_psc in v1)_

## Web search (firecrawl, 2026-05-16)

### `"mr vadim samoylenko" (shell OR offshore OR director OR PSC)` — 3 hits
- [MR. VADIM SAMOYLENKO \| ICIJ Offshore Leaks Database](https://offshoreleaks.icij.org/nodes/13006329) — _Panama Papers Officer: MR. VADIM SAMOYLENKO. ... Explore the offshore connections of world leaders ... Offshore Leaks investigations. The records cover ..._
- [PAWELL SHIPPING COMPANY LLP - OpenSanctions](https://www.opensanctions.org/entities/NK-477D8rZZPKwcLJNRAWNbUC/) — _The Director Disqualification Sanction was imposed on 09/04/2025. — UK FCDO ... Mr Vadim Samoylenko, -, 2019-07-15, 2020-06-17. Ms Maria Vovk, -, 2020-06-17 ..._
- [PAWELL SHIPPING CO LLP - YouControl](https://youcontrol.com.ua/en/catalog/gb-card/oc428060/) — _Mr Vadim Samoylenko. Status: Not active. Notified on: Monday, 15 July 2019. Correspondence address: 205 Maysnikovskiy District, Russia. Nationality: Russian._

### `"mr vadim samoylenko"` — 3 hits
- [MR. VADIM SAMOYLENKO \| ICIJ Offshore Leaks Database](https://offshoreleaks.icij.org/nodes/13006329) — _Entity (1). Role, From, To, Incorporation, Jurisdiction, Status · MARTLAND PROJECT LIMITED ; Officer (1). Role, From, To · MR. VADIM SAMOYLENKO ; Address (1) · APT._
- [PAWELL SHIPPING COMPANY LLP - OpenSanctions](https://www.opensanctions.org/entities/NK-477D8rZZPKwcLJNRAWNbUC/) — _Mr Vadim Samoylenko, -, 2019-07-15, 2020-06-17. Ms Maria Vovk, -, 2020-06-17, -. Data sources#. Ukraine War and Sanctions15,937. Sponsors and accomplices of ..._
- [PAWELL SHIPPING CO LLP - YouControl](https://youcontrol.com.ua/en/catalog/gb-card/oc428060/) — _Mr Vadim Samoylenko. Status: Not active. Notified on: Monday, 15 July 2019. Correspondence address: 205 Maysnikovskiy District, Russia. Nationality: Russian._

### `"mr vadim samoylenko" vg` — 0 hits
_No hits._

## Reproduce

- `processed/rare_officer_dossiers.parquet`, filter `rare_name == "mr vadim samoylenko"`
- Search ran via `scripts/search_dossier_freshness.py` on 2026-05-16
