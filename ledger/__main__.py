import argparse
import json
import sys
from pathlib import Path

from . import dictionary
from .generate import generate, reproduce
from .generator.profile import DEFAULT_SEED, PROFILES, Profile, scaled


def pick_profile(args) -> Profile:
    if args.scale is not None:
        return scaled(args.scale, seed=args.seed)
    base = PROFILES[args.profile]
    return Profile(**{**base.__dict__, "seed": args.seed})


def add_profile_args(p) -> None:
    p.add_argument("--profile", choices=sorted(PROFILES), default="starter")
    p.add_argument("--scale", type=float, default=None, help="fraction of the full volume, overrides --profile")
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)


def main() -> None:
    parser = argparse.ArgumentParser(prog="ledger")
    sub = parser.add_subparsers(dest="command", required=True)

    d = sub.add_parser("dictionary", help="write the data dictionary")
    d.add_argument("--out", default="docs")

    g = sub.add_parser("generate", help="generate the synthetic dataset")
    add_profile_args(g)
    g.add_argument("--out", default=None)
    g.add_argument("--formats", default="csv,json,sql")
    g.add_argument("--clean", action="store_true", help="skip anomaly injection")
    g.add_argument("--quiet", action="store_true")

    r = sub.add_parser("reproduce", help="generate twice and compare checksums")
    add_profile_args(r)
    r.add_argument("--formats", default="csv")
    r.add_argument("--report", default=None)

    args = parser.parse_args()
    if args.command == "dictionary":
        dictionary.write(Path(args.out))
        print(f"wrote {args.out}/data_dictionary.md and data_dictionary.csv")
    elif args.command == "generate":
        profile = pick_profile(args)
        out = Path(args.out or f"data/{profile.name}")
        manifest = generate(profile, out, set(args.formats.split(",")), anomalies=not args.clean)
        if not args.quiet:
            print(f"wrote {out} with {len(manifest['files'])} files, dataset sha256 {manifest['dataset_sha256'][:16]}")
            for name, count in manifest["row_counts"].items():
                print(f"  {name}: {count}")
            print(f"  ground_truth: {manifest['ground_truth_rows']}")
    elif args.command == "reproduce":
        cli = ["--seed", str(args.seed), "--formats", args.formats]
        cli += ["--scale", str(args.scale)] if args.scale is not None else ["--profile", args.profile]
        report = reproduce(cli, Path("data/tmp/reproduce"))
        text = json.dumps(report, indent=2)
        if args.report:
            Path(args.report).write_text(text + "\n")
        print(text)
        sys.exit(0 if report["identical"] else 1)


if __name__ == "__main__":
    main()
