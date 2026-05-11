# Cluster sub-graph centrality + communities

Source dedupe run: `ba237a6c-8a29-43a5-8d07-f0eb81473bce`
Sub-graph: 50998 nodes / 75011 edges (cluster members + direct neighbours)
Communities: 3018 (Louvain, undirected projection)

Centrality metrics computed on the *cluster sub-graph*, not the full 2M-node graph. Edges are directed ICIJ relationships (officer_of, registered_address, intermediary_of, etc.).

## Top 30 by total degree

| entity_uid | source | name | jur | cluster | community | in | out | total |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| `icij:240000001` | ? | `` |  |  | 391 | 1615 | 0 | 1615 |
| `icij:236724` | ? | `` |  |  | 503 | 1067 | 0 | 1067 |
| `icij:54662` | ? | `` |  |  | 503 | 0 | 1065 | 1065 |
| `icij:81027146` | ? | `` |  |  | 613 | 987 | 0 | 987 |
| `icij:240360001` | ? | `` |  |  | 390 | 832 | 0 | 832 |
| `icij:81027090` | ? | `` |  |  | 575 | 580 | 0 | 580 |
| `icij:80011301` | ? | `` |  |  | 613 | 0 | 468 | 468 |
| `icij:240230001` | ? | `` |  |  | 359 | 465 | 0 | 465 |
| `icij:80011987` | ? | `` |  |  | 613 | 0 | 405 | 405 |
| `icij:88002083` | ? | `` |  |  | 2181 | 350 | 0 | 350 |
| `icij:80000191` | ? | `` |  |  | 575 | 0 | 320 | 320 |
| `icij:81027087` | ? | `` |  |  | 610 | 283 | 0 | 283 |
| `icij:81029389` | ? | `` |  |  | 581 | 275 | 0 | 275 |
| `icij:82008648` | icij | `Warburg Pincus (Bermuda) Private Equity ` | bm | 499193 | 611 | 202 | 1 | 203 |
| `icij:82010864` | icij | `Coller International Partners IV-D, L.P.` | ky | 510919 | 612 | 197 | 1 | 198 |
| `icij:82011354` | icij | `Coller International Partners V-A, L.P.` | ky | 510979 | 612 | 169 | 1 | 170 |
| `icij:58007938` | ? | `` |  |  | 2668 | 150 | 0 | 150 |
| `icij:80033884` | ? | `` |  |  | 613 | 0 | 147 | 147 |
| `icij:80036326` | ? | `` |  |  | 613 | 0 | 138 | 138 |
| `icij:82000438` | icij | `Renters Reinsurance Company, Ltd.` | bm | 494208 | 618 | 131 | 2 | 133 |
| `icij:81073055` | ? | `` |  |  | 610 | 129 | 0 | 129 |
| `icij:80012109` | ? | `` |  |  | 613 | 0 | 117 | 117 |
| `icij:80015018` | ? | `` |  |  | 610 | 0 | 115 | 115 |
| `icij:82011355` | icij | `Coller International Partners V-B, L.P.` | ky | 510979 | 612 | 106 | 1 | 107 |
| `icij:85028634` | icij | `CARIBBEAN MERCANTILE BANK N.V. - CARIBBE` | aw | 491891 | 980 | 100 | 7 | 107 |
| `icij:85016455` | icij | `CARIBBEAN MERCANTILE BANK N.V. - CARIBBE` | aw | 491891 | 980 | 105 | 1 | 106 |
| `icij:80117560` | ? | `` |  |  | 613 | 0 | 105 | 105 |
| `icij:85016456` | icij | `CARIBBEAN MERCANTILE BANK N.V. - CARIBBE` | aw | 491891 | 980 | 103 | 1 | 104 |
| `icij:85002427` | icij | `CARIBBEAN MERCANTILE BANK N.V. - CARIBBE` | aw | 491891 | 980 | 102 | 1 | 103 |
| `icij:85002438` | icij | `CARIBBEAN MERCANTILE BANK N.V. - CARIBBE` | aw | 491891 | 980 | 102 | 1 | 103 |

## Top 30 by eigenvector centrality

| entity_uid | source | name | jur | cluster | community | eig |
| --- | --- | --- | --- | ---: | ---: | ---: |
| `icij:236724` | ? | `` |  |  | 503 | 0.5396 |
| `icij:54662` | ? | `` |  |  | 503 | 0.5391 |
| `icij:289359` | ? | `` |  |  | 503 | 0.0425 |
| `icij:45629` | ? | `` |  |  | 503 | 0.0378 |
| `icij:294268` | ? | `` |  |  | 503 | 0.0328 |
| `icij:295141` | ? | `` |  |  | 503 | 0.0319 |
| `icij:44082` | ? | `` |  |  | 503 | 0.0290 |
| `icij:128356` | icij | `Cathay International EW No. 3 Limited` | vg | 213075 | 503 | 0.0224 |
| `icij:128368` | icij | `Cathay International EW No. 4 Limited` | vg | 213075 | 503 | 0.0224 |
| `icij:128363` | icij | `Cathay International EW No. 34 Limited` | vg | 213075 | 503 | 0.0221 |
| `icij:128437` | icij | `Cathay International EW No. 24 Limited` | vg | 213075 | 503 | 0.0220 |
| `icij:128486` | icij | `Cathay International EW No. 25 Limited` | vg | 213075 | 503 | 0.0220 |
| `icij:128550` | icij | `Cathay International EW No. 26 Limited` | vg | 213075 | 503 | 0.0220 |
| `icij:128647` | icij | `Cathay International EW No. 23 Limited` | vg | 213075 | 503 | 0.0220 |
| `icij:124564` | icij | `Cathay International EW No. 17 Limited` | vg | 213075 | 503 | 0.0220 |
| `icij:128415` | icij | `Cathay International EW No. 21 Limited` | vg | 213075 | 503 | 0.0219 |
| `icij:128646` | icij | `Cathay International EW No. 22 Limited` | vg | 213075 | 503 | 0.0219 |
| `icij:128350` | icij | `Cathay International EW No. 5 Limited` | vg | 213075 | 503 | 0.0218 |
| `icij:128351` | icij | `Cathay International EW No. 7 Limited` | vg | 213075 | 503 | 0.0218 |
| `icij:128355` | icij | `Cathay International EW No. 6 Limited` | vg | 213075 | 503 | 0.0218 |
| `icij:128364` | icij | `Cathay International EW No. 9 Limited` | vg | 213075 | 503 | 0.0218 |
| `icij:128365` | icij | `Cathay International EW No. 8 Limited` | vg | 213075 | 503 | 0.0218 |
| `icij:128366` | icij | `Cathay International EW No. 11 Limited` | vg | 213075 | 503 | 0.0218 |
| `icij:128367` | icij | `Cathay International EW No. 10 Limited` | vg | 213075 | 503 | 0.0218 |
| `icij:126862` | icij | `Cathay International EW No. 1 Limited` | vg | 213075 | 503 | 0.0218 |
| `icij:128020` | icij | `Cathay International EW No. 14 Limited` | vg | 213075 | 503 | 0.0218 |
| `icij:128022` | icij | `Cathay International EW No. 19 Limited` | vg | 213075 | 503 | 0.0218 |
| `icij:127201` | icij | `Cathay International EW No. 18 Limited` | vg | 213075 | 503 | 0.0217 |
| `icij:128416` | icij | `Cathay International EW No. 20 Limited` | vg | 213075 | 503 | 0.0217 |
| `icij:130511` | icij | `Cathay International EW No. 2 Limited` | vg | 213075 | 503 | 0.0217 |

## Top 30 by betweenness centrality

| entity_uid | source | name | jur | cluster | community | bc |
| --- | --- | --- | --- | ---: | ---: | ---: |
| `icij:81027090` | ? | `` |  |  | 575 | 0.0145 |
| `icij:240000001` | ? | `` |  |  | 391 | 0.0136 |
| `icij:80011301` | ? | `` |  |  | 613 | 0.0107 |
| `icij:82009376` | icij | `CAI (PTC) Limited` | bm | 494264 | 575 | 0.0102 |
| `icij:240360001` | ? | `` |  |  | 390 | 0.0099 |
| `icij:81027146` | ? | `` |  |  | 613 | 0.0088 |
| `icij:240450008` | ? | `` |  |  | 389 | 0.0079 |
| `icij:240460548` | icij | `CARY INTERNATIONAL LIMITED` | vg | 686162 | 389 | 0.0078 |
| `icij:240371533` | icij | `CARY INTERNATIONAL LIMITED` | vg | 686162 | 389 | 0.0078 |
| `icij:88002083` | ? | `` |  |  | 2181 | 0.0078 |
| `icij:80000191` | ? | `` |  |  | 575 | 0.0055 |
| `icij:81029389` | ? | `` |  |  | 581 | 0.0043 |
| `icij:81027087` | ? | `` |  |  | 610 | 0.0035 |
| `icij:88006968` | ? | `` |  |  | 1180 | 0.0033 |
| `icij:88007215` | ? | `` |  |  | 2013 | 0.0026 |
| `icij:88006490` | ? | `` |  |  | 2013 | 0.0026 |
| `icij:88006854` | ? | `` |  |  | 1334 | 0.0025 |
| `icij:54662` | ? | `` |  |  | 503 | 0.0024 |
| `icij:236724` | ? | `` |  |  | 503 | 0.0024 |
| `icij:80011987` | ? | `` |  |  | 613 | 0.0022 |
| `icij:58007938` | ? | `` |  |  | 2668 | 0.0022 |
| `icij:81001128` | ? | `` |  |  | 584 | 0.0022 |
| `icij:88006771` | ? | `` |  |  | 2130 | 0.0021 |
| `icij:81015145` | ? | `` |  |  | 610 | 0.0019 |
| `icij:85007893` | icij | `RIALTO RITZ` | aw | 518535 | 1334 | 0.0018 |
| `icij:82023813` | icij | `Golden Aviation Limited` | vg | 129696 | 613 | 0.0017 |
| `icij:80060564` | ? | `` |  |  | 610 | 0.0017 |
| `icij:56072048` | ? | `` |  |  | 2548 | 0.0017 |
| `icij:85002067` | icij | `RIALTO RITZ` | aw | 518535 | 1334 | 0.0016 |
| `icij:82012347` | icij | `Appleby Protectors (Cayman) Limited` | ky | 510092 | 613 | 0.0016 |

## Top 30 communities by size

| community_id | size |
| ---: | ---: |
| 391 | 3518 |
| 503 | 3398 |
| 613 | 2697 |
| 575 | 2669 |
| 390 | 1816 |
| 2181 | 1097 |
| 359 | 1096 |
| 610 | 1060 |
| 581 | 1000 |
| 2668 | 770 |
| 2013 | 701 |
| 2548 | 645 |
| 612 | 585 |
| 2471 | 555 |
| 2600 | 509 |
| 389 | 498 |
| 1924 | 466 |
| 2342 | 406 |
| 611 | 400 |
| 1334 | 400 |
| 2339 | 383 |
| 584 | 377 |
| 1131 | 373 |
| 2372 | 315 |
| 2130 | 307 |
| 623 | 297 |
| 1180 | 283 |
| 2147 | 274 |
| 2199 | 256 |
| 2417 | 241 |
