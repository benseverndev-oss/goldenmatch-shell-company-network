# GLEIF L2 ownership chains — asset-frozen entities + adjacent

Generated from OS entities filtered by topic == `sanction` AND datasets containing any of ['us_ofac', 'eu_fsf', 'gb_hmt'].

> **Hypothesis, not proof.** Each chain is a registry-disclosed corporate ownership link via GLEIF Level 2. The fact that one end is OFAC/EU/UK asset-frozen and the other isn't is a *lead* that warrants human review (and possibly secondary-sanctions designation), not a finding. Names may be common; LEI plus jurisdiction is the discriminator.

## Summary

- Directly-sanctioned LEIs (topic == `sanction`, on OFAC/EU/UK lists): **533**
- Edges with both ends sanctioned: **127**
- Edges with exactly one end sanctioned (not-yet-sanctioned neighbour): **390**

## Both-ends-sanctioned chains

Pre-existing intra-sanctioned-network corporate-ownership links. Both endpoints are already on the asset-freeze lists.

| controlled (src) | controller (dst) |
| --- | --- |
| `25340038P8SYW80B9W34` Belvnesheconombank OJSC | `25340076UP17XECUF417` ГОСУДАРСТВЕННАЯ КОРПОРАЦИЯ "БАНК РАЗВИТИЯ И ВНЕШНЕ ЭКОНОМИЧЕ |
| `25340038P8SYW80B9W34` Belvnesheconombank OJSC | `25340076UP17XECUF417` ГОСУДАРСТВЕННАЯ КОРПОРАЦИЯ "БАНК РАЗВИТИЯ И ВНЕШНЕ ЭКОНОМИЧЕ |
| `253400T0B3YA0V01TL29` Товариство з обмеженою відповідальністю інвестиційна компані | `253400XSJ4C01YMCXG44` PUBLICHNOE AKTSIONERNOE OBSCHESTVO MAGNITOGORSKIY METALLURGI |
| `253400T0B3YA0V01TL29` Товариство з обмеженою відповідальністю інвестиційна компані | `253400XSJ4C01YMCXG44` PUBLICHNOE AKTSIONERNOE OBSCHESTVO MAGNITOGORSKIY METALLURGI |
| `213800DHNUILNIQRED05` Общество с ограниченной ответственностью "Полюс Сервис" | `549300FUXVT7TF6ZKV71` Polyus - Nyilvánosan Működő Részvénytársaság |
| `213800DHNUILNIQRED05` Общество с ограниченной ответственностью "Полюс Сервис" | `549300FUXVT7TF6ZKV71` Polyus - Nyilvánosan Működő Részvénytársaság |
| `254900F23AOTVJF93825` BANCO VTB AFRICA SA | `253400V1H6ART1UQ0N98` Банк ВТБ (ПАО) |
| `254900F23AOTVJF93825` BANCO VTB AFRICA SA | `253400V1H6ART1UQ0N98` Банк ВТБ (ПАО) |
| `254900JHWE3G4G31ZK94` BANK VTB KAZAKHSTAN JSC | `253400V1H6ART1UQ0N98` Банк ВТБ (ПАО) |
| `254900JHWE3G4G31ZK94` BANK VTB KAZAKHSTAN JSC | `253400V1H6ART1UQ0N98` Банк ВТБ (ПАО) |
| `549300186QXM3QH30R53` Otkritie Capital Ltd | `253400D1T9WFNN3BTT91` Bank "Otkritie Financial Corporation" PJSC |
| `549300186QXM3QH30R53` Otkritie Capital Ltd | `253400EB56NKL2M3WT18` The Central Bank Of The Russian Federation |
| `635400I6H6CSZ39WIN49` Gtlk Europe Capital DAC | `635400FDT7BRRHTMEC11` GTLK Europe DAC |
| `213800FYT591NMMOL156` Volzhskiy Trubnyi Zavod JSC | `213800TF7S5EDO6V3K66` ОТКРЫТОЕ АКЦИОНЕРНОЕ ОБЩЕСТВО " ТРУБНАЯ МЕТАЛЛУРГИЧЕСКАЯ КОМ |
| `25340038P8SYW80B9W34` Belvnesheconombank OJSC | `25340076UP17XECUF417` ГОСУДАРСТВЕННАЯ КОРПОРАЦИЯ "БАНК РАЗВИТИЯ И ВНЕШНЕ ЭКОНОМИЧЕ |
| `25340038P8SYW80B9W34` Belvnesheconombank OJSC | `25340076UP17XECUF417` ГОСУДАРСТВЕННАЯ КОРПОРАЦИЯ "БАНК РАЗВИТИЯ И ВНЕШНЕ ЭКОНОМИЧЕ |
| `253400YB0S6B5P046G59` JSC SAROVBUSINESSBANK | `253400V1H6ART1UQ0N98` Банк ВТБ (ПАО) |
| `2534007UK6G30KDX1A47` National Clearing Centre | `253400M5M1222KPNWE87` MICEX-RTS PJSC |
| `2534007UK6G30KDX1A47` National Clearing Centre | `253400M5M1222KPNWE87` MICEX-RTS PJSC |
| `2534009M60TLJ672C190` Товариство з обмеженою відповідальністю "Альфа-Форекс" | `253400QWEQNERA6RJS29` AO "ALFA-BANK" |
| `25490097TSPULKFOF602` Mighty Divine Global Fund SPC | `254900IYH8RHI6KT4P60` MIGHTY DIVINE INVESTMENT MANAGEMENT LIMITED |
| `52990002BY85ORK97W78` GPB (SWITZERLAND) LTD | `253400WSS48YWMBUA688` акционерное общество «Газпром Банк» |
| `52990002BY85ORK97W78` GPB (SWITZERLAND) LTD | `253400WSS48YWMBUA688` акционерное общество «Газпром Банк» |
| `253400CW8F4L53HWU734` Общество с ограниченной ответственностью "Бланк банк" | `2534000R9X3PNNE57C55` Credit Bank of Moscow |
| `253400GU1G2W8L6L3885` VOSTOCHNY CAPITAL MANAGEMENT COMPANY LLC | `253400BBBP7990NS0M56` SOVCOMBANK OPEN JOINT STOCK COMPANY |
| `253400T0B3YA0V01TL29` Товариство з обмеженою відповідальністю інвестиційна компані | `253400XSJ4C01YMCXG44` PUBLICHNOE AKTSIONERNOE OBSCHESTVO MAGNITOGORSKIY METALLURGI |
| `253400T0B3YA0V01TL29` Товариство з обмеженою відповідальністю інвестиційна компані | `253400XSJ4C01YMCXG44` PUBLICHNOE AKTSIONERNOE OBSCHESTVO MAGNITOGORSKIY METALLURGI |
| `253400WMV1LDNKA3P870` Публичное акционерное общество МОСКОВСКИЙ ОБЛАСТНОЙ БАНК | `VX43JDHPWL0M8GQ0QU45` Публичное акционерное общество "Банк ПСБ" |
| `253400WMV1LDNKA3P870` Публичное акционерное общество МОСКОВСКИЙ ОБЛАСТНОЙ БАНК | `VX43JDHPWL0M8GQ0QU45` Публичное акционерное общество "Банк ПСБ" |
| `213800NCOJLY8JW3YI89` Bank Sepah International PLC | `5493008Z30ZS378SB107` バンク・セパ |
| `213800NCOJLY8JW3YI89` Bank Sepah International PLC | `5493008Z30ZS378SB107` バンク・セパ |
| `25490097TSPULKFOF602` Mighty Divine Global Fund SPC | `254900IYH8RHI6KT4P60` MIGHTY DIVINE INVESTMENT MANAGEMENT LIMITED |
| `254900CSJGVBZ6CA9D24` Xing Ao Energy Pte Ltd | `655600I0RTPZ3DFASH49` 河北鑫海化工集团有限公司 |
| `254900CSJGVBZ6CA9D24` Xing Ao Energy Pte Ltd | `655600I0RTPZ3DFASH49` 河北鑫海化工集团有限公司 |
| `549300FD9UH07N44ZX88` Azoria Shipping Company Limited | `253400DYLWR5A6YAWJ69` Sovcomflot |
| `549300BV4X39ITLG4R60` Gazprombank Latin America Ventures BV | `549300E5KHMX548FFZ34` GPB GLOBAL RESOURCES B.V. |
| `549300BV4X39ITLG4R60` Gazprombank Latin America Ventures BV | `549300E5KHMX548FFZ34` GPB GLOBAL RESOURCES B.V. |
| `74780080B3J1A5AOWK36` Nis Ad Novi Sad | `253400KXA9P2AN72P004` Московський філіал Відкритого акціонерного товариства "Газпр |
| `74780080B3J1A5AOWK36` Nis Ad Novi Sad | `213800FD9J2IHTA7YX78` ПУБЛИЧНОЕ АКЦИОНЕРНОЕ ОБЩЕСТВО"ГАЗПРОМ" |
| `2534002GCABZ5KDN2B87` OBSHCHESTVO S OGRANICHENNOI OTVETSTVENNOSTYU EVRAZKHOLDING F | `5493005B7DAN39RXLK23` EVRAZ |
| _… 87 more rows_ | |

## Sanctioned parent → not-yet-sanctioned subsidiaries

Each row is one *children-of* group: a sanctioned entity at the top, followed by GLEIF L2 subsidiaries that are not (yet) on the asset-freeze lists. These are the candidate secondary-sanctions targets.

### `549300LCJ1UJXHYBWI24` Lukoil Public Joint Stock Company

- `2549005D4COOXVIAJQ13` TSP FINANCE COMPANY LTD
- `K80PJMCDA9MAE5C8IO91` LITASCO SA
- `724500LG1GUKJ5TOIW61` LUKOIL International Finance B.V.
- `213800FXBZXOXNXKWP95` LUKOIL SECURITIES LIMITED
- `213800FXBZXOXNXKWP95` LUKOIL SECURITIES LIMITED
- `485100TJJ5MAH4VCVF30` LUKOIL Neftohim Burgas AD
- `5299000ZX0XHOS3HT426` (name not in OS — pull GLEIF entity record for full name)
- `5299000ZX0XHOS3HT426` (name not in OS — pull GLEIF entity record for full name)
- `9845007AC47F8H858B51` AC MANAGEMENT COMPANY LIMITED
- `72450024EGZK2K8NAG02` LUKOIL Finance B.V.
- `7872006AZAFVTVIQ3G32` PETROTEL-LUKOIL SA
- `7872006AZAFVTVIQ3G32` PETROTEL-LUKOIL SA
- `2534008CRS9Q4TCJ0Q32` Общество с ограниченной ответственностью "ЛУКОЙЛ-Резервнефтепродукт-Трейдинг"
- `2534008CRS9Q4TCJ0Q32` Общество с ограниченной ответственностью "ЛУКОЙЛ-Резервнефтепродукт-Трейдинг"
- `5299007PQV6X4DPL9Y20` Lukoil International Gmbh
- _… 24 more_

### `549300XIVJCBIGMRUD48` CNOOC Limited (a subsidiary of China National Offshore Oil Corporation

- `549300QK7VNAZ4SHZS12` CNOOC FINANCE (2014) ULC
- `549300RN0NNG8YN46M57` NEXEN PETROLEUM NIGERIA LIMITED
- `5493006KAH3PSSMCES09` CNOOC Finance (2013) Limited
- `549300I04PB7X2824122` CNOOC Petroleum North America
- `213800XVGNY3635WQB24` CNOOC U.K. MARKETING LTD
- `5493006KAH3PSSMCES09` CNOOC Finance (2013) Limited
- `549300KSB04UT8CS3T40` CNOOC Finance (2003) Limited
- `549300RN0NNG8YN46M57` NEXEN PETROLEUM NIGERIA LIMITED
- `549300I04PB7X2824122` CNOOC Petroleum North America
- `5493006KAH3PSSMCES09` CNOOC Finance (2013) Limited
- `5493006KAH3PSSMCES09` CNOOC Finance (2013) Limited
- `SA0EED3S78SK0QZJ1S18` CNOOC Marketing Canada
- `549300QK7VNAZ4SHZS12` CNOOC FINANCE (2014) ULC
- `549300KSB04UT8CS3T40` CNOOC Finance (2003) Limited
- `549300KSB04UT8CS3T40` CNOOC Finance (2003) Limited
- _… 6 more_

### `213800JSZ2UUK4QQK694` PJSC ‘Motovilikhinskiye Zavody'

- `253400801C3YP0QS5A62` (name not in OS — pull GLEIF entity record for full name)
- `2534008FX8EXH1FMJA74` MTS
- `2534008FX8EXH1FMJA74` MTS
- `2534004JKXBEM0T4LW33` Акционерное общество "Система Финанс"
- `2534004JKXBEM0T4LW33` Акционерное общество "Система Финанс"
- `253400801C3YP0QS5A62` (name not in OS — pull GLEIF entity record for full name)
- `2534008FX8EXH1FMJA74` MTS
- `2534008FX8EXH1FMJA74` MTS
- `253400M8F9ZXY9CN3U71` Общество с ограниченной ответственностью "Система Телеком Активы"
- `253400M8F9ZXY9CN3U71` Общество с ограниченной ответственностью "Система Телеком Активы"
- `253400QD4JHES5PGDR15` Dega Retail Holding Limited
- `253400YCVQ7DZPFUWH47` Общество с ограниченной ответственностью "Бастион"
- `2534004JKXBEM0T4LW33` Акционерное общество "Система Финанс"
- `2534004JKXBEM0T4LW33` Акционерное общество "Система Финанс"
- `254900YJTZ2JT3ZSZS32` SISTEMA ASIA FUND PTE. LTD.
- _… 6 more_

### `213800FD9J2IHTA7YX78` ПУБЛИЧНОЕ АКЦИОНЕРНОЕ ОБЩЕСТВО"ГАЗПРОМ"

- `213800UNP9N6BPNYMQ45` GAZ FINANCE PLC
- `213800UNP9N6BPNYMQ45` GAZ FINANCE PLC
- `253400BA8SBX73FTSY30` Общество с ограниченной ответственностью "Газпром экспорт"
- `253400BA8SBX73FTSY30` Общество с ограниченной ответственностью "Газпром экспорт"
- `253400U464BV6CWFSP06` ОТКРЫТОЕ АКЦИОНЕРНОЕ ОБЩЕСТВО "ГАЗПРОМ ГАЗОРАСПРЕДЕЛЕНИЕ"
- `253400BA8SBX73FTSY30` Общество с ограниченной ответственностью "Газпром экспорт"
- `253400BA8SBX73FTSY30` Общество с ограниченной ответственностью "Газпром экспорт"
- `529900NO5DX9WP6BVS50` (name not in OS — pull GLEIF entity record for full name)
- `724500M3ZGNKQ8Y95460` (name not in OS — pull GLEIF entity record for full name)
- `724500M3ZGNKQ8Y95460` (name not in OS — pull GLEIF entity record for full name)
- `54930066L2C7E3XB4I78` DRIADUS INVESTMENTS LIMITED
- `529900SFSY70GU4R8868` Wienerberger - Sisteme de Caramizi SRL
- `529900SFSY70GU4R8868` Wienerberger - Sisteme de Caramizi SRL
- `213800UNP9N6BPNYMQ45` GAZ FINANCE PLC
- `213800UNP9N6BPNYMQ45` GAZ FINANCE PLC
- _… 1 more_

### `5493009YJ817TFZ7IY48` Swiru Holding AG

- `5493000HYVYGGJD6WD50` Watertight International Inc.
- `5493000HYVYGGJD6WD50` Watertight International Inc.
- `549300JPG0LATOO6U958` IFI Estates S.A.
- `549300JPG0LATOO6U958` IFI Estates S.A.
- `549300UOZWP600U87905` VH Estates S.A.
- `549300UOZWP600U87905` VH Estates S.A.
- `549300TI4Z3BV40ZZS46` Rayblue International Corp.
- `549300TI4Z3BV40ZZS46` Rayblue International Corp.
- `5493004SVYFTS2420V43` CDA Investment S.A.
- `549300A111N4Z3HU2S06` SGI Investment Group Ltd.
- `549300A111N4Z3HU2S06` SGI Investment Group Ltd.
- `549300X9D1GFNNYNLM74` Burlington Properties S.A.
- `549300X9D1GFNNYNLM74` Burlington Properties S.A.

### `HOXMZG026UQNRK6J0C60` Javno dioničko društvo Rosbank

- `25340025EEVZ9ZWKJB62` Общество с ограниченной ответственностью "РБ Сервис"
- `25340025EEVZ9ZWKJB62` Общество с ограниченной ответственностью "РБ Сервис"
- `2534006R1P1QVPP0QY05` Общество с ограниченной ответственностью "РБ Факторинг"
- `253400A72AVL4HETJJ04` Общество с ограниченной ответственностью Управляющая компания "Эра Инвестиций"
- `253400A72AVL4HETJJ04` Общество с ограниченной ответственностью Управляющая компания "Эра Инвестиций"
- `253400HT8W559RHRJD67` Общество с ограниченной ответственностью "РУСФИНАНС"
- `253400HT8W559RHRJD67` Общество с ограниченной ответственностью "РУСФИНАНС"
- `253400LXY16NWXD91X50` Общество с ограниченной ответственностью "РБ ЛИЗИНГ"
- `253400LXY16NWXD91X50` Общество с ограниченной ответственностью "РБ ЛИЗИНГ"
- `253400PKJ6ENZH6TNB51` Общество с ограниченной ответственностью РБ Трейдинг
- `253400PKJ6ENZH6TNB51` Общество с ограниченной ответственностью РБ Трейдинг
- `253400SFPE4HAPQ7E257` Общество с ограниченной ответственностью "Телсиком"
- `253400SFPE4HAPQ7E257` Общество с ограниченной ответственностью "Телсиком"

### `2138008R6GCRVBDFA581` ОТКРЫТОЕ АКЦИОНЕРНОЕ ОБЩЕСТВО "ФИНАНСОВО-ИНВЕСТИЦИОННАЯ КОМПАНИЯ "НОВА

- `213800PLONZRLEIL5O33` Новатек Гез енд Павер Азія Прайвет Лтд.
- `213800PLONZRLEIL5O33` Новатек Гез енд Павер Азія Прайвет Лтд.
- `9845009D478FC6FD9X22` NOVATEK ASIA DEVELOPMENT HOLDING PTE. LTD.
- `9845009D478FC6FD9X22` NOVATEK ASIA DEVELOPMENT HOLDING PTE. LTD.
- `2138002S2PUI8UJTCW32` Новатек Гез енд Павер ГмбХ
- `2138002S2PUI8UJTCW32` Новатек Гез енд Павер ГмбХ
- `259400ARXZZ95TN6NB50` Novatek Green Energy Sp. z o.o.
- `259400ARXZZ95TN6NB50` Novatek Green Energy Sp. z o.o.
- `2138002S2PUI8UJTCW32` Новатек Гез енд Павер ГмбХ
- `2138002S2PUI8UJTCW32` Новатек Гез енд Павер ГмбХ
- `54930061YME13P5ACZ80` (name not in OS — pull GLEIF entity record for full name)
- `54930061YME13P5ACZ80` (name not in OS — pull GLEIF entity record for full name)

### `253400DYLWR5A6YAWJ69` Sovcomflot

- `549300D5RCZXC01LFR21` PURPOSEFUL CORPORATION
- `549300DV9MBCETFDQK65` GLOBAL CHALLENGE SHIPPING COMPANY LIMITED
- `549300UHLMV4C8PJXC82` ENSAY SHIPPING LIMITED
- `549300T8W114GXW7VJ40` SERAFINA ENTERPRISES INCORPORATED
- `549300T8W114GXW7VJ40` SERAFINA ENTERPRISES INCORPORATED
- `549300TBS8P1G7YT9554` DAFNE LINE SHIPPING COMPANY LIMITED
- `549300TQK1L0OB4BLA83` PABBAY SHIPPING LIMITED
- `549300HP592ZBPX8ZQ58` BORERAY SHIPPING LIMITED
- `549300IK6JC36UQF2U15` HEADLINER MARITIME S.A.
- `5493008SD1AMV0GACM32` SCALPAY SHIPPING LIMITED
- `54930092VOQEBHRVRR40` ALBUS SHIPPING LIMITED

### `213800ZZOU5P76L8XB92` a.k.a. Atlas Mining LLC

- `213800CTKD5CPG2DR188` (name not in OS — pull GLEIF entity record for full name)
- `213800CTKD5CPG2DR188` (name not in OS — pull GLEIF entity record for full name)
- `213800IJHR39Z98KEW82` Petropavlovsk 2010 Limited
- `213800IJHR39Z98KEW82` Petropavlovsk 2010 Limited
- `213800IJHR39Z98KEW82` Petropavlovsk 2010 Limited
- `213800IJHR39Z98KEW82` Petropavlovsk 2010 Limited
- `213800RHF5YBDQJD4L03` CAYIRON LIMITED
- `213800RHF5YBDQJD4L03` CAYIRON LIMITED
- `213800CTKD5CPG2DR188` (name not in OS — pull GLEIF entity record for full name)
- `213800CTKD5CPG2DR188` (name not in OS — pull GLEIF entity record for full name)

### `529900LWYPVP93SJ2U42` China Communications Construction Co. Ltd.

- `959800ERQR68W4NMZ613` ESTRUCTURAS Y MONTAJE DE PREFABRICADOS S.A
- `959800H3JWA8GP8M8F73` PUENTES Y CALZADAS INFRAESTRUCTURAS SLU
- `959800RDSNAPGK786L84` PREFABRICADOS TECNOLOGICOS DEL HORMIGON SL
- `959800S6J8JJ6ZL93573` ELABORACION Y MONTAJE DE ARMADURAS S.A
- `959800UQ4WENQFQJM545` PUENTES Y CALZADAS GRUPO DE EMPRESAS S.A
- `959800ERQR68W4NMZ613` ESTRUCTURAS Y MONTAJE DE PREFABRICADOS S.A
- `959800H3JWA8GP8M8F73` PUENTES Y CALZADAS INFRAESTRUCTURAS SLU
- `959800RDSNAPGK786L84` PREFABRICADOS TECNOLOGICOS DEL HORMIGON SL
- `959800S6J8JJ6ZL93573` ELABORACION Y MONTAJE DE ARMADURAS S.A
- `959800UQ4WENQFQJM545` PUENTES Y CALZADAS GRUPO DE EMPRESAS S.A

### `253400V1H6ART1UQ0N98` Банк ВТБ (ПАО)

- `335800LW6BBDNFASPG17` (name not in OS — pull GLEIF entity record for full name)
- `74OG4PIVJ3TT4O5NSN12` VTB Bank Europe Plc
- `74OG4PIVJ3TT4O5NSN12` VTB Bank Europe Plc
- `253400N2R0RF14JQ0060` Акционерное общество Арована Капитал
- `2549003TD6LLFXE2E197` VTB Capital Russia & CIS Fixed Income Fund Ltd.
- `25490071D47DFCHOZ745` VTB Capital Russia & CIS Equity Fund Ltd.
- `335800LW6BBDNFASPG17` (name not in OS — pull GLEIF entity record for full name)
- `254900XHIMTHLHK4JK65` VTB Leasing (Europe) Limited
- `254900LNPJ6HZDLTSJ15` VTBC Asset Management International Limited

### `300300AY5BEBCYDR2F31` China National Offshore Oil Corporation

- `5493006KAH3PSSMCES09` CNOOC Finance (2013) Limited
- `5493006KAH3PSSMCES09` CNOOC Finance (2013) Limited
- `549300KSB04UT8CS3T40` CNOOC Finance (2003) Limited
- `300300456LYTMECHLJ21` 中海石油化工进出口有限公司
- `300300456LYTMECHLJ21` 中海石油化工进出口有限公司
- `5493006KAH3PSSMCES09` CNOOC Finance (2013) Limited
- `5493006KAH3PSSMCES09` CNOOC Finance (2013) Limited
- `549300KSB04UT8CS3T40` CNOOC Finance (2003) Limited

### `549300WE6TAF5EEWQS81` ОТКРЫТОЕ АКЦИОНЕРНОЕ ОБЩЕСТВО

- `F68F5WN6OGTEHIP5ZT82` SIB (CYPRUS) LIMITED
- `506700AUNEQF0C694855` Sber Trading Swiss AG
- `549300BKWHXYEXPV0328` SBERBANK CIB (UK) LIMITED
- `253400EUHVTSUKPJXL42` (name not in OS — pull GLEIF entity record for full name)
- `253400EUHVTSUKPJXL42` (name not in OS — pull GLEIF entity record for full name)
- `549300L1G21ZCED8UN98` SBGB CYPRUS LIMITED
- `31570010000000029583` Sberbank CZ V likvidaci as
- `529900YLHSF7E5PF9A73` V-Dat Informatikai Szolgáltató és Kereskedelmi Korlátolt Felelősségü Társaság

### `213800OKDPTV6K4ONO53` Severstal' PAO

- `259400K9K1EPHLZ2NJ95` СІА "Сєверсталь Дистриб'юшн"
- `259400K9K1EPHLZ2NJ95` СІА "Сєверсталь Дистриб'юшн"
- `259400K9K1EPHLZ2NJ95` СІА "Сєверсталь Дистриб'юшн"
- `259400K9K1EPHLZ2NJ95` СІА "Сєверсталь Дистриб'юшн"
- `549300W88RLKPUPT5X89` MELSONDA HOLDINGS LIMITED
- `5493005HEI4KQBOLWW87` Cambay Services Limited
- `5493009Q8TVWEGQE5H68` ABIGROVE LIMITED

### `253400JT3MQWNDKMJE44` PUBLIC JOINT-STOCK COMPANY ROSNEFT OIL COMPANY

- `25340076BE9D5XUK4H54` Общество с ограниченной ответственностью "РН-Капитал"
- `253400EDWTVJSHMJ4D40` Общество с ограниченной ответственностью "ДИНК-ИНВЕСТ"
- `391200PKEUF3Y2NUMW25` Rosneft Deutschland
- `391200PKEUF3Y2NUMW25` Rosneft Deutschland
- `253400EDWTVJSHMJ4D40` Общество с ограниченной ответственностью "ДИНК-ИНВЕСТ"
- `253400EDWTVJSHMJ4D40` Общество с ограниченной ответственностью "ДИНК-ИНВЕСТ"
- `25340076BE9D5XUK4H54` Общество с ограниченной ответственностью "РН-Капитал"

### `5493005B7DAN39RXLK23` EVRAZ

- `549300LN6T6MYMUY9357` EAST METALS AG IN LIQUIDATION
- `549300LN6T6MYMUY9357` EAST METALS AG IN LIQUIDATION
- `54930080DFVZ551GGT17` ЕВРАЗ ГРУП С.А.
- `54930080DFVZ551GGT17` ЕВРАЗ ГРУП С.А.
- `549300LN6T6MYMUY9357` EAST METALS AG IN LIQUIDATION

### `253400WD8ULWSUGGXP64` Акционерное общество Банк Синара

- `253400KDCJH4J89WM664` (name not in OS — pull GLEIF entity record for full name)
- `253400D41E6VN0NCHW49` АО "Газэнергобанк"
- `253400KDCJH4J89WM664` (name not in OS — pull GLEIF entity record for full name)
- `253400D41E6VN0NCHW49` АО "Газэнергобанк"

### `253400XEMNQ5WBPN5635` Ak Bars Bank

- `253400S8T8CGUUR3P751` (name not in OS — pull GLEIF entity record for full name)
- `253400S8T8CGUUR3P751` (name not in OS — pull GLEIF entity record for full name)
- `253400S8T8CGUUR3P751` (name not in OS — pull GLEIF entity record for full name)
- `253400S8T8CGUUR3P751` (name not in OS — pull GLEIF entity record for full name)

### `5299008NK571QZL7CF97` Centrex Europe Energy & Gas AG

- `529900L80WEGMSUN9X14` CENTREX ITALIA S.P.A.
- `529900L80WEGMSUN9X14` CENTREX ITALIA S.P.A.
- `529900L80WEGMSUN9X14` CENTREX ITALIA S.P.A.
- `529900L80WEGMSUN9X14` CENTREX ITALIA S.P.A.

### `VX43JDHPWL0M8GQ0QU45` Публичное акционерное общество "Банк ПСБ"

- `253400D7J0M5W58DHL79` Joint-Stock Company «St. Petersburg Currency Exchange»
- `253400D7J0M5W58DHL79` Joint-Stock Company «St. Petersburg Currency Exchange»
- `253400D7J0M5W58DHL79` Joint-Stock Company «St. Petersburg Currency Exchange»
- `253400D7J0M5W58DHL79` Joint-Stock Company «St. Petersburg Currency Exchange»

### `253400GMWZ0DBU6G0E87` INSURANCE PUBLIC JOINT-STOCK COMPANY "INGOSSTRAKH"

- `2534005A0H3F1ETBW010` Акционерное общество Управляющая компания "Ингосстрах - Инвестиции"
- `253400GCG0X8W4X00156` (name not in OS — pull GLEIF entity record for full name)
- `253400GCG0X8W4X00156` (name not in OS — pull GLEIF entity record for full name)
- `2534005A0H3F1ETBW010` Акционерное общество Управляющая компания "Ингосстрах - Инвестиции"

### `253400BEVESMWQRXBQ11` Bank Saint-Petersburg Public Joint Stock Company

- `2534006PW83DFZHA8W75` ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ "БСПБ КАПИТАЛ"
- `2534006PW83DFZHA8W75` ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ "БСПБ КАПИТАЛ"
- `2534006PW83DFZHA8W75` ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ "БСПБ КАПИТАЛ"
- `2534006PW83DFZHA8W75` ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ "БСПБ КАПИТАЛ"

### `253400397QM0B6AM0H48` Joint Stock Commercial Bank International Financial Club

- `253400A0TJAPQ45B2A12` TAVRICHESKY BANK (JOINT-STOCK COMPANY)
- `253400A0TJAPQ45B2A12` TAVRICHESKY BANK (JOINT-STOCK COMPANY)
- `253400A0TJAPQ45B2A12` TAVRICHESKY BANK (JOINT-STOCK COMPANY)
- `253400A0TJAPQ45B2A12` TAVRICHESKY BANK (JOINT-STOCK COMPANY)

### `253400MF70R9W1E92E58` BALTIC DEVELOPMENT BANK CLOSED JOINT STOCK COMPANY

- `253400DDXRL535CQ5T91` Общество с ограниченной ответственностью "ББР БРОКЕР"
- `253400DDXRL535CQ5T91` Общество с ограниченной ответственностью "ББР БРОКЕР"
- `253400DDXRL535CQ5T91` Общество с ограниченной ответственностью "ББР БРОКЕР"
- `253400DDXRL535CQ5T91` Общество с ограниченной ответственностью "ББР БРОКЕР"

### `253400D1T9WFNN3BTT91` Bank "Otkritie Financial Corporation" PJSC

- `253400QJ9FJ1W4HEEX74` Общество с ограниченной ответственностью Страховая компания "Росгосстрах Жизнь"
- `253400Y63ZZGPKB9GP20` (name not in OS — pull GLEIF entity record for full name)
- `253400Y63ZZGPKB9GP20` (name not in OS — pull GLEIF entity record for full name)
- `213800UAI89I5Z2BNA05` (name not in OS — pull GLEIF entity record for full name)

### `253400L5RQK7PU6R7J04` Акционерное общество «Страховое общество газовой промышленности» АО «С

- `253400YDU6F3939GZB77` Общество с ограниченной ответственностью "Страховая Компания СОГАЗ-ЖИЗНЬ"
- `253400YDU6F3939GZB77` Общество с ограниченной ответственностью "Страховая Компания СОГАЗ-ЖИЗНЬ"
- `253400YDU6F3939GZB77` Общество с ограниченной ответственностью "Страховая Компания СОГАЗ-ЖИЗНЬ"
- `253400YDU6F3939GZB77` Общество с ограниченной ответственностью "Страховая Компания СОГАЗ-ЖИЗНЬ"

### `335800EQ8YXHIA6YMS18` NAYARA ENERGY LIMITED

- `2549002AK79F82L58C28` NAYARA ENERGY SINGAPORE PTE. LIMITED
- `2549002AK79F82L58C28` NAYARA ENERGY SINGAPORE PTE. LIMITED
- `2549002AK79F82L58C28` NAYARA ENERGY SINGAPORE PTE. LIMITED
- `2549002AK79F82L58C28` NAYARA ENERGY SINGAPORE PTE. LIMITED

### `300300RRBXAZRYJGIN14` China General Nuclear Power Corp

- `213800LDQL9XCZZZ4814` CGN GLOBAL URANIUM LIMITED
- `3003001ZNU8IEE7PF561` 华普资本有限公司
- `3003005GSDIB3CZDHR07` 中广核华盛投资有限公司
- `3003005GSDIB3CZDHR07` 中广核华盛投资有限公司

### `253400D38E021531V531` PUBLIC JOINT-STOCK COMPANY BANK ALEXANDROVSKY

- `2534006PW83DFZHA8W75` ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ "БСПБ КАПИТАЛ"
- `2534006PW83DFZHA8W75` ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ "БСПБ КАПИТАЛ"
- `2534006PW83DFZHA8W75` ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ "БСПБ КАПИТАЛ"
- `2534006PW83DFZHA8W75` ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ "БСПБ КАПИТАЛ"

### `213800HE6VDVJWT85874` Megafon PAO

- `213800FEEFIWRLXDF608` MEGAFON INVESTMENTS (CYPRUS) LIMITED
- `253400GW57HKS5TCYW22` Общество с ограниченной ответственностью "Рево Чардж Рус"
- `253400GW57HKS5TCYW22` Общество с ограниченной ответственностью "Рево Чардж Рус"

## Sanctioned subsidiary ← not-yet-sanctioned parent

The reverse direction: a sanctioned entity that is controlled by an entity not on the asset-freeze lists. Less common (sanctions tend to flow downward through ownership) but each row is worth flagging.

### `253400QBQPWTFL8FAS39` Bank Dom.RF AO

- `253400HUG1NXSZVHP181` JOINT-STOCK COMPANY "DOM.RF"
- `253400HUG1NXSZVHP181` JOINT-STOCK COMPANY "DOM.RF"
- `253400HUG1NXSZVHP181` JOINT-STOCK COMPANY "DOM.RF"
- `253400HUG1NXSZVHP181` JOINT-STOCK COMPANY "DOM.RF"
- `253400HUG1NXSZVHP181` JOINT-STOCK COMPANY "DOM.RF"
- `253400HUG1NXSZVHP181` JOINT-STOCK COMPANY "DOM.RF"

### `253400W29T5225G8X631` Відкрите акціонерне товариство "Банк дабрабит"

- `253400AAUDQ6NK0HNK41` NATIONAL BANK OF REPUBLIC BELARUS
- `253400AAUDQ6NK0HNK41` NATIONAL BANK OF REPUBLIC BELARUS
- `253400AAUDQ6NK0HNK41` NATIONAL BANK OF REPUBLIC BELARUS
- `253400AAUDQ6NK0HNK41` NATIONAL BANK OF REPUBLIC BELARUS
- `253400AAUDQ6NK0HNK41` NATIONAL BANK OF REPUBLIC BELARUS
- `253400AAUDQ6NK0HNK41` NATIONAL BANK OF REPUBLIC BELARUS

### `2534000KL0PLD6KG7T76` Banka Tinkoff d.d.

- `549300XQRN9MR54V1W18` Международная компания публичное акционерное общество "ТКС Холдинг"
- `549300XQRN9MR54V1W18` Международная компания публичное акционерное общество "ТКС Холдинг"
- `549300XQRN9MR54V1W18` Международная компания публичное акционерное общество "ТКС Холдинг"
- `549300XQRN9MR54V1W18` Международная компания публичное акционерное общество "ТКС Холдинг"

### `2534000R9X3PNNE57C55` Credit Bank of Moscow

- `253400UBPA9S0ZZHV261` Общество с ограниченной ответственностью "Концерн "РОССИУМ"
- `253400UBPA9S0ZZHV261` Общество с ограниченной ответственностью "Концерн "РОССИУМ"
- `253400UBPA9S0ZZHV261` Общество с ограниченной ответственностью "Концерн "РОССИУМ"
- `253400UBPA9S0ZZHV261` Общество с ограниченной ответственностью "Концерн "РОССИУМ"

### `253400AU1YFUM0C4QG84` Акционерное общество "БКС Банк"

- `21380052EDE2C3IEYR60` ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ "СИБИРСКИЕ ИНВЕСТИЦИИ"
- `21380052EDE2C3IEYR60` ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ "СИБИРСКИЕ ИНВЕСТИЦИИ"
- `21380052EDE2C3IEYR60` ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ "СИБИРСКИЕ ИНВЕСТИЦИИ"
- `21380052EDE2C3IEYR60` ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ "СИБИРСКИЕ ИНВЕСТИЦИИ"

### `253400BBBP7990NS0M56` SOVCOMBANK OPEN JOINT STOCK COMPANY

- `894500MDFP0SADLG9B22` Sovco Capital Partners B.V
- `894500MDFP0SADLG9B22` Sovco Capital Partners B.V
- `894500MDFP0SADLG9B22` Sovco Capital Partners B.V
- `894500MDFP0SADLG9B22` Sovco Capital Partners B.V

### `2549001I42I6G4P13T82` Castle Peak Power

- `2549000BCUSHGY6SZW33` CLP Power Hong Kong
- `25490002BUTSMP94GO68` CLP Holdings
- `2549000BCUSHGY6SZW33` CLP Power Hong Kong
- `25490002BUTSMP94GO68` CLP Holdings

### `529900XGGQVECOWYLC69` Ul'yanovskiy Stankostroitel'nyi Zavod OOO

- `529900HXE4EQIHJY8518` DMG MORI AKTIENGESELLSCHAFT
- `353800P4I3FIXTQV2E13` ＤＭＧ森精機株式会社
- `529900HXE4EQIHJY8518` DMG MORI AKTIENGESELLSCHAFT
- `353800P4I3FIXTQV2E13` ＤＭＧ森精機株式会社

### `253400QMD7MRJ6LTSS76` ОАО ВОСТОЧНО-ЕВРОПЕЙСКОЕ СТРАХОВОЕ АГЕНТСТВО

- `549300502MVL52NR6221` ABH HOLDINGS S.A.
- `549300502MVL52NR6221` ABH HOLDINGS S.A.
- `549300502MVL52NR6221` ABH HOLDINGS S.A.

### `253400T1524HLVLPUC37` SDK GARANT

- `253400PLAVEWZR55AU39` ЗАКРЫТОЕ АКЦИОНЕРНОЕ ОБЩЕСТВО "ХОЛДИНГОВАЯ КОМПАНИЯ ГАРАНТ"
- `253400PLAVEWZR55AU39` ЗАКРЫТОЕ АКЦИОНЕРНОЕ ОБЩЕСТВО "ХОЛДИНГОВАЯ КОМПАНИЯ ГАРАНТ"

### `253400CW8F4L53HWU734` Общество с ограниченной ответственностью "Бланк банк"

- `253400UBPA9S0ZZHV261` Общество с ограниченной ответственностью "Концерн "РОССИУМ"
- `253400UBPA9S0ZZHV261` Общество с ограниченной ответственностью "Концерн "РОССИУМ"

### `2138008KTNTDICZU8L25` IRAN OVERSEAS INVESTMENT BANK LIMITED

- `549300KBNGV4NYY3GE68` (name not in OS — pull GLEIF entity record for full name)
- `549300KBNGV4NYY3GE68` (name not in OS — pull GLEIF entity record for full name)

### `253400QWEQNERA6RJS29` AO "ALFA-BANK"

- `549300502MVL52NR6221` ABH HOLDINGS S.A.
- `549300502MVL52NR6221` ABH HOLDINGS S.A.

### `25340031R6A1E6TW7M44` JOINT-STOCK COMPANY NATIONAL STANDARD BANK

- `213800SACPJZDWYLL793` (name not in OS — pull GLEIF entity record for full name)
- `213800SACPJZDWYLL793` (name not in OS — pull GLEIF entity record for full name)

### `2534005803A5MMD61T78` ПАО "МТС-Банк"

- `2534008FX8EXH1FMJA74` MTS
- `2534008FX8EXH1FMJA74` MTS

### `253400NT4MB307747N58` PJSC Zenit Bank

- `253400PAT768SVJMV121` ОТКРЫТОЕ АКЦИОНЕРНОЕ ОБЩЕСТВО "ТАТНЕФТЬ" ИМЕНИ В. Д. ШАШИНА
- `253400PAT768SVJMV121` ОТКРЫТОЕ АКЦИОНЕРНОЕ ОБЩЕСТВО "ТАТНЕФТЬ" ИМЕНИ В. Д. ШАШИНА

### `253400U667MFV5QQWX26` JOINT STOCK COMPANY IBS IT SERVICES

- `2534007X9FQKGQ09MP77` Общество с ограниченной ответственностью "ИБС Холдинг"
- `2534007X9FQKGQ09MP77` Общество с ограниченной ответственностью "ИБС Холдинг"

### `253400UQS2QLH2209P60` Морський акціонерний банк (Акціонерне товариство)

- `213800HOF3LSAOZBHO78` (name not in OS — pull GLEIF entity record for full name)
- `213800HOF3LSAOZBHO78` (name not in OS — pull GLEIF entity record for full name)

### `213800TF7S5EDO6V3K66` ОТКРЫТОЕ АКЦИОНЕРНОЕ ОБЩЕСТВО " ТРУБНАЯ МЕТАЛЛУРГИЧЕСКАЯ КОМПАНИЯ"

- `549300K26N6FSAOJFH50` TMK STEEL HOLDING LIMITED
- `549300K26N6FSAOJFH50` TMK STEEL HOLDING LIMITED

### `894500MDF6I8J93LO347` Bank Saderat Iran

- `549300KBNGV4NYY3GE68` (name not in OS — pull GLEIF entity record for full name)
- `549300KBNGV4NYY3GE68` (name not in OS — pull GLEIF entity record for full name)
