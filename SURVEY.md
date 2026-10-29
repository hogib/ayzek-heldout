# Survey of the Greek and New Zealand networks (metadata only)

Made 2026-10-28/29 for ayzek's pre-registered held-out tests. Nothing here
comes from waveforms or event lists of the test period (2018 on): only station
metadata, availability (time-span) listings, documentation, and the logged
2012 service checks at the end. `survey/survey.py` regenerates every number
(`greece`, `nz` and `collisions` query the services; `report` and `tables`
work offline from `survey/out/`).

Coverage period: **2025-01-01 to 2026-10-28**. "Open now": an HH channel epoch
without an end date, or ending after 2026-10-29. "Usable": three HH channels
at exactly 100 Hz at one location code (HHZ with HHN/HHE or HH1/HH2) and at
least 90% coverage on each of the three.

## 1. Services, access, licence

| | Greece (HL, HT, also HA, HP, HC) | New Zealand (NZ) |
|---|---|---|
| station | `https://eida.gein.noa.gr/fdsnws/station/1/` | `https://service.geonet.org.nz/fdsnws/station/1/` (StationXML 1.2) |
| dataselect | `https://eida.gein.noa.gr/fdsnws/dataselect/1/` | `https://service.geonet.org.nz/fdsnws/dataselect/1/`; near-real-time: `service-nrt.geonet.org.nz` |
| availability | `https://eida.gein.noa.gr/fdsnws/availability/1/` (query, extent) | **none** (`/fdsnws/availability` is 404; station `includeavailability` "not supported") |
| event | `https://eida.gein.noa.gr/fdsnws/event/1/` (SeisComP; `/catalogs` and `/contributors` empty) | `https://service.geonet.org.nz/fdsnws/event/1/` (catalog `GeoNet`, contributor `WEL`; no `limit` parameter) |
| routing | EIDA routing sends HL, HT, HA, HP, HC (and HI, EG, ME, CQ, MK, MA, 1Y, 5B ...) to the NOA node. AUTH's own node (`eida.geophysics.geo.auth.gr`) did not answer; HT is served by NOA. | - |
| authentication | none for these open networks (StationXML `restrictedStatus="open"`; the node's `eida-auth` is for restricted data only) | none ("There is no restricted data in webservice") |
| rate limits | none documented. In practice the node dropped connections (SSL EOF, "remote end closed") with 4 parallel availability requests and stopped answering for minutes; 1-2 requests at a time with backoff worked. Three stations' availability queries (HL.NISR2, HP.ANX, HP.KSTR) failed every time. | no numbers; GeoNet asks not to request too much in one request, nor many very small requests; connections break after 5-10 min without data; bulk users are pointed to the AWS open-data bucket |
| licence | NOA EIDA node: "The content shared from our services is licensed under a Creative Commons Attribution 4.0 International License." No separate HT/AUTH licence found. | CC BY 3.0 NZ: "GeoNet content is copyright Earth Sciences New Zealand and is licensed under a Creative Commons Attribution 3.0 New Zealand License." |
| citation | HL: National Observatory of Athens, Institute of Geodynamics, Athens (1975). Hellenic Unified Seismological Network. doi:10.7914/SN/HL. HT: Aristotle University of Thessaloniki (1981). doi:10.7914/SN/HT. HA: University of Athens (2008), doi:10.7914/SN/HA. HP: University of Patras (2000), doi:10.7914/SN/HP. HC: Technological Educational Institute of Crete (2006), doi:10.7914/SN/HC. | GNS Science (2021). GeoNet Aotearoa New Zealand Seismic Digital Waveform Dataset. doi:10.21420/G19Y-9D40, plus the acknowledgement "We acknowledge the New Zealand GeoNet programme and its sponsors NHC, Earth Sciences NZ, LINZ, NEMA and MBIE for providing data/images used in this study." Catalogue: doi:10.21420/0S8P-TZ38. |
| redistribution of extracted miniSEED | allowed by CC BY 4.0 with attribution and a note of changes (we re-encode to 512-byte Steim2). The licence is stated by the node, not by AUTH; worth a line to eida@noa.gr / AUTH before publishing HT extracts. | allowed by CC BY 3.0 NZ with attribution (licence terms; the policy page itself says nothing on redistribution). |

**Which Greek networks.** All five are open, at 100 Hz on HH, and on the same
node: HL (NOA, 76 stations with HH open), HT (AUTH, 50), HA (NKUA Athens, 32),
HP (Patras, 22), HC (Crete, 14). HA and HP are dense in central Greece and the
Gulf of Corinth/western Greece and add many usable stations (27 and 16); HC
adds 5 on Crete. HI (ITSAK) and EG (EUROSEISTEST) are strong-motion networks;
CQ, MK, MA, ME are Cyprus and neighbouring countries; 1Y/5B/XZ are temporary.
The tool knows KO, HL, HT and NZ; adding HA/HP/HC is one entry each in
`heldout/networks.py` (same node, same services) if the protocol wants them.

## 2. Stations with three HH channels at 100 Hz, open now

| | open with HH | three HH at 100 Hz | not 100 Hz (excluded) |
|---|---|---|---|
| HL | 76 | 75 | **HL.IDI** (80 Hz) |
| HT | 50 | 50 | - |
| HA | 32 | 32 | - |
| HP | 22 | 22 | - |
| HC | 14 | 14 | - |
| NZ | 133 | 133 | - |

Every station is listed in the appendix (code, lat, lon, elevation, location
and channels, start of the current epoch, first HH epoch, number of epochs);
all channel epochs, with sample rates and azimuths, are in
`survey/out/greece_epochs.csv` and `survey/out/nz_epochs.csv`.

Things that matter for ayzek:

- **Location codes.** Greek stations use the empty location (HL.DILO and
  HP.AMT use `00`; HL.PTL has HH at two locations). NZ uses `10` for 121
  stations, `11`/`12`/`13` for the rest; MAVZ, TKGZ, WHSZ and WLCZ have HH at
  two location codes. The tool takes one location per station (the first in
  sort order that passes) and never mixes them; ayzek itself ignores the
  location code, so a file must not hold two.
- **HH1/HH2 and orientation.** 28 NZ stations deliver HH1/HH2, and 26 NZ
  stations have horizontals more than 5 deg off N/E (borehole sensors at
  arbitrary azimuths, e.g. ABAZ HH1 at 209 deg; MKTZ lists both horizontals
  at 0 deg, a metadata error); 18 of them are among the usable stations.
  Greek offsets are small (6-10 deg: HL.ATH, KEK, LKR, HT.KOKK, LIT, PAIG,
  SRS, and a few others). ayzek reads 1 as N and 2 as E without rotating.
  The tool records each station's offsets in `stations.json`/`dataset.json`;
  `max_azimuth_offset_deg` in a set's config refuses stations beyond a
  limit. Whether to exclude, rotate, or keep them is a protocol decision.

## 3. Coverage 2025-01-01 to 2026-10-28

Greece, from NOA's fdsnws/availability (minimum over the three channels):

| | stations with a value | median | >= 90% | 0% |
|---|---|---|---|---|
| HL | 74 | 0.828 | 32 | 20 |
| HT | 50 | 0.932 | 28 | 3 |
| HA | 32 | 0.983 | 27 | 0 |
| HP | 20 | 0.961 | 16 | 0 |
| HC | 14 | 0.821 | 5 | 1 |

(HL.IDI is excluded at 80 Hz; HL.NISR2, HP.ANX and HP.KSTR have no value
because their availability query always failed.) The 20 HL stations at 0%
have open HH metadata but nothing in the EIDA archive over the period.

The NOA service clips spans to the request window inconsistently: for a short
window it can return spans whose end precedes their start (seen for HT.THE on
2012-06-01, a day with no data). Such spans count as zero, which is right for
that case; over the 22-month window only the two ends are affected.

New Zealand has **no availability service**. Coverage was taken from the
object listing of GeoNet's open-data bucket
(`geonet-open-data.s3-ap-southeast-2.amazonaws.com`, keys
`waveforms/miniseed/YYYY/YYYY.DDD/STA.NZ/YYYY.DDD.STA.LOC-CHA.NZ.D`, one file
per channel and UTC day): the fraction of the 665 days with a file for each
channel. Only keys were read, never sizes or contents (file sizes would carry
a little amplitude information). This is an **upper bound** at day
resolution: a day with one hour of data counts as a full day. Result: 133
stations, median 0.9985, 89 at >= 99%, 107 at >= 90%, 122 at >= 50%.
To check NZ coverage more finely without waveforms one could (a) keep to the
key listing, as here (day resolution), or (b) read only the
miniSEED fixed headers of each day file with HTTP range requests, which gives
record start times and sample counts without decoding samples; (b) does
touch the data files, so it should wait for the freeze or be agreed first.

Usable (three HH at 100 Hz, >= 90% on every channel):

| | usable |
|---|---|
| HL | 32 |
| HT | 28 |
| HA | 27 |
| HP | 16 |
| HC | 5 |
| **Greece, HL+HT** | **60** |
| Greece, all five | 108 |
| **NZ** | **107** |

## 4. Clusters (usable stations with >= 5 usable stations within 150 km)

Greedy as in ayzek's KO scout: centres in order of how many usable stations
lie within 150 km, a centre is skipped once it is a member of an earlier
cluster; members can appear in more than one cluster.

Greece, HL and HT only (60 usable):

| centre | lat, lon | n | members |
|---|---|---|---|
| HT.HORT | 40.60, 23.10 | 20 | HL.NEO NVR PLG PRAS THL, HT.FLNA GRG HMT1 HORT KAVA KNT KOKK LIT NESN OUR PAIG SOH SRS THAS THE |
| HL.EVR | 38.92, 21.81 | 16 | HL.EVR JAN KLV LKR NEO RLS TETR THL VLS, HT.ACHL EVGI LIT LKD2 NESN NYDR TSLK |
| HT.AOS2 | 39.15, 23.84 | 13 | HL.ATH LIA LKR NEO PLG PTL VLY, HT.ACHL AOS2 HMT1 NESN OUR PAIG |
| HL.DILO | 37.40, 25.27 | 11 | HL.AMGA APE ASTA DILO PTL SAP3 VLY, HT.AKRO THR3 THR5 THR8 |
| HL.PENT | 40.20, 21.14 | 10 | HL.JAN KEK PENT TETR THL, HT.FLNA GRG LIT NESN NEST |
| HL.ORTH | 37.85, 20.70 | 9 | HL.ITM KLV ORTH RLS VLS, HT.EVGI LKD2 NYDR TSLK |
| HL.RDO | 41.15, 25.54 | 8 | HL.LIA NVR PRAS RDO, HT.HMT1 KAVA KOKK THAS |

Greece, all five networks (108 usable): HA.KALE (38.39, 22.14) 50;
HL.VLY (37.85, 23.79) 32; HA.ATHR (38.32, 20.42) 25; HT.NESN (39.73, 22.54) 24;
HT.HMT1 (40.26, 24.25) 17; HT.AKRO (36.36, 25.40) 16; HT.KNT (41.17, 22.90) 14;
HL.KEK (39.71, 19.80) 9; HC.CHAN (35.52, 24.04) 5; HL.KARP (35.55, 27.16) 5.
Members: `survey/out/greece_log.txt`.

New Zealand (107 usable; coverage an upper bound):

| centre | lat, lon | n | members |
|---|---|---|---|
| NZ.OAHZ | -38.85, 176.05 | 39 | BKZ COVZ ETVZ FEGZ FWVZ HATZ HIZ HNCZ KNZ KPRZ KRVZ LIRZ MNMZ MTVZ MWZ NGZ NTVZ OAHZ OMRZ OPRZ OTVZ PKTZ PXZ RATZ RTZ TGRZ TLZ TMVZ TOZ TRVZ TSZ URZ UTU VRZ WATZ WAZ WHTZ WHVZ WTVZ |
| NZ.OHWZ | -40.21, 175.32 | 24 | BFZ COVZ ETVZ FWVZ KRVZ MNMZ MRZ MTVZ MWOZ NGZ NTVZ OHWZ OTVZ PXZ TMVZ TRVZ TSZ VRZ WAZ WEL WHVZ WLCZ WRRZ WTVZ |
| NZ.LRRZ | -36.15, 174.54 | 22 | ABAZ AKFZ AWKZ GRZ HTPZ JBLZ KPFZ KRBZ KUZ LRRZ MKAZ MNTZ OTNZ OUZ PAKZ PKAZ PNUZ PTAZ TTTZ WCZ WIAZ WTAZ |
| NZ.HORZ | -43.78, 170.11 | 15 | CVZ DBHZ FOZ HORZ HSPZ JCZ LBZ MKTZ ODZ RDHZ RPZ SLTZ WHSZ WKZ WVZ |
| NZ.EAZ | -45.23, 169.31 | 14 | EAZ HSPZ JCZ LBZ MLZ MSZ ODZ OPZ RDHZ SLTZ SYZ TUZ WHZ WKZ |
| NZ.HAZ | -37.76, 177.78 | 13 | HAZ HNCZ KNZ LIRZ MWZ MXZ OMRZ OPRZ PUZ RTZ TGRZ URZ UTU |
| NZ.LTZ | -42.78, 172.27 | 10 | DBHZ DSZ GVZ INZ KHZ LTZ OXZ RPZ THZ WVZ |
| NZ.BSWZ | -41.71, 173.88 | 8 | BSWZ KHZ NNZ QRZ THZ WEL WLCZ WRRZ |
| NZ.DCZ | -45.46, 167.15 | 5 | DCZ MLZ MSZ PYZ WHZ |

Many NZ stations ending in `VZ` are volcano-monitoring sites (Taupō
Volcanic Zone, Ruapehu, Tongariro); the OAHZ cluster is dominated by them.

## 5. Catalogues of the networks' own agencies (from documentation)

**NOA (HL).** FDSNWS-event at `eida.gein.noa.gr/fdsnws/event/1/query`
(SeisComP back end; formats xml/QuakeML, text, csv, sc3ml; every query needs
a start/end time or an event id; `catalog` and `updatedafter` not
implemented). The service page documents no agency, magnitude types or
completeness. QuakeML carries origin depth. The one allowed check
(2012-06-01, limit 3) returned HTTP 204: the service apparently does not hold
events from 2012, so the magnitude types it returns could not be seen under
the blindness rules. NOA's bulletins use ML; not verified here.

**AUTH (HT).** No FDSN event service. `seismo.auth.gr/en/seismicity-catalogs/`
offers flat text files: a preliminary, unreviewed catalogue with M > 2.0 from
2023-01-01 (`.../CATALOGS/preliminary/prelcatDB.txt`), a reviewed one with
M > 2.0 for 1995-01-01 to 2024-03-31 (`.../preliminary/finalcat.cat`, origin
time, epicentre, focal depth, magnitude), and a historical Mw catalogue
(550 BC-2010, M > 4.5, completeness "M>6.5 since 1901, M>5.2 since 1911,
M>4.8 since 1950 and M>4.5 since 1964"). No licence is stated; users are
asked to cite doi:10.7914/SN/HT. The two modern files cover the test period,
so they were **not downloaded** and their format and magnitude type are
unknown. Until a parser is written after the freeze, the tool's HT sets use
NOA's catalogue.

**GeoNet (NZ).** FDSNWS-event at `service.geonet.org.nz/fdsnws/event/1/query`
(QuakeML; no `limit`), also the near-real-time host. Magnitude types
documented on GeoNet's event pages: ML, MLv (local magnitude on the
vertical), mB, Mw(mB) (from mB by Bormann and Saul 2008) and the summary M (a
weighted combination of MLv and Mw(mB)); the preferred magnitude varies by
event. The allowed 2012 check returned type `M` as preferred, and **depth is
in the output** (82.7 km and 15.5 km for its two events), so deep events
(100-300 km) will reach `catalog.csv` with their depth. GeoNet publishes no
completeness figure that I found; a 2008 NZSEE Bulletin study gives Mc = 2.6
for shallow seismicity 1987-2004, with higher values for intermediate and
deep events.

**AFAD (KO).** KOERI runs no FDSN event service (its EIDA node answers 404),
so KO sets use AFAD's `apiv2/event/filter` (redirects to
`servisnet.afad.gov.tr/apigateway/deprem/apiv2/event/filter`), as ayzek's KO
development catalogues are AFAD exports. Its allowed 2012 check returned an
empty list.

## 6. Station-code collisions

ayzek looks stations up by code alone in four tables of its models directory:
`stations.csv` (coordinates), `pd_gain.csv` (vertical sensitivity),
`pd_terms.csv` (Pd station terms; a term above the flag threshold also
excludes the station) and `pd_noise.csv` (the noise band outside which a Pd
is dropped). Codes compared (ayzek_code at 571e383): stations.csv 1564,
pd_gain.csv 121, pd_terms.csv 125, pd_noise.csv 148 (1601 distinct; KO, TU,
6G, IJ and AFAD codes, not separated by network in these files); KO from
KOERI's station service, every epoch: 278 codes; foreign: every HL, HT, HA,
HP, HC and NZ station code of any channel and epoch: 1830.

| code | network(s) | collides with | HH open now, coverage |
|---|---|---|---|
| ACOR | HA | ayzek stations.csv (36.99 N 28.46 E, a Turkish station) | yes, 0.990: **usable** |
| ALN | HT | ayzek stations.csv (40.90 N 26.05 E: the same HT.ALN) | yes, 0.794 |
| KARA | HL | KO; ayzek stations, pd_gain, pd_terms, pd_noise | no |
| KARS | NZ | KO; ayzek stations, pd_gain, pd_noise | no |
| KURT | HL | ayzek stations.csv | yes, 0.0 |
| LALA | HL | ayzek stations.csv | yes, 0.0 |
| SIVA | HL | ayzek stations.csv | yes, 0.825 |
| DSLC, HAS, HNZ, KIRS, KKZ, MANS, STZ | NZ | ayzek stations.csv | no |
| MRTH | HA + HL | each other | HA.MRTH yes, 0.984: **usable**; HL.MRTH 0.0 |
| STRF | HL + HT | each other | HT.STRF yes, 0.29 |
| PRNS | HC + NZ | each other | no |
| THT2 | HC + HT | each other | no |

None of HL, HT and NZ collide with each other except STRF (HL/HT). Of the
usable stations only **HA.ACOR** (wrong coordinates from ayzek's table) and
**HA.MRTH** (vs HL.MRTH) collide, and both are outside HL/HT. SIVA and ALN
are near the threshold and would collide if they qualify in a later window.
The tool refuses a second station with the same code within one set.

## 7. Requests made while building this repository

Waveforms (all through `heldout pull`, one dataselect request per station):

| UTC of request | network.station | span | why |
|---|---|---|---|
| 2026-10-28T23:46Z (files written 23:46:24-23:46:55) | KO SIMA KULA YAYO DKL TVSB KCTX (6 requests) | 2025-11-10T18:04:00-18:35:00 | the development set demo_ko, explicitly allowed, to compare with ayzek's copy |
| 2026-10-28T23:52:02Z | HL.ATH HHZ/HHN/HHE | 2012-06-01T12:00:00-12:01:00 | dataselect and decoding check |
| 2026-10-28T23:52:21Z | NZ.WEL.10 HHZ/HHN/HHE | 2012-06-01T12:00:00-12:01:00 | same |
| 2026-10-29T02:44:14Z | HT.XOR HHZ/HHN/HHE | 2012-06-01T12:00:00-12:01:00 | same; HT.THE, the first choice, had no data that day (availability), so no request was made for it |

Later `pull` runs on these sets found the files present and only re-read
them; no further waveform request was made. HL and HT were each given their
own minute although both are served by NOA: "Greece" counted as two
networks here. All three decode with ayzek's own `tools/mseed_dump`
("all records decoded, integrity checks passed").

Events (nothing from 2018 on; nothing counted or summarised):

| UTC | service | query | answer |
|---|---|---|---|
| 2026-10-28T23:56:59Z | GeoNet fdsnws/event | 2012-06-01 (one day), within 1000 km of Wellington, M >= 4 (GeoNet has no `limit`) | 2 events |
| 2026-10-28T23:57:11Z | NOA fdsnws/event | 2012-06-01, within 1000 km of Athens, limit 3 | HTTP 204, none |
| 2026-10-28T23:57:42Z | NOA fdsnws/event | the identical query repeated once, to read the HTTP status | HTTP 204, 0 bytes |
| 2026-10-28T23:58:03Z | AFAD apiv2 | 2012-06-01, within 300 km of 39.22 N 28.17 E, limit 3 | empty list |

Two earlier attempts were stopped inside ObsPy before any query was sent
(GeoNet: `limit` not in its WADL; NOA: WADL unreachable). The catalogue for
demo_ko (2025) was not fetched.

Metadata and availability only: KOERI station service and availability
(demo_ko span; KO code list); NOA station service (HH channels of HL, HT, HA,
HP, HC, all epochs; network list) and availability (193 stations over
2025-01-01 to 2026-10-28, and the 2012 minute for HL/HT candidates); GeoNet
station service; the GeoNet bucket's key listing for the 665 days and for
2012-06-01; EIDA routing; DOI citations (doi.org); documentation pages of
GeoNet, the NOA node, AUTH (catalogue page only, not its files) and FDSN.

## Appendix: stations

Generated by `uv run python survey/survey.py tables survey/out`. "current
epoch from" is the start of the open HH epoch, "HH since" the first HH epoch
at that location, "epochs" the number of HH epochs; "horiz. off N/E" names
the horizontals more than 5 deg from their nominal azimuth. NZ coverage is
the day-file upper bound.

#### greece: 193 stations with three HH at 100 Hz (>= 90%: 108)

| net | code | lat | lon | elev m | loc.channels | current epoch from | HH since | epochs | cov min | >=90% | horiz. off N/E |
|---|---|---|---|---|---|---|---|---|---|---|---|
| HA | ACOR | 37.8902 | 22.8692 | 437 | --.HHZ/HHN/HHE | 2022-10-07 | 2009-02-17 | 6 | 0.9898 | yes |  |
| HA | ADRO | 37.8569 | 24.8425 | 450 | --.HHZ/HHN/HHE | 2026-08-24 | 2026-08-24 | 1 | 0.094 | no |  |
| HA | ALIO | 38.0657 | 23.6727 | 180 | --.HHZ/HHN/HHE | 2023-11-24 | 2023-11-24 | 1 | 0.7733 | no |  |
| HA | AMPE | 38.3015 | 23.2688 | 365 | --.HHZ/HHN/HHE | 2025-09-04 | 2021-08-03 | 3 | 0.9819 | yes |  |
| HA | ANTK | 38.3605 | 22.6385 | 340 | --.HHZ/HHN/HHE | 2023-09-30 | 2023-09-30 | 1 | 0.9411 | yes |  |
| HA | ATAL | 38.6926 | 23.0213 | 290 | --.HHZ/HHN/HHE | 2025-12-11 | 2008-01-23 | 13 | 0.9542 | yes |  |
| HA | ATHR | 38.3172 | 20.4165 | 263 | --.HHZ/HHN/HHE | 2022-04-14 | 2022-04-14 | 1 | 0.9952 | yes |  |
| HA | ATHU | 37.9665 | 23.7845 | 308 | --.HHZ/HHN/HHE | 2023-03-06 | 2008-01-01 | 7 | 0.9969 | yes |  |
| HA | AXAR | 38.7664 | 22.6590 | 406 | --.HHZ/HHN/HHE | 2026-05-13 | 2008-06-19 | 4 | 0.998 | yes |  |
| HA | DOMV | 38.2569 | 22.9795 | 170 | --.HHZ/HHN/HHE | 2022-09-20 | 2021-07-29 | 2 | 0.998 | yes |  |
| HA | ELEO | 38.2176 | 24.2484 | 276 | --.HHZ/HHN/HHE | 2026-05-14 | 2026-05-14 | 1 | 0.2473 | no |  |
| HA | EMPO | 36.6024 | 27.1783 | 345 | --.HHZ/HHN/HHE | 2026-07-03 | 2026-07-03 | 1 | 0.1709 | no |  |
| HA | EPID | 37.6144 | 23.1189 | 444 | --.HHZ/HHN/HHE | 2012-12-06 | 2011-07-23 | 3 | 0.9981 | yes |  |
| HA | ERTR | 38.4066 | 23.7865 | 121 | --.HHZ/HHN/HHE | 2026-05-27 | 2022-09-28 | 3 | 0.9981 | yes |  |
| HA | HAVD | 38.2036 | 20.3848 | 200 | --.HHZ/HHN/HHE | 2022-04-13 | 2022-04-13 | 1 | 0.9573 | yes |  |
| HA | IOSI | 36.7225 | 25.2887 | 220 | --.HHZ/HHN/HHE | 2025-02-12 | 2025-02-12 | 1 | 0.9316 | yes |  |
| HA | KALE | 38.3911 | 22.1398 | 760 | --.HHZ/HHN/HHE | 2017-04-05 | 2008-01-01 | 3 | 0.998 | yes |  |
| HA | KARY | 38.0321 | 24.4370 | 220 | --.HHZ/HHN/HHE | 2013-07-11 | 2010-06-22 | 2 | 0.9818 | yes |  |
| HA | LAKA | 38.2401 | 21.9785 | 505 | --.HHZ/HHN/HHE | 2025-11-27 | 2008-01-23 | 11 | 0.9966 | yes |  |
| HA | LOUT | 37.9879 | 22.9743 | 307 | --.HHZ/HHN/HHE | 2012-11-16 | 2010-06-22 | 3 | 0.9982 | yes |  |
| HA | MDRA | 38.0606 | 23.4662 | 370 | --.HHZ/HHN/HHE | 2021-07-09 | 2020-09-22 | 2 | 0.998 | yes |  |
| HA | MRKA | 38.7047 | 23.5863 | 466 | --.HHZ/HHN/HHE | 2026-05-27 | 2008-11-04 | 6 | 0.9963 | yes |  |
| HA | MRTH | 38.1225 | 23.9409 | 130 | --.HHZ/HHN/HHE | 2020-09-08 | 2020-09-08 | 1 | 0.984 | yes |  |
| HA | PRDM | 38.2804 | 22.8470 | 600 | --.HHZ/HHN/HHE | 2023-09-30 | 2023-09-30 | 1 | 0.9817 | yes |  |
| HA | PSAH | 38.5694 | 23.6473 | 36 | --.HHZ/HHN/HHE | 2023-01-11 | 2023-01-11 | 1 | 0.9973 | yes |  |
| HA | SERI | 37.1609 | 24.4853 | 460 | --.HHZ/HHN/HHE | 2021-07-13 | 2010-07-07 | 2 | 0.9413 | yes |  |
| HA | SNT1 | 36.4159 | 25.4282 | 12 | --.HHZ/HHN/HHE | 2025-02-14 | 2012-09-21 | 4 | 0.9486 | yes |  |
| HA | SNT5 | 36.4037 | 25.3953 | 124 | --.HHZ/HHN/HHE | 2025-02-14 | 2014-04-29 | 3 | 0.9311 | yes |  |
| HA | STFN | 38.1766 | 23.5440 | 589 | --.HHZ/HHN/HHE | 2019-07-20 | 2019-07-20 | 1 | 0.1816 | no |  |
| HA | THAL | 38.0357 | 22.6634 | 196 | --.HHZ/HHN/HHE | 2014-10-01 | 2008-07-18 | 4 | 0.998 | yes |  |
| HA | THIV | 38.2990 | 23.3320 | 325 | --.HHZ/HHN/HHE | 2022-09-20 | 2021-08-03 | 2 | 0.9818 | yes |  |
| HA | VILL | 38.1642 | 23.3122 | 650 | --.HHZ/HHN/HHE | 2022-10-07 | 2009-10-20 | 4 | 0.9977 | yes |  |
| HC | CHAN | 35.5193 | 24.0428 | 37 | --.HHZ/HHN/HHE | 2013-11-28 | 2013-11-28 | 1 | 0.9219 | yes |  |
| HC | GVDS | 34.8389 | 24.0585 | 358 | --.HHZ/HHN/HHE | 2016-03-15 | 2016-03-15 | 1 | 0.4469 | no |  |
| HC | IMOD | 34.9731 | 24.7995 | 243 | --.HHZ/HHN/HHE | 2020-07-08 | 2020-07-08 | 1 | 0.8355 | no |  |
| HC | IPPL | 35.3486 | 24.4632 | 193 | --.HHZ/HHN/HHE | 2020-09-28 | 2020-09-28 | 1 | 0.9588 | yes |  |
| HC | KNDR | 35.2348 | 23.6248 | 13 | --.HHZ/HHN/HHE | 2013-11-28 | 2013-11-28 | 1 | 0.9491 | yes |  |
| HC | KNSS | 35.3042 | 25.1802 | 297 | --.HHZ/HHN/HHE | 2020-11-04 | 2020-11-04 | 1 | 0.8821 | no |  |
| HC | KOSP | 36.8810 | 27.2810 | 40 | --.HHZ/HHN/HHE | 2022-04-13 | 2021-10-29 | 2 | 0.5084 | no |  |
| HC | KTHR | 36.2447 | 22.9939 | 270 | --.HHZ/HHN/HHE | 2021-09-23 | 2013-11-28 | 4 | 0.2599 | no |  |
| HC | KTRS | 36.9261 | 22.1360 | 110 | --.HHZ/HHN/HHE | 2021-09-25 | 2021-09-25 | 1 | 0.0 | no |  |
| HC | PFKS | 35.0429 | 25.4733 | 745 | --.HHZ/HHN/HHE | 2020-07-08 | 2020-07-08 | 1 | 0.9371 | yes |  |
| HC | RODP | 35.5604 | 23.7577 | 299 | --.HHZ/HHN/HHE | 2020-10-31 | 2014-10-17 | 2 | 0.5315 | no |  |
| HC | STIA | 35.2021 | 26.0909 | 93 | --.HHZ/HHN/HHE | 2014-09-10 | 2014-09-10 | 1 | 0.9601 | yes |  |
| HC | TEFL | 35.0933 | 25.1634 | 353 | --.HHZ/HHN/HHE | 2022-07-13 | 2022-07-13 | 1 | 0.7464 | no |  |
| HC | THNO | 37.6541 | 25.0221 | 273 | --.HHZ/HHN/HHE | 2020-10-06 | 2020-10-06 | 1 | 0.8062 | no |  |
| HL | AIGN | 37.7481 | 23.4436 | 83 | --.HHZ/HHN/HHE | 2020-06-27 | 2020-06-27 | 1 | 0.0 | no |  |
| HL | AMGA | 36.8316 | 25.8938 | 308 | --.HHZ/HHN/HHE | 2025-02-04 | 2012-05-30 | 2 | 0.9419 | yes |  |
| HL | ANAF | 36.3567 | 25.7726 | 335 | --.HHZ/HHN/HHE | 2025-02-04 | 2012-03-06 | 2 | 0.4386 | no |  |
| HL | ANKY | 35.8670 | 23.3012 | 143 | --.HHZ/HHN/HHE | 2010-01-01 | 2010-01-01 | 1 | 0.4756 | no |  |
| HL | APE | 37.0727 | 25.5230 | 608 | --.HHZ/HHN/HHE | 2008-04-30 | 2008-04-30 | 1 | 0.9844 | yes |  |
| HL | ARG | 36.2136 | 28.1212 | 148 | --.HHZ/HHN/HHE | 2010-12-01 | 2010-12-01 | 1 | 0.9832 | yes |  |
| HL | ASTA | 36.5455 | 26.3529 | 64 | --.HHZ/HHN/HHE | 2025-02-10 | 2025-02-10 | 1 | 0.9351 | yes |  |
| HL | ATH | 37.9738 | 23.7177 | 93 | --.HHZ/HHN/HHE | 2018-10-30 | 2010-03-02 | 3 | 0.9983 | yes | HHN/HHE |
| HL | CHRYS | 35.3099 | 23.5496 | 116 | --.HHZ/HHN/HHE | 2026-05-06 | 2026-05-06 | 1 | 0.0 | no |  |
| HL | CLEM | 37.8906 | 21.1330 | 183 | --.HHZ/HHN/HHE | 2018-10-28 | 2018-10-28 | 1 | 0.0 | no |  |
| HL | DILO | 37.4011 | 25.2692 | 2 | 00.HHZ/HHN/HHE | 2025-01-29 | 2025-01-29 | 1 | 0.909 | yes |  |
| HL | ELEF | 40.8464 | 24.2543 | 67 | --.HHZ/HHN/HHE | 2026-02-28 | 2026-02-28 | 1 | 0.3526 | no | HHE |
| HL | ELIKO | 38.3888 | 22.8622 | 1029 | --.HHZ/HHN/HHE | 2026-10-10 | 2026-10-10 | 1 | 0.0 | no |  |
| HL | EVR | 38.9166 | 21.8105 | 1037 | --.HHZ/HHN/HHE | 2010-12-01 | 2010-12-01 | 1 | 0.9832 | yes |  |
| HL | GRAMV | 35.5204 | 23.5944 | 187 | --.HHZ/HHN/HHE | 2026-05-05 | 2026-05-05 | 1 | 0.0 | no |  |
| HL | GVD | 34.8391 | 24.0874 | 170 | --.HHZ/HHN/HHE | 2010-09-21 | 2010-09-21 | 1 | 0.1424 | no |  |
| HL | IACM | 35.3058 | 25.0709 | 45 | --.HHZ/HHN/HHE | 2010-01-01 | 2010-01-01 | 1 | 0.7974 | no |  |
| HL | IMMV | 35.4606 | 23.9811 | 230 | --.HHZ/HHN/HHE | 2010-07-16 | 2010-07-16 | 1 | 0.8917 | no |  |
| HL | ITM | 37.1787 | 21.9252 | 423 | --.HHZ/HHN/HHE | 2010-02-24 | 2010-02-24 | 1 | 0.9932 | yes |  |
| HL | JAN | 39.6562 | 20.8487 | 526 | --.HHZ/HHN/HHE | 2010-12-08 | 2010-12-08 | 1 | 0.9972 | yes |  |
| HL | KARP | 35.5471 | 27.1611 | 524 | --.HHZ/HHN/HHE | 2009-11-24 | 2009-11-24 | 1 | 0.9637 | yes |  |
| HL | KEK | 39.7127 | 19.7962 | 227 | --.HHZ/HHN/HHE | 2018-07-24 | 2010-12-07 | 3 | 0.993 | yes | HHN/HHE |
| HL | KLV | 38.0435 | 22.1504 | 758 | --.HHZ/HHN/HHE | 2010-01-01 | 2010-01-01 | 1 | 0.9156 | yes |  |
| HL | KOSD | 36.7027 | 26.9470 | 243 | --.HHZ/HHN/HHE | 2021-04-16 | 2021-04-16 | 1 | 0.0 | no |  |
| HL | KRYO | 37.9712 | 22.6180 | 883 | --.HHZ/HHN/HHE | 2025-08-05 | 2025-08-05 | 1 | 0.6712 | no |  |
| HL | KSL | 36.1503 | 29.5856 | 64 | --.HHZ/HHN/HHE | 2010-10-07 | 2010-10-07 | 1 | 0.0 | no |  |
| HL | KSTE | 35.1801 | 25.3372 | 395 | --.HHZ/HHN/HHE | 2026-01-22 | 2021-11-05 | 2 | 0.018 | no | HHN/HHE |
| HL | KTHA | 36.2566 | 23.0621 | 360 | --.HHZ/HHN/HHE | 2013-06-18 | 2013-06-18 | 1 | 0.9976 | yes |  |
| HL | KURT | 37.9650 | 21.3280 | 135 | --.HHZ/HHN/HHE | 2018-10-28 | 2018-10-28 | 1 | 0.0 | no |  |
| HL | KYMI | 38.6233 | 24.1014 | 378 | --.HHZ/HHN/HHE | 2026-08-28 | 2014-04-01 | 2 | 0.0896 | no |  |
| HL | KYPS | 37.8188 | 20.8234 | 117 | --.HHZ/HHN/HHE | 2018-10-27 | 2018-10-27 | 1 | 0.0 | no |  |
| HL | KZN | 40.3033 | 21.7821 | 791 | --.HHZ/HHN/HHE | 2010-01-01 | 2010-01-01 | 1 | 0.761 | no |  |
| HL | LALA | 37.7112 | 21.7209 | 612 | --.HHZ/HHN/HHE | 2022-07-06 | 2022-07-06 | 1 | 0.0 | no |  |
| HL | LIA | 39.8972 | 25.1806 | 67 | --.HHZ/HHN/HHE | 2019-06-06 | 2010-01-01 | 3 | 0.9212 | yes |  |
| HL | LKR | 38.6496 | 22.9988 | 192 | --.HHZ/HHN/HHE | 2022-05-06 | 2010-01-01 | 2 | 0.9222 | yes | HHN/HHE |
| HL | MET1 | 37.5785 | 23.3859 | 15 | --.HHZ/HHN/HHE | 2024-03-20 | 2019-11-20 | 2 | 0.7118 | no |  |
| HL | MET2 | 37.6127 | 23.3296 | 197 | --.HHZ/HHN/HHE | 2026-02-27 | 2019-05-20 | 2 | 0.0 | no | HHN |
| HL | MHLO | 36.6898 | 24.4017 | 175 | --.HHZ/HHN/HHE | 2010-06-05 | 2010-06-05 | 1 | 0.8105 | no |  |
| HL | MRTH | 37.0587 | 21.5761 | 6 | --.HHZ/HHN/HHE | 2022-06-07 | 2022-06-07 | 1 | 0.0 | no |  |
| HL | NEO | 39.3057 | 23.2219 | 148 | --.HHZ/HHN/HHE | 2011-04-28 | 2010-11-13 | 2 | 0.9848 | yes |  |
| HL | NISR | 36.6106 | 27.1309 | 48 | --.HHZ/HHN/HHE | 2021-01-15 | 2007-11-14 | 4 | 0.8995 | no |  |
| HL | NISR2 | 36.5744 | 27.1767 | 423 | --.HHZ/HHN/HHE | 2021-11-26 | 2021-11-26 | 1 | n/a | no |  |
| HL | NPS | 35.2613 | 25.6104 | 288 | --.HHZ/HHN/HHE | 2019-07-31 | 2010-07-17 | 3 | 0.6248 | no |  |
| HL | NVR | 41.3485 | 23.8652 | 627 | --.HHZ/HHN/HHE | 2024-10-23 | 2010-12-07 | 4 | 0.9509 | yes |  |
| HL | ORTH | 37.8511 | 20.6963 | 450 | --.HHZ/HHN/HHE | 2020-07-16 | 2018-10-27 | 3 | 0.9866 | yes |  |
| HL | OTHN | 39.8416 | 19.4057 | 3 | --.HHZ/HHN/HHE | 2022-06-28 | 2022-06-28 | 1 | 0.8305 | no |  |
| HL | PARNA | 38.5032 | 22.6441 | 1768 | --.HHZ/HHN/HHE | 2026-10-09 | 2026-10-09 | 1 | 0.0 | no |  |
| HL | PARNI | 38.1558 | 23.7593 | 864 | --.HHZ/HHN/HHE | 2026-10-05 | 2026-10-05 | 1 | 0.0 | no |  |
| HL | PENT | 40.1961 | 21.1380 | 1134 | --.HHZ/HHN/HHE | 2024-05-23 | 2010-10-22 | 3 | 0.9999 | yes |  |
| HL | PLG | 40.3733 | 23.4444 | 566 | --.HHZ/HHN/HHE | 2021-11-08 | 2010-12-08 | 7 | 0.9833 | yes |  |
| HL | PRAS | 41.3524 | 24.5500 | 671 | --.HHZ/HHN/HHE | 2021-05-19 | 2021-05-19 | 1 | 0.9542 | yes |  |
| HL | PRK | 39.2456 | 26.2650 | 130 | --.HHZ/HHN/HHE | 2012-12-29 | 2010-01-01 | 2 | 0.9859 | yes |  |
| HL | PTL | 38.0495 | 23.8646 | 506 | --.HHZ/HHN/HHE | 2026-10-02 | 2010-01-01 | 6 | 0.9999 | yes |  |
| HL | RDO | 41.1450 | 25.5355 | 116 | --.HHZ/HHN/HHE | 2021-05-18 | 2010-10-29 | 2 | 0.9969 | yes |  |
| HL | RLS | 38.0559 | 21.4647 | 97 | --.HHZ/HHN/HHE | 2020-03-10 | 2010-12-07 | 4 | 0.9837 | yes |  |
| HL | SAGMA | 38.3994 | 23.4111 | 743 | --.HHZ/HHN/HHE | 2026-10-06 | 2026-10-06 | 1 | 0.0 | no |  |
| HL | SANT | 36.3705 | 25.4593 | 591 | --.HHZ/HHN/HHE | 2024-04-08 | 2010-05-05 | 2 | 0.8466 | no |  |
| HL | SAP3 | 36.4356 | 25.3454 | 173 | --.HHZ/HHN/HHE | 2025-01-14 | 2011-06-23 | 2 | 0.9722 | yes |  |
| HL | SIVA | 35.0178 | 24.8120 | 96 | --.HHZ/HHN/HHE | 2011-07-21 | 2010-11-24 | 2 | 0.8249 | no |  |
| HL | SKYRO | 38.9021 | 24.5441 | 98 | --.HHZ/HHN/HHE | 2026-10-12 | 2026-10-12 | 1 | 0.0217 | no |  |
| HL | SMG | 37.7043 | 26.8377 | 348 | --.HHZ/HHN/HHE | 2020-11-03 | 2010-01-01 | 3 | 0.8682 | no |  |
| HL | SMTH | 40.4709 | 25.5304 | 365 | --.HHZ/HHN/HHE | 2010-01-01 | 2010-01-01 | 1 | 0.207 | no |  |
| HL | SOUNI | 37.7198 | 24.0218 | 173 | --.HHZ/HHN/HHE | 2026-10-01 | 2026-10-01 | 1 | 0.0 | no |  |
| HL | SPART | 37.0612 | 22.3790 | 481 | --.HHZ/HHN/HHE | 2026-04-07 | 2026-04-07 | 1 | 0.0 | no |  |
| HL | TENAR | 36.4215 | 22.4898 | 141 | --.HHZ/HHN/HHE | 2026-04-21 | 2026-04-21 | 1 | 0.0 | no |  |
| HL | TETR | 39.3445 | 21.2747 | 942 | --.HHZ/HHN/HHE | 2018-11-05 | 2018-11-05 | 1 | 0.9782 | yes |  |
| HL | THERA | 36.3670 | 25.4753 | 288 | --.HHZ/HHN/HHE | 2019-06-14 | 2019-06-14 | 1 | 0.8262 | no |  |
| HL | THL | 39.5647 | 22.0144 | 86 | --.HHZ/HHN/HHE | 2010-12-07 | 2010-12-07 | 1 | 0.9626 | yes |  |
| HL | VAM | 35.4070 | 24.1997 | 225 | --.HHZ/HHN/HHE | 2019-11-29 | 2010-05-29 | 4 | 0.3822 | no |  |
| HL | VARD | 38.7026 | 22.1600 | 1469 | --.HHZ/HHN/HHE | 2026-10-08 | 2026-10-08 | 1 | 0.0 | no |  |
| HL | VLI | 36.7180 | 22.9469 | 220 | --.HHZ/HHN/HHE | 2013-12-29 | 2010-01-01 | 2 | 0.9225 | yes |  |
| HL | VLS | 38.1768 | 20.5886 | 402 | --.HHZ/HHN/HHE | 2011-11-29 | 2010-12-07 | 2 | 0.9451 | yes |  |
| HL | VLY | 37.8524 | 23.7942 | 256 | --.HHZ/HHN/HHE | 2012-12-14 | 2010-01-01 | 3 | 0.9934 | yes |  |
| HL | ZARAX | 36.9148 | 23.0034 | 586 | --.HHZ/HHN/HHE | 2026-04-08 | 2026-04-08 | 1 | 0.0 | no |  |
| HL | ZKR | 35.1147 | 26.2169 | 254 | --.HHZ/HHN/HHE | 2023-05-02 | 2011-07-19 | 2 | 0.9929 | yes |  |
| HP | AMPL | 38.9224 | 21.2135 | 260 | --.HHZ/HHN/HHE | 2019-04-22 | 2019-04-22 | 1 | 0.9988 | yes |  |
| HP | AMT | 37.5324 | 21.7089 | 482 | 00.HHZ/HHN/HHE | 2018-04-21 | 2018-04-21 | 1 | 0.9915 | yes |  |
| HP | ANX | 38.5933 | 21.9209 | 1020 | --.HHZ/HHN/HHE | 2010-12-15 | 2010-12-15 | 1 | n/a | no |  |
| HP | AXS | 38.1962 | 21.3763 | 102 | --.HHZ/HHN/HHE | 2021-12-20 | 2012-07-04 | 3 | 0.9746 | yes |  |
| HP | DRO | 37.9520 | 21.7100 | 465 | --.HHZ/HHN/HHE | 2019-07-26 | 2009-09-21 | 2 | 0.9517 | yes |  |
| HP | DSF | 38.4112 | 22.5271 | 701 | --.HHZ/HHN/HHE | 2023-05-31 | 2008-02-29 | 4 | 0.9974 | yes |  |
| HP | EFP | 38.4269 | 21.9058 | 107 | --.HHZ/HHN/HHE | 2023-12-04 | 2008-01-05 | 6 | 0.9941 | yes |  |
| HP | FSK | 38.4593 | 20.5623 | 113 | --.HHZ/HHN/HHE | 2021-01-17 | 2012-03-27 | 3 | 0.9975 | yes |  |
| HP | GUR | 37.9363 | 22.3423 | 1087 | --.HHZ/HHN/HHE | 2024-10-07 | 2006-04-13 | 4 | 0.9234 | yes |  |
| HP | KSTR | 39.2492 | 20.5760 | 30 | --.HHZ/HHN/HHE | 2022-01-31 | 2022-01-31 | 1 | n/a | no |  |
| HP | LTHK | 37.7095 | 20.8367 | 35 | --.HHZ/HHN/HHE | 2022-03-22 | 2015-04-22 | 3 | 0.9386 | yes |  |
| HP | LTK | 38.0228 | 22.9673 | 408 | --.HHZ/HHN/HHE | 2018-11-23 | 2006-12-04 | 3 | 0.9361 | yes |  |
| HP | MANGA | 36.6628 | 25.3703 | 15 | --.HHZ/HHN/HHE | 2026-07-12 | 2026-07-12 | 1 | 0.1492 | no | HHE |
| HP | PDO | 38.5986 | 21.1833 | 227 | --.HHZ/HHN/HHE | 2016-06-05 | 2009-10-12 | 6 | 0.9908 | yes |  |
| HP | PLEV | 38.4124 | 21.4073 | 168 | --.HHZ/HHN/HHE | 2023-05-30 | 2020-03-12 | 3 | 0.994 | yes |  |
| HP | PRMD | 39.5299 | 21.0965 | 832 | --.HHZ/HHN/HHE | 2019-07-22 | 2019-07-22 | 1 | 0.8808 | no |  |
| HP | PVO | 38.6160 | 21.5250 | 184 | --.HHZ/HHN/HHE | 2023-02-03 | 2011-05-01 | 2 | 0.9024 | yes |  |
| HP | PYL | 36.8955 | 21.7420 | 226 | --.HHZ/HHN/HHE | 2024-11-26 | 2007-12-28 | 5 | 0.8179 | no |  |
| HP | SERG | 38.4133 | 22.0566 | 480 | --.HHZ/HHN/HHE | 2025-09-09 | 2010-06-30 | 4 | 0.9219 | yes |  |
| HP | UPR | 38.2836 | 21.7864 | 138 | --.HHZ/HHN/HHE | 2022-10-27 | 2007-12-28 | 5 | 0.9913 | yes |  |
| HP | VLX | 37.3703 | 22.3793 | 1035 | --.HHZ/HHN/HHE | 2019-02-01 | 2006-07-28 | 2 | 0.8509 | no |  |
| HP | VVK | 38.4222 | 21.8116 | 650 | --.HHZ/HHN/HHE | 2022-07-01 | 2018-07-31 | 2 | 0.9711 | yes |  |
| HT | ACHL | 39.0083 | 22.9581 | 5 | --.HHZ/HHN/HHE | 2023-03-14 | 2022-05-17 | 2 | 0.9473 | yes |  |
| HT | AGG | 39.0211 | 22.3360 | 625 | --.HHZ/HHN/HHE | 2018-09-05 | 2007-12-20 | 10 | 0.7629 | no |  |
| HT | AKRO | 36.3584 | 25.3967 | 179 | --.HHZ/HHN/HHE | 2024-02-12 | 2024-02-12 | 1 | 0.9899 | yes |  |
| HT | ALN | 40.8957 | 26.0497 | 58 | --.HHZ/HHN/HHE | 2025-10-22 | 2007-12-20 | 6 | 0.7936 | no | HHN/HHE |
| HT | AMPK | 39.0574 | 26.3130 | 358 | --.HHZ/HHN/HHE | 2024-03-21 | 2024-03-21 | 1 | 0.9661 | yes |  |
| HT | ANYD | 36.6300 | 25.6779 | 56 | --.HHZ/HHN/HHE | 2025-02-03 | 2025-02-03 | 1 | 0.6427 | no |  |
| HT | AOS2 | 39.1478 | 23.8436 | 185 | --.HHZ/HHN/HHE | 2018-07-07 | 2018-07-07 | 1 | 0.9875 | yes |  |
| HT | CHOS | 38.3869 | 26.0506 | 854 | --.HHZ/HHN/HHE | 2014-11-28 | 2007-12-20 | 2 | 0.8534 | no |  |
| HT | CHRI | 36.2491 | 25.2076 | 51 | --.HHZ/HHN/HHE | 2025-02-26 | 2025-02-26 | 1 | 0.6047 | no |  |
| HT | CMBO | 36.4709 | 25.4056 | 108 | --.HHZ/HHN/HHE | 2015-03-25 | 2011-02-02 | 3 | 0.7123 | no |  |
| HT | DMLN | 38.2385 | 20.3734 | 370 | --.HHZ/HHN/HHE | 2014-09-19 | 2014-09-19 | 1 | 0.7935 | no |  |
| HT | DRAG | 38.6839 | 20.5746 | 348 | --.HHZ/HHN/HHE | 2025-04-01 | 2014-10-03 | 9 | 0.7258 | no |  |
| HT | EVGI | 38.6210 | 20.6560 | 249 | --.HHZ/HHN/HHE | 2014-07-10 | 2012-07-06 | 2 | 0.974 | yes |  |
| HT | FLNA | 40.7809 | 21.3863 | 730 | --.HHZ/HHN/HHE | 2026-05-29 | 2022-11-23 | 2 | 0.9757 | yes |  |
| HT | FNA | 40.7817 | 21.3836 | 806 | --.HHZ/HHN/HHE | 2016-11-03 | 2008-01-14 | 5 | 0.0 | no |  |
| HT | GRG | 40.9557 | 22.4029 | 558 | --.HHZ/HHN/HHE | 2025-05-06 | 2008-01-14 | 11 | 0.9725 | yes |  |
| HT | GVRL | 36.3456 | 25.4383 | 160 | --.HHZ/HHN/HHE | 2025-02-07 | 2025-02-07 | 1 | 0.8478 | no |  |
| HT | HMT1 | 40.2581 | 24.2476 | 351 | --.HHZ/HHN/HHE | 2024-09-29 | 2024-09-29 | 1 | 0.9926 | yes |  |
| HT | HORT | 40.5978 | 23.0996 | 933 | --.HHZ/HHN/HHE | 2016-03-02 | 2008-01-14 | 4 | 0.9854 | yes |  |
| HT | IGT | 39.5314 | 20.3300 | 240 | --.HHZ/HHN/HHE | 2025-03-07 | 2008-07-11 | 5 | 0.7435 | no | HHN/HHE |
| HT | ITHC | 38.4622 | 20.6320 | 356 | --.HHZ/HHN/HHE | 2023-09-18 | 2023-09-18 | 1 | 0.8394 | no |  |
| HT | KAVA | 40.9967 | 24.5137 | 112 | --.HHZ/HHN/HHE | 2024-03-28 | 2008-07-03 | 12 | 0.9885 | yes |  |
| HT | KNT | 41.1670 | 22.9005 | 385 | --.HHZ/HHN/HHE | 2024-08-28 | 2008-11-03 | 5 | 0.9513 | yes |  |
| HT | KOKK | 40.8178 | 23.9992 | 261 | --.HHZ/HHN/HHE | 2023-05-30 | 2015-12-09 | 4 | 0.9963 | yes | HHN/HHE |
| HT | KPRO | 39.9549 | 21.3632 | 837 | --.HHZ/HHN/HHE | 2017-07-12 | 2011-04-01 | 3 | 0.8723 | no |  |
| HT | KRND | 37.3830 | 23.1502 | 140 | --.HHZ/HHN/HHE | 2026-02-06 | 2010-06-09 | 3 | 0.703 | no |  |
| HT | LES3 | 39.3032 | 26.1807 | 218 | --.HHZ/HHN/HHE | 2023-10-12 | 2023-10-12 | 1 | 0.9905 | yes |  |
| HT | LIT | 40.1003 | 22.4894 | 517 | --.HHZ/HHN/HHE | 2018-02-23 | 2006-02-01 | 6 | 0.9309 | yes | HHN/HHE |
| HT | LKD2 | 38.7889 | 20.6578 | 485 | --.HHZ/HHN/HHE | 2009-04-03 | 2008-07-29 | 3 | 0.9319 | yes |  |
| HT | NESN | 39.7267 | 22.5399 | 101 | --.HHZ/HHN/HHE | 2021-03-06 | 2021-03-06 | 1 | 0.9532 | yes |  |
| HT | NEST | 40.4147 | 21.0489 | 999 | --.HHZ/HHN/HHE | 2013-09-25 | 2008-07-29 | 4 | 0.9321 | yes |  |
| HT | NIS1 | 36.6023 | 27.1782 | 378 | --.HHZ/HHN/HHE | 2008-07-29 | 2008-07-29 | 1 | 0.0 | no |  |
| HT | NYDR | 38.7135 | 20.6983 | 14 | --.HHZ/HHN/HHE | 2023-03-12 | 2014-10-03 | 3 | 0.9846 | yes |  |
| HT | OUR | 40.3325 | 23.9791 | 117 | --.HHZ/HHN/HHE | 2014-09-02 | 2008-07-11 | 2 | 0.9956 | yes |  |
| HT | PAIG | 39.9363 | 23.6768 | 163 | --.HHZ/HHN/HHE | 2025-10-21 | 2008-01-14 | 9 | 0.9786 | yes | HHN/HHE |
| HT | PSDA | 38.1140 | 20.5841 | 48 | --.HHZ/HHN/HHE | 2014-10-15 | 2014-10-15 | 1 | 0.5794 | no |  |
| HT | RTZL | 38.0760 | 20.7715 | 103 | --.HHZ/HHN/HHE | 2019-09-21 | 2018-06-14 | 2 | 0.7534 | no |  |
| HT | SIGR | 39.2114 | 25.8553 | 90 | --.HHZ/HHN/HHE | 2010-05-25 | 2008-02-12 | 7 | 0.8393 | no |  |
| HT | SOH | 40.8206 | 23.3557 | 677 | --.HHZ/HHN/HHE | 2025-01-31 | 2006-02-01 | 8 | 0.9504 | yes |  |
| HT | SRS | 41.1086 | 23.5846 | 274 | --.HHZ/HHN/HHE | 2024-01-12 | 2008-02-13 | 3 | 0.9357 | yes | HHN/HHE |
| HT | STRF | 37.2497 | 21.0130 | 8 | --.HHZ/HHN/HHE | 2024-08-04 | 2022-09-08 | 3 | 0.2915 | no |  |
| HT | THAS | 40.6064 | 24.7194 | 67 | --.HHZ/HHN/HHE | 2012-07-04 | 2012-07-04 | 1 | 0.9502 | yes |  |
| HT | THE | 40.6319 | 22.9628 | 132 | --.HHZ/HHN/HHE | 2015-12-18 | 2008-01-08 | 8 | 0.9684 | yes |  |
| HT | THR3 | 36.4091 | 25.4008 | 71 | --.HHZ/HHN/HHE | 2025-02-07 | 2025-02-07 | 1 | 0.9401 | yes |  |
| HT | THR5 | 36.4172 | 25.3479 | 180 | --.HHZ/HHN/HHE | 2025-02-08 | 2025-02-08 | 1 | 0.9382 | yes |  |
| HT | THR8 | 36.4070 | 25.4788 | 30 | --.HHZ/HHN/HHE | 2025-02-05 | 2025-02-05 | 1 | 0.9291 | yes |  |
| HT | THT1 | 36.3858 | 25.4296 | 0 | --.HHZ/HHN/HHE | 2022-04-01 | 2011-09-27 | 4 | 0.0 | no |  |
| HT | TSLK | 38.8249 | 20.6554 | 212 | --.HHZ/HHN/HHE | 2012-10-10 | 2012-10-10 | 1 | 0.985 | yes |  |
| HT | TYRN | 39.7110 | 22.2325 | 151 | --.HHZ/HHN/HHE | 2026-06-03 | 2015-12-18 | 4 | 0.8797 | no |  |
| HT | XOR | 39.3660 | 23.1918 | 541 | --.HHZ/HHN/HHE | 2018-11-21 | 2008-02-12 | 2 | 0.8643 | no |  |

#### nz: 133 stations with three HH at 100 Hz (>= 90%: 107)

| net | code | lat | lon | elev m | loc.channels | current epoch from | HH since | epochs | cov min | >=90% | horiz. off N/E |
|---|---|---|---|---|---|---|---|---|---|---|---|
| NZ | ABAZ | -36.6002 | 174.8323 | 74 | 12.HHZ/HH1/HH2 | 2024-11-20 | 2024-11-20 | 1 | 0.9985 | yes | HH1/HH2 |
| NZ | AKFZ | -36.6057 | 174.5224 | 94 | 10.HHZ/HHN/HHE | 2023-03-21 | 2023-03-21 | 1 | 0.9985 | yes |  |
| NZ | APZ | -46.8318 | 167.9888 | 601 | 10.HHZ/HHN/HHE | 2022-04-13 | 2006-05-07 | 3 | 0.9805 | yes |  |
| NZ | ARHZ | -39.2631 | 176.9959 | 270 | 10.HHZ/HHN/HHE | 2026-10-07 | 2026-10-07 | 1 | 0.0301 | no |  |
| NZ | AWKZ | -35.9078 | 173.9065 | 68 | 10.HHZ/HHN/HHE | 2022-12-21 | 2022-12-21 | 1 | 0.9985 | yes |  |
| NZ | BFZ | -40.6797 | 176.2463 | 283 | 10.HHZ/HHN/HHE | 2021-04-29 | 2003-07-30 | 9 | 0.9985 | yes |  |
| NZ | BKZ | -39.1657 | 176.4925 | 706 | 10.HHZ/HHN/HHE | 2021-10-20 | 2004-02-11 | 4 | 0.9985 | yes |  |
| NZ | BSWZ | -41.7149 | 173.8757 | 277 | 10.HHZ/HHN/HHE | 2024-04-11 | 2024-04-11 | 1 | 0.9985 | yes |  |
| NZ | COVZ | -39.1999 | 175.5424 | 1133 | 11.HHZ/HH1/HH2 | 2024-09-25 | 2024-09-25 | 1 | 0.9985 | yes | HH1/HH2 |
| NZ | CTZ | -43.7355 | -176.6172 | 99 | 10.HHZ/HHN/HHE | 2021-11-24 | 2007-12-15 | 2 | 0.9985 | yes | HHN/HHE |
| NZ | CVZ | -44.3832 | 171.0062 | 454 | 10.HHZ/HHN/HHE | 2018-09-06 | 2014-05-16 | 3 | 0.9985 | yes |  |
| NZ | DBHZ | -43.2883 | 171.3154 | 708 | 10.HHZ/HH1/HH2 | 2024-11-07 | 2024-11-07 | 1 | 0.9985 | yes | HH1/HH2 |
| NZ | DCZ | -45.4647 | 167.1535 | 71 | 10.HHZ/HHN/HHE | 2024-03-13 | 2005-07-23 | 6 | 0.9985 | yes |  |
| NZ | DSZ | -41.7450 | 171.8046 | 650 | 10.HHZ/HHN/HHE | 2021-11-10 | 1998-10-15 | 6 | 0.9985 | yes |  |
| NZ | EAZ | -45.2311 | 169.3082 | 350 | 10.HHZ/HHN/HHE | 2024-09-03 | 2004-11-01 | 4 | 0.9985 | yes |  |
| NZ | ERWZ | -43.5227 | 170.8613 | 594 | 10.HHZ/HH1/HH2 | 2025-06-18 | 2025-06-18 | 1 | 0.7218 | no | HH1/HH2 |
| NZ | ETVZ | -39.1357 | 175.7106 | 1236 | 10.HHZ/HHN/HHE | 2023-09-01 | 2014-03-12 | 4 | 0.9985 | yes |  |
| NZ | FEGZ | -39.0472 | 174.3401 | 192 | 10.HHZ/HH1/HH2 | 2023-04-30 | 2023-04-30 | 1 | 0.9985 | yes | HH1/HH2 |
| NZ | FOZ | -43.5321 | 169.8155 | 54 | 11.HHZ/HHN/HHE | 2018-12-11 | 2015-09-23 | 3 | 0.9955 | yes |  |
| NZ | FRNZ | -43.4531 | 170.0993 | 1341 | 10.HHZ/HHN/HHE | 2026-02-09 | 2026-02-09 | 1 | 0.391 | no |  |
| NZ | FWVZ | -39.2550 | 175.5530 | 2043 | 10.HHZ/HHN/HHE | 2025-02-03 | 1999-05-11 | 8 | 0.9985 | yes |  |
| NZ | GLKZ | -29.2607 | -177.9180 | 30 | 10.HHZ/HHN/HHE | 2021-10-24 | 2009-05-19 | 3 | 0.2752 | no |  |
| NZ | GRZ | -36.2502 | 175.4578 | 146 | 10.HHZ/HHN/HHE | 2026-06-08 | 2010-05-13 | 5 | 0.9985 | yes |  |
| NZ | GVZ | -42.9674 | 173.0348 | 400 | 10.HHZ/HHN/HHE | 2024-04-02 | 2012-12-04 | 3 | 0.9985 | yes |  |
| NZ | HATZ | -38.8908 | 176.0921 | 506 | 10.HHZ/HHN/HHE | 2023-10-04 | 2023-10-04 | 1 | 0.9985 | yes |  |
| NZ | HAZ | -37.7561 | 177.7826 | 81 | 10.HHZ/HHN/HHE | 2026-07-21 | 2010-01-14 | 3 | 0.9985 | yes |  |
| NZ | HIZ | -38.5129 | 174.8557 | 237 | 10.HHZ/HHN/HHE | 2021-05-21 | 2004-02-03 | 4 | 0.9985 | yes |  |
| NZ | HNCZ | -38.3858 | 176.2880 | 645 | 10.HHZ/HH1/HH2 | 2023-08-23 | 2023-08-23 | 1 | 0.9985 | yes | HH1/HH2 |
| NZ | HORZ | -43.7773 | 170.1055 | 943 | 10.HHZ/HH1/HH2 | 2025-01-30 | 2025-01-30 | 1 | 0.9549 | yes | HH1/HH2 |
| NZ | HPRZ | -42.6080 | 171.7726 | 1147 | 10.HHZ/HH1/HH2 | 2025-03-19 | 2025-03-19 | 1 | 0.8827 | no | HH1/HH2 |
| NZ | HSPZ | -44.0498 | 169.3037 | 1237 | 10.HHZ/HH1/HH2 | 2025-02-27 | 2025-02-27 | 1 | 0.9128 | yes |  |
| NZ | HTPZ | -35.3657 | 174.0130 | 247 | 10.HHZ/HHN/HHE | 2022-12-19 | 2022-12-19 | 1 | 0.9985 | yes |  |
| NZ | IFMZ | -43.0238 | 171.0608 | 1339 | 10.HHZ/HH1/HH2 | 2025-03-16 | 2025-03-16 | 1 | 0.8872 | no | HH1/HH2 |
| NZ | INZ | -42.7245 | 171.4441 | 165 | 10.HHZ/HHN/HHE | 2025-09-16 | 2011-01-26 | 6 | 0.9895 | yes |  |
| NZ | JBLZ | -35.5339 | 174.3913 | 212 | 10.HHZ/HHN/HHE | 2022-12-20 | 2022-12-20 | 1 | 0.9985 | yes |  |
| NZ | JCZ | -44.0732 | 168.7855 | 1062 | 10.HHZ/HHN/HHE | 2026-07-22 | 2004-06-23 | 5 | 0.9654 | yes |  |
| NZ | KARZ | -38.0202 | 176.2443 | 405 | 11.HHZ/HHN/HHE | 2024-08-30 | 2024-08-30 | 1 | 0.8361 | no |  |
| NZ | KBAZ | -37.0947 | 174.8886 | 12 | 12.HHZ/HH1/HH2 | 2025-04-28 | 2025-04-28 | 1 | 0.8226 | no | HH1/HH2 |
| NZ | KHEZ | -39.2942 | 174.0145 | 929 | 12.HHZ/HHN/HHE | 2025-05-06 | 2025-05-06 | 1 | 0.8105 | no |  |
| NZ | KHZ | -42.4160 | 173.5390 | 64 | 10.HHZ/HHN/HHE | 2021-05-27 | 2003-08-06 | 6 | 0.9985 | yes |  |
| NZ | KNZ | -39.0218 | 177.6737 | 32 | 10.HHZ/HHN/HHE | 2026-03-19 | 1998-10-19 | 7 | 0.9729 | yes |  |
| NZ | KPFZ | -36.4269 | 174.6165 | 109 | 10.HHZ/HHN/HHE | 2023-03-17 | 2023-03-17 | 1 | 0.9985 | yes |  |
| NZ | KPRZ | -38.8020 | 175.7929 | 593 | 10.HHZ/HHN/HHE | 2022-12-13 | 2022-12-13 | 1 | 0.9985 | yes |  |
| NZ | KRBZ | -36.8919 | 175.4635 | 284 | 10.HHZ/HHN/HHE | 2023-05-10 | 2023-05-10 | 1 | 0.9985 | yes |  |
| NZ | KRVZ | -39.0944 | 175.6412 | 1207 | 10.HHZ/HHN/HHE | 2024-06-21 | 2024-06-21 | 1 | 0.9985 | yes |  |
| NZ | KUZ | -36.7452 | 175.7209 | 76 | 10.HHZ/HHN/HHE | 2021-11-11 | 2004-02-05 | 3 | 0.9985 | yes |  |
| NZ | KWHZ | -39.4240 | 176.4228 | 854 | 10.HHZ/HHN/HHE | 2026-03-24 | 2026-03-24 | 1 | 0.3263 | no |  |
| NZ | LBZ | -44.3856 | 170.1844 | 438 | 10.HHZ/HHN/HHE | 2025-01-29 | 2004-06-04 | 4 | 0.9985 | yes |  |
| NZ | LIRZ | -38.0036 | 176.3852 | 340 | 10.HHZ/HHN/HHE | 2025-06-13 | 2024-09-04 | 2 | 0.985 | yes |  |
| NZ | LRRZ | -36.1463 | 174.5383 | 142 | 10.HHZ/HHN/HHE | 2023-03-19 | 2023-03-19 | 1 | 0.9985 | yes |  |
| NZ | LTZ | -42.7817 | 172.2710 | 648 | 10.HHZ/HHN/HHE | 2025-06-18 | 2004-02-27 | 5 | 0.9985 | yes |  |
| NZ | MAVZ | -39.2679 | 175.5616 | 2624 | 10.HHZ/HH1/HH2 | 2026-03-23 | 2012-05-22 | 7 | 0.3293 | no |  |
| NZ | MBAZ | -36.7688 | 174.8979 | 60 | 10.HHZ/HH1/HH2 | 2025-03-12 | 2025-03-12 | 1 | 0.8932 | no | HH1/HH2 |
| NZ | MKAZ | -37.1041 | 175.1612 | 140 | 10.HHZ/HHN/HHE | 2022-12-08 | 2007-05-10 | 3 | 0.9985 | yes |  |
| NZ | MKTZ | -43.8706 | 169.1795 | 1098 | 10.HHZ/HH1/HH2 | 2025-09-30 | 2025-02-20 | 2 | 0.9158 | yes | HH2 |
| NZ | MLZ | -45.3665 | 168.1184 | 594 | 10.HHZ/HHN/HHE | 2022-07-07 | 2003-09-08 | 4 | 0.9985 | yes |  |
| NZ | MNMZ | -39.0216 | 175.8353 | 469 | 10.HHZ/HH1/HH2 | 2023-09-14 | 2023-09-14 | 1 | 0.9985 | yes | HH1/HH2 |
| NZ | MNTZ | -35.4195 | 173.7085 | 285 | 10.HHZ/HHN/HHE | 2022-12-19 | 2022-12-19 | 1 | 0.9985 | yes |  |
| NZ | MOVZ | -39.4068 | 175.7528 | 874 | 10.HHZ/HHN/HHE | 2025-08-21 | 2025-08-21 | 1 | 0.6496 | no |  |
| NZ | MQZ | -43.7061 | 172.6538 | 57 | 13.HHZ/HHN/HHE | 2025-09-18 | 2025-09-18 | 1 | 0.6075 | no |  |
| NZ | MRTZ | -39.2086 | 174.0854 | 477 | 10.HHZ/HHN/HHE | 2026-06-17 | 2026-06-17 | 1 | 0.1985 | no |  |
| NZ | MRZ | -40.6606 | 175.5785 | 286 | 10.HHZ/HHN/HHE | 2022-08-12 | 2003-07-31 | 3 | 0.9985 | yes |  |
| NZ | MSZ | -44.6733 | 167.9264 | 55 | 10.HHZ/HHN/HHE | 2026-06-10 | 2005-07-19 | 5 | 0.9805 | yes |  |
| NZ | MTVZ | -39.3846 | 175.4704 | 840 | 10.HHZ/HHN/HHE | 2024-06-13 | 2024-06-13 | 1 | 0.9985 | yes |  |
| NZ | MWOZ | -39.3974 | 174.0870 | 410 | 10.HHZ/HH1/HH2 | 2023-04-18 | 2023-04-18 | 1 | 0.9985 | yes | HH1/HH2 |
| NZ | MWZ | -38.3340 | 177.5278 | 573 | 10.HHZ/HHN/HHE | 2021-11-01 | 2004-02-29 | 4 | 0.9985 | yes |  |
| NZ | MXZ | -37.5623 | 178.3066 | 106 | 10.HHZ/HHN/HHE | 2024-08-15 | 2004-02-29 | 5 | 0.9789 | yes |  |
| NZ | NGZ | -39.1756 | 175.6012 | 1452 | 10.HHZ/HHN/HHE | 2024-06-21 | 2024-06-21 | 1 | 0.9985 | yes |  |
| NZ | NNZ | -41.2171 | 173.3795 | 130 | 10.HHZ/HHN/HHE | 2023-03-29 | 2003-08-12 | 7 | 0.9985 | yes |  |
| NZ | NTVZ | -39.0985 | 175.6760 | 1260 | 10.HHZ/HHN/HHE | 2025-08-22 | 2014-11-07 | 4 | 0.9985 | yes |  |
| NZ | OAHZ | -38.8458 | 176.0475 | 662 | 10.HHZ/HHN/HHE | 2026-10-16 | 2022-12-07 | 2 | 0.985 | yes |  |
| NZ | ODZ | -45.0440 | 170.6446 | 274 | 10.HHZ/HHN/HHE | 2021-10-21 | 2003-09-11 | 4 | 0.9985 | yes |  |
| NZ | OHWZ | -40.2056 | 175.3151 | 59 | 10.HHZ/HHN/HHE | 2026-09-06 | 2024-05-22 | 2 | 0.9835 | yes |  |
| NZ | OMRZ | -38.1062 | 176.3717 | 566 | 10.HHZ/HHN/HHE | 2024-06-19 | 2024-06-19 | 1 | 0.9985 | yes |  |
| NZ | OPRZ | -37.8443 | 176.5549 | 134 | 10.HHZ/HHN/HHE | 2024-06-11 | 2007-06-19 | 4 | 0.9985 | yes |  |
| NZ | OPZ | -45.8844 | 170.5978 | 375 | 10.HHZ/HHN/HHE | 2023-03-29 | 2008-06-27 | 5 | 0.9985 | yes |  |
| NZ | ORRZ | -36.9727 | 174.7705 | 44 | 10.HHZ/HH1/HH2 | 2025-04-16 | 2025-04-16 | 1 | 0.8406 | no | HH1/HH2 |
| NZ | OTNZ | -35.5902 | 173.8251 | 142 | 10.HHZ/HHN/HHE | 2022-12-20 | 2022-12-20 | 1 | 0.9985 | yes |  |
| NZ | OTVZ | -39.1631 | 175.6651 | 1506 | 10.HHZ/HHN/HHE | 2024-08-15 | 2011-11-11 | 3 | 0.9985 | yes |  |
| NZ | OUZ | -35.2197 | 173.5961 | 63 | 10.HHZ/HHN/HHE | 2024-05-29 | 2002-08-30 | 6 | 0.9985 | yes |  |
| NZ | OXZ | -43.3259 | 172.0383 | 360 | 10.HHZ/HHN/HHE | 2023-02-10 | 2009-03-14 | 3 | 0.9925 | yes |  |
| NZ | PAKZ | -35.5347 | 174.1302 | 259 | 10.HHZ/HHN/HHE | 2022-12-19 | 2022-12-19 | 1 | 0.9985 | yes |  |
| NZ | PKAZ | -35.7757 | 174.2131 | 204 | 10.HHZ/HHN/HHE | 2022-12-21 | 2022-12-21 | 1 | 0.9985 | yes |  |
| NZ | PKGZ | -37.8664 | 178.0805 | 405 | 10.HHZ/HHN/HHE | 2026-07-21 | 2026-07-21 | 1 | 0.0827 | no |  |
| NZ | PKTZ | -38.6724 | 175.8046 | 495 | 10.HHZ/HH1/HH2 | 2024-07-16 | 2024-07-16 | 1 | 0.9985 | yes | HH1/HH2 |
| NZ | PNUZ | -37.3976 | 174.8411 | 240 | 10.HHZ/HHN/HHE | 2023-05-11 | 2023-05-11 | 1 | 0.9985 | yes |  |
| NZ | PREZ | -39.3421 | 174.1589 | 613 | 10.HHZ/HHN/HHE | 2026-05-27 | 2026-05-27 | 1 | 0.2195 | no |  |
| NZ | PTAZ | -35.7089 | 174.4972 | 99 | 10.HHZ/HHN/HHE | 2022-12-08 | 2022-12-08 | 1 | 0.9985 | yes |  |
| NZ | PUZ | -38.0716 | 178.2572 | 430 | 10.HHZ/HHN/HHE | 2021-11-02 | 2003-08-20 | 3 | 0.9985 | yes |  |
| NZ | PXZ | -40.0306 | 176.8622 | 103 | 10.HHZ/HHN/HHE | 2023-03-01 | 2005-08-22 | 4 | 0.9985 | yes |  |
| NZ | PYZ | -46.1662 | 166.6807 | 277 | 10.HHZ/HHN/HHE | 2024-12-01 | 2007-05-01 | 5 | 0.9985 | yes |  |
| NZ | QRZ | -40.8255 | 172.5291 | 263 | 10.HHZ/HHN/HHE | 2021-10-05 | 2003-08-06 | 7 | 0.9985 | yes |  |
| NZ | RATZ | -38.8665 | 175.7722 | 653 | 10.HHZ/HHN/HHE | 2019-02-14 | 2008-10-20 | 3 | 0.9985 | yes |  |
| NZ | RDHZ | -44.2476 | 168.3570 | 1206 | 10.HHZ/HH1/HH2 | 2025-02-26 | 2025-02-26 | 1 | 0.9143 | yes | HH1/HH2 |
| NZ | RIZ | -29.2449 | -177.9289 | 110 | 10.HHZ/HHN/HHE | 2021-02-12 | 2009-05-18 | 5 | 0.8692 | no |  |
| NZ | RPZ | -43.7146 | 171.0539 | 453 | 10.HHZ/HH1/HH2 | 2021-06-24 | 2001-06-06 | 7 | 0.9985 | yes | HH1/HH2 |
| NZ | RTZ | -38.6154 | 176.9805 | 867 | 10.HHZ/HHN/HHE | 2026-07-17 | 2011-08-04 | 4 | 0.9774 | yes |  |
| NZ | SLTZ | -43.9097 | 169.5931 | 1187 | 10.HHZ/HH1/HH2 | 2025-02-28 | 2025-02-28 | 1 | 0.9113 | yes | HH1/HH2 |
| NZ | SMRZ | -43.1959 | 170.7221 | 1326 | 10.HHZ/HH1/HH2 | 2025-03-16 | 2025-03-16 | 1 | 0.8872 | no | HH1/HH2 |
| NZ | SYZ | -46.5369 | 169.1388 | 52 | 10.HHZ/HHN/HHE | 2024-03-03 | 2006-05-05 | 5 | 0.9985 | yes |  |
| NZ | TGRZ | -37.7288 | 176.2608 | 145 | 11.HHZ/HHN/HHE | 2024-06-06 | 2024-06-06 | 1 | 0.9985 | yes |  |
| NZ | THZ | -41.7625 | 172.9052 | 747 | 10.HHZ/HHN/HHE | 2024-09-27 | 2003-08-08 | 5 | 0.9985 | yes |  |
| NZ | TKGZ | -38.4392 | 177.8485 | 157 | 10.HHZ/HHN/HHE | 2026-07-23 | 2026-07-23 | 1 | 0.1444 | no |  |
| NZ | TLZ | -38.3294 | 175.5380 | 660 | 10.HHZ/HHN/HHE | 2022-10-06 | 2009-05-07 | 3 | 0.9985 | yes |  |
| NZ | TMVZ | -39.1156 | 175.7041 | 1200 | 10.HHZ/HHN/HHE | 2025-12-09 | 2013-05-14 | 5 | 0.9624 | yes |  |
| NZ | TOZ | -37.7310 | 175.5018 | 85 | 10.HHZ/HHN/HHE | 2024-10-01 | 1998-10-15 | 4 | 0.9985 | yes |  |
| NZ | TRVZ | -39.2988 | 175.5478 | 2062 | 10.HHZ/HHN/HHE | 2024-10-23 | 2009-04-14 | 4 | 0.9985 | yes |  |
| NZ | TSZ | -40.0585 | 175.9611 | 531 | 10.HHZ/HHN/HHE | 2018-08-30 | 2004-01-26 | 3 | 0.9985 | yes |  |
| NZ | TTTZ | -35.3400 | 174.3041 | 103 | 10.HHZ/HHN/HHE | 2023-01-16 | 2023-01-16 | 1 | 0.9985 | yes |  |
| NZ | TUZ | -45.9540 | 169.6311 | 110 | 10.HHZ/HHN/HHE | 2022-07-07 | 2003-09-10 | 6 | 0.9985 | yes |  |
| NZ | TWGZ | -38.1767 | 177.9804 | 687 | 10.HHZ/HHN/HHE | 2026-07-21 | 2026-07-21 | 1 | 0.1429 | no |  |
| NZ | TWVZ | -39.0707 | 175.4377 | 1084 | 10.HHZ/HHN/HHE | 2025-05-13 | 2025-05-13 | 1 | 0.8 | no |  |
| NZ | UPKZ | -39.3049 | 173.9502 | 408 | 10.HHZ/HH1/HH2 | 2026-01-20 | 2025-11-27 | 2 | 0.4977 | no |  |
| NZ | URZ | -38.2593 | 177.1109 | 95 | 10.HHZ/HH1/HH2 | 2021-05-26 | 2001-05-21 | 9 | 0.9985 | yes | HH1/HH2 |
| NZ | UTU | -38.1766 | 176.1938 | 410 | 13.HHZ/HHN/HHE | 2024-07-03 | 2024-07-03 | 1 | 0.9985 | yes |  |
| NZ | VRZ | -39.1243 | 174.7585 | 166 | 10.HHZ/HHN/HHE | 2022-12-21 | 2003-11-26 | 7 | 0.9985 | yes |  |
| NZ | WATZ | -38.7079 | 175.7332 | 560 | 10.HHZ/HHN/HHE | 2024-08-07 | 2024-08-07 | 1 | 0.9985 | yes |  |
| NZ | WAZ | -39.7546 | 174.9855 | 382 | 10.HHZ/HHN/HHE | 2023-04-14 | 2003-07-18 | 4 | 0.9985 | yes |  |
| NZ | WCZ | -35.9386 | 174.3450 | 108 | 10.HHZ/HHN/HHE | 2023-05-30 | 2002-08-29 | 8 | 0.9985 | yes |  |
| NZ | WEL | -41.2841 | 174.7682 | 138 | 10.HHZ/HHN/HHE | 2023-12-06 | 2008-12-18 | 4 | 0.9925 | yes |  |
| NZ | WHSZ | -43.2906 | 170.4065 | 110 | 10.HHZ/HHN/HHE | 2021-11-03 | 2021-11-03 | 1 | 0.997 | yes |  |
| NZ | WHTZ | -38.6660 | 175.9575 | 778 | 13.HHZ/HHN/HHE | 2024-08-06 | 2024-08-06 | 1 | 0.9188 | yes |  |
| NZ | WHVZ | -39.2825 | 175.5886 | 2105 | 10.HHZ/HHN/HHE | 2025-02-03 | 2009-04-14 | 5 | 0.9985 | yes |  |
| NZ | WHZ | -45.8924 | 167.9470 | 345 | 10.HHZ/HHN/HHE | 2024-09-24 | 2001-04-07 | 5 | 0.9985 | yes |  |
| NZ | WIAZ | -36.7930 | 175.1339 | 255 | 11.HHZ/HH1/HH2 | 2024-10-09 | 2024-10-09 | 1 | 0.9985 | yes | HH1/HH2 |
| NZ | WKZ | -44.8270 | 169.0176 | 558 | 10.HHZ/HHN/HHE | 2021-12-08 | 2004-06-03 | 3 | 0.9985 | yes |  |
| NZ | WLCZ | -41.3044 | 174.7828 | 42 | 10.HHZ/HH1/HH2 | 2026-07-06 | 2024-10-16 | 2 | 0.9985 | yes | HH1/HH2 |
| NZ | WLRZ | -39.1652 | 173.9451 | 276 | 10.HHZ/HH1/HH2 | 2025-05-07 | 2025-05-07 | 1 | 0.809 | no | HH1/HH2 |
| NZ | WMVZ | -41.8845 | 174.0516 | 120 | 10.HHZ/HHN/HHE | 2025-06-06 | 2025-06-06 | 1 | 0.7639 | no |  |
| NZ | WRRZ | -41.4550 | 175.4557 | 214 | 10.HHZ/HHN/HHE | 2024-05-09 | 2024-05-09 | 1 | 0.9985 | yes |  |
| NZ | WTAZ | -36.9324 | 174.5734 | 340 | 13.HHZ/HH1/HH2 | 2025-03-11 | 2023-04-12 | 3 | 0.9985 | yes | HH1/HH2 |
| NZ | WTVZ | -39.1153 | 175.5897 | 1186 | 10.HHZ/HHN/HHE | 2024-06-21 | 2024-06-21 | 1 | 0.9729 | yes |  |
| NZ | WVZ | -43.0744 | 170.7368 | 91 | 10.HHZ/HHN/HHE | 2022-10-19 | 2003-09-06 | 6 | 0.9985 | yes |  |
