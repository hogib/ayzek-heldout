"""Writes the set configs of the per-station STA/LTA tuning data (held-out
protocol, section 4): for each test network group, four 6 h windows with start
times drawn uniformly, on the minute, from its pre-pool period, by a fixed seed.

    python3 tools/make_tuning_sets.py

Every station of the group within the radius goes into the window's set (the
probe keeps those with three 100 Hz HH channels and the coverage rule). These
windows are before the pools: Greece and New Zealand 2022, KO from 2026-07-01
to 2026-08-29 (its pool starts 2026-08-30).
"""
import datetime as dt
import random
from pathlib import Path

SEED = 20221231
WINDOWS, HOURS = 4, 6
GROUPS = {
    # name: (networks, period start, period end, centre, radius km)
    "greece": (["HL", "HT", "HA", "HP", "HC"], "2022-01-01", "2023-01-01", (38.5, 23.5), 650.0),
    "nz": (["NZ"], "2022-01-01", "2023-01-01", (-41.0, 174.0), 1000.0),
    "ko": (["KO"], "2026-07-01", "2026-08-30", (39.0, 35.0), 1100.0),
}

rng = random.Random(SEED)
out = Path(__file__).resolve().parents[1] / "sets"
for name, (nets, a, b, (lat, lon), radius) in GROUPS.items():
    t0, t1 = dt.datetime.fromisoformat(a), dt.datetime.fromisoformat(b)
    span = int((t1 - t0).total_seconds() // 60) - HOURS * 60
    starts = sorted(t0 + dt.timedelta(minutes=rng.randrange(span)) for _ in range(WINDOWS))
    for i, s in enumerate(starts, 1):
        e = s + dt.timedelta(hours=HOURS)
        net = nets[0] if len(nets) == 1 else nets
        text = (f"# Per-station STA/LTA tuning data (protocol section 4), window {i} of "
                f"{WINDOWS}, drawn by tools/make_tuning_sets.py (seed {SEED}) from the\n"
                f"# pre-pool period {a} to {b}.\n"
                f'name = "tune_{name}_{i}"\n'
                f"network = {net!r}\n".replace("'", '"') +
                f'start = "{s.isoformat()}"\nend = "{e.isoformat()}"\n'
                f"centre = [{lat}, {lon}]\nradius_km = {radius}\nmax_stations = 300\n"
                f"\n[catalog]\nstart = \"{(s - dt.timedelta(hours=1)).isoformat()}\"\n"
                f"end = \"{e.isoformat()}\"\nradius_km = {radius + 300.0}\n")
        (out / f"tune_{name}_{i}.toml").write_text(text)
        print(f"tune_{name}_{i}: {s} to {e}")
