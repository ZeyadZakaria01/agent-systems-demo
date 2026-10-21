"""The run of record: a finished run copied from `demo/results/<run id>/` (git-ignored) into the tracked
`demo/record/<run id>/`. The scorecard, `results.json` and the snapshots go; databases stay in `.runtime/` (the
results cite their absolute paths) and logs stay with the run. The scorecard's snapshot links are relative to the run
folder, so they resolve inside the record. `python -m demo.record <run dir>` does the copy for a run already made;
`python -m demo.run --record` does it as the final step.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from demo.paths import RECORD_ROOT

COPIED = ("scorecard.md", "results.json", "snapshots")


def record_run(run_dir: Path, record_root: Path = RECORD_ROOT) -> Path:
    target = record_root / run_dir.name
    if target.exists():
        raise FileExistsError(f"{target} already exists; a run of record is never overwritten")
    target.mkdir(parents=True)
    for name in COPIED:
        src = run_dir / name
        if src.is_dir():
            shutil.copytree(src, target / name)
        elif src.exists():
            shutil.copy2(src, target / name)
    return target


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m demo.record", description=__doc__.split("\n\n")[0])
    ap.add_argument("run_dir", type=Path)
    print(record_run(ap.parse_args(argv).run_dir.resolve()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
