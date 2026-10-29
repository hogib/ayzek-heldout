"""Fetches an ayzek replay dataset (KO, HL/HT or NZ) described by a sets/*.toml.

    heldout probe    sets/demo_ko.toml   # metadata + availability: stations.json,
                                         # stationxml/, stations.csv, pd_gain.csv
    heldout pull     sets/demo_ko.toml   # waveforms hour by hour, dataset.json
    heldout catalog  sets/demo_ko.toml   # the network's catalogue -> catalog.csv
    heldout validate sets/demo_ko.toml   # dataset.json against the files

`pull` and `catalog` refuse any window reaching into a network's held-out pool (the
held-out test period) unless --allow-test-period is given. `probe` reads
metadata and availability only and is never guarded. Output goes to
DATA/<set>/ (--data, default ./data).
"""
import argparse
import sys

from . import config, fetch, rules


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
    a = p.parse_args(argv)
    try:
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
