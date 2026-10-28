"""A dataset is a small TOML file in sets/:

    name = "demo_ko"
    network = "KO"                 # or ["HL", "HT"]: one service, one set
    start = "2025-11-10T18:04:00"  # UTC
    end = "2025-11-10T18:35:00"
    centre = [39.22333, 28.16556]  # lat, lon of the target
    radius_km = 150.0              # stations within this distance of the centre
    max_stations = 6               # the nearest that pass the probe
    min_coverage = 0.9             # optional: fraction of the span each channel must cover
    max_azimuth_offset_deg = 5.0   # optional: refuse horizontals further than this from
                                   # N/E (ayzek reads 1/2 as N/E, unrotated); default: keep

    [catalog]                      # optional
    lead_days = 30                 # also the 30 days before the span (ayzek --assess)
    radius_km = 300.0              # events within this distance of the centre
    min_magnitude = 0.0
    # start / end / limit override the window (used only by the 2012 smoke sets)

`load` validates it and returns a SetConfig; nothing is fetched.
"""
import datetime as dt
import tomllib
from dataclasses import asdict, dataclass, field
from pathlib import Path

from . import networks

NAME_CHARS = set("abcdefghijklmnopqrstuvwxyz0123456789_-")


class ConfigError(ValueError):
    pass


def parse_utc(s, what):
    if isinstance(s, dt.datetime):  # an unquoted TOML datetime
        s = s.isoformat()
    if not isinstance(s, str):
        raise ConfigError(f"{what}: expected an ISO time string, got {s!r}")
    try:
        t = dt.datetime.fromisoformat(s.removesuffix("Z"))
    except ValueError:
        raise ConfigError(f"{what}: not an ISO time: {s!r}") from None
    if t.tzinfo is not None:
        t = t.astimezone(dt.UTC).replace(tzinfo=None)
    return t


@dataclass(frozen=True)
class CatalogConfig:
    lead_days: float = 30.0
    radius_km: float | None = None   # default: twice the station radius
    min_magnitude: float | None = None
    start: dt.datetime | None = None
    end: dt.datetime | None = None
    limit: int | None = None


@dataclass(frozen=True)
class SetConfig:
    name: str
    networks: tuple[str, ...]
    start: dt.datetime
    end: dt.datetime
    lat: float
    lon: float
    radius_km: float
    max_stations: int
    min_coverage: float = 0.9
    max_azimuth_offset_deg: float | None = None
    catalog: CatalogConfig = field(default_factory=CatalogConfig)
    source: str = ""

    @property
    def network_info(self):
        return [networks.get(n) for n in self.networks]

    @property
    def base_url(self):
        return self.network_info[0].base_url

    def catalog_window(self):
        c = self.catalog
        t0 = c.start or self.start - dt.timedelta(days=c.lead_days)
        t1 = c.end or self.end
        return t0, t1

    def catalog_radius_km(self):
        return self.catalog.radius_km if self.catalog.radius_km is not None else 2 * self.radius_km

    def to_json(self):
        d = asdict(self)
        for k in ("start", "end"):
            d[k] = d[k].isoformat()
        for k in ("start", "end"):
            if d["catalog"][k] is not None:
                d["catalog"][k] = d["catalog"][k].isoformat()
        d["networks"] = list(self.networks)
        return d


def _number(d, key, what, default=None, kind=float):
    if key not in d:
        if default is None:
            raise ConfigError(f"{what}: missing {key!r}")
        return default
    v = d[key]
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise ConfigError(f"{what}: {key} must be a number, got {v!r}")
    if kind is int and not isinstance(v, int):
        raise ConfigError(f"{what}: {key} must be an integer, got {v!r}")
    return kind(v)


def parse(d, source=""):
    what = source or "config"
    known = {"name", "network", "start", "end", "centre", "radius_km",
             "max_stations", "min_coverage", "max_azimuth_offset_deg", "catalog"}
    extra = set(d) - known
    if extra:
        raise ConfigError(f"{what}: unknown keys {sorted(extra)}")
    name = d.get("name")
    if not isinstance(name, str) or not name or not set(name) <= NAME_CHARS:
        raise ConfigError(f"{what}: name must be lower-case letters, digits, _ or -, got {name!r}")
    net = d.get("network")
    nets = (net,) if isinstance(net, str) else tuple(net) if isinstance(net, list) else ()
    if not nets or not all(isinstance(n, str) for n in nets):
        raise ConfigError(f"{what}: network must be a code or a list of codes")
    try:
        info = [networks.get(n) for n in nets]
    except ValueError as e:
        raise ConfigError(f"{what}: {e}") from None
    if len({i.base_url for i in info}) != 1 or len(set(nets)) != len(nets):
        raise ConfigError(f"{what}: the networks of one set must be distinct and share a service")
    start = parse_utc(d.get("start"), f"{what}: start")
    end = parse_utc(d.get("end"), f"{what}: end")
    if end <= start:
        raise ConfigError(f"{what}: end {end} is not after start {start}")
    centre = d.get("centre")
    if (not isinstance(centre, list) or len(centre) != 2
            or not all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in centre)):
        raise ConfigError(f"{what}: centre must be [lat, lon]")
    lat, lon = map(float, centre)
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ConfigError(f"{what}: centre {centre} out of range")
    radius = _number(d, "radius_km", what)
    if not 0 < radius <= 2000:
        raise ConfigError(f"{what}: radius_km must be in (0, 2000], got {radius}")
    nmax = _number(d, "max_stations", what, kind=int)
    if nmax < 1:
        raise ConfigError(f"{what}: max_stations must be at least 1")
    cov = _number(d, "min_coverage", what, default=0.9)
    if not 0 <= cov <= 1:
        raise ConfigError(f"{what}: min_coverage must be in [0, 1]")
    azmax = (_number(d, "max_azimuth_offset_deg", what)
             if "max_azimuth_offset_deg" in d else None)
    if azmax is not None and not 0 <= azmax <= 180:
        raise ConfigError(f"{what}: max_azimuth_offset_deg must be in [0, 180]")
    c = d.get("catalog", {})
    if not isinstance(c, dict):
        raise ConfigError(f"{what}: [catalog] must be a table")
    extra = set(c) - {"lead_days", "radius_km", "min_magnitude", "start", "end", "limit"}
    if extra:
        raise ConfigError(f"{what}: unknown catalog keys {sorted(extra)}")
    cat = CatalogConfig(
        lead_days=_number(c, "lead_days", what, default=30.0),
        radius_km=_number(c, "radius_km", what) if "radius_km" in c else None,
        min_magnitude=_number(c, "min_magnitude", what) if "min_magnitude" in c else None,
        start=parse_utc(c["start"], f"{what}: catalog.start") if "start" in c else None,
        end=parse_utc(c["end"], f"{what}: catalog.end") if "end" in c else None,
        limit=_number(c, "limit", what, kind=int) if "limit" in c else None)
    if cat.lead_days < 0:
        raise ConfigError(f"{what}: catalog.lead_days must be >= 0")
    if (cat.start is None) != (cat.end is None):
        raise ConfigError(f"{what}: catalog.start and catalog.end go together")
    if cat.start is not None and cat.end <= cat.start:
        raise ConfigError(f"{what}: catalog.end is not after catalog.start")
    if cat.limit is not None and cat.limit < 1:
        raise ConfigError(f"{what}: catalog.limit must be at least 1")
    return SetConfig(name=name, networks=nets, start=start, end=end, lat=lat, lon=lon,
                     radius_km=radius, max_stations=nmax, min_coverage=cov,
                     max_azimuth_offset_deg=azmax, catalog=cat, source=source)


def load(path):
    path = Path(path)
    try:
        d = tomllib.loads(path.read_text())
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"{path}: {e}") from None
    return parse(d, source=str(path))
