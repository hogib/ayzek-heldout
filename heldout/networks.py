"""The networks the tool fetches: where each one's services are, how to cite
it, and which catalogue goes with it.

Greek HL (NOA) and HT (AUTH) are both served by the NOA EIDA node, which also
hosts their availability service and NOA's event service. AUTH's own
catalogue is a flat text file, not a service (SURVEY.md), so the HT catalogue
is NOA's for now; see README.md.
"""
from dataclasses import dataclass

KOERI = "https://eida.koeri.boun.edu.tr"
NOA = "https://eida.gein.noa.gr"
GEONET = "https://service.geonet.org.nz"
GEONET_BUCKET = "https://geonet-open-data.s3-ap-southeast-2.amazonaws.com"
AFAD_EVENTS = "https://servisnet.afad.gov.tr/apigateway/deprem/apiv2/event/filter"


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

    @property
    def station_url(self):
        return f"{self.base_url}/fdsnws/station/1/query"

    @property
    def dataselect_url(self):
        return f"{self.base_url}/fdsnws/dataselect/1/query"


NETWORKS = {
    "KO": Network(
        code="KO", name="Kandilli Observatory and Earthquake Research Institute (KOERI)",
        base_url=KOERI,
        availability=f"{KOERI}/fdsnws/availability/1/query", day_listing=None,
        # KOERI runs no FDSN event service; ayzek's KO development catalogues
        # are AFAD's, so the KO sets use AFAD's too.
        catalog="afad", event_url=AFAD_EVENTS,
        catalog_agency="AFAD (Disaster and Emergency Management Authority, Turkiye)",
        citation=("Kandilli Observatory and Earthquake Research Institute (KOERI), "
                  "Bogazici University. International Federation of Digital "
                  "Seismograph Networks. doi:10.7914/SN/KO"),
        licence="open under citation (doi:10.7914/SN/KO)",
        catalog_citation="AFAD earthquake catalogue, https://deprem.afad.gov.tr"),
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
        catalog_citation="NOA Institute of Geodynamics, FDSNWS-event at eida.gein.noa.gr"),
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
        catalog_citation="NOA Institute of Geodynamics, FDSNWS-event at eida.gein.noa.gr"),
    "HA": Network(
        code="HA", name="Hellenic Seismological Network, University of Athens",
        base_url=NOA,
        availability=f"{NOA}/fdsnws/availability/1/query", day_listing=None,
        catalog="fdsn", event_url=f"{NOA}/fdsnws/event/1/query",
        catalog_agency="NOA (National Observatory of Athens, Institute of Geodynamics)",
        citation=("National and Kapodistrian University of Athens (2008). International Federation of Digital "
                  "Seismograph Networks. doi:10.7914/SN/HA"),
        licence="CC BY 4.0 (NOA EIDA node: content shared from its services)",
        catalog_citation="NOA Institute of Geodynamics, FDSNWS-event at eida.gein.noa.gr"),
    "HP": Network(
        code="HP", name="University of Patras Seismological Network",
        base_url=NOA,
        availability=f"{NOA}/fdsnws/availability/1/query", day_listing=None,
        catalog="fdsn", event_url=f"{NOA}/fdsnws/event/1/query",
        catalog_agency="NOA (National Observatory of Athens, Institute of Geodynamics)",
        citation=("University of Patras, Geology Department (2000). International Federation of Digital "
                  "Seismograph Networks. doi:10.7914/SN/HP"),
        licence="CC BY 4.0 (NOA EIDA node: content shared from its services)",
        catalog_citation="NOA Institute of Geodynamics, FDSNWS-event at eida.gein.noa.gr"),
    "HC": Network(
        code="HC", name="Seismological Network of Crete",
        base_url=NOA,
        availability=f"{NOA}/fdsnws/availability/1/query", day_listing=None,
        catalog="fdsn", event_url=f"{NOA}/fdsnws/event/1/query",
        catalog_agency="NOA (National Observatory of Athens, Institute of Geodynamics)",
        citation=("Technological Educational Institute of Crete (2006). International Federation of Digital "
                  "Seismograph Networks. doi:10.7914/SN/HC"),
        licence="CC BY 4.0 (NOA EIDA node: content shared from its services)",
        catalog_citation="NOA Institute of Geodynamics, FDSNWS-event at eida.gein.noa.gr"),
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
                          "Catalogue [Dataset]. doi:10.21420/0S8P-TZ38")),
}


def get(code):
    try:
        return NETWORKS[code]
    except KeyError:
        raise ValueError(f"unknown network {code!r}; known: {', '.join(sorted(NETWORKS))}") from None
