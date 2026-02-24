from __future__ import annotations

from pathlib import Path
import subprocess
import sys


def main() -> None:
    script = Path(__file__).resolve().parent / "resample_m1_timeframes.py"
    cmd = [
        sys.executable,
        str(script),
        "--timeframes",
        "M15",
        "M30",
        "H1",
        "H4",
        "--overwrite",
    ]
    raise SystemExit(subprocess.call(cmd))


if __name__ == "__main__":
    main()
