from __future__ import annotations

import sys
from pathlib import Path


ALPHA_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ALPHA_ROOT))

from shared.utils.cross_sectional import main  # noqa: E402


if __name__ == "__main__":
    main()
