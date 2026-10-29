"""Fetches an ayzek replay dataset (KO, HL/HT or NZ) described by a sets/*.toml.

    heldout probe    sets/demo_ko.toml   # metadata + availability: stations.json,
                                         # stationxml/, stations.csv, pd_gain.csv
    heldout pull     sets/demo_ko.toml   # waveforms hour by hour, dataset.json
    heldout catalog  sets/demo_ko.toml   # the network's catalogue -> catalog.csv
    heldout validate sets/demo_ko.toml   # dataset.json against the files
    heldout verify   data/demo_ko        # every file against its recorded SHA-256
    heldout select greece --start ... --end ... --name now
                                         # a pool's sequences, reserve split and
                                         # quiet windows -> set configs (select.py)

`pull`, `catalog` and `select` refuse any window reaching into a network's held-out
pool (the held-out test period) unless --allow-test-period is given. `probe` reads
metadata and availability only and is never guarded. Output goes to
DATA/<set>/ (--data, default ./data).
"""
import argparse
import sys

from . import config, fetch, rules, select


def main(argv=None):
    p = argparse.ArgumentParser(prog="heldout", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    for name, helptext in (("probe", "choose stations from metadata and availability"),
                           ("pull", "download the chosen stations"),
                           ("catalog", "the network's catalogue for the set"),
                           ("validate", "check dataset.json against the files")):
        s = sub.add_parser(name, help=helptext)
        s.add_argument("config", help="sets/<name>.toml")
        s.add_argument("--data", default="data", help="parent of the set directory")
        if name in ("pull", "catalog"):
            s.add_argument("--allow-test-period", action="store_true",
                           help="allow windows in the held-out pools (only after the freeze)")
        if name == "pull":
            s.add_argument("--force", action="store_true", help="re-download files present")
    s = sub.add_parser("verify", help="check a set's files against dataset.json's SHA-256")
    s.add_argument("setdir", help="a set directory (DATA/<set>)")
    s = sub.add_parser("select", help="a pool's sequences, reserve split and quiet windows")
    s.add_argument("group", choices=sorted(select.GROUPS))
    s.add_argument("--start", required=True, help="UTC, ISO")
    s.add_argument("--end", required=True, help="UTC, ISO (the freeze, for a pool)")
    s.add_argument("--name", required=True, help="e.g. now, prospective, dry2022")
    s.add_argument("--out", default="selections")
    s.add_argument("--prospective", action="store_true",
                   help="no reserve split; quiet seed 44 (protocol section 10)")
    s.add_argument("--target", type=int, help="scorable events (default: the protocol's)")
    s.add_argument("--no-quiet", action="store_true", help="sequences only")
    s.add_argument("--allow-test-period", action="store_true",
                   help="allow a held-out pool (only after the freeze)")
    a = p.parse_args(argv)
    try:
        if a.cmd == "verify":
            return fetch.cmd_verify(a.setdir)
        if a.cmd == "select":
            return select.cmd_select(
                a.group, config.parse_utc(a.start, "--start"), config.parse_utc(a.end, "--end"),
                a.name, a.out, a.prospective, a.target, not a.no_quiet, a.allow_test_period)
        cfg = config.load(a.config)
        if a.cmd == "probe":
            return fetch.cmd_probe(cfg, a.data)
        if a.cmd == "pull":
            return fetch.cmd_pull(cfg, a.data, a.allow_test_period, a.force)
        if a.cmd == "catalog":
            return fetch.cmd_catalog(cfg, a.data, a.allow_test_period)
        return fetch.cmd_validate(cfg, a.data)
    except (config.ConfigError, rules.TestPeriodError, FileNotFoundError) as e:
        print(f"heldout: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
