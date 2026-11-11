import json
import os
import shutil
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

from .domain.catalog import AS_OF
from .generator.pipeline import build
from .generator.profile import Profile
from .io import sha256, write_dataset

SOURCE_NOTE = (
    "Fully synthetic. Names come from short hand written lists, emails use example.edu, no external dataset, "
    "API or scraped data is used, so there is nothing to license or attribute."
)


def command_for(profile: Profile, formats: set[str], anomalies: bool) -> str:
    cmd = f"python -m ledger generate --profile {profile.name} --seed {profile.seed}"
    if profile.name.startswith("scale-"):
        cmd = f"python -m ledger generate --scale {profile.name[6:]} --seed {profile.seed}"
    if formats != {"csv", "json", "sql"}:
        cmd += f" --formats {','.join(sorted(formats))}"
    if not anomalies:
        cmd += " --clean"
    return cmd


def generate(profile: Profile, out: Path, formats: set[str], anomalies: bool = True) -> dict:
    ds = build(profile, anomalies=anomalies)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    files = write_dataset(out, ds.tables, ds.ground_truth, formats)
    entries = [{"path": str(p.relative_to(out)), "bytes": p.stat().st_size, "sha256": sha256(p)} for p in files]
    combined = "".join(e["path"] + e["sha256"] for e in entries)
    manifest = {
        "generator_command": command_for(profile, formats, anomalies),
        "profile": asdict(profile),
        "seed": profile.seed,
        "as_of": AS_OF.isoformat(),
        "anomalies_injected": anomalies,
        "source": SOURCE_NOTE,
        "external_sources": [],
        "row_counts": {name: len(rows) for name, rows in ds.tables.items()},
        "ground_truth_rows": len(ds.ground_truth),
        "files": entries,
        "dataset_sha256": __import__("hashlib").sha256(combined.encode()).hexdigest(),
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def reproduce(args: list[str], work: Path) -> dict:
    runs = []
    for n, hash_seed in enumerate(("1", "2"), start=1):
        out = work / f"run_{n}"
        env = dict(os.environ, PYTHONHASHSEED=hash_seed)
        subprocess.run([sys.executable, "-m", "ledger", "generate", *args, "--out", str(out), "--quiet"],
                       check=True, env=env)
        runs.append(json.loads((out / "manifest.json").read_text()))
    a, b = runs
    files_a = {f["path"]: f["sha256"] for f in a["files"]}
    files_b = {f["path"]: f["sha256"] for f in b["files"]}
    differing = sorted(p for p in files_a.keys() | files_b.keys() if files_a.get(p) != files_b.get(p))
    report = {
        "command": a["generator_command"],
        "runs": 2,
        "python_hash_seeds": ["1", "2"],
        "row_counts_equal": a["row_counts"] == b["row_counts"],
        "files_compared": len(files_a),
        "files_differing": differing,
        "dataset_sha256_run_1": a["dataset_sha256"],
        "dataset_sha256_run_2": b["dataset_sha256"],
        "identical": not differing and a["dataset_sha256"] == b["dataset_sha256"],
        "row_counts": a["row_counts"],
    }
    shutil.rmtree(work, ignore_errors=True)
    return report
