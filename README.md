# ayzek_heldout

Fetches the held-out test data for **ayzek**, the earthquake early-warning
detection pipeline, from three networks:

| set network | operator | service |
|---|---|---|
| `KO` | KOERI, Türkiye | `eida.koeri.boun.edu.tr` (station, dataselect, availability); catalogue: EMSC |
| `HL`, `HT` | NOA, AUTH (Greece) | NOA EIDA node `eida.gein.noa.gr` serves both (station, dataselect, availability, event) |
| `NZ` | GeoNet (Earth Sciences NZ) | `service.geonet.org.nz` (station, dataselect, event); no availability service |

It writes the layout ayzek replays and nothing else; it does not depend on
ayzek_code or any other repository at run time. `SURVEY.md` is the
metadata-only survey of the Greek and New Zealand networks behind the
pre-registered protocol (`survey/survey.py` regenerates its tables).

## Blindness rules (until the method is frozen)

The held-out pools (ayzek_code `docs/protocol-heldout.md`, section 3) start on
**2023-01-01** for Greece (HL, HT, HA, HP, HC) and New Zealand (NZ) and on
**2026-08-30** for KO. Before the freeze:

- No waveform or event list is fetched from a pool.
- Before the pools, the tool fetched: the 2012 service checks (`smoke_*`, one
  minute each), the 2012 dry runs (`dryrun_*`, 30 min), the rotation check
  (`rotcheck_nz_2012`), KO's development set `demo_ko`, and the per-station
  STA/LTA tuning windows (`tune_*`, four 6 h windows per network group, drawn by
  `tools/make_tuning_sets.py`), with their catalogues.
- Station metadata (fdsnws/station) and availability listings (fdsnws/
  availability, or the GeoNet bucket's object listing) are allowed for any
  period: they carry no seismic content.
- `pull` and `catalog` refuse a window that reaches into the pool of any of
  its networks (a span *ending* after the pool's start, so also one that
  starts before and runs into it) unless `--allow-test-period` is given.
  `probe` reads metadata and availability only and is not guarded.

The one exception made so far is ayzek's development set `demo_ko`
(2025-11-10, already used for development), pulled with
`--allow-test-period` to check the tool against ayzek's own copy; its
catalogue was not fetched. Every waveform and event request made while
building this repository is logged in `SURVEY.md`.

## Running

Python with ObsPy, managed with uv:

    uv sync
    uv run pytest                       # no network needed

    uv run heldout probe    sets/demo_ko.toml
    uv run heldout pull     sets/demo_ko.toml --allow-test-period
    uv run heldout catalog  sets/demo_ko.toml --allow-test-period
    uv run heldout validate sets/demo_ko.toml

A set is a TOML file in `sets/` (the protocol lists them; anyone can rebuild a
set from its file):

    name = "demo_ko"
    network = "KO"                 # or ["HL", "HT"]: networks on one service
    start = "2025-11-10T18:04:00"  # UTC
    end = "2025-11-10T18:35:00"
    centre = [39.22333, 28.16556]  # lat, lon
    radius_km = 150.0
    max_stations = 6
    min_coverage = 0.9             # optional, default 0.9
    max_azimuth_offset_deg = 5.0   # optional, default: keep rotated horizontals

    [catalog]                      # optional
    lead_days = 30                 # the 30 days before the span too (--assess)
    radius_km = 300.0              # default: twice radius_km
    min_magnitude = 0.0

**probe** asks the station service for HH channels over the span, keeps the
stations within `radius_km` whose current epochs have, at one location code,
HHZ plus HHN/HHE or HH1/HH2, all at exactly 100 Hz and covering the whole span
(anything else is refused: ayzek does not resample), then asks the
availability service what fraction of the span each channel covers (for NZ,
which has none, whether each UTC day's file exists in GeoNet's open-data
bucket: an upper bound). The nearest `max_stations` with at least
`min_coverage` on every channel are chosen; a station code already chosen
from another network is refused, since ayzek keys stations on the code alone.
It writes `stations.json` (every candidate and why it was kept or not), the
chosen stations' StationXML (`stationxml/`, response level), `stations.csv`
and `pd_gain.csv`. A vertical epoch gets a gain row only when its velocity
response divided by the stated sensitivity lies within 0.8-1.25 at 0.1, 0.2,
0.5, 1, 2 and 5 Hz (Pd divides by that one number); the others are listed with
the ratios under `gains_refused` in `stations.json` (and `pd_gains_refused` in
`dataset.json`), and ayzek does not measure Pd at those stations. No waveform
is requested.

**pull** downloads each chosen station hour by hour (a failure that outlasts
the retries below costs one hour, and is listed in `dataset.json`), keeps only the chosen location and three channels at 100 Hz with
integer samples, trims to the span, and writes `<STATION>.mseed` as 512-byte
big-endian Steim2 records (ayzek's reader takes nothing else). It then writes
`dataset.json`: the config, the networks and service URLs, span, centre,
radius, stations requested (with reasons) and chosen, what arrived per
station (seconds per component, bytes), the request failures, the retrieval
time in UTC, the tool's git commit (`+dirty` if uncommitted), the citations
and licences. `dataset.json` is validated first; if no station returned data,
nothing is written and the exit status is 2. A file is written only when it
has data, via a temporary file.

**catalog** queries the network's own catalogue over the span plus
`lead_days` before it and writes `catalog.csv` in the AFAD CSV that ayzek's
`--catalog` reads (`Date,Longitude,Latitude,Depth,Rms,Type,Magnitude,
Location,EventID`, date `DD/MM/YYYY HH:MM:SS` UTC, depth km, `Type` the
magnitude type as published). Events without depth or magnitude are left out
and listed in `dataset.json`. Catalogues: KO: EMSC fdsnws/event (KOERI runs no
FDSN event service, and AFAD's event API answers with an empty list, see
below); HL, HT, HA, HP, HC: NOA fdsnws/event (for HT standing in for AUTH's,
see below); NZ: GeoNet fdsnws/event.

Before the catalogue itself, the step asks the same service for the network's
canary (`heldout/networks.py`): a fixed window before the network's pool,
known to contain events (KO: the Sındırgı Mw 6.1 replay of 2025-08-10, 69
events from EMSC on 2026-10-29; Greece and New Zealand: the catalogue windows
of tune_greece_1 and tune_nz_1, 14 and 51 events). If fewer than about 40% of
those come back, the service is not trusted: nothing is written and the exit
status is 3. `dataset.json` records the canary's window, minimum, count and
request.

The set directory:

    data/<set>/<STATION>.mseed   three HH components
    data/<set>/dataset.json
    data/<set>/stations.json
    data/<set>/stations.csv      code,lat,lon,elev_m (ayzek models/stations.csv)
    data/<set>/pd_gain.csv       station,channel,start,end,sensitivity
                                 (ayzek models/pd_gain.csv; HHZ epochs in the span)
    data/<set>/stationxml/<NET>.<STA>.xml
    data/<set>/catalog.csv

## Replaying a set in ayzek

ayzek looks up coordinates (`models/stations.csv`) and Pd gains
(`models/pd_gain.csv`) by station code alone, from its models directory.
To replay a foreign set, the set's `stations.csv` and `pd_gain.csv` rows have
to reach that lookup (a copy of the models directory with the rows appended,
or an ayzek option to read them from the set); `SURVEY.md` lists the codes
that collide with codes ayzek already holds.

## Open points

- AUTH publishes its catalogue only as flat text files
  (`seismo.auth.gr/wp-content/uploads/CATALOGS/...`) covering 1995–2024 and
  2023–today. Reading either would reveal test-period events, so their format
  was not inspected and no parser exists yet; HT sets use NOA's catalogue
  until then.
- NOA's event service returned no event for 2012-06-01 within 1000 km of
  Athens (HTTP 204): it may not hold events that old, so its output format is
  checked only by the offline tests.
- NOA's availability service clips spans to the request window in a way that
  can return a span whose end precedes its start (seen for HT.THE on
  2012-06-01, which has no data that day); such spans count as zero. Under
  more than about two parallel requests the node drops connections and then
  stops answering for minutes: the tool uses two requests at a time, and a
  probe that still fails stops with an error rather than treating the station
  as empty.
- Every request to a service (stations, availability, waveforms, events) is
  made again after 5, 15, 45, 120 and 300 s while it fails with a server
  error, a timeout or a dropped connection, and never when the service
  answers, with no data or by refusing the request (`heldout/retry.py`). In
  the tuning fetch of 2026-10-29, before this, NOA dropped connections for
  longer than the availability requests' 45 s of retries, and KOERI's proxy
  answered 502 to one station's metadata request; each stopped a whole set.
- AFAD's event API (`servisnet.afad.gov.tr/apigateway/deprem/apiv2/event/filter`,
  to which `deprem.afad.gov.tr/apiv2` redirects) returned HTTP 200 with an empty
  list to every query of 2026-10-29: by time and area, by time alone, and by
  event id for development events (the Sındırgı hours of 2025-11-09/10 and
  Simav's of 2026-04-11). The KO tuning catalogues fetched from it were empty
  before the canary existed, and were fetched again from EMSC. Whether it
  serves recent events was not checked, since that would have meant asking
  for KO's test period. The AFAD reader stays, checked by the offline tests.

## Provenance

Adapted, not imported, from ayzek_code at commit `d6e8414`
(`git -C ../ayzek_code rev-parse --short HEAD` at the time). Rechecked at
`571e383` (branch pd-magnitude-window): the sources below, `models/
stations.csv`, `models/pd_gain.csv` and the catalogue reader are unchanged
between the two commits.

- `tools/fetch_ko_data.py`: the probe/pull structure, the hour-by-hour pull,
  merge-then-split of segments, the KO citation and the `demo_ko` set
  parameters. Changed: the probe uses station metadata and the availability
  service instead of one minute of waveforms per candidate; sets are TOML
  files, not a dict in the code; any of KO/HL/HT/NZ; one location code and
  three named channels per station instead of `*`/`HH?`; output forced to
  512-byte Steim2; seconds per component instead of their mean; a station
  already on disk is measured and listed (the original left it out of
  `dataset.json`); validation and the empty-set failure; the test-period
  guard; `quiet-scan` dropped.
- `tools/export_pd.py` (`gains`): the rule for the vertical channel's
  sensitivity (input units m/s, epoch start/end in seconds). Changed: HH only,
  the station's chosen location code, and only for a response flat across
  Pd's band (see probe).
- `tools/export_models.py`: the `stations.csv` header.
- The catalogue format follows `load_afad_catalog` (`src/pipeline/network.cpp`)
  and `tests/catalogs/demo_ko.csv`; the 512-byte record requirement follows
  `src/mseed.hpp`. No code is copied from them.
