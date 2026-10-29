"""The networks the tool fetches: where each one's services are, how to cite
it, and which catalogue goes with it.

Greek HL (NOA) and HT (AUTH) are both served by the NOA EIDA node, which also
hosts their availability service and NOA's event service. AUTH's own
catalogue is a flat text file, not a service (SURVEY.md), so the HT catalogue
is NOA's for now; see README.md.

Each network's catalogue service has a canary: a fixed window before its pool,
known to contain events, which the catalog step asks for first through the
same request. A service that returns fewer than `min_events` for it is not
trusted, so that a broken service cannot pass for a quiet window (AFAD's event
API answered every query with an empty list on 2026-10-29).
"""
from dataclasses import dataclass

KOERI = "https://eida.koeri.boun.edu.tr"
NOA = "https://eida.gein.noa.gr"
GEONET = "https://service.geonet.org.nz"
GEONET_BUCKET = "https://geonet-open-data.s3-ap-southeast-2.amazonaws.com"
AFAD_EVENTS = "https://servisnet.afad.gov.tr/apigateway/deprem/apiv2/event/filter"
EMSC_EVENTS = "https://www.seismicportal.eu/fdsnws/event/1/query"


@dataclass(frozen=True)
class Canary:
    start: str        # UTC, before the network's pool
    end: str
    lat: float
    lon: float
    radius_km: float
    min_events: int   # about 40% of what the service returned on 2026-10-29


@dataclass(frozen=True)
class Network:
    code: str
    name: str
    base_url: str              # FDSN station and dataselect
    availability: str | None   # fdsnws/availability query URL, or None
    day_listing: str | None    # open-data bucket listed per UTC day, or None
    catalog: str               # "fdsn" or "afad"
    event_url: str             # the catalogue's query URL
    catalog_agency: str
    citation: str
    licence: str
    catalog_citation: str = ""
    canary: Canary | None = None

    @property
    def station_url(self):
        return f"{self.base_url}/fdsnws/station/1/query"

    @property
    def dataselect_url(self):
        return f"{self.base_url}/fdsnws/dataselect/1/query"


# The Sindirgi Mw 6.1 replay of the development data (69 events from EMSC on
# 2026-10-29); tune_greece_1's and tune_nz_1's catalogue windows (14 and 51).
KO_CANARY = Canary("2025-08-10T16:00:00", "2025-08-10T19:00:00", 39.2, 28.2, 150.0, 30)
GREEK_CANARY = Canary("2022-01-15T18:08:00", "2022-01-16T01:08:00", 38.5, 23.5, 950.0, 5)
NZ_CANARY = Canary("2022-01-27T05:19:00", "2022-01-27T12:19:00", -41.0, 174.0, 1300.0, 20)

NETWORKS = {
    "KO": Network(
        code="KO", name="Kandilli Observatory and Earthquake Research Institute (KOERI)",
        base_url=KOERI,
        availability=f"{KOERI}/fdsnws/availability/1/query", day_listing=None,
        # KOERI runs no FDSN event service, and AFAD's event API returned an
        # empty list to every query on 2026-10-29, even for development events
        # by their ids; EMSC's service carries the Turkish agencies' solutions
        # (8 of AFAD's 9 events in the demo window).
        catalog="fdsn", event_url=EMSC_EVENTS,
        catalog_agency="EMSC (European-Mediterranean Seismological Centre)",
        citation=("Kandilli Observatory and Earthquake Research Institute (KOERI), "
                  "Bogazici University. International Federation of Digital "
                  "Seismograph Networks. doi:10.7914/SN/KO"),
        licence="open under citation (doi:10.7914/SN/KO)",
        catalog_citation="EMSC, FDSNWS-event at www.seismicportal.eu",
        canary=KO_CANARY),
    "HL": Network(
        code="HL", name="Hellenic Seismic Network (NOA, Institute of Geodynamics)",
        base_url=NOA,
        availability=f"{NOA}/fdsnws/availability/1/query", day_listing=None,
        catalog="fdsn", event_url=f"{NOA}/fdsnws/event/1/query",
        catalog_agency="NOA (National Observatory of Athens, Institute of Geodynamics)",
        citation=("National Observatory of Athens, Institute of Geodynamics, Athens "
                  "(1975). Hellenic Unified Seismological Network [Dataset]. "
                  "International Federation of Digital Seismograph Networks. "
                  "doi:10.7914/SN/HL"),
        licence="CC BY 4.0 (NOA EIDA node: content shared from its services)",
        catalog_citation="NOA Institute of Geodynamics, FDSNWS-event at eida.gein.noa.gr",
        canary=GREEK_CANARY),
    "HT": Network(
        code="HT", name="Aristotle University of Thessaloniki Seismological Network",
        base_url=NOA,
        availability=f"{NOA}/fdsnws/availability/1/query", day_listing=None,
        catalog="fdsn", event_url=f"{NOA}/fdsnws/event/1/query",
        catalog_agency=("NOA (stand-in: AUTH publishes its catalogue only as a "
                        "text file, see README.md)"),
        citation=("Aristotle University of Thessaloniki (1981). Hellenic Unified "
                  "Seismological Network [Dataset]. International Federation of "
                  "Digital Seismograph Networks. doi:10.7914/SN/HT"),
        licence="CC BY 4.0 (NOA EIDA node: content shared from its services)",
        catalog_citation="NOA Institute of Geodynamics, FDSNWS-event at eida.gein.noa.gr",
        canary=GREEK_CANARY),
    "HA": Network(
        code="HA", name="Hellenic Seismological Network, University of Athens",
        base_url=NOA,
        availability=f"{NOA}/fdsnws/availability/1/query", day_listing=None,
        catalog="fdsn", event_url=f"{NOA}/fdsnws/event/1/query",
        catalog_agency="NOA (National Observatory of Athens, Institute of Geodynamics)",
        citation=("National and Kapodistrian University of Athens (2008). International Federation of Digital "
                  "Seismograph Networks. doi:10.7914/SN/HA"),
        licence="CC BY 4.0 (NOA EIDA node: content shared from its services)",
        catalog_citation="NOA Institute of Geodynamics, FDSNWS-event at eida.gein.noa.gr",
        canary=GREEK_CANARY),
    "HP": Network(
        code="HP", name="University of Patras Seismological Network",
        base_url=NOA,
        availability=f"{NOA}/fdsnws/availability/1/query", day_listing=None,
        catalog="fdsn", event_url=f"{NOA}/fdsnws/event/1/query",
        catalog_agency="NOA (National Observatory of Athens, Institute of Geodynamics)",
        citation=("University of Patras, Geology Department (2000). International Federation of Digital "
                  "Seismograph Networks. doi:10.7914/SN/HP"),
        licence="CC BY 4.0 (NOA EIDA node: content shared from its services)",
        catalog_citation="NOA Institute of Geodynamics, FDSNWS-event at eida.gein.noa.gr",
        canary=GREEK_CANARY),
    "HC": Network(
        code="HC", name="Seismological Network of Crete",
        base_url=NOA,
        availability=f"{NOA}/fdsnws/availability/1/query", day_listing=None,
        catalog="fdsn", event_url=f"{NOA}/fdsnws/event/1/query",
        catalog_agency="NOA (National Observatory of Athens, Institute of Geodynamics)",
        citation=("Technological Educational Institute of Crete (2006). International Federation of Digital "
                  "Seismograph Networks. doi:10.7914/SN/HC"),
        licence="CC BY 4.0 (NOA EIDA node: content shared from its services)",
        catalog_citation="NOA Institute of Geodynamics, FDSNWS-event at eida.gein.noa.gr",
        canary=GREEK_CANARY),
    "NZ": Network(
        code="NZ", name="New Zealand National Seismograph Network (GeoNet)",
        base_url=GEONET, availability=None, day_listing=GEONET_BUCKET,
        catalog="fdsn", event_url=f"{GEONET}/fdsnws/event/1/query",
        catalog_agency="GeoNet (Earth Sciences New Zealand)",
        citation=("GNS Science (2021). GeoNet Aotearoa New Zealand Seismic Digital "
                  "Waveform Dataset [Dataset]. doi:10.21420/G19Y-9D40. We acknowledge "
                  "the New Zealand GeoNet programme and its sponsors NHC, Earth "
                  "Sciences NZ, LINZ, NEMA and MBIE for providing data used in this "
                  "study."),
        licence="CC BY 3.0 NZ (GeoNet data policy)",
        catalog_citation=("GNS Science (1970). GeoNet Aotearoa New Zealand Earthquake "
                          "Catalogue [Dataset]. doi:10.21420/0S8P-TZ38"),
        canary=NZ_CANARY),
}


def get(code):
    try:
        return NETWORKS[code]
    except KeyError:
        raise ValueError(f"unknown network {code!r}; known: {', '.join(sorted(NETWORKS))}") from None
